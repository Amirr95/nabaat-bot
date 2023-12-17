from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

def start_keyboard_future():
    keyboard = [ ['👨‍🌾 ارسال سوال'],  ['🌟 پرداخت'] , ['📤 دعوت از دیگران', '📬 درباره نبات']]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)



def expert_keyboard():
    keyboard = [ ['سوال از کاربر'], ['ارسال توصیه نهایی']]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


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


def select_expert_keyboard():
    keyboard = [['مشاهده و انتخاب کارشناس'], ['انتخاب کارشناس توسط نبات'], ['بازگشت']]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


def specialties_keyboard():
    keyboard = [['زراعت و صیفی جات'], ['باغ(درختان میوه)'], ['تغذیه گیاهی'], ['گل خانه'], ['علوم باغبانی'], ['بازگشت']]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


def next_button():
    keyboard = [['بعدی'], ['انتخاب کارشناس'], ['بازگشت']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def middle_button():
    keyboard = [['بعدی'], ['انتخاب کارشناس'], ['قبلی'], ['بازگشت']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)