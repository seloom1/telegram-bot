# -*- coding: utf-8 -*-
"""
Telegram Multi-Purpose & PDF Translator Bot (24/7 Cloud Ready - Zero VPS)
بوت تليجرام متكامل لترجمة ملفات PDF بين السطور + الترجمة الفورية + دعم السحابة 24/7
"""

import os
import sys
import threading
import time
import telebot
from telebot import types
from flask import Flask

# Force UTF-8 on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 1. قراءة التوكن
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("BOT_TOKEN="):
                    BOT_TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

# 2. خادم ويب لإبقاء البوت نشطاً على السحابة
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
    <head><meta charset="utf-8"><title>حالة البوت</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px; background: #0f172a; color: white;">
        <h1 style="color: #4ade80;">🚀 البوت ومترجم الـ PDF يعمل بنجاح 24/7!</h1>
        <p>أرسل أي ملف PDF للبوت في تليجرام وسيترجمه فوراً بين السطور باللون الأحمر.</p>
    </body>
    </html>
    """

@app.route('/healthz')
def health():
    return "OK", 200

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def start_keep_alive():
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()


# 3. التحقق من التوكن
if not BOT_TOKEN:
    print("[!] خطأ: لم يتم العثور على BOT_TOKEN. يرجى وضعه في ملف .env أو متغيرات البيئة.")
    sys.exit(1)

bot = telebot.TeleBot(BOT_TOKEN)


# 4. إعدادات المستخدم وحجم ولون الخط
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "user_settings.json")

DEFAULT_SETTINGS = {
    'font_size': 6.8,
    'size_label': 'متوسط (6.8pt)',
    'color': [0.85, 0.0, 0.0],
    'color_name': 'red',
    'color_label': '🔴 أحمر'
}

SIZE_OPTIONS = {
    'size_small': {'font_size': 5.5, 'size_label': '🔹 صغير (5.5pt)'},
    'size_medium': {'font_size': 6.8, 'size_label': '🔹 متوسط (6.8pt)'},
    'size_large': {'font_size': 7.8, 'size_label': '🔹 كبير (7.8pt)'},
    'size_xlarge': {'font_size': 9.0, 'size_label': '🔹 كبير جداً (9.0pt)'}
}

COLOR_OPTIONS = {
    'color_red': {'color': [0.85, 0.0, 0.0], 'color_name': 'red', 'color_label': '🔴 أحمر'},
    'color_blue': {'color': [0.0, 0.3, 0.85], 'color_name': 'blue', 'color_label': '🔵 أزرق'},
    'color_green': {'color': [0.0, 0.55, 0.15], 'color_name': 'green', 'color_label': '🟢 أخضر'},
    'color_purple': {'color': [0.55, 0.0, 0.65], 'color_name': 'purple', 'color_label': '🟣 بنفسجي'},
    'color_orange': {'color': [0.9, 0.4, 0.0], 'color_name': 'orange', 'color_label': '🟠 برتقالي'},
    'color_black': {'color': [0.08, 0.08, 0.08], 'color_name': 'black', 'color_label': '⚫ أسود'}
}

def get_user_settings(chat_id):
    chat_id = str(chat_id)
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if chat_id in data:
                    res = DEFAULT_SETTINGS.copy()
                    res.update(data[chat_id])
                    return res
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def update_user_settings(chat_id, new_vals):
    chat_id = str(chat_id)
    data = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            pass
    user_conf = data.get(chat_id, DEFAULT_SETTINGS.copy())
    user_conf.update(new_vals)
    data[chat_id] = user_conf
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return user_conf

# لوحات الأزرار
def settings_main_markup(chat_id):
    conf = get_user_settings(chat_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_size = types.InlineKeyboardButton(f"📏 حجم الخط: {conf['size_label']}", callback_data="menu_size")
    btn_color = types.InlineKeyboardButton(f"🎨 اللون: {conf['color_label']}", callback_data="menu_color")
    btn_reset = types.InlineKeyboardButton("🔄 إعادة ضبط للافتراضي", callback_data="set_reset")
    markup.add(btn_size)
    markup.add(btn_color)
    markup.add(btn_reset)
    return markup

def size_menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b1 = types.InlineKeyboardButton("صغير (5.5pt)", callback_data="opt_size_small")
    b2 = types.InlineKeyboardButton("متوسط (6.8pt)", callback_data="opt_size_medium")
    b3 = types.InlineKeyboardButton("كبير (7.8pt)", callback_data="opt_size_large")
    b4 = types.InlineKeyboardButton("كبير جداً (9.0pt)", callback_data="opt_size_xlarge")
    back = types.InlineKeyboardButton("🔙 رجوع", callback_data="menu_settings_main")
    markup.add(b1, b2)
    markup.add(b3, b4)
    markup.add(back)
    return markup

def color_menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b1 = types.InlineKeyboardButton("🔴 أحمر", callback_data="opt_color_red")
    b2 = types.InlineKeyboardButton("🔵 أزرق", callback_data="opt_color_blue")
    b3 = types.InlineKeyboardButton("🟢 أخضر", callback_data="opt_color_green")
    b4 = types.InlineKeyboardButton("🟣 بنفسجي", callback_data="opt_color_purple")
    b5 = types.InlineKeyboardButton("🟠 برتقالي", callback_data="opt_color_orange")
    b6 = types.InlineKeyboardButton("⚫ أسود", callback_data="opt_color_black")
    back = types.InlineKeyboardButton("🔙 رجوع", callback_data="menu_settings_main")
    markup.add(b1, b2)
    markup.add(b3, b4)
    markup.add(b5, b6)
    markup.add(back)
    return markup

# 5. لوحة الأزرار الرئيسية
def main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_pdf = types.InlineKeyboardButton("📄 طريقة ترجمة ملف PDF", callback_data="how_pdf")
    btn_settings = types.InlineKeyboardButton("⚙️ إعدادات الخط واللون", callback_data="menu_settings_main")
    btn_trans = types.InlineKeyboardButton("🌐 مترجم فوري للنصوص", callback_data="trans_mode")
    btn_info = types.InlineKeyboardButton("ℹ️ حسابي", callback_data="my_info")
    markup.add(btn_pdf)
    markup.add(btn_settings)
    markup.add(btn_trans, btn_info)
    return markup


# 5. الترحيب /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_name = message.from_user.first_name or "صديقي"
    text = (
        f"مرحباً بك يا {user_name}! 🌹\n\n"
        f"أنا **بوت مترجم ملفات PDF التفاعلي**.\n\n"
        f"📥 **كيف تستخدم البوت؟**\n"
        f"فقط **أرسل لي أي ملف PDF** (محاضرة، كتاب، تقرير طبي...)، "
        f"وسأقوم بترجمته ووضع المعنى العربي فوق كل كلمة باللون الأحمر وإعادة إرساله لك فوراً كملف PDF جاهز! 📄✨"
    )
    bot.reply_to(message, text, parse_mode="Markdown", reply_markup=main_keyboard())


# 6. المساعدة /help
@bot.message_handler(commands=['help'])
def handle_help(message):
    help_text = (
        "📌 **دليل استخدام البوت**:\n\n"
        "1️⃣ **ترجمة ملفات PDF**: أرسل أي ملف `PDF` مباشرة في المحادثة، وسيرسله لك مترجماً بين السطور باللون والحجم الذي تختاره.\n"
        "2️⃣ **تخصيص الخط واللون**: اكتب `/settings` لتغيير حجم خط الترجمة ولونه (أحمر، أزرق، أخضر، بنفسجي...).\n"
        "3️⃣ **ترجمة النصوص**: اكتب `/tr <النص>` لترجمته فورياً.\n"
        "4️⃣ **معلومات حسابك**: اكتب `/info` لعرض بياناتك والآيدي."
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")


# 7. إعدادات حجم الخط واللون /settings
@bot.message_handler(commands=['settings', 'options', 'font', 'color'])
def handle_settings(message):
    conf = get_user_settings(message.chat.id)
    text = (
        "⚙️ **لوحة التحكم بإعدادات خط ولون الترجمة**:\n\n"
        f"• **حجم الخط الحالي**: `{conf['size_label']}`\n"
        f"• **لون الترجمة الحالي**: `{conf['color_label']}`\n\n"
        "اختر ما تريد تعديله من الأزرار أدناه:"
    )
    bot.reply_to(message, text, parse_mode="Markdown", reply_markup=settings_main_markup(message.chat.id))


# 8. استلام وترجمة ملفات PDF (الميزة الأساسية)
@bot.message_handler(content_types=['document'])
def handle_document(message):
    doc = message.document
    file_name = doc.file_name or "document.pdf"

    if not file_name.lower().endswith(".pdf"):
        bot.reply_to(message, "⚠️ عذراً، البوت مخصص لترجمة ملفات الـ PDF فقط. يرجى إرسال ملف بصيغة `.pdf`.")
        return

    # قراءة تفضيلات المستخدم للحجم واللون
    user_conf = get_user_settings(message.chat.id)
    chosen_size = user_conf['font_size']
    chosen_color = user_conf['color']
    size_label = user_conf['size_label']
    color_label = user_conf['color_label']

    # إشعار البدء
    status_msg = bot.reply_to(
        message,
        f"📥 **تم استلام ملف الـ PDF**: `{file_name}`\n"
        f"⚙️ **الإعدادات**: خط `{size_label}` | لون `{color_label}`\n"
        f"⏳ **جاري ترجمة النصوص والمخططات التوضيحية... يرجى الانتظار ثوانٍ معدودة.**",
        parse_mode="Markdown"
    )

    temp_dir = os.path.join(os.path.dirname(__file__), "temp_downloads")
    os.makedirs(temp_dir, exist_ok=True)

    input_path = os.path.join(temp_dir, f"in_{message.chat.id}_{int(time.time())}.pdf")
    output_path = os.path.join(temp_dir, f"translated_{file_name}")

    try:
        t_start = time.time()
        print(f"[{time.strftime('%X')}] تلقي ملف PDF جديد من المستخدم {message.chat.id}: {file_name} (حجم {chosen_size}, لون {color_label})")
        # تنزيل الملف من تليجرام
        file_info = bot.get_file(doc.file_id)
        downloaded = bot.download_file(file_info.file_path)
        with open(input_path, 'wb') as f:
            f.write(downloaded)

        print(f"[{time.strftime('%X')}] بدأ المحرك بترجمة النصوص والمخططات...")
        # استدعاء محرك الترجمة مع الحجم واللون وتقنية OCR للمخططات
        from pdf_engine import translate_pdf_file
        translate_pdf_file(
            input_path,
            output_path,
            font_size=chosen_size,
            color=chosen_color,
            enable_ocr=True
        )
        print(f"[{time.strftime('%X')}] تمت الترجمة في {time.time() - t_start:.2f} ثانية! جاري إرسال الملف...")

        # إرسال الملف المترجم للمستخدم
        with open(output_path, 'rb') as f_out:
            caption = (
                f"✅ **تمت ترجمة ملفك بنجاح!** 📄✨\n\n"
                f"• حجم الخط: `{size_label}` | اللون: `{color_label}`\n"
                f"• شملت الترجمة نصوص ومخططات الـ PDF التوضيحية بدقة 🩺\n"
                f"• تم الحفاظ التام على المصطلحات الطبية والأكاديمية.\n"
                f"• استغرقت المعالجة: `{time.time() - t_start:.1f}` ثانية ⚡\n\n"
                f"💡 *لتغيير حجم الخط أو اللون أرسل الأمر:* /settings"
            )
            bot.send_document(
                message.chat.id,
                f_out,
                caption=caption,
                parse_mode="Markdown",
                reply_to_message_id=message.message_id
            )

        print(f"[{time.strftime('%X')}] تم إرسال الملف المترجم بنجاح إلى المستخدم {message.chat.id}")

        # حذف رسالة الانتظار
        try:
            bot.delete_message(message.chat.id, status_msg.message_id)
        except Exception:
            pass

    except Exception as e:
        print(f"[{time.strftime('%X')}] خطأ أثناء معالجة الملف: {e}")
        bot.reply_to(message, f"❌ حدث خطأ أثناء معالجة الملف:\n`{e}`", parse_mode="Markdown")

    finally:
        # تنظيف الملفات المؤقتة
        if os.path.exists(input_path):
            try: os.remove(input_path)
            except Exception: pass
        if os.path.exists(output_path):
            try: os.remove(output_path)
            except Exception: pass


# 8. ترجمة النصوص السريعة /tr
@bot.message_handler(commands=['tr', 'translate'])
def handle_translate(message):
    query = message.text.split(maxsplit=1)
    if len(query) < 2:
        bot.reply_to(message, "⚠️ يرجى كتابة النص بعد الأمر، مثال:\n`/tr Medical microbiology`", parse_mode="Markdown")
        return

    text_to_translate = query[1].strip()
    try:
        from deep_translator import GoogleTranslator
        has_arabic = any('\u0600' <= char <= '\u06FF' for char in text_to_translate)
        target_lang = 'en' if has_arabic else 'ar'
        translated = GoogleTranslator(source='auto', target=target_lang).translate(text_to_translate)
        bot.reply_to(message, f"🌐 **الترجمة**:\n\n`{translated}`", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ أثناء الترجمة: {e}")


# 9. معلومات الحساب /info
@bot.message_handler(commands=['info'])
def handle_info(message):
    user = message.from_user
    info_text = (
        "📋 **بيانات حسابك**:\n\n"
        f"• **الاسم**: {user.first_name}\n"
        f"• **المعرف**: @{user.username if user.username else 'لا يوجد'}\n"
        f"• **الآيدي**: `{user.id}`"
    )
    bot.reply_to(message, info_text, parse_mode="Markdown")


# 10. معالجة الأزرار التفاعلية
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    data = call.data

    if data == "how_pdf":
        bot.send_message(
            chat_id,
            "📄 **طريقة ترجمة ملف الـ PDF**:\n\n"
            "فقط قم بسحب أو إرسال ملف الـ PDF كملف في هذه المحادثة مباشرة، "
            "وسيقوم البوت تلقائياً بمعالجته وإرسال النسخة المترجمة لك في ثوانٍ!",
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)

    elif data == "trans_mode":
        bot.send_message(
            chat_id,
            "🌐 اكتب الأمر `/tr` متبوعاً بأي جملة لترجمتها فوراً.",
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)

    elif data == "my_info":
        handle_info(call.message)
        bot.answer_callback_query(call.id)

    elif data == "help_cmd":
        handle_help(call.message)
        bot.answer_callback_query(call.id)

    # قائمة الإعدادات الرئيسية
    elif data == "menu_settings_main":
        conf = get_user_settings(chat_id)
        text = (
            "⚙️ **لوحة التحكم بإعدادات خط ولون الترجمة**:\n\n"
            f"• **حجم الخط الحالي**: `{conf['size_label']}`\n"
            f"• **لون الترجمة الحالي**: `{conf['color_label']}`\n\n"
            "اختر ما تريد تعديله من الأزرار أدناه:"
        )
        try:
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="Markdown", reply_markup=settings_main_markup(chat_id))
        except Exception:
            bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=settings_main_markup(chat_id))
        bot.answer_callback_query(call.id)

    # قائمة اختيار الحجم
    elif data == "menu_size":
        text = "📏 **اختر حجم خط الترجمة المطلوب للملفات:**"
        bot.edit_message_text(text, chat_id, msg_id, parse_mode="Markdown", reply_markup=size_menu_markup())
        bot.answer_callback_query(call.id)

    # قائمة اختيار اللون
    elif data == "menu_color":
        text = "🎨 **اختر لون خط الترجمة المطلوب:**"
        bot.edit_message_text(text, chat_id, msg_id, parse_mode="Markdown", reply_markup=color_menu_markup())
        bot.answer_callback_query(call.id)

    # حفظ الحجم المختار
    elif data in SIZE_OPTIONS:
        chosen = SIZE_OPTIONS[data]
        update_user_settings(chat_id, chosen)
        conf = get_user_settings(chat_id)
        text = (
            f"✅ **تم ضبط حجم الخط بنجاح إلى**: `{chosen['size_label']}`\n\n"
            f"• **لون الترجمة الحالي**: `{conf['color_label']}`\n\n"
            "سيتم تطبيق هذا الحجم على جميع ملفاتك القادمة تلقائياً."
        )
        bot.edit_message_text(text, chat_id, msg_id, parse_mode="Markdown", reply_markup=settings_main_markup(chat_id))
        bot.answer_callback_query(call.id, f"تم اختيار: {chosen['size_label']}")

    # حفظ اللون المختار
    elif data in COLOR_OPTIONS:
        chosen = COLOR_OPTIONS[data]
        update_user_settings(chat_id, chosen)
        conf = get_user_settings(chat_id)
        text = (
            f"✅ **تم ضبط لون الترجمة بنجاح إلى**: `{chosen['color_label']}`\n\n"
            f"• **حجم الخط الحالي**: `{conf['size_label']}`\n\n"
            "سيتم تطبيق هذا اللون على جميع ملفاتك القادمة تلقائياً."
        )
        bot.edit_message_text(text, chat_id, msg_id, parse_mode="Markdown", reply_markup=settings_main_markup(chat_id))
        bot.answer_callback_query(call.id, f"تم اختيار: {chosen['color_label']}")

    # إعادة التعيين للافتراضي
    elif data == "set_reset":
        update_user_settings(chat_id, DEFAULT_SETTINGS)
        conf = get_user_settings(chat_id)
        text = (
            "🔄 **تمت استعادة الإعدادات الافتراضية بنجاح!**\n\n"
            f"• **حجم الخط**: `{conf['size_label']}`\n"
            f"• **اللون**: `{conf['color_label']}`"
        )
        bot.edit_message_text(text, chat_id, msg_id, parse_mode="Markdown", reply_markup=settings_main_markup(chat_id))
        bot.answer_callback_query(call.id, "تمت استعادة الإعدادات الافتراضية")


# 11. الرسائل العادية
@bot.message_handler(func=lambda message: True)
def handle_general_text(message):
    text = message.text.strip()
    if text in ["مرحبا", "مرحباً", "هلا", "السلام عليكم"]:
        bot.reply_to(message, f"أهلاً وسهلاً بك يا {message.from_user.first_name}! أرسل لي أي ملف PDF لأترجمه لك فوراً. 📄", reply_markup=main_keyboard())
    else:
        bot.reply_to(
            message,
            "💡 **ملاحظة**: لترجمة ملف، أرسل الملف كـ `Document` مباشرة.\nأو للترجمة النصية اكتب:\n`/tr " + text + "`",
            parse_mode="Markdown"
        )


# التشغيل
if __name__ == "__main__":
    print("=" * 60)
    print(" Telegram PDF Translator Bot is starting...")
    print("=" * 60)
    start_keep_alive()
    print("[+] البوت جاهز ويستقبل ملفات الـ PDF الآن بنجاح...")
    bot.infinity_polling(skip_pending=False)
