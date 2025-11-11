#!/usr/bin/env python3
"""
CLI-NLP: Natural Language to Shell Command Converter
Converts natural language requests into shell commands using OpenAI.
"""

import json
import os
import shutil
import sys
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

# Initialize Typer app and console
app = typer.Typer(
    name="nlp",
    help="Convert natural language to shell commands using OpenAI",
    add_completion=False,
    rich_markup_mode="rich",  # Use Rich but we'll handle help manually
)
console = Console()

# Monkey-patch to avoid the make_metavar bug in Typer 0.12.5
def _safe_get_help(ctx):
    """Safe help that avoids the make_metavar bug."""
    try:
        return ctx.get_help()
    except (TypeError, AttributeError) as e:
        if "make_metavar" in str(e) or "Parameter" in str(e):
            # Return a simple help message
            return """Usage: nlp [OPTIONS] <query> | nlp <command> [ARGS]

Convert natural language to shell commands using OpenAI

Arguments:
  query    Natural language description of the command you want

Options:
  -e, --execute          Execute the generated command automatically
  -m, --model TEXT       OpenAI model to use
  -c, --copy             Copy command to clipboard
  -h, --help             Show this message and exit

Commands:
  init-config            Create a default config file template

Examples:
  nlp "list all python files"
  nlp "show disk usage" --execute
  nlp init-config
"""
        raise


def get_config_path() -> Path:
    """Get the path to the config file."""
    # Try XDG config directory first, then fallback to ~/.config
    xdg_config = os.getenv("XDG_CONFIG_HOME")
    if xdg_config:
        config_dir = Path(xdg_config) / "cli-nlp"
    else:
        config_dir = Path.home() / ".config" / "cli-nlp"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.json"


def load_config() -> dict:
    """Load configuration from JSON file."""
    config_path = get_config_path()
    
    if not config_path.exists():
        return {}
    
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error: Invalid JSON in config file: {e}[/red]")
        console.print(f"Config file location: {config_path}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error reading config file: {e}[/red]")
        raise typer.Exit(1)


def create_default_config() -> bool:
    """Create a default config file with template."""
    config_path = get_config_path()
    
    if config_path.exists():
        console.print(f"[yellow]Config file already exists at: {config_path}[/yellow]")
        return False
    
    default_config = {
        "openai_api_key": "",
        "default_model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 200
    }
    
    try:
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        # Set restrictive permissions (read/write for user only)
        os.chmod(config_path, 0o600)
        
        console.print(f"[green]Created config file at: {config_path}[/green]")
        console.print("[yellow]Please edit it and add your OpenAI API key.[/yellow]")
        return True
    except Exception as e:
        console.print(f"[red]Error creating config file: {e}[/red]")
        return False


def get_openai_client():
    """Initialize OpenAI client with API key from config or environment."""
    try:
        from openai import OpenAI
    except ImportError:
        console.print("[red]Error: OpenAI package not installed.[/red]")
        console.print("[yellow]Please install it with: poetry install[/yellow]")
        raise typer.Exit(1)
    
    config = load_config()
    
    # Try config file first, then environment variable
    api_key = config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        config_path = get_config_path()
        console.print("[red]Error: OpenAI API key not found.[/red]")
        console.print("Please either:")
        console.print(f"  1. Add 'openai_api_key' to config file: {config_path}")
        console.print("  2. Set OPENAI_API_KEY environment variable")
        console.print("  3. Run: nlp init-config")
        raise typer.Exit(1)
    
    return OpenAI(api_key=api_key)


def generate_command(
    client,
    query: str,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Generate a shell command from natural language query.
    
    Args:
        client: OpenAI client instance
        query: Natural language query
        model: OpenAI model to use (defaults to config or gpt-4o-mini)
        temperature: Temperature for generation (defaults to config or 0.3)
        max_tokens: Max tokens for response (defaults to config or 200)
    
    Returns:
        Generated shell command string
    """
    config = load_config()
    
    # Use provided values or fall back to config or defaults
    model = model or config.get("default_model", "gpt-4o-mini")
    temperature = temperature if temperature is not None else config.get("temperature", 0.3)
    max_tokens = max_tokens if max_tokens is not None else config.get("max_tokens", 200)
    
    system_prompt = """You are a helpful assistant that converts natural language requests into shell commands.
    
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

    try:
        with console.status("[bold green]Generating command..."):
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
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


def check_clipboard_available() -> bool:
    """Check if clipboard tools (xclip or xsel) are available."""
    return shutil.which("xclip") is not None or shutil.which("xsel") is not None


def copy_to_clipboard(command: str) -> bool:
    """Copy command to clipboard. Returns True if successful."""
    # Check if clipboard tools are available first
    if not check_clipboard_available():
        return False
    
    try:
        # Try xclip first (most common on Linux)
        subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=command.encode(),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            # Fallback to xsel
            subprocess.run(
                ["xsel", "--clipboard", "--input"],
                input=command.encode(),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """Convert natural language to shell commands using OpenAI."""
    # If a subcommand was invoked, let it handle it
    if ctx.invoked_subcommand is not None:
        return
    
    # Handle help case - check sys.argv before Typer tries to parse
    import sys
    if '--help' in sys.argv or '-h' in sys.argv:
        # Use safe help to avoid the make_metavar bug
        try:
            help_text = _safe_get_help(ctx)
            console.print(help_text)
        except:
            # Fallback to simple help
            console.print("""
[bold]CLI-NLP: Natural Language to Shell Command Converter[/bold]

[bold]Usage:[/bold]
    nlp [OPTIONS] <query>
    nlp <command> [ARGS]

[bold]Arguments:[/bold]
    query    Natural language description of the command you want

[bold]Options:[/bold]
    -e, --execute          Execute the generated command automatically
    -m, --model TEXT       OpenAI model to use (default: from config or gpt-4o-mini)
    -c, --copy             Copy command to clipboard (requires xclip or xsel)
    -h, --help             Show this message and exit

[bold]Commands:[/bold]
    init-config            Create a default config file template

[bold]Examples:[/bold]
    nlp "list all python files in current directory"
    nlp "show disk usage" --execute
    nlp "find files modified in last 24 hours" --model gpt-4o
    nlp init-config
""")
        raise typer.Exit()
    
    # Parse arguments manually
    args = sys.argv[1:]
    query_parts = []
    i = 0
    while i < len(args):
        if args[i] in ['-e', '--execute', '-m', '--model', '-c', '--copy']:
            if args[i] in ['-m', '--model'] and i + 1 < len(args):
                i += 2
            else:
                i += 1
        elif not args[i].startswith('-'):
            query_parts.append(args[i])
            i += 1
        else:
            i += 1
    
    if not query_parts:
        try:
            help_text = _safe_get_help(ctx)
            console.print(help_text)
        except:
            console.print("[red]Error: Query is required. Use --help for usage information.[/red]")
        raise typer.Exit(1)
    
    query_str = " ".join(query_parts)
    
    # Parse options manually
    execute = '-e' in args or '--execute' in args
    copy = '-c' in args or '--copy' in args
    model = None
    if '-m' in args:
        idx = args.index('-m')
        if idx + 1 < len(args):
            model = args[idx + 1]
    elif '--model' in args:
        idx = args.index('--model')
        if idx + 1 < len(args):
            model = args[idx + 1]
    
    # Call the run function logic
    _run_command(query_str, execute=execute, model=model, copy=copy)


def _run_command(
    query_str: str,
    execute: bool = False,
    model: Optional[str] = None,
    copy: bool = False,
):
    """Internal function to run the command generation logic."""
    
    # Initialize OpenAI client
    client = get_openai_client()
    
    # Generate command (model will use config default if not specified)
    command = generate_command(client, query_str, model=model)
    
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


@app.command(name="init-config")
def init_config_cmd():
    """Create a default config file template."""
    create_default_config()


# Set the default command
def cli():
    """CLI entry point."""
    import sys
    
    # Known subcommands
    known_commands = ['init-config']
    
    # Check for help flag before Typer tries to parse (which triggers the bug)
    if '--help' in sys.argv or '-h' in sys.argv:
        console.print("""
[bold]CLI-NLP: Natural Language to Shell Command Converter[/bold]

[bold]Usage:[/bold]
    nlp [OPTIONS] <query>
    nlp <command> [ARGS]

[bold]Arguments:[/bold]
    query    Natural language description of the command you want

[bold]Options:[/bold]
    -e, --execute          Execute the generated command automatically
    -m, --model TEXT       OpenAI model to use (default: from config or gpt-4o-mini)
    -c, --copy             Copy command to clipboard (requires xclip or xsel)
    -h, --help             Show this message and exit

[bold]Commands:[/bold]
    init-config            Create a default config file template

[bold]Examples:[/bold]
    nlp "list all python files in current directory"
    nlp "show disk usage" --execute
    nlp "find files modified in last 24 hours" --model gpt-4o
    nlp init-config
""")
        sys.exit(0)
    
    # Pre-process arguments: if first non-option arg is not a known command,
    # treat everything as a query and call the internal function directly
    args = sys.argv[1:]
    first_non_option = None
    i = 0
    while i < len(args):
        if args[i] in ['-e', '--execute', '-c', '--copy', '-h', '--help']:
            i += 1
        elif args[i] in ['-m', '--model']:
            i += 2  # Skip option and value
        elif not args[i].startswith('-'):
            first_non_option = args[i]
            break
        else:
            i += 1
    
    # If first non-option is not a known command, treat everything as query
    if first_non_option and first_non_option not in known_commands:
        # Parse as query directly
        query_parts = []
        execute = False
        copy = False
        model = None
        
        i = 0
        while i < len(args):
            if args[i] in ['-e', '--execute']:
                execute = True
                i += 1
            elif args[i] in ['-c', '--copy']:
                copy = True
                i += 1
            elif args[i] in ['-m', '--model']:
                if i + 1 < len(args):
                    model = args[i + 1]
                    i += 2
                else:
                    i += 1
            elif not args[i].startswith('-'):
                query_parts.append(args[i])
                i += 1
            else:
                i += 1
        
        if query_parts:
            _run_command(" ".join(query_parts), execute=execute, model=model, copy=copy)
            return
    
    # Otherwise, let Typer handle it (for known commands)
    try:
        app()
    except (TypeError, AttributeError) as e:
        error_str = str(e)
        if "make_metavar" in error_str or "Parameter" in error_str:
            # Workaround for Typer 0.12.5 bug - show custom help
            console.print("""
[bold]CLI-NLP: Natural Language to Shell Command Converter[/bold]

[bold]Usage:[/bold]
    nlp [OPTIONS] <query>
    nlp <command> [ARGS]

[bold]Arguments:[/bold]
    query    Natural language description of the command you want

[bold]Options:[/bold]
    -e, --execute          Execute the generated command automatically
    -m, --model TEXT       OpenAI model to use (default: from config or gpt-4o-mini)
    -c, --copy             Copy command to clipboard (requires xclip or xsel)
    -h, --help             Show this message and exit

[bold]Commands:[/bold]
    init-config            Create a default config file template

[bold]Examples:[/bold]
    nlp "list all python files in current directory"
    nlp "show disk usage" --execute
    nlp "find files modified in last 24 hours" --model gpt-4o
    nlp init-config
""")
            sys.exit(0)
        else:
            raise
    except typer.Exit:
        raise
    except SystemExit:
        raise
    except Exception as e:
        # If it's a "No such command" error, treat it as a query
        if "No such command" in str(e):
            # Parse everything as query
            args = sys.argv[1:]
            query_parts = []
            execute = False
            copy = False
            model = None
            
            i = 0
            while i < len(args):
                if args[i] in ['-e', '--execute']:
                    execute = True
                    i += 1
                elif args[i] in ['-c', '--copy']:
                    copy = True
                    i += 1
                elif args[i] in ['-m', '--model']:
                    if i + 1 < len(args):
                        model = args[i + 1]
                        i += 2
                    else:
                        i += 1
                elif not args[i].startswith('-'):
                    query_parts.append(args[i])
                    i += 1
                else:
                    i += 1
            
            if query_parts:
                _run_command(" ".join(query_parts), execute=execute, model=model, copy=copy)
                return
        raise


if __name__ == "__main__":
    cli()
