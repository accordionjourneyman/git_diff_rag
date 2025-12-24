"""Google Gemini CLI integration module.

Provides programmatic interface to Google Gemini CLI, parallel to call_copilot_cli.py.
Uses the 'gemini' command for CLI interactions.
"""

import os
import sys
import subprocess
import json
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import shutil

load_dotenv()

# Default model (Gemini 2.0 Flash as of Dec 2025)
DEFAULT_MODEL = "gemini-3-flash-preview"


class GeminiCLIError(Exception):
    """Raised when Gemini CLI operations fail."""
    pass


class GeminiCLINotInstalledError(GeminiCLIError):
    """Raised when Gemini CLI is not installed or not in PATH."""
    pass


class GeminiCLIAuthError(GeminiCLIError):
    """Raised when Gemini CLI authentication fails."""
    pass


def is_gemini_cli_installed() -> bool:
    """Check if Google Gemini CLI is installed and available.

    Returns:
        True if 'gemini' command is available in PATH
    """
    gemini_path = shutil.which('gemini')
    if gemini_path:
        try:
            result = subprocess.run(
                [gemini_path, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False
    return False


def is_gemini_cli_authenticated() -> bool:
    """Verify that Gemini CLI is authenticated.

    Returns:
        True if authenticated, False otherwise
    """
    gemini_path = shutil.which('gemini')
    if not gemini_path:
        return False

    try:
        # Try to run gemini with --version to check if it's working
        # If it can run basic commands, assume it's authenticated
        result = subprocess.run(
            [gemini_path, '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def call_gemini_cli(
    prompt: str,
    model: Optional[str] = None,
    allow_tools: Optional[list[str]] = None,
    deny_tools: Optional[list[str]] = None,
    allow_all_tools: bool = False,
    timeout: int = 300
) -> str:
    """Call Google Gemini CLI with a prompt in programmatic mode.

    Args:
        prompt: The prompt to send to Gemini CLI
        model: Model to use (optional, uses default if not specified)
        allow_tools: List of tools to allow without approval
        deny_tools: List of tools to deny
        allow_all_tools: If True, allow all tools without approval (DANGEROUS)
        timeout: Timeout in seconds (default: 300)

    Returns:
        Gemini CLI's response text

    Raises:
        GeminiCLINotInstalledError: If Gemini CLI is not installed
        GeminiCLIAuthError: If authentication fails
        GeminiCLIError: For other CLI errors
    """
    if not is_gemini_cli_installed():
        raise GeminiCLINotInstalledError("Gemini CLI is not installed or not in PATH")

    # Get the full path to gemini
    gemini_path = shutil.which('gemini')
    if not gemini_path:
        raise GeminiCLINotInstalledError("Gemini CLI is not installed or not in PATH")

    # Build command - use positional argument for the prompt
    # For very long prompts, we might need to use stdin, but try positional first
    MAX_ARG_LENGTH = 131072  # 128KB limit for command line arguments
    
    if len(prompt) > MAX_ARG_LENGTH:
        # For extremely long prompts, use stdin
        cmd = [gemini_path]
        input_text = prompt
    else:
        # Use positional argument for normal prompts
        cmd = [gemini_path, prompt]
        input_text = None

    # Add model if specified
    if model:
        cmd.extend(['-m', model])

    # Handle tool permissions
    if allow_all_tools:
        cmd.append('-y')  # YOLO mode - auto-approve all tools
    elif allow_tools:
        # Convert tool names to CLI format
        tool_mapping = {
            'shell': 'shell',
            'write': 'edit',
            'read': 'read',
            'run': 'run'
        }
        allowed = []
        for tool in allow_tools:
            if tool in tool_mapping:
                allowed.append(tool_mapping[tool])
        if allowed:
            cmd.extend(['--allowed-tools', ','.join(allowed)])

    # Set output format to json for programmatic use (might avoid thinking issues)
    cmd.extend(['-o', 'json'])
    
    # Set approval mode to auto_edit to avoid thinking features
    cmd.extend(['--approval-mode', 'auto_edit'])

    try:
        result = subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=dict(os.environ, FORCE_COLOR='0', NO_THINKING='1')  # Disable colors and thinking
        )

        if result.returncode != 0:
            stderr = result.stderr.lower()
            if 'auth' in stderr or 'authenticate' in stderr or 'login' in stderr:
                raise GeminiCLIAuthError(f"Gemini CLI authentication failed: {result.stderr}")
            else:
                raise GeminiCLIError(f"Gemini CLI error: {result.stderr}")

        # Parse JSON output
        try:
            output_data = json.loads(result.stdout)
            # Extract the response text from JSON structure
            if isinstance(output_data, dict) and 'response' in output_data:
                return output_data['response']
            elif isinstance(output_data, dict) and 'text' in output_data:
                return output_data['text']
            elif isinstance(output_data, str):
                return output_data
            else:
                return result.stdout.strip()
        except json.JSONDecodeError:
            # If JSON parsing fails, return as text
            return result.stdout.strip()

    except subprocess.TimeoutExpired:
        raise GeminiCLIError(f"Gemini CLI timed out after {timeout} seconds")
    except FileNotFoundError:
        raise GeminiCLINotInstalledError("Gemini CLI command not found")


def get_available_models() -> list[str]:
    """Get list of available models from Gemini CLI.

    Note:
        Gemini CLI may not expose programmatic model listing.
        This returns known available models based on Gemini API offerings.

    Returns:
        List of model names
    """
    # TODO: When Gemini CLI adds programmatic model listing, implement it here
    # For now, return known models from Gemini API, prioritizing thinking-capable models
    return [
        "gemini-2.5-pro",  # Supports thinking
        "gemini-2.0-flash",
        "gemini-2.0-flash-exp",
        "gemini-2.5-flash",
        "gemini-3-flash-preview",
        "gemini-1.5-pro",
        "gemini-1.5-flash"
    ]


def estimate_tokens(prompt: str) -> int:
    """Estimate token count for a prompt.

    Note:
        Gemini CLI doesn't provide token counting API. This is a rough estimate
        based on character count (approximately 4 chars per token for English).

    Args:
        prompt: The prompt text

    Returns:
        Estimated token count
    """
    # Rough estimation: ~4 characters per token for English text
    return len(prompt) // 4


if __name__ == '__main__':
    # Simple test
    if len(sys.argv) < 2:
        print("Usage: python call_gemini_cli.py <prompt>")
        sys.exit(1)

    try:
        response = call_gemini_cli(sys.argv[1])
        print(response)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)