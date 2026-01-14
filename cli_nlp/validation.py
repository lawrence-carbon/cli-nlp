"""Input validation utilities."""

from cli_nlp.exceptions import ValidationError


def validate_query(query: str) -> str:
    """
    Validate user query input.

    Args:
        query: User query string

    Returns:
        Validated and normalized query

    Raises:
        ValidationError: If query is invalid
    """
    if not query or not isinstance(query, str):
        raise ValidationError(
            "Query must be a non-empty string",
            field="query",
            value=str(query)[:100] if query else None,
        )

    query = query.strip()

    if not query:
        raise ValidationError("Query cannot be empty", field="query")

    if len(query) > 10000:  # Reasonable limit
        raise ValidationError(
            f"Query too long ({len(query)} characters). Maximum length: 10000 characters",
            field="query",
            value=query[:100],
        )

    return query


def validate_model_name(model: str) -> str:
    """
    Validate model name.

    Args:
        model: Model name string

    Returns:
        Validated model name

    Raises:
        ValidationError: If model name is invalid
    """
    if not model or not isinstance(model, str):
        raise ValidationError(
            "Model name must be a non-empty string",
            field="model",
            value=str(model)[:100] if model else None,
        )

    model = model.strip()

    if not model:
        raise ValidationError("Model name cannot be empty", field="model")

    if len(model) > 200:  # Reasonable limit
        raise ValidationError(
            f"Model name too long ({len(model)} characters). Maximum length: 200 characters",
            field="model",
            value=model[:100],
        )

    return model


def validate_temperature(temperature: float | None) -> float:
    """
    Validate temperature value.

    Args:
        temperature: Temperature value (0.0 to 2.0)

    Returns:
        Validated temperature

    Raises:
        ValidationError: If temperature is invalid
    """
    if temperature is None:
        return 0.3  # Default

    if not isinstance(temperature, (int, float)):
        raise ValidationError(
            "Temperature must be a number",
            field="temperature",
            value=str(temperature),
        )

    if temperature < 0.0 or temperature > 2.0:
        raise ValidationError(
            f"Temperature must be between 0.0 and 2.0, got {temperature}",
            field="temperature",
            value=str(temperature),
        )

    return float(temperature)


def validate_max_tokens(max_tokens: int | None) -> int:
    """
    Validate max_tokens value.

    Args:
        max_tokens: Maximum tokens (1 to 100000)

    Returns:
        Validated max_tokens

    Raises:
        ValidationError: If max_tokens is invalid
    """
    if max_tokens is None:
        return 200  # Default

    if not isinstance(max_tokens, int):
        raise ValidationError(
            "max_tokens must be an integer",
            field="max_tokens",
            value=str(max_tokens),
        )

    if max_tokens < 1 or max_tokens > 100000:
        raise ValidationError(
            f"max_tokens must be between 1 and 100000, got {max_tokens}",
            field="max_tokens",
            value=str(max_tokens),
        )

    return max_tokens


def validate_config_structure(config: dict) -> dict:
    """
    Validate configuration structure.

    Args:
        config: Configuration dictionary

    Returns:
        Validated configuration

    Raises:
        ValidationError: If config structure is invalid
    """
    if not isinstance(config, dict):
        raise ValidationError(
            "Configuration must be a dictionary",
            field="config",
        )

    # Check required top-level keys
    required_keys = ["providers"]
    for key in required_keys:
        if key not in config:
            raise ValidationError(
                f"Configuration missing required key: {key}",
                field="config",
            )

    # Validate providers structure
    if not isinstance(config["providers"], dict):
        raise ValidationError(
            "Configuration 'providers' must be a dictionary",
            field="providers",
        )

    # Validate each provider
    for provider_name, provider_config in config["providers"].items():
        if not isinstance(provider_config, dict):
            raise ValidationError(
                f"Provider '{provider_name}' configuration must be a dictionary",
                field=f"providers.{provider_name}",
            )

        # Check for api_key
        if "api_key" not in provider_config:
            raise ValidationError(
                f"Provider '{provider_name}' missing required 'api_key'",
                field=f"providers.{provider_name}.api_key",
            )

        # Validate models if present
        if "models" in provider_config:
            if not isinstance(provider_config["models"], list):
                raise ValidationError(
                    f"Provider '{provider_name}' 'models' must be a list",
                    field=f"providers.{provider_name}.models",
                )

    return config
