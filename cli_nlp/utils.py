"""Utility functions for CLI-NLP."""

from rich.console import Console

console = Console()

# Help text template (single source of truth)
HELP_TEXT = """
[bold]QTC: Query to Command - Natural Language to Shell Command Converter[/bold]

[bold]Usage:[/bold]
    qtc [OPTIONS] <query>
    qtc [OPTIONS]              (interactive mode with tab completion)
    qtc <command> [ARGS]

[bold]Arguments:[/bold]
    query    Natural language description of the command you want
            (if omitted, enters interactive mode with tab completion)

[bold]Options:[/bold]
    -e, --execute          Execute the generated command automatically
    -f, --force            Bypass safety check for modifying commands (use with caution)
    -m, --model TEXT       OpenAI model to use (default: from config or gpt-4o-mini)
    -c, --copy             Copy command to clipboard (requires xclip or xsel)
    -h, --help             Show this message and exit

[bold]Commands:[/bold]
    init-config            Create a default config file template

[bold]Examples:[/bold]
    qtc "list all python files in current directory"
    qtc "show disk usage" --execute
    qtc "find files modified in last 24 hours" --model gpt-4o
    qtc init-config
"""


def show_help():
    """Display the help text."""
    console.print(HELP_TEXT)


def check_clipboard_available() -> bool:
    """Check if clipboard tools (xclip or xsel) are available."""
    import shutil
    return shutil.which("xclip") is not None or shutil.which("xsel") is not None


def copy_to_clipboard(command: str) -> bool:
    """Copy command to clipboard. Returns True if successful."""
    import subprocess
    
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

