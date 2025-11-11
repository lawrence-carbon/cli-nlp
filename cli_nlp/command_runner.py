"""Command generation and execution for CLI-NLP."""

import json
import subprocess
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from cli_nlp.config_manager import ConfigManager
from cli_nlp.models import CommandResponse, SafetyLevel
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
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self._client = None
    
    @property
    def client(self):
        """Lazy-load OpenAI client."""
        if self._client is None:
            self._client = self._get_openai_client()
        return self._client
    
    def _get_openai_client(self):
        """Initialize OpenAI client with API key from config or environment."""
        try:
            from openai import OpenAI
        except ImportError:
            console.print("[red]Error: OpenAI package not installed.[/red]")
            console.print("[yellow]Please install it with: poetry install[/yellow]")
            raise typer.Exit(1)
        
        api_key = self.config_manager.get_api_key()
        
        if not api_key:
            config_path = self.config_manager.config_path
            console.print("[red]Error: OpenAI API key not found.[/red]")
            console.print("Please either:")
            console.print(f"  1. Add 'openai_api_key' to config file: {config_path}")
            console.print("  2. Set OPENAI_API_KEY environment variable")
            console.print("  3. Run: qtc init-config")
            raise typer.Exit(1)
        
        return OpenAI(api_key=api_key)
    
    def generate_command(
        self,
        query: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> CommandResponse:
        """
        Generate a shell command from natural language query with safety analysis.
        
        Args:
            query: Natural language query
            model: OpenAI model to use (defaults to config or gpt-4o-mini)
            temperature: Temperature for generation (defaults to config or 0.3)
            max_tokens: Max tokens for response (defaults to config or 200)
        
        Returns:
            CommandResponse object containing command and safety information
        """
        # Use provided values or fall back to config or defaults
        model = model or self.config_manager.get("default_model", "gpt-4o-mini")
        temperature = temperature if temperature is not None else self.config_manager.get("temperature", 0.3)
        max_tokens = max_tokens if max_tokens is not None else self.config_manager.get("max_tokens", 200)
        
        try:
            with console.status("[bold green]Generating command..."):
                # Try structured output with Pydantic (OpenAI SDK 1.0+)
                try:
                    response = self.client.beta.chat.completions.parse(
                        model=model,
                        messages=[
                            {"role": "system", "content": self.SYSTEM_PROMPT},
                            {"role": "user", "content": query}
                        ],
                        response_format=CommandResponse,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    
                    command_response = response.choices[0].message.parsed
                    
                    # Ensure safety_level is set based on is_safe
                    if command_response.safety_level is None:
                        command_response.safety_level = SafetyLevel.SAFE if command_response.is_safe else SafetyLevel.MODIFYING
                    
                    return command_response
                except (AttributeError, TypeError):
                    # Fallback: Use JSON mode for models that don't support structured output
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "system",
                                "content": self.SYSTEM_PROMPT + "\n\nYou must respond with a valid JSON object matching this schema: {\"command\": \"string\", \"is_safe\": boolean, \"safety_level\": \"safe\" or \"modifying\", \"explanation\": \"string (optional)\"}"
                            },
                            {"role": "user", "content": query}
                        ],
                        response_format={"type": "json_object"},
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    
                    content = response.choices[0].message.content.strip()
                    data = json.loads(content)
                    
                    # Create CommandResponse from JSON
                    command_response = CommandResponse(
                        command=data.get("command", ""),
                        is_safe=data.get("is_safe", False),
                        safety_level=SafetyLevel(data.get("safety_level", "modifying")),
                        explanation=data.get("explanation")
                    )
                    
                    return command_response
        
        except Exception as e:
            console.print(f"[red]Error generating command: {e}[/red]")
            raise typer.Exit(1)
    
    def run(
        self,
        query: str,
        execute: bool = False,
        model: Optional[str] = None,
        copy: bool = False,
        force: bool = False,
    ):
        """
        Generate and optionally execute a command.
        
        Args:
            query: Natural language query
            execute: Whether to execute the command
            model: OpenAI model to use
            copy: Whether to copy command to clipboard
            force: Whether to bypass safety warnings for modifying commands
        """
        # Generate command with safety analysis
        command_response = self.generate_command(query, model=model)
        command = command_response.command
        
        # Determine panel style based on safety
        if command_response.is_safe:
            panel_style = "green"
            title = "[bold green]Generated Command (Safe - Read Only)[/bold green]"
        else:
            panel_style = "yellow"
            title = "[bold yellow]Generated Command (⚠️  Will Modify System)[/bold yellow]"
        
        # Display the command in a nice panel
        console.print(Panel(command, title=title, border_style=panel_style))
        
        # Show explanation if available
        if command_response.explanation:
            console.print(f"[dim]{command_response.explanation}[/dim]")
        
        # Show safety warning for modifying commands
        if not command_response.is_safe and not force:
            console.print("\n[bold yellow]⚠️  Warning: This command will modify your system![/bold yellow]")
            console.print("[yellow]It may write files, change configuration, or alter system state.[/yellow]")
            if execute:
                console.print("[yellow]Review the command above before it executes.[/yellow]\n")
            else:
                console.print("[yellow]Review the command carefully before executing it.[/yellow]\n")
        
        # Copy to clipboard if requested
        if copy:
            if copy_to_clipboard(command):
                console.print("[dim](Command copied to clipboard)[/dim]")
            else:
                console.print("[yellow]Warning: Could not copy to clipboard. Install xclip or xsel (e.g., 'sudo apt install xclip' or 'sudo apt install xsel').[/yellow]")
        
        # Execute if requested
        if execute:
            # Additional safety check for modifying commands
            if not command_response.is_safe and not force:
                console.print("[bold red]⚠️  Safety Check Failed: This command will modify your system![/bold red]")
                console.print("[red]Use --force flag to execute modifying commands.[/red]")
                console.print(f"[dim]Command: {command}[/dim]")
                sys.exit(1)
            
            console.print(f"\n[bold yellow]Executing:[/bold yellow] {command}\n")
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    check=False
                )
                # Exit with the command's return code
                sys.exit(result.returncode)
            except KeyboardInterrupt:
                console.print("\n[yellow]Command interrupted by user[/yellow]")
                sys.exit(130)
            except Exception as e:
                console.print(f"[red]Error executing command: {e}[/red]")
                sys.exit(1)

