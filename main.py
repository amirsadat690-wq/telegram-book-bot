import sqlite3
import time
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = "8687515349:AAGgxslDiMG8v6astAbIp0dbSMha34xPA4s"
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

# ================= ROLE =================
async def get_role(user_id, chat_id):
    if user_id == OWNER_ID:
        return "owner"

    cursor.execute("SELECT role FROM admins WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    if res:
        return res[0]

    member = await bot.get_chat_member(chat_id, user_id)
    if member.is_chat_admin():
        return "admin"

    return "user"

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

# ================= ADMIN SYSTEM =================
@dp.message_handler(commands=['add_sudo'])
async def add_sudo(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        cursor.execute("INSERT INTO admins VALUES (?,?)", (user_id, "sudo"))
        conn.commit()
        await message.reply("🧠 سودو شد")

@dp.message_handler(commands=['add_admin'])
async def add_admin(message: types.Message):
    role = await get_role(message.from_user.id, message.chat.id)
    if role not in ["owner","sudo"]:
        return
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        cursor.execute("INSERT INTO admins VALUES (?,?)", (user_id, "admin"))
        conn.commit()
        await message.reply("🛡 ادمین شد")

@dp.message_handler(commands=['admins'])
async def admins(message: types.Message):
    cursor.execute("SELECT user_id, role FROM admins")
    users = cursor.fetchall()
    text = "👮‍♂️ لیست:\n"
    for u in users:
        text += f"{u[0]} ➜ {u[1]}\n"
    await message.reply(text)

# ================= PANEL =================
def page_locks():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔒 فحش", callback_data="lock_fosh"),
        InlineKeyboardButton("🔓 فحش", callback_data="unlock_fosh"),
        InlineKeyboardButton("🔒 لینک", callback_data="lock_link"),
        InlineKeyboardButton("🔓 لینک", callback_data="unlock_link"),
        InlineKeyboardButton("⏭ بعدی", callback_data="page_manage")
    )
    return kb

def page_manage():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔇 میوت", callback_data="mute"),
        InlineKeyboardButton("🔊 آنمیوت", callback_data="unmute"),
        InlineKeyboardButton("⏮ برگشت", callback_data="page_locks"),
        InlineKeyboardButton("⏭ بعدی", callback_data="page_stats")
    )
    return kb

def page_stats():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("📊 وضعیت", callback_data="status"),
        InlineKeyboardButton("⏮ برگشت", callback_data="page_manage")
    )
    return kb

@dp.message_handler(commands=['panel'])
async def panel(message: types.Message):
    role = await get_role(message.from_user.id, message.chat.id)
    if role not in ["owner","admin","sudo"]:
        return
    await message.reply("🎛 پنل:", reply_markup=page_locks())

# ================= CALLBACK =================
@dp.callback_query_handler()
async def callbacks(call):

    if call.data == "page_locks":
        await call.message.edit_text("🔒 قفل‌ها:", reply_markup=page_locks())

    elif call.data == "page_manage":
        await call.message.edit_text("👮‍♂️ مدیریت:", reply_markup=page_manage())

    elif call.data == "page_stats":
        await call.message.edit_text("📊 آمار:", reply_markup=page_stats())

    elif call.data == "lock_fosh":
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
        await call.message.edit_text(f"📊\nفحش: {fosh}\nلینک: {link}", reply_markup=page_stats())

# ================= MUTE =================
@dp.message_handler(commands=['mute'])
async def mute(message: types.Message):
    if not message.reply_to_message:
        return
    user_id = message.reply_to_message.from_user.id
    duration = 600
    end_time = int(time.time()) + duration

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

# ================= MAIN =================
@dp.message_handler()
async def main(message: types.Message):

    if not message.text:
        return

    text = message.text.lower()
    user_id = message.from_user.id

    # stats
    cursor.execute("SELECT * FROM stats WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    if res:
        cursor.execute("UPDATE stats SET messages=messages+1 WHERE user_id=?", (user_id,))
    else:
        cursor.execute("INSERT INTO stats VALUES (?,?,?,?)", (user_id,1,0,0))
    conn.commit()

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
            cursor.execute("UPDATE stats SET links=links+1 WHERE user_id=?", (user_id,))
            conn.commit()
            return await warn_user(message,"🚫 لینک")

    # bad words
    if get_setting("fosh")=="on":
        cursor.execute("SELECT word FROM bad_words")
        for w in cursor.fetchall():
            if w[0] in text:
                await message.delete()
                cursor.execute("UPDATE stats SET bad_words=bad_words+1 WHERE user_id=?", (user_id,))
                conn.commit()
                return await warn_user(message,"🚫 فحش")

# ================= RUN =================
loop = asyncio.get_event_loop()
loop.create_task(mute_checker())

executor.start_polling(dp)
