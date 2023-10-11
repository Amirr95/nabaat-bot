import datetime
from telegram import (
    Update
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler, 
    MessageHandler,
    filters
)
from telegram.constants import ParseMode
from telegram.error import Forbidden, BadRequest
from telegram.warnings import PTBUserWarning

import warnings
import random
import string

import database
from .logger import logger
from .keyboards import start_keyboard, register_keyboard

warnings.filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)
db = database.Database()

# Conversation states
RECEIVE_CUSTOMER_MESSAGE = range(1)


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
از اینکه به پلتفرم مشاوره کشاورزی نبات اعتماد کردید از شما سپاسگذاریم.
لطفا با انتخاب گزینه «✍️ ثبت نام»، اطلاعات خواسته شده را وارد کنید.
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
سلام
از اینکه به پلتفرم مشاوره کشاورزی نبات اعتماد کردید از شما سپاسگذاریم.
می‌توانید با انتخاب گزینه «👨‍🌾 ارسال سوال»، سوال خود را با کارشناسان ما مطرح کنید. 
                """
        await update.message.reply_text(reply_text, reply_markup=start_keyboard())
        return ConversationHandler.END


async def about_us(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    reply_text = """
<b><a href='https://telegra.ph/%D8%AF%D8%B1%D8%A8%D8%A7%D8%B1%D9%87-%D9%86%D8%A8%D8%A7%D8%AA-10-11'>درباره نبات\r\n\r\n</b>


"""
    await update.message.reply_text(reply_text, reply_markup=start_keyboard, parse_mode=ParseMode.HTML)


async def reply_to_expert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_data = update.callback_query.data
    user_data = context.user_data
    if query_data.startswith("reply_button"):
        user_id = update.callback_query.message.chat.id
        question_num = query_data[-1]
        user_data["question_num"] = question_num
        await context.bot.send_message(chat_id=user_id, text="پاسخ خود به کارشناس را وارد کنید")
        return RECEIVE_CUSTOMER_MESSAGE


async def receive_customer_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data
    question_num = user_data["question_num"]
    # logger.i/nfo(update)
    question_doc = db.wip_questions.find_one( {'_id': user.id})
    expert_id = question_doc[f"question{question_num}"]["expert-id"]
    group_id = db.get_experts()[str((expert_id))]
    topic_id = question_doc[f"question{question_num}"]["topic-id"]
    if update.message:
        message_id = update.message.id
        await context.bot.forward_message(chat_id=group_id, from_chat_id=user.id, message_id=message_id, message_thread_id=topic_id)
        if update.message.text:
            db.wip_questions.update_one({"_id": user.id},
                                        {"$push": {f"question{question_num}.messages": {"customer": update.message.text}}})
        elif update.message.photo:
            db.wip_questions.update_one({"_id": user.id},
                                        {"$push": {f"question{question_num}.picture-id": message_id}})

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات کنسل شد!")
    return ConversationHandler.END


customer_reply_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(reply_to_expert, )],
    states={
        RECEIVE_CUSTOMER_MESSAGE: [MessageHandler(~filters.COMMAND, receive_customer_message)]
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)