import logging
import json
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, \
    InputMediaPhoto
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import requests

# Конфигурация
KINOPOISK_API_KEY = "WE5F7TA-CBS4MEF-MBENDVR-Z31P1H5"
BOT_TOKEN = "7981463799:AAHxvci7hCtrq_Zm1pfpYHNmJFgrIrVe9r8"

# Файлы для хранения данных
FAVORITES_FILE = "favorites.json"
WATCHLIST_FILE = "watchlist.json"
COLLECTIONS_FILE = "collections.json"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def load_data(filename):
    """Загружает данные из файла с обработкой ошибок"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        return {}
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Error loading {filename}: {e}")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        return {}


def save_data(filename, data):
    """Сохраняет данные в файл"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving {filename}: {e}")


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


# Функции для работы с коллекциями
def create_collection(user_id, collection_name):
    """Создает новую коллекцию"""
    data = load_data(COLLECTIONS_FILE)

    if str(user_id) not in data:
        data[str(user_id)] = {}

    # Создаем уникальный ID для коллекции
    collection_id = str(len(data[str(user_id)]) + 1)
    data[str(user_id)][collection_id] = {
        'name': collection_name,
        'movies': []
    }

    save_data(COLLECTIONS_FILE, data)
    return collection_id


def get_user_collections(user_id):
    """Получает все коллекции пользователя"""
    data = load_data(COLLECTIONS_FILE)
    return data.get(str(user_id), {})


def add_to_collection(user_id, collection_id, movie_data):
    """Добавляет фильм в коллекцию"""
    data = load_data(COLLECTIONS_FILE)

    if str(user_id) in data and collection_id in data[str(user_id)]:
        # Проверяем, нет ли уже этого фильма в коллекции
        for movie in data[str(user_id)][collection_id]['movies']:
            if movie.get('id') == movie_data.get('id'):
                return False

        data[str(user_id)][collection_id]['movies'].append(movie_data)
        save_data(COLLECTIONS_FILE, data)
        return True

    return False


def remove_from_collection(user_id, collection_id, movie_id):
    """Удаляет фильм из коллекции"""
    data = load_data(COLLECTIONS_FILE)

    if str(user_id) in data and collection_id in data[str(user_id)]:
        initial_length = len(data[str(user_id)][collection_id]['movies'])
        data[str(user_id)][collection_id]['movies'] = [
            movie for movie in data[str(user_id)][collection_id]['movies']
            if str(movie.get('id')) != str(movie_id)
        ]

        if len(data[str(user_id)][collection_id]['movies']) < initial_length:
            save_data(COLLECTIONS_FILE, data)
            return True

    return False


def get_main_keyboard():
    keyboard = [
        [KeyboardButton("🎬 Поиск фильмов и сериалов")],
        [KeyboardButton("🔍 Поиск по актерам"), KeyboardButton("🎭 Фильтр по жанру/году")],
        [KeyboardButton("⭐ Избранное"), KeyboardButton("🎯 Хочу посмотреть")],
        [KeyboardButton("📚 Мои подборки"), KeyboardButton("🎲 Случайный фильм")],
        [KeyboardButton("📺 Случайный сериал")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_back_keyboard():
    keyboard = [
        [KeyboardButton("⬅️ Назад в меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_collections_keyboard(user_id=None):
    """Клавиатура для управления подборками"""
    if user_id:
        collections = get_user_collections(user_id)
        keyboard = []

        for collection_id, collection_data in collections.items():
            movie_count = len(collection_data['movies'])
            keyboard.append([KeyboardButton(f"📁 {collection_data['name']} ({movie_count})")])

        keyboard.append([KeyboardButton("➕ Создать подборку")])
        keyboard.append([KeyboardButton("⬅️ Назад в меню")])
    else:
        keyboard = [
            [KeyboardButton("➕ Создать подборку")],
            [KeyboardButton("📋 Мои подборки")],
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

    # Кнопка для добавления в подборку
    keyboard.append([InlineKeyboardButton("📚 Добавить в подборку", callback_data=f"add_to_collection_{movie_id}")])

    return InlineKeyboardMarkup(keyboard)


def get_collections_choice_keyboard(user_id, movie_id):
    """Создает клавиатуру с выбором подборок для добавления фильма"""
    collections = get_user_collections(user_id)
    keyboard = []

    for collection_id, collection_data in collections.items():
        keyboard.append([
            InlineKeyboardButton(
                f"📁 {collection_data['name']}",
                callback_data=f"add_collection_{collection_id}_{movie_id}"
            )
        ])

    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_collection")])
    return InlineKeyboardMarkup(keyboard)


def get_collection_movies_keyboard(collection_id, current_index, total_items, current_movie_id=None):
    """Создает клавиатуру для навигации по фильмам в подборке"""
    keyboard = []

    # Кнопки навигации
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"nav_collection_{collection_id}_{current_index - 1}"))

    nav_buttons.append(InlineKeyboardButton(f"{current_index + 1}/{total_items}", callback_data="page_info"))

    if current_index < total_items - 1:
        nav_buttons.append(
            InlineKeyboardButton("Дальше ➡️", callback_data=f"nav_collection_{collection_id}_{current_index + 1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Кнопка удаления из подборки
    if current_movie_id:
        keyboard.append([InlineKeyboardButton("❌ Удалить из подборки",
                                              callback_data=f"remove_from_collection_{collection_id}_{current_movie_id}")])

    return InlineKeyboardMarkup(keyboard)


def get_list_navigation_keyboard(current_index, total_items, list_type, current_movie_id=None):
    """Создает клавиатуру для навигации по списку"""
    keyboard = []

    # Кнопки навигации
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"nav_{list_type}_{current_index - 1}"))

    nav_buttons.append(InlineKeyboardButton(f"{current_index + 1}/{total_items}", callback_data="page_info"))

    if current_index < total_items - 1:
        nav_buttons.append(InlineKeyboardButton("Дальше ➡️", callback_data=f"nav_{list_type}_{current_index + 1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Кнопки управления для текущего фильма
    if current_movie_id:
        keyboard.append(
            [InlineKeyboardButton("❌ Удалить из списка", callback_data=f"remove_from_{list_type}_{current_movie_id}")])

    return InlineKeyboardMarkup(keyboard)


def get_search_navigation_keyboard(current_index, total_items, current_movie_id, user_id, is_series=False,
                                   search_type="search"):
    """Создает клавиатуру для навигации по результатам поиска"""
    keyboard = []

    # Кнопки навигации
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"nav_{search_type}_{current_index - 1}"))

    nav_buttons.append(InlineKeyboardButton(f"{current_index + 1}/{total_items}", callback_data="page_info"))

    if current_index < total_items - 1:
        nav_buttons.append(InlineKeyboardButton("Дальше ➡️", callback_data=f"nav_{search_type}_{current_index + 1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Кнопки действий для фильма/сериала
    action_buttons = []
    in_favorites = is_movie_in_list(user_id, current_movie_id, "favorites")
    in_watchlist = is_movie_in_list(user_id, current_movie_id, "watchlist")

    if in_favorites:
        action_buttons.append(
            InlineKeyboardButton("❌ Удалить из избранного", callback_data=f"remove_fav_{current_movie_id}"))
    else:
        action_buttons.append(InlineKeyboardButton("⭐ В избранное", callback_data=f"add_fav_{current_movie_id}"))

    if in_watchlist:
        action_buttons.append(
            InlineKeyboardButton("❌ Удалить из желаемого", callback_data=f"remove_watch_{current_movie_id}"))
    else:
        action_buttons.append(InlineKeyboardButton("🎯 Хочу посмотреть", callback_data=f"add_watch_{current_movie_id}"))

    action_buttons.append(
        InlineKeyboardButton("📚 Добавить в подборку", callback_data=f"add_to_collection_{current_movie_id}"))

    keyboard.append(action_buttons)

    return InlineKeyboardMarkup(keyboard)


def get_random_navigation_keyboard(current_index, total_items, current_movie_id, user_id, is_series=False,
                                   content_type="movie"):
    """Создает клавиатуру для навигации по случайным фильмам/сериалам"""
    keyboard = []

    # Кнопки навигации
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"nav_random_{content_type}_{current_index - 1}"))

    nav_buttons.append(InlineKeyboardButton(f"{current_index + 1}/{total_items}", callback_data="page_info"))

    if current_index < total_items - 1:
        nav_buttons.append(
            InlineKeyboardButton("Дальше ➡️", callback_data=f"nav_random_{content_type}_{current_index + 1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Кнопки действий для фильма/сериала
    action_buttons = []
    in_favorites = is_movie_in_list(user_id, current_movie_id, "favorites")
    in_watchlist = is_movie_in_list(user_id, current_movie_id, "watchlist")

    if in_favorites:
        action_buttons.append(
            InlineKeyboardButton("❌ Удалить из избранного", callback_data=f"remove_fav_{current_movie_id}"))
    else:
        action_buttons.append(InlineKeyboardButton("⭐ В избранное", callback_data=f"add_fav_{current_movie_id}"))

    if in_watchlist:
        action_buttons.append(
            InlineKeyboardButton("❌ Удалить из желаемого", callback_data=f"remove_watch_{current_movie_id}"))
    else:
        action_buttons.append(InlineKeyboardButton("🎯 Хочу посмотреть", callback_data=f"add_watch_{current_movie_id}"))

    action_buttons.append(
        InlineKeyboardButton("📚 Добавить в подборку", callback_data=f"add_to_collection_{current_movie_id}"))

    keyboard.append(action_buttons)

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
    if not content:
        return False

    poster = content.get('poster', {})
    if not poster or not isinstance(poster, dict):
        return False
    poster_url = poster.get('url')
    if not poster_url or not poster_url.startswith('http'):
        return False

    description = content.get('description', '')
    if not description or description == 'None':
        description = content.get('shortDescription', '')
        if not description or description == 'None':
            return False

    return True


def is_modern_content(content):
    """Проверяет, что фильм/сериал выпущен с 1998 года"""
    if not content:
        return False

    year = content.get('year')
    if not year:
        return False
    try:
        return int(year) >= 1998
    except (ValueError, TypeError):
        return False


def get_content_type(content):
    """Определяет тип контента (фильм или сериал)"""
    if not content:
        return 'контент'

    type_str = content.get('type', '')
    if type_str == 'tv-series':
        return 'сериал'
    elif type_str == 'movie':
        return 'фильм'
    else:
        return 'контент'


def get_genres(content):
    """Получает список жанров"""
    if not content:
        return "Неизвестно"

    genres = content.get('genres', [])
    if not genres:
        return "Неизвестно"

    genre_names = [genre.get('name', '') for genre in genres if genre.get('name')]
    return ", ".join(genre_names) if genre_names else "Неизвестно"


async def get_quality_random_movie():
    """Ищет случайный фильм ТОЛЬКО с 1998 года с постером и описанием"""
    max_attempts = 10

    for attempt in range(max_attempts):
        try:
            logger.info(f"Attempt {attempt + 1}: Searching for random movie...")

            response = requests.get(
                "https://api.kinopoisk.dev/v1.4/movie/random",
                headers={"X-API-KEY": KINOPOISK_API_KEY},
                params={
                    "type": "movie",
                    "year": "1998-2024",
                    "rating.kp": "5-10",
                    "votes.kp": "1000-10000000"
                },
                timeout=15
            )

            if response.status_code == 200:
                movie = response.json()
                logger.info(f"Found movie: {movie.get('name')} ({movie.get('year')})")

                if movie and is_modern_content(movie) and has_poster_and_description(movie):
                    logger.info(f"Quality movie found: {movie.get('name')}")
                    return movie

        except Exception as e:
            logger.error(f"Attempt {attempt + 1} error: {e}")
            continue

    return None


async def get_truly_random_series():
    """Находит СЛУЧАЙНЫЙ сериал"""
    max_attempts = 10

    for attempt in range(max_attempts):
        try:
            logger.info(f"Attempt {attempt + 1}: Searching for random series...")

            response = requests.get(
                "https://api.kinopoisk.dev/v1.4/movie/random",
                headers={"X-API-KEY": KINOPOISK_API_KEY},
                params={
                    "type": "tv-series",
                    "year": "1998-2024",
                    "rating.kp": "5-10",
                    "votes.kp": "1000-10000000"
                },
                timeout=15
            )

            if response.status_code == 200:
                series = response.json()
                logger.info(f"Found series: {series.get('name')} ({series.get('year')})")

                if series and is_modern_content(series) and has_poster_and_description(series):
                    logger.info(f"Quality series found: {series.get('name')}")
                    return series

        except Exception as e:
            logger.error(f"Attempt {attempt + 1} error: {e}")
            continue

    return None


async def send_content(update, content, user_id, is_series=False, navigation_data=None, search_type="search"):
    """Отправляет фильм/сериал с постером и описанием"""
    if not content:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text("❌ Ошибка: контент не найден",
                                                          reply_markup=get_back_keyboard())
        else:
            await update.message.reply_text("❌ Ошибка: контент не найден", reply_markup=get_back_keyboard())
        return

    title = content.get('name', 'Неизвестно')
    year = content.get('year', 'Неизвестно')
    rating = content.get('rating', {}).get('kp', 'Нет рейтинга')
    content_type_str = get_content_type(content)
    genres = get_genres(content)

    description = content.get('description', '')
    if not description or description == 'None':
        description = content.get('shortDescription', 'Описание отсутствует')

    # Ограничиваем длину описания для Telegram
    if len(description) > 800:
        description = description[:800] + "..."

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
    message += f"🎭 <b>Тип:</b> {content_type_str}\n"
    message += f"🏷️ <b>Жанр:</b> {genres}\n"
    message += f"⭐ <b>Рейтинг:</b> {rating}\n"
    if seasons_info:
        message += seasons_info
    message += f"📖 <b>Описание:</b> {description}\n"
    message += f"🆔 <code>ID: {content.get('id', 'Неизвестно')}</code>"

    if navigation_data:
        # Если есть данные для навигации, используем навигационную клавиатуру
        current_index, total_items, nav_type, extra_data = navigation_data

        if nav_type == "random":
            keyboard = get_random_navigation_keyboard(current_index, total_items, content['id'], user_id, is_series,
                                                      search_type)
        elif nav_type in ["favorites", "watchlist"]:
            keyboard = get_list_navigation_keyboard(current_index, total_items, nav_type, content['id'])
        elif nav_type == "collection":
            keyboard = get_collection_movies_keyboard(extra_data, current_index, total_items, content['id'])
        else:
            keyboard = get_search_navigation_keyboard(current_index, total_items, content['id'], user_id, is_series,
                                                      search_type)
    else:
        # Иначе обычную клавиатуру действий
        keyboard = get_movie_actions_keyboard(content['id'], user_id, is_series)

    # Определяем тип update
    if hasattr(update, 'callback_query') and update.callback_query:
        # Это callback query (навигация по спискам)
        if poster_url and poster_url.startswith('http'):
            try:
                await update.callback_query.edit_message_media(
                    media=InputMediaPhoto(media=poster_url, caption=message, parse_mode='HTML'),
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Error editing media: {e}")
                # Если не удалось изменить медиа, просто меняем текст
                await update.callback_query.edit_message_text(
                    message,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
        else:
            await update.callback_query.edit_message_text(
                message,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    else:
        # Это обычное сообщение
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
    """Случайный фильм с навигацией"""
    try:
        # Проверяем тип update
        if hasattr(update, 'callback_query') and update.callback_query:
            # Если это callback, редактируем сообщение
            await update.callback_query.edit_message_text(
                "🎲 Ищу современный фильм (с 1998 года) с постером и описанием...")
        else:
            # Если это обычное сообщение
            await update.message.reply_text("🎲 Ищу современный фильм (с 1998 года) с постером и описанием...")

        # Генерируем несколько случайных фильмов
        random_movies = []
        for i in range(5):  # Генерируем 5 фильмов для навигации
            movie = await get_quality_random_movie()
            if movie and movie not in random_movies:
                random_movies.append(movie)

        if not random_movies:
            error_msg = "😔 Не удалось найти современные фильмы с постером и описанием."
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(error_msg, reply_markup=get_back_keyboard())
            else:
                await update.message.reply_text(error_msg, reply_markup=get_back_keyboard())
            return

        # Сохраняем в context для навигации
        context.user_data['random_movies'] = random_movies
        context.user_data['random_movie_index'] = 0
        context.user_data['current_search_type'] = 'random_movie'

        # Показываем первый фильм с навигацией
        await show_random_movie(update, context, 0)

    except Exception as e:
        logger.error(f"Error in random_movie: {e}")
        error_msg = "❌ Ошибка при поиске фильма"
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(error_msg, reply_markup=get_back_keyboard())
        else:
            await update.message.reply_text(error_msg, reply_markup=get_back_keyboard())


async def show_random_movie(update: Update, context: ContextTypes.DEFAULT_TYPE, index=0):
    """Показывает случайный фильм с навигацией"""
    random_movies = context.user_data.get('random_movies', [])

    if not random_movies or index >= len(random_movies):
        message_text = "❌ Ошибка отображения"
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message_text, reply_markup=get_back_keyboard())
        else:
            await update.message.reply_text(message_text, reply_markup=get_back_keyboard())
        return

    movie = random_movies[index]
    context.user_data['random_movie_index'] = index

    # Отправляем с навигацией
    navigation_data = (index, len(random_movies), "random", None)
    await send_content(update, movie, update.effective_user.id, is_series=False,
                       navigation_data=navigation_data, search_type="movie")


async def random_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Случайный сериал с навигацией"""
    try:
        # Проверяем тип update
        if hasattr(update, 'callback_query') and update.callback_query:
            # Если это callback, редактируем сообщение
            await update.callback_query.edit_message_text("📺 Ищу случайный сериал (с 1998 года)...")
        else:
            # Если это обычное сообщение
            await update.message.reply_text("📺 Ищу случайный сериал (с 1998 года)...")

        # Генерируем несколько случайных сериалов
        random_series_list = []
        for i in range(5):  # Генерируем 5 сериалов для навигации
            series = await get_truly_random_series()
            if series and series not in random_series_list:
                random_series_list.append(series)

        if not random_series_list:
            error_msg = "😔 Не удалось найти сериалы."
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(error_msg, reply_markup=get_back_keyboard())
            else:
                await update.message.reply_text(error_msg, reply_markup=get_back_keyboard())
            return

        # Сохраняем в context для навигации
        context.user_data['random_series'] = random_series_list
        context.user_data['random_series_index'] = 0
        context.user_data['current_search_type'] = 'random_series'

        # Показываем первый сериал с навигацией
        await show_random_series(update, context, 0)

    except Exception as e:
        logger.error(f"Error in random_series: {e}")
        error_msg = "❌ Ошибка при поиске сериала"
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(error_msg, reply_markup=get_back_keyboard())
        else:
            await update.message.reply_text(error_msg, reply_markup=get_back_keyboard())


async def show_random_series(update: Update, context: ContextTypes.DEFAULT_TYPE, index=0):
    """Показывает случайный сериал с навигацией"""
    random_series_list = context.user_data.get('random_series', [])

    if not random_series_list or index >= len(random_series_list):
        message_text = "❌ Ошибка отображения"
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message_text, reply_markup=get_back_keyboard())
        else:
            await update.message.reply_text(message_text, reply_markup=get_back_keyboard())
        return

    series = random_series_list[index]
    context.user_data['random_series_index'] = index

    # Отправляем с навигацией
    navigation_data = (index, len(random_series_list), "random", None)
    await send_content(update, series, update.effective_user.id, is_series=True,
                       navigation_data=navigation_data, search_type="series")


async def search_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск фильмов и сериалов с навигацией по результатам"""
    if not context.args:
        await update.message.reply_text("❌ Введите название фильма или сериала:", reply_markup=get_back_keyboard())
        return

    query = " ".join(context.args).lower().strip()

    if len(query) < 2:
        await update.message.reply_text("❌ Слишком короткий запрос. Введите минимум 2 символа.",
                                        reply_markup=get_back_keyboard())
        return

    try:
        await update.message.reply_text("🔍 Ищу фильмы и сериалы...", reply_markup=get_back_keyboard())

        response = requests.get(
            "https://api.kinopoisk.dev/v1.4/movie/search",
            headers={"X-API-KEY": KINOPOISK_API_KEY},
            params={"page": 1, "limit": 50, "query": query},
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()

            if data.get('total', 0) == 0 or not data.get('docs'):
                await update.message.reply_text("😔 Ничего не найдено.", reply_markup=get_back_keyboard())
                return

            content_list = data['docs']

            # Фильтруем результаты - только точные совпадения
            matching_content = []

            for content in content_list:
                if content.get('id') and content.get('name'):
                    content_title = content.get('name', '').lower().strip()

                    # Только точные совпадения или содержащие запрос
                    if content_title == query or query in content_title:
                        matching_content.append(content)

            # Ограничиваем максимум 5 результатами
            matching_content = matching_content[:5]

            if not matching_content:
                await update.message.reply_text(
                    f"😔 Не найдено фильмов/сериалов с точным названием '{query}'. Попробуйте изменить запрос.",
                    reply_markup=get_back_keyboard()
                )
                return

            # Сохраняем результаты поиска в user_data для навигации
            context.user_data['search_results'] = matching_content
            context.user_data['search_index'] = 0
            context.user_data['current_search_type'] = 'search'

            # Показываем первый результат с навигацией
            await show_search_result(update, context, 0)

        else:
            logger.error(f"Search API error: {response.status_code}")
            await update.message.reply_text("❌ Ошибка при поиске. Попробуйте позже.", reply_markup=get_back_keyboard())

    except Exception as e:
        logger.error(f"Error in search_content: {e}")
        await update.message.reply_text("❌ Ошибка при поиске.", reply_markup=get_back_keyboard())


async def show_search_result(update: Update, context: ContextTypes.DEFAULT_TYPE, index=0):
    """Показывает один результат поиска с навигацией"""
    user_id = update.effective_user.id
    search_results = context.user_data.get('search_results', [])

    if not search_results or index >= len(search_results):
        message_text = "❌ Ошибка отображения результатов"
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message_text, reply_markup=get_back_keyboard())
        else:
            await update.message.reply_text(message_text, reply_markup=get_back_keyboard())
        return

    content = search_results[index]
    context.user_data['search_index'] = index

    is_series = content.get('type') == 'tv-series'

    # Отправляем с навигацией
    navigation_data = (index, len(search_results), "search", None)
    await send_content(update, content, user_id, is_series, navigation_data, search_type="search")


async def search_by_actor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск фильмов по актеру"""
    if not context.args:
        await update.message.reply_text(
            "🎭 Введите имя актера для поиска:",
            reply_markup=get_back_keyboard()
        )
        context.user_data['waiting_for_actor'] = True
        return

    actor_name = " ".join(context.args)

    try:
        await update.message.reply_text(f"🔍 Ищу фильмы с участием {actor_name}...", reply_markup=get_back_keyboard())

        # Ищем фильмы по имени актера
        response = requests.get(
            "https://api.kinopoisk.dev/v1.4/movie",
            headers={"X-API-KEY": KINOPOISK_API_KEY},
            params={
                "page": 1,
                "limit": 50,
                "persons.name": actor_name,
                "year": "1998-2024",
                "rating.kp": "5-10",
                "selectFields": ["id", "name", "year", "rating", "poster", "description", "type", "persons", "genres"]
            },
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            movies_list = data.get('docs', [])

            if not movies_list:
                await update.message.reply_text(
                    f"😔 Не найдено фильмов с участием {actor_name}.",
                    reply_markup=get_back_keyboard()
                )
                return

            # Ограничиваем максимум 5 результатами
            movies_list = movies_list[:5]

            # Сохраняем результаты поиска
            context.user_data['actor_results'] = movies_list
            context.user_data['actor_index'] = 0
            context.user_data['current_search_type'] = 'actor'

            # Показываем первый результат
            await show_actor_result(update, context, 0)
        else:
            await update.message.reply_text("❌ Ошибка при поиске фильмов.", reply_markup=get_back_keyboard())

    except Exception as e:
        logger.error(f"Error in search_by_actor: {e}")
        await update.message.reply_text("❌ Ошибка при поиске.", reply_markup=get_back_keyboard())


async def show_actor_result(update: Update, context: ContextTypes.DEFAULT_TYPE, index=0):
    """Показывает результат поиска по актеру"""
    user_id = update.effective_user.id
    actor_results = context.user_data.get('actor_results', [])

    if not actor_results or index >= len(actor_results):
        message_text = "❌ Ошибка отображения результатов"
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message_text, reply_markup=get_back_keyboard())
        else:
            await update.message.reply_text(message_text, reply_markup=get_back_keyboard())
        return

    content = actor_results[index]
    context.user_data['actor_index'] = index

    is_series = content.get('type') == 'tv-series'

    # Отправляем с навигацией
    navigation_data = (index, len(actor_results), "search", None)
    await send_content(update, content, user_id, is_series, navigation_data, search_type="actor")


async def filter_by_genre_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Фильтр по жанру и году"""
    await update.message.reply_text(
        "🎭 Введите параметры поиска в формате:\n\n"
        "• <b>Жанр год</b> - например: <code>комедия 2010</code>\n"
        "• <b>Жанр год-год</b> - например: <code>фантастика 2010-2020</code>\n"
        "• <b>Жанр</b> - например: <code>драма</code>\n\n"
        "Доступные жанры: комедия, драма, боевик, фантастика, ужасы, триллер, мелодрама, детектив, приключения, аниме",
        reply_markup=get_back_keyboard(),
        parse_mode='HTML'
    )
    context.user_data['waiting_for_filter'] = True


async def handle_filter_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода фильтра"""
    if not context.user_data.get('waiting_for_filter'):
        return

    query = update.message.text.lower().strip()
    context.user_data['waiting_for_filter'] = False

    try:
        # Парсим запрос
        parts = query.split()
        if not parts:
            await update.message.reply_text("❌ Неверный формат запроса.", reply_markup=get_back_keyboard())
            return

        genre = parts[0]
        year_range = "1998-2024"  # По умолчанию с 1998 года

        if len(parts) > 1:
            year_param = parts[1]
            if '-' in year_param:
                # Диапазон годов
                start_year, end_year = year_param.split('-')
                try:
                    start_year = int(start_year)
                    end_year = int(end_year)
                    if start_year > end_year:
                        year_param = f"{end_year}-{start_year}"
                    year_range = year_param
                except:
                    year_range = "1998-2024"
            else:
                # Один год - ищем с этого года
                try:
                    year_int = int(year_param)
                    year_range = f"{year_int}-2024"
                except:
                    year_range = "1998-2024"

        # Маппинг жанров
        genre_mapping = {
            'комедия': 'комедия',
            'драма': 'драма',
            'боевик': 'боевик',
            'фантастика': 'фантастика',
            'ужасы': 'ужасы',
            'триллер': 'триллер',
            'мелодрама': 'мелодрама',
            'детектив': 'детектив',
            'приключения': 'приключения',
            'аниме': 'аниме'
        }

        if genre not in genre_mapping:
            await update.message.reply_text(
                "❌ Неизвестный жанр. Используйте один из доступных жанров.",
                reply_markup=get_back_keyboard()
            )
            return

        await update.message.reply_text(
            f"🔍 Ищу {genre} {year_range if year_range != '1998-2024' else 'с 1998 года'}...",
            reply_markup=get_back_keyboard()
        )

        # Получаем ВСЕ фильмы по жанру и году (увеличиваем лимит)
        all_content = []
        page = 1

        while True:
            response = requests.get(
                "https://api.kinopoisk.dev/v1.4/movie",
                headers={"X-API-KEY": KINOPOISK_API_KEY},
                params={
                    "page": page,
                    "limit": 250,  # Увеличиваем лимит для получения большего количества результатов
                    "genres.name": genre_mapping[genre],
                    "year": year_range,
                    "rating.kp": "5-10",
                    "votes.kp": "1000-10000000",
                    "selectFields": ["id", "name", "year", "rating", "poster", "description", "type", "genres"]
                },
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                page_content = data.get('docs', [])

                if not page_content:
                    break

                all_content.extend(page_content)
                page += 1

                # Ограничиваем общее количество для предотвращения перегрузки
                if len(all_content) >= 1000:
                    break
            else:
                break

        if not all_content:
            await update.message.reply_text(
                f"😔 Не найдено результатов по вашему запросу.",
                reply_markup=get_back_keyboard()
            )
            return

        # Сохраняем ВСЕ результаты
        context.user_data['filter_results'] = all_content
        context.user_data['filter_index'] = 0
        context.user_data['current_search_type'] = 'filter'

        # Показываем первый результат
        await show_filter_result(update, context, 0)

    except Exception as e:
        logger.error(f"Error in handle_filter_input: {e}")
        await update.message.reply_text("❌ Ошибка при обработке запроса.", reply_markup=get_back_keyboard())


async def show_filter_result(update: Update, context: ContextTypes.DEFAULT_TYPE, index=0):
    """Показывает результат фильтра"""
    user_id = update.effective_user.id
    filter_results = context.user_data.get('filter_results', [])

    if not filter_results or index >= len(filter_results):
        message_text = "❌ Ошибка отображения результатов"
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message_text, reply_markup=get_back_keyboard())
        else:
            await update.message.reply_text(message_text, reply_markup=get_back_keyboard())
        return

    content = filter_results[index]
    context.user_data['filter_index'] = index

    is_series = content.get('type') == 'tv-series'

    # Отправляем с навигацией
    navigation_data = (index, len(filter_results), "search", None)
    await send_content(update, content, user_id, is_series, navigation_data, search_type="filter")


# Функции для работы с подборками
async def show_collections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню подборок"""
    user_id = update.effective_user.id
    await update.message.reply_text(
        "📚 <b>Мои подборки</b>\n\n"
        "Здесь вы можете создавать свои собственные подборки фильмов и сериалов.",
        reply_markup=get_collections_keyboard(user_id),
        parse_mode='HTML'
    )


async def create_collection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик создания подборки"""
    await update.message.reply_text(
        "📝 Введите название для новой подборки:",
        reply_markup=get_back_keyboard()
    )
    context.user_data['waiting_for_collection_name'] = True


async def handle_collection_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода названия подборки"""
    if not context.user_data.get('waiting_for_collection_name'):
        return

    collection_name = update.message.text.strip()
    user_id = update.effective_user.id

    if not collection_name:
        await update.message.reply_text("❌ Название не может быть пустым.",
                                        reply_markup=get_collections_keyboard(user_id))
        return

    # Создаем подборку
    collection_id = create_collection(user_id, collection_name)

    await update.message.reply_text(
        f"✅ Подборка '<b>{collection_name}</b>' успешно создана!",
        reply_markup=get_collections_keyboard(user_id),
        parse_mode='HTML'
    )
    context.user_data['waiting_for_collection_name'] = False


async def show_user_collections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает подборки пользователя"""
    user_id = update.effective_user.id
    collections = get_user_collections(user_id)

    if not collections:
        await update.message.reply_text(
            "📭 У вас пока нет подборок.\n\nСоздайте первую подборку!",
            reply_markup=get_collections_keyboard(user_id)
        )
        return

    message = "📚 <b>Ваши подборки:</b>\n\n"
    for collection_id, collection_data in collections.items():
        movie_count = len(collection_data['movies'])
        message += f"• <b>{collection_data['name']}</b> ({movie_count} фильмов)\n"

    await update.message.reply_text(
        message,
        reply_markup=get_collections_keyboard(user_id),
        parse_mode='HTML'
    )


async def show_collection_movies(update: Update, context: ContextTypes.DEFAULT_TYPE, collection_id=None):
    """Показывает фильмы в подборке"""
    user_id = update.effective_user.id

    if not collection_id:
        # Получаем collection_id из текста сообщения
        text = update.message.text
        collections = get_user_collections(user_id)

        # Ищем подборку по названию (убираем эмодзи и количество фильмов)
        collection_name = text.replace("📁 ", "").split(" (")[0]

        for cid, collection_data in collections.items():
            if collection_data['name'] == collection_name:
                collection_id = cid
                break

    if not collection_id:
        await update.message.reply_text("❌ Подборка не найдена.", reply_markup=get_collections_keyboard(user_id))
        return

    collections = get_user_collections(user_id)
    collection_data = collections.get(collection_id)

    if not collection_data:
        await update.message.reply_text("❌ Подборка не найдена.", reply_markup=get_collections_keyboard(user_id))
        return

    movies = collection_data['movies']

    if not movies:
        await update.message.reply_text(
            f"📭 Подборка '<b>{collection_data['name']}</b>' пуста.\n\nДобавьте фильмы в подборку через меню действий фильма.",
            reply_markup=get_collections_keyboard(user_id),
            parse_mode='HTML'
        )
        return

    # Сохраняем в context для навигации
    context.user_data['current_collection'] = movies
    context.user_data['current_collection_index'] = 0
    context.user_data['current_collection_id'] = collection_id
    context.user_data['current_search_type'] = 'collection'

    # Показываем первый фильм
    await show_collection_movie(update, context, 0)


async def show_collection_movie(update: Update, context: ContextTypes.DEFAULT_TYPE, index=0):
    """Показывает один фильм из подборки"""
    user_id = update.effective_user.id
    collection_movies = context.user_data.get('current_collection', [])
    collection_id = context.user_data.get('current_collection_id')

    if not collection_movies or index >= len(collection_movies):
        message_text = "❌ Ошибка отображения подборки"
        await update.message.reply_text(message_text, reply_markup=get_collections_keyboard(user_id))
        return

    content_data = collection_movies[index]
    context.user_data['current_collection_index'] = index

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

                # Отправляем с навигацией
                navigation_data = (index, len(collection_movies), "collection", collection_id)
                await send_content(update, content, user_id, is_series, navigation_data)
                return

    except Exception as e:
        logger.error(f"Error loading collection movie: {e}")

    # Если не удалось загрузить полную информацию, показываем базовую
    content_type = "сериал" if content_data.get('type') == 'tv-series' else "фильм"
    genres = get_genres(content_data)
    message = f"<b>🎬 {content_data.get('name', 'Неизвестно')}</b> ({content_data.get('year', 'Неизвестно')}) - {content_type}\n🏷️ <b>Жанр:</b> {genres}"

    keyboard = get_collection_movies_keyboard(collection_id, index, len(collection_movies), content_data.get('id'))

    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode='HTML'
        )


async def show_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает избранное"""
    user_id = update.effective_user.id
    favorites = get_user_list(user_id, "favorites")

    if not favorites:
        await update.message.reply_text("📭 Нет избранных фильмов и сериалов.", reply_markup=get_back_keyboard())
        return

    # Сохраняем список избранного в user_data для навигации
    context.user_data['current_favorites'] = favorites
    context.user_data['current_favorites_index'] = 0
    context.user_data['current_search_type'] = 'favorites'

    # Показываем первый элемент
    await show_favorites_item(update, context, 0)


async def show_favorites_item(update: Update, context: ContextTypes.DEFAULT_TYPE, index=0):
    """Показывает один элемент из избранного с навигацией"""
    user_id = update.effective_user.id
    favorites = context.user_data.get('current_favorites', [])

    if not favorites or index >= len(favorites):
        message_text = "❌ Ошибка отображения списка"
        await update.message.reply_text(message_text, reply_markup=get_back_keyboard())
        return

    content_data = favorites[index]
    context.user_data['current_favorites_index'] = index

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

                # Отправляем с навигацией
                navigation_data = (index, len(favorites), "favorites", None)
                await send_content(update, content, user_id, is_series, navigation_data)
                return

    except Exception as e:
        logger.error(f"Error loading favorite: {e}")

    # Если не удалось загрузить полную информацию, показываем базовую
    content_type = "сериал" if content_data.get('type') == 'tv-series' else "фильм"
    genres = get_genres(content_data)
    message = f"<b>🎬 {content_data.get('name', 'Неизвестно')}</b> ({content_data.get('year', 'Неизвестно')}) - {content_type}\n🏷️ <b>Жанр:</b> {genres}"

    keyboard = get_list_navigation_keyboard(index, len(favorites), "favorites", content_data.get('id'))

    await update.message.reply_text(
        message,
        reply_markup=keyboard,
        parse_mode='HTML'
    )


async def show_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список желаемого"""
    user_id = update.effective_user.id
    watchlist = get_user_list(user_id, "watchlist")

    if not watchlist:
        await update.message.reply_text("📭 Нет фильмов и сериалов в списке.", reply_markup=get_back_keyboard())
        return

    # Сохраняем список желаемого в user_data для навигации
    context.user_data['current_watchlist'] = watchlist
    context.user_data['current_watchlist_index'] = 0
    context.user_data['current_search_type'] = 'watchlist'

    # Показываем первый элемент
    await show_watchlist_item(update, context, 0)


async def show_watchlist_item(update: Update, context: ContextTypes.DEFAULT_TYPE, index=0):
    """Показывает один элемент из списка желаемого с навигацией"""
    user_id = update.effective_user.id
    watchlist = context.user_data.get('current_watchlist', [])

    if not watchlist or index >= len(watchlist):
        message_text = "❌ Ошибка отображения списка"
        await update.message.reply_text(message_text, reply_markup=get_back_keyboard())
        return

    content_data = watchlist[index]
    context.user_data['current_watchlist_index'] = index

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

                # Отправляем с навигацией
                navigation_data = (index, len(watchlist), "watchlist", None)
                await send_content(update, content, user_id, is_series, navigation_data)
                return

    except Exception as e:
        logger.error(f"Error loading watchlist item: {e}")

    # Если не удалось загрузить полную информацию, показываем базовую
    content_type = "сериал" if content_data.get('type') == 'tv-series' else "фильм"
    genres = get_genres(content_data)
    message = f"<b>🎬 {content_data.get('name', 'Неизвестно')}</b> ({content_data.get('year', 'Неизвестно')}) - {content_type}\n🏷️ <b>Жанр:</b> {genres}"

    keyboard = get_list_navigation_keyboard(index, len(watchlist), "watchlist", content_data.get('id'))

    await update.message.reply_text(
        message,
        reply_markup=keyboard,
        parse_mode='HTML'
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = """
🎬 Добро пожаловать в КиноБот!

🎬 Поиск фильмов и сериалов - найти по названию
🔍 Поиск по актерам - найти фильмы по актерам
🎭 Фильтр по жанру/году - поиск по жанру и году
⭐ Избранное - ваши любимые фильмы и сериалы  
🎯 Хочу посмотреть - фильмы и сериалы для просмотра
📚 Мои подборки - создавайте свои коллекции фильмов
🎲 Случайный фильм - современные фильмы с навигацией
📺 Случайный сериал - современные сериалы с навигацией
"""
    await update.message.reply_text(message, reply_markup=get_main_keyboard())


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "🎬 Поиск фильмов и сериалов":
        await update.message.reply_text(
            "🎬 Введите название фильма или сериала для поиска:",
            reply_markup=get_back_keyboard()
        )
        context.user_data['waiting_for_search'] = True

    elif text == "🔍 Поиск по актерам":
        await search_by_actor(update, context)

    elif text == "🎭 Фильтр по жанру/году":
        await filter_by_genre_year(update, context)

    elif text == "⭐ Избранное":
        await show_favorites(update, context)

    elif text == "🎯 Хочу посмотреть":
        await show_watchlist(update, context)

    elif text == "📚 Мои подборки":
        await show_collections(update, context)

    elif text == "🎲 Случайный фильм":
        await random_movie(update, context)

    elif text == "📺 Случайный сериал":
        await random_series(update, context)

    elif text == "⬅️ Назад в меню":
        await update.message.reply_text("🏠 Главное меню:", reply_markup=get_main_keyboard())

    elif text == "➕ Создать подборку":
        await create_collection_handler(update, context)

    elif text == "📋 Мои подборки":
        await show_user_collections(update, context)

    elif text.startswith("📁 "):
        # Обработка нажатия на конкретную подборку
        await show_collection_movies(update, context)


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
    if context.user_data.get('waiting_for_search'):
        context.args = update.message.text.split()
        await search_content(update, context)
        context.user_data['waiting_for_search'] = False
    elif context.user_data.get('waiting_for_actor'):
        context.args = update.message.text.split()
        await search_by_actor(update, context)
        context.user_data['waiting_for_actor'] = False
    elif context.user_data.get('waiting_for_filter'):
        await handle_filter_input(update, context)
    elif context.user_data.get('waiting_for_collection_name'):
        await handle_collection_name(update, context)
    else:
        context.args = update.message.text.split()
        await search_content(update, context)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # Обработка добавления в подборку - ПЕРВЫЙ ВАРИАНТ (выбор подборки)
    if data.startswith('add_to_collection_'):
        # Показ выбора подборок
        movie_id = data.split('_')[3]
        collections = get_user_collections(user_id)

        if not collections:
            if query.message.caption:
                await query.edit_message_caption(
                    caption=query.message.caption + "\n\n📭 У вас нет подборок. Создайте первую подборку!",
                    parse_mode='HTML'
                )
            else:
                await query.edit_message_text(
                    query.message.text + "\n\n📭 У вас нет подборок. Создайте первую подборку!",
                    parse_mode='HTML'
                )
            return

        keyboard = get_collections_choice_keyboard(user_id, movie_id)

        # Создаем сообщение с выбором подборки
        message_text = "📚 Выберите подборку для добавления фильма:"

        if query.message.caption:
            # Если сообщение с фото, создаем новое текстовое сообщение
            await query.edit_message_caption(
                caption=query.message.caption + f"\n\n{message_text}",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            # Если текстовое сообщение, редактируем его
            await query.edit_message_text(
                query.message.text + f"\n\n{message_text}",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        return

    # Обработка добавления в конкретную подборку - ВТОРОЙ ВАРИАНТ
    elif data.startswith('add_collection_'):
        parts = data.split('_')

        if len(parts) == 4:
            # Выбор подборки для добавления
            collection_id = parts[2]
            movie_id = parts[3]

            try:
                response = requests.get(
                    f"https://api.kinopoisk.dev/v1.4/movie/{movie_id}",
                    headers={"X-API-KEY": KINOPOISK_API_KEY},
                    timeout=10
                )

                if response.status_code == 200:
                    content = response.json()
                    content_data = {
                        'id': content['id'],
                        'name': content.get('name', 'Неизвестно'),
                        'year': content.get('year', 'Неизвестно'),
                        'rating': content.get('rating', {}).get('kp', 'Нет рейтинга'),
                        'type': content.get('type', 'movie'),
                        'genres': content.get('genres', [])
                    }

                    collections = get_user_collections(user_id)
                    collection_name = collections.get(collection_id, {}).get('name', 'Неизвестно')

                    if add_to_collection(user_id, collection_id, content_data):
                        success_msg = f"\n\n✅ Добавлено в подборку '{collection_name}'!"
                    else:
                        success_msg = f"\n\n⚠️ Этот фильм уже есть в подборке '{collection_name}'!"

                    # Обновляем сообщение с исходной клавиатурой
                    is_series = content.get('type') == 'tv-series'

                    # Определяем контекст для восстановления правильной клавиатуры
                    search_type = context.user_data.get('current_search_type', 'search')
                    current_index = 0
                    total_items = 1

                    if search_type == 'search':
                        current_index = context.user_data.get('search_index', 0)
                        search_results = context.user_data.get('search_results', [])
                        total_items = len(search_results)
                        new_keyboard = get_search_navigation_keyboard(current_index, total_items, movie_id, user_id,
                                                                      is_series, "search")
                    elif search_type == 'actor':
                        current_index = context.user_data.get('actor_index', 0)
                        actor_results = context.user_data.get('actor_results', [])
                        total_items = len(actor_results)
                        new_keyboard = get_search_navigation_keyboard(current_index, total_items, movie_id, user_id,
                                                                      is_series, "actor")
                    elif search_type == 'filter':
                        current_index = context.user_data.get('filter_index', 0)
                        filter_results = context.user_data.get('filter_results', [])
                        total_items = len(filter_results)
                        new_keyboard = get_search_navigation_keyboard(current_index, total_items, movie_id, user_id,
                                                                      is_series, "filter")
                    elif search_type == 'favorites':
                        current_index = context.user_data.get('current_favorites_index', 0)
                        favorites = context.user_data.get('current_favorites', [])
                        total_items = len(favorites)
                        new_keyboard = get_list_navigation_keyboard(current_index, total_items, "favorites", movie_id)
                    elif search_type == 'watchlist':
                        current_index = context.user_data.get('current_watchlist_index', 0)
                        watchlist = context.user_data.get('current_watchlist', [])
                        total_items = len(watchlist)
                        new_keyboard = get_list_navigation_keyboard(current_index, total_items, "watchlist", movie_id)
                    elif search_type == 'random_movie':
                        current_index = context.user_data.get('random_movie_index', 0)
                        random_movies = context.user_data.get('random_movies', [])
                        total_items = len(random_movies)
                        new_keyboard = get_random_navigation_keyboard(current_index, total_items, movie_id, user_id,
                                                                      is_series, "movie")
                    elif search_type == 'random_series':
                        current_index = context.user_data.get('random_series_index', 0)
                        random_series_list = context.user_data.get('random_series', [])
                        total_items = len(random_series_list)
                        new_keyboard = get_random_navigation_keyboard(current_index, total_items, movie_id, user_id,
                                                                      is_series, "series")
                    elif search_type == 'collection':
                        current_index = context.user_data.get('current_collection_index', 0)
                        collection_movies = context.user_data.get('current_collection', [])
                        total_items = len(collection_movies)
                        collection_id_ctx = context.user_data.get('current_collection_id')
                        new_keyboard = get_collection_movies_keyboard(collection_id_ctx, current_index, total_items,
                                                                      movie_id)
                    else:
                        new_keyboard = get_movie_actions_keyboard(movie_id, user_id, is_series)

                    if query.message.caption:
                        # Восстанавливаем оригинальную подпись без текста о выборе подборки
                        original_caption = query.message.caption.split('\n\n📚 Выберите подборку')[0]
                        new_caption = original_caption + success_msg
                        await query.edit_message_caption(
                            caption=new_caption,
                            reply_markup=new_keyboard,
                            parse_mode='HTML'
                        )
                    else:
                        # Восстанавливаем оригинальный текст без текста о выборе подборки
                        original_text = query.message.text.split('\n\n📚 Выберите подборку')[0]
                        new_text = original_text + success_msg
                        await query.edit_message_text(
                            new_text,
                            reply_markup=new_keyboard,
                            parse_mode='HTML'
                        )
                else:
                    if query.message.caption:
                        await query.edit_message_caption(
                            caption=query.message.caption + "\n\n❌ Ошибка при добавлении в подборку.",
                            parse_mode='HTML'
                        )
                    else:
                        await query.edit_message_text(
                            query.message.text + "\n\n❌ Ошибка при добавлении в подборку.",
                            parse_mode='HTML'
                        )

            except Exception as e:
                logger.error(f"Error adding to collection: {e}")
                if query.message.caption:
                    await query.edit_message_caption(
                        caption=query.message.caption + "\n\n❌ Ошибка при добавлении в подборку.",
                        parse_mode='HTML'
                    )
                else:
                    await query.edit_message_text(
                        query.message.text + "\n\n❌ Ошибка при добавлении в подборку.",
                        parse_mode='HTML'
                    )
        return

    # Обработка отмены выбора подборки
    elif data == "cancel_collection":
        # Восстанавливаем оригинальное сообщение с фильмом
        try:
            # Получаем movie_id из предыдущего состояния
            movie_id = None
            if 'current_search_type' in context.user_data:
                search_type = context.user_data['current_search_type']
                if search_type == 'search':
                    current_index = context.user_data.get('search_index', 0)
                    search_results = context.user_data.get('search_results', [])
                    if search_results and current_index < len(search_results):
                        movie_id = search_results[current_index].get('id')
                # Аналогично для других типов поиска...

            if movie_id:
                # Загружаем информацию о фильме и показываем с оригинальной клавиатурой
                response = requests.get(
                    f"https://api.kinopoisk.dev/v1.4/movie/{movie_id}",
                    headers={"X-API-KEY": KINOPOISK_API_KEY},
                    timeout=10
                )

                if response.status_code == 200:
                    content = response.json()
                    is_series = content.get('type') == 'tv-series'
                    new_keyboard = get_movie_actions_keyboard(movie_id, user_id, is_series)

                    if query.message.caption:
                        # Восстанавливаем оригинальную подпись
                        original_caption = query.message.caption.split('\n\n📚 Выберите подборку')[0]
                        await query.edit_message_caption(
                            caption=original_caption,
                            reply_markup=new_keyboard,
                            parse_mode='HTML'
                        )
                    else:
                        # Восстанавливаем оригинальный текст
                        original_text = query.message.text.split('\n\n📚 Выберите подборку')[0]
                        await query.edit_message_text(
                            original_text,
                            reply_markup=new_keyboard,
                            parse_mode='HTML'
                        )
                else:
                    await query.edit_message_text(
                        "❌ Добавление в подборку отменено.",
                        reply_markup=get_back_keyboard()
                    )
            else:
                await query.edit_message_text(
                    "❌ Добавление в подборку отменено.",
                    reply_markup=get_back_keyboard()
                )
        except Exception as e:
            logger.error(f"Error canceling collection: {e}")
            await query.edit_message_text(
                "❌ Добавление в подборку отменено.",
                reply_markup=get_back_keyboard()
            )
        return

    # ... остальной код обработчика button_handler остается без изменений ...

    # Обработка навигации по подборкам
    elif data.startswith('nav_collection_'):
        parts = data.split('_')
        collection_id = parts[2]
        new_index = int(parts[3])
        context.user_data['current_collection_id'] = collection_id
        await show_collection_movie(update, context, new_index)
        return

    # Обработка удаления из подборки
    elif data.startswith('remove_from_collection_'):
        parts = data.split('_')
        collection_id = parts[3]
        movie_id = parts[4]

        if remove_from_collection(user_id, collection_id, movie_id):
            # Обновляем список фильмов в контексте
            collection_movies = context.user_data.get('current_collection', [])
            context.user_data['current_collection'] = [m for m in collection_movies if
                                                       str(m.get('id')) != str(movie_id)]
            current_index = context.user_data.get('current_collection_index', 0)

            if not context.user_data['current_collection']:
                await query.edit_message_text("📭 Подборка пуста!", reply_markup=get_collections_keyboard(user_id))
                return

            if current_index >= len(context.user_data['current_collection']):
                current_index = len(context.user_data['current_collection']) - 1

            await show_collection_movie(update, context, current_index)
        return

    # Обработка навигации по случайным фильмам
    elif data.startswith('nav_random_movie_'):
        new_index = int(data.split('_')[3])
        await show_random_movie(update, context, new_index)
        return

    # Обработка навигации по случайным сериалам
    elif data.startswith('nav_random_series_'):
        new_index = int(data.split('_')[3])
        await show_random_series(update, context, new_index)
        return

    # Обработка навигации по поиску
    elif data.startswith('nav_search_'):
        new_index = int(data.split('_')[2])
        await show_search_result(update, context, new_index)
        return

    # Обработка навигации по актерам
    elif data.startswith('nav_actor_'):
        new_index = int(data.split('_')[2])
        await show_actor_result(update, context, new_index)
        return

    # Обработка навигации по фильтру
    elif data.startswith('nav_filter_'):
        new_index = int(data.split('_')[2])
        await show_filter_result(update, context, new_index)
        return

    # Обработка навигации по спискам
    elif data.startswith('nav_'):
        parts = data.split('_')
        list_type = parts[1]
        new_index = int(parts[2])

        if list_type == "favorites":
            await show_favorites_item(update, context, new_index)
        elif list_type == "watchlist":
            await show_watchlist_item(update, context, new_index)
        return

    # Обработка удаления из списка
    elif data.startswith('remove_from_'):
        parts = data.split('_')
        list_type = parts[2]
        movie_id = parts[3]

        if remove_from_list(user_id, movie_id, list_type):
            if list_type == "favorites":
                favorites = context.user_data.get('current_favorites', [])
                context.user_data['current_favorites'] = [m for m in favorites if str(m.get('id')) != str(movie_id)]
                current_index = context.user_data.get('current_favorites_index', 0)

                if not context.user_data['current_favorites']:
                    await query.edit_message_text("📭 Избранное пусто!", reply_markup=get_back_keyboard())
                    return

                if current_index >= len(context.user_data['current_favorites']):
                    current_index = len(context.user_data['current_favorites']) - 1

                await show_favorites_item(update, context, current_index)

            elif list_type == "watchlist":
                watchlist = context.user_data.get('current_watchlist', [])
                context.user_data['current_watchlist'] = [m for m in watchlist if str(m.get('id')) != str(movie_id)]
                current_index = context.user_data.get('current_watchlist_index', 0)

                if not context.user_data['current_watchlist']:
                    await query.edit_message_text("📭 Список желаемого пуст!", reply_markup=get_back_keyboard())
                    return

                if current_index >= len(context.user_data['current_watchlist']):
                    current_index = len(context.user_data['current_watchlist']) - 1

                await show_watchlist_item(update, context, current_index)
        return

    # Обработка информации о странице
    elif data == "page_info":
        return

    # Обработка кнопок добавления/удаления
    parts = data.split('_')
    action = parts[0] + '_' + parts[1]
    movie_id = parts[2]

    try:
        response = requests.get(
            f"https://api.kinopoisk.dev/v1.4/movie/{movie_id}",
            headers={"X-API-KEY": KINOPOISK_API_KEY},
            timeout=10
        )

        if response.status_code != 200:
            if query.message.caption:
                await query.edit_message_caption(
                    caption=query.message.caption + "\n\n❌ Ошибка.",
                    parse_mode='HTML'
                )
            else:
                await query.edit_message_text(
                    query.message.text + "\n\n❌ Ошибка.",
                    parse_mode='HTML'
                )
            return

        content = response.json()

        content_data = {
            'id': content['id'],
            'name': content.get('name', 'Неизвестно'),
            'year': content.get('year', 'Неизвестно'),
            'rating': content.get('rating', {}).get('kp', 'Нет рейтинга'),
            'type': content.get('type', 'movie'),
            'genres': content.get('genres', [])
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

        # Обновляем сообщение
        is_series = content.get('type') == 'tv-series'

        # Определяем контекст по текущему типу поиска
        search_type = context.user_data.get('current_search_type', 'search')
        current_index = 0
        total_items = 1

        if search_type == 'search':
            current_index = context.user_data.get('search_index', 0)
            search_results = context.user_data.get('search_results', [])
            total_items = len(search_results)
            new_keyboard = get_search_navigation_keyboard(current_index, total_items, movie_id, user_id, is_series,
                                                          "search")
        elif search_type == 'actor':
            current_index = context.user_data.get('actor_index', 0)
            actor_results = context.user_data.get('actor_results', [])
            total_items = len(actor_results)
            new_keyboard = get_search_navigation_keyboard(current_index, total_items, movie_id, user_id, is_series,
                                                          "actor")
        elif search_type == 'filter':
            current_index = context.user_data.get('filter_index', 0)
            filter_results = context.user_data.get('filter_results', [])
            total_items = len(filter_results)
            new_keyboard = get_search_navigation_keyboard(current_index, total_items, movie_id, user_id, is_series,
                                                          "filter")
        elif search_type == 'favorites':
            current_index = context.user_data.get('current_favorites_index', 0)
            favorites = context.user_data.get('current_favorites', [])
            total_items = len(favorites)
            new_keyboard = get_list_navigation_keyboard(current_index, total_items, "favorites", movie_id)
        elif search_type == 'watchlist':
            current_index = context.user_data.get('current_watchlist_index', 0)
            watchlist = context.user_data.get('current_watchlist', [])
            total_items = len(watchlist)
            new_keyboard = get_list_navigation_keyboard(current_index, total_items, "watchlist", movie_id)
        elif search_type == 'random_movie':
            current_index = context.user_data.get('random_movie_index', 0)
            random_movies = context.user_data.get('random_movies', [])
            total_items = len(random_movies)
            new_keyboard = get_random_navigation_keyboard(current_index, total_items, movie_id, user_id, is_series,
                                                          "movie")
        elif search_type == 'random_series':
            current_index = context.user_data.get('random_series_index', 0)
            random_series_list = context.user_data.get('random_series', [])
            total_items = len(random_series_list)
            new_keyboard = get_random_navigation_keyboard(current_index, total_items, movie_id, user_id, is_series,
                                                          "series")
        elif search_type == 'collection':
            current_index = context.user_data.get('current_collection_index', 0)
            collection_movies = context.user_data.get('current_collection', [])
            total_items = len(collection_movies)
            collection_id = context.user_data.get('current_collection_id')
            new_keyboard = get_collection_movies_keyboard(collection_id, current_index, total_items, movie_id)
        else:
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
        if query.message.caption:
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n❌ Ошибка.",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(
                query.message.text + "\n\n❌ Ошибка.",
                parse_mode='HTML'
            )


def main():
    # Создаем файлы если их нет
    for filename in [FAVORITES_FILE, WATCHLIST_FILE, COLLECTIONS_FILE]:
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    # Основные кнопки меню
    application.add_handler(MessageHandler(filters.Text([
        "🎬 Поиск фильмов и сериалов", "🔍 Поиск по актерам", "🎭 Фильтр по жанру/году",
        "⭐ Избранное", "🎯 Хочу посмотреть", "📚 Мои подборки",
        "🎲 Случайный фильм", "📺 Случайный сериал", "⬅️ Назад в меню",
        "➕ Создать подборку", "📋 Мои подборки"
    ]), handle_main_menu))

    # Обработка нажатия на подборки (кнопки начинающиеся с "📁 ")
    application.add_handler(MessageHandler(filters.Regex(r"^📁 .*"), handle_main_menu))

    application.add_handler(MessageHandler(filters.Text([
        "🗑 Очистить избранное", "🗑 Очистить желаемое"
    ]), handle_list_management))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_input))
    application.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Бот запущен...")
    application.run_polling()


if __name__ == '__main__':
    main()