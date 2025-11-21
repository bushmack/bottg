import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.movie_service import MovieService
from services.collection_service import CollectionService
from keyboards.keyboard_manager import KeyboardManager

logger = logging.getLogger(__name__)


class CallbackHandlers:
    def __init__(self):
        self.movie_service = MovieService()
        self.collection_service = CollectionService()
        self.keyboard_manager = KeyboardManager()

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback кнопок"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        data = query.data
        logger.info(f"User {user_id} pressed button: {data}")

        if data.startswith('add_fav_'):
            movie_id = int(data.split('_')[2])
            await self.add_to_favorites(update, context, user_id, movie_id)

        elif data.startswith('remove_fav_'):
            movie_id = int(data.split('_')[2])
            await self.remove_from_favorites(update, context, user_id, movie_id)

        elif data.startswith('add_watch_'):
            movie_id = int(data.split('_')[2])
            await self.add_to_watchlist(update, context, user_id, movie_id)

        elif data.startswith('remove_watch_'):
            movie_id = int(data.split('_')[2])
            await self.remove_from_watchlist(update, context, user_id, movie_id)

        elif data.startswith('add_to_collection_'):
            movie_id = data.split('_')[3]
            await self.show_collections_choice(update, context, user_id, movie_id)

        elif data.startswith('add_collection_'):
            parts = data.split('_')
            if len(parts) == 4:
                collection_id = parts[2]
                movie_id = parts[3]
                await self.add_to_collection(update, context, user_id, collection_id, movie_id)

        elif data.startswith('nav_prev_'):
            list_type = data.split('_')[2]
            await self.handle_navigation(update, context, 'prev', list_type)

        elif data.startswith('nav_next_'):
            list_type = data.split('_')[2]
            await self.handle_navigation(update, context, 'next', list_type)

        elif data == 'nav_main_menu':
            await self.handle_main_menu_navigation(update, context)

        elif data == 'cancel_collection':
            await self.handle_cancel_collection(update, context)

        elif data == 'no_action':
            await query.answer()

    async def add_to_favorites(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, movie_id: int):
        """Добавление в избранное"""
        query = update.callback_query
        movie = self.movie_service.get_movie_by_id(movie_id)
        if movie:
            movie_data = {
                'id': movie['id'],
                'name': movie.get('name', 'Неизвестно'),
                'year': movie.get('year', 'Неизвестно'),
                'rating': movie.get('rating', {}).get('kp', 'Нет рейтинга'),
                'type': movie.get('type', 'movie'),
                'genres': movie.get('genres', []),
                'poster': movie.get('poster', {}),
                'description': movie.get('description', '')
            }
            if self.movie_service.add_to_favorites(user_id, movie_data):
                success_msg = "\n\n✅ Добавлено в избранное"
            else:
                success_msg = "\n\n⚠️ Уже в избранном"

            await self.update_message_with_success(query, success_msg, user_id, movie_id)

    async def remove_from_favorites(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int,
                                    movie_id: int):
        """Удаление из избранного"""
        query = update.callback_query
        if self.movie_service.remove_from_favorites(user_id, movie_id):
            success_msg = "\n\n❌ Удалено из избранного"
        else:
            success_msg = "\n\n⚠️ Не было в избранном"

        await self.update_message_with_success(query, success_msg, user_id, movie_id)

    async def add_to_watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, movie_id: int):
        """Добавление в список желаемого"""
        query = update.callback_query
        movie = self.movie_service.get_movie_by_id(movie_id)
        if movie:
            movie_data = {
                'id': movie['id'],
                'name': movie.get('name', 'Неизвестно'),
                'year': movie.get('year', 'Неизвестно'),
                'rating': movie.get('rating', {}).get('kp', 'Нет рейтинга'),
                'type': movie.get('type', 'movie'),
                'genres': movie.get('genres', []),
                'poster': movie.get('poster', {}),
                'description': movie.get('description', '')
            }
            if self.movie_service.add_to_watchlist(user_id, movie_data):
                success_msg = "\n\n✅ Добавлено в желаемое"
            else:
                success_msg = "\n\n⚠️ Уже в желаемом"

            await self.update_message_with_success(query, success_msg, user_id, movie_id)

    async def remove_from_watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int,
                                    movie_id: int):
        """Удаление из списка желаемого"""
        query = update.callback_query
        if self.movie_service.remove_from_watchlist(user_id, movie_id):
            success_msg = "\n\n❌ Удалено из желаемого"
        else:
            success_msg = "\n\n⚠️ Не было в желаемом"

        await self.update_message_with_success(query, success_msg, user_id, movie_id)

    async def show_collections_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int,
                                      movie_id: str):
        """Показ выбора подборок"""
        query = update.callback_query
        collections = self.collection_service.get_user_collections(user_id)

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

        keyboard = self.keyboard_manager.get_collections_choice_keyboard(user_id, movie_id)
        message_text = "📚 Выберите подборку для добавления фильма:"

        if query.message.caption:
            await query.edit_message_caption(
                caption=query.message.caption + f"\n\n{message_text}",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(
                query.message.text + f"\n\n{message_text}",
                reply_markup=keyboard,
                parse_mode='HTML'
            )

    async def add_to_collection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int,
                                collection_id: str, movie_id: str):
        """Добавление в коллекцию"""
        query = update.callback_query
        movie = self.movie_service.get_movie_by_id(int(movie_id))
        if movie:
            movie_data = {
                'id': movie['id'],
                'name': movie.get('name', 'Неизвестно'),
                'year': movie.get('year', 'Неизвестно'),
                'rating': movie.get('rating', {}).get('kp', 'Нет рейтинга'),
                'type': movie.get('type', 'movie'),
                'genres': movie.get('genres', []),
                'poster': movie.get('poster', {}),
                'description': movie.get('description', '')
            }
            collections = self.collection_service.get_user_collections(user_id)
            collection_name = collections.get(collection_id, {}).get('name', 'Неизвестно')

            if self.collection_service.add_to_collection(user_id, collection_id, movie_data):
                success_msg = f"\n\n✅ Добавлено в подборку '{collection_name}'!"
            else:
                success_msg = f"\n\n⚠️ Этот фильм уже есть в подборке '{collection_name}'!"

            await self.update_message_with_success(query, success_msg, user_id, int(movie_id))

    async def handle_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, direction: str,
                                list_type: str):
        """Обработка навигации по спискам"""
        query = update.callback_query
        await query.answer()

        current_index = context.user_data.get('current_index', 0)
        total_count = context.user_data.get('total_count', 0)

        if direction == 'next' and current_index < total_count - 1:
            context.user_data['current_index'] = current_index + 1
        elif direction == 'prev' and current_index > 0:
            context.user_data['current_index'] = current_index - 1
        else:
            return

        # Создаем временный объект update с message для вызова show_current_item
        from telegram import Message
        temp_update = Update(update.update_id, message=query.message)

        # Обновляем сообщение через импорт обработчика сообщений
        from handlers.message_handlers import MessageHandlers
        message_handler = MessageHandlers()
        await message_handler.show_current_item(temp_update, context)

    async def handle_main_menu_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка возврата в главное меню"""
        query = update.callback_query
        await query.answer()

        # Очищаем данные навигации
        context.user_data.pop('current_list', None)
        context.user_data.pop('current_index', None)
        context.user_data.pop('current_list_type', None)
        context.user_data.pop('total_count', None)

        # Убираем клавиатуру у текущего сообщения
        await query.edit_message_reply_markup(reply_markup=None)

        # Отправляем новое сообщение с главным меню
        await query.message.reply_text(
            "🏠 Главное меню:",
            reply_markup=self.keyboard_manager.get_main_keyboard()
        )

    async def handle_cancel_collection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка отмены выбора подборки"""
        query = update.callback_query
        await query.answer()

        # Возвращаемся к обычному виду сообщения с фильмом
        if query.message.caption:
            original_caption = query.message.caption.split("\n\n📚 Выберите подборку")[0]
            await query.edit_message_caption(
                caption=original_caption,
                parse_mode='HTML'
            )
        else:
            original_text = query.message.text.split("\n\n📚 Выберите подборку")[0]
            await query.edit_message_text(
                original_text,
                parse_mode='HTML'
            )

    async def update_message_with_success(self, query, success_msg, user_id, movie_id):
        """Обновление сообщения с результатом операции"""
        try:
            is_series = False
            # Получаем актуальные данные о статусе фильма
            in_favorites = self.movie_service.is_in_favorites(user_id, movie_id)
            in_watchlist = self.movie_service.is_in_watchlist(user_id, movie_id)

            # Получаем обновленную клавиатуру
            new_keyboard = self.keyboard_manager.get_movie_actions_keyboard(movie_id, user_id, is_series)

            if query.message.caption:
                # Убираем предыдущие сообщения об успехе/ошибке
                original_caption = query.message.caption.split("\n\n✅")[0].split("\n\n⚠️")[0].split("\n\n❌")[0]
                new_caption = original_caption + success_msg
                await query.edit_message_caption(
                    caption=new_caption,
                    reply_markup=new_keyboard,
                    parse_mode='HTML'
                )
            else:
                # Убираем предыдущие сообщения об успехе/ошибке
                original_text = query.message.text.split("\n\n✅")[0].split("\n\n⚠️")[0].split("\n\n❌")[0]
                new_text = original_text + success_msg
                await query.edit_message_text(
                    new_text,
                    reply_markup=new_keyboard,
                    parse_mode='HTML'
                )

        except Exception as e:
            logger.error(f"Error updating message: {e}")
            # Если не удалось обновить сообщение, просто отправляем уведомление
            await query.answer(success_msg.strip(), show_alert=True)