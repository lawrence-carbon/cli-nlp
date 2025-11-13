"""Unit tests for Pydantic models."""


from cli_nlp.models import CommandResponse, MultiCommandResponse, SafetyLevel


class TestSafetyLevel:
    """Test suite for SafetyLevel enum."""

    def test_safety_level_values(self):
        """Test SafetyLevel enum values."""
        assert SafetyLevel.SAFE == "safe"
        assert SafetyLevel.MODIFYING == "modifying"

    def test_safety_level_from_string(self):
        """Test creating SafetyLevel from string."""
        assert SafetyLevel("safe") == SafetyLevel.SAFE
        assert SafetyLevel("modifying") == SafetyLevel.MODIFYING


class TestCommandResponse:
    """Test suite for CommandResponse model."""

    def test_create_command_response(self):
        """Test creating CommandResponse."""
        response = CommandResponse(
            command="ls -la",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            explanation="List files",
        )

        assert response.command == "ls -la"
        assert response.is_safe is True
        assert response.safety_level == SafetyLevel.SAFE
        assert response.explanation == "List files"

    def test_command_response_without_explanation(self):
        """Test CommandResponse without explanation."""
        response = CommandResponse(
            command="ls",
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
        )

        assert response.explanation is None

    def test_command_response_modifying(self):
        """Test CommandResponse for modifying command."""
        response = CommandResponse(
            command="rm -rf /tmp/test",
            is_safe=False,
            safety_level=SafetyLevel.MODIFYING,
            explanation="Remove test directory",
        )

        assert response.is_safe is False
        assert response.safety_level == SafetyLevel.MODIFYING


class TestMultiCommandResponse:
    """Test suite for MultiCommandResponse model."""

    def test_create_multi_command_response(self):
        """Test creating MultiCommandResponse."""
        commands = [
            CommandResponse(
                command="find . -name '*.py'",
                is_safe=True,
                safety_level=SafetyLevel.SAFE,
            ),
            CommandResponse(
                command="wc -l",
                is_safe=True,
                safety_level=SafetyLevel.SAFE,
            ),
        ]

        response = MultiCommandResponse(
            commands=commands,
            execution_type="pipeline",
            combined_command="find . -name '*.py' | wc -l",
            overall_safe=True,
            explanation="Find and count Python files",
        )

        assert len(response.commands) == 2
        assert response.execution_type == "pipeline"
        assert response.combined_command == "find . -name '*.py' | wc -l"
        assert response.overall_safe is True
        assert response.explanation == "Find and count Python files"

    def test_multi_command_response_defaults(self):
        """Test MultiCommandResponse with defaults."""
        commands = [
            CommandResponse(
                command="ls",
                is_safe=True,
                safety_level=SafetyLevel.SAFE,
            ),
        ]

        response = MultiCommandResponse(
            commands=commands,
            overall_safe=True,
        )

        assert response.execution_type == "sequence"
        assert response.combined_command is None
        assert response.explanation is None

    def test_multi_command_response_mixed_safety(self):
        """Test MultiCommandResponse with mixed safety levels."""
        commands = [
            CommandResponse(
                command="ls",
                is_safe=True,
                safety_level=SafetyLevel.SAFE,
            ),
            CommandResponse(
                command="rm file.txt",
                is_safe=False,
                safety_level=SafetyLevel.MODIFYING,
            ),
        ]

        response = MultiCommandResponse(
            commands=commands,
            overall_safe=False,
        )

        assert response.overall_safe is False

