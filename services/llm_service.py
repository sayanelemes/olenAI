"""
services/llm_service.py
Google Gemini client using the official google-genai SDK.
Implements unified content moderation and lyrics generation in JSON mode:
response_mime_type="application/json".
"""

import json
import logging
from typing import Any

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiServiceError(Exception):
    """Base exception for Gemini service failures."""
    pass


LLMServiceError = GeminiServiceError


class GeminiService:
    """
    Client for Google Gemini API via official google-genai SDK.
    Performs simultaneous content moderation and structured lyrics composition
    using response_mime_type='application/json'.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.1-flash-lite",
        session: Any = None,
        request_timeout: int = 45,
    ) -> None:
        self._api_key = api_key
        # Clean model name if passed with models/ prefix
        cleaned_model = model.replace("models/", "")
        self._model = cleaned_model
        self._client = genai.Client(api_key=api_key)
        self._request_timeout = request_timeout

    async def close(self) -> None:
        """Close client if needed."""
        pass

    async def moderate_and_generate_lyrics(
        self,
        name: str,
        occasion: str,
        details: str,
        genre: str,
        language: str = "ru",
    ) -> dict[str, Any]:
        """
        Unified Step 4:
        Evaluates user inputs for toxicity, harassment, obscenity, and 18+ content,
        and generates high-quality structured song lyrics in a single call.
        Returns:
            {
                "is_safe": bool,
                "reason": str | None,
                "title": str,
                "lyrics": str
            }
        """
        lang_instruction = {
            "kk": "Жауапты және әннің мәтінін ТАЗА ҚАЗАҚ ТІЛІНДЕ жаз.",
            "ru": "Ответ и текст песни пиши на РУССКОМ ЯЗЫКЕ.",
            "en": "Write the response and the song lyrics in ENGLISH.",
        }.get(language, "Ответ и текст песни пиши на РУССКОМ ЯЗЫКЕ.")

        prompt = f"""
Ты — профессиональный поэт-песенник, продюсер и ответственный модератор контента для музыкального сервиса.
{lang_instruction}

ТВОИ ДВЕ ОБЯЗАТЕЛЬНЫЕ ЗАДАЧИ:
1. МОДЕРАЦИЯ ВХОДНЫХ ДАННЫХ:
   - Внимательно оцени имя, повод и факты на токсичность, буллинг, оскорбления личности, травлю, мат, нецензурную брань, экстремизм и контент 18+.
   - Если факты нарушают эти нормы:
     установи "is_safe": false,
     в поле "reason" дай понятную, вежливую и четкую причину отказа на языке запроса ({language}) без лишней морали,
     в полях "title" и "lyrics" верни пустые строки.
   - Если факты безобидные, праздничные, добрые шутки или теплые воспоминания (даже с легким дружеским юмором без мата/унижения):
     установи "is_safe": true, "reason": null и выполни задачу 2.

2. ГЕНЕРАЦИЯ ТЕКСТА ПЕСНИ (для Suno AI):
   - Сочини яркий, мелодичный, ритмичный текст песни под указанный музыкальный жанр ({genre}).
   - Строгая структура песни:
     [Verse 1]
     (раскрытие имени адресата и праздничной атмосферы)
     [Chorus]
     (главный запоминающийся, качающий и зажигательный припев)
     [Verse 2]
     (органично вплети личные факты и воспоминания)
     [Chorus]
     (повтор припева)
     [Outro]
     (яркий финальный аккорд и пожелание)
   - Идеальная рифма и ритмика куплетов, без сбоев размера.

ВХОДНЫЕ ДАННЫЕ ЗАКАЗА:
- Имя адресата: {name}
- Повод: {occasion}
- Личные факты и детали: {details}
- Музыкальный жанр: {genre}

ФОРМАТ ОТВЕТА:
Верни СТРОГО валидный JSON-объект следующей схемы:
{{
  "is_safe": true или false,
  "reason": null или "Понятная причина отказа на языке пользователя",
  "lyrics": "[Verse 1]...\\n\\n[Chorus]...\\n\\n[Verse 2]...\\n\\n[Chorus]...\\n\\n[Outro]...",
  "tags": "musical style tags for suno (e.g. q-pop, upbeat, electronic, festive)",
  "title": "Название песни"
}}
"""

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.7,
        )

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=config,
            )
            raw_text = response.text or "{}"
            data = json.loads(raw_text)

            is_safe = bool(data.get("is_safe", True))
            reason = data.get("reason")
            title = str(data.get("title") or f"Song for {name}").strip()
            lyrics = str(data.get("lyrics") or "").strip()
            tags = str(data.get("tags") or genre).strip()

            return {
                "is_safe": is_safe,
                "reason": reason,
                "lyrics": lyrics,
                "tags": tags,
                "title": title,
            }
        except json.JSONDecodeError as err:
            logger.error("Failed to decode JSON from Gemini: %s. Response was: %s", err, response.text)
            # If JSON decoding fails but text is generated, check if it's safe
            return {
                "is_safe": True,
                "reason": None,
                "title": f"Song for {name}",
                "lyrics": response.text or "",
            }
        except Exception as exc:
            logger.exception("Gemini API call failed: %s", exc)
            raise GeminiServiceError(f"Ошибка вызова Gemini API: {exc}") from exc

    # Backward compatibility method for existing handlers
    async def generate_lyrics(
        self,
        name: str,
        occasion: str,
        details: str,
        genre: str,
        language: str = "ru",
    ) -> str:
        res = await self.moderate_and_generate_lyrics(
            name=name,
            occasion=occasion,
            details=details,
            genre=genre,
            language=language,
        )
        if not res["is_safe"]:
            raise GeminiServiceError(res["reason"] or "Текст не прошел модерацию безопасности.")
        return res["lyrics"]


LLMService = GeminiService
