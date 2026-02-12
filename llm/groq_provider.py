"""Groq API sağlayıcısı - OpenAI uyumlu API üzerinden LLM erişimi."""

import json
import logging
from typing import Generator

import httpx

from config.settings import Settings
from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


class GroqProvider(BaseLLMProvider):
    """Groq API üzerinden LLM erişimi sağlayan sınıf."""

    def __init__(self):
        settings = Settings()
        self._api_key = settings.groq_api_key
        self._base_url = settings.groq_base_url.rstrip("/")
        self._model = settings.groq_model
        self._temperature = settings.temperature
        self._max_tokens = settings.max_tokens
        self._client = httpx.Client(timeout=60.0)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self, messages: list[dict], tools: list[dict] | None = None, stream: bool = False
    ) -> dict:
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        return payload

    def _handle_error_response(self, response: httpx.Response) -> None:
        status = response.status_code
        try:
            body = response.json()
            detail = body.get("error", {}).get("message", response.text)
        except (json.JSONDecodeError, ValueError):
            detail = response.text

        if status == 401:
            raise PermissionError(f"Groq kimlik doğrulama hatası: {detail}")
        if status == 429:
            raise RuntimeError(f"Groq istek limiti aşıldı: {detail}")
        if status >= 500:
            raise ConnectionError(f"Groq sunucu hatası ({status}): {detail}")
        raise RuntimeError(f"Groq API hatası ({status}): {detail}")

    def _parse_response(self, data: dict) -> dict:
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        return {
            "content": message.get("content"),
            "tool_calls": message.get("tool_calls"),
            "usage": data.get("usage", {}),
            "finish_reason": choice.get("finish_reason"),
        }

    def chat_completion(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        if not self._api_key:
            raise PermissionError("Groq API anahtarı ayarlanmamış")

        payload = self._build_payload(messages, tools, stream=False)

        try:
            response = self._client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
        except httpx.ConnectError as exc:
            raise ConnectionError(f"Groq'a bağlanılamadı: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise ConnectionError(f"Groq isteği zaman aşımına uğradı: {exc}") from exc

        if response.status_code != 200:
            self._handle_error_response(response)

        return self._parse_response(response.json())

    def stream_completion(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> Generator[dict, None, None]:
        if not self._api_key:
            raise PermissionError("Groq API anahtarı ayarlanmamış")

        payload = self._build_payload(messages, tools, stream=True)

        try:
            with self._client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as response:
                if response.status_code != 200:
                    response.read()
                    self._handle_error_response(response)

                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[len("data: "):]
                    if data_str.strip() == "[DONE]":
                        yield {"content": None, "tool_calls": None, "done": True}
                        return

                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        logger.warning("Groq SSE JSON ayrıştırma hatası: %s", data_str)
                        continue

                    choice = data.get("choices", [{}])[0]
                    delta = choice.get("delta", {})
                    yield {
                        "content": delta.get("content"),
                        "tool_calls": delta.get("tool_calls"),
                        "done": choice.get("finish_reason") is not None,
                    }

        except httpx.ConnectError as exc:
            raise ConnectionError(f"Groq'a bağlanılamadı: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise ConnectionError(f"Groq isteği zaman aşımına uğradı: {exc}") from exc

    def get_available_models(self) -> list[str]:
        if not self._api_key:
            raise PermissionError("Groq API anahtarı ayarlanmamış")

        try:
            response = self._client.get(
                f"{self._base_url}/models",
                headers=self._headers(),
            )
        except httpx.ConnectError as exc:
            raise ConnectionError(f"Groq'a bağlanılamadı: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise ConnectionError(f"Groq isteği zaman aşımına uğradı: {exc}") from exc

        if response.status_code != 200:
            self._handle_error_response(response)

        data = response.json()
        models = data.get("data", [])
        return sorted([m["id"] for m in models if "id" in m])

    def set_model(self, model_name: str) -> None:
        self._model = model_name
        logger.info("Groq modeli değiştirildi: %s", model_name)

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
