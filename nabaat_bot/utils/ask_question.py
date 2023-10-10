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
# Constants for ConversationHandler states
PREDEFINED_QUESTIONS = [
    "لطفا <a href='https://telegra.ph/%D8%B4%D8%B1%D8%A7%DB%8C%D8%B7-%D8%A7%D8%B3%D8%AA%D9%81%D8%A7%D8%AF%D9%87-%D8%A7%D8%B2-%D9%86%D8%A8%D8%A7%D8%AA-10-10-2'>آیین‌نامه</a> نبات را مطالعه کنید\n\n",
    'لطفا مشکل اصلی خود را مطرح کنید',
    'pictures?',
    'additional-info'
]
(
    MAIN_QUESTION,
    Q3,
    GET_PICTURES,
    HANDLE_PICTURES,
    ADDITIONAL_INFO,
    HANDLE_INFO   
) = range(6)

async def show_disclaimer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data
    db.log_activity(user.id, "started to ask a question")
    user_wip_doc = db.wip_questions.find_one({"_id": user.id})
    if not user_wip_doc:
        user_data["question-name"] = "question1"
    elif user_wip_doc.get("question1") and user_wip_doc.get("question2"):
        reply_text = """
شما دو سوال ثبت کرده‌اید. لطفا پیش از ثبت سوال جدید، منتظر پاسخ کارشناس به سوالات قبلی بمانید.
"""
        await update.message.reply_text(reply_text, reply_markup=start_keyboard())
        return ConversationHandler.END
    elif not user_wip_doc.get("question1"):
        user_data["question-name"] = "question1"
    elif not user_wip_doc.get("question2"):
        user_data["question-name"] = "question2"
    logger.info(f"{user.id} started a question")
    if not db.check_if_user_is_registered(user_id=user.id):
        db.log_activity(user.id, "error - start question", "not registered yet")
        await update.message.reply_text(
            "لطفا پیش از ارسال سوال، از طریق /start ثبت نام کنید",
            reply_markup=register_keyboard(),
        )
        return ConversationHandler.END
    reply_text = PREDEFINED_QUESTIONS[0]
    await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML,reply_markup=disclaimer_keyboard())
    #
    return MAIN_QUESTION

async def main_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data
    if update.message.text == "بازگشت":
        db.log_activity(user.id, "back")
        await update.message.reply_text("عمیلات لغو شد", reply_markup=start_keyboard())
        return ConversationHandler.END
    if update.message.text in MENU_CMDS or update.message.text == "قبول نمی‌کنم":
        db.log_activity(user.id, "error - answer in menu_cmd list", update.message.text)
        await update.message.reply_text("عمیلات لغو شد.", reply_markup=start_keyboard())
        return ConversationHandler.END
    if update.message.text == "قبول نمی‌کنم":
        db.log_activity(user.id, "declined disclaimer", update.message.text)
        await update.message.reply_text("عمیلات لغو شد.", reply_markup=start_keyboard())
        return ConversationHandler.END
    elif update.message.text == "آیین‌نامه را خواندم و قبول می‌کنم":
        answer1 = update.message.text
        db.log_activity(user.id, "accepted disclaimer")
        reply_text = PREDEFINED_QUESTIONS[1]
        await update.message.reply_text(reply_text, reply_markup=back_button())
        return GET_PICTURES
    else:
        return ConversationHandler.END 

async def get_pictures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data
    if update.message.text == "بازگشت":
        db.log_activity(user.id, "back")
        reply_text = PREDEFINED_QUESTIONS[0]
        await update.message.reply_text(reply_text, reply_markup=disclaimer_keyboard())
        return MAIN_QUESTION
    if update.message.text in MENU_CMDS:
        db.log_activity(user.id, "error - answer in menu_cmd list", update.message.text)
        await update.message.reply_text("عمیلات قبلی لغو شد. لطفا دوباره تلاش کنید.", reply_markup=start_keyboard())
        return ConversationHandler.END
    if not update.message.text:
        db.log_activity(user.id, "error - no answer received to q3")
        reply_text = PREDEFINED_QUESTIONS[1]
        await update.message.reply_text(reply_text, reply_markup=back_button())
        return MAIN_QUESTION
    answer = update.message.text
    # db.wip_questions.update_one({"_id": user.id}, {"$set": {PREDEFINED_QUESTIONS[1]: answer}})
    user_data['answer'] = answer
    db.log_activity(user.id, "answer received to main question", answer)
    db.add_new_question(user.id, user_data["question-name"], PREDEFINED_QUESTIONS[1], answer)
    timestamp = datetime.datetime.now().strftime("%Y%m%d %H:%M")
    db.wip_questions.update_one({"_id": user.id}, 
                                {"$set": {f"{user_data['question-name']}.timestamp": timestamp}})
    # index = db.current_question_index(user.id)
    # db.set_user_attribute(user.id, f"questions[{index}].{PREDEFINED_QUESTIONS[2]}", answer3)
    reply_text = PREDEFINED_QUESTIONS[2]
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
        reply_text = PREDEFINED_QUESTIONS[1]
        await update.message.reply_text(reply_text, reply_markup=back_button())
        return GET_PICTURES

    if message_text == 'پایان':
        db.log_activity(user.id, "finished sending pictures")
        reply_text = PREDEFINED_QUESTIONS[3]
        await update.message.reply_text(reply_text, reply_markup=back_button())
        return ADDITIONAL_INFO
    
    if message_photo:
        message_id = update.message.id
        db.log_activity(user.id, "sent a picture", str(message_id))
        user_data['message_ids'].append(message_id)
        db.wip_questions.update_one({"_id": user.id}, {"$push": {f"{user_data['question-name']}.picture-id": message_id}})
        reply_text = "در صورتی که تصویر دیگری ندارید بنویسید 'پایان' در غیر این صورت تصویر ارسال کنید"
        await update.message.reply_text(reply_text)
        return HANDLE_PICTURES

    if not update.message.photo and message_text != 'پایان':
        reply_text = "در صورتی که تصویر دیگری ندارید بنویسید 'پایان' در غیر این صورت تصویر ارسال کنید"
        await update.message.reply_text(reply_text, reply_markup=back_button())
        return HANDLE_PICTURES

async def additional_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data
    message_text = update.message.text

    if message_text == "بازگشت":
        db.log_activity(user.id, "back")
        reply_text = PREDEFINED_QUESTIONS[2]
        await update.message.reply_text(reply_text, reply_markup=back_button())
        return HANDLE_PICTURES

    if message_text in MENU_CMDS:
        db.log_activity(user.id, "error - answer in menu_cmd list", update.message.text)
        await update.message.reply_text("عمیلات قبلی لغو شد. لطفا دوباره تلاش کنید.", reply_markup=start_keyboard())
        return ConversationHandler.END
    
    if message_text == "پایان":
        db.log_activity(user.id, "finished asking question")
        reply_text = "سوال شما ثبت شد. لطفا منتظر پاسخ کارشناس باشید."
        await update.message.reply_text(reply_text, reply_markup=start_keyboard())
        context.job_queue.run_once(send_question_to_expert, when=10, chat_id=user.id, data=user.username)
        return ConversationHandler.END

    if message_text and message_text != "پایان":
        db.log_activity(user.id, "entered additional info")
        added_info = message_text
        db.wip_questions.update_one({"_id": user.id}, {"$set": {f"{user_data['question-name']}.additional-information": added_info}})
        reply_text = "سوال شما ثبت شد. لطفا منتظر پاسخ کارشناس باشید."
        await update.message.reply_text(reply_text, reply_markup=start_keyboard())
        context.job_queue.run_once(send_question_to_expert, when=10, chat_id=user.id, 
                                   data={"username":user.username, "question-name":user_data["question-name"]})
        return ConversationHandler.END

    if not message_text:
        db.log_activity(user.id, "error - additional info had no text")
        reply_text = "اگه اطلاعات دیگری نداری بنویس پایان"
        await update.message.reply_text(reply_text)
        return ADDITIONAL_INFO

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات کنسل شد!")
    return ConversationHandler.END


ask_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('👨‍🌾 ارسال سوال'), show_disclaimer)],
        states={
            MAIN_QUESTION: [MessageHandler(~filters.COMMAND, main_question)],
            # Q3: [MessageHandler(~filters.COMMAND, q3)],
            GET_PICTURES: [MessageHandler(~filters.COMMAND, get_pictures)],
            HANDLE_PICTURES: [MessageHandler(~filters.COMMAND, handle_pictures)],
            ADDITIONAL_INFO: [MessageHandler(~filters.COMMAND, additional_info)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )