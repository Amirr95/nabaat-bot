import datetime
import random

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
from .keyboards import *
from .comms import send_question_to_expert
from .logger import logger
from .resumes import *


MENU_CMDS = ['✍️ ثبت نام', '📤 دعوت از دیگران', '🖼 مشاهده باغ ها', '➕ اضافه کردن باغ', '🗑 حذف باغ ها', '✏️ ویرایش باغ ها', '🌦 درخواست اطلاعات هواشناسی', '/start', '/stats', '/send', '/set']

db = database.Database()
# Constants for ConversationHandler states
PREDEFINED_QUESTIONS = [
    "<a href='https://telegra.ph/%D8%B4%D8%B1%D8%A7%DB%8C%D8%B7-%D8%A7%D8%B3%D8%AA%D9%81%D8%A7%D8%AF%D9%87-%D8%A7%D8%B2-%D9%86%D8%A8%D8%A7%D8%AA-10-10-2'>آیین‌نامه</a> استفاده از خدمات نبات را خوانده‌ام و آن را می‌پذیرم",
    'لطفا سوال یا مشکل اصلی خود را مطرح کنید',
    'لطفا تعدادی عکس واضح از گیاه خود ارسال کنید که بیانگر مشکل و سوال شما باشد. در صورتی که عکس ندارید برای رفتن به مرحله بعد <b>/fin</b> را بزنید.',
    'اگر توضیح تکمیلی در خصوص سوال خود یا سوابق رسیدگی به زمین یا گیاه دارید بنویسید. در غیر این صورت روی <b>/fin</b> بزنید'
]
(
    MAIN_QUESTION,
    Q3,
    GET_PICTURES,
    HANDLE_PICTURES,
    ADDITIONAL_INFO,
    HANDLE_INFO,
    SELECT_EXPERT,
    HANDLE_SPECIALTIES,
    NEXT,
) = range(9)

async def show_disclaimer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data
    db.log_activity(user.id, "started to ask a question")
    user_wip_doc = db.wip_questions.find_one({"_id": user.id})
    if not user_wip_doc:
        user_data["question-name"] = "question1"
    elif user_wip_doc.get("question1"): # and user_wip_doc.get("question2"):
        reply_text = """
شما یک سوال ثبت کرده‌اید. لطفا پیش از ثبت سوال جدید، منتظر پاسخ کارشناس به سوال قبلی بمانید.
"""
        await update.message.reply_text(reply_text, reply_markup=start_keyboard())
        return ConversationHandler.END
    elif not user_wip_doc.get("question1"):
        user_data["question-name"] = "question1"
    # elif not user_wip_doc.get("question2"):
    #     user_data["question-name"] = "question2"
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
    user_data["main-question"] = ""
    if update.message.text == "بازگشت":
        db.log_activity(user.id, "back")
        await update.message.reply_text("عمیلات لغو شد", reply_markup=start_keyboard())
        return ConversationHandler.END
    if update.message.text in MENU_CMDS:
        db.log_activity(user.id, "error - answer in menu_cmd list", update.message.text)
        await update.message.reply_text("عمیلات لغو شد.", reply_markup=start_keyboard())
        return ConversationHandler.END
    if update.message.text == "قبول نمی‌کنم":
        db.log_activity(user.id, "declined disclaimer", update.message.text)
        await update.message.reply_text("عمیلات لغو شد.", reply_markup=start_keyboard())
        return ConversationHandler.END
    elif update.message.text == "آیین‌نامه را خواندم و قبول می‌کنم":
        db.log_activity(user.id, "accepted disclaimer")
        reply_text = 'کدام یک از تخصص های زیر مد نظر شماست؟'
        await update.message.reply_text(reply_text, reply_markup=specialties_keyboard())
        return HANDLE_SPECIALTIES
    else:
        reply_text = PREDEFINED_QUESTIONS[0]
        await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML,reply_markup=disclaimer_keyboard())
        return MAIN_QUESTION 

async def get_pictures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data
    if update.message.text == "بازگشت":
        db.log_activity(user.id, "back")
        reply_text = 'کدام یک از تخصص های زیر مد نظر شماست؟'
        await update.message.reply_text(reply_text, reply_markup=specialties_keyboard())
        return HANDLE_SPECIALTIES
    elif update.message.text in MENU_CMDS:
        db.log_activity(user.id, "error - answer in menu_cmd list", update.message.text)
        await update.message.reply_text("عمیلات قبلی لغو شد. لطفا دوباره تلاش کنید.", reply_markup=start_keyboard())
        return ConversationHandler.END
    elif not update.message.text:
        db.log_activity(user.id, "error - no answer received to q3")
        reply_text = PREDEFINED_QUESTIONS[1]
        await update.message.reply_text(reply_text, reply_markup=back_button())
        return MAIN_QUESTION
    elif update.message.text != "/fin":
        user_data["main-question"] = user_data["main-question"] + " " + update.message.text
        reply_text = "در صورتی که سوالتان ادامه ندارد <b>/fin</b> را بزنید و در غیر این‌صورت ادامه سوال خود را تایپ کنید."
        await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)
        return GET_PICTURES
    elif update.message.text == "/fin":
        user_question = user_data["main-question"]
        # db.wip_questions.update_one({"_id": user.id}, {"$set": {PREDEFINED_QUESTIONS[1]: answer}})
        db.log_activity(user.id, "received main question", user_question)
        db.add_new_question(user.id, user_data["question-name"], PREDEFINED_QUESTIONS[1], user_question)
        timestamp = datetime.datetime.now().strftime("%Y%m%d %H:%M")
        db.wip_questions.update_one({"_id": user.id}, 
                                    {"$set": {f"{user_data['question-name']}.timestamp": timestamp}})
        # index = db.current_question_index(user.id)
        # db.set_user_attribute(user.id, f"questions[{index}].{PREDEFINED_QUESTIONS[2]}", answer3)
        reply_text = PREDEFINED_QUESTIONS[2]
        await update.message.reply_text(reply_text, reply_markup=back_button(), parse_mode=ParseMode.HTML)
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

    if message_text == '/fin':
        db.log_activity(user.id, "finished sending pictures")
        reply_text = PREDEFINED_QUESTIONS[3]
        await update.message.reply_text(reply_text, reply_markup=back_button(), parse_mode=ParseMode.HTML)
        return ADDITIONAL_INFO
    
    if message_photo:
        message_id = update.message.id
        file_id = message_photo[3].file_id
        db.log_activity(user.id, "sent a picture", str(message_id))
        user_data['message_ids'].append(message_id)
        db.wip_questions.update_one({"_id": user.id}, {"$push": {f"{user_data['question-name']}.picture-id": message_id}})
        db.wip_questions.update_one({"_id": user.id}, {"$push": {f"{user_data['question-name']}.file-id": file_id}})
        reply_text = "در صورتی که تصویر دیگری ندارید <b>/fin</b> را بزنید. در غیر این صورت تصویر خود را ارسال کنید."
        await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)
        return HANDLE_PICTURES

    if not update.message.photo and message_text != '/fin':
        reply_text = "در صورتی که تصویر دیگری ندارید <b>/fin</b> را بزنید. در غیر این صورت تصویر خود را ارسال کنید."
        await update.message.reply_text(reply_text, reply_markup=back_button(), parse_mode=ParseMode.HTML)
        return HANDLE_PICTURES

async def additional_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data
    message_text = update.message.text

    if message_text == "بازگشت":
        db.log_activity(user.id, "back")
        reply_text = PREDEFINED_QUESTIONS[2]
        await update.message.reply_text(reply_text, reply_markup=back_button(), parse_mode=ParseMode.HTML)
        return HANDLE_PICTURES

    if message_text in MENU_CMDS:
        db.log_activity(user.id, "error - answer in menu_cmd list", update.message.text)
        await update.message.reply_text("عمیلات قبلی لغو شد. لطفا دوباره تلاش کنید.", reply_markup=start_keyboard())
        return ConversationHandler.END
    
    if message_text == "/fin":
        db.log_activity(user.id, "finished asking question")
        reply_text = "سوال شما با موفقیت ثبت شد.لطفا کارشناس مورد نظر خود را برای پاسخ به سوالتان انتخاب کنید"
        await update.message.reply_text(reply_text, reply_markup=select_expert_keyboard())
        return SELECT_EXPERT

    if message_text and message_text != "/fin":
        db.log_activity(user.id, "entered additional info")
        added_info = message_text
        key = "اطلاعات تکمیلی"
        db.wip_questions.update_one({"_id": user.id}, {"$set": {f"{user_data['question-name']}.{key}": added_info}})
        reply_text = "سوال شما با موفقیت ثبت شد.لطفا کارشناس مورد نظر خود را برای پاسخ به سوالتان انتخاب کنید"
        await update.message.reply_text(reply_text, reply_markup=select_expert_keyboard())
        return SELECT_EXPERT

    if not message_text:
        db.log_activity(user.id, "error - additional info had no text")
        reply_text = "اگر اطلاعات تکمیلی دیگری ندارید روی <b>/fin</b> بزنید."
        await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)
        return ADDITIONAL_INFO


async def select_expert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    specialty = context.user_data['specialty']

    if message_text == "مشاهده و انتخاب کارشناس":
        if specialty == 'nutrition':
            reply_text = nutrition[0]

        if specialty == 'gardening':
            reply_text = gardening[0]

        if specialty == 'green_house':
            reply_text = green_house[0]

        if specialty == 'garden':
            reply_text = garden[0]

        if specialty == 'agriculture':
            reply_text = agriculture[0]

        await update.message.reply_text(reply_text, reply_markup=next_button(), parse_mode=ParseMode.HTML)
        return NEXT

    if message_text == "انتخاب کارشناس توسط نبات":
        user = update.effective_user
        user_data = context.user_data
        specialty = context.user_data['specialty']

        if specialty == 'nutrition':
            expert = random.choice(nutrition).split('\n')[0]

        if specialty == 'gardening':
            expert = random.choice(gardening).split('\n')[0]

        if specialty == 'green_house':
            expert = random.choice(green_house).split('\n')[0]

        if specialty == 'garden':
            expert = random.choice(garden).split('\n')[0]

        if specialty == 'agriculture':
            expert = random.choice(agriculture).split('\n')[0]

        job_data = {"username": user.username, "question-name": user_data["question-name"], "expert": expert}
        context.user_data["expert"] = expert

        reply_text = "سوال شما به کارشناس ارسال گردید و در اسرع وقت مورد شما را بررسی میکنند و خدمتتون پیام میدهند"
        await update.message.reply_text(reply_text, reply_markup=start_keyboard(), parse_mode=ParseMode.HTML)
        context.job_queue.run_once(send_question_to_expert, when=1, chat_id=user.id, data=job_data)
        return ConversationHandler.END

    if message_text == "بازگشت":
        reply_text = PREDEFINED_QUESTIONS[3]
        await update.message.reply_text(reply_text, reply_markup=back_button(), parse_mode=ParseMode.HTML)
        return ADDITIONAL_INFO


async def next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text

    if message_text == 'بعدی':
        context.user_data['status'] += 1
        specialty = context.user_data['specialty']

        if specialty == 'nutrition':
            length = len(nutrition)

        if specialty == 'gardening':
            reply_text = gardening[context.user_data['status']]
            length = len(gardening)

        if specialty == 'green_house':
            length = len(green_house)

        if specialty == 'garden':
            length = len(garden)

        if specialty == 'agriculture':
            length = len(agriculture)

        if context.user_data['status'] < length:
            if specialty == 'gardening':
                reply_text = gardening[context.user_data['status']]

            if specialty == 'nutrition':
                reply_text = nutrition[context.user_data['status']]

            if specialty == 'green_house':
                reply_text = green_house[context.user_data['status']]

            if specialty == 'garden':
                reply_text = garden[context.user_data['status']]

            if specialty == 'agriculture':
                reply_text = agriculture[context.user_data['status']]

            context.user_data['expert'] = reply_text.split('\n')[0]
            await update.message.reply_text(reply_text, reply_markup=middle_button(), parse_mode=ParseMode.HTML)
            return NEXT

    if message_text == 'قبلی':
        context.user_data['status'] -= 1
        if context.user_data['status'] >= 0:
            specialty = context.user_data['specialty']

            if specialty == 'gardening':
                reply_text = gardening[context.user_data['status']]

            if specialty == 'nutrition':
                reply_text = nutrition[context.user_data['status']]

            if specialty == 'green_house':
                reply_text = green_house[context.user_data['status']]

            if specialty == 'garden':
                reply_text = garden[context.user_data['status']]

            if specialty == 'agriculture':
                reply_text = agriculture[context.user_data['status']]

            await update.message.reply_text(reply_text, reply_markup=middle_button(), parse_mode=ParseMode.HTML)
            return NEXT

    if message_text == "انتخاب کارشناس":
        user = update.effective_user
        user_data = context.user_data
        job_data = {"username": user.username, "question-name": user_data["question-name"], "expert": user_data["expert"]}

        reply_text = "کارشناس انتخابی شما با موفقیت ثبت شد و سوال شما برای ایشان ارسال خواهد شد"
        await update.message.reply_text(reply_text, reply_markup=start_keyboard(), parse_mode=ParseMode.HTML)
        context.job_queue.run_once(send_question_to_expert, when=1, chat_id=user.id, data=job_data)
        return ConversationHandler.END

    if message_text == "بازگشت":
        reply_text = 'سوال شما با موفقیت ثبت شد.لطفا کارشناس مورد نظر خود را برای پاسخ به سوالتان انتخاب کنید'
        await update.message.reply_text(reply_text, reply_markup=select_expert_keyboard(), parse_mode=ParseMode.HTML)
        return HANDLE_SPECIALTIES


async def handle_specialties(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    context.user_data['status'] = 0
    reply_text = PREDEFINED_QUESTIONS[1]

    if message_text == "علوم باغبانی":
        context.user_data['specialty'] = 'gardening'
        context.user_data['expert'] = gardening[0].split('\n')[0]
        await update.message.reply_text(reply_text, reply_markup=back_button(), parse_mode=ParseMode.HTML)
        return GET_PICTURES

    if message_text == "تغذیه گیاهی":
        context.user_data['specialty'] = 'nutrition'
        context.user_data['expert'] = nutrition[0].split('\n')[0]
        await update.message.reply_text(reply_text, reply_markup=back_button(), parse_mode=ParseMode.HTML)
        return GET_PICTURES

    if message_text == "گل خانه":
        context.user_data['specialty'] = 'green_house'
        context.user_data['expert'] = green_house[0].split('\n')[0]
        await update.message.reply_text(reply_text, reply_markup=back_button(), parse_mode=ParseMode.HTML)
        return GET_PICTURES

    if message_text == "باغ(درختان میوه)":
        context.user_data['specialty'] = 'garden'
        context.user_data['expert'] = garden[0].split('\n')[0]
        await update.message.reply_text(reply_text, reply_markup=back_button(), parse_mode=ParseMode.HTML)
        return GET_PICTURES

    if message_text == "زراعت و صیفی جات":
        context.user_data['specialty'] = 'agriculture'
        context.user_data['expert'] = agriculture[0].split('\n')[0]
        await update.message.reply_text(reply_text, reply_markup=back_button(), parse_mode=ParseMode.HTML)
        return GET_PICTURES

    if message_text == "بازگشت":
        reply_text = PREDEFINED_QUESTIONS[0]
        await update.message.reply_text(reply_text, reply_markup=disclaimer_keyboard(), parse_mode=ParseMode.HTML)
        return MAIN_QUESTION



async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات کنسل شد!")
    return ConversationHandler.END


ask_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('👨‍🌾 ارسال سوال'), show_disclaimer)],
        states={
            MAIN_QUESTION: [MessageHandler(~filters.COMMAND, main_question)],
            # Q3: [MessageHandler(~filters.COMMAND, q3)],
            GET_PICTURES: [MessageHandler(filters.COMMAND | filters.TEXT, get_pictures)],
            HANDLE_PICTURES: [MessageHandler(filters.ALL, handle_pictures)],
            ADDITIONAL_INFO: [MessageHandler(filters.ALL, additional_info)],
            SELECT_EXPERT: [MessageHandler(filters.ALL, select_expert)],
            HANDLE_SPECIALTIES: [MessageHandler(filters.ALL, handle_specialties)],
            NEXT: [MessageHandler(filters.ALL, next)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )