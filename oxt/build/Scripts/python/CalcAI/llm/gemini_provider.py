"""Google Gemini API sağlayıcısı - Gemini LLM erişimi sağlar."""

import json
import logging
import re
import time
from typing import Generator

import httpx

from config.settings import Settings
from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

# Rate limit için maksimum retry sayısı ve bekleme süresi
MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 30  # saniye


class GeminiProvider(BaseLLMProvider):
    """Gemini API üzerinden LLM erişimi sağlayan sınıf."""

    def __init__(self):
        settings = Settings()
        self._api_key = settings.gemini_api_key
        self._base_url = settings.gemini_base_url.rstrip("/")
        self._model = settings.gemini_model
        self._temperature = settings.temperature
        self._max_tokens = settings.max_tokens
        self._client = httpx.Client(timeout=60.0)

    def _build_contents(self, messages: list[dict]) -> list[dict]:
        """OpenAI tarzı mesajları Gemini contents'e dönüştürür."""
        contents = []
        system_prefix = ""
        if messages and messages[0].get("role") == "system":
            system_prefix = messages[0].get("content", "")

        for m in messages[1:]:
            role = m.get("role")
            content = m.get("content")
            if content is None:
                continue
            if role == "user":
                text = content
                if system_prefix:
                    text = f"{system_prefix}\n\n{content}"
                    system_prefix = ""
                contents.append({
                    "role": "user",
                    "parts": [{"text": text}],
                })
            elif role == "assistant":
                contents.append({
                    "role": "model",
                    "parts": [{"text": content}],
                })

        if system_prefix:
            contents.insert(0, {
                "role": "user",
                "parts": [{"text": system_prefix}],
            })

        return contents

    def _parse_retry_delay(self, response_text: str) -> float:
        """Hata mesajından retry süresini çıkarır."""
        match = re.search(r"retry in ([\d.]+)s", response_text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return DEFAULT_RETRY_DELAY

    def _make_request(self, url: str, payload: dict, retry_count: int = 0) -> httpx.Response:
        """API isteği yapar, rate limit durumunda otomatik retry uygular."""
        try:
            response = self._client.post(url, params={"key": self._api_key}, json=payload)
        except httpx.ConnectError as exc:
            raise ConnectionError(f"Gemini'ye bağlanılamadı: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise ConnectionError(f"Gemini isteği zaman aşımına uğradı: {exc}") from exc

        # Rate limit hatası (429)
        if response.status_code == 429:
            if retry_count >= MAX_RETRIES:
                raise RuntimeError(
                    f"Gemini API kota limiti aşıldı. {MAX_RETRIES} deneme sonrası başarısız.\n"
                    "Lütfen birkaç dakika bekleyin veya ücretli plana geçin."
                )

            retry_delay = self._parse_retry_delay(response.text)
            logger.warning(
                "Gemini rate limit aşıldı. %d saniye sonra tekrar denenecek (deneme %d/%d)",
                int(retry_delay), retry_count + 1, MAX_RETRIES
            )
            time.sleep(retry_delay)
            return self._make_request(url, payload, retry_count + 1)

        return response

    def chat_completion(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        if not self._api_key:
            raise PermissionError("Gemini API anahtarı ayarlanmamış")

        payload = {
            "contents": self._build_contents(messages),
            "generationConfig": {
                "temperature": self._temperature,
                "maxOutputTokens": self._max_tokens,
            },
        }

        url = f"{self._base_url}/models/{self._model}:generateContent"
        response = self._make_request(url, payload)

        if response.status_code != 200:
            raise RuntimeError(f"Gemini API hatası ({response.status_code}): {response.text}")

        data = response.json()
        candidates = data.get("candidates", [])
        content = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                content = parts[0].get("text", "")

        return {
            "content": content,
            "tool_calls": None,
            "usage": {},
            "finish_reason": "stop",
        }

    def stream_completion(self, messages: list[dict], tools: list[dict] | None = None) -> Generator[dict, None, None]:
        """Stream desteklenmiyor; tek parça döndürür."""
        result = self.chat_completion(messages, tools=None)
        yield {"content": result.get("content"), "tool_calls": None, "done": True}

    def _make_get_request(self, url: str, retry_count: int = 0) -> httpx.Response:
        """GET isteği yapar, rate limit durumunda otomatik retry uygular."""
        try:
            response = self._client.get(url, params={"key": self._api_key})
        except httpx.ConnectError as exc:
            raise ConnectionError(f"Gemini'ye bağlanılamadı: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise ConnectionError(f"Gemini isteği zaman aşımına uğradı: {exc}") from exc

        if response.status_code == 429:
            if retry_count >= MAX_RETRIES:
                raise RuntimeError(
                    f"Gemini API kota limiti aşıldı. {MAX_RETRIES} deneme sonrası başarısız.\n"
                    "Lütfen birkaç dakika bekleyin veya ücretli plana geçin."
                )

            retry_delay = self._parse_retry_delay(response.text)
            logger.warning(
                "Gemini rate limit aşıldı. %d saniye sonra tekrar denenecek (deneme %d/%d)",
                int(retry_delay), retry_count + 1, MAX_RETRIES
            )
            time.sleep(retry_delay)
            return self._make_get_request(url, retry_count + 1)

        return response

    def get_available_models(self) -> list[str]:
        if not self._api_key:
            raise PermissionError("Gemini API anahtarı ayarlanmamış")
        url = f"{self._base_url}/models"
        response = self._make_get_request(url)
        if response.status_code != 200:
            raise RuntimeError(f"Gemini API hatası ({response.status_code}): {response.text}")
        data = response.json()
        models = data.get("models", [])
        names = []
        for m in models:
            name = m.get("name", "")
            if name.startswith("models/"):
                name = name.split("/", 1)[1]
            if name:
                names.append(name)
        return names

    def set_model(self, model_name: str) -> None:
        self._model = model_name
        logger.info("Gemini modeli değiştirildi: %s", model_name)

    def close(self) -> None:
        """HTTP client'ı kapatır."""
        if self._client:
            self._client.close()
            self._client = None
