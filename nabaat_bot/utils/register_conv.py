from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from telegram.constants import ParseMode
import database
from .keyboards import (
    start_keyboard
)
import database

db = database.Database()

# Conversation states
ASK_PHONE, HANDLE_PHONE, HANDLE_LOCATION = range(3)
MENU_CMDS = ['✍️ ثبت نام', '📤 دعوت از دیگران', '🖼 مشاهده باغ ها', '➕ اضافه کردن باغ', '🗑 حذف باغ ها', '✏️ ویرایش باغ ها', '🌦 درخواست اطلاعات هواشناسی', '/start', '/stats', '/send', '/set']

# START OF REGISTER CONVERSATION
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.log_activity(user.id, "start register", f"{user.id} - username: {user.username}")
    if db.check_if_user_is_registered(user_id=user.id):
        await update.message.reply_text(
            "شما قبلا ثبت نام کرده‌اید. می‌توانید با استفاده از /start به ثبت باغ‌های خود اقدام کنید"
        )
        return ConversationHandler.END
    await update.message.reply_text(
        "لطفا نام و نام خانوادگی خود را وارد کنید \nلغو با /cancel", reply_markup=ReplyKeyboardRemove()
    )
    return ASK_PHONE

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.log_activity(user.id, "entered name", f"{update.message.text}")
    user_data = context.user_data
    # Get the answer to the area question
    if update.message.text in MENU_CMDS:
        db.log_activity(user.id, "error - answer in menu_cmd list", update.message.text)
        await update.message.reply_text("عمیلات قبلی لغو شد. لطفا دوباره تلاش کنید.", reply_markup=start_keyboard())
        return ConversationHandler.END
    if not update.message.text:
        await update.message.reply_text("لطفا نام و نام خانوادگی خود را وارد کنید \nلغو با /cancel")
        db.log_activity(user.id, "error - enter name", f"{update.message.text}")
        return ASK_PHONE
    name = update.message.text.strip()
    user_data["name"] = name
    db.set_user_attribute(user_id=user.id, key="name", value=name)
    await update.message.reply_text("لطفا شماره تلفن خود را وارد کنید: \nلغو با /cancel")
    return HANDLE_PHONE

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data
    # Get the answer to the area question
    phone = update.message.text
    if phone in MENU_CMDS:
        db.log_activity(user.id, "error - answer in menu_cmd list", phone)
        await update.message.reply_text("عمیلات قبلی لغو شد. لطفا دوباره تلاش کنید.", reply_markup=start_keyboard())
        return ConversationHandler.END
    if not phone or not phone.isdigit() or len(phone) != 11:
        db.log_activity(user.id, "error - entered phone", phone)
        await update.message.reply_text("شماره وارد شده مورد تایید نیست. لطفا دوباره شماره تلفن خود را وارد کنید: \nلغو با /cancel")
        return HANDLE_PHONE
    db.log_activity(user.id, "entered phone", phone)
    user_data["phone"] = phone
    db.set_user_attribute(user_id=user.id, key="phone-number", value=phone)
    reply_text = """
لطفا استان، شهرستان و روستای خود را بنویسید.
لغو با /cancel
    """
    await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)
    return HANDLE_LOCATION

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data
    # Get the answer to the area question
    address = update.message.text
    if address in MENU_CMDS:
        db.log_activity(user.id, "error - answer in menu_cmd list", address)
        await update.message.reply_text("عمیلات قبلی لغو شد. لطفا دوباره تلاش کنید.", reply_markup=start_keyboard())
        return ConversationHandler.END
    db.log_activity(user.id, "entered phone", address)
    user_data["address"] = address
    db.set_user_attribute(user_id=user.id, key="address", value=address)
    reply_text = """
ثبت‌نام شما تکمیل شد.
اکنون می‌توانید با انتخاب گزینه <b>(👨‍🌾 ارسال سوال)</b> مشکل اصلی خود را مطرح کنید.
    """
    keyboard = [['👨‍🌾 ارسال سوال']]

    await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True))
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات کنسل شد!")
    return ConversationHandler.END


register_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("✍️ ثبت نام"), register)],
        states={
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            HANDLE_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
            HANDLE_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_location)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )