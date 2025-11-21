from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from services.movie_service import MovieService
from services.collection_service import CollectionService

class KeyboardManager:
    def __init__(self):
        self.movie_service = MovieService()
        self.collection_service = CollectionService()

    def get_main_keyboard(self):
        """Основная клавиатура"""
        keyboard = [
            [KeyboardButton("🎬 Поиск фильмов и сериалов")],
            [KeyboardButton("🔍 Поиск по актерам"), KeyboardButton("🎭 Фильтр по жанру/году")],
            [KeyboardButton("⭐ Избранное"), KeyboardButton("🎯 Хочу посмотреть")],
            [KeyboardButton("📚 Мои подборки"), KeyboardButton("🎲 Случайный фильм")],
            [KeyboardButton("📺 Случайный сериал")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    def get_back_keyboard(self):
        """Клавиатура назад"""
        keyboard = [
            [KeyboardButton("⬅️ Назад в меню")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    def get_collections_keyboard(self, user_id=None):
        """Клавиатура для управления подборками"""
        if user_id:
            collections = self.collection_service.get_user_collections(user_id)
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

    def get_movie_actions_keyboard(self, movie_id, user_id, is_series=False):
        """Клавиатура действий для фильма"""
        in_favorites = self.movie_service.is_in_favorites(user_id, movie_id)
        in_watchlist = self.movie_service.is_in_watchlist(user_id, movie_id)

        keyboard = []
        if in_favorites:
            keyboard.append([InlineKeyboardButton("❌ Удалить из избранного", callback_data=f"remove_fav_{movie_id}")])
        else:
            keyboard.append([InlineKeyboardButton("⭐ В избранное", callback_data=f"add_fav_{movie_id}")])

        if in_watchlist:
            keyboard.append([InlineKeyboardButton("❌ Удалить из желаемого", callback_data=f"remove_watch_{movie_id}")])
        else:
            keyboard.append([InlineKeyboardButton("🎯 Хочу посмотреть", callback_data=f"add_watch_{movie_id}")])

        keyboard.append([InlineKeyboardButton("📚 Добавить в подборку", callback_data=f"add_to_collection_{movie_id}")])
        return InlineKeyboardMarkup(keyboard)

    def get_collections_choice_keyboard(self, user_id, movie_id):
        """Клавиатура выбора подборок"""
        collections = self.collection_service.get_user_collections(user_id)
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