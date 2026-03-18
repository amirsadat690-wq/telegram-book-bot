import re
import sqlite3
import os
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

# =====================
# 🟢 دستورات
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام 👋 ربات فعال است")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong 🏓")

# ✅ پنل جدید
async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text("🎛 پنل مدیریت:", reply_markup=reply_markup)

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
        await query.edit_message_text("❌ فقط ادمین")
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
# 🟢 اجرا
# =====================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ping", ping))
app.add_handler(CommandHandler("panel", panel))  # ✅ جدید

app.add_handler(CallbackQueryHandler(button))

app.run_polling()
