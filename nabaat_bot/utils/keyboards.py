from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

def start_keyboard():
    keyboard = [ ['👨‍🌾 ارسال سوال'],  ['🌟 پرداخت'] , ['📤 دعوت از دیگران', '📬 ارتباط با ما']]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)


def register_keyboard():
    keyboard = [['✍️ ثبت نام']]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


def back_button():
    keyboard = [['بازگشت']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True ,one_time_keyboard=True)