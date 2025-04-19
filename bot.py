import logging
import os

import httpx
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove,
    Update,
    )
from telegram.ext import (
    Application, 
    CommandHandler,
    ContextTypes,
    ConversationHandler, 
    CallbackQueryHandler,
    MessageHandler,
    filters,
    )
from telegram.constants import ChatAction
from telegram.error import InvalidToken

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Настройки
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
FASTAPI_URL = os.getenv('BOT_FASTAPI_URL', '')  # URL FastAPI сервера

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
    """
    Функция для запроса к FastAPI
    
    Формат ответа:
    {  
        'query_id': 'dd1d1f58-0190-4264-91c8-33a798f762f6', 
        'query_text': 'кто такая нэнси', 
        'timestamp': '2025-04-19T14:57:21.362012+00:00', 
        'vectordb_doc_count': 5, 
        'vdb_latency': 0.06935114902444184, 
        'llm_latency': 103.62458060507197, 
        'latency': 103.687061, 
        'response_text': "According to the context, Nancy is not explicitly mentioned as a specific character in the story..."
    }
    
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                FASTAPI_URL,
                params={"query_text": question},
                timeout=300.0,
            )
            if response.status_code == 200:
                response_obj = response.json()
                logger.info(f"Backend Answer: {response_obj}")
                return response_obj
        except httpx.RequestError:
            return "Ошибка: не удалось подключиться к серверу."

# Обработка команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "Привет! Я бот CatSearch и я отвечаю на вопросы по внутренней базе знаний. Задай вопрос, и я найду ответ. Примеры:"
    examples_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Что ты знаешь про Нэнси?", callback_data="sample_1")],
        [InlineKeyboardButton("Назови лучшие экспонаты Лувра!", callback_data="sample_2")],
        [InlineKeyboardButton("Кто совершил хладнокровное убийство?", callback_data="sample_3")],
    ])
    await update.message.reply_text(text, reply_markup=examples_keyboard)
    return QUESTION

# Обработка выбора "Задать вопрос"
async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "Привет! Задай вопрос, и я найду ответ. Примеры:"
    examples_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Что ты знаешь про Нэнси?", callback_data="sample_1")],
        [InlineKeyboardButton("Назови лучшие экспонаты Лувра!", callback_data="sample_2")],
        [InlineKeyboardButton("Кто совершил хладнокровное убийство?", callback_data="sample_3")],
    ])
    await update.message.reply_text(text, reply_markup=examples_keyboard)
    return QUESTION

# Обработка текстового вопроса
async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question: str = ''
    if update and update.message:
        question = update.message.text
    else:
        question = context.user_data['current_question']

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, 
        action=ChatAction.TYPING
    )
    await update.message.reply_text("🔍 Ищу ответ...")

    answer: dict = await fetch_answer(question)

    await update.message.reply_text(
        "🤖 Ответ: " + answer.get("response_text", "Ошибка: ответ не распознан."), 
        # reply_markup=keyboard,
        )
    
    rag_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("RAG Вопрос 1", callback_data="rag_callback")],
        [InlineKeyboardButton("RAG Вопрос 2", callback_data="rag_callback")],
        [InlineKeyboardButton("RAG Вопрос 3", callback_data="rag_callback")],
    ])

    await update.message.reply_text(
        "🤖 Возможно вам будет интересно следующее: ",
        reply_markup=rag_keyboard,
        )

    return QUESTION

async def handle_sample_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Определите текст вопроса по callback_data
    sample_questions = {
        "sample_1": "Что ты знаешь про Нэнси?",
        "sample_2": "Назови лучшие экспонаты Лувра\!",
        "sample_3": "Кто совершил хладнокровное убийство?"
    }
    question = sample_questions.get(query.data, "Неизвестный вопрос")

    context.user_data['current_question'] = question  # Сохраняем вопрос в контексте

    await query.edit_message_text(f"🔍 Ищу ответ на вопрос: *{question}*", parse_mode="MarkdownV2")
    
    # Эмулируем ввод вопроса пользователем
    # return await handle_question(update, context)

    answer: dict = await fetch_answer(question)

    await query.edit_message_text(
        f"Вопрос: {question}" \
        + "\n\n" \
        "🤖 Ответ: " + answer.get("response_text", "Ошибка: ответ не распознан."), 
        )
    
    rag_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("RAG Вопрос 1", callback_data="rag_callback")],
        [InlineKeyboardButton("RAG Вопрос 2", callback_data="rag_callback")],
        [InlineKeyboardButton("RAG Вопрос 3", callback_data="rag_callback")],
    ])

    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="🤖 Возможно вам будет интересно следующее: ", 
        reply_markup=rag_keyboard)

    return QUESTION


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
    try:
        app = Application.builder().token(BOT_TOKEN).build()
    except InvalidToken:
        logger.error("❌ Неверный токен. Используйте переменную окружения BOT_TOKEN.")
        exit(1)

    # ConversationHandler для управления диалогом
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            # START: [MessageHandler(filters.Regex("^Задать вопрос$"), ask_question)],
            QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question),
                CallbackQueryHandler(handle_sample_questions, pattern="^sample_"),  # Обработчик для примеров
                CallbackQueryHandler(cancel, pattern="^cancel"),
            ],
            CONTINUE: [
                MessageHandler(filters.Regex("^Новый вопрос$"), continue_conversation),
                MessageHandler(filters.Regex("^Завершить$"), cancel),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=True,
    )

    app.add_handler(conv_handler)
    logger.info("Bot started")

    app.run_polling()

if __name__ == "__main__":
    main()