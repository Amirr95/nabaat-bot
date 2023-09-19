import datetime
from telegram import (
    Update,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)
import warnings
import random
import string

import database
from .logger import logger
from .keyboards import start_keyboard, register_keyboard


db = database.Database()
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data
    # context.job_queue.run_once(no_farm_reminder, when=datetime.timedelta(hours=1), chat_id=user.id, data=user.username)    
    # Check if the user has already signed up
    if not db.check_if_user_is_registered(user_id=user.id):
        user_data["username"] = user.username
        user_data["blocked"] = False
        db.add_new_user(user_id=user.id, username=user.username)
        logger.info(f"{user.username} (id: {user.id}) started the bot.")
        reply_text = """
سلام
از این که به ما اعتماد کردید متشکریم.
برای ارسال سوال به کارشناسان ما، ابتدا ثبت نام خود را کامل کرده
و سپس سوال خود را بپرسید.
راه‌های ارتباطی با ما:
ادمین: @nabaatadmin
تلفن ثابت: 02164063410
                """
        args = context.args
        if args:
            db.log_token_use(user.id, args[0])
        await update.message.reply_text(reply_text, reply_markup=register_keyboard())
        # await update.message.reply_text("https://t.me/agriweath/48")  # introduction video to new users
        # context.job_queue.run_once(register_reminder, when=datetime.timedelta(hours=3), chat_id=user.id, data=user.username)    
        return ConversationHandler.END
    else:
        reply_text = """
باغدار عزیز سلام
از این که به ما اعتماد کردید متشکریم.
می‌توانید سوال خود را بپرسید 
راه‌های ارتباطی با ما:
ادمین: @agriiadmin
تلفن ثابت: 02164063410
                """
        await update.message.reply_text(reply_text, reply_markup=start_keyboard())
        return ConversationHandler.END

