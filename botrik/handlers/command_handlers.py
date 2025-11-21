import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.user_service import UserService
from keyboards.keyboard_manager import KeyboardManager

logger = logging.getLogger(__name__)

class CommandHandlers:
    def __init__(self):
        self.user_service = UserService()
        self.keyboard_manager = KeyboardManager()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        logger.info(f"User {user.id} started the bot")

        # Регистрируем пользователя
        self.user_service.register_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )

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
        await update.message.reply_text(message, reply_markup=self.keyboard_manager.get_main_keyboard())