"""
services/llm_service.py
Google Gemini client for generating structured congratulatory song lyrics.
Supports Kazakh ('kk'), Russian ('ru'), and English ('en') with strict verse structure.
"""

import asyncio
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class GeminiServiceError(Exception):
    """Base exception for Gemini service failures."""
    pass


# Backward compatibility alias
LLMServiceError = GeminiServiceError


class GeminiService:
    """
    Direct asynchronous client for Google Gemini API via official REST API with aiohttp.
    Supports multilingual song lyrics generation (Kazakh, Russian, English)
    with strict structure ([Verse 1], [Chorus], [Verse 2], [Chorus], [Outro])
    and zero truncation.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.6-flash",
        session: aiohttp.ClientSession | None = None,
        request_timeout: int = 45,
    ) -> None:
        self._api_key = api_key

        # Auto-upgrade deprecated model names if passed from legacy configs
        cleaned_model = model.replace("models/", "")
        if cleaned_model in ("gemini-2.5-flash", "gemini-1.5-flash"):
            logger.info("Auto-migrating deprecated model '%s' to 'gemini-3.6-flash'", cleaned_model)
            cleaned_model = "gemini-3.6-flash"

        self._model = cleaned_model
        self._session = session
        self._owns_session = session is None
        self._request_timeout = aiohttp.ClientTimeout(total=request_timeout)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._request_timeout)
            self._owns_session = True
        return self._session

    async def close(self) -> None:
        """Close HTTP session if owned by this service."""
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()

    def _build_prompts(
        self,
        name: str,
        occasion: str,
        details: str,
        genre: str,
        language: str = "ru",
    ) -> tuple[str, str]:
        """
        Build language-specific system and user prompts.
        Supports Kazakh (kk), Russian (ru), and English (en).
        """
        if language == "kk":
            system_prompt = (
                "Сен — қазақтың кәсіби ақыны, сазгері және хит әндердің шеберісің. "
                "Сенің міндетің — Suno AI музыкалық генераторы үшін көркем, ұйқасы мінсіз, "
                "терең мағыналы әрі көңілді қазақша құттықтау әнін (той әнін) жазу.\n\n"
                "ҚАТАҢ ЕРЕЖЕЛЕР:\n"
                "1. Ән құрылымы МІНДЕТТІ ТҮРДЕ мынадай болуы тиіс:\n"
                "   [Verse 1]\n"
                "   (1-шумақ: адресаттың есімі мен мерекелік көңіл-күйді ашу)\n"
                "   [Chorus]\n"
                "   (Қайырма: есте қаларлық, әуезді, көңілді әрі жалынды негізгі кульминация)\n"
                "   [Verse 2]\n"
                "   (2-шумақ: берілген нақты деректерді, хоббиін, мінезін шебер ұйқастыру)\n"
                "   [Chorus]\n"
                "   (Қайырма: қайталау)\n"
                "   [Outro]\n"
                "   (Қорытынды: ақ тілек, бата, жарқын финал)\n"
                "2. Тіл тазалығы мен ұйқас: Тек таза, әдеби қазақ тілінде жаз. Калька мен бөтен сөздерді қоспа. "
                "Ұйқасы мінсіз қара өлең немесе шалыс ұйқас болсын, буын ырғағы нақты сақталсын.\n"
                "3. Ән толық әрі аяқталған болуы керек, сөздер мен шумақтар үзілмесін.\n"
                "4. ТЕК ҚАНА әннің сөздерін шығар! Ешқандай кіріспе сөздер («Міне сіздің әніңіз:»), "
                "түсініктемелер мен код блоктарын (```) жазуға ТЫЙЫМ САЛЫНАДЫ."
            )
            user_prompt = (
                f"Мына мәліметтер бойынша толық қазақша ән мәтінін жаз:\n"
                f"- Кімге арналады (Есімі): {name}\n"
                f"- Себебі/Мереке: {occasion}\n"
                f"- Музыка стилі: {genre}\n"
                f"- Қызықты деректер мен тілектер: {details}\n\n"
                f"Әнді жоғарыдағы құрылым бойынша [Verse 1], [Chorus], [Verse 2], [Chorus], [Outro] тегтерімен толық жазып шық."
            )

        elif language == "en":
            system_prompt = (
                "You are an award-winning songwriter and lyricist. "
                "Your task is to write a catchy, emotionally resonant, perfectly rhymed celebration song "
                "optimized for Suno AI audio generation.\n\n"
                "STRICT RULES:\n"
                "1. You MUST follow this exact song structure:\n"
                "   [Verse 1]\n"
                "   (Story begins, introduces the recipient and the celebratory mood)\n"
                "   [Chorus]\n"
                "   (Memorable, energetic, emotional hook that sticks in the listener's head)\n"
                "   [Verse 2]\n"
                "   (Integrates the specific personal facts, hobbies, and memories smoothly)\n"
                "   [Chorus]\n"
                "   (Repeat chorus)\n"
                "   [Outro]\n"
                "   (Warm heartfelt sendoff and grand celebratory finale)\n"
                "2. Maintain strict rhythm, consistent meter, and natural contemporary rhymes (AABB or ABAB).\n"
                "3. Ensure the song is 100% complete — do not leave any verse unfinished.\n"
                "4. Output ONLY the song lyrics with section tags. Absolutely NO meta-commentary, "
                "greetings, explanations, or code blocks (```)."
            )
            user_prompt = (
                f"Write a complete celebration song with these details:\n"
                f"- Recipient: {name}\n"
                f"- Occasion: {occasion}\n"
                f"- Music Genre/Style: {genre}\n"
                f"- Personal Facts & Wishes: {details}\n\n"
                f"Deliver the finished song formatted with [Verse 1], [Chorus], [Verse 2], [Chorus], [Outro]."
            )

        else:  # Russian (ru)
            system_prompt = (
                "Ты — профессиональный российский поэт-песенник и хитмейкер. "
                "Твоя задача — написать яркий, эмоциональный, ритмичный текст поздравительной песни "
                "для генератора музыки Suno AI.\n\n"
                "СТРОГИЕ ПРАВИЛА:\n"
                "1. Обязательная законченная структура песни:\n"
                "   [Verse 1]\n"
                "   (Вступление, имя виновника торжества и атмосфера праздника)\n"
                "   [Chorus]\n"
                "   (Яркий, запоминающийся, эмоциональный припев-кульминация)\n"
                "   [Verse 2]\n"
                "   (Органичное вплетение фактов, воспоминаний, хобби и черт характера)\n"
                "   [Chorus]\n"
                "   (Повторение припева)\n"
                "   [Outro]\n"
                "   (Финал с теплыми пожеланиями и красивым затуханием/кодой)\n"
                "2. Текст должен безупречно рифмоваться (точная рифма, четкий размер) и строго соответствовать выбранному стилю.\n"
                "3. Песня должна быть законченной от начала до конца, без обрыва строк и куплетов.\n"
                "4. Выводи ТОЛЬКО текст песни с тегами разделов. Запрещены вступительные слова, "
                "комментарии автора и обрамление в код (```)."
            )
            user_prompt = (
                f"Напиши готовую праздничную песню со следующими вводными:\n"
                f"- Имя адресата: {name}\n"
                f"- Повод: {occasion}\n"
                f"- Музыкальный стиль/жанр: {genre}\n"
                f"- Факты, детали и пожелания: {details}\n\n"
                f"Выдай полный текст со структурой [Verse 1], [Chorus], [Verse 2], [Chorus], [Outro]."
            )

        return system_prompt, user_prompt

    async def generate_lyrics(
        self,
        name: str,
        occasion: str,
        details: str,
        genre: str,
        lang: str = "ru",
        language: str | None = None,
    ) -> str:
        """
        Generate complete, structured song lyrics in the specified language (kk, ru, en).

        :param name: Recipient name.
        :param occasion: Holiday or occasion.
        :param details: Personal memories, hobbies, traits.
        :param genre: Music style.
        :param lang: Language code ('kk', 'ru', 'en').
        :param language: Optional alias for lang.
        :return: Fully structured lyrics without truncation or meta-text.
        """
        chosen_lang = language or lang or "ru"
        system_prompt, user_prompt = self._build_prompts(
            name=name,
            occasion=occasion,
            details=details,
            genre=genre,
            language=chosen_lang,
        )

        models_to_try = [
            self._model,
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-3.6-flash",
        ]
        unique_models = list(dict.fromkeys([m.replace("models/", "") for m in models_to_try if m]))
        session = await self._get_session()
        last_error_msg = ""

        # -------------------------------------------------------------------
        # Strategy 1: Google Interactions API with Automatic Model Fallback
        # -------------------------------------------------------------------
        interactions_endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/interactions?key={self._api_key}"
        )

        for candidate_model in unique_models:
            full_model_name = f"models/{candidate_model}"
            interactions_payload: dict[str, Any] = {
                "model": full_model_name,
                "input": user_prompt,
                "system_instruction": system_prompt,
                "generation_config": {
                    # 4096 tokens guarantees full song lyrics without cutting off
                    "max_output_tokens": 4096,
                    # 'low' thinking level prevents token exhaustion while keeping verses smart
                    "thinking_level": "low",
                },
            }

            logger.info(
                "Requesting lyrics via Interactions API (model=%s, lang=%s, name='%s')...",
                full_model_name,
                chosen_lang,
                name,
            )

            try:
                async with session.post(
                    interactions_endpoint,
                    headers={"Content-Type": "application/json"},
                    json=interactions_payload,
                ) as response:
                    response_data = await response.json()
                    if response.status == 200:
                        text = self._extract_text(response_data)
                        if text and len(text) >= 150:
                            logger.info(
                                "Successfully generated lyrics with %s (%d chars, lang=%s)",
                                full_model_name,
                                len(text),
                                chosen_lang,
                            )
                            return self._sanitize_lyrics(text)
                    else:
                        err_detail = response_data.get("error", {})
                        last_error_msg = err_detail.get("message") or str(response_data)
                        logger.warning(
                            "Interactions API returned HTTP %s for %s: %s. Trying next candidate...",
                            response.status,
                            full_model_name,
                            last_error_msg[:120],
                        )
            except Exception as exc:
                last_error_msg = str(exc)
                logger.warning("Interactions API request error for %s: %s. Trying next candidate...", full_model_name, exc)

        # -------------------------------------------------------------------
        # Strategy 2: generateContent fallback
        # -------------------------------------------------------------------
        for candidate_model in unique_models:
            full_model_name = f"models/{candidate_model}"
            generate_endpoint = (
                f"https://generativelanguage.googleapis.com/v1beta/{full_model_name}:generateContent"
                f"?key={self._api_key}"
            )
            generate_payload: dict[str, Any] = {
                "system_instruction": {
                    "parts": [{"text": system_prompt}],
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": user_prompt}],
                    }
                ],
                "generationConfig": {
                    "temperature": 0.75,
                    "maxOutputTokens": 4096,
                },
            }

            logger.info("Calling generateContent fallback (model=%s, lang=%s)...", full_model_name, chosen_lang)
            try:
                async with session.post(
                    generate_endpoint,
                    headers={"Content-Type": "application/json"},
                    json=generate_payload,
                ) as response:
                    response_data = await response.json()

                    if response.status == 200:
                        text = self._extract_text(response_data)
                        if text and len(text) >= 150:
                            logger.info("Successfully generated lyrics via generateContent fallback with %s (%d chars)", full_model_name, len(text))
                            return self._sanitize_lyrics(text)
                    else:
                        err_detail = response_data.get("error", {})
                        last_error_msg = err_detail.get("message") or str(response_data)
                        logger.warning("generateContent returned HTTP %s for %s: %s", response.status, full_model_name, last_error_msg[:120])
            except Exception as exc:
                last_error_msg = str(exc)
                logger.warning("generateContent error for %s: %s", full_model_name, exc)

        raise GeminiServiceError(f"Не удалось сгенерировать текст песни через Gemini: {last_error_msg}")

    def _extract_text(self, data: dict[str, Any]) -> str | None:
        """Extract text from Interactions API or generateContent responses."""
        # 1. Check steps in Interactions API
        texts: list[str] = []
        for step in data.get("steps", []):
            for item in step.get("content", []):
                if isinstance(item, dict):
                    # Only accept 'text' type items, strictly ignore thought and tool outputs
                    if item.get("type") == "text" and "text" in item:
                        t = str(item["text"]).strip()
                        if t:
                            texts.append(t)
                elif isinstance(item, str) and item.strip():
                    texts.append(item.strip())

        if texts:
            return "\n\n".join(texts)

        # 2. Check candidates in generateContent
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            cand_texts = [
                str(p["text"]).strip()
                for p in parts
                if isinstance(p, dict) and "text" in p and not p.get("thought")
            ]
            if cand_texts:
                return "\n\n".join(cand_texts)

        if "output_text" in data and data["output_text"]:
            return str(data["output_text"]).strip()

        return None

    @staticmethod
    def _sanitize_lyrics(lyrics: str) -> str:
        """Clean markdown codeblock wrappers and trim accidental pre-verse meta commentary."""
        cleaned = lyrics.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if len(lines) >= 2 and lines[-1].strip() == "```":
                cleaned = "\n".join(lines[1:-1]).strip()

        # If there is meta-chatter before [Verse 1] / [Intro], start from the actual song tag
        for tag in ("[Verse 1]", "[Verse]", "[Intro]"):
            pos = cleaned.find(tag)
            if pos != -1 and pos < 200:
                cleaned = cleaned[pos:].strip()
                break

        return cleaned


# Backward compatibility aliases
LLMService = GeminiService


# Standalone function helper
async def generate_lyrics(
    name: str,
    occasion: str,
    details: str,
    genre: str,
    lang: str = "ru",
    api_key: str | None = None,
    model: str = "gemini-3.6-flash",
) -> str:
    """
    Convenience function to generate lyrics directly without managing service instances manually.
    """
    if not api_key:
        from config import get_settings
        api_key = get_settings().GEMINI_API_KEY.get_secret_value()
        model = get_settings().GEMINI_MODEL

    service = GeminiService(api_key=api_key, model=model)
    try:
        return await service.generate_lyrics(
            name=name,
            occasion=occasion,
            details=details,
            genre=genre,
            lang=lang,
        )
    finally:
        await service.close()
