import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import BOT_TOKEN
from handlers.command_handlers import CommandHandlers
from handlers.message_handlers import MessageHandlers
from handlers.callback_handlers import CallbackHandlers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция запуска бота"""
    # Инициализация обработчиков
    command_handlers = CommandHandlers()
    message_handlers = MessageHandlers()
    callback_handlers = CallbackHandlers()

    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", command_handlers.start))

    # Регистрация обработчиков сообщений меню
    application.add_handler(MessageHandler(filters.Text([
        "🎬 Поиск фильмов и сериалов", "🔍 Поиск по актерам", "🎭 Фильтр по жанру/году",
        "⭐ Избранное", "🎯 Хочу посмотреть", "📚 Мои подборки",
        "🎲 Случайный фильм", "📺 Случайный сериал", "⬅️ Назад в меню",
        "➕ Создать подборку", "📋 Мои подборки"
    ]), message_handlers.handle_main_menu))

    # Обработка нажатия на подборки
    application.add_handler(MessageHandler(filters.Regex(r"^📁 .*"), message_handlers.handle_main_menu))

    # Обработка ВСЕХ текстовых сообщений (поиск и создание подборок)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        message_handlers.handle_text_input
    ))

    # Регистрация обработчиков callback
    application.add_handler(CallbackQueryHandler(callback_handlers.handle_callback))

    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()