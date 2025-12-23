"""Tests for LLM Strategy Pattern."""

import pytest
from scripts.llm_strategy import (
    LLMProvider,
    GeminiProvider,
    CopilotCLIProvider,
    ManualCopilotProvider,
    get_provider,
    list_available_providers,
    PROVIDERS
)


class TestLLMProviderInterface:
    """Test the LLMProvider abstract interface."""
    
    def test_cannot_instantiate_abstract_class(self):
        """LLMProvider is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            LLMProvider()


class TestGeminiProvider:
    """Test Gemini API provider."""
    
    def test_initialization(self):
        """GeminiProvider can be instantiated."""
        provider = GeminiProvider()
        assert isinstance(provider, LLMProvider)
    
    def test_get_default_model(self):
        """Default model is gemini-2.0-flash-exp."""
        provider = GeminiProvider()
        assert provider.get_default_model() == "gemini-2.0-flash-exp"
    
    def test_list_models(self):
        """List of models includes expected models."""
        provider = GeminiProvider()
        models = provider.list_models()
        
        assert isinstance(models, list)
        assert len(models) > 0
        assert "gemini-2.0-flash-exp" in models
        assert "gemini-1.5-pro" in models
    
    def test_is_available_without_key(self, monkeypatch):
        """Provider is not available without GEMINI_API_KEY."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        
        provider = GeminiProvider()
        assert provider.is_available() is False
    
    def test_is_available_with_key(self, monkeypatch):
        """Provider is available with GEMINI_API_KEY set."""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
        
        provider = GeminiProvider()
        assert provider.is_available() is True


class TestCopilotCLIProvider:
    """Test GitHub Copilot CLI provider."""
    
    def test_initialization(self):
        """CopilotCLIProvider can be instantiated."""
        provider = CopilotCLIProvider()
        assert isinstance(provider, LLMProvider)
    
    def test_get_default_model(self):
        """Default model is gpt-4."""
        provider = CopilotCLIProvider()
        assert provider.get_default_model() == "gpt-4"
    
    def test_list_models(self):
        """List of models includes known Copilot models."""
        provider = CopilotCLIProvider()
        models = provider.list_models()
        
        assert isinstance(models, list)
        assert len(models) > 0
        assert "gpt-4" in models
        assert "claude-sonnet-4.5" in models


class TestManualCopilotProvider:
    """Test manual Copilot provider (clipboard mode)."""
    
    def test_initialization(self):
        """ManualCopilotProvider can be instantiated."""
        provider = ManualCopilotProvider()
        assert isinstance(provider, LLMProvider)
    
    def test_get_default_model(self):
        """Default model is 'manual'."""
        provider = ManualCopilotProvider()
        assert provider.get_default_model() == "manual"
    
    def test_list_models(self):
        """Model list contains 'manual'."""
        provider = ManualCopilotProvider()
        models = provider.list_models()
        
        assert models == ["manual"]


class TestProviderRegistry:
    """Test provider registry and factory functions."""
    
    def test_provider_registry_has_expected_providers(self):
        """Provider registry contains expected providers."""
        assert "gemini" in PROVIDERS
        assert "gh-copilot" in PROVIDERS
        assert "copilot" in PROVIDERS
    
    def test_get_provider_gemini(self):
        """get_provider returns GeminiProvider for 'gemini'."""
        provider = get_provider("gemini")
        assert isinstance(provider, GeminiProvider)
    
    def test_get_provider_copilot_cli(self):
        """get_provider returns CopilotCLIProvider for 'gh-copilot'."""
        provider = get_provider("gh-copilot")
        assert isinstance(provider, CopilotCLIProvider)
    
    def test_get_provider_manual_copilot(self):
        """get_provider returns ManualCopilotProvider for 'copilot'."""
        provider = get_provider("copilot")
        assert isinstance(provider, ManualCopilotProvider)
    
    def test_get_provider_unknown_raises_error(self):
        """get_provider raises ValueError for unknown provider."""
        with pytest.raises(ValueError) as exc_info:
            get_provider("unknown-provider")
        
        assert "Unknown LLM provider" in str(exc_info.value)
        assert "unknown-provider" in str(exc_info.value)
    
    def test_list_available_providers(self):
        """list_available_providers returns status for all providers."""
        providers = list_available_providers()
        
        assert isinstance(providers, dict)
        assert "gemini" in providers
        assert "gh-copilot" in providers
        assert "copilot" in providers
        
        # Each provider should have expected keys
        for provider_info in providers.values():
            assert "available" in provider_info
            assert "default_model" in provider_info
            assert "models" in provider_info
            assert isinstance(provider_info["available"], bool)
            assert isinstance(provider_info["models"], list)


class TestProviderExtensibility:
    """Test that the Strategy Pattern makes it easy to add new providers."""
    
    def test_can_add_new_provider_to_registry(self):
        """New providers can be added to the registry."""
        
        class CustomProvider(LLMProvider):
            def call(self, prompt: str, **kwargs) -> str:
                return "custom response"
            
            def is_available(self) -> bool:
                return True
            
            def get_default_model(self) -> str:
                return "custom-model"
            
            def list_models(self) -> list[str]:
                return ["custom-model"]
        
        # Add to registry (in real code, this would be in the module)
        PROVIDERS["custom"] = CustomProvider
        
        # Should be able to get the provider
        provider = get_provider("custom")
        assert isinstance(provider, CustomProvider)
        
        # Cleanup
        del PROVIDERS["custom"]
