# from flask import Flask, request
import telebot
import qrcode
from telebot import types
import time
# from telegram import Update
# from telegram.ext import Updater, CallbackContext
import sqlite3
import os
import cv2
from pyzbar.pyzbar import decode
# import requests
from threading import Thread, Timer
import secrets
import string
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from requests.exceptions import ProxyError, ConnectionError

API_TOKEN_ADMIN = '7214607296:AAHkOUm8l4ZO8C2-hIm7Hh1Tk_QZ9kveF54'
API_TOKEN_CLIENT = "7279640066:AAEKtd7OiTZh1fqjbWMfxzSwUnE0V8hahI4"
bot_admin = telebot.TeleBot(API_TOKEN_ADMIN)
bot_client = telebot.TeleBot(API_TOKEN_CLIENT)
CLIENT_BOT_URL = 'http://127.0.0.1:5432/send_notification'


QR_CODE_DIR = 'Qr Code Images'
EXCEL_FILES_DIR = 'Excel Files'

os.makedirs(QR_CODE_DIR, exist_ok=True)
os.makedirs(EXCEL_FILES_DIR, exist_ok=True)

def init_db():
    conn = sqlite3.connect('clients.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            qr_code TEXT UNIQUE,
            unique_link TEXT UNIQUE,
            balance REAL DEFAULT 0.0,
            chat_id INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            amount REAL,
            description TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    ''')
    conn.execute('PRAGMA journal_mode=WAL')
    conn.commit()
    conn.close()

init_db()

def start_client_bot():
    # @app.route('/send_notification', methods=['POST'])
    def send_notification(client_chat_id,message):
        print("halaloia")
        # data = request.json
        # print(data)
        # client_chat_id = data.get('client_id')
        # message = data.get('message')

        if client_chat_id and message:
            bot_client.send_message(chat_id=client_chat_id, text=f'إشعار جديد : {message}')

    # def run_flask():
    #     app.run(port=5432)
    # user_session = {'is_logged_in': False, 'client_id': ""}
    @bot_client.message_handler(commands=['start'])
    def send_welcome(message):
        def process_request():
            args = message.text.split()
            if len(args) > 1:
                unique_link = f"https://t.me/Clients_balanceChecker_bot?start={args[1]}"
                conn = sqlite3.connect('clients.db')
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM clients WHERE unique_link = ?', (unique_link,))
                client = cursor.fetchone()

                if client:
                    cursor.execute('UPDATE clients SET chat_id = ? WHERE id = ?', (message.chat.id, client[0]))
                    conn.commit()
                    markup = types.InlineKeyboardMarkup()
                    cancel_button = types.InlineKeyboardButton("عرض تفاصيل الحساب", url=unique_link ) # callback_data=f'show_client_{client_id}'
                    markup.add(cancel_button)
                    bot_client.send_message(message.chat.id, f"مرحباً {client[1]}، رصيدك الحالي هو: {client[4]}")
                    bot_client.send_photo(message.chat.id, photo=open(client[2], 'rb'),reply_markup=markup)
                    # user_session['is_logged_in'] = True
                    # user_session['client_id'] = client[0]
                else:
                    bot_client.send_message(message.chat.id, "لم يتم العثور على الزبون.",)
                    # user_session['is_logged_in'] = False
                    # user_session['chat_id'] = ''
                conn.close()
            else:
                msg = bot_client.send_message(message.chat.id, "مرحباً! يرجى إرسال رمز QR Code الخاص بك:")
                bot_client.register_next_step_handler(msg, process_qr_code)
        thread = Thread(target=process_request)
        thread.start()

    def process_qr_code(message):
        def process_request():
            try:
                file_info = bot_client.get_file(message.photo[-1].file_id)
                downloaded_file = bot_client.download_file(file_info.file_path)
                qr_image_path = "scanned_qr.png"
                with open(qr_image_path, 'wb') as new_file:
                    new_file.write(downloaded_file)
                img = cv2.imread(qr_image_path)
                decoded_objects = decode(img)
                if decoded_objects:
                    client_link = decoded_objects[0].data.decode('utf-8')
                    print(f"link : {client_link}")
                    conn = sqlite3.connect('clients.db')
                    cursor = conn.cursor()
                    cursor.execute('SELECT * FROM clients WHERE unique_link = ?', (client_link,))
                    client = cursor.fetchone()
                    client_id = client[0]
                    if client:
                        cursor.execute('UPDATE clients SET chat_id = ? WHERE id = ?', (message.chat.id, client_id))
                        conn.commit()
                        unique_link = client[3]
                        markup = types.InlineKeyboardMarkup()
                        cancel_button = types.InlineKeyboardButton("عرض تفاصيل الحساب", url=unique_link)
                        markup.add(cancel_button)
                        bot_client.send_message(message.chat.id, f"مرحباً {client[1]}، رصيدك الحالي هو: {client[4]}")
                        bot_client.send_photo(message.chat.id, photo=open(client[2], 'rb'),reply_markup=markup)
                    else:
                        bot_client.send_message(message.chat.id, "رمز ال QR Code غير مسجل")
                    conn.close()
                else:
                    bot_client.send_message(message.chat.id, "رمز QR Code غير صالح.")
            except Exception as e:
                bot_client.send_message(message.chat.id, f"خطأ في تحليل ال QR Code : {e}")
        thread = Thread(target=process_request)
        thread.start()

    @bot_client.callback_query_handler(func=lambda call: call.data.startswith('show_client_'))
    def show_client_details(call):
        def process_request():
            bot_client.answer_callback_query(call.id)
            client_id = call.data.split('_')[2]
            chat_id = call.message.chat.id
            conn = sqlite3.connect('clients.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
            client = cursor.fetchone()
            conn.close()
            client_name = client[1]
            client_qr = client[2]
            client_balance = client[4]
            bot_client.send_message(chat_id, f"مرحباً {client_name}\nرقم المعرف : {client_id}\n رصيدك الكلي: {client_balance}")
            markup = types.InlineKeyboardMarkup()
            cancel_button = types.InlineKeyboardButton("عرض تفاصيل الحساب", callback_data=f'show_client_{client_id}')
            markup.add(cancel_button)
            bot_client.send_photo(chat_id, photo=open(client_qr, 'rb'),reply_markup=markup)
        thread = Thread(target=process_request)
        thread.start()

    # def decode_qr_code(file_id):
    #     file_info = bot_client.get_file(file_id)
    #     downloaded_file = bot_client.download_file(file_info.file_path)
    #
    #     nparr = np.frombuffer(downloaded_file, np.uint8)
    #     img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    #     decoded_objects = decode(img_np)
    #
    #     if decoded_objects:
    #         return decoded_objects[0].data.decode("utf-8")
    #     return None

    # flask_thread = Thread(target=run_flask)
    # flask_thread.start()
    # bot_thread = Thread(target=bot_client.polling())
    # bot_thread.start()
    # bot_client.polling()
    while True:
        try:
            bot_client.polling(none_stop=True, interval=1)
        except ProxyError as e:
            print(f"Proxy error occurred: {e}")
            time.sleep(5)  # Wait 5 seconds before retrying
        except ConnectionError as e:
            print(f"Connection error occurred: {e}")
            time.sleep(5)  # Wait 5 seconds before retrying
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            time.sleep(5)  # Wait 5 seconds before retrying


def start_admin_bot():
    # متغيرات لتسجيل الدخول
    conn = sqlite3.connect('clients.db')
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id FROM users WHERE is_main_admin = True')
    main_admin = cursor.fetchall()
    main_admins = []
    if main_admin != None:
        for index, value in enumerate(main_admin):
            print(main_admin[index][0])
            main_admins.append(main_admin[index][0])
    print(main_admins)
    # if main_admins == []:
    #     main_admins = cursor.fetchall()
    # else :
    #     main_admins = cursor.fetchall()
    cursor.execute('SELECT chat_id FROM users WHERE is_admin = True')
    admins = cursor.fetchall()
    if admins == []:
        admins = cursor.fetchall()
    else :
        admins = admins
    print(f"main admins : {main_admins}")
    print(f" admins : {admins}")

    cursor.execute("SELECT password FROM admin_settings ")
    passw = cursor.fetchone()[0]
    print(f"password : {passw}")
    login_session = {'is_logged_in': False, 'last_login_time': 0}
    cursor.execute("SELECT session_duration FROM admin_settings WHERE id = 1")
    login_duration = cursor.fetchone()[0]
    print(f'login duration : {login_duration}')
    conn.close()
    authorized_users = []
    print("admins - authorized_users")
    print(admins)
    if admins != None:
        for index, value in enumerate(admins):
            print(admins[index][0])
            authorized_users.append(admins[index][0])
    PASSWORD = passw
    def check_login(chat_id):
        if login_session['is_logged_in'] and chat_id in authorized_users:
            return True
        return False

# وظيفة لإعادة ضبط تسجيل الدخول بعد 20 دقيقة
    # وظيفة لإعادة ضبط تسجيل الدخول بعد 20 دقيقة
    def reset_login():
        login_session['is_logged_in'] = False


    def generate_qr_code(client_id, data):
        logo_path = 'logo.png'
        font_path = 'NotoKufi.ttf'

        # توليد QR Code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        # إنشاء صورة QR Code
        qr_code_image = qr.make_image(fill='black', back_color='white').convert("RGBA")

        # تحديد حجم الصورة الجديدة
        qr_width, qr_height = qr_code_image.size
        new_width = qr_width + 100  # زيادة العرض
        new_height = qr_height + 150  # زيادة الطول

        # إنشاء صورة جديدة أكبر
        new_image = Image.new("RGBA", (new_width, new_height), "white")

        # لصق صورة QR Code في الصورة الجديدة
        qr_code_image = qr_code_image.resize((qr_width, qr_height), Image.LANCZOS)
        new_image.paste(qr_code_image, (50, 50))  # إدراج QR Code مع مساحة إضافية حوله

        draw = ImageDraw.Draw(new_image)

        # تحميل الخطوط
        font_large = ImageFont.truetype(font_path, 37)
        font_small = ImageFont.truetype(font_path, 33)
        smallest_font = ImageFont.truetype(font_path, 24)

        # نصوص العبارات
        header_text = "مطبعة سكوير للطباعة والتجليد"
        footer_text = "كود الخصم"
        customer_text = f"No: {client_id}"

        header_text_color = (0, 0, 0)  # اللون الأزرق

        # حساب حجم النصوص لإضافة الشعار
        header_bbox = draw.textbbox((0, 0), header_text, font=font_large)
        footer_bbox = draw.textbbox((0, 0), footer_text, font=font_small)
        customer_bbox = draw.textbbox((0, 0), customer_text, font=smallest_font)

        header_width = header_bbox[2] - header_bbox[0]
        footer_width = footer_bbox[2] - footer_bbox[0]
        customer_width = customer_bbox[2] - customer_bbox[0]

        # حساب مواضع النصوص والشعار
        qr_code_position = (50, 50)
        qr_code_center_x = qr_code_position[0] + qr_width // 2
        qr_code_center_y = qr_code_position[1] + qr_height // 2

        header_position = ((new_width - header_width) // 2, 10)
        footer_position = ((new_width - footer_width) // 2, new_height - 130)
        customer_position = ((new_width - customer_width) // 2 - 12, new_height - 70)

        # إضافة النصوص
        draw.text(header_position, header_text, font=font_large, fill=header_text_color)
        draw.text(footer_position, footer_text, font=font_small, fill="black")
        draw.text(customer_position, customer_text, font=font_small, fill="black")

        # إضافة الشعار في منتصف الكود
        logo_image = Image.open(logo_path).convert("RGBA")
        logo_size = (qr_width // 3, qr_height // 3)  # حجم الشعار
        logo_image = logo_image.resize(logo_size, Image.LANCZOS)

        logo_position = (
            qr_code_center_x - logo_size[0] // 2,
            qr_code_center_y - logo_size[1] // 2
        )
        new_image.paste(logo_image, logo_position, logo_image)

        return new_image

    def generate_unique_link(client_id):
        random_string = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        unique_link = f"https://t.me/Clients_balanceChecker_bot?start={client_id}_{random_string}"
        return unique_link


    def get_cancel_markup():
        markup = types.InlineKeyboardMarkup()
        cancel_button = types.InlineKeyboardButton("إلغاء", callback_data='cancel')
        markup.add(cancel_button)
        return markup


    def notify_client(chat_id, client_id, message):
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()
        cursor.execute('SELECT chat_id,unique_link FROM clients WHERE id = ?', (client_id,))
        client = cursor.fetchone()
        conn.close()
        if client and client[0]:
            # bot_client.send_message(client[0], message)
            try:
                # response = requests.post(CLIENT_BOT_URL, json={
                #     'client_id': client[0],
                #     'message': message,
                #     # 'photo_path': photo_path
                # })
                markup = types.InlineKeyboardMarkup()
                unique_link = client[1]
                cancel_button = types.InlineKeyboardButton("عرض تفاصيل الحساب", url=unique_link)
                markup.add(cancel_button)
                bot_client.send_message(chat_id=client[0], text=f'إشعار جديد : {message}',reply_markup=markup)
                # if response.status_code == 200:
                bot_admin.send_message(chat_id,"تم إرسال إشعار الى المستخدم")
            except Exception as e:
                query.message.reply_text('حدث خطأ أثناء إرسال إشعار للمستخدم. الرجاء المحاولة مرة أخرى لاحقاً.')
                print(e)
        else :
            bot_admin.send_message(chat_id, "لم يتم ارسال إشعار للمستخدم لإنه لم يدخل لبوت الزبائن بعد")

    @bot_admin.callback_query_handler(func=lambda call: call.data == 'cancel')
    def cancel_action(call):
        bot_admin.answer_callback_query(call.id)
        # bot_admin.send_message(call.message.chat.id, "تم إلغاء العملية.")
        bot_admin.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
        return main_menu(call.message.chat.id, welcome_message=False)

    def main_menu(chat_id, welcome_message=True):
        # chat_id = message.chat.id
        print (authorized_users)
        if chat_id not in authorized_users:
            bot_admin.send_message(chat_id, "غير مصرح لك باستخدام هذا البوت.")
            return
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        btn1 = types.KeyboardButton('إنشاء QR Code')
        btn2 = types.KeyboardButton('مسح QR Code')
        btn3 = types.KeyboardButton('عرض جميع الزبائن')
        btn4 = types.KeyboardButton('عرض زبون')
        btn5 = types.KeyboardButton('حذف زبون')
        btn6 = types.KeyboardButton('اضافة عمولة')
        btn7 = types.KeyboardButton('سحب رصيد')
        btn8 = types.KeyboardButton('إضافة ادمن')
        btn9 = types.KeyboardButton('حذف ادمن')
        btn10 = types.KeyboardButton('تغيير كلمة السر')
        btn11 = types.KeyboardButton('تغيير زمن الجلسة')
        markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7)
         # تحقق إذا كان المستخدم أدمن رئيسي
        if chat_id in main_admins:
            print('main admin')
            # btn8 = types.KeyboardButton('إضافة ادمن')
            markup.add(btn8,btn9,btn10,btn11)
        if welcome_message:
            bot_admin.send_message(chat_id, "القائمة الرئيسية:", reply_markup=markup)
        else:
            return bot_admin.send_message(chat_id,"تم إلغاء العملية ، اختر خيار", reply_markup=markup)

    @bot_admin.message_handler(commands=['start'])
    def send_welcome(message):
        print('authorized_users')
        print(authorized_users)
        chat_id = message.chat.id
        username = message.from_user.username
        #
        # # تخزين أو طباعة chat_id
        print(f'Chat ID for user {username}: {chat_id}')
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM users WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()
        if (result is None) or (result[0] not in authorized_users):
            if result is None:
                cursor.execute('INSERT INTO users (username,chat_id) VALUES (?,?)', (username, chat_id))
                conn.commit()
            bot_admin.send_message(chat_id, "غير مصرح لك باستخدام هذا البوت.")
            conn.close()
            return
        conn.close()
        # if chat_id not in authorized_users:
        #     bot_admin.send_message(chat_id, "غير مصرح لك باستخدام هذا البوت.")
        #     return
        if(login_session['is_logged_in'] == False):
            bot_admin.send_message(chat_id, "الرجاء إدخال كلمة المرور:")
            return bot_admin.register_next_step_handler(message, process_password)
        main_menu(message.chat.id)

    # معالجة كلمة المرور
    def process_password(message):
        chat_id = message.chat.id
        if message.text == PASSWORD:
            login_session['is_logged_in'] = True
            login_session['last_login_time'] = time.time()
            bot_admin.send_message(chat_id, f"تم تسجيل الدخول بنجاح. الجلسة صالحة لمدة {login_duration} دقيقة.")
            # إعداد مؤقت لمدة 20 دقيقة
            Timer(login_duration * 60, reset_login).start()  # 1200 ثانية = 20 دقيقة
            main_menu(message.chat.id)
        else:
            msg = bot_admin.send_message(chat_id, "كلمة المرور غير صحيحة. الرجاء المحاولة مرة أخرى.")
            bot_admin.register_next_step_handler(msg, process_password)

    @bot_admin.message_handler(func=lambda message: message.text == 'إنشاء QR Code')
    def create_qr(message):
        chat_id = message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        msg = bot_admin.send_message(message.chat.id, "أدخل إسم الزبون :", reply_markup=get_cancel_markup())
        bot_admin.register_next_step_handler(msg, process_name_step)

    def process_name_step(message):

        chat_id = message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        try:
            client_name = message.text
            conn = sqlite3.connect('clients.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO clients (name) VALUES (?)', (client_name,))
            client_id = cursor.lastrowid
            unique_link = generate_unique_link(client_id)
            img = generate_qr_code(client_id, unique_link)
            img_path = os.path.join(QR_CODE_DIR, f"{client_name}_qr.png")
            img.save(img_path)

            cursor.execute('UPDATE clients SET qr_code = ?, unique_link = ? WHERE id = ?', (img_path, unique_link, client_id))
            conn.commit()
            conn.close()

            bot_admin.send_message(message.chat.id, f"تم إنشاء QR Code ورابط خاص للزبون : {client_name}.")
            bot_admin.send_photo(message.chat.id, photo=open(img_path, 'rb'))
            bot_admin.send_message(message.chat.id, f"رقم معرف الزبون : {client_id}\nرابط الزبون : {unique_link}.")
            main_menu(message.chat.id)
        except Exception as e:
            bot_admin.reply_to(message, 'حدث خطأ : ' + str(e))

    @bot_admin.message_handler(func=lambda message: message.text == 'مسح QR Code')
    def scan_qr(message):

        chat_id = message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        msg = bot_admin.send_message(message.chat.id, "أرسل ال QR Code المراد مسحه:", reply_markup=get_cancel_markup())
        bot_admin.register_next_step_handler(msg, process_qr_scan)
    def process_qr_scan(message):

        chat_id = message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        try:
            file_info = bot_admin.get_file(message.photo[-1].file_id)
            downloaded_file = bot_admin.download_file(file_info.file_path)
            qr_image_path = "scanned_qr.png"
            with open(qr_image_path, 'wb') as new_file:
                new_file.write(downloaded_file)
            img = cv2.imread(qr_image_path)
            decoded_objects = decode(img)
            if decoded_objects:
                unique_link = decoded_objects[0].data.decode('utf-8')
                conn = sqlite3.connect('clients.db')
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM clients WHERE unique_link = ?', (unique_link,))
                client = cursor.fetchone()
                conn.close()

                if client:
                    client_id = client[0]
                    client_name = client[1]
                    client_link = client[3]
                    client_balance = client[4]
                    bot_admin.send_message(message.chat.id, f"معلومات الزبون: \nرقم معرف الزبون : {client_id}\nإسم الزبون : {client_name}\nرصيد الزبون : {client_balance} دينار\nرابط الزبون : {client_link}")
                    # bot_admin.send_photo(message.chat.id, photo=open(client[2], 'rb'))

                    # markup = types.InlineKeyboardMarkup()
                    # add_commission_button = types.InlineKeyboardButton("إضافة عمولة", callback_data=f"add_commission_{client[0]}")
                    # markup.add(add_commission_button)
                    bot_admin.send_message(message.chat.id, "أختر خيار:",reply_markup=get_client_options_markup(client[0],client[1],chat_id))
                else:
                    bot_admin.send_message(message.chat.id, "الزبون غير موجود.")
            else:
                bot_admin.send_message(message.chat.id, "لم يتم إيجاد QR Code.")
            main_menu(message.chat.id)
        except Exception as e:
            bot_admin.reply_to(message, 'خطأ : ' + str(e))

    @bot_admin.callback_query_handler(func=lambda call: call.data.startswith('add_commission_'))
    def add_commission_callback(call):

        chat_id = call.message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        bot_admin.answer_callback_query(call.id)
        client_id = call.data.split('_')[2]
        msg = bot_admin.send_message(call.message.chat.id, "أدخل قيمة العمولة:",reply_markup=get_cancel_markup())
        bot_admin.register_next_step_handler(msg, process_commission, client_id)

    def add_commission_to_client(message, client_id):

        chat_id = message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        msg = bot_admin.send_message(message.chat.id, "أدخل قيمة العمولة:",reply_markup=get_cancel_markup())
        bot_admin.register_next_step_handler(msg, process_commission, client_id)

    def process_commission(message, client_id):

        chat_id = message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        try:
            amount = float(message.text)
            conn = sqlite3.connect('clients.db')
            cursor = conn.cursor()
            cursor.execute('UPDATE clients SET balance = balance + ? WHERE id = ?', (amount, client_id))
            cursor.execute('INSERT INTO transactions (client_id, amount, description) VALUES (?, ?, ?)', (client_id, amount, 'إضافة عمولة'))
            conn.commit()
            conn.close()
            notify_client(message.chat.id,client_id, f"تمت إضافة عمولة بقيمة {amount} دينار إلى حسابك")
            bot_admin.send_message(message.chat.id, f"تم إضافة عمولة بمبلغ : {amount} دينار  بنجاح. ")
            main_menu(message.chat.id)
        except Exception as e:
            bot_admin.reply_to(message, 'حدث خطأ : ' + str(e))

    @bot_admin.message_handler(func=lambda message: message.text == 'عرض زبون')
    def view_client(message):

        chat_id = message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        msg = bot_admin.send_message(message.chat.id, "أدخل اسم الزبون أو رقم معرف الزبون:", reply_markup=get_cancel_markup())
        bot_admin.register_next_step_handler(msg, process_view_client)

    def process_view_client(message):
        chat_id = message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        try:
            client_identifier = message.text
            conn = sqlite3.connect('clients.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM clients WHERE name = ? OR id = ?', (client_identifier, client_identifier))
            client = cursor.fetchone()
            conn.close()

            if client:
                client_id = client[0]
                client_name = client[1]
                client_link = client[3]
                client_balance = client[4]
                bot_admin.send_message(message.chat.id, f"معلومات الزبون: \nرقم معرف الزبون : {client_id}\nإسم الزبون : {client_name}\nرصيد الزبون : {client_balance} دينار\nرابط الزبون : {client_link}")
                bot_admin.send_photo(message.chat.id, photo=open(client[2], 'rb'),reply_markup=get_client_options_markup(client[0],client[1],chat_id))
                # bot_admin.send_message(message.chat.id, "اختر خيارًا:", reply_markup=get_client_options_markup(client[0],client[1]))
            else:
                bot_admin.send_message(message.chat.id, "الزبون غير موجود.")
            main_menu(message.chat.id)
        except Exception as e:
            bot_admin.reply_to(message, 'خطأ: ' + str(e))

    def get_client_options_markup(client_id,client_name,chat_id):
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        markup = types.InlineKeyboardMarkup()
        add_commission_button = types.InlineKeyboardButton("إضافة عمولة", callback_data=f"add_commission_{client_id}")
        view_transactions_button = types.InlineKeyboardButton("عرض المعاملات", callback_data=f"view_transactions_{client_id}")
        export_button = types.InlineKeyboardButton("تصدير المعلومات إلى Excel", callback_data=f"export_transactions_{client_id}_{client_name}")
        markup.row(add_commission_button,view_transactions_button)
        markup.add(export_button)
        return markup

    @bot_admin.callback_query_handler(func=lambda call: call.data.startswith('view_transactions_'))
    def view_client_transactions(call):

        chat_id = call.message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        bot_admin.answer_callback_query(call.id)
        client_id = call.data.split('_')[2]
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transactions WHERE client_id = ?', (client_id,))
        transactions = cursor.fetchall()
        conn.close()

        if transactions:
            response = "\n".join([f"ID: {t[0]}\n المبلغ: {t[2]}\n الوصف: {t[3]}\n التاريخ: {t[4]}" for t in transactions])
            bot_admin.send_message(call.message.chat.id, f"المعاملات:\n{response}")
        else:
            bot_admin.send_message(call.message.chat.id, "لا توجد معاملات لهذا الزبون.")
        main_menu(call.message.chat.id)

    @bot_admin.message_handler(func=lambda message: message.text == 'عرض جميع الزبائن')
    def view_all_clients(message):

        chat_id = message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients')
        clients = cursor.fetchall()
        conn.close()
        if not clients:
            bot_admin.send_message(message.chat.id, "لا يوجد أي زبون مسجل حاليًا.")
            main_menu(message.chat.id)
            return

        # markup = types.InlineKeyboardMarkup()
        # btn1 = types.InlineKeyboardButton('عرض المعلومات الأساسية', callback_data='view_basic_info')
        # btn2 = types.InlineKeyboardButton('عرض المعلومات بالتفصيل', callback_data='view_detailed_info')
        # cancel_button = types.InlineKeyboardButton("إلغاء", callback_data='cancel')
        # markup.add(btn1, btn2, cancel_button)

        keyboard = [
            [types.InlineKeyboardButton('عرض المعلومات الأساسية', callback_data='view_basic_info')],
            [types.InlineKeyboardButton('عرض المعلومات بالتفصيل', callback_data='export_all_clients')], # view_detailed_info
            [types.InlineKeyboardButton("إلغاء", callback_data='cancel')],
        ]

        markup = types.InlineKeyboardMarkup(keyboard)

        bot_admin.send_message(message.chat.id, "اختر خيارًا:", reply_markup=markup)

    @bot_admin.callback_query_handler(func=lambda call: call.data == 'view_basic_info')
    def view_basic_info_callback(call):

        chat_id = call.message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        bot_admin.answer_callback_query(call.id)
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients')
        clients = cursor.fetchall()
        conn.close()

        if not clients:
            bot_admin.send_message(call.message.chat.id, "لا يوجد أي زبون مسجل حاليًا.")
            main_menu(call.message.chat.id)
            return

        for client in clients:
            client_id = client[0]
            client_name = client[1]
            client_link = client[3]
            client_balance = f"{client[4]} د.ع"
            bot_admin.send_message(call.message.chat.id, f"معلومات الزبون: \nرقم معرف الزبون : {client_id}\nإسم الزبون : {client_name}\nرصيد الزبون : {client_balance} دينار\nرابط الزبون : {client_link}")
            bot_admin.send_photo(call.message.chat.id, photo=open(client[2], 'rb'))

        markup = types.InlineKeyboardMarkup()
        export_button = types.InlineKeyboardButton("تصدير إلى Excel", callback_data="export_basic_info")
        markup.add(export_button)
        bot_admin.send_message(call.message.chat.id, "تصدير معلومات الزبائن الأساسية إلى Excel؟", reply_markup=markup)

    @bot_admin.callback_query_handler(func=lambda call: call.data == 'view_detailed_info')
    def view_detailed_info_callback(call):

        chat_id = call.message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        bot_admin.answer_callback_query(call.id)
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients')
        clients = cursor.fetchall()
        conn.close()

        if not clients:
            bot_admin.send_message(call.message.chat.id, "لا يوجد أي زبون مسجل حاليًا.")
            main_menu(call.message.chat.id)
            return

        def send_client_info(client, index):
            client_id = client[0]
            client_name = client[1]
            client_link = client[3]
            client_balance = f"{client[4]} د.ع"
            bot_admin.send_message(call.message.chat.id, f"معلومات الزبون: \nرقم معرف الزبون : {client_id}\nإسم الزبون : {client_name}\nرصيد الزبون : {client_balance} دينار\nرابط الزبون : {client_link}")
            bot_admin.send_photo(call.message.chat.id, photo=open(client[2], 'rb'))

            conn = sqlite3.connect('clients.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM transactions WHERE client_id = ?', (client[0],))
            transactions = cursor.fetchall()
            conn.close()

            if transactions:
                response = ''
                response = "\n".join([f"ID: {t[0]}\n المبلغ: {t[2]}\n الوصف: {t[3]}\n التاريخ: {t[4]}" for t in transactions])
                markup = types.InlineKeyboardMarkup()
                export_button = types.InlineKeyboardButton("تصدير معلومات الزبون إلى Excel", callback_data=f"export_transactions_{client[0]}_{client[1]}")
                markup.add(export_button)
                bot_admin.send_message(call.message.chat.id, f"المعاملات:\n{response}", reply_markup=markup)
                # bot_admin.send_message(call.message.chat.id, "تصدير معلومات الزبون إلى Excel؟", reply_markup=markup)

            # الانتقال للزبون التالي
            if index + 1 < len(clients):
                next_client = clients[index + 1]
                send_client_info(next_client, index + 1)
            else:
                markup = types.InlineKeyboardMarkup()
                export_all_button = types.InlineKeyboardButton("تصدير جميع الزبائن ومعاملاتهم إلى Excel", callback_data="export_all_clients")
                markup.add(export_all_button)
                bot_admin.send_message(call.message.chat.id, "تم عرض جميع الزبائن. اختر أحد الخيارات:", reply_markup=markup)
                main_menu(call.message.chat.id)

        if clients:
            send_client_info(clients[0], 0)

    @bot_admin.callback_query_handler(func=lambda call: call.data.startswith('export_basic_info'))
    def export_basic_info_callback(call):

        chat_id = call.message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        bot_admin.answer_callback_query(call.id)
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients')
        clients = cursor.fetchall()
        conn.close()

        data = []
        for client in clients:
            client_id = client[0]
            client_name = client[1]
            client_link = client[3]
            client_balance = f"{client[4]} د.ع"
            data.append([client_id, client_name, client_link, client_balance])

        df_clients = pd.DataFrame(data, columns=['ID', 'Name', 'Unique Link', 'Balance'])
        excel_path = os.path.join(EXCEL_FILES_DIR, 'معلومات الزبائن الأساسية.xlsx')
        df_clients.to_excel(excel_path, index=False)

        bot_admin.send_document(call.message.chat.id, open(excel_path, 'rb'))
        os.remove(excel_path)
        main_menu(call.message.chat.id)

    @bot_admin.callback_query_handler(func=lambda call: call.data.startswith('export_transactions_'))
    def export_transactions_callback(call):

        chat_id = call.message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        bot_admin.answer_callback_query(call.id)
        # _, client_id, client_name = call.data.split('_')
        client_id = call.data.split('_')[2]
        client_name= call.data.split('_')[3]
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transactions WHERE client_id = ?', (client_id,))
        transactions = cursor.fetchall()
        conn.close()

        data = []
        for transaction in transactions:
            transaction_id = transaction[0]
            client_id = transaction[1]
            amount = f"{transaction[2]} د.ع"
            description = transaction[3]
            date = transaction[4]
            data.append([transaction_id, client_name, amount, description, date])

        df_transactions = pd.DataFrame(data, columns=['Transaction ID', 'Client name', 'Amount', 'Description', 'Date'])
        excel_path = os.path.join(EXCEL_FILES_DIR, f'معاملات الزبون {client_name}.xlsx')
        df_transactions.to_excel(excel_path, index=False)

        bot_admin.send_document(call.message.chat.id, open(excel_path, 'rb'))
        os.remove(excel_path)
        main_menu(call.message.chat.id)

    @bot_admin.callback_query_handler(func=lambda call: call.data == 'export_all_clients')
    def export_all_clients_callback(call):

        chat_id = call.message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        bot_admin.answer_callback_query(call.id)
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients')
        clients = cursor.fetchall()
        cursor.execute('SELECT * FROM transactions')
        transactions = cursor.fetchall()
        conn.close()

        data = []
        for client in clients:
            client_id = client[0]
            client_name = client[1]
            client_link = client[3]
            client_balance = f"{client[4]} د.ع"
            for transaction in transactions:
                if transaction[1] == client_id:
                    data.append([client_id, client_name, client_link, client_balance, transaction[3], transaction[4]])

        df_all = pd.DataFrame(data, columns=['Client ID', 'Name', 'Unique Link', 'Balance', 'Transaction Type', 'Date'])
        excel_path = os.path.join(EXCEL_FILES_DIR, 'معلومات كل الزبائن ومعاملاتهم.xlsx')
        df_all.to_excel(excel_path, index=False)

        bot_admin.send_document(call.message.chat.id, open(excel_path, 'rb'))
        os.remove(excel_path)
        main_menu(call.message.chat.id)

    @bot_admin.message_handler(func=lambda message: message.text == 'اضافة عمولة')
    def add_commission_to_client(message):

        chat_id = message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        msg = bot_admin.send_message(message.chat.id, "يرجى مسح الQR Code الخاص بالزبون أو ارسال رقم المعرف الخاص به أو إسمه")
        bot_admin.register_next_step_handler(msg, process_commission_input)

    def process_commission_input(message):
        try:
            if message.photo:
                file_info = bot_client.get_file(message.photo[-1].file_id)
                downloaded_file = bot_client.download_file(file_info.file_path)
                qr_image_path = "scanned_qr.png"
                with open(qr_image_path, 'wb') as new_file:
                    new_file.write(downloaded_file)
                img = cv2.imread(qr_image_path)
                decoded_objects = decode(img)
                if decoded_objects:
                    client_link = decoded_objects[0].data.decode('utf-8')
                    conn = sqlite3.connect('clients.db')
                    cursor = conn.cursor()
                    cursor.execute('SELECT * FROM clients WHERE unique_link = ?', (client_link,))
                    client = cursor.fetchone()
                    conn.close()
                    client_id = client[0]
                    client_name = client[1]
                    client_balance = client[4]
                    bot_admin.send_message(message.chat.id,f"إسم الزبون : {client_name}\nرقم معرف الزبون : {client_id}\nرصيد الزبون الحالي : {client_balance}")
                    msg = bot_admin.send_message(message.chat.id, "أدخل قيمة العمولة:",reply_markup=get_cancel_markup())
                    bot_admin.register_next_step_handler(msg, process_commission, client_id)
                else:
                    bot_admin.send_message(message.chat.id, "تعذر قراءة رمز QR Code. يرجى المحاولة مرة أخرى.")
            else:
                input_data = message.text.strip()
                conn = sqlite3.connect('clients.db')
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM clients WHERE name = ? OR id = ?', (input_data, input_data))
                client = cursor.fetchone()
                conn.close()
                client_id = client[0]
                client_name = client[1]
                client_balance = client[4]
                bot_admin.send_message(message.chat.id,f"إسم الزبون : {client_name}\nرقم معرف الزبون : {client_id}\nرصيد الزبون الحالي : {client_balance}")
                msg = bot_admin.send_message(message.chat.id, "أدخل قيمة العمولة:",reply_markup=get_cancel_markup())
                bot_admin.register_next_step_handler(msg, process_commission, client_id)
        except Exception as e:
            bot_admin.reply_to(message, 'خطأ: ' + str(e))
    @bot_admin.message_handler(func=lambda message: message.text == 'سحب رصيد')
    def withdraw_balance(message):

        chat_id = message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        msg = bot_admin.send_message(message.chat.id, "يرجى إدخال اسم الزبون أو رقم معرف الزبون:")
        bot_admin.register_next_step_handler(msg, process_withdraw_balance)

    def process_withdraw_balance(message):
        try:
            client_identifier = message.text
            conn = sqlite3.connect('clients.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM clients WHERE name = ? OR id = ?', (client_identifier, client_identifier))
            client = cursor.fetchone()
            conn.close()

            if client:
                client_id = client[0]
                client_name = client[1]
                client_link = client[3]
                client_balance = client[4]
                bot_admin.send_message(message.chat.id, f"معلومات الزبون: \nرقم معرف الزبون : {client_id}\nإسم الزبون : {client_name}\nرصيد الزبون : {client_balance} د.ع")
                msg = bot_admin.send_message(message.chat.id, "أدخل مبلغ السحب:", reply_markup=get_cancel_markup())
                bot_admin.register_next_step_handler(msg, process_withdraw_amount, client)
            else:
                bot_admin.send_message(message.chat.id, "الزبون غير موجود.")
                main_menu(message.chat.id)
        except Exception as e:
            bot_admin.reply_to(message, 'خطأ: ' + str(e))

    def process_withdraw_amount(message, client):
        try:
            amount = float(message.text)
            client_id, name, qr_code, unique_link, balance, chat_id = client

            if amount <= balance:
                conn = sqlite3.connect('clients.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE clients SET balance = balance - ? WHERE id = ?', (amount, client_id))
                cursor.execute('INSERT INTO transactions (client_id, amount, description) VALUES (?, ?, ?)', (client_id, -amount, 'تم سحب رصيد'))
                conn.commit()
                conn.close()
                notify_client(message.chat.id,client_id, f"تم سحب رصيد بقيمة {amount} دينار من حسابك")
                bot_admin.send_message(message.chat.id, "تم خصم الرصيد بنجاح.")
            else:
                bot_admin.send_message(message.chat.id, "خطأ: قيمة السحب أكبر من رصيد الزبون.")

            main_menu(message.chat.id)
        except Exception as e:
            bot_admin.reply_to(message, 'خطأ: ' + str(e))
    @bot_admin.message_handler(func=lambda message: message.text == 'حذف زبون')
    def delete_client(message):

        chat_id = message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        msg = bot_admin.send_message(message.chat.id, "يرجى إدخال اسم الزبون أو رقم معرف الزبون:",reply_markup=get_cancel_markup())
        bot_admin.register_next_step_handler(msg, process_delete_client)

    def process_delete_client(message):
        try:
            client_identifier = message.text
            conn = sqlite3.connect('clients.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM clients WHERE name = ? OR id = ?', (client_identifier, client_identifier))
            client = cursor.fetchone()
            conn.close()

            if client:
                client_id = client[0]
                client_name = client[1]
                client_link = client[3]
                client_balance = client[4]
                bot_admin.send_message(message.chat.id, f"معلومات الزبون: \nرقم معرف الزبون : {client_id}\nإسم الزبون : {client_name}\nرصيد الزبون : {client_balance} د.ع")
                markup = types.InlineKeyboardMarkup()
                confirm_button = types.InlineKeyboardButton("تأكيد الحذف", callback_data=f"confirm_delete_{client_id}")
                cancel_button = types.InlineKeyboardButton("إلغاء", callback_data='cancel')
                markup.add(confirm_button,cancel_button)
                bot_admin.send_message(message.chat.id, "هل تريد بالتأكيد حذف هذا الزبون؟", reply_markup=markup)
            else:
                bot_admin.send_message(message.chat.id, "الزبون غير موجود.")
                main_menu(message.chat.id)
        except Exception as e:
            bot_admin.reply_to(message, 'خطأ: ' + str(e))

    @bot_admin.callback_query_handler(func=lambda call: call.data.startswith('confirm_delete_'))
    def confirm_delete_callback(call):

        chat_id = call.message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        bot_admin.answer_callback_query(call.id)
        client_id = int(call.data.split('_')[2])
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
        client = cursor.fetchone()
        if client:
            qr_code_path = client[2]
            if os.path.exists(qr_code_path):
                os.remove(qr_code_path)
            cursor.execute('DELETE FROM clients WHERE id = ?', (client_id,))
            cursor.execute('DELETE FROM transactions WHERE client_id = ?', (client_id,))
            conn.commit()
            bot_admin.send_message(call.message.chat.id, "تم حذف الزبون بنجاح.")
        else:
            bot_admin.send_message(call.message.chat.id, "الزبون غير موجود.")
        conn.close()
        main_menu(call.message.chat.id)

    @bot_admin.message_handler(func=lambda message: message.text == 'إضافة ادمن')
    def add_admin(message):
        chat_id = message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()
        cursor.execute('SELECT is_admin FROM users WHERE chat_id = ?', (chat_id,))
        is_user_admin = cursor.fetchone()

        # print(is_user_admin[0])


        cursor.execute("SELECT username, chat_id FROM users WHERE is_admin = FALSE")
        non_admin_users = cursor.fetchall()

        if non_admin_users:
            keyboard = [[types.InlineKeyboardButton(user[0], callback_data=f"add_admin_{user[1]}")] for user in non_admin_users]
            reply_markup = types.InlineKeyboardMarkup(keyboard)
            bot_admin.send_message(chat_id,"اختر يوزر لإضافته كأدمن:", reply_markup=reply_markup)
        else:
            bot_admin.send_message(chat_id,"لا يوجد يوزرات لإضافتهم.")
        conn.close()
    @bot_admin.callback_query_handler(func=lambda call: call.data.startswith('add_admin_'))
    def process_add_admin(call):
        chat_id = call.message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        print('hello')
        admin_chat_id = call.data.split('_')[2]
        print(f'admin : {admin_chat_id}')
        bot_admin.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        print(f"chat_id : {chat_id}")

        # تحديث حالة المستخدم ليصبح أدمن
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_admin = TRUE WHERE chat_id = ?", (admin_chat_id,))
        conn.commit()
        authorized_users.append(int(admin_chat_id))
        # authorized_users.extend(admin_chat_id)


        bot_admin.send_message(chat_id,text="تمت إضافة الادمن بنجاح.")

    @bot_admin.message_handler(func=lambda message: message.text == 'حذف ادمن')
    def remove_admin(message):
        chat_id = message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()
        cursor.execute('SELECT is_admin FROM users WHERE chat_id = ?', (chat_id,))
        is_user_admin = cursor.fetchone()

        cursor.execute("SELECT username, chat_id FROM users WHERE is_admin = TRUE")
        admin_users = cursor.fetchall()

        if admin_users:
            keyboard = [[types.InlineKeyboardButton(user[0], callback_data=f"remove_admin_{user[1]}")] for user in admin_users]
            reply_markup = types.InlineKeyboardMarkup(keyboard)
            bot_admin.send_message(chat_id, "اختر يوزر لحذفه كأدمن:", reply_markup=reply_markup)
        else:
            bot_admin.send_message(chat_id, "لا يوجد أدمنز لحذفهم.")
        conn.close()

    @bot_admin.callback_query_handler(func=lambda call: call.data.startswith('remove_admin_'))
    def process_remove_admin(call):
        chat_id = call.message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return
        admin_chat_id = call.data.split('_')[2]
        bot_admin.answer_callback_query(call.id)
        chat_id = call.message.chat.id

        # تحديث حالة المستخدم ليصبح ليس أدمن
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_admin = FALSE WHERE chat_id = ?", (admin_chat_id,))
        conn.commit()

        if int(admin_chat_id) in authorized_users:
            authorized_users.remove(int(admin_chat_id))

        bot_admin.send_message(chat_id, text="تم حذف الادمن بنجاح.")
        conn.close()

    @bot_admin.message_handler(func=lambda message: message.text == 'تغيير كلمة السر')
    def change_password(message):
        chat_id = message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return

        # طلب إدخال كلمة السر القديمة
        msg = bot_admin.send_message(chat_id, "الرجاء إدخال كلمة السر القديمة:")
        bot_admin.register_next_step_handler(msg, verify_old_password)

    def verify_old_password(message):
        chat_id = message.chat.id
        old_password = message.text

        # التحقق من كلمة السر القديمة
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM admin_settings WHERE id = 1")
        current_password = cursor.fetchone()[0]

        if old_password == current_password:
            # طلب إدخال كلمة السر الجديدة
            msg = bot_admin.send_message(chat_id, "الرجاء إدخال كلمة السر الجديدة:")
            bot_admin.register_next_step_handler(msg, get_new_password)
        else:
            bot_admin.send_message(chat_id, "كلمة السر القديمة غير صحيحة.")

        conn.close()

    def get_new_password(message):
        chat_id = message.chat.id
        new_password = message.text

        # طلب تأكيد كلمة السر الجديدة
        msg = bot_admin.send_message(chat_id, "الرجاء تأكيد كلمة السر الجديدة:")
        bot_admin.register_next_step_handler(msg, confirm_new_password, new_password)

    def confirm_new_password(message, new_password):
        global PASSWORD
        chat_id = message.chat.id
        confirm_password = message.text

        if new_password == confirm_password:
            # تحديث كلمة السر في قاعدة البيانات
            conn = sqlite3.connect('clients.db')
            cursor = conn.cursor()
            cursor.execute("UPDATE admin_settings SET password = ? WHERE id = 1", (new_password,))
            conn.commit()
            conn.close()
            PASSWORD = new_password
            bot_admin.send_message(chat_id, "تم تغيير كلمة السر بنجاح.")
        else:
            bot_admin.send_message(chat_id, "كلمة السر الجديدة غير متطابقة. حاول مرة أخرى.")

    @bot_admin.message_handler(func=lambda message: message.text == 'تغيير زمن الجلسة')
    def change_session_duration(message):
        chat_id = message.chat.id
        if not check_login(chat_id):
            bot_admin.send_message(chat_id, "يجب عليك تسجيل الدخول لاستخدام هذا البوت.")
            return

        # طلب إدخال زمن الجلسة الجديد بالدقائق
        msg = bot_admin.send_message(chat_id, "الرجاء إدخال زمن الجلسة الجديد بالدقائق:")
        bot_admin.register_next_step_handler(msg, update_session_duration)

    def update_session_duration(message):
        global login_duration
        chat_id = message.chat.id
        try:
            # تحويل زمن الجلسة المدخل إلى عدد صحيح
            new_duration = int(message.text)
            if new_duration <= 0:
                raise ValueError("زمن الجلسة يجب أن يكون عددًا موجبًا.")

            # تحديث زمن الجلسة في قاعدة البيانات
            conn = sqlite3.connect('clients.db')
            cursor = conn.cursor()
            cursor.execute("UPDATE admin_settings SET session_duration = ? WHERE id = 1", (new_duration,))
            conn.commit()
            conn.close()
            login_duration = new_duration
            bot_admin.send_message(chat_id, f"تم تغيير زمن الجلسة بنجاح إلى {new_duration} دقيقة.")
        except ValueError:
            bot_admin.send_message(chat_id, "الرجاء إدخال زمن جلسة صحيح (رقم موجب).")


    # bot_admin.polling()
    while True:
        try:
            bot_admin.polling(none_stop=True, interval=1)
        except ProxyError as e:
            print(f"Proxy error occurred: {e}")
            time.sleep(5)  # Wait 5 seconds before retrying
        except ConnectionError as e:
            print(f"Connection error occurred: {e}")
            time.sleep(5)  # Wait 5 seconds before retrying
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            time.sleep(5)  # Wait 5 seconds before retrying

admin_bot_thread = Thread(target=start_admin_bot)
client_bot_thread = Thread(target=start_client_bot)
admin_bot_thread.start()
client_bot_thread.start()

admin_bot_thread.join()
client_bot_thread.join()
