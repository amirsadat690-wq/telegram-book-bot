import sqlite3
import time
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = "8257996186:AAE09LpmB9sbXUR_JpTTftPE08qI5LgTcUs"
OWNER_ID = 8500689915

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ================= DATABASE =================
conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT, value TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS bad_words (word TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS warnings (user_id INTEGER, count INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER, role TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS mutes (user_id INTEGER, chat_id INTEGER, end_time INTEGER)")
cursor.execute("""
CREATE TABLE IF NOT EXISTS stats (
user_id INTEGER,
messages INTEGER,
bad_words INTEGER,
links INTEGER
)
""")
conn.commit()

# ================= SETTINGS =================
def set_setting(key, value):
    cursor.execute("DELETE FROM settings WHERE key=?", (key,))
    cursor.execute("INSERT INTO settings VALUES (?,?)", (key, value))
    conn.commit()

def get_setting(key):
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = cursor.fetchone()
    return res[0] if res else "off"

# ================= WARN =================
async def warn_user(message, text):
    user_id = message.from_user.id

    cursor.execute("SELECT count FROM warnings WHERE user_id=?", (user_id,))
    res = cursor.fetchone()

    if res:
        count = res[0] + 1
        cursor.execute("UPDATE warnings SET count=? WHERE user_id=?", (count, user_id))
    else:
        count = 1
        cursor.execute("INSERT INTO warnings VALUES (?,?)", (user_id, count))

    conn.commit()

    if count >= 3:
        await bot.kick_chat_member(message.chat.id, user_id)
        await message.answer("🚫 بن شد")
    else:
        await message.answer(f"⚠️ اخطار {count}/3")

# ================= PANEL =================
def panel_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔒 فحش", callback_data="lock_fosh"),
        InlineKeyboardButton("🔓 فحش", callback_data="unlock_fosh"),
        InlineKeyboardButton("🔒 لینک", callback_data="lock_link"),
        InlineKeyboardButton("🔓 لینک", callback_data="unlock_link"),
        InlineKeyboardButton("📊 وضعیت", callback_data="status")
    )
    return kb

@dp.message_handler(commands=['panel'])
async def panel(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    await message.reply("🎛 پنل:", reply_markup=panel_kb())

# ================= CALLBACK =================
@dp.callback_query_handler()
async def callbacks(call):

    if call.data == "lock_fosh":
        set_setting("fosh","on")
        await call.answer("فعال شد")

    elif call.data == "unlock_fosh":
        set_setting("fosh","off")
        await call.answer("خاموش شد")

    elif call.data == "lock_link":
        set_setting("link","on")
        await call.answer("فعال شد")

    elif call.data == "unlock_link":
        set_setting("link","off")
        await call.answer("خاموش شد")

    elif call.data == "status":
        fosh = get_setting("fosh")
        link = get_setting("link")
        await call.message.edit_text(f"📊\nفحش: {fosh}\nلینک: {link}", reply_markup=panel_kb())

# ================= MUTE =================
@dp.message_handler(commands=['mute'])
async def mute(message: types.Message):
    if not message.reply_to_message:
        return
    user_id = message.reply_to_message.from_user.id
    end_time = int(time.time()) + 600

    cursor.execute("INSERT INTO mutes VALUES (?,?,?)", (user_id, message.chat.id, end_time))
    conn.commit()

    await bot.restrict_chat_member(message.chat.id, user_id,
        permissions=types.ChatPermissions(can_send_messages=False))

    await message.reply("🔇 میوت شد")

@dp.message_handler(commands=['unmute'])
async def unmute(message: types.Message):
    if not message.reply_to_message:
        return
    user_id = message.reply_to_message.from_user.id

    await bot.restrict_chat_member(message.chat.id, user_id,
        permissions=types.ChatPermissions(can_send_messages=True))

    await message.reply("🔊 آزاد شد")

# ================= AUTO UNMUTE =================
async def mute_checker():
    while True:
        now = int(time.time())
        cursor.execute("SELECT * FROM mutes")
        for user_id, chat_id, end_time in cursor.fetchall():
            if now >= end_time:
                await bot.restrict_chat_member(chat_id, user_id,
                    permissions=types.ChatPermissions(can_send_messages=True))
                cursor.execute("DELETE FROM mutes WHERE user_id=? AND chat_id=?", (user_id,chat_id))
                conn.commit()
        await asyncio.sleep(5)

# ================= SPAM =================
user_messages = {}
SPAM_LIMIT = 5
SPAM_TIME = 5

# ================= START =================
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("🤖 ربات فعال شد!")

# ================= MAIN =================
@dp.message_handler()
async def main(message: types.Message):

    if not message.text:
        return

    text = message.text.lower()
    user_id = message.from_user.id

    # spam
    now = time.time()
    user_messages.setdefault(user_id, []).append(now)
    user_messages[user_id] = [t for t in user_messages[user_id] if now-t<SPAM_TIME]

    if len(user_messages[user_id]) > SPAM_LIMIT:
        await message.delete()
        return await warn_user(message,"🚫 اسپم")

    # link
    if get_setting("link")=="on":
        if "http" in text or "t.me" in text:
            await message.delete()
            return await warn_user(message,"🚫 لینک")

    # bad words
    if get_setting("fosh")=="on":
        cursor.execute("SELECT word FROM bad_words")
        for w in cursor.fetchall():
            if w[0] in text:
                await message.delete()
                return await warn_user(message,"🚫 فحش")

    await message.reply("پیامت ثبت شد 👀")

# ================= RUN =================
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(mute_checker())
    executor.start_polling(dp, skip_updates=True)
