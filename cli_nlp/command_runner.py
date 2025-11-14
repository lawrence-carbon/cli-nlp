"""Command generation and execution for CLI-NLP."""

import importlib.util
import json
import os
import subprocess
import sys
from typing import Any

import click
from rich.panel import Panel

from cli_nlp.cache_manager import CacheManager
from cli_nlp.config_manager import ConfigManager
from cli_nlp.context_manager import ContextManager
from cli_nlp.history_manager import HistoryManager
from cli_nlp.models import CommandResponse, MultiCommandResponse, SafetyLevel
from cli_nlp.utils import console, copy_to_clipboard


class CommandRunner:
    """Handles command generation and execution."""

    SYSTEM_PROMPT = """You are a helpful assistant that converts natural language requests into shell commands.

You must analyze each command to determine if it will modify the system or only read/display information.

A command is considered MODIFYING (not safe) if it:
- Writes, creates, modifies, or deletes files
- Changes system configuration
- Installs or removes software
- Modifies environment variables
- Kills or modifies processes
- Changes file permissions or ownership
- Any operation that alters system state

A command is considered SAFE (read-only) if it:
- Lists or displays information
- Searches for files without modifying them
- Shows system status or statistics
- Reads configuration without changing it
- Displays process information
- Any operation that only reads/displays data

Rules:
1. Provide the shell command itself
2. Use standard Unix/Linux commands (bash, zsh compatible)
3. If the request is ambiguous or potentially dangerous, still provide the command but make it safe
4. For file operations, use relative paths when possible
5. Prefer common, portable commands over system-specific ones
6. Accurately assess if the command modifies the system or is read-only

Examples:
- "list all python files" -> command: "find . -name '*.py'", is_safe: true (read-only)
- "show disk usage" -> command: "df -h", is_safe: true (read-only)
- "create a file test.txt" -> command: "touch test.txt", is_safe: false (creates file)
- "delete all .pyc files" -> command: "find . -name '*.pyc' -delete", is_safe: false (deletes files)
- "kill process on port 3000" -> command: "lsof -ti:3000 | xargs kill -9", is_safe: false (kills process)
"""

    def __init__(
        self,
        config_manager: ConfigManager,
        history_manager: HistoryManager | None = None,
        cache_manager: CacheManager | None = None,
        context_manager: ContextManager | None = None,
    ):
        self.config_manager = config_manager
        self.history_manager = history_manager or HistoryManager()
        self.cache_manager = cache_manager or CacheManager(
            ttl_seconds=config_manager.get("cache_ttl_seconds", 86400)
        )
        self.context_manager = context_manager or ContextManager()

    @staticmethod
    def _coerce_bool(value: Any) -> bool:
        """Normalize truthy values coming back from LLM responses."""
        if isinstance(value, bool):
            return value
        if isinstance(value, int | float):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "yes", "y", "1"}:
                return True
            if normalized in {"false", "no", "n", "0"}:
                return False
        # Default to False for unknown values (safer assumption)
        return False

    @staticmethod
    def _normalize_safety_level(value: Any, is_safe: bool | None) -> str:
        """Map varied safety level strings into canonical enum values."""
        if isinstance(value, SafetyLevel):
            return value.value
        if isinstance(value, str):
            normalized = value.strip().lower().replace("_", "-")
            mapping = {
                "safe": SafetyLevel.SAFE.value,
                "read-only": SafetyLevel.SAFE.value,
                "readonly": SafetyLevel.SAFE.value,
                "read only": SafetyLevel.SAFE.value,
                "non-modifying": SafetyLevel.SAFE.value,
                "non modifying": SafetyLevel.SAFE.value,
                "modifying": SafetyLevel.MODIFYING.value,
                "unsafe": SafetyLevel.MODIFYING.value,
                "dangerous": SafetyLevel.MODIFYING.value,
                "write": SafetyLevel.MODIFYING.value,
                "modifies": SafetyLevel.MODIFYING.value,
            }
            if normalized in mapping:
                return mapping[normalized]
        if isinstance(is_safe, bool):
            return SafetyLevel.SAFE.value if is_safe else SafetyLevel.MODIFYING.value
        # Fall back to the more conservative option
        return SafetyLevel.MODIFYING.value

    @classmethod
    def _prepare_command_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        """Normalize raw payload data so it can be parsed by CommandResponse."""
        normalized: dict[str, Any] = dict(payload)

        # Ensure command is a plain string
        command = normalized.get("command", "")
        if command is None:
            command = ""
        normalized["command"] = str(command).strip()

        # Normalize boolean flags that can come back as strings
        normalized["is_safe"] = cls._coerce_bool(normalized.get("is_safe", False))

        # Normalize safety level and add default when missing
        safety_level = normalized.get("safety_level")
        normalized["safety_level"] = cls._normalize_safety_level(
            safety_level, normalized["is_safe"]
        )

        # Explanation can be null or another type; coerce to string if needed
        explanation = normalized.get("explanation")
        if explanation is not None and not isinstance(explanation, str):
            normalized["explanation"] = str(explanation)

        return normalized

    @classmethod
    def _build_command_response(cls, payload: dict[str, Any]) -> CommandResponse:
        """Create a CommandResponse from raw payload data."""
        normalized_payload = cls._prepare_command_payload(payload)
        return CommandResponse(**normalized_payload)

    def _setup_litellm_api_key(self):
        """Setup LiteLLM API key from config."""
        try:
            litellm_spec = importlib.util.find_spec("litellm")
        except ValueError:
            # Module is already present in sys.modules (e.g., mocked in tests)
            litellm_spec = True

        if litellm_spec is None:
            console.print("[red]Error: LiteLLM package not installed.[/red]")
            console.print("[yellow]Please install it with: poetry install[/yellow]")
            sys.exit(1)

        api_key = self.config_manager.get_api_key()
        active_provider = self.config_manager.get_active_provider()
        config = self.config_manager.load()
        providers = config.get("providers", {})
        config_exists = self.config_manager.config_path.exists()

        if not api_key:
            config_path = self.config_manager.config_path

            # Detect fresh installation (no config file or no providers)
            if not config_exists or not providers:
                console.print("[bold yellow]Welcome to CLI-NLP! 🎉[/bold yellow]")
                console.print("\n[bold]First-time setup required:[/bold]")
                console.print("You need to configure an LLM provider to get started.\n")
                console.print("[bold cyan]Quick start:[/bold cyan]")
                console.print("  Run: [green]qtc config providers set[/green]")
                console.print("\nThis will guide you through:")
                console.print(
                    "  • Selecting a provider (OpenAI, Anthropic, Google, etc.)"
                )
                console.print("  • Choosing a model")
                console.print("  • Entering your API key securely")
                console.print(
                    "\n[dim]The config file will be created automatically at:[/dim]"
                )
                console.print(f"[dim]{config_path}[/dim]")
                console.print(
                    "\n[dim]Alternative: Set environment variables (e.g., OPENAI_API_KEY)[/dim]"
                )
            else:
                # Config exists but no active provider or API key
                console.print(
                    "[red]Error: API key not found for active provider.[/red]"
                )
                if not active_provider:
                    console.print("\n[yellow]No active provider configured.[/yellow]")
                    console.print(
                        "Run: [green]qtc config providers set[/green] to configure a provider."
                    )
                else:
                    console.print(
                        f"\n[yellow]Active provider '{active_provider}' is missing an API key.[/yellow]"
                    )
                    console.print("Please either:")
                    console.print("  1. Run: [green]qtc config providers set[/green]")
                    console.print("  2. Set provider-specific environment variable")
                    console.print(f"  3. Add provider config to: {config_path}")
            sys.exit(1)

        # Set API key in environment for LiteLLM
        # LiteLLM reads from environment variables
        if active_provider:
            env_var_map = {
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "cohere": "COHERE_API_KEY",
                "google": "GOOGLE_API_KEY",
                "mistral": "MISTRAL_API_KEY",
                "azure": "AZURE_API_KEY",
            }
            env_var = env_var_map.get(active_provider.lower())
            if env_var and not os.getenv(env_var):
                os.environ[env_var] = api_key
        else:
            # Fallback to OPENAI_API_KEY
            if not os.getenv("OPENAI_API_KEY"):
                os.environ["OPENAI_API_KEY"] = api_key

    def generate_command(
        self,
        query: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        use_cache: bool = True,
    ) -> CommandResponse:
        """
        Generate a shell command from natural language query with safety analysis.

        Args:
            query: Natural language query
            model: OpenAI model to use (defaults to config or gpt-4o-mini)
            temperature: Temperature for generation (defaults to config or 0.3)
            max_tokens: Max tokens for response (defaults to config or 200)
            use_cache: Whether to use cache (default: True)

        Returns:
            CommandResponse object containing command and safety information
        """
        # Setup LiteLLM API key
        self._setup_litellm_api_key()

        # Use provided values or fall back to config or defaults
        model = model or self.config_manager.get_active_model()
        temperature = (
            temperature
            if temperature is not None
            else self.config_manager.get("temperature", 0.3)
        )
        max_tokens = (
            max_tokens
            if max_tokens is not None
            else self.config_manager.get("max_tokens", 200)
        )

        # Check cache first
        if use_cache:
            cached_response = self.cache_manager.get(query, model=model)
            if cached_response:
                return cached_response

        # Build context-aware prompt
        context_str = self.context_manager.build_context_string(
            include_git=self.config_manager.get("include_git_context", True)
        )
        context_prompt = (
            f"{context_str}\n\nUser request: {query}" if context_str else query
        )

        try:
            import litellm
        except ImportError:
            console.print("[red]Error: LiteLLM package not installed.[/red]")
            console.print("[yellow]Please install it with: poetry install[/yellow]")
            sys.exit(1)

        try:
            with console.status("[bold green]Generating command..."):
                # Try Pydantic structured output first (for models that support it)
                try:
                    # Get JSON schema from Pydantic model
                    json_schema = CommandResponse.model_json_schema()

                    # Try using JSON schema structured output
                    response = litellm.completion(
                        model=model,
                        messages=[
                            {"role": "system", "content": self.SYSTEM_PROMPT},
                            {"role": "user", "content": context_prompt},
                        ],
                        response_format={
                            "type": "json_schema",
                            "json_schema": json_schema,
                            "strict": True,
                        },
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )

                    content = response.choices[0].message.content.strip()
                    data = json.loads(content)

                    # Create CommandResponse from JSON
                    command_response = self._build_command_response(data)
                    # Cache the response
                    if use_cache:
                        self.cache_manager.set(query, command_response, model=model)

                    return command_response
                except Exception:
                    # Fallback: Use JSON mode (requires "json" in prompt)
                    try:
                        system_prompt_with_json = (
                            self.SYSTEM_PROMPT
                            + '\n\nYou must respond with a valid JSON object matching this schema: {"command": "string", "is_safe": boolean, "safety_level": "safe" or "modifying", "explanation": "string (optional)"}'
                        )

                        response = litellm.completion(
                            model=model,
                            messages=[
                                {"role": "system", "content": system_prompt_with_json},
                                {"role": "user", "content": context_prompt},
                            ],
                            response_format={"type": "json_object"},
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )

                        content = response.choices[0].message.content.strip()
                        data = json.loads(content)

                        # Create CommandResponse from JSON
                        command_response = self._build_command_response(data)
                        # Cache the response
                        if use_cache:
                            self.cache_manager.set(query, command_response, model=model)

                        return command_response
                    except Exception:
                        # Final fallback: No structured output
                        response = litellm.completion(
                            model=model,
                            messages=[
                                {
                                    "role": "system",
                                    "content": self.SYSTEM_PROMPT
                                    + '\n\nYou must respond with a valid JSON object matching this schema: {"command": "string", "is_safe": boolean, "safety_level": "safe" or "modifying", "explanation": "string (optional)"}',
                                },
                                {"role": "user", "content": context_prompt},
                            ],
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )

                        content = response.choices[0].message.content.strip()
                        # Try to extract JSON from response if it's wrapped
                        if "```json" in content:
                            import re

                            json_match = re.search(
                                r"```json\n(.*?)\n```", content, re.DOTALL
                            )
                            if json_match:
                                content = json_match.group(1)
                        elif "```" in content:
                            import re

                            json_match = re.search(
                                r"```\n(.*?)\n```", content, re.DOTALL
                            )
                            if json_match:
                                content = json_match.group(1)

                        data = json.loads(content)

                        # Create CommandResponse from JSON
                        command_response = self._build_command_response(data)
                        # Cache the response
                        if use_cache:
                            self.cache_manager.set(query, command_response, model=model)

                        return command_response

        except Exception as e:
            console.print(f"[red]Error generating command: {e}[/red]")
            active_provider = self.config_manager.get_active_provider()
            if active_provider:
                console.print(
                    f"[yellow]Active provider: {active_provider}, Model: {model}[/yellow]"
                )
            console.print(
                "[yellow]Please check your API key and provider configuration.[/yellow]"
            )
            sys.exit(1)

    def refine_command(
        self,
        original_query: str,
        refinement_request: str,
        original_command: str | None = None,
        model: str | None = None,
    ) -> CommandResponse:
        """
        Refine an existing command based on user feedback.

        Args:
            original_query: Original natural language query
            refinement_request: User's refinement request (e.g., "make it recursive", "add verbose flag")
            original_command: The original command (optional, will regenerate if not provided)
            model: OpenAI model to use

        Returns:
            Refined CommandResponse
        """
        if original_command:
            refinement_prompt = f"""Original query: {original_query}
Original command: {original_command}
Refinement request: {refinement_request}

Please provide a refined version of the command based on the refinement request."""
        else:
            refinement_prompt = f"""Original query: {original_query}
Refinement request: {refinement_request}

Please provide an improved version of the command based on the refinement request."""

        return self.generate_command(refinement_prompt, model=model, use_cache=False)

    def generate_alternatives(
        self,
        query: str,
        count: int = 3,
        model: str | None = None,
    ) -> list[CommandResponse]:
        """
        Generate alternative command options for a query.

        Args:
            query: Natural language query
            count: Number of alternatives to generate (default: 3)
            model: OpenAI model to use

        Returns:
            List of CommandResponse alternatives
        """
        alternatives_prompt = f"""Generate {count} different shell command alternatives for this request: {query}

Provide {count} distinct approaches, each with different flags, tools, or methods. Return them as a JSON array where each element has: command, is_safe, safety_level, and explanation."""

        try:
            self._setup_litellm_api_key()
            import litellm

            model = model or self.config_manager.get_active_model()
            temperature = self.config_manager.get("temperature", 0.3)
            max_tokens = self.config_manager.get(
                "max_tokens", 500
            )  # More tokens for multiple commands

            with console.status("[bold green]Generating alternatives..."):
                response = litellm.completion(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": self.SYSTEM_PROMPT
                            + "\n\nYou must respond with a valid JSON object containing an 'alternatives' array of command objects, each with: command, is_safe, safety_level, and explanation.",
                        },
                        {"role": "user", "content": alternatives_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=temperature
                    + 0.2,  # Slightly higher temperature for variety
                    max_tokens=max_tokens,
                )

                content = response.choices[0].message.content.strip()
                data = json.loads(content)

                # Handle different response formats
                if isinstance(data, list):
                    alternatives_data = data
                elif "alternatives" in data:
                    alternatives_data = data["alternatives"]
                elif "commands" in data:
                    alternatives_data = data["commands"]
                else:
                    # Assume the whole object is a single command wrapped
                    alternatives_data = [data]

                alternatives = []
                for alt_data in alternatives_data[:count]:
                    payload = {
                        "command": alt_data.get("command", ""),
                        "is_safe": alt_data.get("is_safe", False),
                        "safety_level": alt_data.get("safety_level"),
                        "explanation": alt_data.get("explanation"),
                    }
                    alternatives.append(self._build_command_response(payload))
                return alternatives
        except Exception as e:
            console.print(f"[red]Error generating alternatives: {e}[/red]")
            # Fallback to single command
            return [self.generate_command(query, model=model)]

    def generate_multi_command(
        self,
        query: str,
        model: str | None = None,
    ) -> MultiCommandResponse:
        """
        Generate multiple commands for complex queries (chaining, pipelines, etc.).

        Args:
            query: Natural language query that may require multiple commands
            model: OpenAI model to use

        Returns:
            MultiCommandResponse with multiple commands
        """
        multi_prompt = f"""Analyze this request and determine if it requires multiple commands: {query}

If the request involves:
- Multiple steps (e.g., "list files and then count lines")
- Piping data between commands (e.g., "find files and grep for pattern")
- Sequential operations (e.g., "create directory then copy files")
- Parallel operations

Return a JSON object with:
- commands: array of command objects (each with command, is_safe, safety_level, explanation)
- execution_type: "sequence" (one after another), "pipeline" (piped with |), or "parallel" (simultaneously)
- combined_command: the full combined command string if applicable
- overall_safe: true if all commands are safe
- explanation: brief explanation

If it's a simple single command, return it as a single-item array."""

        try:
            self._setup_litellm_api_key()
            import litellm

            model = model or self.config_manager.get_active_model()
            temperature = self.config_manager.get("temperature", 0.3)
            max_tokens = self.config_manager.get("max_tokens", 500)

            with console.status("[bold green]Generating commands..."):
                response = litellm.completion(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": self.SYSTEM_PROMPT
                            + "\n\nYou must respond with a valid JSON object containing commands array, execution_type, combined_command, overall_safe, and explanation.",
                        },
                        {"role": "user", "content": multi_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                content = response.choices[0].message.content.strip()
                data = json.loads(content)

                # Parse commands
                commands_data = data.get("commands", [])
                if not commands_data:
                    # Fallback: treat as single command
                    single_cmd = self.generate_command(query, model=model)
                    commands_data = [
                        (
                            single_cmd.to_dict()
                            if hasattr(single_cmd, "to_dict")
                            else {
                                "command": single_cmd.command,
                                "is_safe": single_cmd.is_safe,
                                "safety_level": single_cmd.safety_level.value,
                                "explanation": single_cmd.explanation,
                            }
                        )
                    ]

                commands = []
                for cmd_data in commands_data:
                    if isinstance(cmd_data, CommandResponse):
                        commands.append(cmd_data)
                        continue
                    if isinstance(cmd_data, str):
                        payload = {
                            "command": cmd_data,
                            "is_safe": False,
                            "safety_level": SafetyLevel.MODIFYING.value,
                        }
                    elif isinstance(cmd_data, dict):
                        payload = {
                            "command": cmd_data.get("command", ""),
                            "is_safe": cmd_data.get("is_safe", False),
                            "safety_level": cmd_data.get("safety_level"),
                            "explanation": cmd_data.get("explanation"),
                        }
                    else:
                        payload = {
                            "command": str(cmd_data),
                            "is_safe": False,
                            "safety_level": SafetyLevel.MODIFYING.value,
                        }
                    commands.append(self._build_command_response(payload))
                overall_safe = all(cmd.is_safe for cmd in commands)

                # Build combined command if needed
                combined = data.get("combined_command")
                if not combined:
                    exec_type = data.get("execution_type", "sequence")
                    if exec_type == "pipeline":
                        combined = " | ".join(cmd.command for cmd in commands)
                    elif exec_type == "sequence":
                        combined = " && ".join(cmd.command for cmd in commands)
                    elif exec_type == "parallel":
                        combined = " & ".join(cmd.command for cmd in commands)
                    else:
                        combined = " && ".join(cmd.command for cmd in commands)

                return MultiCommandResponse(
                    commands=commands,
                    execution_type=data.get("execution_type", "sequence"),
                    combined_command=combined,
                    overall_safe=overall_safe,
                    explanation=data.get("explanation"),
                )
        except Exception as e:
            console.print(f"[red]Error generating multi-command: {e}[/red]")
            # Fallback to single command
            single_cmd = self.generate_command(query, model=model)
            return MultiCommandResponse(
                commands=[single_cmd],
                execution_type="sequence",
                combined_command=single_cmd.command,
                overall_safe=single_cmd.is_safe,
            )

    def run(
        self,
        query: str,
        execute: bool = False,
        model: str | None = None,
        copy: bool = False,
        force: bool = False,
        refine: bool = False,
        alternatives: bool = False,
        edit: bool = False,
    ):
        """
        Generate and optionally execute a command.

        Args:
            query: Natural language query
            execute: Whether to execute the command
            model: OpenAI model to use
            copy: Whether to copy command to clipboard
            force: Whether to bypass safety warnings for modifying commands
            refine: Whether to enter refinement mode
            alternatives: Whether to show alternative commands
            edit: Whether to allow editing before execution
        """
        # Handle alternatives
        if alternatives:
            alt_commands = self.generate_alternatives(query, count=3, model=model)
            from rich.table import Table
            from rich.text import Text

            table = Table(title="Alternative Commands")
            table.add_column("#", style="cyan", width=3)
            table.add_column("Command", style="green", width=60)
            table.add_column("Safe", style="yellow", width=6)
            table.add_column("Explanation", style="dim", width=40)

            for idx, alt in enumerate(alt_commands, 1):
                safe_text = "✓" if alt.is_safe else "⚠"
                safe_style = "green" if alt.is_safe else "yellow"
                table.add_row(
                    str(idx),
                    alt.command,
                    Text(safe_text, style=safe_style),
                    alt.explanation or "",
                )

            console.print(table)
            return

        # Detect if query needs multi-command support
        multi_keywords = [
            " and ",
            " then ",
            " after ",
            " before ",
            " followed by ",
            " pipe ",
            " | ",
            " chain ",
        ]
        is_multi = (
            any(keyword in query.lower() for keyword in multi_keywords)
            or "list" in query.lower()
            and "count" in query.lower()
        )

        if is_multi and not refine and not alternatives:
            # Use multi-command generation
            multi_response = self.generate_multi_command(query, model=model)

            if len(multi_response.commands) > 1:
                # Display multi-command
                from rich.table import Table
                from rich.text import Text

                console.print(
                    Panel(
                        multi_response.combined_command
                        or " && ".join(cmd.command for cmd in multi_response.commands),
                        title=f"[bold]Multi-Command ({multi_response.execution_type})[/bold]",
                        border_style=(
                            "green" if multi_response.overall_safe else "yellow"
                        ),
                    )
                )

                if multi_response.explanation:
                    console.print(f"[dim]{multi_response.explanation}[/dim]")

                table = Table(title="Command Breakdown")
                table.add_column("#", style="cyan", width=3)
                table.add_column("Command", style="green", width=60)
                table.add_column("Safe", style="yellow", width=6)
                table.add_column("Explanation", style="dim", width=40)

                for idx, cmd in enumerate(multi_response.commands, 1):
                    safe_text = "✓" if cmd.is_safe else "⚠"
                    safe_style = "green" if cmd.is_safe else "yellow"
                    table.add_row(
                        str(idx),
                        cmd.command,
                        Text(safe_text, style=safe_style),
                        cmd.explanation or "",
                    )

                console.print(table)

                command = multi_response.combined_command or " && ".join(
                    cmd.command for cmd in multi_response.commands
                )
                command_response = CommandResponse(
                    command=command,
                    is_safe=multi_response.overall_safe,
                    safety_level=(
                        SafetyLevel.SAFE
                        if multi_response.overall_safe
                        else SafetyLevel.MODIFYING
                    ),
                    explanation=multi_response.explanation,
                )
            else:
                # Fall back to single command
                command_response = multi_response.commands[0]
                command = command_response.command
        else:
            # Generate single command with safety analysis
            command_response = self.generate_command(query, model=model)
            command = command_response.command

        # Handle refinement mode
        if refine:
            console.print("[bold cyan]Refinement Mode[/bold cyan]")
            console.print(f"[dim]Current command: {command}[/dim]\n")
            refinement = click.prompt(
                "How would you like to refine this command? (or 'done' to finish)"
            )
            if refinement.lower() != "done":
                command_response = self.refine_command(
                    query, refinement, original_command=command, model=model
                )
                command = command_response.command
                console.print(f"[green]Refined command: {command}[/green]\n")

        # Handle edit mode
        if edit and not execute:
            import os
            import tempfile

            # Create temp file with command
            with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
                f.write(f"#!/bin/bash\n{command}\n")
                temp_path = f.name

            try:
                # Open in editor
                editor = os.getenv("EDITOR", "nano")
                os.system(f"{editor} {temp_path}")

                # Read edited command
                with open(temp_path) as f:
                    lines = f.readlines()
                    # Skip shebang if present
                    if lines and lines[0].startswith("#!"):
                        edited_command = "".join(lines[1:]).strip()
                    else:
                        edited_command = "".join(lines).strip()

                if edited_command and edited_command != command:
                    command = edited_command
                    console.print(f"[green]Using edited command: {command}[/green]\n")
            finally:
                os.unlink(temp_path)

        # Determine panel style based on safety
        if command_response.is_safe:
            panel_style = "green"
            title = "[bold green]Generated Command (Safe - Read Only)[/bold green]"
        else:
            panel_style = "yellow"
            title = (
                "[bold yellow]Generated Command (⚠️  Will Modify System)[/bold yellow]"
            )

        # Display the command in a nice panel
        console.print(Panel(command, title=title, border_style=panel_style))

        # Show explanation if available
        if command_response.explanation:
            console.print(f"[dim]{command_response.explanation}[/dim]")

        # Show safety warning for modifying commands
        if not command_response.is_safe and not force:
            console.print(
                "\n[bold yellow]⚠️  Warning: This command will modify your system![/bold yellow]"
            )
            console.print(
                "[yellow]It may write files, change configuration, or alter system state.[/yellow]"
            )
            if execute:
                console.print(
                    "[yellow]Review the command above before it executes.[/yellow]\n"
                )
            else:
                console.print(
                    "[yellow]Review the command carefully before executing it.[/yellow]\n"
                )

        # Copy to clipboard if requested
        if copy:
            if copy_to_clipboard(command):
                console.print("[dim](Command copied to clipboard)[/dim]")
            else:
                console.print(
                    "[yellow]Warning: Could not copy to clipboard. Install xclip or xsel (e.g., 'sudo apt install xclip' or 'sudo apt install xsel').[/yellow]"
                )

        # Execute if requested
        if execute:
            # Additional safety check for modifying commands
            if not command_response.is_safe and not force:
                console.print(
                    "[bold red]⚠️  Safety Check Failed: This command will modify your system![/bold red]"
                )
                console.print(
                    "[red]Use --force flag to execute modifying commands.[/red]"
                )
                console.print(f"[dim]Command: {command}[/dim]")
                sys.exit(1)

            console.print(f"\n[bold yellow]Executing:[/bold yellow] {command}\n")
            return_code = None
            try:
                result = subprocess.run(command, shell=True, check=False)
                return_code = result.returncode
                # Save to history with execution info
                self.history_manager.add_entry(
                    query=query,
                    command=command,
                    is_safe=command_response.is_safe,
                    safety_level=command_response.safety_level,
                    explanation=command_response.explanation,
                    executed=True,
                    return_code=return_code,
                )
                # Exit with the command's return code
                sys.exit(result.returncode)
            except KeyboardInterrupt:
                console.print("\n[yellow]Command interrupted by user[/yellow]")
                # Save to history even if interrupted
                self.history_manager.add_entry(
                    query=query,
                    command=command,
                    is_safe=command_response.is_safe,
                    safety_level=command_response.safety_level,
                    explanation=command_response.explanation,
                    executed=True,
                    return_code=130,
                )
                sys.exit(130)
            except Exception as e:
                console.print(f"[red]Error executing command: {e}[/red]")
                # Save to history with error
                self.history_manager.add_entry(
                    query=query,
                    command=command,
                    is_safe=command_response.is_safe,
                    safety_level=command_response.safety_level,
                    explanation=command_response.explanation,
                    executed=True,
                    return_code=1,
                )
                sys.exit(1)
        else:
            # Save to history even if not executed
            self.history_manager.add_entry(
                query=query,
                command=command,
                is_safe=command_response.is_safe,
                safety_level=command_response.safety_level,
                explanation=command_response.explanation,
                executed=False,
            )

    def run_batch(self, queries_file: str, model: str | None = None):
        """
        Process multiple queries from a file (one per line).

        Args:
            queries_file: Path to file containing queries (one per line)
            model: OpenAI model to use
        """
        try:
            with open(queries_file) as f:
                queries = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]
        except FileNotFoundError:
            console.print(f"[red]Error: File '{queries_file}' not found.[/red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Error reading file: {e}[/red]")
            sys.exit(1)

        if not queries:
            console.print("[yellow]No queries found in file.[/yellow]")
            return

        console.print(f"[bold]Processing {len(queries)} queries...[/bold]\n")

        for idx, query in enumerate(queries, 1):
            console.print(f"[bold cyan]Query {idx}/{len(queries)}:[/bold cyan] {query}")
            try:
                self.run(query, execute=False, model=model)
                console.print()  # Blank line between queries
            except (Exception, SystemExit) as e:
                console.print(f"[red]Error processing query: {e}[/red]\n")
                continue
