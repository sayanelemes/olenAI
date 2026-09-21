from aiogram.fsm.state import State, StatesGroup


class OrderStates(StatesGroup):
    """
    FSM states for the song ordering and payment pipeline.
    """
    occasion = State()          # Шаг 1: Выбор повода (Туған күн, Прикол, Лирика, Свадьба)
    details = State()           # Шаг 2: Ввод имени и 2-3 личных фактов (текст)
    genre = State()             # Шаг 3: Выбор музыкального стиля (Q-pop, Той, Дрилл, Акустика)
    preview_approval = State()  # Шаги 4-5: Согласование текста и обязательный дисклеймер
    waiting_payment = State()   # Ожидание оплаты Telegram Stars (XTR)
    generating_audio = State()  # Генерация трека в Suno (блокировка повторных кликов)
