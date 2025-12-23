"""GitHub Copilot CLI integration module.

Provides programmatic interface to GitHub Copilot CLI, parallel to call_gemini.py.
Uses the new 'copilot' command (not the deprecated gh-copilot extension).
"""

import os
import sys
import subprocess
import json
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Default model (Claude Sonnet 4.5 as of Dec 2025)
DEFAULT_MODEL = "claude-sonnet-4.5"


class CopilotError(Exception):
    """Raised when Copilot CLI operations fail."""
    pass


class CopilotNotInstalledError(CopilotError):
    """Raised when Copilot CLI is not installed or not in PATH."""
    pass


class CopilotAuthError(CopilotError):
    """Raised when Copilot CLI authentication fails."""
    pass


def is_copilot_installed() -> bool:
    """Check if GitHub Copilot CLI is installed and available.
    
    Returns:
        True if 'copilot' command is available in PATH
    """
    try:
        result = subprocess.run(
            ['copilot', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_authentication() -> bool:
    """Verify that Copilot CLI is authenticated.
    
    Returns:
        True if authenticated, False otherwise
        
    Note:
        The new Copilot CLI doesn't have a dedicated auth check command.
        This attempts a minimal operation to verify authentication.
    """
    if not is_copilot_installed():
        return False
    
    try:
        # Try a simple prompt to verify authentication
        result = subprocess.run(
            ['copilot', '-p', 'test', '--allow-all-tools'],
            capture_output=True,
            text=True,
            timeout=10
        )
        # If we get a response (even an error about the prompt), auth is OK
        # If auth fails, we typically get a different error pattern
        return 'authenticate' not in result.stderr.lower()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def call_copilot(
    prompt: str,
    allow_tools: Optional[list[str]] = None,
    deny_tools: Optional[list[str]] = None,
    allow_all_tools: bool = False,
    timeout: int = 300
) -> str:
    """Call GitHub Copilot CLI with a prompt in programmatic mode.
    
    Args:
        prompt: The prompt to send to Copilot
        allow_tools: List of tools to allow without approval (e.g., ['shell', 'write'])
        deny_tools: List of tools to deny (e.g., ['shell(rm)', 'shell(git push)'])
        allow_all_tools: If True, allow all tools without approval (DANGEROUS)
        timeout: Timeout in seconds (default: 300)
        
    Returns:
        Copilot's response text
        
    Raises:
        CopilotNotInstalledError: If Copilot CLI is not installed
        CopilotAuthError: If Copilot CLI is not authenticated
        CopilotError: If the API call fails
    """
    if not prompt.strip():
        raise ValueError("Empty prompt provided")
    
    if not is_copilot_installed():
        raise CopilotNotInstalledError(
            "GitHub Copilot CLI is not installed. "
            "Install it from: https://docs.github.com/en/copilot/how-tos/set-up/install-copilot-cli"
        )
    
    # Build command
    cmd = ['copilot', '-p', prompt]
    
    # Add tool permissions
    if allow_all_tools:
        cmd.append('--allow-all-tools')
    else:
        if allow_tools:
            for tool in allow_tools:
                cmd.extend(['--allow-tool', tool])
        
        if deny_tools:
            for tool in deny_tools:
                cmd.extend(['--deny-tool', tool])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )
        
        # Check for auth error in stderr even if return code is 0 (Copilot CLI quirk)
        if 'No authentication information found' in result.stderr or 'authenticate' in result.stderr.lower():
             raise CopilotAuthError(
                f"Copilot CLI authentication failed. Please authenticate.\n{result.stderr}"
            )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            
            # Check for authentication errors
            if 'authenticate' in error_msg.lower() or 'unauthorized' in error_msg.lower():
                raise CopilotAuthError(
                    f"Copilot CLI authentication failed. Please authenticate.\n{error_msg}"
                )
            
            # Generic error
            raise CopilotError(
                f"Copilot CLI failed with exit code {result.returncode}:\n"
                f"STDERR: {error_msg}\n"
                f"STDOUT: {result.stdout.strip()}"
            )
        
        return result.stdout.strip()
        
    except subprocess.TimeoutExpired:
        raise CopilotError(f"Copilot CLI timed out after {timeout} seconds")
    except FileNotFoundError:
        raise CopilotNotInstalledError("Copilot CLI executable not found in PATH")


def call_with_file(
    prompt_file: str,
    output_file: Optional[str] = None,
    allow_tools: Optional[list[str]] = None,
    timeout: int = 300
) -> str:
    """Call Copilot CLI with a prompt from a file.
    
    Args:
        prompt_file: Path to file containing the prompt
        output_file: Optional path to save the response
        allow_tools: List of tools to allow without approval
        timeout: Timeout in seconds
        
    Returns:
        Copilot's response text
    """
    prompt_path = Path(prompt_file)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt = f.read()
    
    response = call_copilot(prompt, allow_tools=allow_tools, timeout=timeout)
    
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(response)
    
    return response


def get_available_models() -> list[str]:
    """Get list of available models from Copilot CLI.
    
    Note:
        As of Dec 2025, Copilot CLI uses /model slash command in interactive mode only.
        Programmatic mode doesn't expose model listing API. This returns the known
        default model.
        
    Returns:
        List of model names (currently just the default)
    """
    # TODO: When Copilot CLI adds programmatic model listing, implement it here
    # For now, return known default
    return [DEFAULT_MODEL, "gpt-4", "gpt-3.5-turbo"]  # Based on GitHub Copilot offerings


def estimate_tokens(prompt: str) -> int:
    """Estimate token count for a prompt.
    
    Note:
        Copilot CLI doesn't provide token counting API. This is a rough estimate
        based on character count (approximately 4 chars per token for English).
        
    Args:
        prompt: The prompt text
        
    Returns:
        Estimated token count
    """
    return len(prompt) // 4


def main():
    """Command-line interface for Copilot CLI integration."""
    if len(sys.argv) < 2:
        print("Usage: call_copilot_cli.py <prompt_file> [output_file]")
        print("       call_copilot_cli.py --check-install")
        print("       call_copilot_cli.py --check-auth")
        sys.exit(1)
    
    if sys.argv[1] == '--check-install':
        if is_copilot_installed():
            print("✓ GitHub Copilot CLI is installed")
            sys.exit(0)
        else:
            print("✗ GitHub Copilot CLI is not installed")
            print("Install from: https://docs.github.com/en/copilot/how-tos/set-up/install-copilot-cli")
            sys.exit(1)
    
    if sys.argv[1] == '--check-auth':
        if not is_copilot_installed():
            print("✗ GitHub Copilot CLI is not installed")
            sys.exit(1)
        
        if check_authentication():
            print("✓ GitHub Copilot CLI is authenticated")
            sys.exit(0)
        else:
            print("✗ GitHub Copilot CLI is not authenticated")
            print("Please authenticate with: copilot")
            sys.exit(1)
    
    # Call with prompt file
    prompt_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        response = call_with_file(
            prompt_file,
            output_file,
            allow_tools=['shell(git)', 'write']  # Safe defaults
        )
        
        if not output_file:
            print(response)
        
        sys.exit(0)
        
    except CopilotNotInstalledError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    except CopilotAuthError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(3)
    except CopilotError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
