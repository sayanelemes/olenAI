"""
keyboards/inline.py
Inline keyboards for language selection, occasions, genres (2xN grid), and preview actions.
Supports aiogram 3.x CallbackData and multilingual labels for Kazakh ('kk'), Russian ('ru'), and English ('en').
"""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from locales.texts import (
    DEFAULT_LANGUAGE,
    GENRES_LIST,
    GENRES_MAP,
    LANG_EN,
    LANG_KK,
    LANG_RU,
    OCCASIONS_LIST,
    OCCASIONS_MAP,
    t,
)


class LanguageCallback(CallbackData, prefix="lang"):
    code: str  # "kk", "ru", "en"


class OccasionCallback(CallbackData, prefix="occ"):
    value: str


class GenreCallback(CallbackData, prefix="gnr"):
    value: str


class PreviewActionCallback(CallbackData, prefix="prev"):
    action: str  # "approve", "rewrite", "cancel"


def get_language_kb() -> InlineKeyboardMarkup:
    """
    Keyboard for interface language selection:
    🇰🇿 Қазақша | 🇷🇺 Русский | 🇬🇧 English
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="🇰🇿 Қазақша", callback_data=LanguageCallback(code=LANG_KK).pack())
    builder.button(text="🇷🇺 Русский", callback_data=LanguageCallback(code=LANG_RU).pack())
    builder.button(text="🇬🇧 English", callback_data=LanguageCallback(code=LANG_EN).pack())
    builder.adjust(1)
    return builder.as_markup()


def get_genres_kb(lang: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """
    Keyboard for selecting music genre / style formatted in a clean 2xN grid,
    with a localized Cancel button at the bottom.
    """
    builder = InlineKeyboardBuilder()
    genres = GENRES_LIST.get(lang) or GENRES_LIST[LANG_RU]

    for item in genres:
        builder.button(
            text=item["label"],
            callback_data=GenreCallback(value=item["id"]).pack(),
        )

    # 2 buttons per row for all genres
    builder.adjust(2)

    # Add Cancel button as a full-width bottom row
    builder.row(
        InlineKeyboardButton(
            text=t("btn_cancel", lang),
            callback_data="cancel_order",
        )
    )
    return builder.as_markup()


def get_preview_kb(lang: str = DEFAULT_LANGUAGE, is_test: bool = False) -> InlineKeyboardMarkup:
    """
    Keyboard for lyrics preview and agreement:
    [✅ Все верно, поем! (Тест: 0 ⭐️)] (in test mode)
    or [✅ Все верно, поем!] (in real mode)
    [🔄 Изменить детали]
    [❌ Отмена]
    """
    builder = InlineKeyboardBuilder()
    approve_text = t("btn_approve_sing_test" if is_test else "btn_approve_sing", lang)
    builder.button(
        text=approve_text,
        callback_data=PreviewActionCallback(action="approve").pack(),
    )
    builder.button(
        text=t("btn_edit_details", lang),
        callback_data=PreviewActionCallback(action="edit_details").pack(),
    )
    builder.button(
        text=t("btn_cancel", lang),
        callback_data=PreviewActionCallback(action="cancel").pack(),
    )
    builder.adjust(1, 1, 1)
    return builder.as_markup()


def get_occasions_kb(lang: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """
    Keyboard for selecting holiday occasion formatted in a 2xN grid + cancel row.
    """
    builder = InlineKeyboardBuilder()
    occasions = OCCASIONS_LIST.get(lang) or OCCASIONS_LIST[LANG_RU]

    for label, val in occasions:
        builder.button(
            text=label,
            callback_data=OccasionCallback(value=val).pack(),
        )
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(
            text=t("btn_cancel", lang),
            callback_data="cancel_order",
        )
    )
    return builder.as_markup()


def get_start_kb(lang: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """
    Main menu keyboard localized for the chosen language.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_start_order", lang), callback_data="start_order")
    builder.button(text=t("btn_how_it_works", lang), callback_data="how_it_works")
    builder.button(text=t("btn_change_lang", lang), callback_data="change_language")
    builder.adjust(1)
    return builder.as_markup()


def get_cancel_kb(lang: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """
    Cancel keyboard for text input steps.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_cancel", lang), callback_data="cancel_order")
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Aliases for backward compatibility with different handler conventions
# ---------------------------------------------------------------------------
get_language_keyboard = get_language_kb
get_genres_keyboard = get_genres_kb
get_preview_approval_keyboard = get_preview_kb
get_occasions_keyboard = get_occasions_kb
get_start_keyboard = get_start_kb
get_cancel_keyboard = get_cancel_kb
