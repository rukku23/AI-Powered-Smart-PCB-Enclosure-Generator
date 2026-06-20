from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import AsyncIterator

from app.llm.few_shot_library import (
    ESP32_SCAD_OUTPUT,
    ARDUINO_SCAD_OUTPUT,
    CUSTOM_SCAD_OUTPUT,
)


class LLMInterface(ABC):

    @abstractmethod
    async def generate(self, messages: list[dict]) -> str:
        pass

    @abstractmethod
    async def generate_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        pass


class TemplateClient(LLMInterface):

    async def generate(self, messages):

        prompt = str(messages)

        # Large custom board
        if "100.0" in prompt or "100" in prompt:
            return CUSTOM_SCAD_OUTPUT
            

        # Arduino-sized board
        elif "85.6" in prompt or "85" in prompt:
            return CUSTOM_SCAD_OUTPUT

        elif "68.6" in prompt or "68" in prompt:
             return ARDUINO_SCAD_OUTPUT

        # Default ESP32
        else:
            return ESP32_SCAD_OUTPUT

    async def generate_stream(self, messages):

        result = await self.generate(messages)
        yield result


class FallbackClient(LLMInterface):
    """Tries primary client, falls back to secondary on connection errors."""
    def __init__(self, primary: LLMInterface, secondary: LLMInterface):
        self.primary = primary
        self.secondary = secondary

    async def generate(self, messages: list[dict]) -> str:
        try:
            return await self.primary.generate(messages)
        except Exception as e:
            # We catch any connection or API errors and fallback
            import logging
            logger = logging.getLogger("enclosureai.llm.fallback")
            logger.warning(f"Primary LLM failed: {e}. Falling back to secondary.")
            return await self.secondary.generate(messages)

    async def generate_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        try:
            async for chunk in self.primary.generate_stream(messages):
                yield chunk
        except Exception as e:
            import logging
            logger = logging.getLogger("enclosureai.llm.fallback")
            logger.warning(f"Primary LLM stream failed: {e}. Falling back to secondary.")
            async for chunk in self.secondary.generate_stream(messages):
                yield chunk


def llm_factory(provider: str | None = None):

    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "glm_fallback").lower()

    if provider == "template":
        return TemplateClient()

    elif provider == "claude":
        from app.llm.claude_client import ClaudeClient
        return ClaudeClient()

    elif provider == "ollama":
        from app.llm.ollama_client import OllamaClient
        return OllamaClient()

    elif provider == "glm":
        from app.llm.glm_client import GLMClient
        return GLMClient()

    elif provider == "glm_fallback":
        from app.llm.glm_client import GLMClient
        from app.llm.ollama_client import OllamaClient
        try:
            primary = GLMClient()
        except ValueError:
            # If NVIDIA_API_KEY is not set, just use Ollama directly
            return OllamaClient()
        return FallbackClient(primary=primary, secondary=OllamaClient())

    else:
        raise ValueError(f"Unknown provider: {provider}")