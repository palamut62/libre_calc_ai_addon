"""Ollama yerel LLM sağlayıcısı - Yerel modellere erişim sağlar."""

import json
import logging
from typing import Generator

import httpx

from config.settings import Settings
from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """Ollama API üzerinden yerel LLM modelllerine erişim sağlayan sınıf.

    Ollama'nın /api/chat ve /api/tags endpoint'lerini kullanır.
    """

    def __init__(self):
        """Ayarlardan base URL ve model bilgisini yükler."""
        settings = Settings()
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self._temperature = settings.temperature
        self._client = httpx.Client(timeout=120.0)

    def _check_connection(self) -> None:
        """Ollama sunucusunun çalışıp çalışmadığını kontrol eder."""
        try:
            self._client.get(f"{self._base_url}/api/tags")
        except httpx.ConnectError as exc:
            raise ConnectionError(
                f"Ollama sunucusuna bağlanılamadı ({self._base_url}). "
                "Ollama'nın çalıştığından emin olun: 'ollama serve'"
            ) from exc

    def _build_payload(
        self, messages: list[dict], tools: list[dict] | None = None, stream: bool = False
    ) -> dict:
        """Ollama API isteği için JSON gövdesini oluşturur."""
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": self._temperature,
            },
        }
        if tools:
            payload["tools"] = tools
        return payload

    def chat_completion(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> dict:
        """Ollama'ya sohbet tamamlama isteği gönderir.

        Args:
            messages: Mesaj listesi.
            tools: Opsiyonel araç tanımları (model desteğine bağlı).

        Returns:
            Standart formatta yanıt sözlüğü.

        Raises:
            ConnectionError: Ollama sunucusu çalışmıyorsa.
            RuntimeError: API hatası durumunda.
        """
        return self._do_chat_completion(messages, tools)

    def _do_chat_completion(
        self, messages: list[dict], tools: list[dict] | None = None, retry_without_tools: bool = True
    ) -> dict:
        """İç chat completion metodu - tool fallback desteği ile."""
        payload = self._build_payload(messages, tools, stream=False)

        try:
            response = self._client.post(
                f"{self._base_url}/api/chat",
                json=payload,
            )
        except httpx.ConnectError as exc:
            raise ConnectionError(
                f"Ollama sunucusuna bağlanılamadı ({self._base_url}). "
                "Ollama'nın çalıştığından emin olun: 'ollama serve'"
            ) from exc
        except httpx.TimeoutException as exc:
            raise ConnectionError(
                f"Ollama isteği zaman aşımına uğradı: {exc}"
            ) from exc

        # Tool desteklenmiyor hatası - tool'suz tekrar dene
        if response.status_code == 400 and tools and retry_without_tools:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", "")
                if "does not support tools" in error_msg:
                    logger.warning(
                        "Model '%s' tool desteği yok, tool'suz devam ediliyor.",
                        self._model
                    )
                    return self._do_chat_completion(messages, tools=None, retry_without_tools=False)
            except (json.JSONDecodeError, KeyError):
                pass

        if response.status_code != 200:
            raise RuntimeError(
                f"Ollama API hatası ({response.status_code}): {response.text}"
            )

        data = response.json()
        message = data.get("message", {})

        return {
            "content": message.get("content"),
            "tool_calls": message.get("tool_calls"),
            "usage": {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
            "finish_reason": "tool_calls" if message.get("tool_calls") else "stop",
        }

    def stream_completion(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> Generator[dict, None, None]:
        """Akış modunda sohbet tamamlama isteği gönderir (JSON Lines).

        Args:
            messages: Mesaj listesi.
            tools: Opsiyonel araç tanımları.

        Yields:
            Her JSON satırı için sözlük.
        """
        yield from self._do_stream_completion(messages, tools)

    def _do_stream_completion(
        self, messages: list[dict], tools: list[dict] | None = None, retry_without_tools: bool = True
    ) -> Generator[dict, None, None]:
        """İç stream completion metodu - tool fallback desteği ile."""
        payload = self._build_payload(messages, tools, stream=True)

        try:
            with self._client.stream(
                "POST",
                f"{self._base_url}/api/chat",
                json=payload,
            ) as response:
                # Tool desteklenmiyor hatası - tool'suz tekrar dene
                if response.status_code == 400 and tools and retry_without_tools:
                    response.read()
                    try:
                        error_data = json.loads(response.text)
                        error_msg = error_data.get("error", "")
                        if "does not support tools" in error_msg:
                            logger.warning(
                                "Model '%s' tool desteği yok, tool'suz devam ediliyor.",
                                self._model
                            )
                            yield from self._do_stream_completion(messages, tools=None, retry_without_tools=False)
                            return
                    except (json.JSONDecodeError, KeyError):
                        pass

                if response.status_code != 200:
                    response.read()
                    raise RuntimeError(
                        f"Ollama API hatası ({response.status_code}): {response.text}"
                    )

                for line in response.iter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning("Ollama JSON ayrıştırma hatası: %s", line)
                        continue

                    message = data.get("message", {})
                    done = data.get("done", False)

                    yield {
                        "content": message.get("content"),
                        "tool_calls": message.get("tool_calls"),
                        "done": done,
                    }

                    if done:
                        return

        except httpx.ConnectError as exc:
            raise ConnectionError(
                f"Ollama sunucusuna bağlanılamadı ({self._base_url}). "
                "Ollama'nın çalıştığından emin olun: 'ollama serve'"
            ) from exc
        except httpx.TimeoutException as exc:
            raise ConnectionError(
                f"Ollama isteği zaman aşımına uğradı: {exc}"
            ) from exc

    def get_available_models(self) -> list[str]:
        """Ollama'da yüklü olan modellerin listesini döndürür."""
        try:
            response = self._client.get(f"{self._base_url}/api/tags")
        except httpx.ConnectError as exc:
            raise ConnectionError(
                f"Ollama sunucusuna bağlanılamadı ({self._base_url}). "
                "Ollama'nın çalıştığından emin olun: 'ollama serve'"
            ) from exc

        if response.status_code != 200:
            raise RuntimeError(
                f"Ollama API hatası ({response.status_code}): {response.text}"
            )

        data = response.json()
        models = data.get("models", [])
        return [m["name"] for m in models if "name" in m]

    def set_model(self, model_name: str) -> None:
        """Aktif modeli değiştirir.

        Args:
            model_name: Ollama model ismi (ör: 'llama3.1', 'codellama').
        """
        self._model = model_name
        logger.info("Ollama modeli değiştirildi: %s", model_name)
