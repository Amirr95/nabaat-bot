from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from telegram.error import Forbidden, BadRequest
import random
import database
from .logger import logger

db = database.Database()

# Conversation states
RECEIVE_MESSAGE = range(1)

async def send_question_to_expert(context: ContextTypes.DEFAULT_TYPE):
    customer_id = context.job.chat_id
    customer_username = context.job.data["username"]
    question_name = context.job.data["question-name"]
    experts = db.get_experts()
    chosen_expert = random.choice(list(experts.keys()))
    db.wip_questions.update_one({"_id": 103465015}, {"$set": {f"{question_name}.expert-id": int(chosen_expert)}})
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
    await context.bot.send_message(chat_id=group_id, text=text, message_thread_id=res.message_thread_id)
    photo_ids = question[question_name].get("picture-id")
    if photo_ids:
        for photo in photo_ids:
            await context.bot.forward_message(group_id, from_chat_id=customer_id, message_id=photo, message_thread_id=res.message_thread_id)
    else:
        await context.bot.send_message(chat_id=group_id, text="user didn't send any photos", message_thread_id=res.message_thread_id)

async def ask_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user_data = context.user_data
    expert_id = update.effective_user.id
    experts = db.get_experts()
    group_id = experts[str(expert_id)]
    topic_id = update.message.message_thread_id
    # logger.info(f"type: {update.effective_chat.type}")
    if not args or len(args)!=2:
        reply_text = """
نحوه استفاده:
/ask ID question-number
example: /ask 103465015 1
ID مشتری و شماره سوال را از عنوان تاپیک بردار
"""
        await context.bot.send_message(chat_id=group_id, text=reply_text, message_thread_id=topic_id)
        return ConversationHandler.END
    customer_id = int(args[0])
    question_num = args[1]
    if not db.check_if_user_exists(customer_id):
        reply_text = """
این ID در دیتابیس موجود نیست.
"""
        await context.bot.send_message(chat_id=group_id, text=reply_text, message_thread_id=topic_id)
        return ConversationHandler.END
    user_data["customer_id"] = customer_id
    user_data["question_num"] = question_num
    reply_text = "چی میخوای به مشتری بگی؟"
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
            await context.bot.send_message(chat_id=customer_id, text=message, reply_markup=markup)
            db.wip_questions.update_one({"_id": customer_id},
                                        {"$push": {f"question{question_num}.messages": {"expert": message}}})
        except Forbidden or BadRequest:
            await context.bot.send_message(chat_id=group_id, text="Couldn't send the message:\n1-User blocked the bot or\n2-User not found", 
                                           message_thread_id=topic_id)
        finally:            
            return ConversationHandler.END
    else:
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات کنسل شد!")
    return ConversationHandler.END

expert_reply_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('ask', ask_message)],
    states={
        RECEIVE_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_message)]
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)