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


def _to_camel_case(snake_str):
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])



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

    def _convert_tools_to_gemini_format(self, tools: list[dict]) -> list[dict] | None:
        """OpenAI tool formatını Gemini formatına çevirir."""
        if not tools:
            return None

        declarations = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                # OpenAI parametrelerini olduğu gibi alıyoruz
                # Gemini REST API genellikle standart JSON Schema kabul eder
                declarations.append(func)

        if not declarations:
            return None

        return [{"functionDeclarations": declarations}]

    def _build_contents(self, messages: list[dict]) -> list[dict]:
        """OpenAI tarzı mesajları Gemini contents'e dönüştürür."""
        contents = []
        system_prefix = ""
        
        # Tool call ID -> Function Name haritası (Function Response için gerekli)
        # Mesajları tarayıp function call'ları bulmamız gerekir.
        tool_id_to_name = {}

        # İlk geçiş: Tool call ID'lerini topla
        for m in messages:
            if m.get("role") == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    if "id" in tc and "function" in tc:
                        tool_id_to_name[tc["id"]] = tc["function"].get("name")

        if messages and messages[0].get("role") == "system":
            system_prefix = messages[0].get("content", "")

        for m in messages[1:]:
            role = m.get("role")
            content = m.get("content")
            tool_calls = m.get("tool_calls")
            
            if role == "tool":
                # Function Response
                tool_call_id = m.get("tool_call_id")
                func_name = tool_id_to_name.get(tool_call_id)
                if not func_name:
                    # İsim bulunamadıysa atla veya logla
                    continue
                    
                # Content JSON ise parse et, değilse string olarak sar
                response_content = content
                try:
                    if isinstance(content, str):
                        # Basit bir dict içine al, Gemini yapısal veri tercih eder
                        response_content = {"result": content}
                except Exception:
                    response_content = {"result": str(content)}

                contents.append({
                    "role": "function",
                    "parts": [{
                        "functionResponse": {
                            "name": func_name,
                            "response": {"name": func_name, "content": response_content}
                        }
                    }]
                })
                continue

            if role == "user":
                text = content or ""
                if system_prefix:
                    text = f"{system_prefix}\n\n{text}"
                    system_prefix = ""
                contents.append({
                    "role": "user",
                    "parts": [{"text": text}],
                })
            
            elif role == "assistant":
                parts = []
                if content:
                    parts.append({"text": content})
                
                if tool_calls:
                    for tc in tool_calls:
                        func = tc.get("function", {})
                        parts.append({
                            "functionCall": {
                                "name": func.get("name"),
                                "args": func.get("arguments") if isinstance(func.get("arguments"), dict) else json.loads(func.get("arguments", "{}"))
                            }
                        })
                
                if parts:
                    contents.append({
                        "role": "model",
                        "parts": parts,
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

        gemini_tools = self._convert_tools_to_gemini_format(tools)
        
        payload = {
            "contents": self._build_contents(messages),
            "generationConfig": {
                "temperature": self._temperature,
                "maxOutputTokens": self._max_tokens,
            },
        }

        if gemini_tools:
            payload["tools"] = gemini_tools
            # Tool kullanımı için config: AUTO (model karar verir)
            payload["toolConfig"] = {"functionCallingConfig": {"mode": "AUTO"}}

        url = f"{self._base_url}/models/{self._model}:generateContent"
        response = self._make_request(url, payload)

        if response.status_code != 200:
            raise RuntimeError(f"Gemini API hatası ({response.status_code}): {response.text}")

        data = response.json()
        candidates = data.get("candidates", [])
        
        content = None
        tool_calls = None
        finish_reason = "stop"

        if candidates:
            candidate = candidates[0]
            parts = candidate.get("content", {}).get("parts", [])
            finish_reason = candidate.get("finishReason", "stop").lower()
            
            # Text content
            texts = [p.get("text") for p in parts if "text" in p]
            if texts:
                content = "".join(texts)
                
            # Function calls
            f_calls = [p.get("functionCall") for p in parts if "functionCall" in p]
            if f_calls:
                tool_calls = []
                for i, fc in enumerate(f_calls):
                    name = fc.get("name")
                    args = fc.get("args", {})
                    # Args dict gelmeli, string ise parse etmeye çalışalım
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except:
                            pass
                            
                    tool_calls.append({
                        "id": f"call_{int(time.time())}_{i}", # Gemini ID dönmez, biz üretelim
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(args, ensure_ascii=False)
                        }
                    })

        return {
            "content": content,
            "tool_calls": tool_calls,
            "usage": {},
            "finish_reason": finish_reason,
        }

    def stream_completion(self, messages: list[dict], tools: list[dict] | None = None) -> Generator[dict, None, None]:
        """Stream desteklenmiyor; tek parça döndürür."""
        # Tools parametresini geçiriyoruz
        result = self.chat_completion(messages, tools=tools)
        # Eğer tool_calls varsa onları da döndür
        yield {
            "content": result.get("content"), 
            "tool_calls": result.get("tool_calls"), 
            "done": True
        }

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
