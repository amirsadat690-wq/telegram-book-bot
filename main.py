import re
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)
import logging

logging.basicConfig(level=logging.INFO)

# =====================
# ⚡ تنظیمات اولیه
# =====================
TOKEN = "8257996186:AAE09LpmB9sbXUR_JpTTftPE08qI5LgTcUs"

# دیتابیس
conn = sqlite3.connect("supergroup_bot.db", check_same_thread=False)
cursor = conn.cursor()

# ایجاد جدول‌ها
cursor.execute("""CREATE TABLE IF NOT EXISTS groups(
    chat_id INTEGER PRIMARY KEY,
    anti_link INTEGER DEFAULT 1,
    auto_reply INTEGER DEFAULT 1,
    bad_word INTEGER DEFAULT 1,
    spam INTEGER DEFAULT 1,
    welcome INTEGER DEFAULT 1
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS custom_words(
    chat_id INTEGER,
    word TEXT,
    response TEXT,
    PRIMARY KEY(chat_id, word)
)""")
conn.commit()

bad_words = ["کیر", "کص", "حرامزاده", "fuck", "shit"]
spam_counts = {}
warns = {}

# =====================
# 🟢 توابع کمکی
# =====================
def get_group_settings(chat_id):
    cursor.execute("SELECT * FROM groups WHERE chat_id=?", (chat_id,))
    row = cursor.fetchone()
    if row:
        return {
            "anti_link": bool(row[1]),
            "auto_reply": bool(row[2]),
            "bad_word": bool(row[3]),
            "spam": bool(row[4]),
            "welcome": bool(row[5])
        }
    else:
        cursor.execute("INSERT INTO groups(chat_id) VALUES(?)", (chat_id,))
        conn.commit()
        return get_group_settings(chat_id)

def toggle_setting(chat_id, setting, value):
    cursor.execute(f"UPDATE groups SET {setting}=? WHERE chat_id=?", (int(value), chat_id))
    conn.commit()

def get_custom_response(chat_id, word):
    cursor.execute("SELECT response FROM custom_words WHERE chat_id=? AND word=?", (chat_id, word.lower()))
    row = cursor.fetchone()
    return row[0] if row else None

def add_custom_word(chat_id, word, response):
    cursor.execute("INSERT OR REPLACE INTO custom_words(chat_id, word, response) VALUES(?,?,?)", (chat_id, word.lower(), response))
    conn.commit()

def remove_custom_word(chat_id, word):
    cursor.execute("DELETE FROM custom_words WHERE chat_id=? AND word=?", (chat_id, word.lower()))
    conn.commit()

def list_custom_words(chat_id):
    cursor.execute("SELECT word, response FROM custom_words WHERE chat_id=?", (chat_id,))
    return cursor.fetchall()

# =====================
# 🟢 دستورات اصلی
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام 👋 ربات حرفه‌ای سوپرگروه آنلاین است ✅")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong! 🏓")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = get_group_settings(chat_id)
    keyboard = [
        [
            InlineKeyboardButton("✅ ضد لینک", callback_data='toggle_anti_link'),
            InlineKeyboardButton("✅ پاسخ خودکار", callback_data='toggle_auto')
        ],
        [
            InlineKeyboardButton("✅ قفل فحش", callback_data='toggle_bad'),
            InlineKeyboardButton("✅ ضد اسپم", callback_data='toggle_spam')
        ],
        [
            InlineKeyboardButton("✅ خوش‌آمدگویی", callback_data='toggle_welcome')
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("مدیریت ربات:", reply_markup=reply_markup)

# =====================
# 🟢 دکمه‌ها
# =====================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    settings = get_group_settings(chat_id)
    user = query.from_user
    member = await query.message.chat.get_member(user.id)
    if member.status not in ["administrator", "creator"]:
        await query.edit_message_text("❌ فقط ادمین می‌تواند استفاده کند")
        return

if query.data == "toggle_anti_link":
        toggle_setting(chat_id, "anti_link", not settings["anti_link"])
        await query.edit_message_text(f"ضد لینک: {not settings['anti_link']}")
    elif query.data == "toggle_auto":
        toggle_setting(chat_id, "auto_reply", not settings["auto_reply"])
        await query.edit_message_text(f"پاسخ خودکار: {not settings['auto_reply']}")
    elif query.data == "toggle_bad":
        toggle_setting(chat_id, "bad_word", not settings["bad_word"])
        await query.edit_message_text(f"قفل فحش: {not settings['bad_word']}")
    elif query.data == "toggle_spam":
        toggle_setting(chat_id, "spam", not settings["spam"])
        await query.edit_message_text(f"ضد اسپم: {not settings['spam']}")
    elif query.data == "toggle_welcome":
        toggle_setting(chat_id, "welcome", not settings["welcome"])
        await query.edit_message_text(f"خوش‌آمدگویی: {not settings['welcome']}")

# =====================
# 🟢 قابلیت‌ها
# =====================
async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = get_group_settings(chat_id)
    if not settings["auto_reply"]: return

    text = update.message.text.lower()
    if "سلام" in text:
        await update.message.reply_text(f"سلام {update.effective_user.first_name} 👋")
    elif "خوبی" in text:
        await update.message.reply_text("مرسی! تو چطوری؟ 😎")
    else:
        resp = get_custom_response(chat_id, text)
        if resp: await update.message.reply_text(resp)

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = get_group_settings(chat_id)
    if not settings["welcome"]: return
    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            await update.message.reply_text(f"👋 خوش آمدی {member.full_name}!")

async def anti_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = get_group_settings(chat_id)
    if not settings["anti_link"]: return
    if not update.message.text: return

    text = update.message.text
    user_id = update.effective_user.id
    chat = update.effective_chat

    if re.search(r"http[s]?://|t\.me|www\.", text):
        try: await update.message.delete()
        except: pass
        warns[user_id] = warns.get(user_id, 0) + 1
        if warns[user_id] >= 3:
            try:
                await chat.ban_member(user_id)
                warns[user_id] = 0
                await update.message.reply_text(f"👢 {update.effective_user.first_name} بن شد (۳ لینک)")
            except:
                await update.message.reply_text("❌ ربات باید ادمین باشد")
        else:
            remaining = 3 - warns[user_id]
            await update.message.reply_text(f"❌ لینک ممنوع! {remaining} اخطار باقی")

async def bad_word_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = get_group_settings(chat_id)
    if not settings["bad_word"]: return
    if not update.message.text: return
    text = update.message.text.lower()
    for word in bad_words:
        if word in text:
            try:
                await update.message.delete()
                await update.message.reply_text("🚫 استفاده از الفاظ بد ممنوع است!")
            except: pass
            break

async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = get_group_settings(chat_id)
    if not settings["spam"]: return
    user_id = update.effective_user.id
    spam_counts[user_id] = spam_counts.get(user_id, 0) + 1
    if spam_counts[user_id] > 5:
        try: await update.message.delete()
        except: pass
    context.job_queue.run_once(lambda ctx: spam_counts.pop(user_id, None), 10)

# =====================
# 🟢 دستورات سفارشی
# =====================
async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("استفاده: /addword کلمه پاسخ")
        return
    word = context.args[0]
    response = " ".join(context.args[1:])
    chat_id = update.effective_chat.id
    add_custom_word(chat_id, word, response)
    await update.message.reply_text(f"✅ دستور '{word}' اضافه شد")

async def remove_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("استفاده: /removeword کلمه")
        return
    word = context.args[0]
    chat_id = update.effective_chat.id
    remove_custom_word(chat_id, word)
    await update.message.reply_text(f"✅ دستور '{word}' حذف شد")

async def list_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    words = list_custom_words(chat_id)
    if not words:
        await update.message.reply_text("❌ دستوری اضافه نشده")
        return
    text = "\n".join([f"{w[0]} → {w[1]}" for w in words])
    await update.message.reply_text(f"دستورات سفارشی:\n{text}")

# =====================
# 🟢 اجرای ربات
# =====================
app = ApplicationBuilder().token(TOKEN).build()

# دستورات پایه
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ping", ping))
app.add_handler(CommandHandler("menu", menu))
app.add_handler(CommandHandler("addword", add_word))
app.add_handler(CommandHandler("removeword", remove_word))
app.add_handler(CommandHandler("listwords", list_words))

# قابلیت‌ها
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_link))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bad_word_filter))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_spam))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))

# دکمه‌ها
app.add_handler(CallbackQueryHandler(button))

# اجرا
app.run_polling()
