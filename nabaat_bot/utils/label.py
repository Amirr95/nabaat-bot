import datetime
from telegram import (
    KeyboardButton,
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden
import warnings

import database
from .keyboards import register_keyboard, start_keyboard, disclaimer_keyboard, back_button
from .comms import send_question_to_expert
from .logger import logger


MENU_CMDS = ['✍️ ثبت نام', '📤 دعوت از دیگران', '🖼 مشاهده باغ ها', '➕ اضافه کردن باغ', '🗑 حذف باغ ها', '✏️ ویرایش باغ ها', '🌦 درخواست اطلاعات هواشناسی', '/start', '/stats', '/send', '/set']

db = database.Database()

(
    ASK_PRODUCT,
    HANDLE_LABELS
) = range(2)

async def ask_main_issue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    expert_id = update.effective_user.id
    experts = db.get_experts()
    topic_id = update.message.message_thread_id
    group_id = experts[str(expert_id)]
    topic_name = update.message.reply_to_message.forum_topic_created.name
    customer_id = int(topic_name.split(" | #")[0])
    # question_num = topic_name.split(" | #")[1]
    payload = {
        "expert_id": expert_id, 
        "topic_id": topic_id,
        "group_id": group_id,
        "customer_id": customer_id,
    }
    user_data.update(payload)
    question_doc = db.wip_questions.find_one({"_id": customer_id})
    if str(expert_id) not in experts:
        await context.bot.send_message(chat_id=group_id, text="تنها کارشناسان قادر به استفاده از این دستور هستند.", message_thread_id=topic_id)
        return ConversationHandler.END 
    if not db.check_if_user_exists(customer_id):
        reply_text = """
این ID در دیتابیس موجود نیست.
"""
        await context.bot.send_message(chat_id=group_id, text=reply_text, message_thread_id=topic_id)
        return ConversationHandler.END
    if not question_doc:
        reply_text = """
این کاربر سوال فعالی ندارد.
"""
        await context.bot.send_message(chat_id=group_id, text=reply_text, message_thread_id=topic_id)
        return ConversationHandler.END
    
    reply_text = """
لطفا برچسب مورد نظر برای مشکل اصلی این کاربر را وارد کنید.
لغو با فشردن /cancel
"""
    await context.bot.send_message(chat_id=group_id, text=reply_text, message_thread_id=topic_id)
    return ASK_PRODUCT

async def ask_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    main_issue = update.message.text
    try:
        if main_issue:
            user_data.update({"main-issue": main_issue})
            reply_text = """
    لطفا برچسب مورد نظر برای رقم محصول این کاربر را وارد کنید.
    لغو با فشردن /cancel
            """
            await context.bot.send_message(chat_id=user_data["group_id"], text=reply_text, message_thread_id=user_data["topic_id"])
            return HANDLE_LABELS
        else:
            reply_text = """
    عملیات لغو شد
            """
            await context.bot.send_message(chat_id=user_data["group_id"], text=reply_text, message_thread_id=user_data["topic_id"])
            return ConversationHandler.END
    except KeyError:
        reply_text = """
خطایی رخ داد. لظفا موضوع را به ادمین اطلاع دهید.
            """
        await context.bot.send_message(chat_id=user_data["group_id"], text=reply_text, message_thread_id=user_data["topic_id"])
        
async def handle_labels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    customer_product = update.message.text
    try:
        if customer_product:
            user_data.update({"customer-product": customer_product})
            db.wip_questions.update_one( {"_id": user_data["customer_id"]},
                                         {"$set": {"question1.expert-label.main-issue": user_data["main-issue"]}})
            db.wip_questions.update_one( {"_id": user_data["customer_id"]},
                                         {"$set": {"question1.expert-label.product": user_data["customer-product"]}})
            reply_text = """
لیبل‌ها با موفقیت اعمال شدند
"""
            await context.bot.send_message(chat_id=user_data["group_id"], text=reply_text, message_thread_id=user_data["topic_id"])
            return ConversationHandler.END
        else:
            reply_text = """
    عملیات لغو شد
            """
            await context.bot.send_message(chat_id=user_data["group_id"], text=reply_text, message_thread_id=user_data["topic_id"])
            return ConversationHandler.END
    except KeyError:
        reply_text = """
خطایی رخ داد. لظفا موضوع را به ادمین اطلاع دهید.
            """
        await context.bot.send_message(chat_id=user_data["group_id"], text=reply_text, message_thread_id=user_data["topic_id"])
        
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات کنسل شد!")
    return ConversationHandler.END


label_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("label", ask_main_issue, filters.ChatType.SUPERGROUP)],
        states={
            ASK_PRODUCT: [MessageHandler(~filters.COMMAND, ask_product)],
            HANDLE_LABELS: [MessageHandler(~filters.COMMAND & filters.TEXT, handle_labels)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )