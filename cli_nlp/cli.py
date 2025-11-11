"""Main CLI interface for CLI-NLP."""

import os
import sys
from typing import List, Optional, Tuple

import typer

from cli_nlp.cache_manager import CacheManager
from cli_nlp.command_runner import CommandRunner
from cli_nlp.completer import QueryCompleter
from cli_nlp.config_manager import ConfigManager
from cli_nlp.context_manager import ContextManager
from cli_nlp.history_manager import HistoryManager
from cli_nlp.template_manager import TemplateManager
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
history_manager = HistoryManager()
cache_manager = CacheManager(
    ttl_seconds=config_manager.get("cache_ttl_seconds", 86400)
)
context_manager = ContextManager()
template_manager = TemplateManager()
command_runner = CommandRunner(config_manager, history_manager, cache_manager, context_manager)


def parse_arguments(args: List[str]) -> Tuple[List[str], bool, bool, Optional[str], bool, bool, bool, bool]:
    """
    Parse command line arguments.
    
    Returns:
        Tuple of (query_parts, execute, copy, model, force, refine, alternatives, edit)
    """
    query_parts = []
    execute = False
    copy = False
    model = None
    force = False
    refine = False
    alternatives = False
    edit = False
    
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
        elif args[i] in ['-r', '--refine']:
            refine = True
            i += 1
        elif args[i] in ['-a', '--alternatives']:
            alternatives = True
            i += 1
        elif args[i] in ['--edit']:
            edit = True
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
    
    return query_parts, execute, copy, model, force, refine, alternatives, edit


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
        if args[i] in ['-e', '--execute', '-c', '--copy', '-f', '--force', '-r', '--refine', '-a', '--alternatives', '--edit', '-h', '--help']:
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
    query_parts, execute, copy, model, force, refine, alternatives, edit = parse_arguments(args)
    
    if not query_parts:
        # Enter interactive mode with tab completion
        query_str = _interactive_query()
        if not query_str:
            console.print("[yellow]No query provided. Exiting.[/yellow]")
            raise typer.Exit(0)
    else:
        query_str = " ".join(query_parts)
    
    command_runner.run(
        query_str,
        execute=execute,
        model=model,
        copy=copy,
        force=force,
        refine=refine,
        alternatives=alternatives,
        edit=edit,
    )


@app.command(name="init-config")
def init_config_cmd():
    """Create a default config file template."""
    config_manager.create_default()


# History subcommand group
history_app = typer.Typer(name="history", help="Manage command history")
app.add_typer(history_app)


@history_app.command(name="list")
def history_list(limit: int = typer.Option(20, "--limit", "-n", help="Number of entries to show")):
    """List recent history entries."""
    entries = history_manager.get_all(limit=limit)
    
    if not entries:
        console.print("[yellow]No history entries found.[/yellow]")
        return
    
    from rich.table import Table
    from rich.text import Text
    
    table = Table(title=f"Command History (showing {len(entries)} entries)")
    table.add_column("ID", style="cyan", width=4)
    table.add_column("Timestamp", style="dim", width=20)
    table.add_column("Query", style="white", width=40)
    table.add_column("Command", style="green", width=50)
    table.add_column("Safe", style="yellow", width=6)
    table.add_column("Executed", style="blue", width=9)
    
    for idx, entry in enumerate(entries):
        safe_text = "✓" if entry.is_safe else "⚠"
        safe_style = "green" if entry.is_safe else "yellow"
        executed_text = "✓" if entry.executed else "-"
        executed_style = "green" if entry.executed and entry.return_code == 0 else "red" if entry.executed else "dim"
        
        table.add_row(
            str(idx),
            entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            entry.query[:37] + "..." if len(entry.query) > 40 else entry.query,
            entry.command[:47] + "..." if len(entry.command) > 50 else entry.command,
            Text(safe_text, style=safe_style),
            Text(executed_text, style=executed_style),
        )
    
    console.print(table)


@history_app.command(name="search")
def history_search(
    query: str = typer.Argument(..., help="Search term"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of results to show"),
):
    """Search history by query or command."""
    results = history_manager.search(query)
    
    if not results:
        console.print(f"[yellow]No history entries found matching '{query}'.[/yellow]")
        return
    
    if limit:
        results = results[:limit]
    
    from rich.table import Table
    from rich.text import Text
    
    table = Table(title=f"Search Results for '{query}' ({len(results)} found)")
    table.add_column("ID", style="cyan", width=4)
    table.add_column("Timestamp", style="dim", width=20)
    table.add_column("Query", style="white", width=40)
    table.add_column("Command", style="green", width=50)
    
    # Find reverse indices for display
    all_entries = history_manager.get_all()
    entry_map = {id(entry): idx for idx, entry in enumerate(all_entries)}
    
    for entry in results:
        reverse_idx = entry_map.get(id(entry), 0)
        table.add_row(
            str(reverse_idx),
            entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            entry.query[:37] + "..." if len(entry.query) > 40 else entry.query,
            entry.command[:47] + "..." if len(entry.command) > 50 else entry.command,
        )
    
    console.print(table)


@history_app.command(name="show")
def history_show(entry_id: int = typer.Argument(..., help="History entry ID")):
    """Show detailed information about a history entry."""
    entry = history_manager.get_by_id(entry_id)
    
    if not entry:
        console.print(f"[red]History entry {entry_id} not found.[/red]")
        raise typer.Exit(1)
    
    from rich.panel import Panel
    from rich.text import Text
    
    console.print(Panel(
        f"[bold]Query:[/bold] {entry.query}\n"
        f"[bold]Command:[/bold] {entry.command}\n"
        f"[bold]Safe:[/bold] {'Yes' if entry.is_safe else 'No'} ({entry.safety_level.value})\n"
        f"[bold]Executed:[/bold] {'Yes' if entry.executed else 'No'}\n"
        f"[bold]Return Code:[/bold] {entry.return_code if entry.return_code is not None else 'N/A'}\n"
        f"[bold]Timestamp:[/bold] {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"[bold]Explanation:[/bold] {entry.explanation or 'N/A'}",
        title=f"History Entry #{entry_id}",
        border_style="green" if entry.is_safe else "yellow"
    ))


@history_app.command(name="execute")
def history_execute(
    entry_id: int = typer.Argument(..., help="History entry ID to execute"),
    force: bool = typer.Option(False, "--force", "-f", help="Bypass safety check"),
):
    """Re-execute a command from history."""
    entry = history_manager.get_by_id(entry_id)
    
    if not entry:
        console.print(f"[red]History entry {entry_id} not found.[/red]")
        raise typer.Exit(1)
    
    console.print(f"[bold]Re-executing command from history entry #{entry_id}:[/bold]")
    console.print(f"[dim]Original query: {entry.query}[/dim]\n")
    
    # Use the command runner to execute
    command_runner.run(
        entry.query,
        execute=True,
        force=force or entry.is_safe,  # Auto-force if safe
    )


@history_app.command(name="export")
def history_export(
    output: str = typer.Option("history.json", "--output", "-o", help="Output file path"),
    format: str = typer.Option("json", "--format", "-f", help="Export format (json or csv)"),
):
    """Export history to a file."""
    if format not in ["json", "csv"]:
        console.print("[red]Format must be 'json' or 'csv'.[/red]")
        raise typer.Exit(1)
    
    try:
        content = history_manager.export(format=format)
        with open(output, 'w') as f:
            f.write(content)
        console.print(f"[green]History exported to {output} ({format} format)[/green]")
    except Exception as e:
        console.print(f"[red]Error exporting history: {e}[/red]")
        raise typer.Exit(1)


@history_app.command(name="clear")
def history_clear(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Clear all history entries."""
    if not confirm:
        console.print("[yellow]This will delete all history entries.[/yellow]")
        response = typer.prompt("Are you sure? (yes/no)", default="no")
        if response.lower() not in ["yes", "y"]:
            console.print("[yellow]Cancelled.[/yellow]")
            return
    
    history_manager.clear()
    console.print("[green]History cleared.[/green]")


# Cache subcommand group
cache_app = typer.Typer(name="cache", help="Manage command cache")
app.add_typer(cache_app)


@cache_app.command(name="stats")
def cache_stats():
    """Show cache statistics."""
    stats = cache_manager.get_stats()
    
    from rich.table import Table
    
    table = Table(title="Cache Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Cache Hits", str(stats["hits"]))
    table.add_row("Cache Misses", str(stats["misses"]))
    table.add_row("Total Requests", str(stats["total"]))
    table.add_row("Hit Rate", f"{stats['hit_rate']}%")
    table.add_row("Cached Entries", str(stats["entries"]))
    
    console.print(table)


@cache_app.command(name="clear")
def cache_clear(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Clear all cached commands."""
    if not confirm:
        console.print("[yellow]This will delete all cached commands.[/yellow]")
        response = typer.prompt("Are you sure? (yes/no)", default="no")
        if response.lower() not in ["yes", "y"]:
            console.print("[yellow]Cancelled.[/yellow]")
            return
    
    cache_manager.clear()
    console.print("[green]Cache cleared.[/green]")


@app.command(name="batch")
def batch_cmd(
    file: str = typer.Argument(..., help="File containing queries (one per line)"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="OpenAI model to use"),
):
    """Process multiple queries from a file."""
    command_runner.run_batch(file, model=model)


# Template subcommand group
template_app = typer.Typer(name="template", help="Manage command templates/aliases")
app.add_typer(template_app)


@template_app.command(name="save")
def template_save(
    name: str = typer.Argument(..., help="Template name/alias"),
    command: str = typer.Argument(..., help="Command to save"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Template description"),
):
    """Save a command as a template/alias."""
    if template_manager.save_template(name, command, description):
        console.print(f"[green]Template '{name}' saved.[/green]")
    else:
        console.print("[red]Error: Failed to save template.[/red]")
        raise typer.Exit(1)


@template_app.command(name="list")
def template_list():
    """List all saved templates."""
    templates = template_manager.list_templates()
    
    if not templates:
        console.print("[yellow]No templates found.[/yellow]")
        return
    
    from rich.table import Table
    
    table = Table(title="Command Templates")
    table.add_column("Name", style="cyan", width=20)
    table.add_column("Command", style="green", width=60)
    table.add_column("Description", style="dim", width=30)
    
    for name, template in templates.items():
        table.add_row(
            name,
            template.get("command", ""),
            template.get("description", ""),
        )
    
    console.print(table)


@template_app.command(name="use")
def template_use(
    name: str = typer.Argument(..., help="Template name to use"),
    execute: bool = typer.Option(False, "--execute", "-e", help="Execute the command"),
    force: bool = typer.Option(False, "--force", "-f", help="Bypass safety check"),
):
    """Use a saved template."""
    command = template_manager.get_template(name)
    
    if not command:
        console.print(f"[red]Template '{name}' not found.[/red]")
        raise typer.Exit(1)
    
    console.print(f"[bold]Using template '{name}':[/bold] {command}\n")
    command_runner.run(
        command,  # Use the command directly as the query
        execute=execute,
        force=force,
    )


@template_app.command(name="delete")
def template_delete(
    name: str = typer.Argument(..., help="Template name to delete"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete a template."""
    if not template_manager.template_exists(name):
        console.print(f"[red]Template '{name}' not found.[/red]")
        raise typer.Exit(1)
    
    if not confirm:
        console.print(f"[yellow]This will delete template '{name}'.[/yellow]")
        response = typer.prompt("Are you sure? (yes/no)", default="no")
        if response.lower() not in ["yes", "y"]:
            console.print("[yellow]Cancelled.[/yellow]")
            return
    
    if template_manager.delete_template(name):
        console.print(f"[green]Template '{name}' deleted.[/green]")
    else:
        console.print(f"[red]Error deleting template '{name}'.[/red]")
        raise typer.Exit(1)


def cli():
    """CLI entry point."""
    # Known subcommands
    known_commands = ['init-config', 'history', 'cache', 'batch', 'template']
    
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
        query_parts, execute, copy, model, force, refine, alternatives, edit = parse_arguments(args)
        if query_parts:
            command_runner.run(
                " ".join(query_parts),
                execute=execute,
                model=model,
                copy=copy,
                force=force,
                refine=refine,
                alternatives=alternatives,
                edit=edit,
            )
            return
    
    # If no query provided and no known command, enter interactive mode
    if not first_non_option:
        query_parts, execute, copy, model, force, refine, alternatives, edit = parse_arguments(args)
        if not query_parts:
            # Interactive mode
            query_str = _interactive_query()
            if query_str:
                command_runner.run(
                    query_str,
                    execute=execute,
                    model=model,
                    copy=copy,
                    force=force,
                    refine=refine,
                    alternatives=alternatives,
                    edit=edit,
                )
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
            query_parts, execute, copy, model, force, refine, alternatives, edit = parse_arguments(args)
            if query_parts:
                command_runner.run(
                    " ".join(query_parts),
                    execute=execute,
                    model=model,
                    copy=copy,
                    force=force,
                    refine=refine,
                    alternatives=alternatives,
                    edit=edit,
                )
                return
        raise


if __name__ == "__main__":
    cli()

