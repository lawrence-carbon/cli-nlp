"""Tests for input validation."""

import pytest

from cli_nlp.exceptions import ValidationError
from cli_nlp.validation import (
    validate_config_structure,
    validate_max_tokens,
    validate_model_name,
    validate_query,
    validate_temperature,
)


class TestValidateQuery:
    """Test validate_query function."""

    def test_valid_query(self):
        """Test valid query."""
        result = validate_query("list all python files")
        assert result == "list all python files"

    def test_query_stripped(self):
        """Test that query is stripped."""
        result = validate_query("  list files  ")
        assert result == "list files"

    def test_empty_query(self):
        """Test that empty query raises error."""
        with pytest.raises(ValidationError, match="cannot be empty|must be a non-empty string"):
            validate_query("")

    def test_whitespace_only_query(self):
        """Test that whitespace-only query raises error."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_query("   ")

    def test_non_string_query(self):
        """Test that non-string query raises error."""
        with pytest.raises(ValidationError, match="must be a non-empty string"):
            validate_query(None)
        with pytest.raises(ValidationError, match="must be a non-empty string"):
            validate_query(123)

    def test_query_too_long(self):
        """Test that query too long raises error."""
        long_query = "x" * 10001
        with pytest.raises(ValidationError, match="too long"):
            validate_query(long_query)

    def test_query_at_limit(self):
        """Test that query at limit is valid."""
        query = "x" * 10000
        result = validate_query(query)
        assert len(result) == 10000


class TestValidateModelName:
    """Test validate_model_name function."""

    def test_valid_model_name(self):
        """Test valid model name."""
        result = validate_model_name("gpt-4o-mini")
        assert result == "gpt-4o-mini"

    def test_model_name_stripped(self):
        """Test that model name is stripped."""
        result = validate_model_name("  gpt-4o-mini  ")
        assert result == "gpt-4o-mini"

    def test_empty_model_name(self):
        """Test that empty model name raises error."""
        with pytest.raises(ValidationError, match="cannot be empty|must be a non-empty string"):
            validate_model_name("")

    def test_non_string_model_name(self):
        """Test that non-string model name raises error."""
        with pytest.raises(ValidationError, match="must be a non-empty string"):
            validate_model_name(None)
        with pytest.raises(ValidationError, match="must be a non-empty string"):
            validate_model_name(123)

    def test_model_name_too_long(self):
        """Test that model name too long raises error."""
        long_name = "x" * 201
        with pytest.raises(ValidationError, match="too long"):
            validate_model_name(long_name)


class TestValidateTemperature:
    """Test validate_temperature function."""

    def test_valid_temperature(self):
        """Test valid temperature."""
        assert validate_temperature(0.0) == 0.0
        assert validate_temperature(0.5) == 0.5
        assert validate_temperature(1.0) == 1.0
        assert validate_temperature(2.0) == 2.0

    def test_none_temperature_defaults(self):
        """Test that None temperature defaults to 0.3."""
        assert validate_temperature(None) == 0.3

    def test_temperature_below_minimum(self):
        """Test that temperature below 0.0 raises error."""
        with pytest.raises(ValidationError, match="between 0.0 and 2.0"):
            validate_temperature(-0.1)

    def test_temperature_above_maximum(self):
        """Test that temperature above 2.0 raises error."""
        with pytest.raises(ValidationError, match="between 0.0 and 2.0"):
            validate_temperature(2.1)

    def test_non_numeric_temperature(self):
        """Test that non-numeric temperature raises error."""
        with pytest.raises(ValidationError, match="must be a number"):
            validate_temperature("0.5")
        with pytest.raises(ValidationError, match="must be a number"):
            validate_temperature([])

    def test_integer_temperature(self):
        """Test that integer temperature is converted to float."""
        result = validate_temperature(1)
        assert isinstance(result, float)
        assert result == 1.0


class TestValidateMaxTokens:
    """Test validate_max_tokens function."""

    def test_valid_max_tokens(self):
        """Test valid max_tokens."""
        assert validate_max_tokens(1) == 1
        assert validate_max_tokens(100) == 100
        assert validate_max_tokens(100000) == 100000

    def test_none_max_tokens_defaults(self):
        """Test that None max_tokens defaults to 200."""
        assert validate_max_tokens(None) == 200

    def test_max_tokens_below_minimum(self):
        """Test that max_tokens below 1 raises error."""
        with pytest.raises(ValidationError, match="between 1 and 100000"):
            validate_max_tokens(0)

    def test_max_tokens_above_maximum(self):
        """Test that max_tokens above 100000 raises error."""
        with pytest.raises(ValidationError, match="between 1 and 100000"):
            validate_max_tokens(100001)

    def test_non_integer_max_tokens(self):
        """Test that non-integer max_tokens raises error."""
        with pytest.raises(ValidationError, match="must be an integer"):
            validate_max_tokens(100.5)
        with pytest.raises(ValidationError, match="must be an integer"):
            validate_max_tokens("100")


class TestValidateConfigStructure:
    """Test validate_config_structure function."""

    def test_valid_config(self):
        """Test valid config structure."""
        config = {
            "providers": {
                "openai": {
                    "api_key": "sk-test",
                    "models": ["gpt-4o-mini"],
                }
            }
        }
        result = validate_config_structure(config)
        assert result == config

    def test_config_missing_providers(self):
        """Test that config without providers raises error."""
        config = {"active_provider": "openai"}
        with pytest.raises(ValidationError, match="missing required key"):
            validate_config_structure(config)

    def test_config_providers_not_dict(self):
        """Test that providers not being a dict raises error."""
        config = {"providers": "not-a-dict"}
        with pytest.raises(ValidationError, match="must be a dictionary"):
            validate_config_structure(config)

    def test_provider_missing_api_key(self):
        """Test that provider without api_key raises error."""
        config = {
            "providers": {
                "openai": {
                    "models": ["gpt-4o-mini"],
                }
            }
        }
        with pytest.raises(ValidationError, match="missing required 'api_key'"):
            validate_config_structure(config)

    def test_provider_models_not_list(self):
        """Test that provider models not being a list raises error."""
        config = {
            "providers": {
                "openai": {
                    "api_key": "sk-test",
                    "models": "not-a-list",
                }
            }
        }
        with pytest.raises(ValidationError, match="must be a list"):
            validate_config_structure(config)

    def test_provider_without_models(self):
        """Test that provider without models is valid."""
        config = {
            "providers": {
                "openai": {
                    "api_key": "sk-test",
                }
            }
        }
        result = validate_config_structure(config)
        assert result == config

    def test_non_dict_config(self):
        """Test that non-dict config raises error."""
        with pytest.raises(ValidationError, match="must be a dictionary"):
            validate_config_structure("not-a-dict")
        with pytest.raises(ValidationError, match="must be a dictionary"):
            validate_config_structure([])

    def test_validate_query_none(self):
        """Test validate_query with None."""
        with pytest.raises(ValidationError, match="must be a non-empty string"):
            validate_query(None)

    def test_validate_model_name_none(self):
        """Test validate_model_name with None."""
        with pytest.raises(ValidationError, match="must be a non-empty string"):
            validate_model_name(None)

    def test_validate_config_provider_without_models_key(self):
        """Test config validation when provider doesn't have models key."""
        config = {
            "providers": {
                "openai": {
                    "api_key": "sk-test",
                    # No models key - should be valid
                }
            }
        }
        result = validate_config_structure(config)
        assert result == config
