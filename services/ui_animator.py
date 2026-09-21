"""
services/ui_animator.py
Asynchronous UI animation service rotating waiting status frames during generation.
Uses asyncio.create_task and handles TelegramRetryAfter and TelegramBadRequest cleanly.
"""

import asyncio
import logging
import math
import time
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.types import Message

from locales.texts import ANIMATION_FRAMES, DEFAULT_LANGUAGE, LANG_RU, get_text

logger = logging.getLogger(__name__)


def make_progress_bar(percent: int, length: int = 10) -> str:
    """
    Render a text-based progress bar of specified segment length.
    Example for 40%: [▰▰▰▰▱▱▱▱▱▱]
    """
    p = max(0, min(100, percent))
    filled = int(round(length * (p / 100.0)))
    unfilled = length - filled
    return f"[{'▰' * filled}{'▱' * unfilled}]"


class UIAnimator:
    """
    Manages periodic animated status updates in Telegram chat during long operations.
    Supports:
    1. Visual progress bar with percentage, elapsed time, and rotating status frames.
    2. Dynamic external progress updates via update_progress(percent).
    3. Handles Telegram flood control (TelegramRetryAfter) and 'Message is not modified' cleanly.
    """

    def __init__(
        self,
        message: Message | None = None,
        bot: Bot | None = None,
        chat_id: int | None = None,
        message_id: int | None = None,
        lang: str = DEFAULT_LANGUAGE,
        interval: float = 2.0,
        custom_frames: list[str] | None = None,
        show_progress_bar: bool = True,
    ) -> None:
        """
        Initialize UIAnimator.

        :param message: The Message object to edit (most common usage).
        :param bot: Bot instance (if message object is not passed).
        :param chat_id: Target chat ID.
        :param message_id: Message ID to edit.
        :param lang: Language code ('kk', 'ru', 'en').
        :param interval: Rotation interval in seconds (default 2.0s).
        :param custom_frames: Optional custom list of text frames.
        :param show_progress_bar: Whether to display visual progress bar and elapsed time.
        """
        self._message = message
        self._bot = bot or (message.bot if message else None)
        self._chat_id = chat_id or (message.chat.id if message else None)
        self._message_id = message_id or (message.message_id if message else None)

        self._lang = lang
        self._interval = interval
        self._show_progress_bar = show_progress_bar
        self._frames = (
            custom_frames
            or ANIMATION_FRAMES.get(lang)
            or ANIMATION_FRAMES.get(DEFAULT_LANGUAGE)
            or ANIMATION_FRAMES[LANG_RU]
        )

        self._reported_progress: int | None = None
        self._start_time = time.monotonic()
        self._task: asyncio.Task[Any] | None = None
        self._running = False
        self._last_rendered_text: str | None = None

    @property
    def is_running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    def start(self) -> asyncio.Task[Any]:
        """Start the animation loop in the background via asyncio.create_task."""
        if self.is_running:
            return self._task  # type: ignore[return-value]

        self._running = True
        self._start_time = time.monotonic()
        self._task = asyncio.create_task(self._animate_loop(), name="ui_animator_task")
        return self._task

    async def update_progress(self, percent: int) -> None:
        """
        Explicitly update reported progress percentage (0-100).
        If percent >= 100, flushes final state immediately to the message.
        """
        self._reported_progress = max(0, min(100, int(percent)))
        if self._reported_progress >= 100 and self._running:
            await self._render_now(100)

    def _calc_simulated_progress(self, elapsed: float) -> int:
        """
        Calculate realistic smooth progress estimation over ~45-50s typical latency:
        Starts at ~10%, reaches ~85% around 40s, and asymptotically approaches 95%.
        """
        val = int(8 + 87 * (1.0 - math.exp(-elapsed / 22.0)))
        return min(95, max(8, val))

    def _format_message(self, percent: int, elapsed: int, frame_idx: int) -> str:
        """Format the status text with progress bar or simple frames."""
        total_frames = len(self._frames) if self._frames else 1
        current_frame = self._frames[frame_idx % total_frames] if self._frames else ""

        if not self._show_progress_bar:
            return f"⏳ <b>{current_frame}</b>"

        title = get_text("progress_title", self._lang)
        sec_label = get_text("progress_sec", self._lang)
        bar = make_progress_bar(percent, length=10)

        if percent >= 100:
            ready_label = get_text("progress_ready", self._lang)
            return (
                f"🎵 <b>{title}</b>\n"
                f"<code>{bar}</code> <b>100%</b> • ⏱️ {elapsed} {sec_label}\n\n"
                f"✨ <i>{ready_label}</i>"
            )

        return (
            f"🎵 <b>{title}</b>\n"
            f"<code>{bar}</code> <b>{percent}%</b> • ⏱️ {elapsed} {sec_label}\n\n"
            f"<i>{current_frame}</i>"
        )

    async def _render_now(self, forced_percent: int | None = None) -> None:
        """Render and edit the message immediately."""
        elapsed = int(time.monotonic() - self._start_time)
        if forced_percent is not None:
            percent = forced_percent
        elif self._reported_progress is not None:
            simulated = self._calc_simulated_progress(elapsed)
            percent = max(self._reported_progress, simulated)
        else:
            percent = self._calc_simulated_progress(elapsed)

        text = self._format_message(percent, elapsed, frame_idx=0)
        await self._safe_edit(text)

    async def stop(self, delete_message: bool = False, final_text: str | None = None) -> None:
        """Stop the animation loop and optionally delete or edit the status message."""
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
        """Internal loop updating status message and progress every interval."""
        if not self._frames and not self._show_progress_bar:
            return

        frame_idx = 0

        # Initial prompt render
        await self._render_now()

        while self._running:
            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break

            if not self._running:
                break

            elapsed = int(time.monotonic() - self._start_time)
            simulated = self._calc_simulated_progress(elapsed)

            if self._reported_progress is not None:
                percent = max(self._reported_progress, simulated)
            else:
                percent = simulated

            text = self._format_message(percent, elapsed, frame_idx)
            await self._safe_edit(text)
            frame_idx += 1

    async def _safe_edit(self, text: str) -> None:
        """Edit message with error handling for Telegram flood limits and modified content."""
        if text == self._last_rendered_text:
            return

        try:
            if self._message:
                await self._message.edit_text(text=text)
            elif self._bot and self._chat_id and self._message_id:
                await self._bot.edit_message_text(
                    text=text,
                    chat_id=self._chat_id,
                    message_id=self._message_id,
                )
            self._last_rendered_text = text
        except TelegramRetryAfter as exc:
            logger.warning("Telegram flood limit in UIAnimator. Pausing for %s seconds", exc.retry_after)
            try:
                await asyncio.sleep(exc.retry_after)
            except asyncio.CancelledError:
                self._running = False
        except TelegramBadRequest as exc:
            err = str(exc).lower()
            if "message is not modified" in err:
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
