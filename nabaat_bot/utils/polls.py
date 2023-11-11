from telegram import Update
from telegram.ext import (
    ContextTypes,
)
from telegram.constants import ParseMode
import html
import json

import database

from .logger import logger

db = database.Database()

async def create_poll(context: ContextTypes.DEFAULT_TYPE) -> None:
    customer_id = context.job.chat_id
    fin_document_id = context.job.data["fin_document_id"]
    question = "لطفا نظر خود را نسبت به عملکرد کارشناس نبات اعلام کنید:"
    options =   ["عالی", "خوب", "متوسط", "ضعیف", "خیلی ضعیف"]
    poll = await context.bot.send_poll(chat_id=customer_id,
                                       question=question,
                                       options=options,
                                       is_anonymous=False,
                                       allows_multiple_answers=False,
                                       )
    
    db.fin_questions.update_one({"_id": fin_document_id}, {"$set": {"poll-id": poll.poll.id}})
    
    bot_data = context.bot_data
    payload = {
        customer_id: {
                "poll_id": poll.poll.id,
                "fin_document_id": fin_document_id
        }
    }
    bot_data.update(payload)
    logger.info(f"bot_data: {bot_data}")
    # poll_str = poll.to_dict() 
    # message = (
    #     f"Poll message attributes:\n\n"
    #     f"{html.escape(json.dumps(poll_str, indent=3, ensure_ascii=False))}"
    # )
    # await context.bot.send_message(chat_id=user.id, text=message, parse_mode=ParseMode.HTML)

async def assess_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    poll_id = update.poll_answer.poll_id
    options = [("عالی", 5), ("خوب", 4), ("متوسط", 3), ("ضعیف", 2), ("خیلی ضعیف", 1)]
    answer = update.poll_answer
    option_id = answer.option_ids
    rating = options[option_id[0]][1]

    document = db.fin_questions.find_one({"poll-id": poll_id})
    if document:
        expert_id = document["question1"]["expert-id"]
        db.bot_collection.update_one({"name": "expert-rating"}, {"$push": {str(expert_id): rating}}, upsert=True)
        db.fin_questions.update_one({"_id": document["_id"]}, {"$set": {"question1.rating": rating}})
    # user_data = context.user_data
    # logger.info(rating)
    # db.bot_collection.update_one
    
    # logger.info(f"answer: {answer}")
    # logger.info(f"\n{answer.option_ids}\n")
    # await context.bot.send_message(user.id, f"answered_poll: {answer[poll_id]}")

    # update_str = update.to_dict()
    # message = (
    #     f"update with a native poll was intercepted:\n\n"
    #     f"{html.escape(json.dumps(update_str, indent=3, ensure_ascii=False))}"
    # )
    # await context.bot.send_message(chat_id=user.id, text=message, parse_mode=ParseMode.HTML)