from aiogram.fsm.state import State, StatesGroup


class OrderStates(StatesGroup):
    """
    FSM states for the song ordering pipeline.
    """
    name = State()              # Имя виновника торжества
    occasion = State()          # Повод / праздник
    details = State()           # Факты, черты характера, воспоминания
    genre = State()             # Музыкальный жанр / стиль
    preview_approval = State()  # Превью текста и подтверждение генерации аудио
