import logging
import json
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import requests

# Конфигурация
KINOPOISK_API_KEY = "7QPGYYT-CV5MZSQ-M5GC50S-VD4BVH4"
BOT_TOKEN = "7981463799:AAHxvci7hCtrq_Zm1pfpYHNmJFgrIrVe9r8"

# Файлы для хранения данных
FAVORITES_FILE = "favorites.json"
WATCHLIST_FILE = "watchlist.json"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def load_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_data(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_to_list(user_id, movie_data, list_type):
    filename = FAVORITES_FILE if list_type == "favorites" else WATCHLIST_FILE
    data = load_data(filename)

    if str(user_id) not in data:
        data[str(user_id)] = []

    for movie in data[str(user_id)]:
        if movie.get('id') == movie_data.get('id'):
            return False

    data[str(user_id)].append(movie_data)
    save_data(filename, data)
    return True


def remove_from_list(user_id, movie_id, list_type):
    """Удаляет фильм из списка"""
    filename = FAVORITES_FILE if list_type == "favorites" else WATCHLIST_FILE
    data = load_data(filename)

    if str(user_id) in data:
        initial_length = len(data[str(user_id)])
        data[str(user_id)] = [movie for movie in data[str(user_id)] if str(movie.get('id')) != str(movie_id)]

        if len(data[str(user_id)]) < initial_length:
            save_data(filename, data)
            return True

    return False


def get_user_list(user_id, list_type):
    filename = FAVORITES_FILE if list_type == "favorites" else WATCHLIST_FILE
    data = load_data(filename)
    return data.get(str(user_id), [])


def is_movie_in_list(user_id, movie_id, list_type):
    """Проверяет, есть ли фильм в списке"""
    user_list = get_user_list(user_id, list_type)
    return any(str(movie.get('id')) == str(movie_id) for movie in user_list)


def get_main_keyboard():
    keyboard = [
        [KeyboardButton("🎬 Поиск фильмов"), KeyboardButton("📺 Поиск сериалов")],
        [KeyboardButton("⭐ Избранное"), KeyboardButton("🎯 Хочу посмотреть")],
        [KeyboardButton("🎲 Случайный фильм"), KeyboardButton("📺 Случайный сериал")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_back_keyboard():
    keyboard = [
        [KeyboardButton("⬅️ Назад в меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_movie_actions_keyboard(movie_id, user_id, is_series=False):
    """Создает клавиатуру с учетом того, есть ли фильм/сериал в списках"""
    in_favorites = is_movie_in_list(user_id, movie_id, "favorites")
    in_watchlist = is_movie_in_list(user_id, movie_id, "watchlist")

    keyboard = []

    # Кнопки для избранного
    if in_favorites:
        keyboard.append([InlineKeyboardButton("❌ Удалить из избранного", callback_data=f"remove_fav_{movie_id}")])
    else:
        keyboard.append([InlineKeyboardButton("⭐ В избранное", callback_data=f"add_fav_{movie_id}")])

    # Кнопки для списка желаемого
    if in_watchlist:
        keyboard.append([InlineKeyboardButton("❌ Удалить из желаемого", callback_data=f"remove_watch_{movie_id}")])
    else:
        keyboard.append([InlineKeyboardButton("🎯 Хочу посмотреть", callback_data=f"add_watch_{movie_id}")])

    return InlineKeyboardMarkup(keyboard)


def get_list_management_keyboard(list_type):
    """Клавиатура для управления списками"""
    if list_type == "favorites":
        keyboard = [
            [KeyboardButton("🗑 Очистить избранное")],
            [KeyboardButton("⬅️ Назад в меню")]
        ]
    else:
        keyboard = [
            [KeyboardButton("🗑 Очистить желаемое")],
            [KeyboardButton("⬅️ Назад в меню")]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def has_poster_and_description(content):
    """Проверяет, есть ли у фильма/сериала постер и описание"""
    # Проверяем постер
    poster = content.get('poster', {})
    if not isinstance(poster, dict):
        return False
    poster_url = poster.get('url')
    if not poster_url or not poster_url.startswith('http'):
        return False

    # Проверяем описание - ДАЖЕ ЕСЛИ КОРОТКОЕ, ГЛАВНОЕ ЧТОБЫ БЫЛО
    description = content.get('description', '')
    if not description or description == 'None':
        description = content.get('shortDescription', '')
        if not description or description == 'None':
            return False

    return True


def is_modern_content(content):
    """Проверяет, что фильм/сериал выпущен с 1998 года"""
    year = content.get('year')
    if not year:
        return False
    try:
        return int(year) >= 1998
    except (ValueError, TypeError):
        return False


def get_content_type(content):
    """Определяет тип контента (фильм или сериал)"""
    type_str = content.get('type', '')
    if type_str == 'tv-series':
        return 'сериал'
    elif type_str == 'movie':
        return 'фильм'
    else:
        return 'контент'


async def get_quality_random_movie():
    """Ищет случайный фильм ТОЛЬКО с 1998 года с постером и описанием"""
    max_attempts = 15

    for attempt in range(max_attempts):
        try:
            # Добавляем случайные параметры для разнообразия
            params = {
                "type": "movie",
                "year": "1998-2025",
                "rating.kp": "5-10",
                "votes.kp": "1000-10000000"
            }

            # Добавляем случайный номер страницы для разнообразия
            if random.random() > 0.5:
                params["page"] = random.randint(1, 10)

            response = requests.get(
                "https://api.kinopoisk.dev/v1.4/movie/random",
                headers={"X-API-KEY": KINOPOISK_API_KEY},
                params=params,
                timeout=8
            )

            if response.status_code == 200:
                movie = response.json()

                if (is_modern_content(movie) and
                        has_poster_and_description(movie)):
                    logger.info(f"Found modern quality movie: {movie.get('name')} ({movie.get('year')})")
                    return movie

        except Exception as e:
            logger.error(f"Attempt {attempt + 1}: Error: {e}")
            continue

    return None


async def get_truly_random_series():
    """Находит СЛУЧАЙНЫЙ сериал разными методами для максимального разнообразия"""

    # Список методов поиска для разнообразия
    methods = [
        _random_series_method1,  # Случайный запрос с разными параметрами
        _random_series_method2,  # Поиск по популярным с рандомной страницей
        _random_series_method3,  # Поиск по разным годам
        _random_series_method4  # Поиск по разным рейтингам
    ]

    # Перемешиваем методы для разнообразия
    random.shuffle(methods)

    for method in methods:
        try:
            series = await method()
            if series:
                logger.info(f"Found series using {method.__name__}: {series.get('name')} ({series.get('year')})")
                return series
        except Exception as e:
            logger.error(f"Method {method.__name__} failed: {e}")
            continue

    return None


async def _random_series_method1():
    """Метод 1: Случайный запрос с разными параметрами"""
    max_attempts = 10

    for attempt in range(max_attempts):
        try:
            # Случайные параметры для разнообразия
            years = ["1998-2025", "2000-2010", "2010-2020", "2020-2025"]
            ratings = ["5-10", "6-10", "7-10", "4-10"]

            params = {
                "type": "tv-series",
                "year": random.choice(years),
                "rating.kp": random.choice(ratings),
                "votes.kp": "1000-10000000"
            }

            # Добавляем случайную страницу иногда
            if random.random() > 0.7:
                params["page"] = random.randint(1, 20)

            response = requests.get(
                "https://api.kinopoisk.dev/v1.4/movie/random",
                headers={"X-API-KEY": KINOPOISK_API_KEY},
                params=params,
                timeout=8
            )

            if response.status_code == 200:
                series = response.json()
                if (is_modern_content(series) and has_poster_and_description(series)):
                    return series

        except Exception as e:
            continue

    return None


async def _random_series_method2():
    """Метод 2: Поиск популярных сериалов со случайной страницы"""
    try:
        # Берем случайную страницу из популярных сериалов
        page = random.randint(1, 50)

        response = requests.get(
            "https://api.kinopoisk.dev/v1.4/movie",
            headers={"X-API-KEY": KINOPOISK_API_KEY},
            params={
                "type": "tv-series",
                "year": "1998-2025",
                "limit": 10,
                "page": page,
                "sortField": "votes.kp",
                "sortType": "-1",
                "selectFields": ["id", "name", "year", "rating", "description", "poster", "shortDescription", "type",
                                 "seasonsInfo"]
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            series_list = data.get('docs', [])

            if series_list:
                # Берем случайный сериал из найденных
                random_series = random.choice(series_list)
                if (is_modern_content(random_series) and has_poster_and_description(random_series)):
                    return random_series

    except Exception as e:
        logger.error(f"Method 2 error: {e}")

    return None


async def _random_series_method3():
    """Метод 3: Поиск по случайному году"""
    max_attempts = 8

    for attempt in range(max_attempts):
        try:
            # Случайный год в диапазоне
            start_year = random.randint(1998, 2020)
            end_year = random.randint(start_year + 1, 2025)
            year_range = f"{start_year}-{end_year}"

            params = {
                "type": "tv-series",
                "year": year_range,
                "rating.kp": "5-10",
                "votes.kp": "1000-10000000"
            }

            response = requests.get(
                "https://api.kinopoisk.dev/v1.4/movie/random",
                headers={"X-API-KEY": KINOPOISK_API_KEY},
                params=params,
                timeout=8
            )

            if response.status_code == 200:
                series = response.json()
                if (is_modern_content(series) and has_poster_and_description(series)):
                    return series

        except Exception as e:
            continue

    return None


async def _random_series_method4():
    """Метод 4: Поиск с минимальными требованиями (только постер)"""
    max_attempts = 15

    for attempt in range(max_attempts):
        try:
            params = {
                "type": "tv-series",
                "year": "1998-2025",
            }

            # Добавляем случайные параметры
            if random.random() > 0.5:
                params["rating.kp"] = "4-10"
            if random.random() > 0.5:
                params["page"] = random.randint(1, 15)

            response = requests.get(
                "https://api.kinopoisk.dev/v1.4/movie/random",
                headers={"X-API-KEY": KINOPOISK_API_KEY},
                params=params,
                timeout=8
            )

            if response.status_code == 200:
                series = response.json()

                # Минимальные требования: только постер и современность
                poster = series.get('poster', {})
                poster_url = poster.get('url') if isinstance(poster, dict) else None

                if (is_modern_content(series) and
                        poster_url and poster_url.startswith('http')):
                    return series

        except Exception as e:
            continue

    return None


async def send_content(update, content, user_id, is_series=False):
    """Отправляет фильм/сериал с постером и описанием"""
    title = content.get('name', 'Неизвестно')
    year = content.get('year', 'Неизвестно')
    rating = content.get('rating', {}).get('kp', 'Нет рейтинга')
    content_type = get_content_type(content)

    description = content.get('description', '')
    if not description or description == 'None':
        description = content.get('shortDescription', 'Описание отсутствует')

    poster_url = content.get('poster', {}).get('url')

    # Для сериалов добавляем информацию о сезонах
    seasons_info = ""
    if is_series and content.get('seasonsInfo'):
        seasons = content.get('seasonsInfo', [])
        if seasons:
            total_seasons = len(seasons)
            total_episodes = sum(season.get('episodesCount', 0) for season in seasons)
            seasons_info = f"\n📺 <b>Сезонов:</b> {total_seasons}, <b>Эпизодов:</b> {total_episodes}"

    message = f"<b>🎬 {title}</b> ({year})\n"
    message += f"🎭 <b>Тип:</b> {content_type}\n"
    message += f"⭐ <b>Рейтинг:</b> {rating}\n"
    if seasons_info:
        message += seasons_info
    message += f"📖 <b>Описание:</b> {description}\n"
    message += f"🆔 <code>ID: {content.get('id', 'Неизвестно')}</code>"

    keyboard = get_movie_actions_keyboard(content['id'], user_id, is_series)

    if poster_url and poster_url.startswith('http'):
        await update.message.reply_photo(
            photo=poster_url,
            caption=message,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode='HTML'
        )


async def random_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Случайный фильм ТОЛЬКО с 1998 года с постером и описанием"""
    try:
        await update.message.reply_text("🎲 Ищу современный фильм (с 1998 года) с постером и описанием...")

        movie = await get_quality_random_movie()

        if movie:
            await send_content(update, movie, update.effective_user.id, is_series=False)
            await update.message.reply_text(
                "✅ Найден современный качественный фильм!",
                reply_markup=get_back_keyboard()
            )
        else:
            await update.message.reply_text(
                "😔 Не удалось найти современный фильм с постером и описанием",
                reply_markup=get_back_keyboard()
            )

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(
            "❌ Ошибка при поиске фильма",
            reply_markup=get_back_keyboard()
        )


async def random_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Случайный сериал ТОЛЬКО с 1998 года с постером и описанием"""
    try:
        await update.message.reply_text("📺 Ищу случайный сериал (с 1998 года)...")

        series = await get_truly_random_series()

        if series:
            await send_content(update, series, update.effective_user.id, is_series=True)
            await update.message.reply_text(
                "✅ Найден случайный сериал!",
                reply_markup=get_back_keyboard()
            )
        else:
            await update.message.reply_text(
                "😔 Не удалось найти сериал",
                reply_markup=get_back_keyboard()
            )

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(
            "❌ Ошибка при поиске сериала",
            reply_markup=get_back_keyboard()
        )


async def search_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск фильмов"""
    if not context.args:
        await update.message.reply_text("❌ Введите название фильма:", reply_markup=get_back_keyboard())
        return

    query = " ".join(context.args)

    try:
        await update.message.reply_text("🔍 Ищу фильмы...", reply_markup=get_back_keyboard())

        response = requests.get(
            "https://api.kinopoisk.dev/v1.4/movie/search",
            headers={"X-API-KEY": KINOPOISK_API_KEY},
            params={"page": 1, "limit": 5, "query": query, "type": "movie"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()

            if data.get('total', 0) == 0:
                await update.message.reply_text("😔 Фильмы не найдены.", reply_markup=get_back_keyboard())
                return

            movies = data['docs']
            found_count = 0

            for movie in movies:
                if movie.get('id') and movie.get('name'):
                    await send_content(update, movie, update.effective_user.id, is_series=False)
                    found_count += 1

            if found_count > 0:
                await update.message.reply_text(f"✅ Найдено фильмов: {found_count}", reply_markup=get_back_keyboard())
            else:
                await update.message.reply_text("😔 Не удалось загрузить фильмы", reply_markup=get_back_keyboard())

        else:
            await update.message.reply_text("❌ Ошибка при поиске.", reply_markup=get_back_keyboard())

    except Exception as e:
        await update.message.reply_text("❌ Ошибка при поиске.", reply_markup=get_back_keyboard())


async def search_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск сериалов"""
    if not context.args:
        await update.message.reply_text("❌ Введите название сериала:", reply_markup=get_back_keyboard())
        return

    query = " ".join(context.args)

    try:
        await update.message.reply_text("🔍 Ищу сериалы...", reply_markup=get_back_keyboard())

        response = requests.get(
            "https://api.kinopoisk.dev/v1.4/movie/search",
            headers={"X-API-KEY": KINOPOISK_API_KEY},
            params={"page": 1, "limit": 5, "query": query, "type": "tv-series"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()

            if data.get('total', 0) == 0:
                await update.message.reply_text("😔 Сериалы не найдены.", reply_markup=get_back_keyboard())
                return

            series_list = data['docs']
            found_count = 0

            for series in series_list:
                if series.get('id') and series.get('name'):
                    await send_content(update, series, update.effective_user.id, is_series=True)
                    found_count += 1

            if found_count > 0:
                await update.message.reply_text(f"✅ Найдено сериалов: {found_count}", reply_markup=get_back_keyboard())
            else:
                await update.message.reply_text("😔 Не удалось загрузить сериалы", reply_markup=get_back_keyboard())

        else:
            await update.message.reply_text("❌ Ошибка при поиске.", reply_markup=get_back_keyboard())

    except Exception as e:
        await update.message.reply_text("❌ Ошибка при поиске.", reply_markup=get_back_keyboard())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = """
🎬 Добро пожаловать в КиноБот!

🎬 Поиск фильмов - найти фильмы по названию
📺 Поиск сериалов - найти сериалы по названию
⭐ Избранное - ваши любимые фильмы и сериалы  
🎯 Хочу посмотреть - фильмы и сериалы для просмотра
🎲 Случайный фильм - современные фильмы (с 1998 года)
📺 Случайный сериал - современные сериалы (с 1998 года)
"""
    await update.message.reply_text(message, reply_markup=get_main_keyboard())


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🎬 Поиск фильмов":
        await update.message.reply_text(
            "🎬 Введите название фильма для поиска:",
            reply_markup=get_back_keyboard()
        )
        context.user_data['waiting_for_movie_search'] = True

    elif text == "📺 Поиск сериалов":
        await update.message.reply_text(
            "📺 Введите название сериала для поиска:",
            reply_markup=get_back_keyboard()
        )
        context.user_data['waiting_for_series_search'] = True

    elif text == "⭐ Избранное":
        await show_favorites(update, context)

    elif text == "🎯 Хочу посмотреть":
        await show_watchlist(update, context)

    elif text == "🎲 Случайный фильм":
        await random_movie(update, context)

    elif text == "📺 Случайный сериал":
        await random_series(update, context)

    elif text == "⬅️ Назад в меню":
        await update.message.reply_text("🏠 Главное меню:", reply_markup=get_main_keyboard())


async def handle_list_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик управления списками"""
    text = update.message.text
    user_id = update.effective_user.id

    if text == "🗑 Очистить избранное":
        data = load_data(FAVORITES_FILE)
        if str(user_id) in data and data[str(user_id)]:
            data[str(user_id)] = []
            save_data(FAVORITES_FILE, data)
            await update.message.reply_text("✅ Избранное очищено!", reply_markup=get_back_keyboard())
        else:
            await update.message.reply_text("📭 В избранном и так пусто!", reply_markup=get_back_keyboard())

    elif text == "🗑 Очистить желаемое":
        data = load_data(WATCHLIST_FILE)
        if str(user_id) in data and data[str(user_id)]:
            data[str(user_id)] = []
            save_data(WATCHLIST_FILE, data)
            await update.message.reply_text("✅ Список желаемого очищен!", reply_markup=get_back_keyboard())
        else:
            await update.message.reply_text("📭 В списке желаемого и так пусто!", reply_markup=get_back_keyboard())


async def handle_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода поискового запроса"""
    if context.user_data.get('waiting_for_movie_search'):
        context.args = update.message.text.split()
        await search_movies(update, context)
        context.user_data['waiting_for_movie_search'] = False
    elif context.user_data.get('waiting_for_series_search'):
        context.args = update.message.text.split()
        await search_series(update, context)
        context.user_data['waiting_for_series_search'] = False
    else:
        # Если просто написали текст, ищем фильмы
        context.args = update.message.text.split()
        await search_movies(update, context)


async def show_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    favorites = get_user_list(user_id, "favorites")

    if not favorites:
        await update.message.reply_text("📭 Нет избранных фильмов и сериалов.", reply_markup=get_back_keyboard())
        return

    await update.message.reply_text(
        f"⭐ Избранные фильмы и сериалы ({len(favorites)}):",
        reply_markup=get_list_management_keyboard("favorites")
    )

    for content_data in favorites:
        try:
            content_id = content_data.get('id')
            if content_id:
                response = requests.get(
                    f"https://api.kinopoisk.dev/v1.4/movie/{content_id}",
                    headers={"X-API-KEY": KINOPOISK_API_KEY},
                    timeout=10
                )

                if response.status_code == 200:
                    content = response.json()
                    is_series = content.get('type') == 'tv-series'
                    await send_content(update, content, user_id, is_series)

        except Exception as e:
            content_type = "сериал" if content_data.get('type') == 'tv-series' else "фильм"
            message = f"<b>🎬 {content_data.get('name', 'Неизвестно')}</b> ({content_data.get('year', 'Неизвестно')}) - {content_type}"
            await update.message.reply_text(message, parse_mode='HTML')


async def show_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    watchlist = get_user_list(user_id, "watchlist")

    if not watchlist:
        await update.message.reply_text("📭 Нет фильмов и сериалов в списке.", reply_markup=get_back_keyboard())
        return

    await update.message.reply_text(
        f"🎯 Хочу посмотреть ({len(watchlist)}):",
        reply_markup=get_list_management_keyboard("watchlist")
    )

    for content_data in watchlist:
        try:
            content_id = content_data.get('id')
            if content_id:
                response = requests.get(
                    f"https://api.kinopoisk.dev/v1.4/movie/{content_id}",
                    headers={"X-API-KEY": KINOPOISK_API_KEY},
                    timeout=10
                )

                if response.status_code == 200:
                    content = response.json()
                    is_series = content.get('type') == 'tv-series'
                    await send_content(update, content, user_id, is_series)

        except Exception as e:
            content_type = "сериал" if content_data.get('type') == 'tv-series' else "фильм"
            message = f"<b>🎬 {content_data.get('name', 'Неизвестно')}</b> ({content_data.get('year', 'Неизвестно')}) - {content_type}"
            await update.message.reply_text(message, parse_mode='HTML')


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    parts = data.split('_')
    action = parts[0] + '_' + parts[1]  # Объединяем первые две части
    movie_id = parts[2]

    try:
        # Получаем информацию о фильме/сериале для обновления сообщения
        response = requests.get(
            f"https://api.kinopoisk.dev/v1.4/movie/{movie_id}",
            headers={"X-API-KEY": KINOPOISK_API_KEY},
            timeout=10
        )

        if response.status_code != 200:
            await query.edit_message_text("❌ Ошибка.")
            return

        content = response.json()

        content_data = {
            'id': content['id'],
            'name': content.get('name', 'Неизвестно'),
            'year': content.get('year', 'Неизвестно'),
            'rating': content.get('rating', {}).get('kp', 'Нет рейтинга'),
            'type': content.get('type', 'movie')
        }

        success_msg = ""

        if action == "add_fav":
            if add_to_list(user_id, content_data, "favorites"):
                success_msg = "\n\n✅ Добавлено в избранное"
            else:
                success_msg = "\n\n⚠️ Уже в избранном"

        elif action == "add_watch":
            if add_to_list(user_id, content_data, "watchlist"):
                success_msg = "\n\n✅ Добавлено в желаемое"
            else:
                success_msg = "\n\n⚠️ Уже в желаемом"

        elif action == "remove_fav":
            if remove_from_list(user_id, movie_id, "favorites"):
                success_msg = "\n\n❌ Удалено из избранного"
            else:
                success_msg = "\n\n⚠️ Не было в избранном"

        elif action == "remove_watch":
            if remove_from_list(user_id, movie_id, "watchlist"):
                success_msg = "\n\n❌ Удалено из желаемого"
            else:
                success_msg = "\n\n⚠️ Не было в желаемом"

        # Обновляем сообщение с новыми кнопками
        is_series = content.get('type') == 'tv-series'
        new_keyboard = get_movie_actions_keyboard(movie_id, user_id, is_series)

        if query.message.caption:
            new_caption = query.message.caption + success_msg
            await query.edit_message_caption(
                caption=new_caption,
                reply_markup=new_keyboard,
                parse_mode='HTML'
            )
        else:
            new_text = query.message.text + success_msg
            await query.edit_message_text(
                new_text,
                reply_markup=new_keyboard,
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Button handler error: {e}")
        await query.edit_message_text("❌ Ошибка.")


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    application.add_handler(MessageHandler(filters.Text([
        "🎬 Поиск фильмов", "📺 Поиск сериалов", "⭐ Избранное", "🎯 Хочу посмотреть",
        "🎲 Случайный фильм", "📺 Случайный сериал", "⬅️ Назад в меню"
    ]), handle_main_menu))

    # Обработчик для управления списками
    application.add_handler(MessageHandler(filters.Text([
        "🗑 Очистить избранное", "🗑 Очистить желаемое"
    ]), handle_list_management))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_input))
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Бот запущен...")
    application.run_polling()


if __name__ == '__main__':
    main()