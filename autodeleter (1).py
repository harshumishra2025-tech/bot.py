import asyncio
from typing import Dict, Any

from pymongo import MongoClient

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import CallbackQuery
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
# ---------------------------
# CONFIG (DIRECT — SIMPLE)
# ---------------------------

BOT_TOKEN = "8410485776:AAHQwm82JUG424gw1BY6o3rjCbYQubcb2Y0"

OWNER_ID = 7995588921
OWNER_USERNAME = "GOODCHEAT01"
JOIN_CHECK_CHANNEL = "@promoters_botse"

MONGO_URI = "mongodb+srv://h17589479_db_user:W5l1NuSQ2cak8I04@cluster0.tkxlnpf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# ---------------------------
# BOT INIT (aiogram v3)
# ---------------------------

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

# ---------------------------
# DATABASE
# ---------------------------

mongo = MongoClient(MONGO_URI)
db = mongo["autodelete_bot"]

groups_col = db["groups"]
premium_col = db["premium"]
users_col = db["users"]
channels_col = db["channels"]

groups_col.create_index("chat_id", unique=True)
premium_col.create_index("user_id", unique=True)
users_col.create_index("user_id", unique=True)
channels_col.create_index("chat_id", unique=True)


from typing import Dict, Any

# ---------------------------
# DEFAULTS
# ---------------------------
DEFAULT_DELETE_TIME = 1
MIN_TIME = 1
MAX_TIME = 86400  # 24 hours (fixed comment)

# ---------------------------
# CACHE (IMPORTANT: int keys use karo)
# ---------------------------
group_settings: dict[int, dict] = {}
premium_users: set[int] = set()

# ---------------------------
# LOAD STATE (CACHE BUILDER)
# ---------------------------
def load_state():
    """
    🔄 Load DB → CACHE (startup only)
    """
    group_settings.clear()
    premium_users.clear()

    # groups cache
    for g in groups_col.find({}, {"chat_id": 1, "enabled": 1, "delete_time": 1}):
        group_settings[int(g["chat_id"])] = {
            "enabled": g.get("enabled", True),
            "delete_time": g.get("delete_time", DEFAULT_DELETE_TIME)
        }

    # premium cache
    for p in premium_col.find({}, {"user_id": 1}):
        premium_users.add(p["user_id"])

# ---------------------------
# GROUP DB HELPERS
# ---------------------------
def get_group(chat_id: int) -> dict:
    """
    ⚡ CACHE FIRST (FAST + LIVE SAFE)
    """
    chat_id = int(chat_id)

    # 1. cache hit
    if chat_id in group_settings:
        return group_settings[chat_id]

    # 2. DB fallback
    g = groups_col.find_one({"chat_id": chat_id})

    if not g:
        return {
            "enabled": True,
            "delete_time": DEFAULT_DELETE_TIME
        }

    # 3. cache update
    group_settings[chat_id] = {
        "enabled": g.get("enabled", True),
        "delete_time": g.get("delete_time", DEFAULT_DELETE_TIME)
    }

    return group_settings[chat_id]


# ---------------------------
# PREMIUM SYSTEM (OPTIMIZED)
# ---------------------------
def is_premium(user_id: int) -> bool:
    """
    💎 Premium check (fast cache + DB fallback)
    """
    if user_id == OWNER_ID:
        return True

    if user_id in premium_users:
        return True

    user = premium_col.find_one({"user_id": user_id})
    if user:
        premium_users.add(user_id)
        return True

    return False


# ---------------------------
# BOT PERMISSION CHECK
# ---------------------------
async def bot_has_delete_permission(chat_id: int) -> bool:
    """
    🔐 Check bot admin delete rights
    """
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id, me.id)

        if member.status == "creator":
            return True

        if member.status == "administrator":
            return bool(getattr(member, "can_delete_messages", False))

        return False

    except Exception:
        return False


# ---------------------------
# USER JOIN CHECK
# ---------------------------
async def user_joined_channel(user_id: int) -> bool:
    """
    📢 Check channel membership
    """
    if not JOIN_CHECK_CHANNEL:
        return True

    try:
        member = await bot.get_chat_member(JOIN_CHECK_CHANNEL, user_id)
        return member.status in ("member", "administrator", "creator")

    except Exception:
        return False


# ---------------------------
# ADMIN CHECK (GROUP CONTROL)
# ---------------------------
async def user_is_admin_or_owner(chat_id: int, user_id: int) -> bool:
    """
    👮 Permission system for commands
    """
    if user_id == OWNER_ID:
        return True

    try:
        member = await bot.get_chat_member(chat_id, user_id)

        if member.status == "creator":
            return True

        if member.status == "administrator":
            return bool(
                getattr(member, "can_delete_messages", False)
                or getattr(member, "can_manage_chat", False)
            )

        return False

    except Exception:
        return False



@dp.callback_query(lambda c: c.data == "verify_join")
async def verify_join_cb(query: CallbackQuery):

    user_id = query.from_user.id

    not_joined = []

    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ("member", "administrator", "creator"):
                not_joined.append(ch)
        except:
            not_joined.append(ch)

    # ❌ NOT JOINED
    if not_joined:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Join Channel 1", url="https://t.me/realchannel1"),
                InlineKeyboardButton(text="📢 Join Channel 2", url="https://t.me/realchannel2"),
            ],
            [
                InlineKeyboardButton(text="📢 Join Channel 3", url="https://t.me/realchannel3"),
            ],
            [
                InlineKeyboardButton(text="🔄 Verify Again", callback_data="verify_join")
            ]
        ])

        await query.message.edit_text(
            "❌ <b>You must join all channels first!</b>",
            reply_markup=kb,
            parse_mode="HTML"
        )
        return await query.answer("Join required channels ❌")

    # ✅ ALL JOINED → MAIN MENU
    me = await bot.get_me()

    kb_buttons = [
        [
            InlineKeyboardButton(
                text="➕ Add Group",
                url=f"https://t.me/{me.username}?startgroup=true"
            ),
            InlineKeyboardButton(
                text="➕ Add Channel",
                url=f"https://t.me/{me.username}?startchannel=true"
            )
        ],
        [
            InlineKeyboardButton(
                text="📘 Tutorial",
                callback_data="show_tutorial"
            )
        ]
    ]

    # 👑 OWNER MENU ADD
    if user_id == OWNER_ID:
        kb_buttons.append([
            InlineKeyboardButton(
                text="👑 Owner Panel",
                callback_data="owner_menu"
            )
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)

    await query.message.edit_text(
        "✅ <b>Verification Successful!</b>\n\nNow you can use the bot 👇",
        reply_markup=kb,
        parse_mode="HTML"
    )

    await query.answer("Access granted ✅")
    


@dp.callback_query(lambda c: c.data == "show_tutorial")
async def tutorial_cb(query: CallbackQuery):

    text = (
        "<b>🤖 BOT TUTORIAL & COMMANDS</b>\n\n"

        "1️⃣ Add the bot to your <b>group or channel</b> and promote it with "
        "<b>Delete Messages</b> permission.\n"
        "2️⃣ Convert group to a supergroup (recommended).\n"
        f"3️⃣ Join required channel: <code>{JOIN_CHECK_CHANNEL}</code>\n"
        "4️⃣ Set auto-delete delay using:\n"
        "   <code>/settime &lt;value&gt; [s/m/h]</code>\n\n"

        "<b>📌 Examples:</b>\n"
        "• <code>/settime 10s</code> → 10 seconds\n"
        "• <code>/settime 5m</code> → 5 minutes\n"
        "• <code>/settime 1h</code> → 1 hour (max 24h)\n\n"

        "<b>🛠️ ADMIN COMMANDS</b>\n"
        "/settime - Set delay\n"
        "/gettime - Show delay\n"
        "/enable - Enable auto delete\n"
        "/disable - Disable auto delete\n"
        "/id - Chat ID\n\n"

        "<b>💎 PREMIUM FEATURES</b>\n"
        "✅ Advanced auto delete\n"
        "✅ Bot + bot messages delete\n\n"

        "<b>💬 Owner:</b> @" + OWNER_USERNAME
    )

    try:
        await query.message.edit_text(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    except TelegramBadRequest as e:
        err = str(e)

        # message same hai to ignore
        if "message is not modified" in err:
            await query.answer("📘 Tutorial already open", show_alert=False)
            return

        # fallback (rare case)
        try:
            await query.message.reply(
                text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except:
            pass

    await query.answer()
    
# ---------------------------
# OWNER MENU
# ---------------------------
@dp.callback_query(lambda c: c.data == "owner_menu")
async def owner_menu_cb(query: CallbackQuery):
    if query.from_user.id != OWNER_ID:
        return await query.answer("Only owner can access.", show_alert=True)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Stats", callback_data="owner_stats")],
        [InlineKeyboardButton(text="💎 Premium list", callback_data="owner_premium_list")]
    ])

    await query.message.edit_text("👑 <b>Owner Panel</b>", reply_markup=kb)


# ---------------------------
# STATS (DB BASED 🔥)
# ---------------------------
@dp.callback_query(lambda c: c.data == "owner_stats")
async def owner_stats_cb(query: CallbackQuery):
    if query.from_user.id != OWNER_ID:
        return await query.answer("Only owner.", show_alert=True)

    total_groups = groups_col.count_documents({})
    total_users = users_col.count_documents({})
    total_channels = channels_col.count_documents({})
    total_premium = premium_col.count_documents({})

    text = (
        f"📊 <b>Bot Stats</b>\n\n"
        f"👥 Users: <b>{total_users}</b>\n"
        f"👨‍👩‍👧‍👦 Groups: <b>{total_groups}</b>\n"
        f"📢 Channels: <b>{total_channels}</b>\n"
        f"💎 Premium: <b>{total_premium}</b>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back", callback_data="owner_menu")]
    ])

    await query.message.edit_text(text, reply_markup=kb)


# ---------------------------
# PREMIUM LIST (WITH EXPIRY 🔥)
# ---------------------------
@dp.callback_query(lambda c: c.data == "owner_premium_list")
async def owner_premium_list_cb(query: CallbackQuery):
    if query.from_user.id != OWNER_ID:
        return await query.answer("Only owner.", show_alert=True)

    users = list(premium_col.find())

    if not users:
        return await query.message.edit_text("❌ No premium users.")

    text = "💎 <b>Premium Users</b>\n\n"

    for user in users:
        uid = user.get("user_id")
        expire = user.get("expire_at", 0)

        if expire > int(time.time()):
            remaining = expire - int(time.time())
            days = remaining // 86400
            status = f"{days} days left"
        else:
            status = "Expired"

        text += f"• <code>{escape(str(uid))}</code> → {status}\n"

        # limit text size (telegram safe)
        if len(text) > 3500:
            text += "\n⚠️ Too many users..."
            break

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back", callback_data="owner_menu")]
    ])

    await query.message.edit_text(text, reply_markup=kb)
    
# =========================
# SAFE REPLY WRAPPER FIX
# =========================
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery
from html import escape

async def safe_reply(
    msg: Message | CallbackQuery,
    text: str,
    parse_mode: str | None = "HTML",
    safe: bool = True,
    **kwargs
):
    """
    🔥 Ultimate Safe Reply Wrapper

    Features:
    - ✅ Optional HTML escaping (safe=True)
    - ✅ Supports HTML formatting when safe=False
    - ✅ Works for Message + CallbackQuery
    - ✅ Smart edit → fallback send
    - ✅ Handles "message not modified"
    """

    # Escape only if needed
    if safe:
        text = escape(text)

    try:
        # ---------------- MESSAGE ----------------
        if isinstance(msg, Message):
            return await msg.reply(text, parse_mode=parse_mode, **kwargs)

        # ---------------- CALLBACK ----------------
        elif isinstance(msg, CallbackQuery):
            if msg.message:
                try:
                    return await msg.message.edit_text(
                        text,
                        parse_mode=parse_mode,
                        **kwargs
                    )
                except TelegramBadRequest as e:
                    err = str(e)

                    # already same text
                    if "message is not modified" in err:
                        return await msg.answer("✅ Already updated", show_alert=False)

                    # can't edit (old msg / no permission)
                    elif "message can't be edited" in err.lower():
                        return await msg.message.reply(
                            text,
                            parse_mode=parse_mode,
                            **kwargs
                        )

                    else:
                        raise

            return await msg.answer()

    except TelegramBadRequest:
        # ---------------- FALLBACK ----------------
        try:
            if isinstance(msg, Message):
                return await bot.send_message(
                    msg.chat.id,
                    text,
                    parse_mode=parse_mode,
                    **kwargs
                )

            elif isinstance(msg, CallbackQuery) and msg.message:
                return await bot.send_message(
                    msg.message.chat.id,
                    text,
                    parse_mode=parse_mode,
                    **kwargs
                )
        except:
            pass

# =========================  
# /settime FIX (GROUP & CHANNEL via DM)  
# =========================  
from aiogram.types import Message
from aiogram.enums import ChatType
import re

async def settime_logic(msg: Message, target_chat_id: int | None = None):
    """
    🔥 Advanced Set Time Logic

    Features:
    - ✅ Supports s / m / h (e.g. 10s, 5m, 1h)
    - ✅ Works for group, supergroup, channel (via DM)
    - ✅ Admin + Owner check
    - ✅ Join check
    - ✅ Premium limits
    - ✅ Clean error handling
    """

    # -----------------------
    # CHAT + USER DETECT
    # -----------------------
    if target_chat_id:  # channel via DM
        chat_id = target_chat_id
        user_id = msg.from_user.id

    else:
        chat_id = msg.chat.id

        if msg.chat.type == ChatType.CHANNEL:
            return await safe_reply(
                msg,
                "🚫 Channel me directly use nahi hota.\n👉 DM me use karo.",
                safe=False
            )

        if not msg.from_user:
            return

        user_id = msg.from_user.id

        # Admin check
        if not await user_is_admin_or_owner(chat_id, user_id):
            return await safe_reply(msg, "❌ Only admins allowed")

        # Join check
        if not await user_joined_channel(user_id):
            return await safe_reply(
                msg,
                f"🚫 Pehle join karo: {JOIN_CHECK_CHANNEL}",
                safe=False
            )

    # -----------------------
    # ARGUMENT PARSE
    # -----------------------
    args = msg.text.split()

    if len(args) < 2:
        return await safe_reply(
            msg,
            "⚙️ Usage:\n/settime 10s | 5m | 1h",
            safe=False
        )

    time_str = args[1].lower()

    match = re.match(r"^(\d+)([smh])$", time_str)
    if not match:
        return await safe_reply(
            msg,
            "❌ Invalid format!\nUse: 10s / 5m / 1h",
            safe=False
        )

    value, unit = match.groups()
    value = int(value)

    # -----------------------
    # CONVERT TIME
    # -----------------------
    if unit == "s":
        seconds = value
    elif unit == "m":
        seconds = value * 60
    elif unit == "h":
        seconds = value * 3600
    else:
        return await safe_reply(msg, "❌ Invalid unit")

    # -----------------------
    # LIMITS (🔥 PREMIUM LOGIC)
    # -----------------------
    if is_premium(user_id):
        max_time = 86400  # 24h
    else:
        max_time = 600    # 10 min

    if seconds < 1:
        return await safe_reply(msg, "❌ Minimum 1 second")

    if seconds > max_time:
        return await safe_reply(
            msg,
            f"❌ Max allowed: {max_time} seconds\n💎 Upgrade for more!",
            safe=False
        )

    # -----------------------
    # SAVE TO DB
    # -----------------------
    update_group(chat_id, {"delete_time": seconds})

    # -----------------------
    # SUCCESS MESSAGE
    # -----------------------
    await safe_reply(
        msg,
        f"✅ Auto-delete set to {value}{unit} ({seconds} sec)",
        safe=False
    ))
    


# ---------------------------
# SET TIME
# ---------------------------
@dp.message(Command("settime"))
async def cmd_settime(msg: Message):
    await settime_logic(msg)

# ---------------------------
# GET TIME / INFO
# ---------------------------
@dp.message(Command("gettime") | Command("delayinfo"))
async def cmd_gettime(msg: Message):
    g = get_group(msg.chat.id) or {}

    await safe_reply(
        msg,
        f"⏱ Delete time: {g.get('delete_time', DEFAULT_DELETE_TIME)} seconds\n"
        f"⚙️ Status: {'Enabled' if g.get('enabled', True) else 'Disabled'}",
        safe=False
    )

# ---------------------------
# ENABLE
# ---------------------------
@dp.message(Command("enable"))
async def cmd_enable(msg: Message):
    update_group(msg.chat.id, {"enabled": True})
    await safe_reply(msg, "🟢 Auto-delete enabled.", safe=False)

# ---------------------------
# DISABLE
# ---------------------------
@dp.message(Command("disable"))
async def cmd_disable(msg: Message):
    update_group(msg.chat.id, {"enabled": False})
    await safe_reply(msg, "🔴 Auto-delete disabled.", safe=False)

# ---------------------------
# CHAT ID
# ---------------------------
@dp.message(Command("id"))
async def cmd_id(msg: Message):
    await safe_reply(
        msg,
        f"🆔 Chat ID: <code>{msg.chat.id}</code>",
        safe=False
    )


# ---------------------------
# CHECK PREMIUM
# ---------------------------
@dp.message(Command("checkpremium"))
async def checkprem(message: Message):
    if is_premium(message.from_user.id):
        await message.reply("💎 Premium")
    else:
        await message.reply("❌ Not Premium")
              
# ---------------------------
# Owner commands (text based)
# ---------------------------
from aiogram.types import Message
from aiogram.filters import Command
import asyncio
import time

# ---------------------------
# STATS (OWNER ONLY)
# ---------------------------
@dp.message(Command("stats"))
async def cmd_stats(msg: Message):
    if not msg.from_user or msg.from_user.id != OWNER_ID:
        return

    total_groups = groups_col.count_documents({})
    total_users = users_col.count_documents({})
    total_premium = premium_col.count_documents({})

    await safe_reply(
        msg,
        "📊 <b>Bot Statistics</b>\n\n"
        f"👥 Groups        : <b>{total_groups}</b>\n"
        f"👤 Users         : <b>{total_users}</b>\n"
        f"💎 Premium Users : <b>{total_premium}</b>",
        safe=False
    )


# ---------------------------
# ADD PREMIUM
# ---------------------------
@dp.message(Command("addpremium"))
async def cmd_add_premium(msg: Message):
    if msg.from_user.id != OWNER_ID:
        return await msg.reply("❌ Only owner can use this command.")

    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        return await msg.reply("Usage: <code>/addpremium user_id</code>", parse_mode="HTML")

    try:
        uid = int(parts[1])
    except ValueError:
        return await msg.reply("❌ Invalid user id.")

    premium_col.update_one(
        {"user_id": uid},
        {"$set": {
            "user_id": uid,
            "expire_at": int(time.time()) + (30 * 86400)  # default 30 days
        }},
        upsert=True
    )

    premium_users.add(uid)

    await safe_reply(
        msg,
        f"✅ <b>{uid}</b> added to premium list.",
        safe=False
    )


# ---------------------------
# REMOVE PREMIUM
# ---------------------------
@dp.message(Command("removepremium"))
async def cmd_remove_premium(msg: Message):
    if msg.from_user.id != OWNER_ID:
        return await msg.reply("❌ Only owner can use this command.")

    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        return await msg.reply("Usage: <code>/removepremium user_id</code>", parse_mode="HTML")

    try:
        uid = int(parts[1])
    except ValueError:
        return await msg.reply("❌ Invalid user id.")

    premium_col.delete_one({"user_id": uid})
    premium_users.discard(uid)

    await safe_reply(
        msg,
        f"❌ <b>{uid}</b> removed from premium list.",
        safe=False
    )


# ---------------------------
# BROADCAST (DB BASED + SAFE)
# ---------------------------
@dp.message(Command("broadcast"))
async def cmd_broadcast(msg: Message):
    if msg.from_user.id != OWNER_ID:
        return await msg.reply("❌ Only owner can use this command.")

    text = msg.text.partition(" ")[2].strip()
    if not text:
        return await msg.reply("Usage: <code>/broadcast message</code>", parse_mode="HTML")

    sent = 0
    failed = 0

    # 🔥 DB based groups (NOT memory)
    groups = groups_col.find({}, {"chat_id": 1})

    for g in groups:
        try:
            await bot.send_message(g["chat_id"], text)
            sent += 1
            await asyncio.sleep(0.05)  # flood control
        except Exception:
            failed += 1

    await safe_reply(
        msg,
        "📢 <b>Broadcast Result</b>\n\n"
        f"✅ Sent   : <b>{sent}</b>\n"
        f"❌ Failed : <b>{failed}</b>",
        safe=False
    )
    
import asyncio
from aiogram.enums import ChatType

# ---------------------------
# SAFE DELETE FUNCTION
# ---------------------------
async def safe_delete(chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id, message_id)
        return True

    except Exception as e:
        err = str(e).lower()

        if "message to delete not found" in err:
            return False

        if "not enough rights" in err:
            return False

        if "bot was kicked" in err:
            groups_col.delete_one({"chat_id": chat_id})
            return False

        print(f"Delete error: {e}")
        return False


# ---------------------------
# DELAY WORKER
# ---------------------------
async def delete_later(chat_id: int, message_id: int, delay: int):
    await asyncio.sleep(delay)
    await safe_delete(chat_id, message_id)


# ---------------------------
# GROUP AUTO DELETE
# ---------------------------
@dp.message()
async def auto_delete_handler(msg: Message):
    if msg.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    g = get_group(msg.chat.id)
    if not g or not g.get("enabled", True):
        return

    delete_time = int(g.get("delete_time", DEFAULT_DELETE_TIME))

    # limits
    delete_time = max(MIN_TIME, min(delete_time, MAX_TIME))

    asyncio.create_task(
        delete_later(msg.chat.id, msg.message_id, delete_time)
    )


# ---------------------------
# CHANNEL AUTO DELETE
# ---------------------------
@dp.channel_post()
async def channel_auto_delete_handler(msg: Message):
    chat_id = msg.chat.id
    message_id = msg.message_id

    ensure_group_defaults(chat_id)

    g = get_group(chat_id)
    if not g or not g.get("enabled", True):
        return

    delete_time = int(g.get("delete_time", DEFAULT_DELETE_TIME))
    delete_time = max(MIN_TIME, min(delete_time, MAX_TIME))

    asyncio.create_task(
        delete_later(chat_id, message_id, delete_time)
    )

# ---------------------------
# Startup / graceful
# ---------------------------
async def on_startup(bot: Bot):
    load_state()   # 🔥 ADD THIS LINE
    print("\n" + "=" * 40)
    print("🤖 Bot Started Successfully")
    print(f"📦 Groups in DB   : {groups_col.count_documents({})}")
    print(f"💎 Premium Users : {premium_col.count_documents({})}")
    print("=" * 40 + "\n")


async def on_shutdown(bot: Bot):
    await bot.session.close()
    print("🛑 Bot stopped gracefully")


async def main():
    await on_startup(bot)

    try:
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await on_shutdown(bot)


if __name__ == "__main__":
    asyncio.run(main())
    
    
