from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

def start_keyboard_future():
    keyboard = [ ['👨‍🌾 ارسال سوال'],  ['🌟 پرداخت'] , ['📤 دعوت از دیگران', '📬 درباره نبات']]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)


def start_keyboard():
    keyboard = [ ['👨‍🌾 ارسال سوال'], ['📬 درباره نبات']]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


def register_keyboard():
    keyboard = [['✍️ ثبت نام']]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


def disclaimer_keyboard():
    keyboard = [['آیین‌نامه را خواندم و قبول می‌کنم'], ['قبول نمی‌کنم'], ['بازگشت']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True ,one_time_keyboard=True)


def back_button():
    keyboard = [['بازگشت']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True ,one_time_keyboard=True)