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
    -r, --refine           Enter refinement mode to improve the command
    -a, --alternatives     Show alternative command options
    --edit                 Edit command in your default editor before execution
    -h, --help             Show this message and exit

[bold]Commands:[/bold]
    init-config            Create a default config file template
    batch <file>           Process multiple queries from a file (one per line)
    
    history                 Manage command history
        list                List recent history entries
        search <query>      Search history by query or command
        show <id>           Show detailed information about a history entry
        execute <id>        Re-execute a command from history
        export              Export history to JSON or CSV
        clear               Clear all history entries
    
    cache                   Manage command cache
        stats               Show cache statistics (hits, misses, hit rate)
        clear               Clear all cached commands
    
    template                Manage command templates/aliases
        save <name> <cmd>   Save a command as a template
        list                List all saved templates
        use <name>          Use a saved template
        delete <name>       Delete a template

[bold]Examples:[/bold]
    # Basic usage
    qtc "list all python files in current directory"
    qtc "show disk usage" --execute
    qtc "find files modified in last 24 hours" --model gpt-4o
    
    # Refinement and alternatives
    qtc "find python files" --refine
    qtc "list files" --alternatives
    
    # Multi-command support (automatic detection)
    qtc "list files and then count lines"
    qtc "find files and grep for pattern"
    
    # History management
    qtc history list
    qtc history search "python"
    qtc history execute 5
    
    # Templates
    qtc template save "clean-pyc" "find . -name '*.pyc' -delete"
    qtc template use "clean-pyc" --execute
    
    # Batch processing
    qtc batch queries.txt
    
    # Configuration
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

