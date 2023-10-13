from telegram import Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ApplicationBuilder,
    PollAnswerHandler
)
from telegram.constants import ParseMode
from telegram.error import NetworkError
import os
import warnings
import html
import json
import traceback

from utils.commands import start, about_us, customer_reply_conv_handler
from utils.register_conv import register_conv_handler
from utils.ask_question import ask_conv_handler
from utils.comms import expert_reply_conv_handler, final_advice_conv_handler
from utils.logger import logger
from utils.polls import assess_poll

warnings.filterwarnings(action="ignore", category=UserWarning)

# Constants for ConversationHandler states
# db = database.Database()
TOKEN = os.environ["AGRIWEATHBOT_TOKEN"]
# ADMIN_LIST = db.get_admins()
# GROUP_IDS = [-1001893146969]

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
    application.add_handler(CommandHandler('start', start, filters=filters.ChatType.PRIVATE))
    application.add_handler(MessageHandler(filters.Regex("^📬 درباره نبات$"), about_us))

    # application.add_handler(CommandHandler("poll", poll))
    application.add_handler(PollAnswerHandler(assess_poll))

    application.add_handler(ask_conv_handler)
    application.add_handler(register_conv_handler)
    application.add_handler(expert_reply_conv_handler)
    application.add_handler(final_advice_conv_handler)
    application.add_handler(customer_reply_conv_handler)
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
