"""OpenRouter API sağlayıcısı - OpenAI uyumlu API üzerinden LLM erişimi."""

import json
import logging
from typing import Generator

import httpx

from config.settings import Settings
from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter API üzerinden LLM erişimi sağlayan sınıf.

    OpenAI uyumlu chat/completions endpoint'ini kullanır.
    Araç çağrıları (function calling) desteklenir.
    """

    def __init__(self):
        """Ayarlardan API anahtarı, base URL ve model bilgisini yükler."""
        settings = Settings()
        self._api_key = settings.openrouter_api_key
        self._base_url = settings.openrouter_base_url.rstrip("/")
        self._model = settings.openrouter_model
        self._temperature = settings.temperature
        self._max_tokens = settings.max_tokens
        self._client = httpx.Client(timeout=60.0)

    def _headers(self) -> dict:
        """API istekleri için gerekli HTTP başlıklarını döndürür."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/libre-calc-ai-addon",
            "X-Title": "LibreCalc AI Assistant",
        }

    def _build_payload(
        self, messages: list[dict], tools: list[dict] | None = None, stream: bool = False
    ) -> dict:
        """API isteği için JSON gövdesini oluşturur."""
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
        """HTTP hata yanıtlarını uygun istisna mesajlarıyla yükseltir."""
        status = response.status_code
        try:
            body = response.json()
            detail = body.get("error", {}).get("message", response.text)
        except (json.JSONDecodeError, ValueError):
            detail = response.text

        if status == 401:
            raise PermissionError(f"OpenRouter kimlik doğrulama hatası: {detail}")
        elif status == 429:
            raise RuntimeError(f"OpenRouter istek limiti aşıldı: {detail}")
        elif status >= 500:
            raise ConnectionError(f"OpenRouter sunucu hatası ({status}): {detail}")
        else:
            raise RuntimeError(f"OpenRouter API hatası ({status}): {detail}")

    def _parse_response(self, data: dict) -> dict:
        """API yanıtını standart formata dönüştürür."""
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        return {
            "content": message.get("content"),
            "tool_calls": message.get("tool_calls"),
            "usage": data.get("usage", {}),
            "finish_reason": choice.get("finish_reason"),
        }

    def chat_completion(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> dict:
        """OpenRouter'a sohbet tamamlama isteği gönderir.

        Args:
            messages: Mesaj listesi.
            tools: Opsiyonel araç tanımları.

        Returns:
            Standart formatta yanıt sözlüğü.

        Raises:
            PermissionError: API anahtarı geçersizse.
            RuntimeError: İstek limiti aşıldıysa veya diğer API hataları.
            ConnectionError: Sunucu hatası veya bağlantı sorunu.
        """
        if not self._api_key:
            raise PermissionError("OpenRouter API anahtarı ayarlanmamış")

        payload = self._build_payload(messages, tools, stream=False)

        try:
            response = self._client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
        except httpx.ConnectError as exc:
            raise ConnectionError(f"OpenRouter'a bağlanılamadı: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise ConnectionError(f"OpenRouter isteği zaman aşımına uğradı: {exc}") from exc

        if response.status_code != 200:
            self._handle_error_response(response)

        return self._parse_response(response.json())

    def stream_completion(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> Generator[dict, None, None]:
        """Akış modunda sohbet tamamlama isteği gönderir (SSE).

        Args:
            messages: Mesaj listesi.
            tools: Opsiyonel araç tanımları.

        Yields:
            Her SSE parçası için sözlük.
        """
        if not self._api_key:
            raise PermissionError("OpenRouter API anahtarı ayarlanmamış")

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
                        logger.warning("SSE JSON ayrıştırma hatası: %s", data_str)
                        continue

                    choice = data.get("choices", [{}])[0]
                    delta = choice.get("delta", {})
                    yield {
                        "content": delta.get("content"),
                        "tool_calls": delta.get("tool_calls"),
                        "done": choice.get("finish_reason") is not None,
                    }

        except httpx.ConnectError as exc:
            raise ConnectionError(f"OpenRouter'a bağlanılamadı: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise ConnectionError(f"OpenRouter isteği zaman aşımına uğradı: {exc}") from exc

    def get_available_models(self) -> list[str]:
        """OpenRouter'daki kullanılabilir modellerin listesini döndürür."""
        try:
            response = self._client.get(
                f"{self._base_url}/models",
                headers=self._headers(),
            )
        except httpx.ConnectError as exc:
            raise ConnectionError(f"OpenRouter'a bağlanılamadı: {exc}") from exc

        if response.status_code != 200:
            self._handle_error_response(response)

        data = response.json()
        models = data.get("data", [])
        return [m["id"] for m in models if "id" in m]

    def set_model(self, model_name: str) -> None:
        """Aktif modeli değiştirir.

        Args:
            model_name: OpenRouter model kimliği (ör: 'anthropic/claude-3.5-sonnet').
        """
        self._model = model_name
        logger.info("OpenRouter modeli değiştirildi: %s", model_name)
