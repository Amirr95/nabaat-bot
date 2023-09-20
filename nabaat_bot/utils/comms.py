from telegram import Update
from telegram.ext import ContextTypes
import random
import database
from .logger import logger

db = database.Database()

async def send_question_to_expert(context: ContextTypes.DEFAULT_TYPE):
    customer_id = context.job.chat_id
    customer_username = context.job.data
    experts = db.get_experts()
    chosen_expert = random.choice(experts.keys())
    group_id = experts[chosen_expert]
    res = await context.bot.create_forum_topic(chat_id=group_id, name=f"@{customer_username} | {customer_id}")
    logger.info(res)