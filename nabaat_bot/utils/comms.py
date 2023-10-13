from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from telegram.error import Forbidden, BadRequest
import random
import html
import json

import database

from .logger import logger
from .keyboards import expert_keyboard
from .polls import create_poll

db = database.Database()

# Conversation states
RECEIVE_MESSAGE = range(1)

async def send_question_to_expert(context: ContextTypes.DEFAULT_TYPE):
    customer_id = context.job.chat_id
    customer_username = context.job.data["username"]
    question_name = context.job.data["question-name"]
    experts = db.get_experts()
    chosen_expert = random.choice(list(experts.keys()))
    db.wip_questions.update_one({"_id": customer_id}, {"$set": {f"{question_name}.expert-id": int(chosen_expert)}})
    group_id = experts[chosen_expert]
    res = await context.bot.create_forum_topic(chat_id=group_id, name=f"{customer_id} | #{question_name[-1]}")
    # logger.info(f"topic-id: {res.message_thread_id}")
    db.wip_questions.update_one({"_id": customer_id}, {"$set": {f"{question_name}.topic-id": res.message_thread_id}})
    question = db.wip_questions.find_one( {"_id": customer_id} )
    question_list = db.bot_collection.find_one( {"name": "questions-list"} )["questions"]
    text = f"username: @{customer_username}\n"
    for q in question_list:
        answer = question[question_name].get(q)
        text = text + "\n" + f"{q}: {answer}"
    cmd_guide = """
تماس با کاربر با دستورات زیر:
<b>سوال پرسیدن از کاربر با ارسال دستور /msg</b>
<b>ارسال توصیه نهایی به کاربر با ارسال دستور /advise</b>
"""
    await context.bot.send_message(chat_id=group_id, text=cmd_guide, message_thread_id=res.message_thread_id, parse_mode=ParseMode.HTML)
    await context.bot.send_message(chat_id=group_id, text=text, message_thread_id=res.message_thread_id)
    photo_ids = question[question_name].get("picture-id")
    if photo_ids:
        for photo in photo_ids:
            await context.bot.forward_message(group_id, from_chat_id=customer_id, message_id=photo, message_thread_id=res.message_thread_id)
    else:
        await context.bot.send_message(chat_id=group_id, text="user didn't send any photos", message_thread_id=res.message_thread_id)

async def ask_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    expert_id = update.effective_user.id
    experts = db.get_experts()
    group_id = experts[str(expert_id)]
    topic_id = update.message.message_thread_id
    topic_name = update.message.reply_to_message.forum_topic_created.name
    customer_id = int(topic_name.split(" | #")[0])
    question_num = topic_name.split(" | #")[1]
    if str(expert_id) not in experts:
        await context.bot.send_message(chat_id=group_id, text="تنها کارشناسان قادر به استفاده از این دستور هستند.", message_thread_id=topic_id)
        return ConversationHandler.END
    if not db.check_if_user_exists(customer_id):
        reply_text = """
این ID در دیتابیس موجود نیست.
"""
        await context.bot.send_message(chat_id=group_id, text=reply_text, message_thread_id=topic_id)
        return ConversationHandler.END
    question_doc = db.wip_questions.find_one({"_id": customer_id})
    if not question_doc:
        reply_text = """
این کاربر سوال فعالی ندارد.
"""
        await context.bot.send_message(chat_id=group_id, text=reply_text, message_thread_id=topic_id)
        return ConversationHandler.END
    user_data["customer_id"] = customer_id
    user_data["question_num"] = question_num
    reply_text = "از کاربر سوال بپرس:\n\nلغو با /cancel"
    await context.bot.send_message(chat_id=group_id, text=reply_text, message_thread_id=topic_id)
    return RECEIVE_MESSAGE

async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    customer_id = user_data["customer_id"]
    question_num = user_data["question_num"]
    expert_id = update.effective_user.id
    experts = db.get_experts()
    group_id = experts[str(expert_id)]
    topic_id = update.message.message_thread_id
    if update.message.text:
        message = update.message.text
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("پاسخ به کارشناس", callback_data=f"reply_button{question_num}")]])
        try:
            await context.bot.send_message(chat_id=customer_id, text= "سوال کارشناس نبات:\r\n\r\n" + f"<pre>{message}</pre>", parse_mode=ParseMode.HTML)
            await context.bot.send_message(chat_id=customer_id, text="برای پاسخ به کارشناس از دکمه زیر استفاده کنید", reply_markup=markup)
            await context.bot.send_message(chat_id=group_id, text="سوال شما به کاربر ارسال شد.", 
                                           message_thread_id=topic_id)
            db.wip_questions.update_one({"_id": customer_id},
                                        {"$push": {f"question{question_num}.messages": {"expert": message}}})
        except Forbidden or BadRequest:
            await context.bot.send_message(chat_id=group_id, text="Couldn't send the message:\n1-User blocked the bot or\n2-User not found", 
                                           message_thread_id=topic_id)
            db.wip_questions.update_one({"_id": customer_id},
                                        {"$push": {f"question{question_num}.messages": {"expert": "message not sent"}}})
        finally:            
            return ConversationHandler.END
    else:
        return ConversationHandler.END
    

async def final_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    expert_id = update.effective_user.id
    experts = db.get_experts()
    topic_id = update.message.message_thread_id
    group_id = experts[str(expert_id)]
    topic_name = update.message.reply_to_message.forum_topic_created.name
    customer_id = int(topic_name.split(" | #")[0])
    question_num = topic_name.split(" | #")[1]
    if str(expert_id) not in experts:
        await context.bot.send_message(chat_id=group_id, text="تنها کارشناسان قادر به استفاده از این دستور هستند.", message_thread_id=topic_id)
        return ConversationHandler.END
    if not db.check_if_user_exists(customer_id):
        reply_text = """
این ID در دیتابیس موجود نیست.
"""
        await context.bot.send_message(chat_id=group_id, text=reply_text, message_thread_id=topic_id)
        return ConversationHandler.END
    question_doc = db.wip_questions.find_one({"_id": customer_id})
    if not question_doc:
        reply_text = """
این کاربر سوال فعالی ندارد.
"""
        await context.bot.send_message(chat_id=group_id, text=reply_text, message_thread_id=topic_id)
        return ConversationHandler.END
    user_data["customer_id"] = customer_id
    user_data["question_num"] = question_num
    reply_text = "توصیه نهایی به کاربر؟\n\nلغو با /cancel"
    await context.bot.send_message(chat_id=group_id, text=reply_text, message_thread_id=topic_id)
    return RECEIVE_MESSAGE

async def receive_final_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    customer_id = user_data["customer_id"]
    question_num = user_data["question_num"]
    expert_id = update.effective_user.id
    experts = db.get_experts()
    group_id = experts[str(expert_id)]
    topic_id = update.message.message_thread_id
    if update.message.text:
        message = "پاسخ کارشناس نبات به سوال شما:\r\n" + f"<pre>{update.message.text}</pre>"
        # markup = InlineKeyboardMarkup([[InlineKeyboardButton("پاسخ به کارشناس", callback_data=f"reply_button{question_num}")]])
        try:
            await context.bot.send_message(chat_id=customer_id, text=message, parse_mode=ParseMode.HTML)
            db.wip_questions.update_one({"_id": customer_id},
                                        {"$push": {f"question{question_num}.messages": {"expert": message}}})
        except Forbidden or BadRequest:
            await context.bot.send_message(chat_id=group_id, text="Couldn't send the message:\n1-User blocked the bot or\n2-User not found", 
                                           message_thread_id=topic_id)
            db.wip_questions.update_one({"_id": customer_id},
                                        {"$push": {f"question{question_num}.messages": {"expert": "message not sent"}}})
        finally:            
            fin_id = db.move_question_to_finished_collection(customer_id)
            db.del_from_wip_collection(customer_id)
            poll_data = {
                "fin_document_id": fin_id,
            }
            try:
                await context.bot.close_forum_topic(chat_id=group_id, message_thread_id= topic_id)
            except:
                pass
            context.job_queue.run_once(create_poll, when=2, chat_id=customer_id, data=poll_data)
            return ConversationHandler.END
    else:
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات کنسل شد!")
    return ConversationHandler.END

expert_reply_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('msg', ask_message)],
    # entry_points=[MessageHandler(filters.Regex("^1$"), ask_message)],
    states={
        RECEIVE_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_message)]
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

final_advice_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('advise', final_message)],
    # entry_points=[MessageHandler(filters.Regex("^2$"), final_message)],
    states={
        RECEIVE_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_final_message)]
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)