import logging
from logging.handlers import RotatingFileHandler
import datetime
from telegram import Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes,
    ApplicationBuilder
)
from telegram.constants import ParseMode
from telegram.error import NetworkError
import os
import warnings
import html
import json
import traceback

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    encoding="utf-8",
    level=logging.INFO,
    handlers=[
        RotatingFileHandler(
            "bot_logs.log", maxBytes=512000, backupCount=5
        ),  # File handler to write logs to a file
        logging.StreamHandler(),  # Stream handler to display logs in the console
    ],
)
logger = logging.getLogger("nabaat-bot")
logging.getLogger("httpx").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=UserWarning)

# Constants for ConversationHandler states
TOKEN = os.environ["AGRIWEATHBOT_TOKEN"]
ADMIN_LIST = [103465015, 31583686, 391763080, 216033407, 5827206050]
GROUP_IDS = [-1001893146969]
###################################################################
###################################################################
async def create_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = await context.bot.create_forum_topic(chat_id=GROUP_IDS[0], name=str(update.effective_user.id))
    await context.bot.send_message(chat_id=ADMIN_LIST[0], text=res)
    await context.bot.send_message(chat_id=ADMIN_LIST[0], text=dir(res))
    # await context.bot.send_message(chat_id=GROUP_IDS[0], text="test message to threadID:81", message_thread_id=81)

async def group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # if update.message.chat.type=='group':
    await context.bot.send_message(chat_id=103465015, text=f"update: {update}")
    await context.bot.forward_message(chat_id=103465015, from_chat_id=update.message.chat_id, message_id=update.message.message_id)

# Fallback handlers
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error('Update "%s" caused error "%s"', update, context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f"An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    # Finally, send the message
    await context.bot.send_message(
        chat_id=103465015, text=message, parse_mode=ParseMode.HTML
    )

def main():
    proxy_url = 'http://127.0.0.1:8889'
    # application = ApplicationBuilder().token(TOKEN).build()
    application = ApplicationBuilder().token(TOKEN).proxy_url(proxy_url).get_updates_proxy_url(proxy_url).build()
    # Add handlers to the application
    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler('start', create_topic))
    # application.add_handler(MessageHandler(filters.ALL, group_handler))

    
    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    try:
        main()
    except NetworkError:
        logger.error("A network error was encountered!")
    except ConnectionRefusedError:
        logger.error("A ConnectionRefusedError was encountered!")
