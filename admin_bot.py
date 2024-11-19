from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
import sqlite3
import os
from threading import Thread
from pyuploadcare import Uploadcare
import requests
import json

app = Flask(__name__)
TOKEN_ADMIN = '7370642517:AAEnPgZzM858tRN2BNCzX9ol6UCGTJzUcfs'
# TOKEN_ADMIN = '7262788418:AAHrQdV64OZxzO5r7X2cRgwp2_I2I0HfLLA'
ADMIN_PASSWORD = 'adminpassword'
UPLOADCARE_PUBLIC_KEY = 'ecffcfc6fb599aa8fb19'
UPLOADCARE_SECRET_KEY = 'ba231c2cb87f9d8f53c9'
uploadcare = Uploadcare(public_key=UPLOADCARE_PUBLIC_KEY, secret_key=UPLOADCARE_SECRET_KEY)
SESSION = {}


# Function to initialize the database with WAL mode
def init_db():
    try:
        conn = sqlite3.connect('shop.db', check_same_thread=False)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.close()
    except sqlite3.OperationalError as e:
        print(f"Database initialization error: {e}")

init_db()


################################## t. ly ##############################

def shorten_with_tly(long_url):
    url = 'https://api.t.ly/api/v1/link/shorten'
    payload = {
        "long_url": f"{long_url}",
        "domain": "https://t.ly",
        "expire_at_datetime": "2035-01-17 15:00:00",
        "description": "Photo Link",
        "public_stats": True,
        "meta": {
            "smart_urls": [
                {
                    "type": "US",
                    "url": "usa.com"
                },
                {
                    "type": "iPhone",
                    "url": "apple.com"
                }
            ]
        }
    }
    headers = {
    'Authorization': 'Bearer 4oaj7uKGjfRlIEikxtfsw8RMuYo2IHdhLdAaUbj29CqnAdvWsVnFPkHN5rcD',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
    }

    response = requests.request('POST', url, headers=headers, json=payload)
    return response.json()['short_url']
#######################################################################
############## short io ###########################
def shorten_with_shortio(long_url):
    url = "https://api.short.io/links"

    payload = {
        "originalURL": long_url,
        "domain": "g3fl.short.gy"
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": "sk_V6tKYWaFYKEYpPO2"
    }

    response = requests.post(url, json=payload, headers=headers)

    print(response.json()['shortURL'])
    return response.json()['shortURL']
# shorten_with_shortio('https://londo.com')
################################################

admin_bot = Bot(token=TOKEN_ADMIN)
@app.route('/send_order', methods=['POST'])
def send_order():
    data = request.json
    product_name = data.get('product_name')
    username = data.get('username')
    photo_path = data.get('photo_path')

    if product_name and username and photo_path:
        with open(photo_path, 'rb') as photo:
            ## hisham id : 1342122126
            ## mthibo88 id : 303701028
            admin_bot.send_photo(chat_id=1342122126, photo=photo, caption=f'طلب جديد:\nالمنتج: {product_name}\nمن المستخدم: @{username}')
        return 'Order sent', 200
    return 'Missing data', 400

def run_flask():
    app.run(port=5432)

def upload_image_to_cdn(image_file_path):
    with open(image_file_path, 'rb') as file_object:
        ucare_file = uploadcare.upload(file_object)
        return ucare_file.cdn_url

def verify_login(func):
    def wrapper(update, context, *args, **kwargs):
        user_id = None
        if update.message:
            user_id = update.message.chat_id
        elif update.callback_query:
            user_id = update.callback_query.message.chat_id

        if user_id is None or user_id not in SESSION or not SESSION[user_id].get('authenticated'):
            if update.message:
                update.message.reply_text('عفوا انت غير مسجل')
            elif update.callback_query:
                update.callback_query.answer('عفوا انت غير مسجل')
            return

        return func(update, context, *args, **kwargs)
    return wrapper


def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    chat_id = update.message.chat_id
    username = update.message.from_user.username
    # تخزين أو طباعة chat_id
    print(f'Chat ID for user {username}: {user_id}')
    if user_id not in SESSION or not SESSION[user_id].get('authenticated'):
        update.message.reply_text('عفوا انت غير مسجل دخول\nالرجاء كتابة كلمة السر')
    else:
        show_admin_menu(update, context)

def authenticate(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    password = update.message.text

    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT password FROM admin WHERE id = 1')
    result = cursor.fetchone()

    if result and result[0] == password:
        SESSION[user_id] = {'authenticated': True}
        update.message.reply_text('مرحبا بك في لوحة التحكم ببوت عرض الطلبات')
        show_admin_menu(update, context)
    else:
        update.message.reply_text('كلمة المرور غير صحيحة')
    conn.close()

@verify_login
def show_admin_menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("إدارة الأقسام", callback_data='manage_categories')],
        [InlineKeyboardButton("إدارة المنتجات", callback_data='manage_products')],
        [InlineKeyboardButton("عرض كل الأقسام", callback_data='show_categories')],
        [InlineKeyboardButton("عرض كل المنتجات", callback_data='show_products')],
        [InlineKeyboardButton("إدارة زمن حذف الرسائل", callback_data='manage_delete_time')],
        [InlineKeyboardButton("تغيير كلمة السر", callback_data='change_password')],
        [InlineKeyboardButton("تسجيل الخروج", callback_data='logout')],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        if "quer" in context.user_data:
            update.message.edit_text('اختر خيار:', reply_markup=reply_markup)
            del context.user_data['quer']
            return
        update.message.reply_text('اختر خيار:', reply_markup=reply_markup)
    elif update.callback_query:
        update.callback_query.message.edit_text('اختر خيار:', reply_markup=reply_markup)
@verify_login
def manage_categories(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("إضافة قسم رئيسي جديد", callback_data='add_category')],
        [InlineKeyboardButton("إضافة قسم فرعي", callback_data='add_subcategory')],
        [InlineKeyboardButton("تعديل قسم", callback_data='edit_category')],
        [InlineKeyboardButton("حذف قسم", callback_data='delete_category')],
        [InlineKeyboardButton("تغيير ترتيب الأقسام", callback_data='reorder_categories')],
        [InlineKeyboardButton("القائمة الرئيسية", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text('إدارة الأقسام:', reply_markup=reply_markup)

@verify_login
def manage_products(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("إضافة منتج جديد", callback_data='add_product')],
        [InlineKeyboardButton("تعديل منتج", callback_data='edit_product')],
        [InlineKeyboardButton("حذف منتج", callback_data='delete_product')],
        [InlineKeyboardButton("القائمة الرئيسة", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text('إدارة المنتجات:', reply_markup=reply_markup)
    # return MANAGE_PRODUCTS


@verify_login
def show_categories(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()

    # Fetching main categories
    cursor.execute("SELECT id, name FROM categories WHERE parent_id IS NULL OR parent_id = 0 ORDER BY order_num ASC")
    main_categories = cursor.fetchall()

    # List to store the final category text
    category_list = []

    for main_category in main_categories:
        # Adding the main category name
        category_list.append(main_category[1])

        # Fetching subcategories for the main category
        cursor.execute("SELECT name FROM categories WHERE parent_id = ? ORDER BY order_num ASC", (main_category[0],))
        subcategories = cursor.fetchall()

        for subcategory in subcategories:
            # Adding subcategories with indentation
            category_list.append(f"    - {subcategory[0]}")

    conn.close()

    if not category_list:
        query.message.reply_text('لا توجد أقسام حاليا.')
        return

    # Convert the category list to a text with line breaks
    category_text = "\n".join(category_list)
    query.message.reply_text(f'الأقسام المتاحة:\n{category_text}')

@verify_login
def add_category(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    query.message.reply_text('أدخل اسم القسم الجديد:')
    context.user_data['state'] = 'waiting_for_category_name'

# @verify_login
def add_subcategory(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    categories = get_all_categories()

    if not categories:
        query.message.reply_text('لا توجد أقسام حاليا.')
        return

    keyboard = [[InlineKeyboardButton(cat[1], callback_data=f'parentcat_{cat[0]}')] for cat in categories]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text('اختر القسم الأب:', reply_markup=reply_markup)
    context.user_data['state'] = 'waiting_for_subcategory_parent'

@verify_login
def reorder_categories(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    categories = get_all_categories()

    if not categories:
        query.message.reply_text('لا توجد أقسام حاليا.')
        return

    keyboard = [[InlineKeyboardButton(f"{cat[1]} ↑", callback_data=f'move_up_{cat[0]}'),
                 InlineKeyboardButton(f"{cat[1]} ↓", callback_data=f'move_down_{cat[0]}')] for cat in categories]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text('اختر قسمًا لتغيير ترتيبه:', reply_markup=reply_markup)
    context.user_data['state'] = 'waiting_for_category_reorder'

@verify_login
def move_category(update, context, direction):
    query = update.callback_query
    category_id = int(query.data.split("_")[-1])

    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()

    # Get the current order of the category to be moved
    cursor.execute("SELECT id, order_num FROM categories WHERE id = ?", (category_id,))
    category = cursor.fetchone()

    if not category:
        query.message.reply_text("القسم غير موجود.")
        return

    current_order = category[1]

    if direction == 'up':
        # Find the category that is directly above the current one
        cursor.execute("SELECT id, order_num FROM categories WHERE order_num < ? ORDER BY order_num DESC LIMIT 1", (current_order,))
        swap_category = cursor.fetchone()
    elif direction == 'down':
        # Find the category that is directly below the current one
        cursor.execute("SELECT id, order_num FROM categories WHERE order_num > ? ORDER BY order_num ASC LIMIT 1", (current_order,))
        swap_category = cursor.fetchone()

    if swap_category:
        # Swap the order values of the current category and the swap category
        cursor.execute("UPDATE categories SET order_num = ? WHERE id = ?", (swap_category[1], category_id))
        cursor.execute("UPDATE categories SET order_num = ? WHERE id = ?", (current_order, swap_category[0]))
        conn.commit()
        query.message.reply_text("تم تغيير ترتيب القسم بنجاح.")
    else:
        query.message.reply_text("لا يمكن تحريك القسم في هذا الاتجاه.")

    conn.close()
    reorder_categories(update, context)


def move_up_category(update: Update, context: CallbackContext) -> None:
    move_category(update, context, 'up')

def move_down_category(update: Update, context: CallbackContext) -> None:
    move_category(update, context, 'down')


# @verify_login
# def add_product(update: Update, context: CallbackContext) -> None:
#     query = update.callback_query
#     query.answer()
#
#     conn = sqlite3.connect('shop.db')
#     cursor = conn.cursor()
#     cursor.execute("SELECT id, name, order_num FROM categories ORDER BY order_num ASC")
#     categories = cursor.fetchall()
#     conn.close()
#
#     if not categories:
#         query.message.reply_text('لا توجد اقسام حاليا ، قم باضافة قسم باختيار خيار اضافة قسم')
#         return
#
#     keyboard = [[InlineKeyboardButton(cat[1], callback_data=f'cat_{cat[0]}')] for cat in categories]
#     reply_markup = InlineKeyboardMarkup(keyboard)
#     query.message.edit_text('اختر قسم المنتج:', reply_markup=reply_markup)
#     context.user_data['state'] = 'waiting_for_product_category'

def add_product(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()

    # Fetching main categories
    cursor.execute("SELECT id, name FROM categories WHERE parent_id IS NULL OR parent_id = 0 ORDER BY order_num ASC")
    main_categories = cursor.fetchall()

    # If there are no main categories
    if not main_categories:
        query.message.reply_text('لا توجد أقسام حاليا.')
        conn.close()
        return

    # Creating inline buttons for main categories
    buttons = []
    for cat_id, cat_name in main_categories:
        buttons.append([InlineKeyboardButton(cat_name, callback_data=f"cat_{cat_id}")])

    query.message.reply_text('اختر قسماً:', reply_markup=InlineKeyboardMarkup(buttons))
    conn.close()

def handle_category_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    # Extract the selected category ID
    selected_category_id = int(query.data.split("_")[1])

    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()

    # Check if the selected category has subcategories
    cursor.execute("SELECT id, name FROM categories WHERE parent_id = ? ORDER BY order_num ASC", (selected_category_id,))
    subcategories = cursor.fetchall()

    if subcategories:
        # If there are subcategories, display them as buttons
        buttons = []
        for subcat_id, subcat_name in subcategories:
            buttons.append([InlineKeyboardButton(subcat_name, callback_data=f"subcategory_{subcat_id}")])

        buttons.append([InlineKeyboardButton('اختيار هذا القسم', callback_data=f'subcategory_{selected_category_id}')])

        query.message.edit_text('اختر قسماً فرعياً او اضغط اختيار هذا القسم لإنشاء المنتج في القسم الرئيسي', reply_markup=InlineKeyboardMarkup(buttons))
    else:
        category_selected(update,context)

    conn.close()

def handle_subcategory_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    # Extract the selected subcategory ID
    selected_subcategory_id = int(query.data.split("_")[1])

    query.message.reply_text('قم بإدخال تفاصيل المنتج ليتم إضافته إلى هذا القسم الفرعي.')

    # Here you can prompt the user to enter product details and handle the input accordingly.
    # Add your product creation logic here.



@verify_login
def delete_category(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, order_num FROM categories WHERE parent_id IS NULL OR parent_id = 0 ORDER BY order_num ASC")
    categories = cursor.fetchall()
    conn.close()

    if not categories:
        query.message.reply_text('لا توجد أقسام حاليا.')
        return

    keyboard = [[InlineKeyboardButton(cat[1], callback_data=f'delcat_{cat[0]}')] for cat in categories]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text('اختر القسم الذي تريد حذفه:', reply_markup=reply_markup)
    context.user_data['state'] = 'waiting_for_category_deletion'


def check_subcategories(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    category_id = query.data.split('_')[1]

    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM categories WHERE parent_id = ? ORDER BY order_num ASC', (category_id,))
    subcategories = cursor.fetchall()
    conn.close()

    if subcategories:
        # إذا كانت هناك أقسام فرعية
        keyboard = [[InlineKeyboardButton(subcat[1], callback_data=f'delcat_{subcat[0]}')] for subcat in subcategories]
        keyboard.append([InlineKeyboardButton('اختيار هذا القسم', callback_data=f'confirmdel_{category_id}')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text('اختر قسم فرعي أو اضغط "اختيار هذا القسم" لحذف القسم الرئيسي:', reply_markup=reply_markup)
    else:
        # إذا لم تكن هناك أقسام فرعية، انتقل إلى تأكيد الحذف
        confirm_delete_category(update, context, category_id)

@verify_login
def category_selected(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    category_id = query.data.split('_')[1]
    context.user_data['category_id'] = category_id
    query.message.reply_text('أدخل اسم المنتج:')
    context.user_data['state'] = 'waiting_for_product_name'
@verify_login
def confirm_delete_category(update: Update, context: CallbackContext,category_id=None) -> None:
    query = update.callback_query
    query.answer()
    # category_id = query.data.split('_')[1]
    context.user_data['category_id'] = category_id
    query.message.reply_text('أدخل كلمة المرور لتأكيد حذف القسم:')
    context.user_data['state'] = 'waiting_for_category_deletion_confirmation'
@verify_login
def show_products(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    conn = sqlite3.connect('shop.db',check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, order_num FROM categories ORDER BY order_num ASC")
    categories = cursor.fetchall()
    conn.close()

    if not categories:
        query.message.reply_text('لا توجد أقسام حاليا.')
        return

    keyboard = [[InlineKeyboardButton(cat[1], callback_data=f'showcat_{cat[0]}')] for cat in categories]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text('اختر القسم لعرض منتجاته:', reply_markup=reply_markup)
    context.user_data['state'] = 'waiting_for_category_to_show_products'
@verify_login
def show_products_in_category(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    category_id = query.data.split('_')[1]
    def process_request():
        conn = sqlite3.connect('shop.db',check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT name, image_path, image_url FROM products WHERE category_id = ?', (category_id,))
        products = cursor.fetchall()
        conn.close()

        if not products:
            query.message.reply_text('لا توجد منتجات في هذا القسم.')
            return

        for product in products:
            product_name, image_path, image_url = product
            with open(image_path, 'rb') as photo:
                # query.message.reply_photo(photo=photo, caption=product_name)
                query.message.reply_photo(photo=photo, caption=f"اسم المنتج : {product_name}\nرابط صورة المنتج : {image_url}")

        query.message.reply_text('تم عرض كل المنتجات.')
        return
    thread = Thread(target=process_request)
    thread.start()
@verify_login
def change_password(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    query.message.reply_text('أدخل كلمة المرور الجديدة:')
    context.user_data['state'] = 'waiting_for_new_password'
@verify_login
def update_password(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    new_password = update.message.text

    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE admin SET password = ? WHERE id = 1', (new_password,))
    conn.commit()
    conn.close()

    update.message.reply_text('تم تغيير كلمة المرور بنجاح.')
    del context.user_data['state']
    return show_admin_menu(update, context)


@verify_login
def delete_product(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, order_num FROM categories ORDER BY order_num ASC")
    categories = cursor.fetchall()
    conn.close()

    if not categories:
        query.message.reply_text('لا توجد أقسام حاليا.')
        return

    keyboard = [[InlineKeyboardButton(cat[1], callback_data=f'delprod_{cat[0]}')] for cat in categories]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text('اختر القسم الذي تريد حذف منتج منه:', reply_markup=reply_markup)
    context.user_data['state'] = 'waiting_for_category_to_delete_product'
@verify_login
def confirm_delete_product(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    # query.message.reply_text(f"state : {context.user_data.get('state')}")
    category_id = query.data.split('_')[1]
    context.user_data['category_id'] = category_id

    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM products WHERE category_id = ?', (category_id,))
    products = cursor.fetchall()
    conn.close()

    if not products:
        query.message.reply_text('لا توجد منتجات في هذا القسم.')
        return

    keyboard = [[InlineKeyboardButton(prod[1], callback_data=f'finaldelprod_{prod[0]}')] for prod in products]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text('اختر المنتج الذي تريد حذفه:', reply_markup=reply_markup)
    context.user_data['state'] = 'waiting_for_product_to_delete'
@verify_login
def delete_product_final(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    product_id = query.data.split('_')[1]

    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT image_path FROM products WHERE id = ?', (product_id,))
    result = cursor.fetchone()
    if result:
        image_path = result[0]
        if os.path.exists(image_path):
            os.remove(image_path)

    cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()

    query.message.reply_text('تم حذف المنتج بنجاح.')
    del context.user_data['state']
    del context.user_data['category_id']
    return show_admin_menu(update,context)

def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id

    if user_id not in SESSION or not SESSION[user_id].get('authenticated'):
        authenticate(update, context)
        return

    state = context.user_data.get('state')

    if state == 'waiting_for_category_name':
        category_name = update.message.text
        conn = sqlite3.connect('shop.db')
        cursor = conn.cursor()
        # Get the current maximum order_num
        cursor.execute("SELECT MAX(order_num) FROM categories")
        max_order_num = cursor.fetchone()[0]
        # If there are no categories, start with order_num = 1
        if max_order_num is None:
            max_order_num = 0
        # Insert the new category with the next order_num
        cursor.execute("INSERT INTO categories (name, order_num) VALUES (?, ?)", (category_name, max_order_num + 1))
        conn.commit()
        conn.close()
        update.message.reply_text('تم إضافة القسم بنجاح')
        del context.user_data['state']
        return show_admin_menu(update, context)

    elif state == 'waiting_for_product_name':
        if update.message.text:
            product_name = update.message.text
            context.user_data['product_name'] = product_name
            update.message.reply_text('أرسل صورة المنتج:')
            context.user_data['state'] = 'waiting_for_product_image'
        else:
            update.message.reply_text("الرجاء إرسال أسم صحيح")

    elif state == 'waiting_for_product_image':
        if update.message.photo:
            photo_file = update.message.photo[-1].get_file()
            file_path = f'images/{context.user_data["product_name"]}.jpg'
            image = photo_file.download(file_path)

            # context.user_data['product_image'] = file_path

            # product_image = update.message.photo[-1].get_file()
            # image_file_path = product_image.download()
            image_url = upload_image_to_cdn(image)
            # shorten_url = shorten_link_urlday(image_url)
            shorten_url = shorten_with_shortio(image_url)
            conn = sqlite3.connect('shop.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO products (name, category_id, image_path, image_url) VALUES (?, ?, ?,?)',
                           (context.user_data['product_name'], context.user_data['category_id'], file_path, shorten_url))
            conn.commit()
            conn.close()
            # context.user_data['product_image'] = image_url
            update.message.reply_text(f'تم رفع الصورة بنجاح. رابط الصورة: {shorten_url}')
            del context.user_data['state']
            del context.user_data['product_name']
            del context.user_data['category_id']
            update.message.reply_text('تم إضافة المنتج بنجاح')
            return show_admin_menu(update, context)


            # update.message.reply_text("الرجاء ارسال رابط صورة المنتج بعد ارفاقها في احد مواقع رفع الصور :")
            # context.user_data['state'] = "waiting_for_product_image_url"
        else:
            update.message.reply_text('الرجاء إرسال صورة صحيحة.')
    # elif state == 'waiting_for_subcategory_parent':
    #     print('moana')
    #     parent_id = int(update.callback_query.data.split('_')[1])
    #     context.user_data['parent_id'] = parent_id
    #     update.callback_query.message.reply_text('أدخل اسم القسم الفرعي الجديد:')
    #     context.user_data['state'] = 'waiting_for_subcategory_name'

    elif state == 'waiting_for_subcategory_name':
        subcategory_name = update.message.text
        parent_id = context.user_data['parent_id']
        conn = sqlite3.connect('shop.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO categories (name, parent_id) VALUES (?, ?)', (subcategory_name, parent_id))
        conn.commit()
        conn.close()
        update.message.reply_text('تم إضافة القسم الفرعي بنجاح')
        del context.user_data['state']
        return show_admin_menu(update, context)


    elif state == 'waiting_for_category_deletion_confirmation':
        password = update.message.text
        conn = sqlite3.connect('shop.db')
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM admin WHERE id = 1')
        result = cursor.fetchone()

        if result and result[0] == password:
            category_id = context.user_data['category_id']
            cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
            cursor.execute('DELETE FROM products WHERE category_id = ?', (category_id,))
            update.message.reply_text('تم حذف القسم بنجاح')
            del context.user_data['state']
            del context.user_data['category_id']
        else:
            update.message.reply_text('كلمة المرور غير صحيحة')
        conn.commit()
        conn.close()

    elif state == 'waiting_for_category_to_delete_product':
        confirm_delete_product(update, context)
        return
    elif state == 'waiting_for_product_to_delete':
         delete_product_final(update, context)
         return

    elif state == 'waiting_for_new_password':
        update_password(update, context)
        return
    elif state == "SELECT_CATEGORY":
        select_category_products(update,context)
        return
    elif state == "SELECT_PRODUCT":
        select_product(update,context)
        return
    elif state == "UPDATE_PRODUCT_NAME":
        update_product_name(update,context)
        return
    elif state == "SELECT_CATEGORY_TO_EDIT":
        select_category_to_edit(update,context)
        return
    elif state == "NEW_CATEGORY_NAME":
        update_category_name(update,context)
        return
    elif state == "set_delete_time":
        handle_delete_time_input(update,context)
        return

def choose_parent_category(update: Update, context: CallbackContext) -> None:
    print('moana')
    parent_id = int(update.callback_query.data.split('_')[1])
    context.user_data['parent_id'] = parent_id
    update.callback_query.message.reply_text('أدخل اسم القسم الفرعي الجديد:')
    context.user_data['state'] = 'waiting_for_subcategory_name'
# @verify_login
def get_all_categories():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, order_num FROM categories ORDER BY order_num ASC")
    categories = cursor.fetchall()
    conn.close()
    return categories
@verify_login
def edit_product(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    categories = get_all_categories()
    keyboard = [[InlineKeyboardButton(cat[1], callback_data=f'sel_cat_{cat[0]}')] for cat in categories]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text('اختر القسم الذي يحتوي على المنتج:', reply_markup=reply_markup)
    context.user_data['state'] = 'SELECT_CATEGORY'
    # return SELECT_CATEGORY
@verify_login
def select_category_products(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    category_id = query.data.split('_')[2]
    context.user_data['selected_category_id'] = category_id

    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM products WHERE category_id = ?', (category_id,))
    products = cursor.fetchall()
    conn.close()

    keyboard = [[InlineKeyboardButton(prod[1], callback_data=f'edit_prod_{prod[0]}')] for prod in products]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text('اختر المنتج لتعديله:', reply_markup=reply_markup)
    context.user_data['state'] = 'SELECT_PRODUCT'
    # return SELECT_PRODUCT
@verify_login
def select_product(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    product_id = query.data.split('_')[2]
    context.user_data['edit_product_id'] = product_id
    query.message.reply_text('أدخل الاسم الجديد للمنتج:')
    context.user_data['state'] = 'UPDATE_PRODUCT_NAME'
    # return NEW_NAME
@verify_login
def update_product_name(update: Update, context: CallbackContext) -> None:
    new_name = update.message.text
    product_id = context.user_data['edit_product_id']
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE products SET name = ? WHERE id = ?', (new_name, product_id))
    conn.commit()
    conn.close()
    update.message.reply_text('تم تعديل المنتج بنجاح.')
    del context.user_data['state']
    del context.user_data['edit_product_id']
    return show_admin_menu(update,context)

# Edit Category Handlers
@verify_login
def edit_category(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    categories = get_all_categories()
    keyboard = [[InlineKeyboardButton(cat[1], callback_data=f'edit_cat_{cat[0]}')] for cat in categories]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text('اختر القسم لتعديله:', reply_markup=reply_markup)
    context.user_data['state'] = 'SELECT_CATEGORY_TO_EDIT'
    # return SELECT_CATEGORY
@verify_login
def select_category_to_edit(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    category_id = query.data.split('_')[2]
    context.user_data['edit_category_id'] = category_id
    query.message.reply_text('أدخل الاسم الجديد للقسم:')
    context.user_data['state'] = 'NEW_CATEGORY_NAME'
    # return NEW_NAME
@verify_login
def update_category_name(update: Update, context: CallbackContext) -> None:
    new_name = update.message.text
    category_id = context.user_data['edit_category_id']
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE categories SET name = ? WHERE id = ?', (new_name, category_id))
    conn.commit()
    conn.close()
    update.message.reply_text('تم تعديل القسم بنجاح.')
    del context.user_data['state']
    del context.user_data['edit_category_id']
    return show_admin_menu(update,context)
@verify_login
def manage_delete_time(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT delete_after_seconds FROM settings WHERE id = 1')
    delete_time = int(cursor.fetchone()[0]) /60 /60
    print(delete_time)
    conn.close()

    keyboard = [
        [InlineKeyboardButton("تعيين زمن حذف الرسائل", callback_data='set_delete_time')],
        [InlineKeyboardButton("الرجوع للقائمة الرئيسية", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text(f'الزمن الحالي لحذف الرسائل هو {delete_time} ساعة.', reply_markup=reply_markup)
@verify_login
def set_delete_time(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    query.message.reply_text('الرجاء إدخال الزمن الجديد لحذف الرسائل (بالساعات):')
    context.user_data['state'] = "set_delete_time"
@verify_login
def handle_delete_time_input(update: Update, context: CallbackContext) -> None:
    try:
        new_time = int(update.message.text) * 60 * 60
        conn = sqlite3.connect('shop.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE settings SET delete_after_seconds = ? WHERE id = 1', (new_time,))
        conn.commit()
        conn.close()
        update.message.reply_text(f'تم تحديث زمن حذف الرسائل إلى {new_time/60/60} ساعة.')
        del context.user_data['state']
        return show_admin_menu(update,context)
    except ValueError:
        update.message.reply_text('الرجاء إدخال قيمة صحيحة.')



@verify_login
def back_to_main(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    context.user_data['quer'] = True
    return show_admin_menu(query, context)


@verify_login
def logout(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    user_id = query.message.chat_id
    if user_id in SESSION:
        SESSION.pop(user_id)
    query.message.reply_text('تم تسجيل الخروج بنجاح.')

def main() -> None:
    updater = Updater(TOKEN_ADMIN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("menu", show_admin_menu))
    dispatcher.add_handler(CommandHandler("logout", logout))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    ##### manage products ######
    dispatcher.add_handler(CallbackQueryHandler(manage_products, pattern='^manage_products$'))
    ## add product
    dispatcher.add_handler(CallbackQueryHandler(add_product, pattern='^add_product$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_category_selection, pattern='^cat_\\d+$'))
    dispatcher.add_handler(CallbackQueryHandler(category_selected, pattern='^subcategory_\\d+$'))
    ## edit product
    dispatcher.add_handler(CallbackQueryHandler(edit_product, pattern='^edit_product$'))
    dispatcher.add_handler(CallbackQueryHandler(select_category_products, pattern='^sel_cat_\\d+$'))
    dispatcher.add_handler(CallbackQueryHandler(select_product, pattern='^edit_prod_\\d+$'))
    ## delete product
    dispatcher.add_handler(CallbackQueryHandler(delete_product, pattern='^delete_product$'))
    dispatcher.add_handler(CallbackQueryHandler(confirm_delete_product, pattern=r'^delprod_[\d]+$'))
    dispatcher.add_handler(CallbackQueryHandler(delete_product_final, pattern=r'^finaldelprod_[\d]+$'))
    ######## manage categories ########
    dispatcher.add_handler(CallbackQueryHandler(manage_categories, pattern='^manage_categories$'))
    dispatcher.add_handler(CallbackQueryHandler(add_subcategory, pattern='add_subcategory'))
    dispatcher.add_handler(CallbackQueryHandler(reorder_categories, pattern='reorder_categories'))
    dispatcher.add_handler(CallbackQueryHandler(move_up_category, pattern='move_up_'))
    dispatcher.add_handler(CallbackQueryHandler(move_down_category, pattern='move_down_'))

    ## add category
    dispatcher.add_handler(CallbackQueryHandler(add_category, pattern='^add_category$'))
    dispatcher.add_handler(CallbackQueryHandler(choose_parent_category, pattern='^parentcat_\\d+$'))
    ## edit category
    dispatcher.add_handler(CallbackQueryHandler(select_category_to_edit, pattern='^edit_cat_\\d+$'),)
    dispatcher.add_handler(CallbackQueryHandler(edit_category, pattern='^edit_category$'))
    ## delete category
    dispatcher.add_handler(CallbackQueryHandler(show_products_in_category, pattern='^showcat_\\d+$'))
    dispatcher.add_handler(CallbackQueryHandler(delete_category, pattern='^delete_category$'))
    dispatcher.add_handler(CallbackQueryHandler(check_subcategories, pattern='^delcat_\\d+$'))
    dispatcher.add_handler(CallbackQueryHandler(confirm_delete_category, pattern='^confirmdel_\\d+$'))
    dispatcher.add_handler(CallbackQueryHandler(show_categories, pattern='^show_categories$'))
    dispatcher.add_handler(CallbackQueryHandler(show_products, pattern='^show_products$'))
    dispatcher.add_handler(CallbackQueryHandler(change_password, pattern='^change_password$'))
    ## manage delete delete_time
    dispatcher.add_handler(CallbackQueryHandler(manage_delete_time, pattern='^manage_delete_time$'))
    dispatcher.add_handler(CallbackQueryHandler(set_delete_time, pattern='^set_delete_time$'))

    dispatcher.add_handler(CallbackQueryHandler(back_to_main, pattern='^back_to_main$'))
    dispatcher.add_handler(CallbackQueryHandler(logout, pattern='^logout$'))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.add_handler(MessageHandler(Filters.photo, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    main()
