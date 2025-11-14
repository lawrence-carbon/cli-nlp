"""Main CLI interface for CLI-NLP."""

import os
import sys

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
cache_manager = CacheManager(ttl_seconds=config_manager.get("cache_ttl_seconds", 86400))
context_manager = ContextManager()
template_manager = TemplateManager()
command_runner = CommandRunner(
    config_manager, history_manager, cache_manager, context_manager
)


def _interactive_query() -> str:
    """Interactive query input with tab completion using prompt_toolkit."""
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
        from prompt_toolkit.history import FileHistory
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
        console.print(
            "[yellow]Warning: prompt_toolkit not available. Install it with: poetry install[/yellow]"
        )
        try:
            query = input("Query: ")
            return query.strip()
        except (EOFError, KeyboardInterrupt):
            return ""
    except (EOFError, KeyboardInterrupt):
        return ""


# Known commands that should be treated as subcommands
KNOWN_COMMANDS = ["history", "cache", "batch", "template", "config"]


@click.group(
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "--execute", "-e", is_flag=True, help="Execute the generated command automatically"
)
@click.option(
    "--copy",
    "-c",
    is_flag=True,
    help="Copy command to clipboard (requires xclip or xsel)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Bypass safety check for modifying commands (use with caution)",
)
@click.option(
    "--refine", "-r", is_flag=True, help="Enter refinement mode to improve the command"
)
@click.option(
    "--alternatives", "-a", is_flag=True, help="Show alternative command options"
)
@click.option(
    "--edit", is_flag=True, help="Edit command in your default editor before execution"
)
@click.pass_context
def cli(ctx, execute, copy, force, refine, alternatives, edit):
    """Convert natural language to shell commands using LLM providers."""
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
        copy=copy,
        force=force,
        refine=refine,
        alternatives=alternatives,
        edit=edit,
    )


# Config subcommand group
@cli.group(name="config", help="Manage configuration settings")
def config_group():
    """Manage configuration settings."""
    pass


@config_group.command(name="show")
def config_show():
    """Show all configuration values."""
    config = config_manager.load()

    from rich.table import Table

    # Create a table for better formatting
    table = Table(title="Configuration", show_header=False, box=None)
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value", style="green")

    # Show non-provider config values
    table.add_row("Active Provider", config.get("active_provider") or "None")
    table.add_row("Active Model", config.get("active_model", "gpt-4o-mini"))
    table.add_row("Temperature", str(config.get("temperature", 0.3)))
    table.add_row("Max Tokens", str(config.get("max_tokens", 200)))

    console.print(table)

    # Show providers count
    providers = config.get("providers", {})
    if providers:
        console.print(
            f"\n[dim]Configured providers: {len(providers)} ({', '.join(providers.keys())})[/dim]"
        )
    else:
        console.print(
            "\n[dim]No providers configured. Run 'qtc config providers set' to configure one.[/dim]"
        )


@config_group.command(name="model")
@click.argument("model_name", required=False)
def config_model(model_name):
    """Get or set the active model."""
    if model_name:
        # Set the model
        config = config_manager.load()

        # Validate that active provider exists
        active_provider = config.get("active_provider")
        if not active_provider:
            console.print("[red]Error: No active provider configured.[/red]")
            console.print(
                "[dim]Run 'qtc config providers set' to configure a provider first.[/dim]"
            )
            sys.exit(1)

        # Optionally validate model against provider's models
        provider_config = config.get("providers", {}).get(active_provider, {})
        provider_models = provider_config.get("models", [])

        if provider_models and model_name not in provider_models:
            console.print(
                f"[yellow]Warning: Model '{model_name}' is not in the configured models for '{active_provider}'.[/yellow]"
            )
            console.print(f"[dim]Configured models: {', '.join(provider_models)}[/dim]")
            if not click.confirm("Continue anyway?", default=False):
                console.print("[yellow]Cancelled.[/yellow]")
                return

        config["active_model"] = model_name
        if config_manager.save(config):
            console.print(f"[green]Active model set to '{model_name}'.[/green]")
        else:
            console.print("[red]Error: Failed to save configuration.[/red]")
            sys.exit(1)
    else:
        # Get the model
        active_model = config_manager.get_active_model()
        console.print(f"[bold]Active Model:[/bold] {active_model}")


@config_group.command(name="temperature")
@click.argument("value", required=False, type=float)
def config_temperature(value):
    """Get or set the temperature setting (0.0-2.0)."""
    if value is not None:
        # Validate temperature range
        if value < 0.0 or value > 2.0:
            console.print("[red]Error: Temperature must be between 0.0 and 2.0.[/red]")
            sys.exit(1)

        # Set the temperature
        config = config_manager.load()
        config["temperature"] = value
        if config_manager.save(config):
            console.print(f"[green]Temperature set to {value}.[/green]")
        else:
            console.print("[red]Error: Failed to save configuration.[/red]")
            sys.exit(1)
    else:
        # Get the temperature
        temperature = config_manager.get("temperature", 0.3)
        console.print(f"[bold]Temperature:[/bold] {temperature}")


@config_group.command(name="max-tokens")
@click.argument("value", required=False, type=int)
def config_max_tokens(value):
    """Get or set the max tokens setting."""
    if value is not None:
        # Validate max_tokens range
        if value < 1:
            console.print("[red]Error: Max tokens must be at least 1.[/red]")
            sys.exit(1)

        if value > 100000:
            console.print(
                "[yellow]Warning: Max tokens is very high (>100000). This may cause issues.[/yellow]"
            )
            if not click.confirm("Continue anyway?", default=False):
                console.print("[yellow]Cancelled.[/yellow]")
                return

        # Set the max_tokens
        config = config_manager.load()
        config["max_tokens"] = value
        if config_manager.save(config):
            console.print(f"[green]Max tokens set to {value}.[/green]")
        else:
            console.print("[red]Error: Failed to save configuration.[/red]")
            sys.exit(1)
    else:
        # Get the max_tokens
        max_tokens = config_manager.get("max_tokens", 200)
        console.print(f"[bold]Max Tokens:[/bold] {max_tokens}")


# Providers subcommand group
@config_group.group(name="providers", help="Manage LLM provider configurations")
def providers_group():
    """Manage LLM provider configurations."""
    pass


@providers_group.command(name="set")
def providers_set():
    """Interactively configure a provider and model."""
    from getpass import getpass

    from cli_nlp.provider_manager import (
        ProviderDiscoveryError,
        format_model_name,
        get_available_providers,
        get_provider_models,
        search_models,
        search_providers,
    )

    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.completion import FuzzyCompleter, WordCompleter
    except ImportError:
        console.print("[red]Error: prompt_toolkit not available.[/red]")
        console.print("[yellow]Please install it with: poetry install[/yellow]")
        sys.exit(1)

    # Get available providers
    try:
        providers = get_available_providers()
    except ProviderDiscoveryError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print(
            "[yellow]Please ensure LiteLLM is properly installed: poetry install[/yellow]"
        )
        sys.exit(1)

    if not providers:
        console.print("[red]Error: No providers available.[/red]")
        sys.exit(1)

    # Interactive provider selection with search/filter
    console.print("[bold cyan]Select a provider:[/bold cyan]")
    console.print(
        "[dim]Type to search/filter providers. Press Tab for completion.[/dim]\n"
    )

    provider_completer = FuzzyCompleter(WordCompleter(providers, ignore_case=True))
    provider_session = PromptSession(
        completer=provider_completer,
        complete_while_typing=True,
    )

    provider = None
    while not provider:
        try:
            provider_input = provider_session.prompt("Provider: ").strip()
            if not provider_input:
                console.print("[yellow]Provider name cannot be empty.[/yellow]")
                continue

            # Search for matching providers
            matches = search_providers(provider_input)
            if not matches:
                console.print(
                    f"[yellow]No provider found matching '{provider_input}'.[/yellow]"
                )
                console.print(f"[dim]Available providers: {', '.join(providers)}[/dim]")
                continue

            if len(matches) == 1:
                provider = matches[0]
                console.print(f"[green]Selected: {provider}[/green]\n")
            else:
                # Multiple matches - show them
                from rich.table import Table

                table = Table(title="Matching Providers")
                table.add_column("#", style="cyan", width=3)
                table.add_column("Provider", style="green")

                for idx, match in enumerate(matches, 1):
                    table.add_row(str(idx), match)

                console.print(table)
                choice = click.prompt(f"\nSelect provider (1-{len(matches)})", type=int)
                if 1 <= choice <= len(matches):
                    provider = matches[choice - 1]
                    console.print(f"[green]Selected: {provider}[/green]\n")
                else:
                    console.print("[yellow]Invalid selection.[/yellow]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Cancelled.[/yellow]")
            sys.exit(0)

    # Get models for selected provider
    try:
        models = get_provider_models(provider)
    except ProviderDiscoveryError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print(
            "[yellow]Please ensure LiteLLM is properly installed: poetry install[/yellow]"
        )
        sys.exit(1)

    if not models:
        console.print(f"[yellow]No models found for provider '{provider}'.[/yellow]")
        model = click.prompt("Enter model name manually")
    else:
        # Interactive model selection with search/filter
        console.print(f"[bold cyan]Select a model for {provider}:[/bold cyan]")
        console.print(
            "[dim]Type to search/filter models. Press Tab for completion.[/dim]\n"
        )

        model_completer = FuzzyCompleter(WordCompleter(models, ignore_case=True))
        model_session = PromptSession(
            completer=model_completer,
            complete_while_typing=True,
        )

        model = None
        while not model:
            try:
                model_input = model_session.prompt("Model: ").strip()
                if not model_input:
                    console.print("[yellow]Model name cannot be empty.[/yellow]")
                    continue

                # Search for matching models
                matches = search_models(provider, model_input)
                if not matches:
                    console.print(
                        f"[yellow]No model found matching '{model_input}'.[/yellow]"
                    )
                    console.print(f"[dim]Available models: {', '.join(models)}[/dim]")
                    continue

                if len(matches) == 1:
                    model = matches[0]
                    console.print(f"[green]Selected: {model}[/green]\n")
                else:
                    # Multiple matches - show them
                    from rich.table import Table

                    table = Table(title="Matching Models")
                    table.add_column("#", style="cyan", width=3)
                    table.add_column("Model", style="green")

                    for idx, match in enumerate(matches, 1):
                        table.add_row(str(idx), match)

                    console.print(table)
                    choice = click.prompt(
                        f"\nSelect model (1-{len(matches)})", type=int
                    )
                    if 1 <= choice <= len(matches):
                        model = matches[choice - 1]
                        console.print(f"[green]Selected: {model}[/green]\n")
                    else:
                        console.print("[yellow]Invalid selection.[/yellow]")
            except (EOFError, KeyboardInterrupt):
                console.print("\n[yellow]Cancelled.[/yellow]")
                sys.exit(0)

    # Format model name for LiteLLM
    formatted_model = format_model_name(provider, model)

    # Get API key
    console.print(f"[bold cyan]Enter API key for {provider}:[/bold cyan]")
    console.print("[dim]The key will be stored securely in your config file.[/dim]\n")
    api_key = getpass("API Key: ").strip()

    if not api_key:
        console.print("[red]Error: API key cannot be empty.[/red]")
        sys.exit(1)

    # Save provider configuration
    if config_manager.add_provider(provider, api_key, models=[formatted_model]):
        console.print(f"[green]Provider '{provider}' configured successfully.[/green]")

        # Ask if user wants to set as active
        set_active = click.confirm(
            f"\nSet '{provider}' as active provider?", default=True
        )
        if set_active:
            config_manager.set_active_provider(provider)
            # Update active model
            config = config_manager.load()
            config["active_model"] = formatted_model
            config_manager.save(config)
            console.print(
                f"[green]Active provider set to '{provider}' with model '{formatted_model}'.[/green]"
            )
    else:
        console.print("[red]Error: Failed to save provider configuration.[/red]")
        sys.exit(1)


@providers_group.command(name="list")
def providers_list():
    """List all configured providers."""
    config = config_manager.load()
    providers = config.get("providers", {})
    active_provider = config.get("active_provider")

    if not providers:
        console.print("[yellow]No providers configured.[/yellow]")
        console.print(
            "[dim]Run 'qtc config providers set' to configure a provider.[/dim]"
        )
        return

    from rich.table import Table
    from rich.text import Text

    table = Table(title="Configured Providers")
    table.add_column("Provider", style="cyan", width=20)
    table.add_column("Models", style="green", width=40)
    table.add_column("Status", style="yellow", width=10)

    for provider_name, provider_config in providers.items():
        models = provider_config.get("models", [])
        models_str = ", ".join(models[:3])
        if len(models) > 3:
            models_str += f" (+{len(models) - 3} more)"

        status = "Active" if provider_name == active_provider else "Inactive"
        status_style = "bold green" if provider_name == active_provider else "dim"

        table.add_row(
            provider_name,
            models_str or "None",
            Text(status, style=status_style),
        )

    console.print(table)


@providers_group.command(name="show")
def providers_show():
    """Show active provider and model."""
    active_provider = config_manager.get_active_provider()
    active_model = config_manager.get_active_model()

    if not active_provider:
        console.print("[yellow]No active provider configured.[/yellow]")
        console.print(
            "[dim]Run 'qtc config providers set' to configure a provider.[/dim]"
        )
        return

    from rich.panel import Panel

    provider_config = config_manager.get_provider_config(active_provider)
    models = provider_config.get("models", []) if provider_config else []

    console.print(
        Panel(
            f"[bold]Provider:[/bold] {active_provider}\n"
            f"[bold]Model:[/bold] {active_model}\n"
            f"[bold]Available Models:[/bold] {', '.join(models) if models else 'None'}",
            title="Active Provider Configuration",
            border_style="green",
        )
    )


@providers_group.command(name="switch")
@click.argument("provider_name", required=True)
def providers_switch(provider_name):
    """Switch active provider."""
    config = config_manager.load()
    providers = config.get("providers", {})

    if provider_name not in providers:
        console.print(
            f"[red]Error: Provider '{provider_name}' is not configured.[/red]"
        )
        console.print(f"[dim]Available providers: {', '.join(providers.keys())}[/dim]")
        sys.exit(1)

    if config_manager.set_active_provider(provider_name):
        # Set first model as active model if available
        provider_config = providers[provider_name]
        models = provider_config.get("models", [])
        if models:
            config = config_manager.load()
            config["active_model"] = models[0]
            config_manager.save(config)
            console.print(
                f"[green]Switched to provider '{provider_name}' with model '{models[0]}'.[/green]"
            )
        else:
            console.print(f"[green]Switched to provider '{provider_name}'.[/green]")
            console.print(
                "[yellow]Warning: No models configured for this provider.[/yellow]"
            )
    else:
        console.print("[red]Error: Failed to switch provider.[/red]")
        sys.exit(1)


@providers_group.command(name="remove")
@click.argument("provider_name", required=True)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def providers_remove(provider_name, yes):
    """Remove a provider configuration."""
    config = config_manager.load()
    providers = config.get("providers", {})

    if provider_name not in providers:
        console.print(
            f"[red]Error: Provider '{provider_name}' is not configured.[/red]"
        )
        sys.exit(1)

    active_provider = config.get("active_provider")
    if provider_name == active_provider:
        console.print(
            f"[yellow]Warning: '{provider_name}' is currently the active provider.[/yellow]"
        )
        if not yes:
            response = click.prompt(
                "Are you sure you want to remove it? (yes/no)", default="no"
            )
            if response.lower() not in ["yes", "y"]:
                console.print("[yellow]Cancelled.[/yellow]")
                return

    if not yes:
        console.print(
            f"[yellow]This will remove provider '{provider_name}' configuration.[/yellow]"
        )
        response = click.prompt("Are you sure? (yes/no)", default="no")
        if response.lower() not in ["yes", "y"]:
            console.print("[yellow]Cancelled.[/yellow]")
            return

    if config_manager.remove_provider(provider_name):
        console.print(f"[green]Provider '{provider_name}' removed.[/green]")
    else:
        console.print("[red]Error: Failed to remove provider.[/red]")
        sys.exit(1)


@providers_group.command(name="refresh")
def providers_refresh():
    """Refresh the provider/model cache from LiteLLM."""
    from cli_nlp.provider_manager import ProviderDiscoveryError, refresh_provider_cache

    console.print("[bold cyan]Refreshing provider/model cache...[/bold cyan]")

    try:
        provider_models = refresh_provider_cache()

        from rich.table import Table

        table = Table(title="Available Providers (Refreshed)")
        table.add_column("Provider", style="cyan", width=20)
        table.add_column("Models Count", style="green", width=15)

        for provider, models in sorted(provider_models.items()):
            table.add_row(provider, str(len(models)))

        console.print(table)
        console.print(
            f"[green]Cache refreshed successfully. Found {len(provider_models)} providers.[/green]"
        )
    except ProviderDiscoveryError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print(
            "[yellow]Please ensure LiteLLM is properly installed: poetry install[/yellow]"
        )
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error refreshing cache: {e}[/red]")
        sys.exit(1)


# History subcommand group
@cli.group(name="history", help="Manage command history")
def history_group():
    """Manage command history."""
    pass


@history_group.command(name="list")
@click.option("--limit", "-n", default=20, help="Number of entries to show")
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
        executed_style = (
            "green"
            if entry.executed and entry.return_code == 0
            else "red"
            if entry.executed
            else "dim"
        )

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
@click.argument("query", required=True)
@click.option("--limit", "-n", default=20, help="Number of results to show")
def history_search(query, limit):
    """Search history by query or command."""
    results = history_manager.search(query)

    if not results:
        console.print(f"[yellow]No history entries found matching '{query}'.[/yellow]")
        return

    if limit:
        results = results[:limit]

    from rich.table import Table

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
@click.argument("entry_id", type=int, required=True)
def history_show(entry_id):
    """Show detailed information about a history entry."""
    entry = history_manager.get_by_id(entry_id)

    if not entry:
        console.print(f"[red]History entry {entry_id} not found.[/red]")
        sys.exit(1)

    from rich.panel import Panel

    console.print(
        Panel(
            f"[bold]Query:[/bold] {entry.query}\n"
            f"[bold]Command:[/bold] {entry.command}\n"
            f"[bold]Safe:[/bold] {'Yes' if entry.is_safe else 'No'} ({entry.safety_level.value})\n"
            f"[bold]Executed:[/bold] {'Yes' if entry.executed else 'No'}\n"
            f"[bold]Return Code:[/bold] {entry.return_code if entry.return_code is not None else 'N/A'}\n"
            f"[bold]Timestamp:[/bold] {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"[bold]Explanation:[/bold] {entry.explanation or 'N/A'}",
            title=f"History Entry #{entry_id}",
            border_style="green" if entry.is_safe else "yellow",
        )
    )


@history_group.command(name="execute")
@click.argument("entry_id", type=int, required=True)
@click.option("--force", "-f", is_flag=True, help="Bypass safety check")
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
@click.option("--output", "-o", default="history.json", help="Output file path")
@click.option("--format", "-f", default="json", help="Export format (json or csv)")
def history_export(output, format):
    """Export history to a file."""
    if format not in ["json", "csv"]:
        console.print("[red]Format must be 'json' or 'csv'.[/red]")
        sys.exit(1)

    try:
        content = history_manager.export(format=format)
        with open(output, "w") as f:
            f.write(content)
        console.print(f"[green]History exported to {output} ({format} format)[/green]")
    except Exception as e:
        console.print(f"[red]Error exporting history: {e}[/red]")
        sys.exit(1)


@history_group.command(name="clear")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
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
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
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
@click.argument("file", required=True)
def batch_cmd(file):
    """Process multiple queries from a file."""
    command_runner.run_batch(file)


# Template subcommand group
@cli.group(name="template", help="Manage command templates/aliases")
def template_group():
    """Manage command templates/aliases."""
    pass


@template_group.command(name="save")
@click.argument("name", required=True)
@click.argument("command", required=True)
@click.option("--description", "-d", help="Template description")
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
@click.argument("name", required=True)
@click.option("--execute", "-e", is_flag=True, help="Execute the command")
@click.option("--force", "-f", is_flag=True, help="Bypass safety check")
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
@click.argument("name", required=True)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
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
        if args[i] in [
            "-e",
            "--execute",
            "-c",
            "--copy",
            "-f",
            "--force",
            "-r",
            "--refine",
            "-a",
            "--alternatives",
            "--edit",
            "-h",
            "--help",
        ]:
            i += 1
        elif not args[i].startswith("-"):
            first_non_option = args[i]
            break
        else:
            i += 1

    # If first non-option is not a known command, treat everything as a query
    if first_non_option and first_non_option not in KNOWN_COMMANDS:
        # Parse options manually
        execute = "--execute" in args or "-e" in args
        copy = "--copy" in args or "-c" in args
        force = "--force" in args or "-f" in args
        refine = "--refine" in args or "-r" in args
        alternatives = "--alternatives" in args or "-a" in args
        edit = "--edit" in args

        # Extract query (everything that's not an option)
        query_parts = []
        i = 0
        while i < len(args):
            if args[i] in [
                "-e",
                "--execute",
                "-c",
                "--copy",
                "-f",
                "--force",
                "-r",
                "--refine",
                "-a",
                "--alternatives",
                "--edit",
            ]:
                i += 1
            elif not args[i].startswith("-"):
                query_parts.append(args[i])
                i += 1
            else:
                i += 1

        if query_parts:
            query_str = " ".join(query_parts)
            command_runner.run(
                query_str,
                execute=execute,
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
    except (UsageError, click.exceptions.UsageError):
        # If Click still fails, re-raise
        raise


# Export main as cli_entry for poetry scripts entry point
def cli_entry():
    """Entry point for poetry scripts."""
    main()


if __name__ == "__main__":
    main()
