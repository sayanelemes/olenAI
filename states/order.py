from aiogram.fsm.state import State, StatesGroup


class OrderStates(StatesGroup):
    """
    FSM states for the song ordering and payment pipeline.
    """
    occasion = State()          # Шаг 1: Выбор повода (Туған күн, Прикол, Лирика, Свадьба)
    name = State()              # Шаг 2: Ввод имени адресата (текст)
    details = State()           # Шаг 3: Ввод личных фактов и пожеланий (текст)
    genre = State()             # Шаг 4: Выбор музыкального стиля (Q-pop, Той, Дрилл, Акустика)
    preview_approval = State()  # Шаги 4-5: Согласование текста и обязательный дисклеймер
    waiting_payment = State()   # Ожидание оплаты Telegram Stars (XTR)
    generating_audio = State()  # Генерация трека в Suno (блокировка повторных кликов)
