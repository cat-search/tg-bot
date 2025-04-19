import logging
import os

import httpx
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove,  # type: ignore
                      Update)
from telegram.ext import (Application, CommandHandler,  # type: ignore
                          ContextTypes, ConversationHandler, MessageHandler,
                          filters)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Настройки
BOT_TOKEN = os.getenv('bot_token', '')
FASTAPI_URL = "http://127.0.0.1:8000/front/query"  # URL FastAPI сервера

START, QUESTION, CONTINUE = range(3)

start_keyboard = ReplyKeyboardMarkup(
    [["Задать вопрос"]],
    resize_keyboard=True,
    one_time_keyboard=True,
)


continue_keyboard = ReplyKeyboardMarkup(
    [["Новый вопрос", "Завершить"]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

# Функция для запроса к FastAPI
async def fetch_answer(question: str) -> str:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                FASTAPI_URL,
                json={"query_text": question},
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json().get("answer", "Ошибка: ответ не распознан.")
            return "Ошибка: сервер недоступен."
        except httpx.RequestError:
            return "Ошибка: не удалось подключиться к серверу."

# Обработка команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот CatSearch, который отвечает на вопросы. Нажми «Задать вопрос», чтобы начать.",
        reply_markup=start_keyboard,
    )
    return START

# Обработка выбора "Задать вопрос"
async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "Введите ваш вопрос:"
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardRemove(),
    )
    return QUESTION

# Обработка текстового вопроса
async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text
    answer = await fetch_answer(question)
    await update.message.reply_text(
        answer,
        reply_markup=continue_keyboard,
    )
    return CONTINUE

# Обработка продолжения (новый вопрос или завершение)
async def continue_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice == "Новый вопрос":
        await update.message.reply_text(
            "Введите ваш вопрос:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return QUESTION
    elif choice == "Завершить":
        await update.message.reply_text(
            "Диалог завершён. Нажмите /start, чтобы начать заново.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

# Обработка отмены
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Диалог отменён. Нажмите /start, чтобы начать заново.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler для управления диалогом
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START: [MessageHandler(filters.Regex("^Задать вопрос$"), ask_question)],
            QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question)],
            CONTINUE: [
                MessageHandler(filters.Regex("^Новый вопрос$"), continue_conversation),
                MessageHandler(filters.Regex("^Завершить$"), cancel),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    logger.info("Bot started")

    app.run_polling()

if __name__ == "__main__":
    main()