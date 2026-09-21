"""
locales/texts.py
Complete multilingual dictionary for Congratulatory Song Telegram Bot.
Supports Kazakh ('kk'), Russian ('ru'), and English ('en').
"""

from typing import Any

# Supported language codes
LANG_KK = "kk"
LANG_RU = "ru"
LANG_EN = "en"

DEFAULT_LANGUAGE = LANG_RU
SUPPORTED_LANGUAGES = (LANG_KK, LANG_RU, LANG_EN)

# Dictionary containing all localized UI and system texts
TEXTS: dict[str, dict[str, str]] = {
    # -----------------------------------------------------------------------
    # 1. Приветствие и выбор языка
    # -----------------------------------------------------------------------
    "choose_language": {
        LANG_RU: "🌐 <b>Выберите язык интерфейса / Тілді таңдаңыз / Choose language:</b>",
        LANG_KK: "🌐 <b>Тілді таңдаңыз / Выберите язык / Choose language:</b>",
        LANG_EN: "🌐 <b>Choose your language / Выберите язык / Тілді таңдаңыз:</b>",
    },
    "language_selected": {
        LANG_RU: "✅ Язык интерфейса установлен на <b>Русский</b>!",
        LANG_KK: "✅ Интерфейс тілі <b>Қазақша</b> болып орнатылды!",
        LANG_EN: "✅ Interface language set to <b>English</b>!",
    },
    "start_welcome": {
        LANG_RU: (
            "👋 <b>Добро пожаловать в генератор поздравительных песен!</b>\n\n"
            "Я помогу создать уникальный музыкальный трек для близких, друзей или коллег:\n"
            "1️⃣ Напишу персональный текст песни под ваш повод и факты (Google Gemini).\n"
            "2️⃣ Превращу его в полноценную студийную песню с вокалом и музыкой в Suno AI.\n\n"
            "Нажмите <b>«🎵 Создать песню»</b>, чтобы начать!"
        ),
        LANG_KK: (
            "👋 <b>Құттықтау әндерін шығаратын ботқа қош келдіңіз!</b>\n\n"
            "Мен жақындарыңызға, достарыңызға немесе әріптестеріңізге арналған ерекше ән шығаруға көмектесемін:\n"
            "1️⃣ Мерекеңізге арнап жеке ән мәтінін жазамын (Google Gemini).\n"
            "2️⃣ Suno AI арқылы шынайы дауыс пен әуені бар студиялық сападағы ән жасаймын.\n\n"
            "Бастау үшін <b>«🎵 Ән жасау»</b> батырмасын басыңыз!"
        ),
        LANG_EN: (
            "👋 <b>Welcome to the Congratulatory Song Generator Bot!</b>\n\n"
            "I'll help you create a custom song for friends, family, or colleagues:\n"
            "1️⃣ Compose personalized lyrics for your occasion and facts (Google Gemini).\n"
            "2️⃣ Generate a studio-quality track with music and vocals via Suno AI.\n\n"
            "Click <b>'🎵 Create Song'</b> below to get started!"
        ),
    },
    "how_it_works": {
        LANG_RU: (
            "ℹ️ <b>Как работает бот:</b>\n\n"
            "1. Вы указываете имя, повод, факты и музыкальный жанр.\n"
            "2. Нейросеть Google Gemini сочиняет гармоничный текст с куплетами и припевом.\n"
            "3. Вы проверяете текст и можете переписать его или утвердить.\n"
            "4. Нейросеть Suno AI синтезирует музыку и поет песню живым голосом!"
        ),
        LANG_KK: (
            "ℹ️ <b>Бот қалай жұмыс істейді:</b>\n\n"
            "1. Сіз есімін, мерекені, деректерді және музыка стилін көрсетесіз.\n"
            "2. Google Gemini нейрожелісі шумақтары мен қайырмасы бар ән сөзін шығарады.\n"
            "3. Мәтінді оқып, бекітесіз немесе қайта жаздырасыз.\n"
            "4. Suno AI әуен шығарып, әнді кәсіби дауыспен орындап береді!"
        ),
        LANG_EN: (
            "ℹ️ <b>How it works:</b>\n\n"
            "1. You provide the name, occasion, personal facts, and genre.\n"
            "2. Google Gemini composes structured lyrics with verses and chorus.\n"
            "3. You preview and approve or regenerate the lyrics.\n"
            "4. Suno AI generates the backing track and sings the vocals in high quality!"
        ),
    },

    # -----------------------------------------------------------------------
    # 2. Вопросы для шагов FSM (имя, повод, детали, жанр)
    # -----------------------------------------------------------------------
    "step_name": {
        LANG_RU: (
            "🎵 <b>Шаг 1 из 4: Для кого создаем песню?</b>\n\n"
            "Напишите имя адресата (например: «Александр», «Любимая Катя», «Мама Алия»):"
        ),
        LANG_KK: (
            "🎵 <b>1-қадам (4-тен): Ән кімге арналады?</b>\n\n"
            "Құттықтау иесінің есімін жазыңыз (мысалы: «Айдар», «Анашым Гүлнар», «Бастығымыз Арман»):"
        ),
        LANG_EN: (
            "🎵 <b>Step 1 of 4: Who is this song for?</b>\n\n"
            "Type the recipient's name (e.g., 'Alexander', 'Sweet Sarah', 'Mom Diana'):"
        ),
    },
    "name_error": {
        LANG_RU: "⚠️ Имя должно быть от 2 до 60 символов. Попробуйте еще раз:",
        LANG_KK: "⚠️ Есім 2-ден 60 таңбаға дейін болуы керек. Қайта жазып көріңіз:",
        LANG_EN: "⚠️ Name must be between 2 and 60 characters. Please try again:",
    },
    "step_occasion_first": {
        LANG_RU: (
            "🎉 <b>Шаг 1 из 3: Какой повод для песни?</b>\n\n"
            "Выберите вариант из списка ниже или отправьте свой текст сообщением:"
        ),
        LANG_KK: (
            "🎉 <b>1-қадам (3-тен): Қандай мереке немесе себеп?</b>\n\n"
            "Төмендегі нұсқалардың бірін таңдаңыз немесе өз нұсқаңызды жазыңыз:"
        ),
        LANG_EN: (
            "🎉 <b>Step 1 of 3: What is the occasion?</b>\n\n"
            "Choose an option from the list below or send your own text:"
        ),
    },
    "step_occasion": {
        LANG_RU: (
            "🎉 Принято: <b>{name}</b>!\n\n"
            "<b>Шаг 2 из 4: Какой повод для песни?</b>\n"
            "Выберите вариант из списка ниже или отправьте свой текст сообщением:"
        ),
        LANG_KK: (
            "🎉 Қабылданды: <b>{name}</b>!\n\n"
            "<b>2-қадам (4-тен): Қандай мереке немесе себеп?</b>\n"
            "Төмендегі нұсқалардың бірін таңдаңыз немесе өз нұсқаңызды жазыңыз:"
        ),
        LANG_EN: (
            "🎉 Got it: <b>{name}</b>!\n\n"
            "<b>Step 2 of 4: What is the occasion?</b>\n"
            "Choose an option from the list below or send your own text:"
        ),
    },
    "occasion_error": {
        LANG_RU: "⚠️ Текст повода должен быть от 3 до 100 символов. Попробуйте еще раз:",
        LANG_KK: "⚠️ Мереке атауы 3-тен 100 таңбаға дейін болуы керек. Қайта жазыңыз:",
        LANG_EN: "⚠️ Occasion must be between 3 and 100 characters. Please try again:",
    },
    "step_details": {
        LANG_RU: (
            "🎈 Повод: <b>{occasion}</b>\n\n"
            "<b>Шаг 3 из 4: Факты, черты характера и пожелания</b>\n\n"
            "Расскажите подробнее об адресате (хобби, любимые фразы, забавные привычки или пожелания):\n"
            "<i>Например: Любит путешествия, программирует по ночам, пьет зеленый чай. Желаем ярких побед!</i>"
        ),
        LANG_KK: (
            "🎈 Мереке: <b>{occasion}</b>\n\n"
            "<b>3-қадам (4-тен): Қызықты деректер, мінезі мен тілектер</b>\n\n"
            "Құттықтау иесі туралы толығырақ айтып беріңіз (хоббиі, жақсы көретін ісі, қызықты сәттері, арнайы тілектер):\n"
            "<i>Мысалы: Саяхаттағанды жақсы көреді, таңертең кофе ішеді, көлікті жылдам жүргізеді. Зор денсаулық пен бақыт тілейміз!</i>"
        ),
        LANG_EN: (
            "🎈 Occasion: <b>{occasion}</b>\n\n"
            "<b>Step 3 of 4: Facts, personal traits, and wishes</b>\n\n"
            "Tell us more about the person (hobbies, funny quirks, favorite memories, or specific wishes):\n"
            "<i>Example: Loves road trips, drinks green tea every morning, always late but the life of the party. Wish them endless joy and success!</i>"
        ),
    },
    "details_error": {
        LANG_RU: "⚠️ Пожалуйста, напишите чуть подробнее (от 10 до 1000 символов):",
        LANG_KK: "⚠️ Өтініш, толығырақ жазыңыз (10-нан 1000 таңбаға дейін):",
        LANG_EN: "⚠️ Please provide a bit more detail (10 to 1000 characters):",
    },
    "step_genre": {
        LANG_RU: (
            "📝 Факты сохранены!\n\n"
            "<b>Шаг 4 из 4: В каком жанре и стиле написать песню?</b>\n"
            "Выберите желаемый стиль трека из списка ниже:"
        ),
        LANG_KK: (
            "📝 Мәліметтер сақталды!\n\n"
            "<b>4-қадам (4-тен): Ән қандай жанрда және стильде болсын?</b>\n"
            "Қалаған музыкалық стильді төмендегі тізімнен таңдаңыз:"
        ),
        LANG_EN: (
            "📝 Details saved!\n\n"
            "<b>Step 4 of 4: Which genre and musical style?</b>\n"
            "Select your preferred music style from the list below:"
        ),
    },

    # -----------------------------------------------------------------------
    # 3. Кнопки интерфейса
    # -----------------------------------------------------------------------
    "btn_start_order": {
        LANG_RU: "🎵 Создать песню",
        LANG_KK: "🎵 Ән жасау",
        LANG_EN: "🎵 Create Song",
    },
    "btn_how_it_works": {
        LANG_RU: "ℹ️ Как это работает",
        LANG_KK: "ℹ️ Бұл қалай жұмыс істейді",
        LANG_EN: "ℹ️ How it works",
    },
    "btn_change_lang": {
        LANG_RU: "🌐 Сменить язык",
        LANG_KK: "🌐 Тілді ауыстыру",
        LANG_EN: "🌐 Change language",
    },
    "btn_approve": {
        LANG_RU: "✨ Запустить генерацию",
        LANG_KK: "✨ Әнді жасау",
        LANG_EN: "✨ Generate Song",
    },
    "btn_rewrite": {
        LANG_RU: "✏️ Переписать",
        LANG_KK: "✏️ Қайта жазу",
        LANG_EN: "✏️ Rewrite",
    },
    "btn_cancel": {
        LANG_RU: "❌ Отмена",
        LANG_KK: "❌ Бас тарту",
        LANG_EN: "❌ Cancel",
    },

    # -----------------------------------------------------------------------
    # 4. Системные статусы и предпросмотр
    # -----------------------------------------------------------------------
    "generating_lyrics": {
        LANG_RU: "✍️ <b>Нейросеть сочиняет текст песни...</b>\n<i>Подбираем рифмы и ритм под ваш жанр.</i>",
        LANG_KK: "✍️ <b>Нейрожелі әннің сөзін шығаруда...</b>\n<i>Ұйқасы мен ырғағын таңдалған жанрға бейімдеп жатырмыз.</i>",
        LANG_EN: "✍️ <b>AI is composing the lyrics...</b>\n<i>Crafting rhymes and rhythm to match your style.</i>",
    },
    "rewriting_lyrics": {
        LANG_RU: "🔄 <b>Сочиняем новый вариант текста...</b>",
        LANG_KK: "🔄 <b>Әннің жаңа нұсқасын жазып жатырмыз...</b>",
        LANG_EN: "🔄 <b>Composing a new version of the lyrics...</b>",
    },
    "generating_audio": {
        LANG_RU: "🎵 <b>Suno AI записывает песню в студии...</b>\n<i>Это занимает обычно 1-2 минуты.</i>",
        LANG_KK: "🎵 <b>Suno AI әнді студияда жазуда...</b>\n<i>Бұл шамамен 1-2 минут уақыт алады.</i>",
        LANG_EN: "🎵 <b>Suno AI is generating the studio track...</b>\n<i>This typically takes 1-2 minutes.</i>",
    },
    "studio_busy_queued": {
        LANG_RU: "⏳ <b>Студия сейчас занята (5/5).</b>\nВаша заявка принята, вы в очереди: <b>#{position}</b>",
        LANG_KK: "⏳ <b>Қазір студия бос емес (5/5).</b>\nӨтінішіңіз қабылданды, кезегіңіз: <b>#{position}</b>",
        LANG_EN: "⏳ <b>The studio is currently busy (5/5).</b>\nYour request is accepted, queue position: <b>#{position}</b>",
    },
    "studio_slot_available": {
        LANG_RU: "🎙 <b>Студия свободна!</b>\nНачинаем генерацию и сведение (~1-2 мин)...",
        LANG_KK: "🎙 <b>Студия босады!</b>\nӘнді жасау және өңдеу басталды (~1-2 мин)...",
        LANG_EN: "🎙 <b>Studio slot available!</b>\nStarting generation and mastering (~1-2 min)...",
    },
    "progress_title": {
        LANG_RU: "Создание вашей песни...",
        LANG_KK: "Әніңіз жасалуда...",
        LANG_EN: "Generating your song...",
    },
    "progress_sec": {
        LANG_RU: "сек",
        LANG_KK: "сек",
        LANG_EN: "s",
    },
    "progress_ready": {
        LANG_RU: "Готово! Отправляем аудио...",
        LANG_KK: "Дайын! Аудио жіберілуде...",
        LANG_EN: "Done! Sending audio...",
    },
    "step_details_name_facts": {
        LANG_RU: (
            "📝 <b>Шаг 2 из 3: Введите имя и 2-3 личных факта</b>\n\n"
            "Напишите имя адресата и факты о нем (профессия, хобби, характер, привычки или добрые приколы) в одном сообщении.\n\n"
            "<i>Пример: «Азамат. Обожает гонять на мотоцикле, каждое утро пьет крепкий кофе и постоянно опаздывает на встречи».</i>"
        ),
        LANG_KK: (
            "📝 <b>2-қадам (3-тен): Есімін және 2-3 жеке деректі жазыңыз</b>\n\n"
            "Бір хабарламада құттықтау иесінің есімін және деректерді (хоббиі, мінезі, қызықтары, әдеттері) жазыңыз.\n\n"
            "<i>Мысалы: «Азамат. Мотоцикл тебуді жақсы көреді, таңертең кофе ішеді, үнемі кездесуге кешігіп келеді».</i>"
        ),
        LANG_EN: (
            "📝 <b>Step 2 of 3: Enter name and 2-3 personal facts</b>\n\n"
            "Type the recipient's name and facts (hobbies, traits, habits, inside jokes) in a single message.\n\n"
            "<i>Example: 'Azamat. Loves riding motorcycles, drinks strong coffee every morning, always late for meetings'.</i>"
        ),
    },
    "moderation_failed": {
        LANG_RU: (
            "⚠️ <b>Текст не прошел проверку безопасности:</b>\n"
            "<i>{reason}</i>\n\n"
            "Пожалуйста, перефразируйте факты (без ненормативной лексики, оскорблений или тем 18+):"
        ),
        LANG_KK: (
            "⚠️ <b>Мәлімет қауіпсіздік тексерісінен өтпеді:</b>\n"
            "<i>{reason}</i>\n\n"
            "Өтініш, деректерді балағат сөздерсіз және қорлаусыз қайта жазыңыз:"
        ),
        LANG_EN: (
            "⚠️ <b>Input did not pass safety moderation:</b>\n"
            "<i>{reason}</i>\n\n"
            "Please rephrase your facts (avoiding profanity, insults, or 18+ content):"
        ),
    },
    "mandatory_disclaimer": {
        LANG_RU: "⚠️ <b>Внимание:</b> трек создается искусственным интеллектом строго по вашей анкете. Претензии по тембру и интонациям нейросети не принимаются.",
        LANG_KK: "⚠️ <b>Назар аударыңыз:</b> ән жасанды интеллект арқылы жасалады. Мәтін мен жанр сауалнамаңызға сай келеді. Нейрожелінің дауыс тембрі мен интонациясына шағымдар қабылданбайды.",
        LANG_EN: "⚠️ <b>Notice:</b> the track is generated by artificial intelligence strictly based on your questionnaire. Claims regarding vocal timbre or intonation are not accepted.",
    },
    "preview_lyrics": {
        LANG_RU: (
            "🎵 <b>Готовый текст для «{name}»</b>\n"
            "🎸 <b>Стиль:</b> {genre}\n"
            "🎉 <b>Повод:</b> {occasion}\n\n"
            "<blockquote>{lyrics}</blockquote>\n\n"
            "⚠️ <i>Внимание: трек создается искусственным интеллектом строго по вашей анкете. Претензии по тембру и интонациям нейросети не принимаются.</i>"
        ),
        LANG_KK: (
            "🎵 <b>«{name}» үшін дайын ән мәтіні</b>\n"
            "🎸 <b>Стилі:</b> {genre}\n"
            "🎉 <b>Мереке:</b> {occasion}\n\n"
            "<blockquote>{lyrics}</blockquote>\n\n"
            "⚠️ <i>Назар аударыңыз: ән жасанды интеллект арқылы жасалады. Мәтін мен жанр сауалнамаңызға сай келеді. Нейрожелінің дауыс тембрі мен интонациясына шағымдар қабылданбайды.</i>"
        ),
        LANG_EN: (
            "🎵 <b>Generated Lyrics for '{name}'</b>\n"
            "🎸 <b>Style:</b> {genre}\n"
            "🎉 <b>Occasion:</b> {occasion}\n\n"
            "<blockquote>{lyrics}</blockquote>\n\n"
            "⚠️ <i>Notice: the track is generated by artificial intelligence strictly based on your questionnaire. Claims regarding vocal timbre or intonation are not accepted.</i>"
        ),
    },
    "btn_approve_sing": {
        LANG_RU: "✅ Все верно, поем!",
        LANG_KK: "✅ Барлығы дұрыс, ән шырқайық!",
        LANG_EN: "✅ All good, let's sing!",
    },
    "btn_approve_sing_test": {
        LANG_RU: "✅ Все верно, поем! (Тест: 0 ⭐️)",
        LANG_KK: "✅ Барлығы дұрыс, ән шырқайық! (Тест: 0 ⭐️)",
        LANG_EN: "✅ All good, let's sing! (Test: 0 ⭐️)",
    },
    "test_payment_confirmed": {
        LANG_RU: "🧪 <b>Тестовая оплата подтверждена (Бесплатно)!</b>\nПередаем задачу в студию...",
        LANG_KK: "🧪 <b>Сынақ төлемі расталды (Тегін)!</b>\nТапсырма студияға жіберілуде...",
        LANG_EN: "🧪 <b>Test payment confirmed (Free)!</b>\nSubmitting job to studio...",
    },
    "btn_edit_details": {
        LANG_RU: "🔄 Начать заново",
        LANG_KK: "🔄 Қайта бастау",
        LANG_EN: "🔄 Start over",
    },
    "stars_invoice_title": {
        LANG_RU: "🎵 Персональная песня (Suno AI)",
        LANG_KK: "🎵 Жеке құттықтау әні (Suno AI)",
        LANG_EN: "🎵 Custom Song (Suno AI)",
    },
    "stars_invoice_desc": {
        LANG_RU: "Студийный трек с вокалом и музыкой по вашей анкете (60 Stars)",
        LANG_KK: "Шынайы дауыс пен әуені бар студиялық сападағы ән (60 Stars)",
        LANG_EN: "Studio track with vocals and music based on your facts (60 Stars)",
    },
    "stars_invoice_label": {
        LANG_RU: "Создание песни",
        LANG_KK: "Ән жасау",
        LANG_EN: "Song Generation",
    },
    "pre_checkout_error": {
        LANG_RU: "⚠️ Студия временно на техобслуживании. Звёзды не списаны, попробуйте позже!",
        LANG_KK: "⚠️ Студияда уақытша техникалық жұмыстар жүруде. Жұлдыздар алынған жоқ, кейінірек қайталап көріңіз!",
        LANG_EN: "⚠️ Studio is temporarily in maintenance. Stars were not charged, please try again later!",
    },
    "stars_refund_notice": {
        LANG_RU: "❌ Ошибка при генерации трека. Все звёзды автоматически возвращены на ваш баланс Telegram!",
        LANG_KK: "❌ Әнді жасау кезінде қате орын алды. Барлық жұлдыздар Telegram теңгеріміңізге автоматты түрде қайтарылды!",
        LANG_EN: "❌ Error generating the track. All Stars have been automatically refunded to your Telegram balance!",
    },
    "already_generating": {
        LANG_RU: "⏳ Песня уже создается! Пожалуйста, дождитесь окончания генерации.",
        LANG_KK: "⏳ Ән қазір жасалып жатыр! Өтініш, дайын болғанша күте тұрыңыз.",
        LANG_EN: "⏳ The song is already generating! Please wait for it to complete.",
    },
    "order_canceled": {
        LANG_RU: "❌ <b>Создание песни отменено.</b>\nВы можете начать заново в любой момент через /start.",
        LANG_KK: "❌ <b>Ән жасау тоқтатылды.</b>\nКез келген уақытта /start арқылы қайта бастай аласыз.",
        LANG_EN: "❌ <b>Song creation canceled.</b>\nYou can start again at any time via /start.",
    },

    # -----------------------------------------------------------------------
    # 5. Ошибки и успешная выдача трека
    # -----------------------------------------------------------------------
    "credits_exhausted": {
        LANG_RU: (
            "⚠️ <b>В сервисе генерации музыки временно закончились кредиты.</b>\n\n"
            "Пожалуйста, свяжитесь с администратором бота или повторите попытку позже."
        ),
        LANG_KK: (
            "⚠️ <b>Музыка жасау сервисінде несиелер (кредиттер) уақытша таусылды.</b>\n\n"
            "Өтініш, бот әкімшісіне хабарласыңыз немесе кейінірек қайталап көріңіз."
        ),
        LANG_EN: (
            "⚠️ <b>Insufficient credits on the music generation service.</b>\n\n"
            "Please contact the administrator or try again later."
        ),
    },
    "lyrics_failed": {
        LANG_RU: "❌ <b>Не удалось сгенерировать текст песни:</b>\n<i>{err}</i>",
        LANG_KK: "❌ <b>Ән мәтінін шығару мүмкін болмады:</b>\n<i>{err}</i>",
        LANG_EN: "❌ <b>Failed to generate song lyrics:</b>\n<i>{err}</i>",
    },
    "audio_timeout": {
        LANG_RU: "⏳ <b>Превышено время ожидания готовности песни.</b> Попробуйте позже.",
        LANG_KK: "⏳ <b>Әннің дайын болу уақыты тым ұзаққа созылды.</b> Кейінірек қайталап көріңіз.",
        LANG_EN: "⏳ <b>Song generation timed out.</b> Please try again later.",
    },
    "audio_failed": {
        LANG_RU: "❌ <b>Ошибка генерации музыки:</b>\n<i>{err}</i>",
        LANG_KK: "❌ <b>Музыка жасау кезінде қате орын алды:</b>\n<i>{err}</i>",
        LANG_EN: "❌ <b>Music generation error:</b>\n<i>{err}</i>",
    },
    "song_ready_caption": {
        LANG_RU: (
            "🎉 <b>Ваша песня готова!</b>\n\n"
            "👤 <b>Кому:</b> {name}\n"
            "🎈 <b>Повод:</b> {occasion}\n"
            "🎸 <b>Стиль:</b> {genre}\n\n"
            "<i>Сгенерировано с помощью Suno AI и Telegram Bot</i>"
        ),
        LANG_KK: (
            "🎉 <b>Сіздің әніңіз дайын!</b>\n\n"
            "👤 <b>Кімге:</b> {name}\n"
            "🎈 <b>Мереке:</b> {occasion}\n"
            "🎸 <b>Стилі:</b> {genre}\n\n"
            "<i>Suno AI және Telegram Bot арқылы жасалды</i>"
        ),
        LANG_EN: (
            "🎉 <b>Your song is ready!</b>\n\n"
            "👤 <b>For:</b> {name}\n"
            "🎈 <b>Occasion:</b> {occasion}\n"
            "🎸 <b>Style:</b> {genre}\n\n"
            "<i>Generated with Suno AI & Telegram Bot</i>"
        ),
    },
    "order_another": {
        LANG_RU: "Хотите заказать еще одну песню?",
        LANG_KK: "Тағы бір ән жаздырғыңыз келе ме?",
        LANG_EN: "Would you like to order another song?",
    },
}

# ---------------------------------------------------------------------------
# Aliases for backward compatibility with different handler conventions
# ---------------------------------------------------------------------------
TEXTS["choose_lang"] = TEXTS["choose_language"]
TEXTS["lang_changed"] = TEXTS["language_selected"]
TEXTS["ask_name"] = TEXTS["step_name"]
TEXTS["name_err"] = TEXTS["name_error"]
TEXTS["ask_occasion"] = TEXTS["step_occasion"]
TEXTS["occasion_err"] = TEXTS["occasion_error"]
TEXTS["ask_details"] = TEXTS["step_details"]
TEXTS["details_err"] = TEXTS["details_error"]
TEXTS["ask_genre"] = TEXTS["step_genre"]
TEXTS["lyrics_generating"] = TEXTS["generating_lyrics"]
TEXTS["lyrics_rewriting"] = TEXTS["rewriting_lyrics"]
TEXTS["preview_header"] = TEXTS["preview_lyrics"]
TEXTS["preview_caption"] = TEXTS["preview_lyrics"]
TEXTS["lyrics_error"] = TEXTS["lyrics_failed"]
TEXTS["audio_error"] = TEXTS["audio_failed"]
TEXTS["track_ready"] = TEXTS["song_ready_caption"]
TEXTS["order_again"] = TEXTS["order_another"]

# ---------------------------------------------------------------------------
# Списки поводов (Occasions) для каждого языка
# ---------------------------------------------------------------------------
OCCASIONS_LIST: dict[str, list[tuple[str, str]]] = {
    LANG_RU: [
        ("🎂 День рождения", "День рождения"),
        ("😂 Прикол над другом", "Прикол над другом"),
        ("❤️ Любовь / Романтика", "Любовь и романтика"),
        ("💌 С любовью / Признание", "Признание в чувствах"),
        ("💍 Свадьба / Юбилей", "Свадьба"),
    ],
    LANG_KK: [
        ("🎂 Туған күн", "Туған күн"),
        ("😂 Досқа әзіл-қалжың", "Досқа әзіл"),
        ("❤️ Махаббат / Романтика", "Махаббат және романтика"),
        ("💌 Сүйіктіме арнау / Сезім білдіру", "Сүйіктіме арнау"),
        ("💍 Үйлену той / Мерейтой", "Үйлену той"),
    ],
    LANG_EN: [
        ("🎂 Birthday", "Birthday"),
        ("😂 Friend Prank / Roast", "Friend Prank"),
        ("❤️ Love / Romance", "Love and Romance"),
        ("💌 Dedication / Confession", "Love Confession"),
        ("💍 Wedding / Anniversary", "Wedding"),
    ],
}

OCCASIONS_MAP = OCCASIONS_LIST

# ---------------------------------------------------------------------------
# Сетка жанров (Genres) - 10 популярных музыкальных стилей
# ---------------------------------------------------------------------------
GENRES_LIST: dict[str, list[dict[str, str]]] = {
    LANG_RU: [
        {"id": "qpop", "label": "🎤 Q-pop", "style": "modern kazakh q-pop, electronic dance upbeat energetic catchy"},
        {"id": "toi", "label": "🪕 Той / Эстрада", "style": "kazakh toi pop estrada, celebratory joyful cheerful dombra dance"},
        {"id": "drill_rap", "label": "⚡ Дрилл / Рэп", "style": "drill hip hop rap, aggressive 808 bass, dark energetic fast flow"},
        {"id": "acoustic", "label": "🎸 Акустика", "style": "warm acoustic guitar, soulful intimate melody, live acoustic strings"},
        {"id": "retro_disco", "label": "🕺 Диско 80-х", "style": "80s synth disco pop, vintage synthesizer, upbeat nostalgic dance rhythm"},
        {"id": "rock_ballad", "label": "🤘 Рок-баллада", "style": "melodic powerful rock ballad, electric guitar solo, driving drums emotional"},
        {"id": "club_house", "label": "🎧 Клубный House", "style": "modern deep house edm, driving grooving bassline, dance club electronic"},
        {"id": "jazz_blues", "label": "🎷 Джаз / Блюз", "style": "smooth lounge jazz blues, warm saxophone, soulful piano swing melody"},
        {"id": "rnb_pop", "label": "✨ R&B / Соул", "style": "smooth contemporary rnb soul, groovy modern beats, emotional velvet vocals"},
        {"id": "chanson", "label": "🪗 Шансон", "style": "warm soulful chanson lyrical romance, acoustic accordion, narrative heartfelt melody"},
    ],
    LANG_KK: [
        {"id": "qpop", "label": "🎤 Q-pop", "style": "modern kazakh q-pop, electronic dance upbeat energetic catchy"},
        {"id": "toi", "label": "🪕 Той / Эстрада", "style": "kazakh toi pop estrada, celebratory joyful cheerful dombra dance"},
        {"id": "drill_rap", "label": "⚡ Дрилл / Рэп", "style": "drill hip hop rap, aggressive 808 bass, dark energetic fast flow"},
        {"id": "acoustic", "label": "🎸 Акустика", "style": "warm acoustic guitar, soulful intimate melody, live acoustic strings"},
        {"id": "retro_disco", "label": "🕺 80-жылдар дискосы", "style": "80s synth disco pop, vintage synthesizer, upbeat nostalgic dance rhythm"},
        {"id": "rock_ballad", "label": "🤘 Рок баллада", "style": "melodic powerful rock ballad, electric guitar solo, driving drums emotional"},
        {"id": "club_house", "label": "🎧 Клубтық House", "style": "modern deep house edm, driving grooving bassline, dance club electronic"},
        {"id": "jazz_blues", "label": "🎷 Джаз / Блюз", "style": "smooth lounge jazz blues, warm saxophone, soulful piano swing melody"},
        {"id": "rnb_pop", "label": "✨ R&B / Соул", "style": "smooth contemporary rnb soul, groovy modern beats, emotional velvet vocals"},
        {"id": "chanson", "label": "🪗 Шансон / Романс", "style": "warm soulful chanson lyrical romance, acoustic accordion, narrative heartfelt melody"},
    ],
    LANG_EN: [
        {"id": "qpop", "label": "🎤 Q-pop", "style": "modern kazakh q-pop, electronic dance upbeat energetic catchy"},
        {"id": "toi", "label": "🪕 Toi / Estrada", "style": "kazakh toi pop estrada, celebratory joyful cheerful dombra dance"},
        {"id": "drill_rap", "label": "⚡ Drill / Rap", "style": "drill hip hop rap, aggressive 808 bass, dark energetic fast flow"},
        {"id": "acoustic", "label": "🎸 Acoustic", "style": "warm acoustic guitar, soulful intimate melody, live acoustic strings"},
        {"id": "retro_disco", "label": "🕺 80s Disco", "style": "80s synth disco pop, vintage synthesizer, upbeat nostalgic dance rhythm"},
        {"id": "rock_ballad", "label": "🤘 Rock Ballad", "style": "melodic powerful rock ballad, electric guitar solo, driving drums emotional"},
        {"id": "club_house", "label": "🎧 Club House", "style": "modern deep house edm, driving grooving bassline, dance club electronic"},
        {"id": "jazz_blues", "label": "🎷 Jazz & Blues", "style": "smooth lounge jazz blues, warm saxophone, soulful piano swing melody"},
        {"id": "rnb_pop", "label": "✨ R&B / Soul", "style": "smooth contemporary rnb soul, groovy modern beats, emotional velvet vocals"},
        {"id": "chanson", "label": "🪗 Chanson", "style": "warm soulful chanson lyrical romance, acoustic accordion, narrative heartfelt melody"},
    ],
}

GENRES_MAP: dict[str, list[tuple[str, str]]] = {
    lang: [(item["label"], item["style"]) for item in items]
    for lang, items in GENRES_LIST.items()
}

GENRE_STYLES: dict[str, str] = {
    "qpop": "modern kazakh q-pop, electronic dance upbeat energetic catchy",
    "toi": "kazakh toi pop estrada, celebratory joyful cheerful dombra dance",
    "drill_rap": "drill hip hop rap, aggressive 808 bass, dark energetic fast flow",
    "acoustic": "warm acoustic guitar, soulful intimate melody, live acoustic strings",
    "retro_disco": "80s synth disco pop, vintage synthesizer, upbeat nostalgic dance rhythm",
    "rock_ballad": "melodic powerful rock ballad, electric guitar solo, driving drums emotional",
    "club_house": "modern deep house edm, driving grooving bassline, dance club electronic",
    "jazz_blues": "smooth lounge jazz blues, warm saxophone, soulful piano swing melody",
    "rnb_pop": "smooth contemporary rnb soul, groovy modern beats, emotional velvet vocals",
    "chanson": "warm soulful chanson lyrical romance, acoustic accordion, narrative heartfelt melody",
}


def get_genre_style(genre_key: str) -> str:
    """Return Apiframe / Suno prompt style for a genre key."""
    return GENRE_STYLES.get(genre_key, genre_key)


def get_genre_label(genre_key: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """Return localized genre label for UI display."""
    genres = GENRES_LIST.get(lang) or GENRES_LIST.get(DEFAULT_LANGUAGE, [])
    for item in genres:
        if item.get("id") == genre_key or item.get("style") == genre_key:
            return item["label"]
    return genre_key


# ---------------------------------------------------------------------------
# Анимация ожидания: ротируемые статусы для services/ui_animator.py
# ---------------------------------------------------------------------------
ANIMATION_FRAMES: dict[str, list[str]] = {
    LANG_RU: [
        "✍️ Нейросеть сочиняет текст и подбирает рифмы...",
        "🎸 Аранжировщик настраивает гармонию и аккорды...",
        "🥁 Барабанщик задает праздничный грув и темп...",
        "🎙️ Вокалист выходит к микрофону на кульминацию припева...",
        "🎛️ Звукорежиссер сводит финальный студийный мастер...",
        "🎧 Почти готово! Полируем звучание трека...",
    ],
    LANG_KK: [
        "✍️ Нейрожелі әннің сөзін ұйқастырып жатыр...",
        "🎸 Композитор әуен мен аккордтарды үйлестіруде...",
        "🥁 Ырғақ пен көңілді екпін қосылуда...",
        "🎙️ Әнші студиялық микрофонда қайырманы шырқауда...",
        "🎛️ Дыбыс режиссері таза әуенді өңдеп жатыр...",
        "🎧 Аз қалды! Әннің соңғы штрихтары аяқталуда...",
    ],
    LANG_EN: [
        "✍️ AI is crafting lyrics and fine-tuning rhymes...",
        "🎸 Arranging musical harmony and catchy chords...",
        "🥁 Setting up the celebratory groove and tempo...",
        "🎙️ Vocalist is in the booth recording the chorus hook...",
        "🎛️ Audio engineer is mastering the final mix...",
        "🎧 Almost ready! Putting the finishing polish on your song...",
    ],
}


def t(key: str, lang: str = LANG_RU, **kwargs: Any) -> str:
    """
    Get localized string by key and language, formatting kwargs if provided.
    Falls back to Russian, then to key representation if translation is missing.
    """
    lang_dict = TEXTS.get(key, {})
    template = lang_dict.get(lang) or lang_dict.get(LANG_RU) or f"[{key}]"
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template


# Function alias
get_text = t
