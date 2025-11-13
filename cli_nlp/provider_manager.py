"""Provider and model discovery for LiteLLM."""

import json
import os
from functools import lru_cache
from pathlib import Path

try:
    import litellm
except ImportError:
    litellm = None


class ProviderDiscoveryError(Exception):
    """Raised when provider/model discovery fails."""

    pass


def _get_cache_path() -> Path:
    """Get path to cache file for provider/model data."""
    xdg_cache = os.getenv("XDG_CACHE_HOME")
    if xdg_cache:
        cache_dir = Path(xdg_cache) / "cli-nlp"
    else:
        cache_dir = Path.home() / ".cache" / "cli-nlp"

    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "provider_models_cache.json"


def _load_cached_providers() -> dict[str, list[str]] | None:
    """Load cached provider/model data."""
    cache_path = _get_cache_path()
    if not cache_path.exists():
        return None

    try:
        with open(cache_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return None


def _save_cached_providers(provider_models: dict[str, list[str]]):
    """Save provider/model data to cache."""
    cache_path = _get_cache_path()
    try:
        with open(cache_path, "w") as f:
            json.dump(provider_models, f, indent=2)
    except Exception:
        pass  # Silently fail if cache can't be saved


def _fetch_from_litellm() -> dict[str, list[str]]:
    """Fetch providers and models dynamically from LiteLLM."""
    if not litellm:
        raise ProviderDiscoveryError(
            "LiteLLM is not installed. Please install it with: poetry install"
        )

    # Access LiteLLM's model registry
    if not hasattr(litellm, "models_by_provider"):
        raise ProviderDiscoveryError(
            "LiteLLM models_by_provider not available. Please ensure you have a compatible version of LiteLLM installed."
        )

    try:
        models_by_provider = litellm.models_by_provider

        if not models_by_provider:
            raise ProviderDiscoveryError(
                "LiteLLM models_by_provider is empty. This may indicate an issue with your LiteLLM installation."
            )

        providers_models: dict[str, list[str]] = {}

        # Extract providers and models from registry
        for provider, models in models_by_provider.items():
            if not models:
                continue

            # Normalize provider name
            provider_normalized = provider.lower()

            # Skip some internal/duplicate providers
            if provider_normalized in ["custom_provider", "custom_llm_provider"]:
                continue

            # Skip text-completion variants (they're usually duplicates)
            if provider_normalized.startswith("text-completion-"):
                continue

            # Convert models to list if needed and filter
            model_list = (
                list(models) if isinstance(models, list | set | tuple) else [models]
            )

            # Deduplicate and sort models
            unique_models = sorted(set(model_list))

            if unique_models:
                providers_models[provider_normalized] = unique_models

        if not providers_models:
            raise ProviderDiscoveryError(
                "No providers found in LiteLLM models_by_provider. This may indicate an issue with your LiteLLM installation."
            )

        return providers_models
    except ProviderDiscoveryError:
        raise
    except Exception as e:
        raise ProviderDiscoveryError(
            f"Failed to fetch providers/models from LiteLLM: {e}"
        ) from e


def _fetch_from_openai_api() -> list[str] | None:
    """Fetch models dynamically from OpenAI API."""
    try:
        try:
            import requests
        except ImportError:
            # requests not available, skip API fetch
            return None

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        response = requests.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5,
        )

        if response.status_code == 200:
            data = response.json()
            models = []
            for model in data.get("data", []):
                model_id = model.get("id", "")
                # Filter for chat models
                if "gpt" in model_id.lower() and (
                    "chat" in model_id.lower()
                    or "gpt-4" in model_id.lower()
                    or "gpt-3.5" in model_id.lower()
                ):
                    models.append(model_id)
            return sorted(models)
    except Exception:
        pass

    return None


@lru_cache(maxsize=1)
def _get_provider_models_dict() -> dict[str, list[str]]:
    """Get provider/models dictionary, using cache and LiteLLM."""
    # Try to load from cache first
    cached = _load_cached_providers()
    if cached:
        return cached

    # Fetch from LiteLLM (will raise ProviderDiscoveryError if it fails)
    provider_models = _fetch_from_litellm()

    # Enhance OpenAI models with API if available
    if "openai" in provider_models:
        api_models = _fetch_from_openai_api()
        if api_models:
            # Merge API models with LiteLLM models
            existing_models = set(provider_models["openai"])
            for model in api_models:
                if model not in existing_models:
                    provider_models["openai"].append(model)
            provider_models["openai"].sort()

    # Save to cache
    _save_cached_providers(provider_models)
    return provider_models


def refresh_provider_cache():
    """Force refresh of provider/model cache."""
    _get_provider_models_dict.cache_clear()

    # Remove cache file to force refresh
    cache_path = _get_cache_path()
    if cache_path.exists():
        try:
            cache_path.unlink()
        except Exception:
            pass

    # Fetch fresh data
    return _get_provider_models_dict()


def get_available_providers() -> list[str]:
    """Get list of available providers dynamically from LiteLLM.

    Raises:
        ProviderDiscoveryError: If provider/model discovery fails.
    """
    try:
        provider_models = _get_provider_models_dict()
        return sorted(provider_models.keys())
    except ProviderDiscoveryError:
        raise
    except Exception as e:
        raise ProviderDiscoveryError(f"Failed to get available providers: {e}") from e


def get_provider_models(provider: str) -> list[str]:
    """Get available models for a provider dynamically from LiteLLM.

    Raises:
        ProviderDiscoveryError: If provider/model discovery fails.
    """
    try:
        provider_models = _get_provider_models_dict()
        return provider_models.get(provider.lower(), [])
    except ProviderDiscoveryError:
        raise
    except Exception as e:
        raise ProviderDiscoveryError(
            f"Failed to get models for provider '{provider}': {e}"
        ) from e


def get_model_provider(model: str) -> str | None:
    """Determine which provider a model belongs to."""
    model_lower = model.lower()
    provider_models = _get_provider_models_dict()

    # Check each provider's models
    for provider, models in provider_models.items():
        for provider_model in models:
            if model_lower == provider_model.lower() or model_lower.startswith(
                f"{provider}/"
            ):
                return provider

    # Check if model has provider prefix
    if "/" in model:
        provider_prefix = model.split("/")[0].lower()
        if provider_prefix in provider_models:
            return provider_prefix

    # Try to infer from LiteLLM if available
    if litellm:
        try:
            if hasattr(litellm, "models_by_provider"):
                models_by_provider = litellm.models_by_provider
                # Search through providers to find which one has this model
                for provider, models in models_by_provider.items():
                    if model_lower in [m.lower() for m in models]:
                        return provider.lower()
        except Exception:
            pass

    # Default to OpenAI for common OpenAI models
    if model_lower.startswith("gpt-"):
        return "openai"

    return None


def format_model_name(provider: str, model: str) -> str:
    """Format model name for LiteLLM (add provider prefix if needed)."""
    # Some providers need prefixes, others don't
    if provider.lower() in ["openai", "anthropic", "google", "cohere"]:
        # These providers don't need prefix for common models
        return model
    elif provider.lower() == "azure":
        if not model.startswith("azure/"):
            return f"azure/{model}"
    elif provider.lower() == "bedrock":
        if not model.startswith("bedrock/"):
            return f"bedrock/{model}"
    elif provider.lower() == "ollama":
        if not model.startswith("ollama/"):
            return f"ollama/{model}"

    return model


def search_providers(query: str) -> list[str]:
    """Search/filter providers by name."""
    query_lower = query.lower()
    providers = get_available_providers()

    # Exact match first
    exact_matches = [p for p in providers if p.lower() == query_lower]
    if exact_matches:
        return exact_matches

    # Contains match
    contains_matches = [p for p in providers if query_lower in p.lower()]

    # Fuzzy match (simple)
    fuzzy_matches = []
    for provider in providers:
        if query_lower[0] in provider.lower():
            if provider not in contains_matches:
                fuzzy_matches.append(provider)

    return contains_matches + fuzzy_matches


def search_models(provider: str, query: str) -> list[str]:
    """Search/filter models for a provider."""
    query_lower = query.lower()
    models = get_provider_models(provider)

    # Exact match first
    exact_matches = [m for m in models if m.lower() == query_lower]
    if exact_matches:
        return exact_matches

    # Contains match
    contains_matches = [m for m in models if query_lower in m.lower()]

    # Fuzzy match (simple)
    fuzzy_matches = []
    for model in models:
        if query_lower[0] in model.lower():
            if model not in contains_matches:
                fuzzy_matches.append(model)

    return contains_matches + fuzzy_matches
