"""Main CLI interface for CLI-NLP."""

import os
import sys
from typing import Optional

import click
from click.exceptions import UsageError

from cli_nlp.cache_manager import CacheManager
from cli_nlp.command_runner import CommandRunner
from cli_nlp.completer import QueryCompleter
from cli_nlp.config_manager import ConfigManager
from cli_nlp.context_manager import ContextManager
from cli_nlp.history_manager import HistoryManager
from cli_nlp.template_manager import TemplateManager
from cli_nlp.utils import console

# Initialize managers
config_manager = ConfigManager()
history_manager = HistoryManager()
cache_manager = CacheManager(
    ttl_seconds=config_manager.get("cache_ttl_seconds", 86400)
)
context_manager = ContextManager()
template_manager = TemplateManager()
command_runner = CommandRunner(config_manager, history_manager, cache_manager, context_manager)


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


# Known commands that should be treated as subcommands
KNOWN_COMMANDS = ['init-config', 'history', 'cache', 'batch', 'template']


@click.group(
    invoke_without_command=True,
    context_settings={'help_option_names': ['-h', '--help']}
)
@click.option('--execute', '-e', is_flag=True, help='Execute the generated command automatically')
@click.option('--copy', '-c', is_flag=True, help='Copy command to clipboard (requires xclip or xsel)')
@click.option('--model', '-m', help='OpenAI model to use (default: from config or gpt-4o-mini)')
@click.option('--force', '-f', is_flag=True, help='Bypass safety check for modifying commands (use with caution)')
@click.option('--refine', '-r', is_flag=True, help='Enter refinement mode to improve the command')
@click.option('--alternatives', '-a', is_flag=True, help='Show alternative command options')
@click.option('--edit', is_flag=True, help='Edit command in your default editor before execution')
@click.pass_context
def cli(ctx, execute, copy, model, force, refine, alternatives, edit):
    """Convert natural language to shell commands using OpenAI."""
    # If a subcommand was invoked, let it handle it
    if ctx.invoked_subcommand is not None:
        return
    
    # Get remaining args after Click has processed options
    # ctx.args contains the remaining positional arguments
    remaining_args = ctx.args
    
    # Build query string from remaining arguments
    if remaining_args:
        query_str = " ".join(remaining_args)
    else:
        # Enter interactive mode with tab completion
        query_str = _interactive_query()
        if not query_str:
            console.print("[yellow]No query provided. Exiting.[/yellow]")
            sys.exit(0)
    
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


@cli.command(name="init-config")
def init_config_cmd():
    """Create a default config file template."""
    config_manager.create_default()


# History subcommand group
@cli.group(name="history", help="Manage command history")
def history_group():
    """Manage command history."""
    pass


@history_group.command(name="list")
@click.option('--limit', '-n', default=20, help='Number of entries to show')
def history_list(limit):
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


@history_group.command(name="search")
@click.argument('query', required=True)
@click.option('--limit', '-n', default=20, help='Number of results to show')
def history_search(query, limit):
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


@history_group.command(name="show")
@click.argument('entry_id', type=int, required=True)
def history_show(entry_id):
    """Show detailed information about a history entry."""
    entry = history_manager.get_by_id(entry_id)
    
    if not entry:
        console.print(f"[red]History entry {entry_id} not found.[/red]")
        sys.exit(1)
    
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


@history_group.command(name="execute")
@click.argument('entry_id', type=int, required=True)
@click.option('--force', '-f', is_flag=True, help='Bypass safety check')
def history_execute(entry_id, force):
    """Re-execute a command from history."""
    entry = history_manager.get_by_id(entry_id)
    
    if not entry:
        console.print(f"[red]History entry {entry_id} not found.[/red]")
        sys.exit(1)
    
    console.print(f"[bold]Re-executing command from history entry #{entry_id}:[/bold]")
    console.print(f"[dim]Original query: {entry.query}[/dim]\n")
    
    # Use the command runner to execute
    command_runner.run(
        entry.query,
        execute=True,
        force=force or entry.is_safe,  # Auto-force if safe
    )


@history_group.command(name="export")
@click.option('--output', '-o', default='history.json', help='Output file path')
@click.option('--format', '-f', default='json', help='Export format (json or csv)')
def history_export(output, format):
    """Export history to a file."""
    if format not in ["json", "csv"]:
        console.print("[red]Format must be 'json' or 'csv'.[/red]")
        sys.exit(1)
    
    try:
        content = history_manager.export(format=format)
        with open(output, 'w') as f:
            f.write(content)
        console.print(f"[green]History exported to {output} ({format} format)[/green]")
    except Exception as e:
        console.print(f"[red]Error exporting history: {e}[/red]")
        sys.exit(1)


@history_group.command(name="clear")
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
def history_clear(yes):
    """Clear all history entries."""
    if not yes:
        console.print("[yellow]This will delete all history entries.[/yellow]")
        response = click.prompt("Are you sure? (yes/no)", default="no")
        if response.lower() not in ["yes", "y"]:
            console.print("[yellow]Cancelled.[/yellow]")
            return
    
    history_manager.clear()
    console.print("[green]History cleared.[/green]")


# Cache subcommand group
@cli.group(name="cache", help="Manage command cache")
def cache_group():
    """Manage command cache."""
    pass


@cache_group.command(name="stats")
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


@cache_group.command(name="clear")
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
def cache_clear(yes):
    """Clear all cached commands."""
    if not yes:
        console.print("[yellow]This will delete all cached commands.[/yellow]")
        response = click.prompt("Are you sure? (yes/no)", default="no")
        if response.lower() not in ["yes", "y"]:
            console.print("[yellow]Cancelled.[/yellow]")
            return
    
    cache_manager.clear()
    console.print("[green]Cache cleared.[/green]")


@cli.command(name="batch")
@click.argument('file', required=True)
@click.option('--model', '-m', help='OpenAI model to use')
def batch_cmd(file, model):
    """Process multiple queries from a file."""
    command_runner.run_batch(file, model=model)


# Template subcommand group
@cli.group(name="template", help="Manage command templates/aliases")
def template_group():
    """Manage command templates/aliases."""
    pass


@template_group.command(name="save")
@click.argument('name', required=True)
@click.argument('command', required=True)
@click.option('--description', '-d', help='Template description')
def template_save(name, command, description):
    """Save a command as a template/alias."""
    if template_manager.save_template(name, command, description):
        console.print(f"[green]Template '{name}' saved.[/green]")
    else:
        console.print("[red]Error: Failed to save template.[/red]")
        sys.exit(1)


@template_group.command(name="list")
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


@template_group.command(name="use")
@click.argument('name', required=True)
@click.option('--execute', '-e', is_flag=True, help='Execute the command')
@click.option('--force', '-f', is_flag=True, help='Bypass safety check')
def template_use(name, execute, force):
    """Use a saved template."""
    command = template_manager.get_template(name)
    
    if not command:
        console.print(f"[red]Template '{name}' not found.[/red]")
        sys.exit(1)
    
    console.print(f"[bold]Using template '{name}':[/bold] {command}\n")
    command_runner.run(
        command,  # Use the command directly as the query
        execute=execute,
        force=force,
    )


@template_group.command(name="delete")
@click.argument('name', required=True)
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
def template_delete(name, yes):
    """Delete a template."""
    if not template_manager.template_exists(name):
        console.print(f"[red]Template '{name}' not found.[/red]")
        sys.exit(1)
    
    if not yes:
        console.print(f"[yellow]This will delete template '{name}'.[/yellow]")
        response = click.prompt("Are you sure? (yes/no)", default="no")
        if response.lower() not in ["yes", "y"]:
            console.print("[yellow]Cancelled.[/yellow]")
            return
    
    if template_manager.delete_template(name):
        console.print(f"[green]Template '{name}' deleted.[/green]")
    else:
        console.print(f"[red]Error deleting template '{name}'.[/red]")
        sys.exit(1)


def main():
    """CLI entry point with error handling for command-less queries."""
    # Check if first non-option arg is a known command
    args = sys.argv[1:]
    first_non_option = None
    i = 0
    while i < len(args):
        if args[i] in ['-e', '--execute', '-c', '--copy', '-f', '--force', 
                      '-r', '--refine', '-a', '--alternatives', '--edit', '-h', '--help']:
            i += 1
        elif args[i] in ['-m', '--model']:
            i += 2
        elif not args[i].startswith('-'):
            first_non_option = args[i]
            break
        else:
            i += 1
    
    # If first non-option is not a known command, treat everything as a query
    if first_non_option and first_non_option not in KNOWN_COMMANDS:
        # Parse options manually
        execute = '--execute' in args or '-e' in args
        copy = '--copy' in args or '-c' in args
        force = '--force' in args or '-f' in args
        refine = '--refine' in args or '-r' in args
        alternatives = '--alternatives' in args or '-a' in args
        edit = '--edit' in args
        
        # Extract model
        model = None
        if '--model' in args:
            idx = args.index('--model')
            if idx + 1 < len(args):
                model = args[idx + 1]
        elif '-m' in args:
            idx = args.index('-m')
            if idx + 1 < len(args):
                model = args[idx + 1]
        
        # Extract query (everything that's not an option)
        query_parts = []
        i = 0
        while i < len(args):
            if args[i] in ['-e', '--execute', '-c', '--copy', '-f', '--force', 
                          '-r', '--refine', '-a', '--alternatives', '--edit']:
                i += 1
            elif args[i] in ['-m', '--model']:
                i += 2
            elif not args[i].startswith('-'):
                query_parts.append(args[i])
                i += 1
            else:
                i += 1
        
        if query_parts:
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
            return
    
    # Otherwise, let Click handle it (for known commands or no args)
    try:
        cli()
    except (UsageError, click.exceptions.UsageError) as e:
        # If Click still fails, re-raise
        raise


# Export main as cli_entry for poetry scripts entry point
def cli_entry():
    """Entry point for poetry scripts."""
    main()


if __name__ == "__main__":
    main()
