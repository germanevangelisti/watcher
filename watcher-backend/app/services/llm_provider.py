"""
LLM Provider Abstraction

Provides a unified interface for multiple LLM providers (Google Gemini, Anthropic).
Allows easy switching between providers via configuration.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class LLMProviderType(str, Enum):
    """Supported LLM providers"""
    GOOGLE = "google"
    ANTHROPIC = "anthropic"


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate_text(
        self, 
        prompt: str, 
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate text from a prompt"""
        pass
    
    @abstractmethod
    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from a conversation history"""
        pass


class GoogleGeminiProvider(LLMProvider):
    """Google Gemini LLM provider"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        """
        Initialize Google Gemini provider
        
        Args:
            api_key: Google API key (reads from GOOGLE_API_KEY env var if not provided)
            model: Model name (default: gemini-2.0-flash)
        """
        try:
            import google.generativeai as genai
            
            self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
            if not self.api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment or parameters")
            
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(model)
            self.model_name = model
            
            logger.info(f"Google Gemini provider initialized with model: {model}")
            
        except ImportError:
            raise ImportError("google-generativeai not installed. Install with: pip install google-generativeai")
    
    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate text from a prompt using Gemini"""
        import asyncio
        import google.generativeai as genai
        
        # Combine system prompt and user prompt
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        response = await asyncio.to_thread(
            self.model.generate_content,
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
        )
        
        return response.text.strip()
    
    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from conversation history using Gemini"""
        import asyncio
        import google.generativeai as genai
        
        # Convert messages to Gemini format
        conversation_text = "\n\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in messages
        ])
        
        response = await asyncio.to_thread(
            self.model.generate_content,
            conversation_text,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
        )
        
        return response.text.strip()


class AnthropicProvider(LLMProvider):
    """Anthropic Claude LLM provider"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize Anthropic provider
        
        Args:
            api_key: Anthropic API key (reads from ANTHROPIC_API_KEY env var if not provided)
            model: Model name (default: claude-3-5-sonnet-20241022)
        """
        try:
            import anthropic
            
            self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment or parameters")
            
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
            self.model_name = model
            
            logger.info(f"Anthropic provider initialized with model: {model}")
            
        except ImportError:
            raise ImportError("anthropic not installed. Install with: pip install anthropic")
    
    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate text from a prompt using Claude"""
        
        # Build messages
        messages = [{"role": "user", "content": prompt}]
        
        # Create message with optional system prompt
        kwargs = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        response = await self.client.messages.create(**kwargs)
        
        return response.content[0].text.strip()
    
    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from conversation history using Claude"""
        
        # Extract system message if present
        system_prompt = None
        chat_messages = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system_prompt = msg['content']
            else:
                chat_messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })
        
        # Create message
        kwargs = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": chat_messages
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        response = await self.client.messages.create(**kwargs)
        
        return response.content[0].text.strip()


class LLMProviderFactory:
    """Factory for creating LLM providers"""
    
    @staticmethod
    def create_provider(
        provider_type: LLMProviderType = LLMProviderType.GOOGLE,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ) -> LLMProvider:
        """
        Create an LLM provider instance
        
        Args:
            provider_type: Type of provider (google or anthropic)
            api_key: API key (optional, reads from env var if not provided)
            model: Model name (optional, uses default if not provided)
        
        Returns:
            LLMProvider instance
        
        Raises:
            ValueError: If provider type is not supported
        """
        if provider_type == LLMProviderType.GOOGLE:
            return GoogleGeminiProvider(api_key=api_key, model=model or "gemini-2.0-flash")
        elif provider_type == LLMProviderType.ANTHROPIC:
            return AnthropicProvider(api_key=api_key, model=model or "claude-3-5-sonnet-20241022")
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")
    
    @staticmethod
    def create_from_env() -> LLMProvider:
        """
        Create an LLM provider based on environment configuration
        
        Reads LLM_PROVIDER environment variable (default: google)
        Reads LLM_MODEL environment variable for model selection
        
        Returns:
            LLMProvider instance
        """
        provider_str = os.getenv("LLM_PROVIDER", "google").lower()
        model = os.getenv("LLM_MODEL", None)  # None = use provider default
        
        try:
            provider_type = LLMProviderType(provider_str)
        except ValueError:
            logger.warning(f"Invalid LLM_PROVIDER '{provider_str}', defaulting to Google")
            provider_type = LLMProviderType.GOOGLE
        
        return LLMProviderFactory.create_provider(provider_type, model=model)


# Convenience function for quick access
def get_llm_provider(
    provider_type: Optional[LLMProviderType] = None
) -> LLMProvider:
    """
    Get an LLM provider instance
    
    Args:
        provider_type: Optional provider type. If not specified, reads from LLM_PROVIDER env var
    
    Returns:
        LLMProvider instance
    """
    if provider_type:
        return LLMProviderFactory.create_provider(provider_type)
    else:
        return LLMProviderFactory.create_from_env()
