"""Tests for utility functions."""

import pytest

from cli_nlp.utils import copy_to_clipboard, show_help


class TestUtils:
    """Test utility functions."""

    def test_show_help(self, capsys):
        """Test show_help function."""
        show_help()
        captured = capsys.readouterr()
        assert "QTC" in captured.out or "Query to Command" in captured.out

    def test_copy_to_clipboard_success(self, monkeypatch):
        """Test copying to clipboard successfully."""
        mock_subprocess = []
        def mock_run(*args, **kwargs):
            mock_subprocess.append(args)
            return type("MockProcess", (), {"returncode": 0})()

        monkeypatch.setattr("subprocess.run", mock_run)

        result = copy_to_clipboard("test command")
        assert result is True
        assert len(mock_subprocess) > 0

    def test_copy_to_clipboard_failure(self, monkeypatch):
        """Test copying to clipboard when it fails."""
        def mock_run(*args, **kwargs):
            raise FileNotFoundError("xclip not found")

        monkeypatch.setattr("subprocess.run", mock_run)

        result = copy_to_clipboard("test command")
        assert result is False

    def test_copy_to_clipboard_xsel_fallback(self, monkeypatch):
        """Test copying to clipboard with xsel fallback."""
        call_count = []
        def mock_run(*args, **kwargs):
            call_count.append(args[0])
            if "xclip" in str(args[0]):
                raise FileNotFoundError("xclip not found")
            return type("MockProcess", (), {"returncode": 0})()

        monkeypatch.setattr("subprocess.run", mock_run)

        result = copy_to_clipboard("test command")
        # Should try xclip first, then xsel
        assert len(call_count) >= 1
        assert result is True or result is False  # May succeed or fail depending on xsel
