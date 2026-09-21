import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from keyboards.inline import (
    LanguageCallback,
    get_language_keyboard,
    get_start_keyboard,
)
from locales import get_text, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)
router = Router(name="start_router")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """
    Handle /start command.
    Prompts user with language selection step (Kazakh, Russian, English).
    """
    await state.clear()
    await message.answer(
        text=get_text("choose_language", DEFAULT_LANGUAGE),
        reply_markup=get_language_keyboard(),
    )


@router.message(Command("language"))
@router.callback_query(F.data == "change_language")
async def cmd_language(event: Message | CallbackQuery, state: FSMContext) -> None:
    """
    Prompt user to choose or change interface language.
    """
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)
    text = get_text("choose_language", lang)

    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(text=text, reply_markup=get_language_keyboard())
    else:
        await event.answer(text=text, reply_markup=get_language_keyboard())


@router.callback_query(LanguageCallback.filter())
async def process_language_choice(
    callback: CallbackQuery,
    callback_data: LanguageCallback,
    state: FSMContext,
) -> None:
    """
    Save chosen language and show main menu in that language.
    """
    await callback.answer()
    chosen_lang = callback_data.code
    await state.update_data(lang=chosen_lang)
    logger.info("User %s selected language: %s", callback.from_user.id, chosen_lang)

    confirm_text = get_text("language_selected", chosen_lang)
    welcome_text = get_text("start_welcome", chosen_lang)

    await callback.message.answer(confirm_text)
    await callback.message.answer(
        text=welcome_text,
        reply_markup=get_start_keyboard(chosen_lang),
    )


@router.message(Command("help"))
@router.callback_query(F.data == "how_it_works")
async def cmd_help(event: Message | CallbackQuery, state: FSMContext) -> None:
    """
    Show explanation of how the bot works in chosen language.
    """
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)
    help_text = get_text("how_it_works", lang)

    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(
            text=help_text,
            reply_markup=get_start_keyboard(lang),
        )
    else:
        await event.answer(
            text=help_text,
            reply_markup=get_start_keyboard(lang),
        )


@router.callback_query(F.data == "cancel_order")
@router.message(Command("cancel"), StateFilter("*"))
async def process_cancel(event: Message | CallbackQuery, state: FSMContext) -> None:
    """
    Cancel current order flow at any point, preserving user language.
    """
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANGUAGE)
    await state.clear()
    await state.update_data(lang=lang)

    text = get_text("order_canceled", lang)

    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(
            text=text,
            reply_markup=get_start_keyboard(lang),
        )
    else:
        await event.answer(
            text=text,
            reply_markup=get_start_keyboard(lang),
        )
