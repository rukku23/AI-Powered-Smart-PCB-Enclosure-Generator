"""
EnclosureAI — GLM 4.7 Client via Nvidia API
"""
from __future__ import annotations

import logging
import os
from typing import AsyncIterator

from openai import AsyncOpenAI
# pyrefly: ignore [missing-import]
import httpx

from app.llm.interface import LLMInterface

logger = logging.getLogger("enclosureai.llm.glm")

class GLMClient(LLMInterface):
    """GLM 4.7 async client via integrate.api.nvidia.com."""

    def __init__(self):
        self._api_key = os.getenv("NVIDIA_API_KEY")
        if not self._api_key:
            raise ValueError("NVIDIA_API_KEY environment variable is not set")
            
        self.client = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=self._api_key
        )
        self.model = "z-ai/glm4.7"
        logger.info(f"GLM client initialized: model={self.model}")

    async def generate(self, messages: list[dict]) -> str:
        """Generate complete response from GLM."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=1,
            top_p=1,
            max_tokens=8192,
            extra_body={"chat_template_kwargs":{"enable_thinking":True,"clear_thinking":False}},
            stream=False
        )
        
        choice = response.choices[0]
        content = choice.message.content or ""
        reasoning = getattr(choice.message, "reasoning_content", None)
        
        if reasoning:
            content = f"/* === ENCLOSUREAI DESIGN REASONING ===\n{reasoning}\n======================================= */\n\n{content}"
            
        return content

    async def generate_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Stream response chunks from GLM."""
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=1,
            top_p=1,
            max_tokens=8192,
            extra_body={"chat_template_kwargs":{"enable_thinking":True,"clear_thinking":False}},
            stream=True
        )

        reasoning_started = False
        
        async for chunk in stream:
            if not getattr(chunk, "choices", None):
                continue
            if len(chunk.choices) == 0 or getattr(chunk.choices[0], "delta", None) is None:
                continue
                
            delta = chunk.choices[0].delta
            
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                if not reasoning_started:
                    yield "/* === ENCLOSUREAI DESIGN REASONING ===\n"
                    reasoning_started = True
                yield reasoning
            
            content = getattr(delta, "content", None)
            if content is not None:
                if reasoning_started:
                    yield "\n======================================= */\n\n"
                    reasoning_started = False
                yield content
