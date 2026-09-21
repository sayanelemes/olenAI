import logging
from aiogram import Router, F, Bot
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, URLInputFile

from keyboards.inline import (
    OccasionCallback,
    GenreCallback,
    PreviewActionCallback,
    get_occasions_keyboard,
    get_genres_keyboard,
    get_preview_approval_keyboard,
    get_cancel_keyboard,
    get_start_keyboard,
)
from states.order import OrderStates
from services.llm_service import LLMService, LLMServiceError
from services.suno_service import (
    SunoService,
    SunoServiceError,
    InsufficientCreditsError,
)
from services.ui_animator import UIAnimator
from locales import get_text, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)
router = Router(name="order_fsm_router")


# ---------------------------------------------------------------------------
# Step 1: Start Order -> Ask for Recipient Name
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "start_order")
@router.message(Command("new_song"))
async def start_order_flow(event: Message | CallbackQuery, state: FSMContext) -> None:
    """
    Entry point for creating a song order.
    Preserves chosen language and prompts for the recipient's name.
    """
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)

    # Clear previous order data while preserving user language
    await state.set_data({"lang": lang})
    await state.set_state(OrderStates.name)

    prompt_text = get_text("step_name", lang)

    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(text=prompt_text, reply_markup=get_cancel_keyboard(lang))
    else:
        await event.answer(text=prompt_text, reply_markup=get_cancel_keyboard(lang))


# ---------------------------------------------------------------------------
# Step 2: Handle Name -> Ask for Occasion
# ---------------------------------------------------------------------------
@router.message(OrderStates.name, F.text)
async def process_recipient_name(message: Message, state: FSMContext) -> None:
    """
    Validate and save recipient name, prompt for occasion.
    """
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)

    name = (message.text or "").strip()
    if len(name) < 2 or len(name) > 60:
        await message.answer(
            text=get_text("name_error", lang),
            reply_markup=get_cancel_keyboard(lang),
        )
        return

    await state.update_data(name=name)
    await state.set_state(OrderStates.occasion)

    await message.answer(
        text=get_text("step_occasion", lang, name=name),
        reply_markup=get_occasions_keyboard(lang),
    )


# ---------------------------------------------------------------------------
# Step 3: Handle Occasion (button or text) -> Ask for Details
# ---------------------------------------------------------------------------
@router.callback_query(OrderStates.occasion, OccasionCallback.filter())
async def process_occasion_callback(
    callback: CallbackQuery,
    callback_data: OccasionCallback,
    state: FSMContext,
) -> None:
    """
    Handle occasion selected via inline button.
    """
    await callback.answer()
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)

    occasion = callback_data.value
    await state.update_data(occasion=occasion)
    await state.set_state(OrderStates.details)

    await callback.message.answer(
        text=get_text("step_details", lang, occasion=occasion),
        reply_markup=get_cancel_keyboard(lang),
    )


@router.message(OrderStates.occasion, F.text)
async def process_occasion_text(message: Message, state: FSMContext) -> None:
    """
    Handle custom occasion sent as text message.
    """
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)

    occasion = (message.text or "").strip()
    if len(occasion) < 3 or len(occasion) > 100:
        await message.answer(
            text=get_text("occasion_error", lang),
            reply_markup=get_cancel_keyboard(lang),
        )
        return

    await state.update_data(occasion=occasion)
    await state.set_state(OrderStates.details)

    await message.answer(
        text=get_text("step_details", lang, occasion=occasion),
        reply_markup=get_cancel_keyboard(lang),
    )


# ---------------------------------------------------------------------------
# Step 4: Handle Details -> Ask for Music Genre
# ---------------------------------------------------------------------------
@router.message(OrderStates.details, F.text)
async def process_details(message: Message, state: FSMContext) -> None:
    """
    Save personal details and prompt for music genre.
    """
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)

    details = (message.text or "").strip()
    if len(details) < 10 or len(details) > 1000:
        await message.answer(
            text=get_text("details_error", lang),
            reply_markup=get_cancel_keyboard(lang),
        )
        return

    await state.update_data(details=details)
    await state.set_state(OrderStates.genre)

    await message.answer(
        text=get_text("step_genre", lang),
        reply_markup=get_genres_keyboard(lang),
    )


# ---------------------------------------------------------------------------
# Step 5: Handle Genre -> Generate Lyrics via Gemini in Selected Language
# ---------------------------------------------------------------------------
@router.callback_query(OrderStates.genre, GenreCallback.filter())
async def process_genre(
    callback: CallbackQuery,
    callback_data: GenreCallback,
    state: FSMContext,
    llm_service: LLMService,
) -> None:
    """
    Save chosen style and generate song lyrics in user's language (kk, ru, en).
    """
    await callback.answer()
    genre_style = callback_data.value
    await state.update_data(genre=genre_style)

    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)

    status_msg = await callback.message.answer(get_text("generating_lyrics", lang))

    try:
        async with UIAnimator(message=status_msg, lang=lang, show_progress_bar=False):
            lyrics = await llm_service.generate_lyrics(
                name=data["name"],
                occasion=data["occasion"],
                details=data["details"],
                genre=genre_style,
                language=lang,
            )
    except LLMServiceError as err:
        logger.error("Failed to generate lyrics: %s", err)
        await status_msg.edit_text(
            text=get_text("lyrics_failed", lang, err=str(err)),
            reply_markup=get_start_keyboard(lang),
        )
        # Keep user language upon clearing order state
        await state.set_data({"lang": lang})
        return

    await state.update_data(lyrics=lyrics)
    await state.set_state(OrderStates.preview_approval)

    preview_text = get_text(
        "preview_caption",
        lang,
        name=data["name"],
        genre=genre_style,
        occasion=data["occasion"],
        lyrics=lyrics,
    )

    await status_msg.delete()
    await callback.message.answer(
        text=preview_text,
        reply_markup=get_preview_approval_keyboard(lang),
    )


# ---------------------------------------------------------------------------
# Step 6: Preview Actions (Approve -> Suno, Rewrite -> Gemini, Cancel)
# ---------------------------------------------------------------------------
@router.callback_query(OrderStates.preview_approval, PreviewActionCallback.filter())
async def process_preview_action(
    callback: CallbackQuery,
    callback_data: PreviewActionCallback,
    state: FSMContext,
    bot: Bot,
    llm_service: LLMService,
    suno_service: SunoService,
) -> None:
    """
    Handle user decision: approve audio generation, rewrite lyrics, or cancel.
    Includes handling for Apiframe 402 Insufficient credits.
    """
    action = callback_data.action
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)

    if action == "cancel":
        await callback.answer()
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await state.clear()
        await state.set_data({"lang": lang})
        await callback.message.answer(
            text=get_text("order_canceled", lang),
            reply_markup=get_start_keyboard(lang),
        )
        return

    if action == "rewrite":
        await callback.answer()
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        status_msg = await callback.message.answer(get_text("rewriting_lyrics", lang))

        try:
            async with UIAnimator(message=status_msg, lang=lang, show_progress_bar=False):
                new_lyrics = await llm_service.generate_lyrics(
                    name=data["name"],
                    occasion=data["occasion"],
                    details=data["details"],
                    genre=data["genre"],
                    language=lang,
                )
        except LLMServiceError as err:
            logger.error("Failed to rewrite lyrics: %s", err)
            await status_msg.edit_text(
                text=get_text("lyrics_failed", lang, err=str(err)),
                reply_markup=get_preview_approval_keyboard(lang),
            )
            return

        await state.update_data(lyrics=new_lyrics)
        preview_text = get_text(
            "preview_caption",
            lang,
            name=data["name"],
            genre=data["genre"],
            occasion=data["occasion"],
            lyrics=new_lyrics,
        )

        await status_msg.delete()
        await callback.message.answer(
            text=preview_text,
            reply_markup=get_preview_approval_keyboard(lang),
        )
        return

    if action == "approve":
        # 1. Guard against duplicate clicks
        current_state = await state.get_state()
        if current_state == OrderStates.generating_audio.state:
            await callback.answer(get_text("already_generating", lang), show_alert=True)
            return

        # 2. Immediately transition to generating_audio and remove buttons
        await state.set_state(OrderStates.generating_audio)
        await callback.answer()
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        status_msg = await callback.message.answer(get_text("generating_audio", lang))

        chat_id = callback.message.chat.id
        title = f"Song for {data['name']}"

        try:
            # 1. Send recording action
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)

            # 2. Animate waiting status while submitting and generating with Suno
            async with UIAnimator(message=status_msg, lang=lang, show_progress_bar=True) as animator:
                task_id = await suno_service.create_song_task(
                    lyrics=data["lyrics"],
                    style=data["genre"],
                    title=title,
                )
                audio_url = await suno_service.wait_for_completion(
                    task_id=task_id,
                    timeout=240,
                    interval=2.0,
                    on_progress=animator.update_progress,
                )
                await animator.update_progress(100)

            # 3. Upload and send audio to Telegram user
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_VOICE)
            audio_file = URLInputFile(
                url=audio_url,
                filename=f"Song_{data['name']}.mp3"
            )

            caption = get_text(
                "song_ready_caption",
                lang,
                name=data["name"],
                occasion=data["occasion"],
                genre=data["genre"],
            )

            await bot.send_audio(
                chat_id=chat_id,
                audio=audio_file,
                caption=caption,
                title=title,
                performer="Suno AI",
            )
            try:
                await status_msg.delete()
            except Exception:
                pass

            # Clear FSM state and preserve user language for next order
            await state.clear()
            await state.set_data({"lang": lang})
            await bot.send_message(
                chat_id=chat_id,
                text=get_text("order_another", lang),
                reply_markup=get_start_keyboard(lang),
            )

        except InsufficientCreditsError as err:
            logger.error("Suno credits exhausted (HTTP 402): %s", err)
            error_message = get_text("credits_exhausted", lang)
            await status_msg.edit_text(
                text=error_message,
                reply_markup=get_start_keyboard(lang),
            )
            await state.clear()
            await state.set_data({"lang": lang})

        except TimeoutError as err:
            logger.error("Suno generation timed out: %s", err)
            await status_msg.edit_text(
                text=get_text("audio_timeout", lang),
                reply_markup=get_start_keyboard(lang),
            )
            await state.clear()
            await state.set_data({"lang": lang})

        except SunoServiceError as err:
            logger.error("Suno service error: %s", err)
            await status_msg.edit_text(
                text=get_text("audio_failed", lang, err=str(err)),
                reply_markup=get_start_keyboard(lang),
            )
            await state.clear()
            await state.set_data({"lang": lang})

        except Exception as exc:
            logger.exception("Unexpected error during song generation: %s", exc)
            await status_msg.edit_text(
                text=get_text("audio_failed", lang, err="Internal error"),
                reply_markup=get_start_keyboard(lang),
            )
            await state.clear()
            await state.set_data({"lang": lang})


# ---------------------------------------------------------------------------
# Guard: reject any button clicks while audio is generating
# ---------------------------------------------------------------------------
@router.callback_query(OrderStates.generating_audio)
async def process_action_while_generating(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)
    await callback.answer(get_text("already_generating", lang), show_alert=True)
