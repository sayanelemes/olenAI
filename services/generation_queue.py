"""
services/generation_queue.py
Concurrency-limited generation queue for Apiframe Suno Music API.
Implements a strict pool of 5 persistent async workers via asyncio.Queue.
Slots are held across the entire generation lifecycle (POST -> poll -> audio_url)
and guaranteed to be freed in try...finally.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from aiogram import Bot
from aiogram.enums import ChatAction
from aiogram.types import URLInputFile

from keyboards.inline import get_start_keyboard
from locales import get_text
from services.suno_service import (
    InsufficientCreditsError,
    SunoService,
    SunoServiceError,
)

logger = logging.getLogger(__name__)


@dataclass
class SongJob:
    """
    Encapsulates all metadata required to execute and deliver a music generation job.
    """
    id: str
    chat_id: int
    user_id: int
    status_message_id: int
    name: str
    occasion: str
    genre: str
    lyrics: str
    lang: str
    charge_id: str | None = None
    was_queued: bool = False
    enqueued_at: float = field(default_factory=time.time)


class GenerationQueue:
    """
    Manages a concurrency-limited worker pool for Suno music generation.
    Strictly limits concurrent active generation tasks to max_concurrency (default 5).
    """

    def __init__(
        self,
        bot: Bot,
        suno_service: SunoService,
        max_concurrency: int = 5,
    ) -> None:
        self._bot = bot
        self._suno_service = suno_service
        self._max_concurrency = max_concurrency

        self._queue: asyncio.Queue[SongJob] = asyncio.Queue()
        self._active_workers: int = 0
        self._active_jobs: dict[str, SongJob] = {}
        self._lock = asyncio.Lock()

        self._workers: list[asyncio.Task] = []
        self._running: bool = False

    @property
    def max_concurrency(self) -> int:
        return self._max_concurrency

    @property
    def active_count(self) -> int:
        return self._active_workers

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    async def start(self) -> None:
        """
        Start the background worker tasks.
        """
        if self._running:
            return

        self._running = True
        self._workers = [
            asyncio.create_task(self._worker_loop(i + 1), name=f"GenerationWorker-{i + 1}")
            for i in range(self._max_concurrency)
        ]
        logger.info(
            "GenerationQueue started with %d concurrent background workers.",
            self._max_concurrency,
        )

    async def stop(self) -> None:
        """
        Gracefully stop all worker tasks.
        """
        if not self._running:
            return

        logger.info("Stopping GenerationQueue workers...")
        self._running = False
        for task in self._workers:
            task.cancel()

        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("GenerationQueue stopped.")

    async def submit_job(
        self,
        chat_id: int,
        user_id: int,
        name: str,
        occasion: str,
        genre: str,
        lyrics: str,
        lang: str,
        charge_id: str | None = None,
    ) -> SongJob:
        """
        Submit a new song order to the queue.
        Sends appropriate status message depending on slot availability:
        - If >= 5 slots busy: '⏳ Студия сейчас занята (5/5). Ваша заявка принята, вы в очереди: #[N]'
        - If < 5 slots busy: '🎙 Студия свободна! Начинаем генерацию и сведение (~1-2 мин)...'
        """
        async with self._lock:
            total_allocated = self._active_workers + self._queue.qsize()
            if total_allocated >= self._max_concurrency:
                position = (total_allocated - self._max_concurrency) + 1
                text = get_text("studio_busy_queued", lang, position=position)
                status_msg = await self._bot.send_message(chat_id=chat_id, text=text)
                was_queued = True
                logger.info(
                    "Slots full (%d active, %d in queue). Enqueued job for user %d at position #%d.",
                    self._active_workers,
                    self._queue.qsize(),
                    user_id,
                    position,
                )
            else:
                text = get_text("studio_slot_available", lang)
                status_msg = await self._bot.send_message(chat_id=chat_id, text=text)
                was_queued = False
                logger.info(
                    "Studio slot available (%d/%d active). Direct job accepted for user %d.",
                    self._active_workers,
                    self._max_concurrency,
                    user_id,
                )

        job = SongJob(
            id=str(uuid.uuid4()),
            chat_id=chat_id,
            user_id=user_id,
            status_message_id=status_msg.message_id,
            name=name,
            occasion=occasion,
            genre=genre,
            lyrics=lyrics,
            lang=lang,
            charge_id=charge_id,
            was_queued=was_queued,
        )

        await self._queue.put(job)
        return job

    async def _worker_loop(self, worker_id: int) -> None:
        """
        Persistent worker process pulling jobs from the asyncio queue.
        Guarantees slot lock and release in try...finally.
        """
        logger.info("Generation worker #%d ready for tasks.", worker_id)
        while self._running:
            try:
                job = await self._queue.get()
            except asyncio.CancelledError:
                break

            async with self._lock:
                self._active_workers += 1
                self._active_jobs[job.id] = job

            logger.info(
                "Worker #%d claimed job %s for chat %d (Active slots: %d/%d)",
                worker_id,
                job.id,
                job.chat_id,
                self._active_workers,
                self._max_concurrency,
            )

            try:
                await self._process_job(worker_id, job)
            except asyncio.CancelledError:
                logger.warning("Worker #%d cancelled during job %s", worker_id, job.id)
                break
            except Exception as exc:
                logger.exception(
                    "Worker #%d unhandled exception on job %s: %s",
                    worker_id,
                    job.id,
                    exc,
                )
            finally:
                # GUARANTEED resource cleanup: slot is ALWAYS freed
                async with self._lock:
                    self._active_workers = max(0, self._active_workers - 1)
                    self._active_jobs.pop(job.id, None)
                self._queue.task_done()
                logger.info(
                    "Worker #%d completed job %s. Slot released. (Active slots: %d/%d, Pending in queue: %d)",
                    worker_id,
                    job.id,
                    self._active_workers,
                    self._max_concurrency,
                    self._queue.qsize(),
                )

    async def _process_job(self, worker_id: int, job: SongJob) -> None:
        """
        Executes Suno music generation lifecycle and delivers audio to user.
        """
        # If job was waiting in the queue, update the status message
        if job.was_queued:
            try:
                await self._bot.edit_message_text(
                    chat_id=job.chat_id,
                    message_id=job.status_message_id,
                    text=get_text("studio_slot_available", job.lang),
                )
            except Exception as e:
                logger.debug("Could not edit queued message for job %s: %s", job.id, e)

        title = f"Song for {job.name}"

        try:
            # 1. Show audio recording action
            try:
                await self._bot.send_chat_action(chat_id=job.chat_id, action=ChatAction.RECORD_VOICE)
            except Exception:
                pass

            # 2. Submit generation task to Suno API via Apiframe
            task_id = await self._suno_service.create_song_task(
                lyrics=job.lyrics,
                style=job.genre,
                title=title,
            )
            logger.info("Worker #%d created Suno task %s for job %s", worker_id, task_id, job.id)

            # 3. Poll for completion while holding the slot
            audio_url = await self._suno_service.wait_for_completion(
                task_id=task_id,
                timeout=240,
                interval=2.0,
            )

            # 4. Upload audio to user
            try:
                await self._bot.send_chat_action(chat_id=job.chat_id, action=ChatAction.UPLOAD_VOICE)
            except Exception:
                pass

            audio_file = URLInputFile(
                url=audio_url,
                filename=f"Song_{job.name}.mp3",
            )
            caption = get_text(
                "song_ready_caption",
                job.lang,
                name=job.name,
                occasion=job.occasion,
                genre=job.genre,
            )

            await self._bot.send_audio(
                chat_id=job.chat_id,
                audio=audio_file,
                caption=caption,
                title=title,
                performer="Suno AI",
            )

            # 5. Clean up the status service message
            try:
                await self._bot.delete_message(
                    chat_id=job.chat_id,
                    message_id=job.status_message_id,
                )
            except Exception:
                pass

            # 6. Offer to create another song
            await self._bot.send_message(
                chat_id=job.chat_id,
                text=get_text("order_another", job.lang),
                reply_markup=get_start_keyboard(job.lang),
            )
            logger.info("Worker #%d delivered song %s to chat %d", worker_id, job.id, job.chat_id)

        except Exception as exc:
            logger.exception("Generation job %s failed: %s", job.id, exc)

            # Auto-refund Telegram Stars if real payment was processed
            if job.charge_id:
                if not job.charge_id.startswith("test_"):
                    try:
                        await self._bot.refund_star_payment(
                            user_id=job.user_id,
                            telegram_payment_charge_id=job.charge_id,
                        )
                        logger.info("Refunded star payment %s to user %d", job.charge_id, job.user_id)
                    except Exception as ref_err:
                        logger.error("Failed to refund star payment %s: %s", job.charge_id, ref_err)
                else:
                    logger.info("Test payment job %s failed, skipping Telegram refund API.", job.id)

                refund_text = get_text("stars_refund_notice", job.lang)
                try:
                    await self._bot.send_message(chat_id=job.chat_id, text=refund_text)
                except Exception:
                    pass

            # Notify user about failure reason
            if isinstance(exc, InsufficientCreditsError):
                err_text = get_text("credits_exhausted", job.lang)
            elif isinstance(exc, TimeoutError):
                err_text = get_text("audio_timeout", job.lang)
            elif isinstance(exc, SunoServiceError):
                err_text = get_text("audio_failed", job.lang, err=str(exc))
            else:
                err_text = get_text("audio_failed", job.lang, err="Внутренняя ошибка")

            try:
                await self._bot.edit_message_text(
                    chat_id=job.chat_id,
                    message_id=job.status_message_id,
                    text=err_text,
                    reply_markup=get_start_keyboard(job.lang),
                )
            except Exception:
                try:
                    await self._bot.send_message(
                        chat_id=job.chat_id,
                        text=err_text,
                        reply_markup=get_start_keyboard(job.lang),
                    )
                except Exception:
                    pass
