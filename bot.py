import os
import threading
import time

import telebot
from telebot import types

import config
import database
from license import user_can_download
from downloader import (
    Downloader,
    DownloadCancelled,
    cleanup_completed_file
)


bot = telebot.TeleBot(
    config.BOT_TOKEN,
    parse_mode="HTML"
)


database.init_db()


# =========================================================
# STATE
# =========================================================

bot_running = True

user_state = {}
active_downloads = {}
download_cancel_events = {}


# =========================================================
# KEYBOARDS
# =========================================================

def user_menu():

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        "🎬 Download Video",
        "🎵 Download MP3"
    )

    kb.row(
        "🔑 Activate Key",
        "👤 My Account"
    )

    kb.row(
        "📊 My Downloads",
        "❓ Help"
    )

    if bot_running is False:
        kb.row("⚠️ Bot Stopped")

    if False:
        kb.row("👑 Owner Mode")

    return kb


def owner_menu():

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        "🔑 Key Control",
        "🤖 Bot Control"
    )

    kb.row(
        "👥 User Management",
        "📊 Statistics"
    )

    kb.row(
        "⚙️ Settings",
        "👤 User Mode"
    )

    return kb


def video_menu():

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        "🟢 Smooth",
        "720p"
    )

    kb.row(
        "1080p",
        "4K / Source"
    )

    kb.row(
        "❌ Cancel"
    )

    return kb


def mp3_menu():

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        "🎵 128 kbps",
        "🎵 192 kbps"
    )

    kb.row(
        "🎵 320 kbps",
        "❌ Cancel"
    )

    return kb


def cancel_menu():

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row("❌ Cancel Download")

    return kb


def key_menu():

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        "➕ Generate Key",
        "📋 All Keys"
    )

    kb.row(
        "🔍 Search Key",
        "⏰ Extend Key"
    )

    kb.row(
        "🟢 Enable Key",
        "🔴 Disable Key"
    )

    kb.row(
        "🗑️ Delete Key",
        "📈 Key Statistics"
    )

    kb.row("🔙 Back")

    return kb


def bot_control_menu():

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        "▶️ Start Bot",
        "⏸️ Stop Bot"
    )

    kb.row(
        "📊 Bot Status",
        "🔙 Back"
    )

    return kb


def user_management_menu():

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        "👥 All Users",
        "🔍 Search User"
    )

    kb.row(
        "🚫 Ban User",
        "🟢 Unban User"
    )

    kb.row(
        "📊 User Statistics",
        "🔙 Back"
    )

    return kb


# =========================================================
# HELPERS
# =========================================================

def is_owner(user_id):

    return user_id == config.OWNER_ID


def ensure_user(message):

    database.register_user(
        message.from_user
    )


def update_message(chat_id, message_id, text):

    try:
        bot.edit_message_text(
            text,
            chat_id,
            message_id,
            parse_mode="HTML"
        )
    except Exception:
        pass


def progress_text(info):

    percent = info.get(
        "percent",
        0
    )

    try:
        percent = float(percent)
    except Exception:
        percent = 0

    filled = int(
        percent / 10
    )

    bar = (
        "█" * filled
        + "░" * (10 - filled)
    )

    return (
        "📥 <b>Downloading...</b>\n\n"
        f"[{bar}] {percent:.1f}%\n\n"
        f"📦 {info.get('downloaded', '0 B')} "
        f"/ {info.get('total', 'Unknown')}\n"
        f"⚡ {info.get('speed', '0 B/s')}\n"
        f"⏳ ETA: {info.get('eta', '--:--')}"
    )


# =========================================================
# START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):

    ensure_user(message)

    if is_owner(message.from_user.id):

        database.set_mode(
            message.from_user.id,
            "user"
        )

    bot.send_message(
        message.chat.id,
        "👋 <b>Welcome to NUTHH Downloader</b>\n\n"
        "📱 Use the buttons below to continue.",
        reply_markup=user_menu()
    )


# =========================================================
# MAIN MENU
# =========================================================

@bot.message_handler(
    func=lambda m: m.text == "🎬 Download Video"
)
def download_video_button(message):

    ensure_user(message)

    if not user_can_download(
        message.from_user.id
    ):

        bot.send_message(
            message.chat.id,
            "🔒 <b>License Required</b>\n\n"
            "Please activate a valid license key first.",
            reply_markup=user_menu()
        )

        return

    user_state[
        message.from_user.id
    ] = {
        "action": "video"
    }

    bot.send_message(
        message.chat.id,
        "🎬 <b>Select Video Quality</b>",
        reply_markup=video_menu()
    )


@bot.message_handler(
    func=lambda m: m.text == "🎵 Download MP3"
)
def download_mp3_button(message):

    ensure_user(message)

    if not user_can_download(
        message.from_user.id
    ):

        bot.send_message(
            message.chat.id,
            "🔒 <b>License Required</b>\n\n"
            "Please activate a valid license key first.",
            reply_markup=user_menu()
        )

        return

    user_state[
        message.from_user.id
    ] = {
        "action": "mp3"
    }

    bot.send_message(
        message.chat.id,
        "🎵 <b>Select MP3 Quality</b>",
        reply_markup=mp3_menu()
    )


# =========================================================
# QUALITY
# =========================================================

@bot.message_handler(
    func=lambda m: m.text in [
        "🟢 Smooth",
        "720p",
        "1080p",
        "4K / Source"
    ]
)
def video_quality(message):

    user_id = message.from_user.id

    if user_id not in user_state:
        return

    quality_map = {
        "🟢 Smooth": "smooth",
        "720p": "720",
        "1080p": "1080",
        "4K / Source": "4k"
    }

    user_state[user_id][
        "quality"
    ] = quality_map[message.text]

    user_state[user_id][
        "waiting_url"
    ] = True

    bot.send_message(
        message.chat.id,
        "🔗 <b>Send the TikTok video URL</b>\n\n"
        "វីដេអូវែងក៏អាចផ្ញើបាន។\n"
        "Bot នឹងព្យាយាម Resume + Retry ប្រសិនបើ connection មានបញ្ហា។",
        reply_markup=cancel_menu()
    )


# =========================================================
# MP3 QUALITY
# =========================================================

@bot.message_handler(
    func=lambda m: m.text in [
        "🎵 128 kbps",
        "🎵 192 kbps",
        "🎵 320 kbps"
    ]
)
def mp3_quality(message):

    user_id = message.from_user.id

    if user_id not in user_state:
        return

    quality_map = {
        "🎵 128 kbps": "128",
        "🎵 192 kbps": "192",
        "🎵 320 kbps": "320"
    }

    user_state[user_id][
        "mp3_quality"
    ] = quality_map[message.text]

    user_state[user_id][
        "waiting_url"
    ] = True

    bot.send_message(
        message.chat.id,
        "🔗 <b>Send the video URL</b>",
        reply_markup=cancel_menu()
    )


# =========================================================
# URL HANDLER
# =========================================================

@bot.message_handler(
    func=lambda m:
        m.from_user.id in user_state
        and user_state[m.from_user.id].get(
            "waiting_url"
        )
)
def receive_url(message):

    user_id = message.from_user.id

    if not user_can_download(user_id):

        bot.send_message(
            message.chat.id,
            "🔒 License expired or disabled.",
            reply_markup=user_menu()
        )

        return

    url = message.text.strip()

    if not (
        url.startswith("http://")
        or url.startswith("https://")
    ):

        bot.send_message(
            message.chat.id,
            "❌ Please send a valid URL.",
            reply_markup=cancel_menu()
        )

        return

    state = user_state[user_id]

    state["waiting_url"] = False
    state["url"] = url

    cancel_event = threading.Event()

    download_cancel_events[
        user_id
    ] = cancel_event

    bot.send_message(
        message.chat.id,
        "⏳ <b>Preparing download...</b>\n\n"
        "Please wait.",
        reply_markup=cancel_menu()
    )

    thread = threading.Thread(
        target=run_download,
        args=(
            message,
            state.copy(),
            cancel_event
        ),
        daemon=True
    )

    active_downloads[user_id] = thread

    thread.start()


# =========================================================
# DOWNLOAD ENGINE
# =========================================================

def run_download(
    message,
    state,
    cancel_event
):

    user_id = message.from_user.id
    chat_id = message.chat.id

    progress_message = bot.send_message(
        chat_id,
        "🔎 <b>Checking source...</b>",
        reply_markup=cancel_menu()
    )

    last_update = [0]

    def progress_callback(info):

        now = time.time()

        status = info.get(
            "status"
        )

        if status == "downloading":

            if now - last_update[0] < 2:
                return

            last_update[0] = now

            text = progress_text(info)

            update_message(
                chat_id,
                progress_message.message_id,
                text
            )

        elif status == "starting":

            update_message(
                chat_id,
                progress_message.message_id,
                (
                    "🔎 <b>Preparing...</b>\n\n"
                    f"🔄 Attempt "
                    f"{info.get('attempt')}/"
                    f"{info.get('max_attempts')}"
                )
            )

        elif status == "processing":

            update_message(
                chat_id,
                progress_message.message_id,
                "⚙️ <b>Processing video...</b>\n\n"
                "🎞️ FFmpeg is merging/converting..."
            )

        elif status == "retry":

            update_message(
                chat_id,
                progress_message.message_id,
                (
                    "⚠️ <b>Download interrupted</b>\n\n"
                    f"🔄 Retry "
                    f"{info.get('attempt')}/"
                    f"{info.get('max_attempts')}\n\n"
                    "Trying again..."
                )
            )

    downloader = Downloader(
        progress_callback=progress_callback,
        cancel_event=cancel_event
    )

    try:

        if state.get("action") == "video":

            result = downloader.video(
                url=state["url"],
                quality=state.get(
                    "quality",
                    "720"
                )
            )

        else:

            result = downloader.mp3(
                url=state["url"],
                quality=state.get(
                    "mp3_quality",
                    "192"
                )
            )

        if cancel_event.is_set():
            raise DownloadCancelled()

        if not result.get("success"):

            update_message(
                chat_id,
                progress_message.message_id,
                (
                    "❌ <b>Download Failed</b>\n\n"
                    f"<code>{result.get('error', 'Unknown error')[:800]}</code>"
                )
            )

            return

        path = result["path"]

        if not os.path.exists(path):

            update_message(
                chat_id,
                progress_message.message_id,
                "❌ Download completed but file was not found."
            )

            return

        update_message(
            chat_id,
            progress_message.message_id,
            "📤 <b>Uploading to Telegram...</b>"
        )

        if state.get("action") == "video":

            with open(
                path,
                "rb"
            ) as video_file:

                bot.send_video(
                    chat_id,
                    video_file,
                    caption=(
                        "🎬 <b>NUTHH Downloader</b>\n\n"
                        f"📌 {result.get('title', 'Video')}"
                    ),
                    supports_streaming=True,
                    timeout=1800
                )

        else:

            with open(
                path,
                "rb"
            ) as audio_file:

                bot.send_audio(
                    chat_id,
                    audio_file,
                    caption=(
                        "🎵 <b>NUTHH Downloader</b>\n\n"
                        f"📌 {result.get('title', 'Audio')}"
                    ),
                    timeout=1800
                )

        database.increment_download(
            user_id
        )

        bot.send_message(
            chat_id,
            "✅ <b>Download completed!</b>",
            reply_markup=user_menu()
        )

        cleanup_completed_file(
            path
        )

    except DownloadCancelled:

        bot.send_message(
            chat_id,
            "❌ <b>Download cancelled.</b>",
            reply_markup=user_menu()
        )

    except Exception as error:

        bot.send_message(
            chat_id,
            (
                "❌ <b>Something went wrong.</b>\n\n"
                f"<code>{str(error)[:800]}</code>"
            ),
            reply_markup=user_menu()
        )

    finally:

        active_downloads.pop(
            user_id,
            None
        )

        download_cancel_events.pop(
            user_id,
            None
        )


# =========================================================
# CANCEL
# =========================================================

@bot.message_handler(
    func=lambda m: m.text in [
        "❌ Cancel",
        "❌ Cancel Download"
    ]
)
def cancel_download(message):

    user_id = message.from_user.id

    event = download_cancel_events.get(
        user_id
    )

    if event:
        event.set()

    user_state.pop(
        user_id,
        None
    )

    bot.send_message(
        message.chat.id,
        "❌ Cancelled.",
        reply_markup=user_menu()
    )


# =========================================================
# ACTIVATE KEY
# =========================================================

@bot.message_handler(
    func=lambda m: m.text == "🔑 Activate Key"
)
def activate_key(message):

    user_state[
        message.from_user.id
    ] = {
        "action": "activate_key"
    }

    bot.send_message(
        message.chat.id,
        "🔑 <b>Send your license key</b>",
        reply_markup=types.ReplyKeyboardMarkup(
            resize_keyboard=True
        )
    )


# =========================================================
# ACCOUNT
# =========================================================

@bot.message_handler(
    func=lambda m: m.text == "👤 My Account"
)
def my_account(message):

    row = database.get_user(
        message.from_user.id
    )

    license_status = (
        "✅ Active"
        if user_can_download(
            message.from_user.id
        )
        else "❌ Inactive"
    )

    downloads = (
        row["downloads"]
        if row
        else 0
    )

    bot.send_message(
        message.chat.id,
        (
            "👤 <b>My Account</b>\n\n"
            f"🆔 ID: <code>{message.from_user.id}</code>\n"
            f"👤 Username: @{message.from_user.username or 'None'}\n"
            f"🔐 License: {license_status}\n"
            f"📥 Downloads: {downloads}"
        ),
        reply_markup=user_menu()
    )


# =========================================================
# MY DOWNLOADS
# =========================================================

@bot.message_handler(
    func=lambda m: m.text == "📊 My Downloads"
)
def my_downloads(message):

    row = database.get_user(
        message.from_user.id
    )

    count = row["downloads"] if row else 0

    bot.send_message(
        message.chat.id,
        f"📊 <b>Your Downloads</b>\n\n"
        f"📥 Total: <b>{count}</b>",
        reply_markup=user_menu()
    )


# =========================================================
# HELP
# =========================================================

@bot.message_handler(
    func=lambda m: m.text == "❓ Help"
)
def help_button(message):

    bot.send_message(
        message.chat.id,
        (
            "❓ <b>NUTHH Downloader Help</b>\n\n"
            "1️⃣ Activate your license.\n"
            "2️⃣ Choose Video or MP3.\n"
            "3️⃣ Select quality.\n"
            "4️⃣ Send the video URL.\n"
            "5️⃣ Wait for download and upload.\n\n"
            "🎬 Long videos are supported.\n"
            "🔄 Retry + Resume are enabled.\n"
            "⚙️ FFmpeg handles video/audio merging."
        ),
        reply_markup=user_menu()
    )


# =========================================================
# OWNER MODE
# =========================================================

@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "👑 Owner Mode"
)
def owner_mode(message):

    database.set_mode(
        message.from_user.id,
        "owner"
    )

    bot.send_message(
        message.chat.id,
        "👑 <b>Owner Mode</b>",
        reply_markup=owner_menu()
    )


@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "👤 User Mode"
)
def user_mode(message):

    database.set_mode(
        message.from_user.id,
        "user"
    )

    bot.send_message(
        message.chat.id,
        "👤 <b>User Mode</b>",
        reply_markup=user_menu()
    )


# =========================================================
# OWNER KEY CONTROL
# =========================================================

@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "🔑 Key Control"
)
def key_control(message):

    bot.send_message(
        message.chat.id,
        "🔑 <b>Key Control</b>",
        reply_markup=key_menu()
    )


@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "➕ Generate Key"
)
def generate_key_button(message):

    user_state[
        message.from_user.id
    ] = {
        "action": "generate_key"
    }

    bot.send_message(
        message.chat.id,
        (
            "⏱ Send duration in minutes.\n\n"
            "Examples:\n"
            "<code>60</code> = 1 hour\n"
            "<code>1440</code> = 1 day\n"
            "<code>0</code> = Lifetime"
        ),
        reply_markup=key_menu()
    )


@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "📋 All Keys"
)
def all_keys(message):

    rows = database.list_licenses()

    if not rows:

        bot.send_message(
            message.chat.id,
            "📋 No keys found.",
            reply_markup=key_menu()
        )

        return

    text = "📋 <b>License Keys</b>\n\n"

    for row in rows[:50]:

        status = (
            "🟢"
            if row["enabled"]
            else "🔴"
        )

        expiry = (
            "♾️ Lifetime"
            if row["expires_at"] is None
            else row["expires_at"][:19]
        )

        text += (
            f"{status} "
            f"<code>{row['license_key']}</code>\n"
            f"⏰ {expiry}\n\n"
        )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=key_menu()
    )


# =========================================================
# KEY ACTIONS
# =========================================================

@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "🔴 Disable Key"
)
def disable_key(message):

    user_state[
        message.from_user.id
    ] = {
        "action": "disable_key"
    }

    bot.send_message(
        message.chat.id,
        "🔑 Send key to disable.",
        reply_markup=key_menu()
    )


@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "🟢 Enable Key"
)
def enable_key(message):

    user_state[
        message.from_user.id
    ] = {
        "action": "enable_key"
    }

    bot.send_message(
        message.chat.id,
        "🔑 Send key to enable.",
        reply_markup=key_menu()
    )


@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "🗑️ Delete Key"
)
def delete_key(message):

    user_state[
        message.from_user.id
    ] = {
        "action": "delete_key"
    }

    bot.send_message(
        message.chat.id,
        "🔑 Send key to delete.",
        reply_markup=key_menu()
    )


# =========================================================
# BOT CONTROL
# =========================================================

@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "🤖 Bot Control"
)
def bot_control(message):

    bot.send_message(
        message.chat.id,
        "🤖 <b>Bot Control</b>",
        reply_markup=bot_control_menu()
    )


@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "⏸️ Stop Bot"
)
def stop_bot(message):

    global bot_running

    bot_running = False

    bot.send_message(
        message.chat.id,
        "⏸️ <b>Bot stopped for users.</b>\n\n"
        "Owner controls remain available.",
        reply_markup=bot_control_menu()
    )


@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "▶️ Start Bot"
)
def start_bot(message):

    global bot_running

    bot_running = True

    bot.send_message(
        message.chat.id,
        "▶️ <b>Bot started.</b>",
        reply_markup=owner_menu()
    )


@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "📊 Bot Status"
)
def bot_status(message):

    status = (
        "🟢 Running"
        if bot_running
        else "🔴 Stopped"
    )

    bot.send_message(
        message.chat.id,
        f"🤖 Bot Status: <b>{status}</b>",
        reply_markup=bot_control_menu()
    )


# =========================================================
# STATISTICS
# =========================================================

@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "📊 Statistics"
)
def statistics(message):

    users = database.total_users()
    downloads = database.total_downloads()

    bot.send_message(
        message.chat.id,
        (
            "📊 <b>NUTHH Statistics</b>\n\n"
            f"👥 Users: <b>{users}</b>\n"
            f"📥 Downloads: <b>{downloads}</b>"
        ),
        reply_markup=owner_menu()
    )


# =========================================================
# USER MANAGEMENT
# =========================================================

@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "👥 User Management"
)
def user_management(message):

    bot.send_message(
        message.chat.id,
        "👥 <b>User Management</b>",
        reply_markup=user_management_menu()
    )


@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "📊 User Statistics"
)
def user_statistics(message):

    bot.send_message(
        message.chat.id,
        (
            "👥 <b>User Statistics</b>\n\n"
            f"Total users: <b>{database.total_users()}</b>"
        ),
        reply_markup=user_management_menu()
    )


# =========================================================
# BACK
# =========================================================

@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "🔙 Back"
)
def back_button(message):

    bot.send_message(
        message.chat.id,
        "👑 <b>Owner Menu</b>",
        reply_markup=owner_menu()
    )


# =========================================================
# STATE MESSAGE HANDLER
# =========================================================

@bot.message_handler(
    func=lambda m:
        m.from_user.id in user_state
)
def state_handler(message):

    user_id = message.from_user.id

    state = user_state.get(
        user_id,
        {}
    )

    action = state.get(
        "action"
    )

    # -------------------------------
    # ACTIVATE KEY
    # -------------------------------

    if action == "activate_key":

        success, text = database.activate_license(
            user_id,
            message.text
        )

        user_state.pop(
            user_id,
            None
        )

        bot.send_message(
            message.chat.id,
            text,
            reply_markup=user_menu()
        )

        return

    # -------------------------------
    # GENERATE KEY
    # -------------------------------

    if action == "generate_key":

        try:

            minutes = int(
                message.text.strip()
            )

            if minutes == 0:
                minutes_value = None
            elif minutes > 0:
                minutes_value = minutes
            else:
                raise ValueError

            key = database.generate_key(
                minutes_value
            )

            expiry = (
                "♾️ Lifetime"
                if minutes_value is None
                else f"{minutes_value} minutes"
            )

            user_state.pop(
                user_id,
                None
            )

            bot.send_message(
                message.chat.id,
                (
                    "✅ <b>Key Created</b>\n\n"
                    f"🔑 <code>{key}</code>\n"
                    f"⏰ {expiry}"
                ),
                reply_markup=key_menu()
            )

        except ValueError:

            bot.send_message(
                message.chat.id,
                "❌ Enter a valid number.",
                reply_markup=key_menu()
            )

        return

    # -------------------------------
    # DISABLE KEY
    # -------------------------------

    if action == "disable_key":

        database.set_license_enabled(
            message.text,
            False
        )

        user_state.pop(
            user_id,
            None
        )

        bot.send_message(
            message.chat.id,
            "🔴 Key disabled.",
            reply_markup=key_menu()
        )

        return

    # -------------------------------
    # ENABLE KEY
    # -------------------------------

    if action == "enable_key":

        database.set_license_enabled(
            message.text,
            True
        )

        user_state.pop(
            user_id,
            None
        )

        bot.send_message(
            message.chat.id,
            "🟢 Key enabled.",
            reply_markup=key_menu()
        )

        return

    # -------------------------------
    # DELETE KEY
    # -------------------------------

    if action == "delete_key":

        database.delete_license(
            message.text
        )

        user_state.pop(
            user_id,
            None
        )

        bot.send_message(
            message.chat.id,
            "🗑️ Key deleted.",
            reply_markup=key_menu()
        )

        return


# =========================================================
# FALLBACK
# =========================================================

@bot.message_handler(
    func=lambda m: True
)
def fallback(message):

    ensure_user(message)

    if (
        not is_owner(message.from_user.id)
        and not bot_running
    ):

        bot.send_message(
            message.chat.id,
            "⏸️ Bot is currently stopped.",
            reply_markup=user_menu()
        )

        return

    bot.send_message(
        message.chat.id,
        "👇 Please use the buttons below.",
        reply_markup=(
            owner_menu()
            if is_owner(message.from_user.id)
            and database.get_mode(
                message.from_user.id
            ) == "owner"
            else user_menu()
        )
    )


# =========================================================
# RUN
# =========================================================

print("NUTHH Downloader Bot is running...")

bot.infinity_polling(
    skip_pending=True,
    timeout=60,
    long_polling_timeout=60
)
