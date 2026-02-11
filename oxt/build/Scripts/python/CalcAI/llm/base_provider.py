"""LLM sağlayıcıları için soyut temel sınıf."""

from abc import ABC, abstractmethod
from typing import Generator


class BaseLLMProvider(ABC):
    """Tüm LLM sağlayıcılarının uygulaması gereken arayüz.

    Alt sınıflar chat_completion, stream_completion, get_available_models
    ve set_model metodlarını uygulamalıdır.
    """

    @abstractmethod
    def chat_completion(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> dict:
        """Sohbet tamamlama isteği gönderir.

        Args:
            messages: Mesaj listesi. Her mesaj {"role": "system"|"user"|"assistant"|"tool",
                      "content": "..."} biçiminde olmalıdır.
            tools: Opsiyonel araç tanımları (OpenAI function calling formatında).

        Returns:
            API yanıtını içeren sözlük. En az şu alanları içerir:
            - "content": Asistan yanıt metni (veya None)
            - "tool_calls": Araç çağrıları listesi (veya None)
            - "usage": Token kullanım bilgisi
        """

    @abstractmethod
    def stream_completion(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> Generator[dict, None, None]:
        """Akış (streaming) modunda sohbet tamamlama isteği gönderir.

        Args:
            messages: Mesaj listesi.
            tools: Opsiyonel araç tanımları.

        Yields:
            Her parça için sözlük:
            - "content": Metin parçası (veya None)
            - "tool_calls": Araç çağrısı parçası (veya None)
            - "done": Akışın tamamlanıp tamamlanmadığı
        """

    @abstractmethod
    def get_available_models(self) -> list[str]:
        """Kullanılabilir model listesini döndürür.

        Returns:
            Model isimlerinden oluşan liste.
        """

    @abstractmethod
    def set_model(self, model_name: str) -> None:
        """Aktif modeli değiştirir.

        Args:
            model_name: Kullanılacak model ismi.
        """

    def close(self) -> None:
        """Kaynakları serbest bırakır (HTTP client vb.).

        Alt sınıflar gerektiğinde override edebilir.
        """
        pass

    def __enter__(self):
        """Context manager desteği."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager çıkışında close() çağırır."""
        self.close()
        return False
