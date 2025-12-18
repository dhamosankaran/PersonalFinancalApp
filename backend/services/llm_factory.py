"""
LLM Factory Service.
Provides a unified interface for switching between OpenAI and Gemini LLMs.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, Literal

from langchain_core.language_models.chat_models import BaseChatModel

from config import settings

# Config file path for persisting LLM provider selection
CONFIG_FILE = Path(__file__).parent.parent / "data" / "llm_config.json"

LLMProvider = Literal["openai", "gemini"]


class LLMFactory:
    """Factory for creating and managing LLM instances."""
    
    def __init__(self):
        """Initialize the LLM factory."""
        self._current_provider: Optional[str] = None
        self._llm_cache: Dict[str, BaseChatModel] = {}
        
        # Ensure data directory exists
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Load persisted provider selection
        self._load_config()
    
    def _load_config(self):
        """Load provider configuration from file."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self._current_provider = config.get("provider", settings.llm_provider)
            except Exception:
                self._current_provider = settings.llm_provider
        else:
            self._current_provider = settings.llm_provider
    
    def _save_config(self):
        """Save provider configuration to file."""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({"provider": self._current_provider}, f)
        except Exception as e:
            print(f"Warning: Could not save LLM config: {e}")
    
    def get_current_provider(self) -> str:
        """Get the current LLM provider name."""
        return self._current_provider or settings.llm_provider
    
    def get_model_name(self) -> str:
        """Get the current model name for the active provider."""
        provider = self.get_current_provider()
        if provider == "gemini":
            return "gemini-2.0-flash"
        elif provider == "openai":
            return "gpt-4o-mini"
        return "unknown"
    
    def set_provider(self, provider: LLMProvider) -> bool:
        """
        Set the LLM provider.
        
        Args:
            provider: "openai" or "gemini"
            
        Returns:
            True if successful, False otherwise
        """
        if provider not in ("openai", "gemini"):
            return False
        
        self._current_provider = provider
        self._save_config()
        
        # Clear cache to force recreation with new provider
        self._llm_cache.clear()
        
        return True
    
    def get_provider_status(self) -> Dict[str, Any]:
        """
        Get status of all LLM providers.
        
        Returns:
            Dictionary with provider status information
        """
        return {
            "current_provider": self.get_current_provider(),
            "providers": {
                "openai": {
                    "configured": bool(settings.openai_api_key),
                    "model": "gpt-4o-mini",
                    "available": bool(settings.openai_api_key)
                },
                "gemini": {
                    "configured": bool(settings.gemini_api_key),
                    "model": "gemini-2.0-flash",
                    "available": bool(settings.gemini_api_key)
                }
            }
        }
    
    def get_llm(self, temperature: float = 0) -> Optional[BaseChatModel]:
        """
        Get an LLM instance based on current provider configuration.
        
        Args:
            temperature: Temperature for generation (0 = deterministic)
            
        Returns:
            LangChain chat model or None if not configured
        """
        provider = self.get_current_provider()
        
        # Check cache
        cache_key = f"{provider}_{temperature}"
        if cache_key in self._llm_cache:
            return self._llm_cache[cache_key]
        
        llm = None
        
        if provider == "gemini" and settings.gemini_api_key:
            llm = self._create_gemini_llm(temperature)
        elif provider == "openai" and settings.openai_api_key:
            llm = self._create_openai_llm(temperature)
        # Fallback: try the other provider if primary isn't configured
        elif provider == "gemini" and settings.openai_api_key:
            llm = self._create_openai_llm(temperature)
        elif provider == "openai" and settings.gemini_api_key:
            llm = self._create_gemini_llm(temperature)
        
        if llm:
            self._llm_cache[cache_key] = llm
        
        return llm
    
    def _create_openai_llm(self, temperature: float) -> Optional[BaseChatModel]:
        """Create an OpenAI LLM instance."""
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model="gpt-4o-mini",
                temperature=temperature,
                api_key=settings.openai_api_key
            )
        except Exception as e:
            print(f"Error creating OpenAI LLM: {e}")
            return None
    
    def _create_gemini_llm(self, temperature: float) -> Optional[BaseChatModel]:
        """Create a Gemini LLM instance."""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                temperature=temperature,
                google_api_key=settings.gemini_api_key
            )
        except Exception as e:
            print(f"Error creating Gemini LLM: {e}")
            return None
    
    def get_raw_client(self):
        """
        Get a raw API client for the current provider.
        Useful for non-LangChain usage (e.g., categorizer).
        
        Returns:
            OpenAI client or Gemini GenerativeModel, or None
        """
        provider = self.get_current_provider()
        
        if provider == "gemini" and settings.gemini_api_key:
            return self._create_gemini_client()
        elif provider == "openai" and settings.openai_api_key:
            return self._create_openai_client()
        # Fallback
        elif settings.gemini_api_key:
            return self._create_gemini_client()
        elif settings.openai_api_key:
            return self._create_openai_client()
        
        return None
    
    def _create_openai_client(self):
        """Create raw OpenAI client."""
        try:
            from openai import OpenAI
            return OpenAI(api_key=settings.openai_api_key)
        except Exception:
            return None
    
    def _create_gemini_client(self):
        """Create raw Gemini client."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            return genai.GenerativeModel("gemini-2.0-flash")
        except Exception:
            return None


# Global singleton instance
llm_factory = LLMFactory()
