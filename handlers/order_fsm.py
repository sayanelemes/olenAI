import logging
import time
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    PreCheckoutQuery,
    LabeledPrice,
)

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
from config import get_settings
from states.order import OrderStates
from services.generation_queue import GenerationQueue
from services.llm_service import LLMService
from services.suno_service import SunoService
from locales import (
    DEFAULT_LANGUAGE,
    get_genre_label,
    get_genre_style,
    get_text,
)

logger = logging.getLogger(__name__)
router = Router(name="order_fsm_router")


# ---------------------------------------------------------------------------
# Step 1: Start Order -> Select Occasion
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "start_order")
@router.message(Command("new_song"))
async def start_order_flow(event: Message | CallbackQuery, state: FSMContext) -> None:
    """
    Entry point for creating a song order.
    Preserves chosen language and prompts for the occasion (Step 1).
    """
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)

    # Clear previous order data while preserving user language
    await state.clear()
    await state.set_data({"lang": lang})
    await state.set_state(OrderStates.occasion)

    prompt_text = get_text("step_occasion_first", lang)

    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(text=prompt_text, reply_markup=get_occasions_keyboard(lang))
    else:
        await event.answer(text=prompt_text, reply_markup=get_occasions_keyboard(lang))


# ---------------------------------------------------------------------------
# Step 1 -> Step 2: Handle Occasion (Button or Text) -> Ask for Name & Facts
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
    await state.set_state(OrderStates.name)

    await callback.message.answer(
        text=get_text("step_name", lang),
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
    await state.set_state(OrderStates.name)

    await message.answer(
        text=get_text("step_name", lang),
        reply_markup=get_cancel_keyboard(lang),
    )


# ---------------------------------------------------------------------------
# Step 2: Handle Recipient Name -> Ask for Personal Facts / Details
# ---------------------------------------------------------------------------
@router.message(OrderStates.name, F.text)
async def process_name(message: Message, state: FSMContext) -> None:
    """
    Save recipient name and prompt for personal facts and wishes.
    """
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)

    raw_name = (message.text or "").strip()
    if len(raw_name) < 2 or len(raw_name) > 60:
        await message.answer(
            text=get_text("name_error", lang),
            reply_markup=get_cancel_keyboard(lang),
        )
        return

    await state.update_data(name=raw_name)
    await state.set_state(OrderStates.details)

    await message.answer(
        text=get_text("step_details", lang, name=raw_name, occasion=data.get("occasion", "Праздник")),
        reply_markup=get_cancel_keyboard(lang),
    )


# ---------------------------------------------------------------------------
# Step 3: Handle Personal Facts -> Ask for Genre (or Regenerate)
# ---------------------------------------------------------------------------
@router.message(OrderStates.details, F.text)
async def process_details(
    message: Message,
    state: FSMContext,
    llm_service: LLMService,
) -> None:
    """
    Save 2-3 personal facts/wishes.
    If genre is already selected (e.g. from '🔄 Изменить детали'),
    style is preserved and we directly re-run moderation and lyrics generation.
    Otherwise, prompts for music genre (Step 4).
    """
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)

    raw_text = (message.text or "").strip()
    if len(raw_text) < 5 or len(raw_text) > 1000:
        await message.answer(
            text=get_text("details_error", lang),
            reply_markup=get_cancel_keyboard(lang),
        )
        return

    name = data.get("name") or ("Дос" if lang == "kk" else "Друг")
    await state.update_data(details=raw_text)

    # Check if genre was already chosen previously (e.g. returning via «🔄 Изменить детали»)
    existing_genre = data.get("genre")
    if existing_genre:
        await _moderate_and_generate_lyrics_step(
            message=message,
            state=state,
            llm_service=llm_service,
            name=name,
            occasion=data.get("occasion", "Праздник"),
            details=raw_text,
            genre=existing_genre,
            lang=lang,
        )
        return

    await state.set_state(OrderStates.genre)
    await message.answer(
        text=get_text("step_genre", lang),
        reply_markup=get_genres_keyboard(lang),
    )


# ---------------------------------------------------------------------------
# Step 3: Handle Genre -> Step 4: Moderate & Generate Lyrics via Gemini
# ---------------------------------------------------------------------------
@router.callback_query(OrderStates.genre, GenreCallback.filter())
async def process_genre(
    callback: CallbackQuery,
    callback_data: GenreCallback,
    state: FSMContext,
    llm_service: LLMService,
) -> None:
    """
    Save chosen style and execute Step 4:
    Unified Gemini call for moderation and lyrics generation in JSON mode.
    """
    await callback.answer()
    genre_style = callback_data.value
    await state.update_data(genre=genre_style)

    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)
    name = data.get("name", "Друг")
    occasion = data.get("occasion", "Праздник")
    details = data.get("details", "")

    await _moderate_and_generate_lyrics_step(
        message=callback.message,
        state=state,
        llm_service=llm_service,
        name=name,
        occasion=occasion,
        details=details,
        genre=genre_style,
        lang=lang,
    )


# ---------------------------------------------------------------------------
# Helper: Step 4 (Gemini JSON Moderation + Lyrics) -> Step 5 (Preview + Disclaimer)
# ---------------------------------------------------------------------------
async def _moderate_and_generate_lyrics_step(
    message: Message,
    state: FSMContext,
    llm_service: LLMService,
    name: str,
    occasion: str,
    details: str,
    genre: str,
    lang: str,
) -> None:
    """
    Unified Step 4 & 5:
    Calls Gemini in JSON mode:
    - If is_safe == False: outputs clear reason, does NOT reset occasion/genre,
      keeps user at OrderStates.details to rephrase personal facts.
    - If is_safe == True: shows lyrics, title, mandatory AI disclaimer, and approval keyboard.
    """
    status_msg = await message.answer(get_text("generating_lyrics", lang))

    genre_label = get_genre_label(genre, lang)
    genre_style = get_genre_style(genre)
    full_genre_prompt = f"{genre_label} ({genre_style})"

    try:
        res = await llm_service.moderate_and_generate_lyrics(
            name=name,
            occasion=occasion,
            details=details,
            genre=full_genre_prompt,
            language=lang,
        )
    except Exception as err:
        logger.error("Failed to generate lyrics via Gemini: %s", err)
        await status_msg.edit_text(
            text=get_text("lyrics_failed", lang, err=str(err)),
            reply_markup=get_start_keyboard(lang),
        )
        await state.clear()
        await state.set_data({"lang": lang})
        return

    # 1. Moderation Check
    if not res.get("is_safe", True):
        reason = res.get("reason") or "Контент нарушает правила безопасности."
        logger.warning("Input moderation rejected. Reason: %s", reason)
        try:
            await status_msg.delete()
        except Exception:
            pass

        # Return user to Step 2 without clearing occasion or genre
        await state.set_state(OrderStates.details)
        await message.answer(
            text=get_text("moderation_failed", lang, reason=reason),
            reply_markup=get_cancel_keyboard(lang),
        )
        return

    # 2. Moderation Passed: Display Lyrics and Mandatory Disclaimer (Step 5)
    lyrics = res.get("lyrics", "").strip()
    title = res.get("title", f"Песня для {name}").strip()

    await state.update_data(lyrics=lyrics, title=title)
    await state.set_state(OrderStates.preview_approval)

    preview_text = get_text(
        "preview_lyrics",
        lang,
        name=name,
        genre=genre_label,
        occasion=occasion,
        lyrics=lyrics,
    )

    try:
        await status_msg.delete()
    except Exception:
        pass

    settings = get_settings()
    await message.answer(
        text=preview_text,
        reply_markup=get_preview_approval_keyboard(lang, is_test=settings.TEST_PAYMENT_MODE),
    )


# ---------------------------------------------------------------------------
# Step 5: Preview Actions (Approve -> Stars Invoice / Free Test, Edit, Cancel)
# ---------------------------------------------------------------------------
@router.callback_query(OrderStates.preview_approval, PreviewActionCallback.filter())
async def process_preview_action(
    callback: CallbackQuery,
    callback_data: PreviewActionCallback,
    state: FSMContext,
    bot: Bot,
    suno_service: SunoService,
    generation_queue: GenerationQueue,
) -> None:
    """
    Handle user decision:
    - 'approve':
      * In TEST_PAYMENT_MODE: simulates free payment (0 Stars), checks health, and submits job immediately.
      * In Real mode: Transitions to waiting_payment and sends Telegram Stars (60 XTR) invoice.
    - 'edit_details': Returns to Step 2 (OrderStates.details) keeping selected genre and occasion.
    - 'cancel': Cancels order flow.
    """
    action = callback_data.action
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)
    settings = get_settings()

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

    if action == "edit_details":
        await callback.answer()
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        # Preserve occasion and genre, just re-ask for details
        name = data.get("name", "Друг")
        occasion = data.get("occasion", "Праздник")
        await state.set_state(OrderStates.details)
        await callback.message.answer(
            text=get_text("step_details", lang, name=name, occasion=occasion),
            reply_markup=get_cancel_keyboard(lang),
        )
        return

    if action == "approve":
        # -------------------------------------------------------------------
        # Test / Free Payment Mode
        # -------------------------------------------------------------------
        if settings.TEST_PAYMENT_MODE:
            await callback.answer()
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass

            # Pre-checkout health check to Apiframe
            is_healthy = await suno_service.check_health(timeout=3.0)
            if not is_healthy:
                logger.warning(
                    "Test payment aborted for user %d: Apiframe Suno API is unhealthy/unreachable.",
                    callback.from_user.id,
                )
                await callback.message.answer(
                    text=get_text("pre_checkout_error", lang),
                    reply_markup=get_preview_approval_keyboard(lang, is_test=True),
                )
                return

            # Prevent double generation
            await state.set_state(OrderStates.generating_audio)
            await callback.message.answer(get_text("test_payment_confirmed", lang))

            name = data.get("name", "Друг")
            occasion = data.get("occasion", "Праздник")
            genre_key = data.get("genre", "qpop")
            genre_style = get_genre_style(genre_key)
            lyrics = data.get("lyrics", "")

            # Submit job with simulated charge_id
            test_charge_id = f"test_free_{callback.from_user.id}_{int(time.time())}"
            await generation_queue.submit_job(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                name=name,
                occasion=occasion,
                genre=genre_style,
                lyrics=lyrics,
                lang=lang,
                charge_id=test_charge_id,
            )

            # Clear order state data, preserving user language
            await state.clear()
            await state.set_data({"lang": lang})
            return

        # -------------------------------------------------------------------
        # Real Payment Mode: Telegram Stars (60 XTR) Invoice
        # -------------------------------------------------------------------
        await callback.answer()
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        await state.set_state(OrderStates.waiting_payment)

        # Send Telegram Stars (XTR) Invoice for 60 Stars
        prices = [LabeledPrice(label=get_text("stars_invoice_label", lang), amount=60)]
        payload = f"song_{callback.from_user.id}_{int(time.time())}"

        await bot.send_invoice(
            chat_id=callback.message.chat.id,
            title=get_text("stars_invoice_title", lang),
            description=get_text("stars_invoice_desc", lang),
            payload=payload,
            currency="XTR",
            prices=prices,
            provider_token="",  # Required empty string for Telegram Stars
        )
        return


# ---------------------------------------------------------------------------
# Pre-Checkout Query: Healthcheck to Apiframe (GET /v2/models with 3s timeout)
# ---------------------------------------------------------------------------
@router.pre_checkout_query()
async def process_pre_checkout_query(
    pre_checkout_query: PreCheckoutQuery,
    state: FSMContext,
    suno_service: SunoService,
) -> None:
    """
    Fast pre-checkout check:
    Ensures Apiframe Suno API is reachable within 3 seconds.
    If unavailable, rejects payment so no Stars are deducted.
    """
    data = await state.get_data()
    lang = data.get("lang") or pre_checkout_query.from_user.language_code or DEFAULT_LANGUAGE

    is_healthy = await suno_service.check_health(timeout=3.0)
    if not is_healthy:
        logger.warning(
            "PreCheckoutQuery rejected for user %d: Apiframe Suno API is unhealthy/unreachable.",
            pre_checkout_query.from_user.id,
        )
        await pre_checkout_query.answer(
            ok=False,
            error_message=get_text("pre_checkout_error", lang),
        )
        return

    await pre_checkout_query.answer(ok=True)


# ---------------------------------------------------------------------------
# Successful Payment: Enqueue to 5-Worker Pool with Charge ID
# ---------------------------------------------------------------------------
@router.message(F.successful_payment)
async def process_successful_payment(
    message: Message,
    state: FSMContext,
    generation_queue: GenerationQueue,
) -> None:
    """
    Payment confirmed!
    Captures telegram_payment_charge_id and submits job to the 5-slot GenerationQueue.
    """
    payment = message.successful_payment
    charge_id = payment.telegram_payment_charge_id
    logger.info(
        "Payment confirmed: %d %s from user %d. Charge ID: %s",
        payment.total_amount,
        payment.currency,
        message.from_user.id,
        charge_id,
    )

    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)
    name = data.get("name", "Друг")
    occasion = data.get("occasion", "Праздник")
    genre_key = data.get("genre", "qpop")
    genre_style = get_genre_style(genre_key)
    lyrics = data.get("lyrics", "")

    # Prevent concurrent clicks during generation
    await state.set_state(OrderStates.generating_audio)

    # Enqueue to 5-slot concurrency queue with charge_id
    await generation_queue.submit_job(
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        name=name,
        occasion=occasion,
        genre=genre_style,
        lyrics=lyrics,
        lang=lang,
        charge_id=charge_id,
    )

    # Clear order state data, preserving user language
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
