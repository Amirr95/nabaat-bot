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
from telegram.error import BadRequest, Forbidden
import warnings

import database
from .keyboards import register_keyboard, start_keyboard, back_button
from .logger import logger


MENU_CMDS = ['✍️ ثبت نام', '📤 دعوت از دیگران', '🖼 مشاهده باغ ها', '➕ اضافه کردن باغ', '🗑 حذف باغ ها', '✏️ ویرایش باغ ها', '🌦 درخواست اطلاعات هواشناسی', '/start', '/stats', '/send', '/set']

db = database.Database()
# Constants for ConversationHandler states
PREDEFINED_QUESTIONS = [
    'question 1',
    'question 2',
    'question 3',
    'pictures?',
    'additional info? else: پایان'
]
(
    Q2,
    Q3,
    GET_PICTURES,
    HANDLE_PICTURES,
    ADDITIONAL_INFO,
    HANDLE_INFO   
) = range(6)

async def q1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.log_activity(user.id, "started to ask a question")
    if not db.check_if_user_is_registered(user_id=user.id):
        db.log_activity(user.id, "error - add farm", "not registered yet")
        await update.message.reply_text(
            "لطفا پیش از ارسال سوال، از طریق /start ثبت نام کنید",
            reply_markup=register_keyboard(),
        )
        return ConversationHandler.END
    reply_text = PREDEFINED_QUESTIONS[0]
    await update.message.reply_text(reply_text, reply_markup=back_button())
    #
    return Q2

async def q2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data
    if update.message.text == "بازگشت":
        db.log_activity(user.id, "back")
        await update.message.reply_text("عمیلات لغو شد", reply_markup=start_keyboard())
        return ConversationHandler.END
    if update.message.text in MENU_CMDS:
        db.log_activity(user.id, "error - answer in menu_cmd list", update.message.text)
        await update.message.reply_text("عمیلات قبلی لغو شد. لطفا دوباره تلاش کنید.", reply_markup=start_keyboard())
        return ConversationHandler.END
    if not update.message.text:
        db.log_activity(user.id, "error - no answer received to q1")
        reply_text = PREDEFINED_QUESTIONS[0]
        await update.message.reply_text(reply_text, reply_markup=back_button())
        return Q2
    answer1 = update.message.text
    user_data['answer1'] = answer1
    db.add_new_question(user.id, PREDEFINED_QUESTIONS[0], answer1)
    reply_text = PREDEFINED_QUESTIONS[1]
    await update.message.reply_text(reply_text, reply_markup=back_button())
    return Q3

async def q3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data
    if update.message.text == "بازگشت":
        db.log_activity(user.id, "back")
        reply_text = PREDEFINED_QUESTIONS[0]
        await update.message.reply_text(reply_text, reply_markup=back_button())
        return Q2
    if update.message.text in MENU_CMDS:
        db.log_activity(user.id, "error - answer in menu_cmd list", update.message.text)
        await update.message.reply_text("عمیلات قبلی لغو شد. لطفا دوباره تلاش کنید.", reply_markup=start_keyboard())
        return ConversationHandler.END
    if not update.message.text:
        db.log_activity(user.id, "error - no answer received to q1")
        reply_text = PREDEFINED_QUESTIONS[1]
        await update.message.reply_text(reply_text, reply_markup=back_button())
        return Q3
    answer2 = update.message.text
    db.wip_questions_collection.update_one({"_id": user.id}, {"$set": {PREDEFINED_QUESTIONS[1]: answer2}})
    user_data['answer2'] = answer2
    # index = db.current_question_index(user.id)
    # db.set_user_attribute(user.id, f"questions.{index}.{PREDEFINED_QUESTIONS[1]}", answer2)
    logger.info(answer2)
    reply_text = PREDEFINED_QUESTIONS[2]
    await update.message.reply_text(reply_text, reply_markup=back_button())
    return GET_PICTURES

async def get_pictures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data
    if update.message.text == "بازگشت":
        db.log_activity(user.id, "back")
        reply_text = PREDEFINED_QUESTIONS[1]
        await update.message.reply_text(reply_text, reply_markup=back_button())
        return Q3
    if update.message.text in MENU_CMDS:
        db.log_activity(user.id, "error - answer in menu_cmd list", update.message.text)
        await update.message.reply_text("عمیلات قبلی لغو شد. لطفا دوباره تلاش کنید.", reply_markup=start_keyboard())
        return ConversationHandler.END
    if not update.message.text:
        db.log_activity(user.id, "error - no answer received to q3")
        reply_text = PREDEFINED_QUESTIONS[2]
        await update.message.reply_text(reply_text, reply_markup=back_button())
        return Q3
    answer3 = update.message.text
    db.wip_questions_collection.update_one({"_id": user.id}, {"$set": {PREDEFINED_QUESTIONS[2]: answer3}})
    user_data['answer3'] = answer3
    # index = db.current_question_index(user.id)
    # db.set_user_attribute(user.id, f"questions[{index}].{PREDEFINED_QUESTIONS[2]}", answer3)
    logger.info(answer3)
    reply_text = PREDEFINED_QUESTIONS[3]
    await update.message.reply_text(reply_text, reply_markup=back_button())
    return HANDLE_PICTURES

async def handle_pictures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message_text = update.message.text
    message_photo = update.message.photo
    user_data = context.user_data
    user_data['message_ids'] = []

    if update.message.text == "بازگشت":
        db.log_activity(user.id, "back")
        reply_text = PREDEFINED_QUESTIONS[2]
        await update.message.reply_text(reply_text, reply_markup=back_button())
        return GET_PICTURES

    if message_text == 'پایان':
        db.log_activity(user.id, "finished sending pictures")
        reply_text = PREDEFINED_QUESTIONS[4]
        await update.message.reply_text(reply_text, reply_markup=back_button())
        return ADDITIONAL_INFO
    
    if message_photo:
        message_id = update.message.id
        user_data['message_ids'].append(message_id)
        db.wip_questions_collection.update_one({"_id": user.id}, {"$push": {"picture-id": message_id}})
        logger.info(user_data['message_ids'])
        reply_text = "در صورتی که تصویر دیگری ندارید بنویسید 'پایان' در غیر این صورت تصویر ارسال کنید"
        await update.message.reply_text(reply_text)
        return HANDLE_PICTURES

    if not update.message.photo and message_text != 'پایان':
        reply_text = "در صورتی که تصویر دیگری ندارید بنویسید 'پایان' در غیر این صورت تصویر ارسال کنید"
        await update.message.reply_text(reply_text, reply_markup=back_button())
        return HANDLE_PICTURES

async def additional_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message_text = update.message.text

    if message_text == "بازگشت":
        reply_text = PREDEFINED_QUESTIONS[3]
        await update.message.reply_text(reply_text, reply_markup=back_button())
        return HANDLE_PICTURES

    if message_text in MENU_CMDS:
        db.log_activity(user.id, "error - answer in menu_cmd list", update.message.text)
        await update.message.reply_text("عمیلات قبلی لغو شد. لطفا دوباره تلاش کنید.", reply_markup=start_keyboard())
        return ConversationHandler.END
    
    if message_text == "پایان":
        db.log_activity(user.id, "finished asking a question")
        return ConversationHandler.END

    if message_text and message_text != "پایان":
        db.log_activity(user.id, "entered additional info")
        added_info = message_text
        logger.info(f"additional info: {added_info}")
        db.wip_questions_collection.update_one({"_id": user.id}, {"$set": {"additional-information": added_info}})
        reply_text = "سوال شما ثبت شد. لطفا منتظر پاسخ کارشناس باشید."
        await update.message.reply_text(reply_text)
        return ConversationHandler.END

    if not message_text :
        reply_text = "اگه اطلاعات دیگری نداری بنویس پایان"
        await update.message.reply_text(reply_text)
        return ADDITIONAL_INFO

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات کنسل شد!")
    return ConversationHandler.END


ask_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('👨‍🌾 ارسال سوال'), q1)],
        states={
            Q2: [MessageHandler(~filters.COMMAND, q2)],
            Q3: [MessageHandler(~filters.COMMAND, q3)],
            GET_PICTURES: [MessageHandler(~filters.COMMAND, get_pictures)],
            HANDLE_PICTURES: [MessageHandler(~filters.COMMAND, handle_pictures)],
            ADDITIONAL_INFO: [MessageHandler(~filters.COMMAND, additional_info)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )