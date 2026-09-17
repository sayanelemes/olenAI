"""
services/ui_animator.py
Asynchronous UI animation service rotating waiting status frames during generation.
Uses asyncio.create_task and handles TelegramRetryAfter and TelegramBadRequest cleanly.
"""

import asyncio
import logging
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.types import Message

from locales.texts import ANIMATION_FRAMES, DEFAULT_LANGUAGE, LANG_RU

logger = logging.getLogger(__name__)


class UIAnimator:
    """
    Manages periodic animated status updates in Telegram chat during long operations.
    Rotates status messages/emojis every 3.0 seconds in the chosen language.
    Handles Telegram flood control (TelegramRetryAfter) and 'Message is not modified' errors safely.
    """

    def __init__(
        self,
        message: Message | None = None,
        bot: Bot | None = None,
        chat_id: int | None = None,
        message_id: int | None = None,
        lang: str = DEFAULT_LANGUAGE,
        interval: float = 3.0,
        custom_frames: list[str] | None = None,
    ) -> None:
        """
        Initialize UIAnimator.

        :param message: The Message object to edit (most common usage).
        :param bot: Bot instance (if message object is not passed).
        :param chat_id: Target chat ID.
        :param message_id: Message ID to edit.
        :param lang: Language code ('kk', 'ru', 'en').
        :param interval: Rotation interval in seconds (default 3.0s).
        :param custom_frames: Optional custom list of text frames.
        """
        self._message = message
        self._bot = bot or (message.bot if message else None)
        self._chat_id = chat_id or (message.chat.id if message else None)
        self._message_id = message_id or (message.message_id if message else None)

        self._lang = lang
        self._interval = interval
        self._frames = (
            custom_frames
            or ANIMATION_FRAMES.get(lang)
            or ANIMATION_FRAMES.get(DEFAULT_LANGUAGE)
            or ANIMATION_FRAMES[LANG_RU]
        )

        self._task: asyncio.Task[Any] | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    def start(self) -> asyncio.Task[Any]:
        """
        Start the animation loop in the background via asyncio.create_task.
        """
        if self.is_running:
            return self._task  # type: ignore[return-value]

        self._running = True
        self._task = asyncio.create_task(self._animate_loop(), name="ui_animator_task")
        return self._task

    async def stop(self, delete_message: bool = False, final_text: str | None = None) -> None:
        """
        Stop the animation loop and optionally delete or edit the status message.
        """
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                logger.debug("Exception waiting for animator task cancellation: %s", exc)

        if delete_message:
            await self._safe_delete()
        elif final_text:
            await self._safe_edit(final_text)

    async def __aenter__(self) -> "UIAnimator":
        self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.stop()

    async def _animate_loop(self) -> None:
        """
        Internal loop rotating status messages every 3.0 seconds.
        """
        if not self._frames:
            return

        frame_idx = 0
        total_frames = len(self._frames)

        while self._running:
            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break

            if not self._running:
                break

            current_frame = self._frames[frame_idx % total_frames]
            text = f"⏳ <b>{current_frame}</b>"

            await self._safe_edit(text)
            frame_idx += 1

    async def _safe_edit(self, text: str) -> None:
        """
        Edit message with error handling for Telegram flood limits and modified content.
        """
        try:
            if self._message:
                await self._message.edit_text(text=text)
            elif self._bot and self._chat_id and self._message_id:
                await self._bot.edit_message_text(
                    text=text,
                    chat_id=self._chat_id,
                    message_id=self._message_id,
                )
        except TelegramRetryAfter as exc:
            logger.warning(
                "Telegram flood limit in UIAnimator. Pausing for %s seconds",
                exc.retry_after,
            )
            try:
                await asyncio.sleep(exc.retry_after)
            except asyncio.CancelledError:
                self._running = False
        except TelegramBadRequest as exc:
            err = str(exc).lower()
            if "message is not modified" in err:
                # Content did not change, completely normal in polling
                pass
            elif "message to edit not found" in err or "chat not found" in err:
                logger.info("Message or chat no longer exists; stopping UIAnimator: %s", exc)
                self._running = False
            else:
                logger.debug("TelegramBadRequest in UIAnimator: %s", exc)
        except asyncio.CancelledError:
            self._running = False
            raise
        except Exception as exc:
            logger.warning("Unexpected error in UIAnimator edit_text: %s", exc)

    async def _safe_delete(self) -> None:
        """Safely delete target message without raising exceptions."""
        try:
            if self._message:
                await self._message.delete()
            elif self._bot and self._chat_id and self._message_id:
                await self._bot.delete_message(
                    chat_id=self._chat_id,
                    message_id=self._message_id,
                )
        except Exception as exc:
            logger.debug("Failed to delete animator message (may be already deleted): %s", exc)
