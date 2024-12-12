from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telegram import Update
from telegram.constants import ParseMode
from dotenv import load_dotenv
import os
import logging

from core.emoji import get_random_emojis
from core.get_chat_history import get_chat_history
from core.save_message import save_message
from core.user import save_user, get_user_history
from core.yandex import YandexSummarize

load_dotenv()

logging.basicConfig(format='\n%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


async def message_handler(update: Update, context: CallbackContext) -> None:
    """
    Save the message to the chat history.
    
    This function is called when the user sends a message.
    It saves the message to the chat history file.
    """

    is_edited = update.edited_message is not None
    message = update.edited_message if is_edited else update.message

    save_message(message, is_edited)
    save_user(chat_id=message.chat_id, sender_id=message.from_user.id)

async def ping_handler(update: Update, context: CallbackContext) -> None:
    try:
        users = get_user_history(update.message.chat_id)["users"]

        reply = ""
        for user_id, emoji in zip(users, get_random_emojis(len(users))):
            reply += f'<a href="tg://user?id={user_id}">{emoji}</a>'

        await update.message.reply_text(reply, parse_mode=ParseMode.HTML)
    except Exception:
        await update.message.reply_text("Something went wrong while trying to ping users.")
        logger.exception("Error while trying to ping users.")
        return

async def summarize_handler(update: Update, context: CallbackContext) -> None:
    """
    Generate a summary of the chat history.

    This function is called when the user sends the /summary command.
    It retrieves the chat history and sends it to the summarization model.
    Then, it sends the generated summary to the chat.
    """

    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to a message with the /summarize command to get a brief summary of the messages sent after it.")
        return
    
    chat_id = update.message.chat_id
    from_message_id = update.message.reply_to_message.message_id

    try:
        messages = get_chat_history(chat_id, from_message_id)

        if not messages or len(messages) == 0:
            await update.message.reply_text("No messages found to summarize. Most likely bot was just added to the chat.")
            return
        
    except Exception:
        await update.message.reply_text("Something went wrong while trying to retrieve the chat history.")
        logger.exception("Error while trying to retrieve the chat history.")
        return

    try:
        source = ""
        for message in messages:
            source += f"{message["sender"]}: {message["message"]}\n"

        YANDEX_SESSION_ID = os.getenv("YANDEX_SESSION_ID")
        ya = YandexSummarize(YANDEX_SESSION_ID)
        summarized = await ya.generation(source)
        await update.message.reply_text(summarized, parse_mode=ParseMode.HTML)
    except Exception:
        await update.message.reply_text("Something went wrong while trying to summarize the chat history.")
        logger.exception("Error while trying to summarize the chat history.")
        return


def error_handler(update: Update, context: CallbackContext):
    """
    Log the error.

    This function is called when an error occurs.
    It logs the error to the console.
    """

    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    load_dotenv()
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    app.add_handler(CommandHandler("summarize", summarize_handler))
    app.add_handler(CommandHandler("ping", ping_handler))
    app.add_error_handler(error_handler)

    app.run_polling()

if __name__ == '__main__':
    main()
