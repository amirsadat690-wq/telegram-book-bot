import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

TOKEN = "8687515349:AAGgxslDiMG8v6astAbIp0dbSMha34xPA4s"

# Welcome message
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 Welcome to the Smart Book Bot!\n\n"
        "Send the name of any book.\n"
        "I will try to find a PDF or download link for you.\n\n"
        "Examples:\n"
        "Harry Potter\n"
        "ملت عشق\n"
        "Atomic Habits"
    )

# Search books
def search_book(title):
    url = f"https://openlibrary.org/search.json?title={title}"
    data = requests.get(url).json()

    if data["docs"]:
        book = data["docs"][0]

        title = book.get("title", "Unknown")
        author = book.get("author_name", ["Unknown"])[0]
        key = book.get("key")

        read_link = f"https://openlibrary.org{key}"

        return {
            "title": title,
            "author": author,
            "link": read_link
        }

    return None


# Handle messages
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text

    book = search_book(query)

    if book:

        message = (
            f"📚 {book['title']}\n"
            f"✍️ {book['author']}\n\n"
            f"📖 Read / Download:\n{book['link']}"
        )

        await update.message.reply_text(message)

    else:
        await update.message.reply_text("❌ Book not found. Try another title.")


# Create bot
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot is running...")

app.run_polling()