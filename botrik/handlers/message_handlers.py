import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.movie_service import MovieService
from services.collection_service import CollectionService
from keyboards.keyboard_manager import KeyboardManager

logger = logging.getLogger(__name__)


class MessageHandlers:
    def __init__(self):
        self.movie_service = MovieService()
        self.collection_service = CollectionService()
        self.keyboard_manager = KeyboardManager()

    async def handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик главного меню"""
        text = update.message.text
        user_id = update.effective_user.id
        logger.info(f"User {user_id} selected menu option: {text}")

        if text == "🎬 Поиск фильмов и сериалов":
            await update.message.reply_text(
                "🎬 Введите название фильма или сериала для поиска:",
                reply_markup=self.keyboard_manager.get_back_keyboard()
            )
            context.user_data['waiting_for_search'] = True

        elif text == "⭐ Избранное":
            await self.show_favorites(update, context)

        elif text == "🎯 Хочу посмотреть":
            await self.show_watchlist(update, context)

        elif text == "📚 Мои подборки":
            await self.show_collections(update, context)

        elif text == "🎲 Случайный фильм":
            await self.random_movie(update, context)

        elif text == "📺 Случайный сериал":
            await self.random_series(update, context)

        elif text == "⬅️ Назад в меню":
            await update.message.reply_text("🏠 Главное меню:", reply_markup=self.keyboard_manager.get_main_keyboard())

        elif text == "➕ Создать подборку":
            await self.create_collection_handler(update, context)

        elif text == "📋 Мои подборки":
            await self.show_user_collections(update, context)

        elif text.startswith("📁 "):
            await self.show_collection_movies(update, context)

    async def handle_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстового ввода"""
        user_id = update.effective_user.id
        text = update.message.text

        # Создание подборки
        if context.user_data.get('waiting_for_collection_name'):
            await self.handle_collection_name(update, context)
            return

        # Поиск фильмов
        if context.user_data.get('waiting_for_search'):
            await self.handle_text_search(update, context)
            return

        # Если не распознано, показываем главное меню
        await update.message.reply_text(
            "Выберите действие из меню:",
            reply_markup=self.keyboard_manager.get_main_keyboard()
        )

    async def show_favorites(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает избранное"""
        user_id = update.effective_user.id
        logger.info(f"User {user_id} viewing favorites")
        favorites = self.movie_service.get_favorites(user_id)

        if not favorites:
            await update.message.reply_text("📭 Нет избранных фильмов и сериалов.",
                                            reply_markup=self.keyboard_manager.get_back_keyboard())
            return

        context.user_data['current_list'] = favorites
        context.user_data['current_index'] = 0
        context.user_data['current_list_type'] = 'favorites'
        context.user_data['total_count'] = len(favorites)

        await self.show_current_item(update, context)

    async def show_watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает список желаемого"""
        user_id = update.effective_user.id
        logger.info(f"User {user_id} viewing watchlist")
        watchlist = self.movie_service.get_watchlist(user_id)

        if not watchlist:
            await update.message.reply_text("📭 Нет фильмов и сериалов в списке.",
                                            reply_markup=self.keyboard_manager.get_back_keyboard())
            return

        context.user_data['current_list'] = watchlist
        context.user_data['current_index'] = 0
        context.user_data['current_list_type'] = 'watchlist'
        context.user_data['total_count'] = len(watchlist)

        await self.show_current_item(update, context)

    async def show_collection_movies(self, update: Update, context: ContextTypes.DEFAULT_TYPE, collection_id=None):
        """Показывает фильмы в подборке"""
        user_id = update.effective_user.id

        if not collection_id:
            text = update.message.text
            collections = self.collection_service.get_user_collections(user_id)
            collection_name = text.replace("📁 ", "").split(" (")[0]

            for cid, collection_data in collections.items():
                if collection_data['name'] == collection_name:
                    collection_id = cid
                    break

        if not collection_id:
            await update.message.reply_text("❌ Подборка не найдена.",
                                            reply_markup=self.keyboard_manager.get_collections_keyboard(user_id))
            return

        collections = self.collection_service.get_user_collections(user_id)
        collection_data = collections.get(collection_id)

        if not collection_data:
            await update.message.reply_text("❌ Подборка не найдена.",
                                            reply_markup=self.keyboard_manager.get_collections_keyboard(user_id))
            return

        movies = collection_data['movies']

        if not movies:
            await update.message.reply_text(
                f"📭 Подборка '<b>{collection_data['name']}</b>' пуста.",
                reply_markup=self.keyboard_manager.get_collections_keyboard(user_id),
                parse_mode='HTML'
            )
            return

        context.user_data['current_list'] = movies
        context.user_data['current_index'] = 0
        context.user_data['current_list_type'] = 'collection'
        context.user_data['collection_id'] = collection_id
        context.user_data['collection_name'] = collection_data['name']
        context.user_data['total_count'] = len(movies)

        await self.show_current_item(update, context)

    async def show_current_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает текущий элемент списка с навигацией"""
        try:
            current_list = context.user_data.get('current_list', [])
            current_index = context.user_data.get('current_index', 0)
            total_count = context.user_data.get('total_count', 0)
            list_type = context.user_data.get('current_list_type', '')

            if not current_list or current_index >= len(current_list):
                await update.message.reply_text(
                    "❌ Ошибка отображения списка",
                    reply_markup=self.keyboard_manager.get_back_keyboard()
                )
                return

            content_data = current_list[current_index]
            user_id = update.effective_user.id

            # Получаем полные данные фильма для постера
            full_movie_data = self.movie_service.get_movie_by_id(content_data['id'])
            if full_movie_data:
                content_data = full_movie_data

            # Получаем клавиатуру с навигацией
            keyboard = self.get_navigation_keyboard(current_index, total_count, list_type, content_data['id'], user_id)

            # Формируем сообщение в новом формате
            message = self.format_content_message_new(content_data, current_index + 1, total_count)

            # Отправляем постер если есть
            poster_url = content_data.get('poster', {}).get('url')
            if poster_url and poster_url.startswith('http'):
                try:
                    await update.message.reply_photo(
                        photo=poster_url,
                        caption=message,
                        reply_markup=keyboard,
                        parse_mode='HTML'
                    )
                    return
                except Exception as e:
                    logger.warning(f"Could not send photo {poster_url}: {e}")

            # Если постер не отправился, отправляем текстовое сообщение
            await update.message.reply_text(
                message,
                reply_markup=keyboard,
                parse_mode='HTML'
            )

        except Exception as e:
            logger.error(f"Error showing current item: {e}")
            await update.message.reply_text(
                "❌ Ошибка при отображении фильма",
                reply_markup=self.keyboard_manager.get_back_keyboard()
            )

    def format_content_message_new(self, content_data: dict, current_number: int, total_count: int) -> str:
        """Форматирует сообщение о фильме/сериале в новом формате (как на скриншотах)"""
        name = content_data.get('name', 'Неизвестно')
        year = content_data.get('year', 'Неизвестно')
        rating = content_data.get('rating', {})

        # Обрабатываем рейтинг
        if isinstance(rating, dict):
            rating_value = rating.get('kp', 'Нет рейтинга')
        else:
            rating_value = rating if rating else 'Нет рейтинга'

        description = content_data.get('description', '')

        # Жанры
        genres = content_data.get('genres', [])
        if genres and isinstance(genres[0], dict):
            genres_str = ', '.join([genre.get('name', '') for genre in genres[:3]])
        else:
            genres_str = ', '.join(genres) if genres else 'Не указаны'

        # Тип контента
        content_type = content_data.get('type', 'movie')
        content_type_str = "сериал" if content_type == 'tv-series' else "фильм"

        # Форматируем сообщение в стиле скриншотов
        message = f"<b>{name} ({year})</b>\n"
        message += f"Тип: {content_type_str}\n"
        message += f"Жанр: {genres_str}\n"
        message += f"Рейтинг: {rating_value}\n\n"

        # Для сериалов добавляем информацию о сезонах
        if content_type == 'tv-series':
            seasons = content_data.get('seasonsInfo', [])
            if seasons:
                seasons_count = len([s for s in seasons if s.get('number')])
                episodes_count = sum([s.get('episodesCount', 0) for s in seasons])
                message += f"Сезонов: {seasons_count}, Эпизодов: {episodes_count}\n"

        # Описание
        if description:
            if len(description) > 300:
                description = description[:300] + '...'
            message += f"Описание: {description}\n\n"
        else:
            message += "Описание: Нет описания\n\n"

        # ID и навигация
        message += f"ID: {content_data.get('id', 'Неизвестно')}\n"
        message += f"{current_number}/{total_count}"

        return message

    def get_navigation_keyboard(self, current_index: int, total_count: int, list_type: str, movie_id: int,
                                user_id: int):
        """Создает клавиатуру с навигацией и действиями в новом формате"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        keyboard = []

        # Кнопки навигации (в одну строку)
        nav_buttons = []
        if current_index > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"nav_prev_{list_type}"))

        nav_buttons.append(InlineKeyboardButton(f"{current_index + 1}/{total_count}", callback_data="no_action"))

        if current_index < total_count - 1:
            nav_buttons.append(InlineKeyboardButton("Дальше ➡️", callback_data=f"nav_next_{list_type}"))

        if nav_buttons:
            keyboard.append(nav_buttons)

        # Кнопки действий (в зависимости от типа списка)
        action_buttons = []

        if list_type == 'favorites':
            action_buttons.append(
                InlineKeyboardButton("❌ Удалить из избранного", callback_data=f"remove_fav_{movie_id}"))
        else:
            if not self.movie_service.is_in_favorites(user_id, movie_id):
                action_buttons.append(InlineKeyboardButton("⭐ В избранное", callback_data=f"add_fav_{movie_id}"))

        if list_type == 'watchlist':
            action_buttons.append(InlineKeyboardButton("❌ Удалить из списка", callback_data=f"remove_watch_{movie_id}"))
        else:
            if not self.movie_service.is_in_watchlist(user_id, movie_id):
                action_buttons.append(InlineKeyboardButton("🎯 Хочу посмотреть", callback_data=f"add_watch_{movie_id}"))

        if action_buttons:
            keyboard.append(action_buttons)

        # Кнопка добавления в подборку (кроме самих подборок)
        if list_type != 'collection':
            keyboard.append(
                [InlineKeyboardButton("📚 Добавить в подборку", callback_data=f"add_to_collection_{movie_id}")])

        return InlineKeyboardMarkup(keyboard)

    async def show_next_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает следующий элемент"""
        current_index = context.user_data.get('current_index', 0)
        total_count = context.user_data.get('total_count', 0)

        if current_index < total_count - 1:
            context.user_data['current_index'] = current_index + 1
            await self.show_current_item(update, context)
        else:
            await update.message.reply_text("🎉 Это последний элемент в списке!")

    async def show_previous_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает предыдущий элемент"""
        current_index = context.user_data.get('current_index', 0)

        if current_index > 0:
            context.user_data['current_index'] = current_index - 1
            await self.show_current_item(update, context)
        else:
            await update.message.reply_text("🎉 Это первый элемент в списке!")

    async def random_movie(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Случайный фильм"""
        try:
            logger.info(f"User {update.effective_user.id} requested random movie")
            await update.message.reply_text("🎲 Ищу современный фильм...")

            movie = self.movie_service.get_random_movie()
            if not movie:
                await update.message.reply_text("😔 Не удалось найти фильм.",
                                                reply_markup=self.keyboard_manager.get_back_keyboard())
                return

            await self.send_content(update, movie, update.effective_user.id)

        except Exception as e:
            logger.error(f"Error in random_movie: {e}")
            await update.message.reply_text("❌ Ошибка при поиске фильма",
                                            reply_markup=self.keyboard_manager.get_back_keyboard())

    async def random_series(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Случайный сериал"""
        try:
            logger.info(f"User {update.effective_user.id} requested random series")
            await update.message.reply_text("📺 Ищу случайный сериал...")

            series = self.movie_service.get_random_series()
            if not series:
                await update.message.reply_text("😔 Не удалось найти сериал.",
                                                reply_markup=self.keyboard_manager.get_back_keyboard())
                return

            await self.send_content(update, series, update.effective_user.id)

        except Exception as e:
            logger.error(f"Error in random_series: {e}")
            await update.message.reply_text("❌ Ошибка при поиске сериала",
                                            reply_markup=self.keyboard_manager.get_back_keyboard())

    async def show_collections(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает меню подборок"""
        user_id = update.effective_user.id
        logger.info(f"User {user_id} viewing collections")
        await update.message.reply_text(
            "📚 <b>Мои подборки</b>\n\n"
            "Здесь вы можете создавать свои собственные подборки фильмов и сериалов.",
            reply_markup=self.keyboard_manager.get_collections_keyboard(user_id),
            parse_mode='HTML'
        )

    async def create_collection_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик создания подборки"""
        await update.message.reply_text(
            "📝 Введите название для новой подборки:",
            reply_markup=self.keyboard_manager.get_back_keyboard()
        )
        context.user_data['waiting_for_collection_name'] = True

    async def handle_collection_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода названия подборки"""
        if not context.user_data.get('waiting_for_collection_name'):
            return

        collection_name = update.message.text.strip()
        user_id = update.effective_user.id

        if not collection_name:
            await update.message.reply_text("❌ Название не может быть пустым.",
                                            reply_markup=self.keyboard_manager.get_collections_keyboard(user_id))
            context.user_data['waiting_for_collection_name'] = False
            return

        try:
            collection_id = self.collection_service.create_collection(user_id, collection_name)

            await update.message.reply_text(
                f"✅ Подборка '<b>{collection_name}</b>' успешно создана!",
                reply_markup=self.keyboard_manager.get_collections_keyboard(user_id),
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            await update.message.reply_text(
                "❌ Ошибка при создании подборки",
                reply_markup=self.keyboard_manager.get_collections_keyboard(user_id)
            )

        context.user_data['waiting_for_collection_name'] = False

    async def show_user_collections(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает подборки пользователя"""
        user_id = update.effective_user.id
        collections = self.collection_service.get_user_collections(user_id)

        if not collections:
            await update.message.reply_text(
                "📭 У вас пока нет подборок.\n\nСоздайте первую подборку!",
                reply_markup=self.keyboard_manager.get_collections_keyboard(user_id)
            )
            return

        message = "📚 <b>Ваши подборки:</b>\n\n"
        for collection_id, collection_data in collections.items():
            movie_count = len(collection_data['movies'])
            message += f"• <b>{collection_data['name']}</b> ({movie_count} фильмов)\n"

        await update.message.reply_text(
            message,
            reply_markup=self.keyboard_manager.get_collections_keyboard(user_id),
            parse_mode='HTML'
        )

    # МЕТОДЫ ДЛЯ ОТОБРАЖЕНИЯ ОДИНОЧНОГО КОНТЕНТА (для поиска и случайных)

    async def send_content(self, update: Update, content_data: dict, user_id: int):
        """Отправляет информацию о фильме/сериале (для одиночного показа)"""
        try:
            # Формируем текст сообщения в новом формате
            message = self.format_content_message_new(content_data, 1, 1)

            # Получаем клавиатуру действий
            is_series = content_data.get('type') == 'tv-series'
            keyboard = self.keyboard_manager.get_movie_actions_keyboard(
                content_data['id'], user_id, is_series
            )

            # Отправляем постер если есть
            poster_url = content_data.get('poster', {}).get('url')
            if poster_url and poster_url.startswith('http'):
                try:
                    await update.message.reply_photo(
                        photo=poster_url,
                        caption=message,
                        reply_markup=keyboard,
                        parse_mode='HTML'
                    )
                    return
                except Exception as e:
                    logger.warning(f"Could not send photo {poster_url}: {e}")

            # Если постер не отправился, отправляем текстовое сообщение
            await update.message.reply_text(
                message,
                reply_markup=keyboard,
                parse_mode='HTML'
            )

        except Exception as e:
            logger.error(f"Error sending content: {e}")
            await update.message.reply_text(
                "❌ Ошибка при отображении фильма",
                reply_markup=self.keyboard_manager.get_back_keyboard()
            )

    async def handle_text_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстового поиска"""
        if context.user_data.get('waiting_for_search'):
            query = update.message.text
            user_id = update.effective_user.id
            logger.info(f"User {user_id} searching for: {query}")

            await update.message.reply_text(f"🔍 Ищу: {query}...")

            # Поиск фильмов
            results = self.movie_service.search_movies(query)

            if not results:
                await update.message.reply_text(
                    "😔 Ничего не найдено. Попробуйте другой запрос.",
                    reply_markup=self.keyboard_manager.get_back_keyboard()
                )
                return

            context.user_data['current_list'] = results
            context.user_data['current_index'] = 0
            context.user_data['current_list_type'] = 'search'
            context.user_data['total_count'] = len(results)
            context.user_data['search_query'] = query

            # Показываем первый результат
            await self.show_current_item(update, context)

            context.user_data['waiting_for_search'] = False