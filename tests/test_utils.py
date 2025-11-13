"""Unit tests for utility functions."""

from unittest.mock import MagicMock, patch

from cli_nlp.utils import check_clipboard_available, copy_to_clipboard, show_help


class TestShowHelp:
    """Test suite for show_help function."""

    @patch("cli_nlp.utils.console")
    def test_show_help(self, mock_console):
        """Test show_help function."""
        show_help()
        mock_console.print.assert_called_once()
        # Verify it was called with HELP_TEXT
        call_args = mock_console.print.call_args[0]
        assert len(call_args) > 0


class TestCheckClipboardAvailable:
    """Test suite for check_clipboard_available function."""

    @patch("shutil.which")
    def test_check_clipboard_available_xclip(self, mock_which):
        """Test check_clipboard_available when xclip is available."""
        mock_which.side_effect = lambda cmd: (
            "/usr/bin/xclip" if cmd == "xclip" else None
        )

        result = check_clipboard_available()
        assert result is True

    @patch("shutil.which")
    def test_check_clipboard_available_xsel(self, mock_which):
        """Test check_clipboard_available when xsel is available."""
        mock_which.side_effect = lambda cmd: "/usr/bin/xsel" if cmd == "xsel" else None

        result = check_clipboard_available()
        assert result is True

    @patch("shutil.which")
    def test_check_clipboard_available_neither(self, mock_which):
        """Test check_clipboard_available when neither tool is available."""
        mock_which.return_value = None

        result = check_clipboard_available()
        assert result is False


class TestCopyToClipboard:
    """Test suite for copy_to_clipboard function."""

    @patch("cli_nlp.utils.check_clipboard_available")
    @patch("subprocess.run")
    def test_copy_to_clipboard_success_xclip(self, mock_subprocess, mock_check):
        """Test copy_to_clipboard with xclip."""
        mock_check.return_value = True
        mock_result = MagicMock()
        mock_subprocess.return_value = mock_result

        result = copy_to_clipboard("test command")
        assert result is True
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert call_args[0][0] == ["xclip", "-selection", "clipboard"]
        assert call_args[1]["input"] == b"test command"

    @patch("cli_nlp.utils.check_clipboard_available")
    @patch("subprocess.run")
    def test_copy_to_clipboard_success_xsel(self, mock_subprocess, mock_check):
        """Test copy_to_clipboard with xsel fallback."""
        mock_check.return_value = True
        mock_result = MagicMock()

        # First call (xclip) fails, second (xsel) succeeds
        mock_subprocess.side_effect = [FileNotFoundError(), mock_result]

        result = copy_to_clipboard("test command")
        assert result is True
        assert mock_subprocess.call_count == 2
        # Check second call was xsel
        second_call = mock_subprocess.call_args_list[1]
        assert second_call[0][0] == ["xsel", "--clipboard", "--input"]

    @patch("cli_nlp.utils.check_clipboard_available")
    def test_copy_to_clipboard_not_available(self, mock_check):
        """Test copy_to_clipboard when clipboard tools are not available."""
        mock_check.return_value = False

        result = copy_to_clipboard("test command")
        assert result is False

    @patch("cli_nlp.utils.check_clipboard_available")
    @patch("subprocess.run")
    def test_copy_to_clipboard_both_fail(self, mock_subprocess, mock_check):
        """Test copy_to_clipboard when both xclip and xsel fail."""
        mock_check.return_value = True

        # Both calls fail
        mock_subprocess.side_effect = [FileNotFoundError(), FileNotFoundError()]

        result = copy_to_clipboard("test command")
        assert result is False

    @patch("cli_nlp.utils.check_clipboard_available")
    @patch("subprocess.run")
    def test_copy_to_clipboard_called_process_error(self, mock_subprocess, mock_check):
        """Test copy_to_clipboard handles CalledProcessError."""
        mock_check.return_value = True
        import subprocess

        # xclip fails with CalledProcessError, xsel also fails
        mock_subprocess.side_effect = [
            subprocess.CalledProcessError(1, "xclip"),
            subprocess.CalledProcessError(1, "xsel"),
        ]

        result = copy_to_clipboard("test command")
        assert result is False

    @patch("cli_nlp.utils.check_clipboard_available")
    @patch("subprocess.run")
    def test_copy_to_clipboard_xclip_fails_xsel_succeeds(
        self, mock_subprocess, mock_check
    ):
        """Test copy_to_clipboard when xclip fails but xsel succeeds."""
        mock_check.return_value = True
        mock_result = MagicMock()

        # xclip fails with CalledProcessError, xsel succeeds
        import subprocess

        mock_subprocess.side_effect = [
            subprocess.CalledProcessError(1, "xclip"),
            mock_result,
        ]

        result = copy_to_clipboard("test command")
        assert result is True
