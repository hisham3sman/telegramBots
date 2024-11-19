from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
import sqlite3
import requests
import urllib.parse
import base64
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import timedelta
from threading import Thread


def init_db():
    try:
        conn = sqlite3.connect('shop.db', check_same_thread=False)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.close()
    except sqlite3.OperationalError as e:
        print(f"Database initialization error: {e}")

init_db()


TOKEN_USER ='7289315765:AAEXho9j2k3iB084PualzU34JIiPNhFwHSw'
# TOKEN_USER = '7312525147:AAFrTStpQloC67RnPfTvcWaEmhePv3Lzfmw'
MERCH_ACCOUNT = 'sqweer'
# ADMIN_URL = 'https://product0and0store.pythonanywhere.com/send_order'
# ADMIN_URL = 'http://localhost:5432/send_order'
# Initialize the scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# قائمة لتتبع آخر رسالة مرسلة لكل مستخدم
last_message = {}

## حذف الرسائل تلقائيا
def get_delete_time():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT delete_after_seconds FROM settings WHERE id = 1')
    delete_time = cursor.fetchone()[0]
    conn.close()
    return delete_time

def delete_message(context: CallbackContext) -> None:
    job = context.job
    context.bot.delete_message(chat_id=job.context['chat_id'], message_id=job.context['message_id'])

def schedule_message_deletion(context: CallbackContext, chat_id: int, message_id: int) -> None:
    delete_after_seconds = int(get_delete_time())
    delete_after = timedelta(seconds=delete_after_seconds)
    context.job_queue.run_once(delete_message, delete_after, context={'chat_id': chat_id, 'message_id': message_id})


# تعريف دالة معالجة الصورة
def process_image(image_path):
  """قراءة الصورة وتحويلها إلى تنسيق مناسب لـ Telegram"""
  with open(image_path, 'rb') as image_file:
    image_data = image_file.read()
  return base64.b64encode(image_data).decode('utf-8')


def start(update: Update, context: CallbackContext) -> None:
    start_msg = update.message
    args = context.args
    if args and args[0] == 'direct_start':
        context.bot.delete_message(chat_id=start_msg.chat_id, message_id=start_msg.message_id)
        print('direct start')
        show_categories(update,context)
        return
    schedule_message_deletion(context, start_msg.chat_id, start_msg.message_id)
    print(f"last message : {last_message}")

    msg = update.message.reply_text('مرحبا بك في بوت متجر سكوير، الرجاء اختيار قسم للمتابعة')
    last_message[update.effective_user.id] = msg.message_id
    schedule_message_deletion(context, msg.chat_id, msg.message_id)
    chat_id = update.message.chat_id
    username = update.message.from_user.username
    #
    # # تخزين أو طباعة chat_id
    print(f'Chat ID for user {username}: {chat_id}')

    show_categories(update, context)



# def show_categories(update: Update, context: CallbackContext) -> None:
#
#     def process_request():
#         conn = sqlite3.connect('shop.db',check_same_thread=False)
#         cursor = conn.cursor()
#         cursor.execute('SELECT id, name FROM categories')
#         categories = cursor.fetchall()
#         conn.close()
#
#         if not categories:
#             msg = update.message.reply_text('لا توجد أقسام متاحة حاليا.')
#             schedule_message_deletion(context, msg.chat_id, msg.message_id)
#             return
#
#         keyboard = [[InlineKeyboardButton(cat[1], callback_data=f'cat_{cat[0]}')] for cat in categories]
#         reply_markup = InlineKeyboardMarkup(keyboard)
#         msg = update.message.reply_text('اختر قسم:', reply_markup=reply_markup)
#         schedule_message_deletion(context, msg.chat_id, msg.message_id)
#         last_message[update.effective_user.id] = msg.message_id
#     thread = Thread(target=process_request)
#     thread.start()

def show_categories(update: Update, context: CallbackContext) -> None:
    def process_request():
        conn = sqlite3.connect('shop.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM categories WHERE parent_id IS NULL OR parent_id = 0 ORDER BY order_num ASC')
        categories = cursor.fetchall()
        conn.close()

        if not categories:
            msg = update.message.reply_text('لا توجد أقسام متاحة حاليا.')
            schedule_message_deletion(context, msg.chat_id, msg.message_id)
            return

        keyboard = [[InlineKeyboardButton(cat[1], callback_data=f'cat_{cat[0]}')] for cat in categories]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg = update.message.reply_text('اختر قسم:', reply_markup=reply_markup)
        schedule_message_deletion(context, msg.chat_id, msg.message_id)
        last_message[update.effective_user.id] = msg.message_id
    thread = Thread(target=process_request)
    thread.start()

def show_subcategories_and_products(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    category_id = query.data.split('_')[1]

    def process_request():
        conn = sqlite3.connect('shop.db', check_same_thread=False)
        cursor = conn.cursor()

        # Check if the selected category has subcategories
        cursor.execute('SELECT id, name FROM categories WHERE parent_id = ? ORDER BY order_num ASC', (category_id,))
        subcategories = cursor.fetchall()

        if subcategories:
            # If there are subcategories, display them as buttons
            keyboard = [[InlineKeyboardButton(subcat[1], callback_data=f'cat_{subcat[0]}')] for subcat in subcategories]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.message.edit_text('اختر قسماً فرعياً:', reply_markup=reply_markup)

            # Optionally, also display products in the main category
            cursor.execute('SELECT id, name, image_path, image_url FROM products WHERE category_id = ?', (category_id,))
            products = cursor.fetchall()
            if products:
                for product in products:
                    pre_filled_message = f"\n أريد أن أطلب {product[1]}\n رابط صورة المنتج : {product[3]}."
                    encoded_message = urllib.parse.quote(pre_filled_message)
                    chat_link = f"https://t.me/{MERCH_ACCOUNT}?text={encoded_message}"
                    last_mesage_url = f"https://t.me/SQWEER_PRINT_BOT?start=direct_start"
                    keyboard = [
                        [InlineKeyboardButton("اطلب الآن", url=chat_link)],
                        [InlineKeyboardButton("القائمة الرئيسية", url=last_mesage_url)]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    with open(product[2], 'rb') as photo:
                        msg = query.message.reply_photo(photo=photo, caption=product[1], reply_markup=reply_markup, parse_mode=ParseMode.HTML)
                        last_message[update.effective_user.id] = msg.message_id
                        schedule_message_deletion(context, msg.chat_id, msg.message_id)
        else:
            # If no subcategories, show products in the selected category
            cursor.execute('SELECT id, name, image_path, image_url FROM products WHERE category_id = ?', (category_id,))
            products = cursor.fetchall()
            if products:
                for product in products:
                    pre_filled_message = f"\n أريد أن أطلب {product[1]}\n رابط صورة المنتج : {product[3]}."
                    encoded_message = urllib.parse.quote(pre_filled_message)
                    chat_link = f"https://t.me/{MERCH_ACCOUNT}?text={encoded_message}"
                    last_mesage_url = f"https://t.me/SQWEER_PRINT_BOT?start=direct_start"
                    keyboard = [
                        [InlineKeyboardButton("اطلب الآن", url=chat_link)],
                        [InlineKeyboardButton("القائمة الرئيسية", url= last_mesage_url)]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    with open(product[2], 'rb') as photo:
                        msg = query.message.reply_photo(photo=photo, caption=product[1], reply_markup=reply_markup, parse_mode=ParseMode.HTML)
                        last_message[update.effective_user.id] = msg.message_id
                        schedule_message_deletion(context, msg.chat_id, msg.message_id)
            else:
                msg = query.message.reply_text('لا توجد منتجات في هذا القسم.')
                schedule_message_deletion(context, msg.chat_id, msg.message_id)

        conn.close()
    thread = Thread(target=process_request)
    thread.start()

# def show_products(update: Update, context: CallbackContext) -> None:
#     query = update.callback_query
#     query.answer()
#     category_id = query.data.split('_')[1]
#
#     def process_request():
#         conn = sqlite3.connect('shop.db', check_same_thread=False)
#         cursor = conn.cursor()
#         cursor.execute('SELECT id, name, image_path, image_url FROM products WHERE category_id = ?', (category_id,))
#         products = cursor.fetchall()
#         conn.close()
#
#         if not products:
#             msg = query.message.reply_text('لا توجد منتجات في هذا القسم.')
#             schedule_message_deletion(context, msg.chat_id, msg.message_id)
#             return
#
#         for product in products:
#             ## google photos : https://photos.app.goo.gl/V2DLvFHWyHyBcJQz6
#             pre_filled_message = f"\n أريد أن أطلب {product[1]}\n رابط صورة المنتج : {product[3]}."
#             encoded_message = urllib.parse.quote(pre_filled_message)
#             chat_link = f"https://t.me/{MERCH_ACCOUNT}?text={encoded_message}"
#             print (chat_link)
#             user_id = query.from_user.id
#             message_id = last_message[user_id]
#             last_mesage_url = f"https://t.me/Show_products_bot?start=direct_start"
#             keyboard = [
#                 # [InlineKeyboardButton("اطلب الآن", callback_data=f'order_{product[0]}')],
#                 [InlineKeyboardButton("اطلب الآن", url = chat_link)],
#                 # [InlineKeyboardButton("القائمة الرئيسية", callback_data='back_to_categories')]
#                 [InlineKeyboardButton("القائمة الرئيسية", url = last_mesage_url)]
#
#             ]
#             reply_markup = InlineKeyboardMarkup(keyboard)
#
#             with open(product[2], 'rb') as photo:
#                 msg = query.message.reply_photo(photo=photo, caption=product[1], reply_markup=reply_markup, parse_mode=ParseMode.HTML)
#                 last_message[update.effective_user.id] = msg.message_id
#                 schedule_message_deletion(context, msg.chat_id, msg.message_id)
#     thread = Thread(target=process_request)
#     thread.start()


def back_to_categories(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    if user_id in last_message:
        message_id = last_message[user_id]
        context.bot.edit_message_reply_markup(chat_id=user_id, message_id=message_id, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("رجوع للقائمة الرئيسية", callback_data='main_menu')]
        ]))
        last_message[user_id] = message_id
    show_categories(query, context)

def main() -> None:
    updater = Updater(TOKEN_USER)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("menu", show_categories))
    dispatcher.add_handler(CallbackQueryHandler(show_subcategories_and_products, pattern='^cat_\\d+$'))
    dispatcher.add_handler(CallbackQueryHandler(back_to_categories, pattern='^back_to_categories$'))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
