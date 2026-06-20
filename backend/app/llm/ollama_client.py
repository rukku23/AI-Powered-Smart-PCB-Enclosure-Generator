"""
EnclosureAI — Ollama Client
Concrete LLM implementation using Ollama local inference.
Uses httpx async client against OLLAMA_BASE_URL/api/chat.
"""
from __future__ import annotations

import json
import logging
import os
from typing import AsyncIterator

import httpx

from app.llm.interface import LLMInterface

logger = logging.getLogger("enclosureai.llm.ollama")

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5-coder:1.5b"


class OllamaClient(LLMInterface):
    """Ollama local inference client with streaming support."""

    def __init__(self):
        self._base_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self._model = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
        self._timeout = httpx.Timeout(120.0, connect=10.0)
        logger.info(f"Ollama client initialized: {self._base_url}, model={self._model}")

    def _build_payload(self, messages: list[dict], stream: bool = False) -> dict:
        """Build Ollama API payload from messages."""
        ollama_msgs = []
        for msg in messages:
            ollama_msgs.append({
                "role": msg["role"],
                "content": msg["content"],
            })
        return {
            "model": self._model,
            "messages": ollama_msgs,
            "stream": stream,
            "options": {
                "temperature": 0.3,
                "num_predict": 4096,
            },
        }

    async def generate(self, messages: list[dict]) -> str:
        """Generate complete response from Ollama."""
        payload = self._build_payload(messages, stream=False)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                text = data.get("message", {}).get("content", "")
                logger.info(f"Ollama response: {len(text)} chars")
                return text

            except httpx.ConnectError:
                raise ConnectionError(
                    f"Cannot connect to Ollama at {self._base_url}. "
                    "Ensure Ollama is running: ollama serve"
                )
            except Exception as e:
                logger.error(f"Ollama API error: {e}")
                raise

    async def generate_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Stream response chunks from Ollama."""
        payload = self._build_payload(messages, stream=True)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/chat",
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            chunk = data.get("message", {}).get("content", "")
                            if chunk:
                                yield chunk
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue

            except httpx.ConnectError:
                raise ConnectionError(
                    f"Cannot connect to Ollama at {self._base_url}."
                )
            except Exception as e:
                logger.error(f"Ollama streaming error: {e}")
                raise
