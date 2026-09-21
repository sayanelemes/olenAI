"""
services/suno_service.py
Asynchronous client for Suno AI music generation via Apiframe.ai v2 API.
Includes mock generation support (asyncio.sleep(4)) and robust 402 InsufficientCreditsError handling.
"""

import asyncio
import logging
import time
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class SunoServiceError(Exception):
    """Base exception for Suno / Apiframe gateway failures."""
    pass


class InsufficientCreditsError(SunoServiceError):
    """Raised when Apiframe returns 402 Payment Required or reports insufficient credits."""
    pass


class SunoService:
    """
    Asynchronous client for generating music with Suno AI via Apiframe.ai v2 API.
    Supports mock mode (USE_MOCK_MUSIC=True) for free local testing without consuming credits.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.apiframe.ai",
        use_mock: bool | None = None,
        mock_audio_url: str = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        session: aiohttp.ClientSession | None = None,
        request_timeout: int = 30,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

        # If use_mock is not explicitly provided, load from config if available
        if use_mock is None:
            try:
                from config import get_settings
                self._use_mock = get_settings().USE_MOCK_MUSIC
                self._mock_audio_url = get_settings().MOCK_AUDIO_URL or mock_audio_url
            except Exception:
                self._use_mock = False
                self._mock_audio_url = mock_audio_url
        else:
            self._use_mock = use_mock
            self._mock_audio_url = mock_audio_url

        self._session = session
        self._owns_session = session is None
        self._request_timeout = aiohttp.ClientTimeout(total=request_timeout)

        if self._use_mock:
            logger.info("SunoService initialized in MOCK MODE (no credits will be consumed).")

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._request_timeout)
            self._owns_session = True
        return self._session

    async def close(self) -> None:
        """Close HTTP session if owned by this service."""
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()

    def _get_headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
        }

    def _check_credits_error(self, status: int, text: str) -> None:
        """Check if response status or text indicates exhausted credits."""
        lowered = text.lower()
        if status == 402 or "credit" in lowered or "insufficient" in lowered:
            logger.error("Credits exhausted on Apiframe (status=%s): %s", status, text)
            raise InsufficientCreditsError(
                "Недостаточно кредитов в сервисе генерации музыки (Apiframe/Suno)."
            )

    async def check_health(self, timeout: float = 3.0) -> bool:
        """
        Fast health check against Apiframe Suno gateway with a strict timeout (default 3.0s).
        Called during Telegram Stars PreCheckoutQuery to ensure the studio is reachable
        before user's balance is debited.
        Returns True if gateway is healthy and accessible, False otherwise.
        """
        if self._use_mock:
            return True

        endpoint = f"{self._base_url}/v2/models"
        session = await self._get_session()
        try:
            async with session.get(
                endpoint,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                logger.debug("Apiframe healthcheck returned status %s", response.status)
                return response.status < 500
        except Exception as exc:
            logger.warning("Apiframe healthcheck failed: %s", exc)
            return False

    async def create_song_task(
        self,
        lyrics: str,
        style: str,
        title: str = "Поздравительная песня",
    ) -> str:
        """
        Send generation request to Apiframe Suno API v2.
        In mock mode, returns a mock task ID immediately.

        :param lyrics: Song lyrics with section tags.
        :param style: Musical genre/style prompt for Suno.
        :param title: Song title.
        :return: Job / Task ID string.
        """
        if self._use_mock:
            logger.info("[MOCK] Simulating Suno task creation for '%s'...", title)
            mock_id = f"mock_task_{int(time.time())}"
            logger.info("[MOCK] Created task with ID: %s", mock_id)
            return mock_id

        endpoint = f"{self._base_url}/v2/music/generate"
        payload: dict[str, Any] = {
            "model": "suno",
            "prompt": lyrics,
            "sunoParams": {
                "custom_mode": True,
                "style": style,
                "title": title,
                "instrumental": False,
            },
        }

        session = await self._get_session()
        logger.info("Submitting song task to Apiframe (style='%s', title='%s')", style, title)

        try:
            async with session.post(endpoint, headers=self._get_headers(), json=payload) as response:
                response_text = await response.text()

                # Check for 402 Payment Required or credit exhaustion
                self._check_credits_error(response.status, response_text)

                if response.status not in (200, 201, 202):
                    logger.error("Apiframe create_song_task failed (%s): %s", response.status, response_text)
                    raise SunoServiceError(f"Ошибка Apiframe API ({response.status}): {response_text}")

                try:
                    data = await response.json()
                except Exception:
                    raise SunoServiceError(f"Apiframe вернул некорректный JSON: {response_text}")

                logger.debug("Apiframe generate response: %s", data)

                job_id = (
                    data.get("jobId")
                    or data.get("job_id")
                    or data.get("id")
                    or data.get("task_id")
                )
                if not job_id and "data" in data and isinstance(data["data"], dict):
                    job_id = data["data"].get("jobId") or data["data"].get("id")

                if not job_id:
                    logger.error("No jobId returned by Apiframe: %s", data)
                    raise SunoServiceError(f"Ответ Apiframe не содержит jobId: {data}")

                logger.info("Apiframe Suno job created: %s", job_id)
                return str(job_id)

        except InsufficientCreditsError:
            raise
        except asyncio.TimeoutError as exc:
            logger.error("Timeout during Apiframe song creation request")
            raise SunoServiceError("Превышено время ожидания ответа при отправке задачи в Apiframe.") from exc
        except aiohttp.ClientError as exc:
            logger.error("Network error connecting to Apiframe API: %s", exc)
            raise SunoServiceError(f"Сетевая ошибка при обращении к Apiframe API: {exc}") from exc
        except SunoServiceError:
            raise
        except Exception as exc:
            logger.exception("Unexpected error in SunoService.create_song_task: %s", exc)
            raise SunoServiceError(f"Не удалось запустить генерацию трека в Apiframe: {exc}") from exc

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        """
        Check status of a single Apiframe / Suno task without blocking indefinitely.
        Returns dict with keys: 'status', 'progress', 'audio_url', 'error'.
        """
        if self._use_mock:
            return {
                "status": "COMPLETED",
                "progress": 100,
                "audio_url": self._mock_audio_url,
                "error": None,
            }

        endpoint = f"{self._base_url}/v2/jobs/{task_id}"
        session = await self._get_session()

        try:
            async with session.get(endpoint, headers=self._get_headers()) as response:
                response_text = await response.text()
                self._check_credits_error(response.status, response_text)

                if response.status != 200:
                    return {
                        "status": "PENDING",
                        "progress": 10,
                        "audio_url": None,
                        "error": f"HTTP {response.status}",
                    }

                data = await response.json()
                status = str(data.get("status") or "PENDING").upper()
                raw_prog = data.get("progress")
                audio_url = self._extract_audio_url(data) if status == "COMPLETED" else None
                error_msg = (
                    data.get("error")
                    or data.get("message")
                    or data.get("failed_reason")
                )

                return {
                    "status": status,
                    "progress": int(raw_prog) if raw_prog is not None else None,
                    "audio_url": audio_url,
                    "error": error_msg,
                }
        except InsufficientCreditsError as exc:
            return {"status": "FAILED", "progress": 0, "audio_url": None, "error": str(exc)}
        except Exception as exc:
            logger.warning("Error fetching task status %s: %s", task_id, exc)
            return {"status": "PENDING", "progress": 15, "audio_url": None, "error": str(exc)}

    async def wait_for_completion(
        self,
        task_id: str,
        timeout: int = 240,
        interval: float = 2.0,
        on_progress: Any = None,
    ) -> str:
        """
        Poll Apiframe job status via GET /v2/jobs/{task_id} until COMPLETED.
        In mock mode, waits exactly 4 seconds (asyncio.sleep(4)) and returns test MP3 URL.

        :param task_id: The job ID returned by create_song_task.
        :param timeout: Maximum seconds to wait.
        :param interval: Polling interval in seconds (default 2.0s for fast detection).
        :param on_progress: Optional async or sync callback(percent: int) called when progress is reported.
        :return: Public URL to the generated MP3 file.
        """
        if self._use_mock:
            logger.info("[MOCK] Simulating audio generation delay (asyncio.sleep(4)) for %s...", task_id)
            if on_progress:
                try:
                    res = on_progress(50)
                    if asyncio.iscoroutine(res):
                        await res
                except Exception:
                    pass
            await asyncio.sleep(4)
            if on_progress:
                try:
                    res = on_progress(100)
                    if asyncio.iscoroutine(res):
                        await res
                except Exception:
                    pass
            logger.info("[MOCK] Generation complete! Returning test audio URL: %s", self._mock_audio_url)
            return self._mock_audio_url

        endpoint = f"{self._base_url}/v2/jobs/{task_id}"
        session = await self._get_session()

        start_time = time.monotonic()
        logger.info("Polling Apiframe job %s (timeout=%ds, interval=%.1fs)", task_id, timeout, interval)

        while time.monotonic() - start_time < timeout:
            try:
                async with session.get(endpoint, headers=self._get_headers()) as response:
                    response_text = await response.text()

                    # Check for 402 or credits error
                    self._check_credits_error(response.status, response_text)

                    if response.status != 200:
                        logger.warning("Polling job %s returned HTTP %s: %s", task_id, response.status, response_text)
                    else:
                        try:
                            data = await response.json()
                        except Exception:
                            logger.warning("Failed to decode JSON from job response: %s", response_text)
                            await asyncio.sleep(interval)
                            continue

                        status = str(data.get("status") or "").upper()
                        logger.debug("Apiframe job %s status: %s", task_id, status)

                        # Report progress if provided by Apiframe
                        if on_progress:
                            raw_prog = data.get("progress")
                            if raw_prog is not None:
                                try:
                                    res = on_progress(int(raw_prog))
                                    if asyncio.iscoroutine(res):
                                        await res
                                except Exception as exc:
                                    logger.debug("Error invoking on_progress callback: %s", exc)

                        if status == "COMPLETED":
                            audio_url = self._extract_audio_url(data)
                            if audio_url:
                                logger.info("Apiframe job %s completed! Audio URL: %s", task_id, audio_url)
                                if on_progress:
                                    try:
                                        res = on_progress(100)
                                        if asyncio.iscoroutine(res):
                                            await res
                                    except Exception:
                                        pass
                                return audio_url
                            logger.warning("Job %s COMPLETED, waiting for audio payload: %s", task_id, data)

                        elif status in ("FAILED", "ERROR", "CANCELLED"):
                            error_msg = (
                                data.get("error")
                                or data.get("message")
                                or data.get("failed_reason")
                                or "Неизвестная ошибка"
                            )
                            if "credit" in str(error_msg).lower() or "insufficient" in str(error_msg).lower():
                                raise InsufficientCreditsError(f"Ошибка кредитов: {error_msg}")
                            logger.error("Apiframe job %s failed: %s", task_id, error_msg)
                            raise SunoServiceError(f"Генерация трека в Apiframe завершилась с ошибкой: {error_msg}")

            except (SunoServiceError, InsufficientCreditsError, asyncio.CancelledError):
                raise
            except Exception as exc:
                logger.warning("Temporary error polling Apiframe job %s: %s", task_id, exc)

            await asyncio.sleep(interval)

        elapsed = int(time.monotonic() - start_time)
        logger.error("Apiframe polling timed out for job %s after %ds", task_id, elapsed)
        raise TimeoutError(f"Превышено время ожидания готовности песни в Apiframe ({timeout} сек).")

    async def generate_music(
        self,
        lyrics: str,
        style: str,
        title: str = "Поздравительная песня",
        timeout: int = 240,
        on_progress: Any = None,
    ) -> str:
        """
        Convenience end-to-end method: creates song task and awaits completion.
        """
        if self._use_mock:
            await asyncio.sleep(4)
            return self._mock_audio_url

        task_id = await self.create_song_task(lyrics=lyrics, style=style, title=title)
        return await self.wait_for_completion(task_id=task_id, timeout=timeout, on_progress=on_progress)

    def _extract_audio_url(self, data: dict[str, Any]) -> str | None:
        """
        Extract direct audio URL from Apiframe result formats.
        Supports audioUrl (camelCase), audio_url (snake_case), mp3_url, and url.
        """
        result = data.get("result")

        # Helper to extract from single dictionary item
        def _get_url_from_item(item: Any) -> str | None:
            if not isinstance(item, dict):
                if isinstance(item, str) and item.startswith("http"):
                    return item
                return None
            return (
                item.get("audioUrl")
                or item.get("audio_url")
                or item.get("mp3_url")
                or item.get("url")
                or item.get("audio")
            )

        # 1. Result is list of tracks / URLs
        if isinstance(result, list) and len(result) > 0:
            for item in result:
                url = _get_url_from_item(item)
                if url:
                    return str(url)

        # 2. Result is dictionary
        if isinstance(result, dict):
            # Check result directly
            url = _get_url_from_item(result)
            if url:
                return str(url)

            # Check sub-arrays like result["tracks"], result["clips"], etc.
            for key in ("tracks", "clips", "output", "audio_urls", "data"):
                sub_list = result.get(key)
                if isinstance(sub_list, list) and len(sub_list) > 0:
                    for item in sub_list:
                        sub_url = _get_url_from_item(item)
                        if sub_url:
                            return str(sub_url)

        # 3. Direct top-level fields
        direct_url = (
            data.get("audioUrl")
            or data.get("audio_url")
            or data.get("mp3_url")
            or data.get("url")
        )
        if direct_url:
            return str(direct_url)

        return None
