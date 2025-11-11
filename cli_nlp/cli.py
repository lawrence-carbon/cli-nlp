"""Main CLI interface for CLI-NLP."""

import os
import sys
from typing import List, Optional, Tuple

import typer

from cli_nlp.command_runner import CommandRunner
from cli_nlp.completer import QueryCompleter
from cli_nlp.config_manager import ConfigManager
from cli_nlp.utils import console, show_help

# Initialize Typer app
app = typer.Typer(
    name="qtc",
    help="Convert natural language to shell commands using OpenAI",
    add_completion=False,
    rich_markup_mode="rich",
)

# Initialize managers
config_manager = ConfigManager()
command_runner = CommandRunner(config_manager)


def parse_arguments(args: List[str]) -> Tuple[List[str], bool, bool, Optional[str], bool]:
    """
    Parse command line arguments.
    
    Returns:
        Tuple of (query_parts, execute, copy, model, force)
    """
    query_parts = []
    execute = False
    copy = False
    model = None
    force = False
    
    i = 0
    while i < len(args):
        if args[i] in ['-e', '--execute']:
            execute = True
            i += 1
        elif args[i] in ['-c', '--copy']:
            copy = True
            i += 1
        elif args[i] in ['-f', '--force']:
            force = True
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
    
    return query_parts, execute, copy, model, force


def _interactive_query() -> str:
    """Interactive query input with tab completion using prompt_toolkit."""
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
        from prompt_toolkit.key_binding import KeyBindings
        
        # Setup history file
        history_file = os.path.expanduser("~/.cli_nlp_history")
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        
        # Create key bindings for better UX
        kb = KeyBindings()
        
        # Create session with history and completion
        session = PromptSession(
            history=FileHistory(history_file),
            completer=QueryCompleter(),
            complete_while_typing=True,
            auto_suggest=AutoSuggestFromHistory(),
            enable_open_in_editor=True,
            key_bindings=kb,
        )
        
        query = session.prompt("Query: ")
        return query.strip()
    except ImportError:
        # Fallback if prompt_toolkit is not available
        console.print("[yellow]Warning: prompt_toolkit not available. Install it with: poetry install[/yellow]")
        try:
            query = input("Query: ")
            return query.strip()
        except (EOFError, KeyboardInterrupt):
            return ""
    except (EOFError, KeyboardInterrupt):
        return ""


def find_first_non_option(args: List[str]) -> Optional[str]:
    """Find the first non-option argument."""
    i = 0
    while i < len(args):
        if args[i] in ['-e', '--execute', '-c', '--copy', '-f', '--force', '-h', '--help']:
            i += 1
        elif args[i] in ['-m', '--model']:
            i += 2  # Skip option and value
        elif not args[i].startswith('-'):
            return args[i]
        else:
            i += 1
    return None


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """Convert natural language to shell commands using OpenAI."""
    # If a subcommand was invoked, let it handle it
    if ctx.invoked_subcommand is not None:
        return
    
    # Handle help case
    if '--help' in sys.argv or '-h' in sys.argv:
        show_help()
        raise typer.Exit()
    
    # Parse arguments manually
    args = sys.argv[1:]
    query_parts, execute, copy, model, force = parse_arguments(args)
    
    if not query_parts:
        # Enter interactive mode with tab completion
        query_str = _interactive_query()
        if not query_str:
            console.print("[yellow]No query provided. Exiting.[/yellow]")
            raise typer.Exit(0)
    else:
        query_str = " ".join(query_parts)
    
    command_runner.run(query_str, execute=execute, model=model, copy=copy, force=force)


@app.command(name="init-config")
def init_config_cmd():
    """Create a default config file template."""
    config_manager.create_default()


def cli():
    """CLI entry point."""
    # Known subcommands
    known_commands = ['init-config']
    
    # Check for help flag before Typer tries to parse (which triggers the bug)
    if '--help' in sys.argv or '-h' in sys.argv:
        show_help()
        sys.exit(0)
    
    # Pre-process arguments: if first non-option arg is not a known command,
    # treat everything as a query and call the runner directly
    args = sys.argv[1:]
    first_non_option = find_first_non_option(args)
    
    # If first non-option is not a known command, treat everything as query
    if first_non_option and first_non_option not in known_commands:
        query_parts, execute, copy, model, force = parse_arguments(args)
        if query_parts:
            command_runner.run(" ".join(query_parts), execute=execute, model=model, copy=copy, force=force)
            return
    
    # If no query provided and no known command, enter interactive mode
    if not first_non_option:
        query_parts, execute, copy, model, force = parse_arguments(args)
        if not query_parts:
            # Interactive mode
            query_str = _interactive_query()
            if query_str:
                command_runner.run(query_str, execute=execute, model=model, copy=copy, force=force)
            return
    
    # Otherwise, let Typer handle it (for known commands)
    try:
        app()
    except (TypeError, AttributeError) as e:
        error_str = str(e)
        if "make_metavar" in error_str or "Parameter" in error_str:
            # Workaround for Typer 0.12.5 bug - show custom help
            show_help()
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
            query_parts, execute, copy, model, force = parse_arguments(args)
            if query_parts:
                command_runner.run(" ".join(query_parts), execute=execute, model=model, copy=copy, force=force)
                return
        raise


if __name__ == "__main__":
    cli()

