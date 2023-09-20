from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import random
import database
from .logger import logger

db = database.Database()

async def send_question_to_expert(context: ContextTypes.DEFAULT_TYPE):
    customer_id = context.job.chat_id
    customer_username = context.job.data
    experts = db.get_experts()
    chosen_expert = random.choice(list(experts.keys()))
    group_id = experts[chosen_expert]
    res = await context.bot.create_forum_topic(chat_id=group_id, name=f"@{customer_username} | {customer_id}")
    logger.info(f"topic-id: {res.message_thread_id}")
    db.wip_questions.update_one({"_id": customer_id}, {"$set": {"topic-id": res.message_thread_id}})
    question = db.wip_questions.find_one( {"_id": customer_id} )
    question_list = db.bot_collection.find_one( {"name": "questions-list"} )["questions"]
    text = ""
    for q in question_list:
        answer = question.get(q)
        text = text + "\n" + f"{q}: {answer}"
    await context.bot.send_message(chat_id=group_id, text=text, message_thread_id=res.message_thread_id)
    photo_ids = question.get("picture-id")
    if photo_ids:
        for photo in photo_ids:
            await context.bot.forward_message(group_id, from_chat_id=customer_id, message_id=photo, message_thread_id=res.message_thread_id)
    else:
        context.bot.send_message(chat_id=group_id, text="user didn't send any photos", message_thread_id=res.message_thread_id)

# async def expert_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     args = context.args
#     user_data = context.user_data
#     expert_id = update.effective_user.id
#     if not args or len(args)!=1:
#         reply_text = """
# نحوه استفاده:
# /send ID
# ID مشتری را از عنوان تاپیک بردار
# """
#         await context.bot.send_message(chat_id=expert_id, text=reply_text)
#         return ConversationHandler.END
#     customer_id = int(args[0])
#     if not db.check_if_user_exists(customer_id):
#         reply_text = """
# این ID در دیتابیس موجود نیست.
# """
#         await context.bot.send_message(chat_id=expert_id, text=reply_text)
#         return ConversationHandler.END
#     user_data["customer_id"] = customer_id
    
#     return SEND

# async def expert_send(update: Update, context: ContextTypes.DEFAULT_TYPE):