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


# 4. لوحة الأزرار الرئيسية
def main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_pdf = types.InlineKeyboardButton("📄 طريقة ترجمة ملف PDF", callback_data="how_pdf")
    btn_trans = types.InlineKeyboardButton("🌐 مترجم فوري للنصوص", callback_data="trans_mode")
    btn_info = types.InlineKeyboardButton("ℹ️ حسابي", callback_data="my_info")
    btn_help = types.InlineKeyboardButton("💡 الأوامر", callback_data="help_cmd")
    markup.add(btn_pdf)
    markup.add(btn_trans)
    markup.add(btn_info, btn_help)
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
        "1️⃣ **ترجمة ملفات PDF**: أرسل أي ملف `PDF` مباشرة في المحادثة، وسيرسله لك مترجماً بين السطور باللون الأحمر.\n"
        "2️⃣ **ترجمة النصوص**: اكتب `/tr <النص>` لترجمته فورياً.\n"
        "3️⃣ **معلومات حسابك**: اكتب `/info` لعرض بياناتك والآيدي."
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")


# 7. استلام وترجمة ملفات PDF (الميزة الأساسية)
@bot.message_handler(content_types=['document'])
def handle_document(message):
    doc = message.document
    file_name = doc.file_name or "document.pdf"

    if not file_name.lower().endswith(".pdf"):
        bot.reply_to(message, "⚠️ عذراً، البوت مخصص لترجمة ملفات الـ PDF فقط. يرجى إرسال ملف بصيغة `.pdf`.")
        return

    # إشعار البدء
    status_msg = bot.reply_to(
        message,
        f"📥 **تم استلام ملف الـ PDF**: `{file_name}`\n"
        f"⏳ **جاري تنزيل الملف وترجمته بين السطور باللون الأحمر... يرجى الانتظار لحظات.**",
        parse_mode="Markdown"
    )

    temp_dir = os.path.join(os.path.dirname(__file__), "temp_downloads")
    os.makedirs(temp_dir, exist_ok=True)

    input_path = os.path.join(temp_dir, f"in_{message.chat.id}_{int(time.time())}.pdf")
    output_path = os.path.join(temp_dir, f"translated_{file_name}")

    try:
        t_start = time.time()
        print(f"[{time.strftime('%X')}] تلقي ملف PDF جديد من المستخدم {message.chat.id}: {file_name}")
        # تنزيل الملف من تليجرام
        file_info = bot.get_file(doc.file_id)
        downloaded = bot.download_file(file_info.file_path)
        with open(input_path, 'wb') as f:
            f.write(downloaded)

        print(f"[{time.strftime('%X')}] بدأ المحرك بترجمة الملف...")
        # استدعاء محرك الترجمة
        from pdf_engine import translate_pdf_file
        translate_pdf_file(input_path, output_path)
        print(f"[{time.strftime('%X')}] تمت الترجمة في {time.time() - t_start:.2f} ثانية! جاري إرسال الملف...")

        # إرسال الملف المترجم للمستخدم
        with open(output_path, 'rb') as f_out:
            caption = (
                f"✅ **تمت ترجمة ملفك بنجاح!** 📄✨\n\n"
                f"• تم وضع المعاني بدقة فوق كل كلمة باللون الأحمر.\n"
                f"• تم الحفاظ على المصطلحات الطبية والأكاديمية.\n"
                f"• تم ضبط المحاذاة لمنع التداخل بين السطور.\n"
                f"• استغرقت المعالجة: `{time.time() - t_start:.1f}` ثانية ⚡"
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
    if call.data == "how_pdf":
        bot.send_message(
            call.message.chat.id,
            "📄 **طريقة ترجمة ملف الـ PDF**:\n\n"
            "فقط قم بسحب أو إرسال ملف الـ PDF كملف في هذه المحادثة مباشرة، "
            "وسيقوم البوت تلقائياً بمعالجته وإرسال النسخة المترجمة لك في ثوانٍ!",
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)
    elif call.data == "trans_mode":
        bot.send_message(
            call.message.chat.id,
            "🌐 اكتب الأمر `/tr` متبوعاً بأي جملة لترجمتها فوراً.",
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)
    elif call.data == "my_info":
        handle_info(call.message)
        bot.answer_callback_query(call.id)
    elif call.data == "help_cmd":
        handle_help(call.message)
        bot.answer_callback_query(call.id)


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
