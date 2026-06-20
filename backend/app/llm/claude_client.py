"""
EnclosureAI — Claude API Client
Concrete LLM implementation using Anthropic Claude API.
Model: claude-sonnet-4-20250514, max_tokens: 4096.
Includes rate limit handling with exponential backoff.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import AsyncIterator

from app.llm.interface import LLMInterface

logger = logging.getLogger("enclosureai.llm.claude")

CLAUDE_MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096
MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds


class ClaudeClient(LLMInterface):
    """Anthropic Claude API client with streaming and retry support."""

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required for Claude provider"
            )
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
        except ImportError:
            raise ImportError("anthropic package required: pip install anthropic")

        self._model = os.getenv("CLAUDE_MODEL", CLAUDE_MODEL)
        self._max_tokens = int(os.getenv("CLAUDE_MAX_TOKENS", str(MAX_TOKENS)))
        logger.info(f"Claude client initialized: model={self._model}")

    def _split_messages(self, messages: list[dict]) -> tuple[str, list[dict]]:
        """Split system message from conversation messages."""
        system = ""
        conversation = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                conversation.append({"role": msg["role"], "content": msg["content"]})
        return system, conversation

    async def generate(self, messages: list[dict]) -> str:
        """Generate complete response with exponential backoff retry."""
        system, conversation = self._split_messages(messages)

        for attempt in range(MAX_RETRIES):
            try:
                response = await self._client.messages.create(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    system=system,
                    messages=conversation,
                )
                text = response.content[0].text
                logger.info(
                    f"Claude response: {len(text)} chars, "
                    f"tokens: {response.usage.input_tokens}in/{response.usage.output_tokens}out"
                )
                return text

            except Exception as e:
                error_name = type(e).__name__
                if "rate" in str(e).lower() or "429" in str(e):
                    delay = BASE_DELAY * (2 ** attempt)
                    logger.warning(f"Rate limited (attempt {attempt+1}), retrying in {delay}s")
                    await asyncio.sleep(delay)
                    continue
                elif "overloaded" in str(e).lower() or "529" in str(e):
                    delay = BASE_DELAY * (2 ** attempt) * 2
                    logger.warning(f"API overloaded (attempt {attempt+1}), retrying in {delay}s")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"Claude API error: {error_name}: {e}")
                    raise

        raise RuntimeError(f"Claude API failed after {MAX_RETRIES} retries")

    async def generate_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Stream response chunks using Claude streaming API."""
        system, conversation = self._split_messages(messages)

        try:
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=conversation,
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Claude streaming error: {e}")
            raise
