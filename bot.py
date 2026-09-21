"""
bot.py
Production-ready Telegram Bot for AI Song Generation with full multilingual support.
Stack: aiogram 3.x, aiosqlite (WAL mode), google-genai (Gemini SDK), aiohttp.

Features:
1. Multilingual interface: Kazakh (kk), Russian (ru), English (en) with easy language selection.
2. SQLite Database (WAL mode, synchronous=NORMAL, busy_timeout=5000).
3. 5-step FSM workflow with Gemini JSON moderation and lyrics composition in the user's language.
4. Telegram Stars (60 XTR) payment with 3-second PreCheckout Healthcheck to Apiframe.
5. 5-worker concurrency queue with automated Star refunds on failure.
"""

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from typing import Any

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatAction, ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    URLInputFile,
)
from google import genai
from google.genai import types

from database import DatabaseManager
from locales import (
    DEFAULT_LANGUAGE,
    GENRES_LIST,
    LANG_EN,
    LANG_KK,
    LANG_RU,
    OCCASIONS_LIST,
    get_genre_label,
    get_genre_style,
    get_text,
)

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("song_bot")

# ---------------------------------------------------------------------------
# Configuration & Environment
# ---------------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview").replace("models/", "")
APIFRAME_API_KEY = os.getenv("APIFRAME_API_KEY", "")
APIFRAME_BASE_URL = os.getenv("APIFRAME_BASE_URL", "https://api.apiframe.ai").rstrip("/")
MAX_CONCURRENT_GENERATIONS = int(os.getenv("MAX_CONCURRENT_GENERATIONS", "5"))
TEST_PAYMENT_MODE = os.getenv("TEST_PAYMENT_MODE", "True").lower() in ("true", "1", "yes")
USE_MOCK_MUSIC = os.getenv("USE_MOCK_MUSIC", "True").lower() in ("true", "1", "yes") or TEST_PAYMENT_MODE
MOCK_AUDIO_URL = os.getenv("MOCK_AUDIO_URL", "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")

# Load values from local .env if present
env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_file):
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k == "BOT_TOKEN":
                    BOT_TOKEN = v
                elif k == "GEMINI_API_KEY":
                    GEMINI_API_KEY = v
                elif k == "GEMINI_MODEL":
                    GEMINI_MODEL = v.replace("models/", "")
                elif k == "APIFRAME_API_KEY":
                    APIFRAME_API_KEY = v
                elif k == "APIFRAME_BASE_URL":
                    APIFRAME_BASE_URL = v.rstrip("/")
                elif k == "MAX_CONCURRENT_GENERATIONS":
                    try:
                        MAX_CONCURRENT_GENERATIONS = int(v)
                    except ValueError:
                        pass
                elif k == "TEST_PAYMENT_MODE":
                    TEST_PAYMENT_MODE = v.lower() in ("true", "1", "yes")
                elif k == "USE_MOCK_MUSIC":
                    USE_MOCK_MUSIC = v.lower() in ("true", "1", "yes")
                elif k == "MOCK_AUDIO_URL":
                    MOCK_AUDIO_URL = v

if TEST_PAYMENT_MODE:
    USE_MOCK_MUSIC = True


# ---------------------------------------------------------------------------
# FSM State Definitions
# ---------------------------------------------------------------------------
class OrderStates(StatesGroup):
    language = State()
    occasion = State()
    details = State()
    genre = State()
    preview_approval = State()
    waiting_payment = State()
    generating_audio = State()


# ---------------------------------------------------------------------------
# Multilingual Keyboards
# ---------------------------------------------------------------------------
def get_language_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting bot interface language."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="set_lang:kk"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru"),
            ],
            [
                InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang:en"),
            ],
        ]
    )


def get_occasions_keyboard(lang: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """Localized keyboard for selecting occasion (Step 1)."""
    occasions = OCCASIONS_LIST.get(lang) or OCCASIONS_LIST.get(DEFAULT_LANGUAGE, [])
    buttons = []
    for label, value in occasions:
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"occ:{value}")])
    buttons.append([InlineKeyboardButton(text=get_text("btn_change_lang", lang), callback_data="change_lang")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_genres_keyboard(lang: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """10 localized music genres formatted in a neat 2-column grid (Step 3)."""
    genres = GENRES_LIST.get(lang) or GENRES_LIST.get(DEFAULT_LANGUAGE, [])
    buttons = []
    for i in range(0, len(genres), 2):
        row = [InlineKeyboardButton(text=genres[i]["label"], callback_data=f"gnr:{genres[i]['id']}")]
        if i + 1 < len(genres):
            row.append(
                InlineKeyboardButton(text=genres[i + 1]["label"], callback_data=f"gnr:{genres[i + 1]['id']}")
            )
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text=get_text("btn_cancel", lang), callback_data="prv:restart")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_preview_keyboard(lang: str = DEFAULT_LANGUAGE, is_test: bool = False) -> InlineKeyboardMarkup:
    """Approval keyboard with mandatory disclaimer options (Step 5)."""
    approve_key = "btn_approve_sing_test" if is_test else "btn_approve_sing"
    approve_text = get_text(approve_key, lang)
    restart_text = get_text("btn_edit_details", lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=approve_text, callback_data="prv:approve")],
            [InlineKeyboardButton(text=restart_text, callback_data="prv:restart")],
            [InlineKeyboardButton(text=get_text("btn_change_lang", lang), callback_data="change_lang")],
        ]
    )


def get_restart_keyboard(lang: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """Keyboard offered after track generation completion."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_text("btn_start_order", lang), callback_data="new_order")],
            [InlineKeyboardButton(text=get_text("btn_change_lang", lang), callback_data="change_lang")],
        ]
    )


# ---------------------------------------------------------------------------
# Task Queue Job Model
# ---------------------------------------------------------------------------
@dataclass
class GenerationJob:
    charge_id: str
    user_id: int
    chat_id: int
    prompt: str  # Generated lyrics
    tags: str    # Musical style tags for Suno
    title: str
    name: str
    occasion: str
    genre_name: str
    lang: str
    enqueued_at: float = 0.0


# ---------------------------------------------------------------------------
# Gemini AI Content Service (Structured JSON Mode)
# ---------------------------------------------------------------------------
class GeminiContentService:
    def __init__(self, api_key: str, model: str) -> None:
        self.primary_model = model
        self.client = genai.Client(api_key=api_key) if api_key else None
        # Candidate models with automatic failover
        raw_candidates = [
            model,
            "gemini-3-flash-preview",
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash-lite",
        ]
        seen = set()
        self.candidate_models = [m for m in raw_candidates if m and not (m in seen or seen.add(m))]

    async def moderate_and_compose(
        self,
        name: str,
        occasion: str,
        details: str,
        genre_title: str,
        genre_tags: str,
        language: str = "ru",
    ) -> dict[str, Any]:
        """
        Step 4: Unified Gemini API call in JSON mode: response_mime_type='application/json'.
        Includes automatic retries and multi-model failover for 503 UNAVAILABLE or spikes.
        """
        if language == "kk":
            lang_instruction = (
                "Жауапты және әннің мәтінін ТАЗА ҚАЗАҚ ТІЛІНДЕ жаз. "
                "Қазақ тілінде көркем, ұйқасы мінсіз, мағыналы ән сөздерін құрастыр."
            )
            default_title = f"{name} үшін арнайы ән"
        elif language == "en":
            lang_instruction = (
                "Write the response and the song lyrics in ENGLISH. "
                "Compose catchy, rhythmic lyrics with perfect rhyme and structure."
            )
            default_title = f"Song for {name}"
        else:
            lang_instruction = (
                "Ответ и текст песни пиши на РУССКОМ ЯЗЫКЕ. "
                "Сочини яркий, ритмичный текст песни с идеальной рифмой и структурой."
            )
            default_title = f"Песня для {name}"

        if not self.client:
            return self._build_template_lyrics(name, occasion, details, genre_tags, default_title, language)

        prompt = f"""
Ты — профессиональный музыкальный продюсер, поэт-песенник и модератор контента сервиса персональных песен.
{lang_instruction}

ЗАДАЧИ:
1. МОДЕРАЦИЯ ВХОДНЫХ ДАННЫХ:
   - Проверь имя, повод и факты на токсичность, буллинг, травлю, оскорбления личности, мат, ненависть, экстремизм и 18+.
   - Если есть нарушение:
     "is_safe": false,
     "reason": "Вежливое и понятное объяснение причины отказа на языке запроса ({language})",
     "lyrics": null,
     "tags": null.
   - Если данные безопасные, добрые, праздничные или с дружеским безобидным юмором:
     "is_safe": true, "reason": null и выполни задачу 2.

2. СОЧИНЕНИЕ ТЕКСТА ПЕСНИ ДЛЯ SUNO AI:
   - Напиши ритмичный, эмоциональный текст песни под стиль: {genre_title} ({genre_tags}).
   - Строгая структура:
     [Verse 1]
     (раскрытие имени адресата и праздничной атмосферы)
     [Chorus]
     (яркий, качающий, зажигательный припев)
     [Verse 2]
     (органично вплети личные факты и воспоминания)
     [Chorus]
     (повтор припева)
     [Outro]
     (финальное теплое пожелание)

ВХОДНЫЕ ДАННЫЕ:
- Имя адресата: {name}
- Повод: {occasion}
- Личные факты и детали: {details}
- Музыкальный стиль: {genre_title}

ФОРМАТ ВЫВОДА:
СТРОГО валидный JSON следующей схемы:
{{
  "is_safe": true,
  "reason": null,
  "lyrics": "[Verse 1]...\\n\\n[Chorus]...\\n\\n[Verse 2]...\\n\\n[Chorus]...\\n\\n[Outro]...",
  "tags": "{genre_tags}",
  "title": "{default_title}"
}}
"""

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.7,
        )

        last_exc: Exception | None = None
        for model_name in self.candidate_models:
            for attempt in range(2):
                try:
                    logger.info("Calling Gemini (model=%s, attempt=%d)...", model_name, attempt + 1)
                    response = await asyncio.wait_for(
                        self.client.aio.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=config,
                        ),
                        timeout=25.0,
                    )
                    raw = response.text or "{}"
                    data = json.loads(raw)
                    return {
                        "is_safe": bool(data.get("is_safe", True)),
                        "reason": data.get("reason"),
                        "lyrics": data.get("lyrics"),
                        "tags": data.get("tags") or genre_tags,
                        "title": data.get("title") or default_title,
                    }
                except Exception as exc:
                    last_exc = exc
                    err_msg = str(exc)
                    logger.warning("Gemini error on model=%s, attempt=%d: %s", model_name, attempt + 1, err_msg)
                    if "503" in err_msg or "UNAVAILABLE" in err_msg or "429" in err_msg or "Timeout" in err_msg:
                        await asyncio.sleep(1.0)
                        continue
                    break  # Try next candidate model

        logger.error("All Gemini candidate models failed (%s). Using template fallback.", last_exc)
        return self._build_template_lyrics(name, occasion, details, genre_tags, default_title, language)

    def _build_template_lyrics(
        self,
        name: str,
        occasion: str,
        details: str,
        genre_tags: str,
        title: str,
        language: str,
    ) -> dict[str, Any]:
        if language == "kk":
            lyrics = (
                f"[Verse 1]\n"
                f"Бүгін саған арналады әсем ән, {name},\n"
                f"Жүрегіңнен кетпесін еш шаттық пен мән!\n"
                f"{occasion} құтты болсын баршамызға,\n"
                f"Ашық болсын өмірде әрбір қадам!\n\n"
                f"[Chorus]\n"
                f"Шырқа әнді, биле бүгін тоқтама!\n"
                f"Бақыт қонсын, шаттық толсын ортаға!\n"
                f"Жүректерді жылытқан осы әуен,\n"
                f"Қуанышқа толы болсын әрбір дем!\n\n"
                f"[Verse 2]\n"
                f"{details}\n"
                f"Орындалсын арманың, арай таңың,\n"
                f"Жадырасын көңілдің әрбір сәті!\n\n"
                f"[Chorus]\n"
                f"Шырқа әнді, биле бүгін тоқтама!\n"
                f"Бақыт қонсын, шаттық толсын ортаға!\n\n"
                f"[Outro]\n"
                f"Құттықтаймыз шын жүректен, {name}!"
            )
        else:
            lyrics = (
                f"[Verse 1]\n"
                f"Этот праздничный трек для тебя, {name}!\n"
                f"Пусть сияют улыбкой и счастьем глаза!\n"
                f"{occasion} встречаем сегодня с душой,\n"
                f"Пусть удача и радость пребудут с тобой!\n\n"
                f"[Chorus]\n"
                f"Пой с нами вместе, танцуй и живи!\n"
                f"Море улыбок, тепла и любви!\n"
                f"Каждый куплет для тебя прозвучит,\n"
                f"Сердце в ритме восторга стучит!\n\n"
                f"[Verse 2]\n"
                f"{details}\n"
                f"Пусть все мечты исполняются вмиг,\n"
                f"Счастье найдет свой заветный родник!\n\n"
                f"[Chorus]\n"
                f"Пой с нами вместе, танцуй и живи!\n\n"
                f"[Outro]\n"
                f"С праздником от всей души, {name}!"
            )
        return {
            "is_safe": True,
            "reason": None,
            "lyrics": lyrics,
            "tags": genre_tags,
            "title": title,
        }


# ---------------------------------------------------------------------------
# Apiframe Suno Gateway Service
# ---------------------------------------------------------------------------
class SunoGatewayService:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        use_mock: bool = False,
        mock_audio_url: str = MOCK_AUDIO_URL,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.use_mock = use_mock
        self.mock_audio_url = mock_audio_url
        self._session = session

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    async def check_health(self, timeout: float = 3.0) -> bool:
        """
        Step 3: Fast 3-second PreCheckout Healthcheck against Apiframe API.
        """
        if self.use_mock:
            return True

        url = f"{self.base_url}/v2/models"
        try:
            async with self._session.get(
                url,
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                return response.status < 500
        except Exception as exc:
            logger.warning("Apiframe healthcheck failed: %s", exc)
            return False

    async def generate_song(self, lyrics: str, tags: str, title: str) -> str:
        """
        Submits generation request to Suno via Apiframe and polls until complete.
        """
        if self.use_mock:
            logger.info("[MOCK] Simulating Suno music generation (4 seconds)...")
            await asyncio.sleep(4)
            return self.mock_audio_url

        generate_url = f"{self.base_url}/v2/music/generate"
        payload = {
            "model": "suno",
            "prompt": lyrics,
            "sunoParams": {
                "custom_mode": True,
                "style": tags,
                "title": title,
                "instrumental": False,
            },
        }

        async with self._session.post(generate_url, headers=self._headers(), json=payload) as resp:
            text = await resp.text()
            if resp.status not in (200, 201, 202):
                raise RuntimeError(f"Apiframe generation error ({resp.status}): {text}")
            data = json.loads(text)
            task_id = data.get("jobId") or data.get("id") or (data.get("data") or {}).get("jobId")
            if not task_id:
                raise RuntimeError(f"No jobId returned by Apiframe: {text}")

        job_url = f"{self.base_url}/v2/jobs/{task_id}"
        start_time = time.monotonic()
        timeout = 240
        while time.monotonic() - start_time < timeout:
            await asyncio.sleep(2.5)
            async with self._session.get(job_url, headers=self._headers()) as poll_resp:
                if poll_resp.status != 200:
                    continue
                job_data = await poll_resp.json()
                status = str(job_data.get("status") or "").upper()
                if status == "COMPLETED":
                    result = job_data.get("result")
                    if isinstance(result, list) and len(result) > 0:
                        first = result[0]
                        url = first.get("audioUrl") or first.get("audio_url") or first.get("url") if isinstance(first, dict) else first
                        if url:
                            return str(url)
                    elif isinstance(result, dict):
                        url = result.get("audioUrl") or result.get("audio_url") or result.get("url")
                        if url:
                            return str(url)
                    direct = job_data.get("audioUrl") or job_data.get("audio_url") or job_data.get("url")
                    if direct:
                        return str(direct)
                elif status in ("FAILED", "ERROR", "CANCELLED"):
                    err = job_data.get("error") or job_data.get("message") or "Generation failed"
                    raise RuntimeError(f"Suno generation failed: {err}")

        raise TimeoutError(f"Generation timed out after {timeout} seconds.")


# ---------------------------------------------------------------------------
# Background Worker Pool (5 Concurrent Slots)
# ---------------------------------------------------------------------------
async def worker_loop(
    worker_id: int,
    queue: asyncio.Queue[GenerationJob],
    bot: Bot,
    db: DatabaseManager,
    suno_service: SunoGatewayService,
) -> None:
    """
    Worker task pulling jobs from asyncio.Queue.
    Maintains strict concurrency limit of 5 workers.
    """
    logger.info("Generation Worker #%d started and ready for jobs.", worker_id)
    while True:
        job = await queue.get()
        job.enqueued_at = time.time()
        logger.info("Worker #%d started job %s for user %d", worker_id, job.charge_id, job.user_id)

        try:
            # 1. Update DB to PROCESSING
            await db.update_status(charge_id=job.charge_id, status="PROCESSING")

            # 2. Inform user generation has started
            await bot.send_chat_action(chat_id=job.chat_id, action=ChatAction.RECORD_VOICE)
            status_text = get_text("studio_slot_available", job.lang)
            status_msg = await bot.send_message(chat_id=job.chat_id, text=status_text)

            # 3. Call Apiframe Suno API
            audio_url = await suno_service.generate_song(
                lyrics=job.prompt,
                tags=job.tags,
                title=job.title,
            )

            # 4. Deliver audio to user
            await bot.send_chat_action(chat_id=job.chat_id, action=ChatAction.UPLOAD_VOICE)
            audio_file = URLInputFile(audio_url, filename=f"Song_{job.name}.mp3")
            caption = get_text(
                "song_ready_caption",
                job.lang,
                name=job.name,
                occasion=job.occasion,
                genre=job.genre_name,
            )

            await bot.send_audio(
                chat_id=job.chat_id,
                audio=audio_file,
                caption=caption,
                title=job.title,
                performer="Suno AI",
            )

            try:
                await bot.delete_message(chat_id=job.chat_id, message_id=status_msg.message_id)
            except Exception:
                pass

            # 5. Update DB to COMPLETED
            await db.update_status(charge_id=job.charge_id, status="COMPLETED", audio_url=audio_url)

            # Offer to create another song
            await bot.send_message(
                chat_id=job.chat_id,
                text=get_text("order_another", job.lang),
                reply_markup=get_restart_keyboard(job.lang),
            )
            logger.info("Worker #%d successfully completed job %s", worker_id, job.charge_id)

        except Exception as exc:
            logger.exception("Worker #%d failed on job %s: %s", worker_id, job.charge_id, exc)

            # 1. Update DB to REFUNDED
            await db.update_status(charge_id=job.charge_id, status="REFUNDED")

            # 2. Refund Telegram Stars if real payment
            if not job.charge_id.startswith("test_"):
                try:
                    await bot.refund_star_payment(
                        user_id=job.user_id,
                        telegram_payment_charge_id=job.charge_id,
                    )
                    logger.info("Successfully refunded Stars for charge %s to user %d", job.charge_id, job.user_id)
                except Exception as ref_err:
                    logger.error("Failed to refund Stars for %s: %s", job.charge_id, ref_err)

            # 3. Inform user with mandatory notification in user's language
            await bot.send_message(
                chat_id=job.chat_id,
                text=get_text("stars_refund_notice", job.lang),
                reply_markup=get_restart_keyboard(job.lang),
            )

        finally:
            queue.task_done()


# ---------------------------------------------------------------------------
# Router & Handlers
# ---------------------------------------------------------------------------
router = Router(name="main_song_router")


@router.message(CommandStart())
@router.message(Command("lang", "language"))
@router.callback_query(F.data == "change_lang")
async def cmd_language_selection(event: Message | CallbackQuery, state: FSMContext) -> None:
    """
    Shows Language Selection keyboard so the user can freely choose language:
    Kazakh, Russian, or English.
    """
    if isinstance(event, CallbackQuery):
        await event.answer()
        msg = event.message
    else:
        msg = event

    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)

    await state.set_state(OrderStates.language)
    await msg.answer(
        text=get_text("choose_language", lang),
        reply_markup=get_language_keyboard(),
    )


@router.callback_query(F.data.startswith("set_lang:"))
async def cb_set_language(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Sets chosen language, greets user in that language, and prompts for Occasion (Step 1).
    """
    await callback.answer()
    lang = callback.data.split(":", 1)[1]
    if lang not in (LANG_KK, LANG_RU, LANG_EN):
        lang = DEFAULT_LANGUAGE

    await state.clear()
    await state.update_data(lang=lang)
    await state.set_state(OrderStates.occasion)

    confirm_msg = get_text("language_selected", lang)
    prompt_text = get_text("step_occasion_first", lang)

    await callback.message.answer(
        text=f"{confirm_msg}\n\n{prompt_text}",
        reply_markup=get_occasions_keyboard(lang),
    )


@router.message(Command("new_song"))
@router.callback_query(F.data == "new_order")
async def cmd_start_new_order(event: Message | CallbackQuery, state: FSMContext) -> None:
    """
    Starts new song creation workflow while preserving selected language.
    """
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)

    await state.clear()
    await state.update_data(lang=lang)
    await state.set_state(OrderStates.occasion)

    prompt_text = get_text("step_occasion_first", lang)
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(text=prompt_text, reply_markup=get_occasions_keyboard(lang))
    else:
        await event.answer(text=prompt_text, reply_markup=get_occasions_keyboard(lang))


@router.callback_query(OrderStates.occasion, F.data.startswith("occ:"))
async def cb_occasion(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 1 -> Step 2: Occasion selected via button."""
    await callback.answer()
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)

    occasion_val = callback.data.split(":", 1)[1]
    await state.update_data(occasion=occasion_val)
    await state.set_state(OrderStates.details)

    await callback.message.answer(text=get_text("step_details_name_facts", lang))


@router.message(OrderStates.occasion, F.text)
async def msg_custom_occasion(message: Message, state: FSMContext) -> None:
    """Step 1 -> Step 2: Custom occasion typed as text."""
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)

    occasion = (message.text or "").strip()
    if len(occasion) < 3 or len(occasion) > 100:
        await message.answer(get_text("occasion_error", lang))
        return

    await state.update_data(occasion=occasion)
    await state.set_state(OrderStates.details)
    await message.answer(get_text("step_details_name_facts", lang))


@router.message(OrderStates.details, F.text)
async def msg_details(message: Message, state: FSMContext) -> None:
    """Step 2 -> Step 3: Name & facts received. Prompt for music genre."""
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)

    raw_text = (message.text or "").strip()
    if len(raw_text) < 5 or len(raw_text) > 1000:
        await message.answer(get_text("details_error", lang))
        return

    first_part = raw_text.split("\n")[0].split(".")[0].strip()
    name = first_part[:40] if first_part else ("Дос" if lang == "kk" else "Друг")

    await state.update_data(name=name, details=raw_text)
    await state.set_state(OrderStates.genre)

    await message.answer(
        text=get_text("step_genre", lang),
        reply_markup=get_genres_keyboard(lang),
    )


@router.callback_query(OrderStates.genre, F.data.startswith("gnr:"))
async def cb_genre(
    callback: CallbackQuery,
    state: FSMContext,
    gemini_service: GeminiContentService,
) -> None:
    """
    Step 3 -> Step 4 & 5: Genre selected.
    Calls Gemini API in JSON mode (moderation + lyrics) in the chosen language.
    If safe: displays preview with mandatory disclaimer and approval button.
    If unsafe: shows reason and keeps user at OrderStates.details.
    """
    await callback.answer()
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)

    genre_id = callback.data.split(":", 1)[1]
    genre_label = get_genre_label(genre_id, lang)
    genre_style = get_genre_style(genre_id)

    await state.update_data(genre_id=genre_id, genre_label=genre_label, genre_style=genre_style)

    name = data.get("name", "Друг")
    occasion = data.get("occasion", "Праздник")
    details = data.get("details", "")

    wait_msg = await callback.message.answer(get_text("generating_lyrics", lang))

    try:
        res = await gemini_service.moderate_and_compose(
            name=name,
            occasion=occasion,
            details=details,
            genre_title=genre_label,
            genre_tags=genre_style,
            language=lang,
        )
    except Exception as err:
        logger.error("Gemini failed: %s", err)
        await wait_msg.edit_text(
            get_text("lyrics_failed", lang, err=str(err)),
            reply_markup=get_restart_keyboard(lang),
        )
        return

    try:
        await wait_msg.delete()
    except Exception:
        pass

    # Moderation check
    if not res.get("is_safe", True):
        reason = res.get("reason") or "Контент не прошел проверку безопасности."
        await state.set_state(OrderStates.details)
        await callback.message.answer(get_text("moderation_failed", lang, reason=reason))
        return

    # Moderation passed: Step 5 preview
    lyrics = res.get("lyrics") or ""
    tags = res.get("tags") or genre_style
    title = res.get("title") or f"Песня для {name}"

    await state.update_data(lyrics=lyrics, tags=tags, title=title)
    await state.set_state(OrderStates.preview_approval)

    preview_text = get_text(
        "preview_lyrics",
        lang,
        name=name,
        genre=genre_label,
        occasion=occasion,
        lyrics=lyrics,
    )

    await callback.message.answer(
        text=preview_text,
        reply_markup=get_preview_keyboard(lang, is_test=TEST_PAYMENT_MODE),
    )


@router.callback_query(OrderStates.preview_approval, F.data.startswith("prv:"))
async def cb_preview_action(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    db: DatabaseManager,
    suno_service: SunoGatewayService,
    queue: asyncio.Queue[GenerationJob],
) -> None:
    """
    Step 5 Approval:
    - 'restart': clears state and goes to Step 1.
    - 'approve':
      * If TEST_PAYMENT_MODE: checks health, saves to DB, and enqueues task immediately.
      * If Real: sends Telegram Stars (60 XTR) invoice.
    """
    action = callback.data.split(":", 1)[1]
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)

    if action == "restart":
        await callback.answer()
        await state.clear()
        await state.update_data(lang=lang)
        await state.set_state(OrderStates.occasion)
        await callback.message.answer(
            get_text("step_occasion_first", lang),
            reply_markup=get_occasions_keyboard(lang),
        )
        return

    if action == "approve":
        await callback.answer()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        name = data.get("name", "Друг")
        occasion = data.get("occasion", "Праздник")
        genre_label = data.get("genre_label", "Поп")
        tags = data.get("tags", "")
        lyrics = data.get("lyrics", "")
        title = data.get("title", f"Песня для {name}")

        # Test Payment Mode (Free 0 Stars)
        if TEST_PAYMENT_MODE:
            is_healthy = await suno_service.check_health(timeout=3.0)
            if not is_healthy:
                await callback.message.answer(
                    text=get_text("pre_checkout_error", lang),
                    reply_markup=get_preview_keyboard(lang, is_test=True),
                )
                return

            test_charge_id = f"test_free_{user_id}_{int(time.time())}"

            await db.create_order(
                charge_id=test_charge_id,
                user_id=user_id,
                prompt=lyrics,
                tags=tags,
                status="PAID",
            )

            job = GenerationJob(
                charge_id=test_charge_id,
                user_id=user_id,
                chat_id=chat_id,
                prompt=lyrics,
                tags=tags,
                title=title,
                name=name,
                occasion=occasion,
                genre_name=genre_label,
                lang=lang,
            )
            await queue.put(job)
            await state.set_state(OrderStates.generating_audio)

            await callback.message.answer(get_text("test_payment_confirmed", lang))
            return

        # Real Mode: Telegram Stars (60 XTR) Invoice
        await state.set_state(OrderStates.waiting_payment)
        prices = [LabeledPrice(label=get_text("stars_invoice_label", lang), amount=60)]
        payload = f"song_{user_id}_{int(time.time())}"

        await bot.send_invoice(
            chat_id=chat_id,
            title=get_text("stars_invoice_title", lang),
            description=get_text("stars_invoice_desc", lang),
            payload=payload,
            currency="XTR",
            prices=prices,
            provider_token="",  # Empty string is required for Telegram Stars
        )


@router.pre_checkout_query()
async def process_pre_checkout(
    query: PreCheckoutQuery,
    state: FSMContext,
    suno_service: SunoGatewayService,
) -> None:
    """
    Telegram Stars PreCheckout:
    Performs fast 3-second healthcheck to Apiframe Suno API.
    Rejects payment without debiting Stars if the studio is unavailable.
    """
    data = await state.get_data()
    lang = data.get("lang") or query.from_user.language_code or DEFAULT_LANGUAGE

    is_healthy = await suno_service.check_health(timeout=3.0)
    if not is_healthy:
        logger.warning("PreCheckout rejected: Apiframe is unreachable.")
        await query.answer(ok=False, error_message=get_text("pre_checkout_error", lang))
        return

    await query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(
    message: Message,
    state: FSMContext,
    db: DatabaseManager,
    queue: asyncio.Queue[GenerationJob],
) -> None:
    """
    Telegram Stars Payment Successful (60 XTR):
    Saves order in SQLite DB as PAID and enqueues to the 5-worker pool.
    """
    payment = message.successful_payment
    charge_id = payment.telegram_payment_charge_id
    user_id = message.from_user.id
    chat_id = message.chat.id

    logger.info("Payment confirmed: %d %s, charge_id=%s", payment.total_amount, payment.currency, charge_id)

    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)
    name = data.get("name", "Друг")
    occasion = data.get("occasion", "Праздник")
    genre_label = data.get("genre_label", "Поп")
    tags = data.get("tags", "")
    lyrics = data.get("lyrics", "")
    title = data.get("title", f"Песня для {name}")

    # 1. Save order to SQLite database with status PAID
    await db.create_order(
        charge_id=charge_id,
        user_id=user_id,
        prompt=lyrics,
        tags=tags,
        status="PAID",
    )

    # 2. Enqueue job into 5-worker pool
    job = GenerationJob(
        charge_id=charge_id,
        user_id=user_id,
        chat_id=chat_id,
        prompt=lyrics,
        tags=tags,
        title=title,
        name=name,
        occasion=occasion,
        genre_name=genre_label,
        lang=lang,
    )
    await queue.put(job)
    await state.set_state(OrderStates.generating_audio)

    q_pos = queue.qsize()
    pos_info = f" ({q_pos})" if q_pos > 1 else ""
    await message.answer(f"🌟 <b>Stars payment confirmed!</b>{pos_info}")


# ---------------------------------------------------------------------------
# Application Entrypoint
# ---------------------------------------------------------------------------
async def main() -> None:
    logger.info("Initializing Telegram Song Bot backend with multilingual support...")

    # 1. Initialize SQLite Database with WAL mode
    db = DatabaseManager(db_path="bot_orders.db")
    await db.init_db()

    # 2. Shared aiohttp session for external APIs
    session = aiohttp.ClientSession()

    # 3. AI and Music Services
    gemini_service = GeminiContentService(api_key=GEMINI_API_KEY, model=GEMINI_MODEL)
    suno_service = SunoGatewayService(
        api_key=APIFRAME_API_KEY,
        base_url=APIFRAME_BASE_URL,
        use_mock=USE_MOCK_MUSIC,
        mock_audio_url=MOCK_AUDIO_URL,
        session=session,
    )

    # 4. Initialize Telegram Bot & Dispatcher
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # 5. Concurrency Queue & 5-Worker Pool
    queue: asyncio.Queue[GenerationJob] = asyncio.Queue()
    workers = [
        asyncio.create_task(
            worker_loop(i + 1, queue, bot, db, suno_service),
            name=f"Worker-{i + 1}",
        )
        for i in range(MAX_CONCURRENT_GENERATIONS)
    ]
    logger.info("Started %d concurrent background workers.", MAX_CONCURRENT_GENERATIONS)

    # 6. Register dependency injection for handlers
    dp.workflow_data.update(
        {
            "db": db,
            "gemini_service": gemini_service,
            "suno_service": suno_service,
            "queue": queue,
        }
    )
    dp.include_router(router)

    # 7. Start bot polling with auto-reconnect
    async def start_polling() -> None:
        while True:
            try:
                await bot.delete_webhook(drop_pending_updates=True)
                suno_info = "MOCK (credits protected)" if USE_MOCK_MUSIC else "Apiframe.ai"
                logger.info("Bot started! Gemini: %s | Suno: %s | Workers: %d", GEMINI_MODEL, suno_info, MAX_CONCURRENT_GENERATIONS)
                await dp.start_polling(bot)
                break
            except (TelegramNetworkError, aiohttp.ClientError, ConnectionResetError) as net_err:
                logger.warning("Network issue: %s. Retrying in 3s...", net_err)
                await asyncio.sleep(3)
            except Exception as exc:
                logger.exception("Fatal polling error: %s", exc)
                break

    try:
        await start_polling()
    finally:
        logger.info("Shutting down bot and cleaning up resources...")
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        await db.close()
        await session.close()
        await bot.session.close()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user.")
