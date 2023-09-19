from telegram import Update
from telegram.ext import ContextTypes


async def send(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    group_id = -100
    res = await context.bot.create_forum_topic(chat_id=group_id, name=str(user_id))