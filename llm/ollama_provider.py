"""Ollama yerel LLM sağlayıcısı - Yerel modellere erişim sağlar."""

import json
import logging
import time
from typing import Generator

import httpx

from config.settings import Settings
from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

# Varsayılan timeout değerleri (saniye)
DEFAULT_TIMEOUT = 300.0  # 5 dakika - büyük modeller için
DEFAULT_CONNECT_TIMEOUT = 10.0  # Bağlantı için
MAX_RETRIES = 2  # Maksimum yeniden deneme


class OllamaProvider(BaseLLMProvider):
    """Ollama API üzerinden yerel LLM modelllerine erişim sağlayan sınıf.

    Ollama'nın /api/chat ve /api/tags endpoint'lerini kullanır.
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        """Ayarlardan base URL ve model bilgisini yükler.

        Args:
            timeout: İstek zaman aşımı (saniye). Varsayılan 5 dakika.
        """
        settings = Settings()
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self._temperature = settings.temperature
        self._timeout = timeout
        self._client = httpx.Client(
            timeout=httpx.Timeout(
                timeout=timeout,
                connect=DEFAULT_CONNECT_TIMEOUT
            )
        )

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
        self, messages: list[dict], tools: list[dict] | None = None,
        retry_without_tools: bool = True, retry_count: int = 0
    ) -> dict:
        """İç chat completion metodu - tool fallback ve retry desteği ile."""
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
            # Retry mekanizması
            if retry_count < MAX_RETRIES:
                logger.warning(
                    "Ollama zaman aşımı, yeniden deneniyor (%d/%d)...",
                    retry_count + 1, MAX_RETRIES
                )
                time.sleep(1)  # Kısa bekleme
                return self._do_chat_completion(
                    messages, tools, retry_without_tools, retry_count + 1
                )
            raise ConnectionError(
                f"Ollama isteği zaman aşımına uğradı ({self._timeout}s). "
                f"Model '{self._model}' ilk kez yükleniyorsa bu normal olabilir. "
                "Lütfen tekrar deneyin veya daha küçük bir model kullanın."
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
        self, messages: list[dict], tools: list[dict] | None = None,
        retry_without_tools: bool = True, retry_count: int = 0
    ) -> Generator[dict, None, None]:
        """İç stream completion metodu - tool fallback ve retry desteği ile."""
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
                            yield from self._do_stream_completion(
                                messages, tools=None, retry_without_tools=False
                            )
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
            # Retry mekanizması
            if retry_count < MAX_RETRIES:
                logger.warning(
                    "Ollama stream zaman aşımı, yeniden deneniyor (%d/%d)...",
                    retry_count + 1, MAX_RETRIES
                )
                time.sleep(1)
                yield from self._do_stream_completion(
                    messages, tools, retry_without_tools, retry_count + 1
                )
                return
            raise ConnectionError(
                f"Ollama isteği zaman aşımına uğradı ({self._timeout}s). "
                f"Model '{self._model}' ilk kez yükleniyorsa bu normal olabilir. "
                "Lütfen tekrar deneyin veya daha küçük bir model kullanın."
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
        except httpx.TimeoutException as exc:
            raise ConnectionError(
                f"Ollama sunucusu yanıt vermiyor ({self._base_url}). "
                "Sunucunun meşgul olmadığından emin olun."
            ) from exc

        if response.status_code != 200:
            raise RuntimeError(
                f"Ollama API hatası ({response.status_code}): {response.text}"
            )

        data = response.json()
        models = data.get("models", [])
        return [m["name"] for m in models if "name" in m]

    def ensure_model_loaded(self) -> bool:
        """Modelin yüklü olduğunu kontrol eder, değilse bilgi verir.

        Returns:
            True eğer model hazırsa.
        """
        try:
            models = self.get_available_models()
            model_base = self._model.split(":")[0]  # "llama3.2:latest" -> "llama3.2"
            for m in models:
                if model_base in m:
                    return True
            logger.warning(
                "Model '%s' Ollama'da yüklü değil. 'ollama pull %s' ile yükleyin.",
                self._model, self._model
            )
            return False
        except Exception as e:
            logger.error("Model kontrolü başarısız: %s", e)
            return False

    def set_model(self, model_name: str) -> None:
        """Aktif modeli değiştirir.

        Args:
            model_name: Ollama model ismi (ör: 'llama3.1', 'codellama').
        """
        self._model = model_name
        logger.info("Ollama modeli değiştirildi: %s", model_name)

    def close(self) -> None:
        """HTTP client'ı kapatır."""
        if self._client:
            self._client.close()
            self._client = None
