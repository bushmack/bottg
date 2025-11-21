import logging
import os
from pathlib import Path
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Создаем папку service если её нет
LOG_DIR = Path("service")
LOG_DIR.mkdir(exist_ok=True)


# Настройка логирования
def setup_logging():
    log_file = LOG_DIR / "bot.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()  # Также выводим в консоль
        ]
    )
    return logging.getLogger(__name__)


logger = setup_logging()


# Пример обработчиков
async def start(update, context):
    logger.info(f"User {update.effective_user.id} started the bot")
    await update.message.reply_text('Привет!')


async def echo(update, context):
    user_id = update.effective_user.id
    message_text = update.message.text
    logger.info(f"User {user_id} sent message: {message_text}")
    await update.message.reply_text(f"Вы сказали: {message_text}")


async def error_handler(update, context):
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)


def main():
    # Инициализация бота
    application = Application.builder().token("7981463799:AAHxvci7hCtrq_Zm1pfpYHNmJFgrIrVe9r8").build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    application.add_error_handler(error_handler)

    logger.info("Bot is starting...")
    application.run_polling()


if __name__ == '__main__':
    main()