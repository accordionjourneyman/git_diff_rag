"""LLM Provider Strategy Pattern.

This module implements a Strategy Pattern for LLM providers, making it easy to add
new providers without modifying the orchestrator.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import os
import logging

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def call(self, prompt: str, **kwargs) -> str:
        """Call the LLM with a prompt.
        
        Args:
            prompt: The prompt to send to the LLM
            **kwargs: Provider-specific parameters
            
        Returns:
            The LLM's response text
            
        Raises:
            Exception: If the API call fails
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available/configured.
        
        Returns:
            True if the provider can be used, False otherwise
        """
        pass
    
    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model for this provider.
        
        Returns:
            Default model identifier
        """
        pass
    
    @abstractmethod
    def list_models(self) -> list[str]:
        """List available models for this provider.
        
        Returns:
            List of model identifiers
        """
        pass


class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""
    
    def call(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Call Gemini API with retry logic.
        
        Args:
            prompt: The prompt to send
            model: Model to use (default: gemini-2.0-flash-exp)
            **kwargs: Additional parameters
            
        Returns:
            Gemini's response text
        """
        from scripts import call_gemini
        
        model = model or self.get_default_model()
        return call_gemini.call_with_retry(prompt, model=model)
    
    def is_available(self) -> bool:
        """Check if Gemini API key is configured."""
        return bool(os.getenv("GEMINI_API_KEY"))
    
    def get_default_model(self) -> str:
        """Get default Gemini model."""
        return "gemini-2.0-flash-exp"
    
    def list_models(self) -> list[str]:
        """List available Gemini models from the SDK."""
        try:
            from scripts import call_gemini
            client = call_gemini.get_client()
            return call_gemini.list_models(client)
        except Exception as e:
            logger.warning(f"Failed to fetch Gemini models from SDK: {e}")
            # Fallback to hardcoded list
            return [
                "gemini-2.0-flash-exp",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
                "gemini-pro"
            ]


class GeminiCLIProvider(LLMProvider):
    """Google Gemini CLI provider."""
    
    def call(
        self,
        prompt: str,
        allow_tools: Optional[list[str]] = None,
        deny_tools: Optional[list[str]] = None,
        allow_all_tools: bool = False,
        timeout: int = 300,
        **kwargs
    ) -> str:
        """Call Google Gemini CLI.
        
        Args:
            prompt: The prompt to send
            allow_tools: List of tools to allow without approval
            deny_tools: List of tools to deny
            allow_all_tools: If True, allow all tools without approval
            timeout: Timeout in seconds
            **kwargs: Additional parameters (model, etc.)
            
        Returns:
            Gemini CLI's response text
        """
        from scripts import call_gemini_cli
        
        model = kwargs.get('model')
        return call_gemini_cli.call_gemini_cli(
            prompt=prompt,
            model=model,
            allow_tools=allow_tools,
            deny_tools=deny_tools,
            allow_all_tools=allow_all_tools,
            timeout=timeout
        )
    
    def is_available(self) -> bool:
        """Check if Gemini CLI is installed and authenticated."""
        from scripts import call_gemini_cli
        
        return (
            call_gemini_cli.is_gemini_cli_installed() and
            call_gemini_cli.is_gemini_cli_authenticated()
        )
    
    def get_default_model(self) -> str:
        """Get default Gemini CLI model."""
        return "gemini-2.5-pro"
    
    def list_models(self) -> list[str]:
        """List available Gemini CLI models."""
        from scripts import call_gemini_cli
        
        return call_gemini_cli.get_available_models()


class CopilotCLIProvider(LLMProvider):
    """GitHub Copilot CLI provider."""
    
    def call(
        self,
        prompt: str,
        allow_tools: Optional[list[str]] = None,
        deny_tools: Optional[list[str]] = None,
        allow_all_tools: bool = False,
        timeout: int = 300,
        **kwargs
    ) -> str:
        """Call GitHub Copilot CLI.
        
        Args:
            prompt: The prompt to send
            allow_tools: List of tools to allow without approval
            deny_tools: List of tools to deny
            allow_all_tools: If True, allow all tools without approval
            timeout: Timeout in seconds
            **kwargs: Additional parameters
            
        Returns:
            Copilot's response text
        """
        from scripts import call_copilot_cli
        
        return call_copilot_cli.call_copilot(
            prompt=prompt,
            allow_tools=allow_tools,
            deny_tools=deny_tools,
            allow_all_tools=allow_all_tools,
            timeout=timeout
        )
    
    def is_available(self) -> bool:
        """Check if Copilot CLI is installed and authenticated."""
        from scripts import call_copilot_cli
        
        return (
            call_copilot_cli.is_copilot_installed() and
            call_copilot_cli.check_authentication()
        )
    
    def get_default_model(self) -> str:
        """Get default Copilot model."""
        return "gpt-4"
    
    def list_models(self) -> list[str]:
        """List available Copilot models.
        
        Note: Copilot CLI doesn't provide a programmatic way to list models.
        These are hardcoded based on known available models.
        """
        return [
            "gpt-4",
            "claude-sonnet-4.5",
            "o1-preview",
            "o1-mini"
        ]


class ManualCopilotProvider(LLMProvider):
    """Manual Copilot provider (clipboard mode)."""
    
    def call(self, prompt: str, **kwargs) -> str:
        """Copy prompt to clipboard for manual pasting.
        
        Args:
            prompt: The prompt to copy
            **kwargs: Ignored
            
        Returns:
            Empty string (manual mode doesn't get response programmatically)
        """
        from scripts import clipboard
        
        success = clipboard.copy_to_clipboard(prompt)
        if success:
            logger.info("✓ Prompt copied to clipboard - paste into Copilot manually")
            return ""
        else:
            logger.warning("⚠️ Failed to copy to clipboard")
            return ""
    
    def is_available(self) -> bool:
        """Check if clipboard is available."""
        from scripts import clipboard
        
        return clipboard.is_clipboard_available()
    
    def get_default_model(self) -> str:
        """Get default model (manual mode)."""
        return "manual"
    
    def list_models(self) -> list[str]:
        """List models (manual mode has no specific models)."""
        return ["manual"]


# Provider Registry
PROVIDERS: Dict[str, type[LLMProvider]] = {
    "gemini": GeminiProvider,
    "gemini-cli": GeminiCLIProvider,
    "gh-copilot": CopilotCLIProvider,
    "copilot": ManualCopilotProvider,
}


def get_provider(name: str) -> LLMProvider:
    """Get an LLM provider by name.
    
    Args:
        name: Provider name (gemini, gh-copilot, copilot)
        
    Returns:
        Instantiated LLM provider
        
    Raises:
        ValueError: If provider name is unknown
    """
    provider_class = PROVIDERS.get(name)
    if not provider_class:
        available = ", ".join(PROVIDERS.keys())
        raise ValueError(
            f"Unknown LLM provider: {name}. "
            f"Available providers: {available}"
        )
    
    return provider_class()


def list_available_providers() -> Dict[str, Dict[str, Any]]:
    """List all providers and their availability status.
    
    Returns:
        Dictionary mapping provider names to their status info
    """
    result = {}
    
    for name, provider_class in PROVIDERS.items():
        provider = provider_class()
        result[name] = {
            "available": provider.is_available(),
            "default_model": provider.get_default_model(),
            "models": provider.list_models()
        }
    
    return result
