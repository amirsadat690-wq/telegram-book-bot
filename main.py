import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)

TOKEN = "PUT_YOUR_NEW_TOKEN_HERE"

warns = {}
anti_link_active = True
auto_reply_active = True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام 👋 ربات آنلاین است. همه قابلیت‌ها آماده‌اند ✅")


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong! 🏓")


async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_reply_active
    if not auto_reply_active:
        return

    text = update.message.text.lower()

    if "سلام" in text:
        await update.message.reply_text(f"سلام {update.effective_user.first_name} 👋")

    elif "خوبی" in text:
        await update.message.reply_text("مرسی! تو چطوری؟ 😎")


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [
            InlineKeyboardButton("✅ فعال کردن ضد لینک", callback_data="enable_antilink"),
            InlineKeyboardButton("❌ غیرفعال کردن ضد لینک", callback_data="disable_antilink"),
        ],
        [
            InlineKeyboardButton("✅ فعال کردن پاسخ خودکار", callback_data="enable_auto"),
            InlineKeyboardButton("❌ غیرفعال کردن پاسخ خودکار", callback_data="disable_auto"),
        ],
    ]

    await update.message.reply_text(
        "مدیریت ربات:", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global anti_link_active, auto_reply_active

    query = update.callback_query
    await query.answer()

    if query.data == "enable_antilink":
        anti_link_active = True
        await query.edit_message_text("ضد لینک ✅ فعال شد")

    elif query.data == "disable_antilink":
        anti_link_active = False
        await query.edit_message_text("ضد لینک ❌ غیرفعال شد")

    elif query.data == "enable_auto":
        auto_reply_active = True
        await query.edit_message_text("پاسخ خودکار ✅ فعال شد")

    elif query.data == "disable_auto":
        auto_reply_active = False
        await query.edit_message_text("پاسخ خودکار ❌ غیرفعال شد")


async def anti_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global warns, anti_link_active

    if not anti_link_active:
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
                await update.message.reply_text("👢 کاربر بن شد (۳ لینک ارسال کرد)")
            except:
                await update.message.reply_text("❌ ربات باید ادمین باشد")

        else:
            remaining = 3 - warns[user_id]
            await update.message.reply_text(f"❌ لینک ممنوع است! {remaining} اخطار باقی مانده")


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ping", ping))
app.add_handler(CommandHandler("menu", menu))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_link))

app.add_handler(CallbackQueryHandler(button))

app.run_polling()
