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
# ⚡ SETTINGS
# =====================
TOKEN = "8257996186:AAE09LpmB9sbXUR_JpTTftPE08qI5LgTcUs"

# DATABASE
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
# 🟢 HELPERS
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
    cursor.execute("INSERT OR REPLACE INTO custom_words(chat_id, word, response) VALUES(?,?,?)",
                   (chat_id, word.lower(), response))
    conn.commit()

def remove_custom_word(chat_id, word):
    cursor.execute("DELETE FROM custom_words WHERE chat_id=? AND word=?",
                   (chat_id, word.lower()))
    conn.commit()

def list_custom_words(chat_id):
    cursor.execute("SELECT word, response FROM custom_words WHERE chat_id=?", (chat_id,))
    return cursor.fetchall()

# =====================
# 🟢 COMMANDS
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello 👋 Bot is online ✅")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong! 🏓")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("✅ Anti-link", callback_data='toggle_anti_link'),
            InlineKeyboardButton("✅ Auto-reply", callback_data='toggle_auto')
        ],
        [
            InlineKeyboardButton("✅ Bad words", callback_data='toggle_bad'),
            InlineKeyboardButton("✅ Anti-spam", callback_data='toggle_spam')
        ],
        [
            InlineKeyboardButton("✅ Welcome", callback_data='toggle_welcome')
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Bot settings:", reply_markup=reply_markup)

# =====================
# 🟢 BUTTON HANDLER (FIXED)
# =====================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    settings = get_group_settings(chat_id)

    user = query.from_user
    member = await query.message.chat.get_member(user.id)

    if member.status not in ["administrator", "creator"]:
        await query.edit_message_text("❌ Only admins can use this")
        return

    if query.data == "toggle_anti_link":
        toggle_setting(chat_id, "anti_link", not settings["anti_link"])
        await query.edit_message_text(f"Anti-link: {not settings['anti_link']}")

    elif query.data == "toggle_auto":
        toggle_setting(chat_id, "auto_reply", not settings["auto_reply"])
        await query.edit_message_text(f"Auto-reply: {not settings['auto_reply']}")

    elif query.data == "toggle_bad":
        toggle_setting(chat_id, "bad_word", not settings["bad_word"])
        await query.edit_message_text(f"Bad words: {not settings['bad_word']}")

    elif query.data == "toggle_spam":
        toggle_setting(chat_id, "spam", not settings["spam"])
        await query.edit_message_text(f"Anti-spam: {not settings['spam']}")

    elif query.data == "toggle_welcome":
        toggle_setting(chat_id, "welcome", not settings["welcome"])
        await query.edit_message_text(f"Welcome: {not settings['welcome']}")

# =====================
# 🟢 FEATURES
# =====================
async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = get_group_settings(chat_id)
    if not settings["auto_reply"] or not update.message.text:
        return

    text = update.message.text.lower()

    if "hello" in text or "سلام" in text:
        await update.message.reply_text(f"Hello {update.effective_user.first_name} 👋")

    elif "how are you" in text:
        await update.message.reply_text("I'm fine 😎")

    else:
        resp = get_custom_response(chat_id, text)
        if resp:
            await update.message.reply_text(resp)

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = get_group_settings(chat_id)
    if not settings["welcome"]:
        return

    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            await update.message.reply_text(f"👋 Welcome {member.full_name}!")

async def anti_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = get_group_settings(chat_id)

    if not settings["anti_link"] or not update.message.text:
        return

    text = update.message.text
    user_id = update.effective_user.id
    chat = update.effective_chat

    if re.search(r"http[s]?://|t\.me|www\.", text):
        try:
            await update.message.delete()
        except:
            pass

        warns[user_id] = warns.get(user_id, 0) + 1

        if warns[user_id] >= 3:
            try:
                await chat.ban_member(user_id)
                warns[user_id] = 0
            except:
                await update.message.reply_text("❌ Bot needs admin rights")
        else:
            await update.message.reply_text("❌ Links are not allowed!")

async def bad_word_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = get_group_settings(chat_id)

    if not settings["bad_word"] or not update.message.text:
        return

    text = update.message.text.lower()

    for word in bad_words:
        if word in text:
            try:
                await update.message.delete()
                await update.message.reply_text("🚫 Bad language is not allowed!")
            except:
                pass
            break

async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = get_group_settings(chat_id)

    if not settings["spam"]:
        return

    user_id = update.effective_user.id
    spam_counts[user_id] = spam_counts.get(user_id, 0) + 1

    if spam_counts[user_id] > 5:
        try:
            await update.message.delete()
        except:
            pass

    context.job_queue.run_once(lambda ctx: spam_counts.pop(user_id, None), 10)

# =====================
# 🟢 RUN BOT
# =====================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ping", ping))
app.add_handler(CommandHandler("menu", menu))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_link))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bad_word_filter))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_spam))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))

app.add_handler(CallbackQueryHandler(button))

app.run_polling()
