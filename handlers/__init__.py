from aiogram import Router
from .start import router as start_router
from .order_fsm import router as order_fsm_router


def get_main_router() -> Router:
    """
    Combine all feature routers into a single root router.
    """
    root_router = Router(name="main_router")
    root_router.include_router(start_router)
    root_router.include_router(order_fsm_router)
    return root_router


__all__ = [
    "get_main_router",
    "start_router",
    "order_fsm_router",
]
