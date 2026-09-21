import asyncio
import logging
import sys

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import get_settings
from handlers import get_main_router
from services import GeminiService, SunoService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("song_bot")


async def main() -> None:
    """
    Main entrypoint:
    Loads config, initializes direct Gemini service and Apiframe Suno service,
    registers handlers and starts bot polling.
    """
    try:
        settings = get_settings()
    except Exception as exc:
        logger.critical("Failed to load application settings from .env: %s", exc)
        sys.exit(1)

    # Shared aiohttp session for connection pooling
    shared_session = aiohttp.ClientSession()

    # Initialize Direct Gemini client (via official REST API)
    gemini_service = GeminiService(
        api_key=settings.GEMINI_API_KEY.get_secret_value(),
        model=settings.GEMINI_MODEL,
        session=shared_session,
    )

    # Initialize Suno API client (via Apiframe.ai or Mock mode)
    suno_service = SunoService(
        api_key=settings.APIFRAME_API_KEY.get_secret_value(),
        base_url=settings.APIFRAME_BASE_URL,
        use_mock=settings.USE_MOCK_MUSIC,
        mock_audio_url=settings.MOCK_AUDIO_URL,
        session=shared_session,
    )

    # Initialize Telegram Bot and Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Inject service dependencies directly into aiogram handlers
    dp.workflow_data.update(
        {
            "llm_service": gemini_service,
            "gemini_service": gemini_service,
            "suno_service": suno_service,
        }
    )

    # Register all handlers
    dp.include_router(get_main_router())

    from aiogram.exceptions import TelegramNetworkError

    try:
        while True:
            try:
                await bot.delete_webhook(drop_pending_updates=True)
                logger.info(
                    "Bot successfully started! (Gemini: %s | Suno: Apiframe.ai)",
                    settings.GEMINI_MODEL,
                )
                await dp.start_polling(bot)
                break
            except (TelegramNetworkError, aiohttp.ClientError, ConnectionResetError) as net_err:
                logger.warning("Temporary network error during bot polling: %s. Retrying in 3 seconds...", net_err)
                await asyncio.sleep(3)
            except Exception as exc:
                logger.exception("Fatal error during bot polling: %s", exc)
                break
    finally:
        logger.info("Shutting down bot and closing active sessions...")
        await gemini_service.close()
        await suno_service.close()
        await shared_session.close()
        await bot.session.close()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Process stopped by user.")
