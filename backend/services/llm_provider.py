"""
LLM Provider Service - MCP-inspired model switching.
Provides a unified interface for multiple LLM providers (OpenAI, Gemini).
Implements Model Context Protocol patterns for standardized tool use.
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
from langchain_core.messages import HumanMessage, SystemMessage
import logging

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """Supported model providers."""
    OPENAI = "openai"
    GEMINI = "gemini"


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    provider: ModelProvider
    model_name: str
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    
    
@dataclass 
class LLMResponse:
    """Standardized response from any LLM provider."""
    content: str
    model: str
    provider: ModelProvider
    usage: Dict[str, int]
    latency_ms: float
    raw_response: Optional[Any] = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is configured and available."""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> ModelProvider:
        """Return the provider type."""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self._llm = None
        
        if api_key:
            from langchain_openai import ChatOpenAI
            self._llm = ChatOpenAI(
                model=model,
                temperature=0,
                api_key=api_key
            )
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        if not self._llm:
            raise RuntimeError("OpenAI provider is not configured")
        
        start_time = time.perf_counter()
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await self._llm.ainvoke(messages)
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Estimate tokens (rough approximation)
        input_tokens = len(system_prompt + user_prompt) // 4
        output_tokens = len(response.content) // 4
        
        return LLMResponse(
            content=response.content,
            model=self.model,
            provider=ModelProvider.OPENAI,
            usage={
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            },
            latency_ms=latency_ms,
            raw_response=response
        )
    
    def is_available(self) -> bool:
        return bool(self.api_key and self._llm)
    
    @property
    def provider_name(self) -> ModelProvider:
        return ModelProvider.OPENAI


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider."""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
        self._client = None
        
        if api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self._client = genai.GenerativeModel(model)
                logger.info(f"Gemini provider initialized with model: {model}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini provider: {e}")
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        if not self._client:
            raise RuntimeError("Gemini provider is not configured")
        
        start_time = time.perf_counter()
        
        # Combine system and user prompt for Gemini
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # Gemini's generate_content is synchronous, so we wrap it
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: self._client.generate_content(full_prompt)
        )
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        content = response.text if hasattr(response, 'text') else str(response)
        
        # Estimate tokens
        input_tokens = len(full_prompt) // 4
        output_tokens = len(content) // 4
        
        return LLMResponse(
            content=content,
            model=self.model,
            provider=ModelProvider.GEMINI,
            usage={
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            },
            latency_ms=latency_ms,
            raw_response=response
        )
    
    def is_available(self) -> bool:
        return bool(self.api_key and self._client)
    
    @property
    def provider_name(self) -> ModelProvider:
        return ModelProvider.GEMINI


class LLMProviderManager:
    """
    MCP-inspired manager for LLM providers.
    Handles provider registration, switching, and unified access.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._providers: Dict[ModelProvider, BaseLLMProvider] = {}
        self._active_provider: Optional[ModelProvider] = None
        self._initialized = True
        
    def register_provider(self, provider: BaseLLMProvider):
        """Register an LLM provider."""
        self._providers[provider.provider_name] = provider
        logger.info(f"Registered LLM provider: {provider.provider_name.value}")
        
        # Set as active if it's the first available provider
        if self._active_provider is None and provider.is_available():
            self._active_provider = provider.provider_name
            logger.info(f"Set active provider to: {provider.provider_name.value}")
    
    def set_active_provider(self, provider: ModelProvider) -> bool:
        """Set the active provider."""
        if provider not in self._providers:
            logger.error(f"Provider {provider.value} is not registered")
            return False
            
        if not self._providers[provider].is_available():
            logger.error(f"Provider {provider.value} is not available")
            return False
            
        self._active_provider = provider
        logger.info(f"Active provider changed to: {provider.value}")
        return True
    
    def get_active_provider(self) -> Optional[BaseLLMProvider]:
        """Get the currently active provider."""
        if self._active_provider is None:
            return None
        return self._providers.get(self._active_provider)
    
    def get_active_provider_name(self) -> Optional[str]:
        """Get the name of the active provider."""
        return self._active_provider.value if self._active_provider else None
    
    def get_available_providers(self) -> List[Dict[str, Any]]:
        """Get list of available providers with their status."""
        providers = []
        for provider_type, provider in self._providers.items():
            providers.append({
                "name": provider_type.value,
                "available": provider.is_available(),
                "active": provider_type == self._active_provider,
                "model": getattr(provider, 'model', 'unknown')
            })
        return providers
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Generate response using the active provider."""
        provider = self.get_active_provider()
        if not provider:
            raise RuntimeError("No active LLM provider available")
        
        return await provider.generate(system_prompt, user_prompt, **kwargs)
    
    def is_available(self) -> bool:
        """Check if any provider is available."""
        return any(p.is_available() for p in self._providers.values())


# Global instance
llm_manager = LLMProviderManager()


def initialize_providers():
    """Initialize all LLM providers from config."""
    from config import settings
    
    # Register OpenAI provider
    if settings.openai_api_key:
        openai_provider = OpenAIProvider(
            api_key=settings.openai_api_key,
            model=getattr(settings, 'openai_model', 'gpt-4o-mini')
        )
        llm_manager.register_provider(openai_provider)
    
    # Register Gemini provider
    if hasattr(settings, 'gemini_api_key') and settings.gemini_api_key:
        gemini_provider = GeminiProvider(
            api_key=settings.gemini_api_key,
            model=getattr(settings, 'gemini_model', 'gemini-1.5-flash')
        )
        llm_manager.register_provider(gemini_provider)
    
    # Set default provider based on config
    if hasattr(settings, 'default_llm_provider'):
        try:
            provider = ModelProvider(settings.default_llm_provider)
            llm_manager.set_active_provider(provider)
        except ValueError:
            logger.warning(f"Unknown default provider: {settings.default_llm_provider}")
    
    return llm_manager
