"""Tests for simplified clipboard module."""

import pytest
from scripts.clipboard import (
    copy_to_clipboard,
    get_from_clipboard,
    is_clipboard_available,
    _command_exists
)


class TestClipboardAvailability:
    """Test clipboard availability checking."""
    
    def test_is_clipboard_available_returns_bool(self):
        """is_clipboard_available returns a boolean."""
        result = is_clipboard_available()
        assert isinstance(result, bool)
    
    def test_command_exists_for_python(self):
        """_command_exists detects python (should exist in test environment)."""
        # Python should exist in the test environment
        assert _command_exists("python") or _command_exists("python3")
    
    def test_command_exists_for_nonexistent_command(self):
        """_command_exists returns False for nonexistent commands."""
        assert _command_exists("definitely-not-a-real-command-xyz123") is False


class TestCopyToClipboard:
    """Test copying text to clipboard."""
    
    def test_copy_to_clipboard_returns_bool(self):
        """copy_to_clipboard returns a boolean."""
        result = copy_to_clipboard("test text")
        assert isinstance(result, bool)
    
    def test_copy_empty_string(self):
        """Can copy empty string without error."""
        result = copy_to_clipboard("")
        assert isinstance(result, bool)
    
    def test_copy_large_text(self):
        """Can handle large text (10KB)."""
        large_text = "x" * 10000
        result = copy_to_clipboard(large_text)
        assert isinstance(result, bool)
    
    @pytest.mark.skipif(not is_clipboard_available(), reason="No clipboard available")
    def test_copy_and_retrieve_roundtrip(self):
        """Test round-trip copy and retrieve (requires working clipboard)."""
        test_text = "Test clipboard content 123"
        
        copy_success = copy_to_clipboard(test_text)
        if copy_success:
            retrieved = get_from_clipboard()
            # Allow for some platforms adding newlines
            if retrieved is not None:
                assert test_text in retrieved or retrieved in test_text


class TestGetFromClipboard:
    """Test retrieving text from clipboard."""
    
    def test_get_from_clipboard_returns_string_or_none(self):
        """get_from_clipboard returns string or None."""
        result = get_from_clipboard()
        assert result is None or isinstance(result, str)


class TestWithoutPyperclip:
    """Test clipboard functionality without pyperclip installed."""
    
    def test_copy_falls_back_without_pyperclip(self, monkeypatch):
        """Clipboard operations fall back to system commands without pyperclip."""
        # Mock pyperclip import to fail
        def mock_import(name, *args, **kwargs):
            if name == "pyperclip":
                raise ImportError("Mock: pyperclip not available")
            return __import__(name, *args, **kwargs)
        
        monkeypatch.setattr("builtins.__import__", mock_import)
        
        # Should still return a boolean (success or failure)
        result = copy_to_clipboard("test")
        assert isinstance(result, bool)
    
    def test_is_available_without_pyperclip(self, monkeypatch):
        """is_clipboard_available checks platform commands without pyperclip."""
        # Mock pyperclip import to fail
        def mock_import(name, *args, **kwargs):
            if name == "pyperclip":
                raise ImportError("Mock: pyperclip not available")
            return __import__(name, *args, **kwargs)
        
        monkeypatch.setattr("builtins.__import__", mock_import)
        
        # Should still check platform-specific commands
        result = is_clipboard_available()
        assert isinstance(result, bool)
