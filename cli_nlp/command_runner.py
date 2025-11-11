"""Command generation and execution for CLI-NLP."""

import os
import subprocess
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from cli_nlp.config_manager import ConfigManager
from cli_nlp.utils import console, copy_to_clipboard


class CommandRunner:
    """Handles command generation and execution."""
    
    SYSTEM_PROMPT = """You are a helpful assistant that converts natural language requests into shell commands.
    
Rules:
1. Only output the shell command itself, nothing else
2. Do not include explanations, markdown code blocks, or any other text
3. Use standard Unix/Linux commands (bash, zsh compatible)
4. If the request is ambiguous or potentially dangerous, still provide the command but make it safe
5. For file operations, use relative paths when possible
6. Prefer common, portable commands over system-specific ones

Examples:
- "list all python files" -> find . -name "*.py"
- "show disk usage" -> df -h
- "find files larger than 100MB" -> find . -type f -size +100M
- "kill process on port 3000" -> lsof -ti:3000 | xargs kill -9
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
            console.print("  3. Run: nlp init-config")
            raise typer.Exit(1)
        
        return OpenAI(api_key=api_key)
    
    def generate_command(
        self,
        query: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a shell command from natural language query.
        
        Args:
            query: Natural language query
            model: OpenAI model to use (defaults to config or gpt-4o-mini)
            temperature: Temperature for generation (defaults to config or 0.3)
            max_tokens: Max tokens for response (defaults to config or 200)
        
        Returns:
            Generated shell command string
        """
        # Use provided values or fall back to config or defaults
        model = model or self.config_manager.get("default_model", "gpt-4o-mini")
        temperature = temperature if temperature is not None else self.config_manager.get("temperature", 0.3)
        max_tokens = max_tokens if max_tokens is not None else self.config_manager.get("max_tokens", 200)
        
        try:
            with console.status("[bold green]Generating command..."):
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": query}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            
            command = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if command.startswith("```"):
                lines = command.split("\n")
                command = "\n".join(lines[1:-1]) if len(lines) > 2 else command
                command = command.strip()
            
            return command
        
        except Exception as e:
            console.print(f"[red]Error generating command: {e}[/red]")
            raise typer.Exit(1)
    
    def run(
        self,
        query: str,
        execute: bool = False,
        model: Optional[str] = None,
        copy: bool = False,
    ):
        """
        Generate and optionally execute a command.
        
        Args:
            query: Natural language query
            execute: Whether to execute the command
            model: OpenAI model to use
            copy: Whether to copy command to clipboard
        """
        # Generate command
        command = self.generate_command(query, model=model)
        
        # Display the command in a nice panel
        console.print(Panel(command, title="[bold green]Generated Command[/bold green]", border_style="green"))
        
        # Copy to clipboard if requested
        if copy:
            if copy_to_clipboard(command):
                console.print("[dim](Command copied to clipboard)[/dim]")
            else:
                console.print("[yellow]Warning: Could not copy to clipboard. Install xclip or xsel (e.g., 'sudo apt install xclip' or 'sudo apt install xsel').[/yellow]")
        
        # Execute if requested
        if execute:
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

