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
MENU_CMD = db.get_menu_cmds()

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
<b>درباره نبات:</b>
مجموعه مشاوره کشاورزی نبات یک شرکت خصوصی دانش بنیان واقع در تهران است که با هدف ارتقا بهره‌وری و کاهش خسارت محصولات کشاورزی، ارتباط بین کشاورزان با متخصصین حوزه کشاورزی را برقرار کرده است. در نبات تعداد زیادی کارشناسان باتجربه و خبره در حوزه‌های باغداری، زراعت، صیفی‌جات و گلخانه در زمینه آفات، بیماری‌ها، تغذیه گیاهی و باغبانی وجود دارند.

با استفاده از نبات می‌توانید بدون نیاز به رفت و آمد و هزینه اضافی، تنها با استفاده از گوشی و ورود به بات تلگرامی نبات، ابتدا ثبت نام خود را به صورت کاملا رایگان انجام دهید و سپس سوال یا مشکل خود را به همراه عکس از گیاه ارسال کنید و جدیدترین توصیه‌های کاربردی را دریافت کنید.

با نبات می‌توانید علی رغم <b>هزینه معقول</b>، سالم‌ترین و باکیفیت‌ترین و بازارپسندترین میوه و محصول را داشته باشید و درختان و مزرعه شما سالم و عاری از هرگونه آفت و بیماری باشد.

ما باور داریم تخصص ما در کنار تجربه ارزشمند شما، کلید موفقیت هر دوی ما است.

"""
    await context.bot.send_message(chat_id=user.id, text=reply_text, reply_markup=start_keyboard(), parse_mode=ParseMode.HTML)
    db.log_activity(user.id, "viewed about us")


async def reply_to_expert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    query_data = query.data
    user_data = context.user_data
    if query_data.startswith("reply_button"):
        user_id = update.callback_query.message.chat.id
        db.log_activity(user_id, "pressed reply_button")
        question_num = query_data[-1]
        user_data["question_num"] = question_num
        await query.edit_message_text(text="پاسخ خود به کارشناس را وارد کنید")
        return RECEIVE_CUSTOMER_MESSAGE


async def receive_customer_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data
    question_num = user_data["question_num"]
    # logger.info(update)
    question_doc = db.wip_questions.find_one( {'_id': user.id})
    expert_id = question_doc[f"question{question_num}"]["expert-id"]
    group_id = db.get_experts()[str((expert_id))]
    topic_id = question_doc[f"question{question_num}"]["topic-id"]
    
    if update.message.text == "/fin":
        await context.bot.send_message(chat_id=user.id, text="پیام شما به کارشناس ارسال شد.")
        return ConversationHandler.END

    if update.message.text in MENU_CMD:
        pass

    if update.message:
        db.log_activity(user.id, "replied to expert", expert_id)
        message_id = update.message.id
        await context.bot.forward_message(chat_id=group_id, from_chat_id=user.id, message_id=message_id, message_thread_id=topic_id)
        await context.bot.send_message(chat_id=user.id, text="اگر پاسخ کارشناس را کامل کردید روی <b>/fin</b> بزنید و در غیر این صورت پاسخ خود را ادامه دهید.", parse_mode=ParseMode.HTML)
        if update.message.text:
            db.wip_questions.update_one({"_id": user.id},
                                        {"$push": {f"question{question_num}.messages": {"customer": update.message.text}}})
        elif update.message.photo:
            db.wip_questions.update_one({"_id": user.id},
                                        {"$push": {f"question{question_num}.picture-id": message_id}})
        return RECEIVE_CUSTOMER_MESSAGE
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات کنسل شد!")
    return ConversationHandler.END


customer_reply_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(reply_to_expert, pattern="^reply_button")],
    states={
        RECEIVE_CUSTOMER_MESSAGE: [MessageHandler(filters.ALL, receive_customer_message)]
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)