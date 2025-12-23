"""Cross-platform clipboard utilities.

Provides a unified interface for clipboard operations across Windows, macOS, and Linux,
replacing the platform-specific bash clipboard detection.
"""

import sys
import subprocess
import platform
from typing import Optional


class ClipboardError(Exception):
    """Raised when clipboard operations fail."""
    pass


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard using the best available method.
    
    Args:
        text: Text to copy to clipboard
        
    Returns:
        True if successful, False if no clipboard method available
        
    Raises:
        ClipboardError: If clipboard operation fails
    """
    # Try pyperclip first (cross-platform)
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except (ImportError, Exception):
        pass
    
    # Fall back to platform-specific methods
    system = platform.system()
    
    try:
        if system == 'Windows':
            return _copy_windows(text)
        elif system == 'Darwin':  # macOS
            return _copy_macos(text)
        elif system == 'Linux':
            return _copy_linux(text)
        else:
            return False
    except Exception as e:
        raise ClipboardError(f"Failed to copy to clipboard: {e}")


def _copy_windows(text: str) -> bool:
    """Copy to clipboard on Windows using PowerShell."""
    try:
        # Try using win32clipboard if available
        import win32clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text)
        win32clipboard.CloseClipboard()
        return True
    except ImportError:
        pass
    
    # Fall back to PowerShell
    try:
        process = subprocess.Popen(
            ['powershell', '-command', '-'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        process.communicate(input=f'Set-Clipboard -Value {repr(text)}')
        return process.returncode == 0
    except Exception:
        return False


def _copy_macos(text: str) -> bool:
    """Copy to clipboard on macOS using pbcopy."""
    try:
        process = subprocess.Popen(
            ['pbcopy'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        process.communicate(input=text)
        return process.returncode == 0
    except FileNotFoundError:
        return False


def _copy_linux(text: str) -> bool:
    """Copy to clipboard on Linux using available tools.
    
    Tries in order: wl-copy (Wayland), xclip (X11), xsel (X11)
    """
    # Try Wayland clipboard
    if _try_linux_tool(['wl-copy'], text):
        return True
    
    # Try X11 clipboard tools
    if _try_linux_tool(['xclip', '-selection', 'clipboard'], text):
        return True
    
    if _try_linux_tool(['xsel', '--clipboard', '--input'], text):
        return True
    
    return False


def _try_linux_tool(cmd: list[str], text: str) -> bool:
    """Try to copy using a specific Linux clipboard tool."""
    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        process.communicate(input=text)
        return process.returncode == 0
    except FileNotFoundError:
        return False
    except Exception:
        return False


def get_from_clipboard() -> Optional[str]:
    """Get text from system clipboard.
    
    Returns:
        Clipboard text or None if unavailable
    """
    # Try pyperclip first
    try:
        import pyperclip
        return pyperclip.paste()
    except (ImportError, Exception):
        pass
    
    # Platform-specific fallbacks
    system = platform.system()
    
    try:
        if system == 'Windows':
            return _get_windows()
        elif system == 'Darwin':
            return _get_macos()
        elif system == 'Linux':
            return _get_linux()
    except Exception:
        pass
    
    return None


def _get_windows() -> Optional[str]:
    """Get clipboard content on Windows."""
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        text = win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
        return text
    except ImportError:
        pass
    
    # PowerShell fallback
    try:
        result = subprocess.run(
            ['powershell', '-command', 'Get-Clipboard'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except Exception:
        return None


def _get_macos() -> Optional[str]:
    """Get clipboard content on macOS."""
    try:
        result = subprocess.run(
            ['pbpaste'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except Exception:
        return None


def _get_linux() -> Optional[str]:
    """Get clipboard content on Linux."""
    # Try Wayland
    try:
        result = subprocess.run(
            ['wl-paste'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except Exception:
        pass
    
    # Try X11 tools
    for cmd in [['xclip', '-selection', 'clipboard', '-o'], ['xsel', '--clipboard', '--output']]:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except Exception:
            continue
    
    return None


def is_clipboard_available() -> bool:
    """Check if clipboard functionality is available.
    
    Returns:
        True if clipboard operations are supported
    """
    try:
        import pyperclip
        return True
    except ImportError:
        pass
    
    system = platform.system()
    
    if system == 'Windows':
        # Windows should always have PowerShell or win32clipboard
        return True
    elif system == 'Darwin':
        # macOS should always have pbcopy
        return True
    elif system == 'Linux':
        # Check if any Linux tool is available
        for tool in ['wl-copy', 'xclip', 'xsel']:
            try:
                subprocess.run([tool, '--version'], capture_output=True, check=False)
                return True
            except FileNotFoundError:
                continue
        return False
    
    return False
