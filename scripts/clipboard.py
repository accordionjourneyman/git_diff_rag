"""Simplified cross-platform clipboard utilities.

Provides clipboard operations via pyperclip with minimal fallback to system commands.
"""

import subprocess
import platform
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ClipboardError(Exception):
    """Raised when clipboard operations fail."""
    pass


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard.
    
    Args:
        text: Text to copy to clipboard
        
    Returns:
        True if successful, False otherwise
    """
    # Try pyperclip first (recommended, cross-platform)
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except ImportError:
        logger.warning(
            "pyperclip not installed. For better clipboard support, install with: "
            "pip install pyperclip"
        )
        # Fall through to system command fallback
    except Exception as e:
        logger.error(f"pyperclip failed: {e}")
        # Fall through to system command fallback
    
    # Minimal platform-specific fallbacks
    system = platform.system()
    
    try:
        if system == 'Darwin':  # macOS
            subprocess.run(
                ['pbcopy'],
                input=text.encode('utf-8'),
                check=True,
                timeout=5
            )
            return True
        elif system == 'Linux':
            # Try wl-copy (Wayland) first, then xclip (X11)
            for cmd in [['wl-copy'], ['xclip', '-selection', 'clipboard']]:
                try:
                    subprocess.run(
                        cmd,
                        input=text.encode('utf-8'),
                        check=True,
                        timeout=5,
                        stderr=subprocess.DEVNULL
                    )
                    return True
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue
            
            logger.warning(
                "No clipboard tool found. Install wl-copy (Wayland) or xclip (X11): "
                "apt install wl-clipboard xclip"
            )
            return False
        elif system == 'Windows':
            # Windows: Try PowerShell as fallback
            subprocess.run(
                ['powershell', '-Command', f'Set-Clipboard -Value "{text}"'],
                check=True,
                timeout=5
            )
            return True
        else:
            logger.warning(f"Unsupported platform: {system}")
            return False
            
    except Exception as e:
        logger.error(f"Clipboard operation failed: {e}")
        return False


def get_from_clipboard() -> Optional[str]:
    """Get text from system clipboard.
    
    Returns:
        Clipboard contents or None if unavailable
    """
    # Try pyperclip first
    try:
        import pyperclip
        return pyperclip.paste()
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"pyperclip failed: {e}")
    
    # Minimal platform-specific fallbacks
    system = platform.system()
    
    try:
        if system == 'Darwin':  # macOS
            result = subprocess.run(
                ['pbpaste'],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            return result.stdout
        elif system == 'Linux':
            # Try wl-paste (Wayland) first, then xclip (X11)
            for cmd in [['wl-paste'], ['xclip', '-selection', 'clipboard', '-o']]:
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=5,
                        stderr=subprocess.DEVNULL
                    )
                    return result.stdout
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue
            return None
        elif system == 'Windows':
            result = subprocess.run(
                ['powershell', '-Command', 'Get-Clipboard'],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            return result.stdout
        else:
            return None
            
    except Exception as e:
        logger.error(f"Failed to get clipboard content: {e}")
        return None


def is_clipboard_available() -> bool:
    """Check if clipboard is available.
    
    Returns:
        True if clipboard operations are likely to work
    """
    # Check if pyperclip is available
    try:
        import pyperclip
        # Try a test operation
        pyperclip.copy("")
        return True
    except ImportError:
        pass
    except Exception:
        # pyperclip installed but doesn't work (e.g., headless Linux)
        pass
    
    # Check platform-specific commands
    system = platform.system()
    
    if system == 'Darwin':
        return _command_exists('pbcopy')
    elif system == 'Linux':
        return _command_exists('wl-copy') or _command_exists('xclip')
    elif system == 'Windows':
        return True  # PowerShell should always be available
    
    return False


def _command_exists(command: str) -> bool:
    """Check if a command exists in PATH.
    
    Args:
        command: Command name to check
        
    Returns:
        True if command exists
    """
    try:
        subprocess.run(
            [command, '--version'],
            capture_output=True,
            timeout=2,
            check=False
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
