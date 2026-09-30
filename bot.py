import os
import time
import threading

import telebot
from telebot import types

import config
import database

from license import can_download

from downloader import (
    Downloader,
    DownloadCancelled,
    cleanup
)


bot = telebot.TeleBot(
    config.BOT_TOKEN,
    parse_mode="HTML"
)

database.init_db()


# =========================================================
# GLOBAL STATE
# =========================================================

BOT_RUNNING = True

USER_STATES = {}

ACTIVE_DOWNLOADS = {}

CANCEL_EVENTS = {}


# =========================================================
# OWNER
# =========================================================

def is_owner(user_id):

    return user_id == config.OWNER_ID


# =========================================================
# USER MENU
# =========================================================

def user_menu(user_id):

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

    if is_owner(user_id):
        kb.row(
            "👑 Owner Mode"
        )

    return kb


# =========================================================
# OWNER MENU
# =========================================================

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


# =========================================================
# VIDEO MENU
# =========================================================

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


# =========================================================
# MP3 MENU
# =========================================================

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


# =========================================================
# CANCEL MENU
# =========================================================

def cancel_menu():

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        "❌ Cancel"
    )

    return kb


# =========================================================
# KEY MENU
# =========================================================

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

    kb.row(
        "🔙 Owner Menu"
    )

    return kb


# =========================================================
# KEY DURATION
# =========================================================

def duration_menu():

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        "⏱ 1 Minute",
        "⏱ 5 Minutes"
    )

    kb.row(
        "⏱ 10 Minutes",
        "⏱ 30 Minutes"
    )

    kb.row(
        "🕐 1 Hour",
        "🕐 6 Hours"
    )

    kb.row(
        "📅 1 Day",
        "📅 7 Days"
    )

    kb.row(
        "📅 30 Days",
        "📅 90 Days"
    )

    kb.row(
        "♾️ Lifetime"
    )

    kb.row(
        "🔙 Key Control"
    )

    return kb


DURATIONS = {

    "⏱ 1 Minute": 1,

    "⏱ 5 Minutes": 5,

    "⏱ 10 Minutes": 10,

    "⏱ 30 Minutes": 30,

    "🕐 1 Hour": 60,

    "🕐 6 Hours": 360,

    "📅 1 Day": 1440,

    "📅 7 Days": 10080,

    "📅 30 Days": 43200,

    "📅 90 Days": 129600,

    "♾️ Lifetime": None
}


# =========================================================
# BOT CONTROL MENU
# =========================================================

def bot_control_menu():

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        "▶️ Start Bot",
        "⏸️ Stop Bot"
    )

    kb.row(
        "📊 Bot Status"
    )

    kb.row(
        "🔙 Owner Menu"
    )

    return kb


# =========================================================
# USER MANAGEMENT MENU
# =========================================================

def user_management_menu():

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        "👥 All Users",
        "📊 User Statistics"
    )

    kb.row(
        "🚫 Ban User",
        "🟢 Unban User"
    )

    kb.row(
        "🔙 Owner Menu"
    )

    return kb


# =========================================================
# REGISTER
# =========================================================

def register(message):

    database.register_user(
        message.from_user
    )


# =========================================================
# START
# =========================================================

@bot.message_handler(
    commands=["start"]
)
def start(message):

    register(message)

    user_id = message.from_user.id

    if is_owner(user_id):

        mode = database.get_mode(
            user_id
        )

        if mode == "owner":

            bot.send_message(
                message.chat.id,
                "👑 <b>Owner Mode</b>",
                reply_markup=owner_menu()
            )

        else:

            bot.send_message(
                message.chat.id,
                "👤 <b>User Mode</b>",
                reply_markup=user_menu(
                    user_id
                )
            )

    else:

        bot.send_message(
            message.chat.id,
            "👋 <b>Welcome to NUTHH Downloader</b>",
            reply_markup=user_menu(
                user_id
            )
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
        "👑 <b>Owner Mode Enabled</b>",
        reply_markup=owner_menu()
    )


# =========================================================
# USER MODE
# =========================================================

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
        "👤 <b>User Mode Enabled</b>",
        reply_markup=user_menu(
            message.from_user.id
        )
    )


# =========================================================
# VIDEO
# =========================================================

@bot.message_handler(
    func=lambda m:
        m.text == "🎬 Download Video"
)
def video_start(message):

    register(message)

    if not BOT_RUNNING and not is_owner(
        message.from_user.id
    ):

        bot.send_message(
            message.chat.id,
            "⏸️ Bot is currently stopped.",
            reply_markup=user_menu(
                message.from_user.id
            )
        )

        return

    if not can_download(
        message.from_user.id
    ):

        bot.send_message(
            message.chat.id,
            (
                "🔒 <b>License Required</b>\n\n"
                "Please activate a valid key first."
            ),
            reply_markup=user_menu(
                message.from_user.id
            )
        )

        return

    USER_STATES[
        message.from_user.id
    ] = {
        "type": "video_quality"
    }

    bot.send_message(
        message.chat.id,
        "🎬 <b>Select Video Quality</b>",
        reply_markup=video_menu()
    )


# =========================================================
# VIDEO QUALITY
# =========================================================

@bot.message_handler(
    func=lambda m:
        m.text in [
            "🟢 Smooth",
            "720p",
            "1080p",
            "4K / Source"
        ]
)
def video_quality(message):

    state = USER_STATES.get(
        message.from_user.id
    )

    if not state:
        return

    quality = {
        "🟢 Smooth": "smooth",
        "720p": "720",
        "1080p": "1080",
        "4K / Source": "source"
    }[message.text]

    USER_STATES[
        message.from_user.id
    ] = {
        "type": "video_url",
        "quality": quality
    }

    bot.send_message(
        message.chat.id,
        (
            "🔗 <b>Send Video URL</b>\n\n"
            "You can send a long video URL."
        ),
        reply_markup=cancel_menu()
    )


# =========================================================
# MP3
# =========================================================

@bot.message_handler(
    func=lambda m:
        m.text == "🎵 Download MP3"
)
def mp3_start(message):

    register(message)

    if not BOT_RUNNING and not is_owner(
        message.from_user.id
    ):

        bot.send_message(
            message.chat.id,
            "⏸️ Bot is currently stopped.",
            reply_markup=user_menu(
                message.from_user.id
            )
        )

        return

    if not can_download(
        message.from_user.id
    ):

        bot.send_message(
            message.chat.id,
            "🔒 <b>Valid license required.</b>",
            reply_markup=user_menu(
                message.from_user.id
            )
        )

        return

    USER_STATES[
        message.from_user.id
    ] = {
        "type": "mp3_quality"
    }

    bot.send_message(
        message.chat.id,
        "🎵 <b>Select MP3 Quality</b>",
        reply_markup=mp3_menu()
    )


# =========================================================
# MP3 QUALITY
# =========================================================

@bot.message_handler(
    func=lambda m:
        m.text in [
            "🎵 128 kbps",
            "🎵 192 kbps",
            "🎵 320 kbps"
        ]
)
def mp3_quality(message):

    state = USER_STATES.get(
        message.from_user.id
    )

    if not state:
        return

    quality = {
        "🎵 128 kbps": "128",
        "🎵 192 kbps": "192",
        "🎵 320 kbps": "320"
    }[message.text]

    USER_STATES[
        message.from_user.id
    ] = {
        "type": "mp3_url",
        "quality": quality
    }

    bot.send_message(
        message.chat.id,
        "🔗 <b>Send Video URL</b>",
        reply_markup=cancel_menu()
    )


# =========================================================
# CANCEL
# =========================================================

@bot.message_handler(
    func=lambda m:
        m.text == "❌ Cancel"
)
def cancel(message):

    user_id = message.from_user.id

    event = CANCEL_EVENTS.get(
        user_id
    )

    if event:
        event.set()

    USER_STATES.pop(
        user_id,
        None
    )

    bot.send_message(
        message.chat.id,
        "❌ Cancelled.",
        reply_markup=user_menu(
            user_id
        )
    )


# =========================================================
# URL PROCESS
# =========================================================

@bot.message_handler(
    func=lambda m:
        USER_STATES.get(
            m.from_user.id,
            {}
        ).get("type")
        in [
            "video_url",
            "mp3_url"
        ]
)
def receive_url(message):

    user_id = message.from_user.id

    state = USER_STATES.get(
        user_id
    )

    if not state:
        return

    if not can_download(user_id):

        USER_STATES.pop(
            user_id,
            None
        )

        bot.send_message(
            message.chat.id,
            "🔒 License expired.",
            reply_markup=user_menu(
                user_id
            )
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

    action = state["type"]

    USER_STATES.pop(
        user_id,
        None
    )

    event = threading.Event()

    CANCEL_EVENTS[
        user_id
    ] = event

    bot.send_message(
        message.chat.id,
        "🔎 <b>Preparing download...</b>",
        reply_markup=cancel_menu()
    )

    thread = threading.Thread(
        target=download_worker,
        args=(
            message,
            url,
            state,
            event
        ),
        daemon=True
    )

    ACTIVE_DOWNLOADS[
        user_id
    ] = thread

    thread.start()


# =========================================================
# PROGRESS
# =========================================================

def progress_message(info):

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

    if filled > 10:
        filled = 10

    bar = (
        "█" * filled
        + "░" * (10 - filled)
    )

    return (
        "📥 <b>Downloading</b>\n\n"
        f"[{bar}] {percent:.1f}%\n\n"
        f"📦 {info.get('downloaded', '0 B')}"
        " / "
        f"{info.get('total', 'Unknown')}\n"
        f"⚡ {info.get('speed', '0 B/s')}\n"
        f"⏳ ETA: {info.get('eta', '--:--')}"
    )


# =========================================================
# WORKER
# =========================================================

def download_worker(
    message,
    url,
    state,
    event
):

    user_id = message.from_user.id
    chat_id = message.chat.id

    status_message = bot.send_message(
        chat_id,
        "🔎 <b>Starting...</b>",
        reply_markup=cancel_menu()
    )

    last_update = [0]

    def callback(info):

        now = time.time()

        status = info.get(
            "status"
        )

        if status == "downloading":

            if now - last_update[0] < 2:
                return

            last_update[0] = now

            try:

                bot.edit_message_text(
                    progress_message(info),
                    chat_id,
                    status_message.message_id,
                    parse_mode="HTML"
                )

            except Exception:
                pass

        elif status == "starting":

            try:

                bot.edit_message_text(
                    (
                        "🔄 <b>Starting download...</b>\n\n"
                        f"Attempt "
                        f"{info.get('attempt')}/"
                        f"{info.get('max_attempts')}"
                    ),
                    chat_id,
                    status_message.message_id,
                    parse_mode="HTML"
                )

            except Exception:
                pass

        elif status == "processing":

            try:

                bot.edit_message_text(
                    "⚙️ <b>Processing with FFmpeg...</b>",
                    chat_id,
                    status_message.message_id,
                    parse_mode="HTML"
                )

            except Exception:
                pass

        elif status == "retry":

            try:

                bot.edit_message_text(
                    (
                        "⚠️ <b>Connection problem</b>\n\n"
                        f"🔄 Retry "
                        f"{info.get('attempt')}/"
                        f"{info.get('max_attempts')}\n\n"
                        "Trying again..."
                    ),
                    chat_id,
                    status_message.message_id,
                    parse_mode="HTML"
                )

            except Exception:
                pass

    downloader = Downloader(
        progress_callback=callback,
        cancel_event=event
    )

    path = None

    try:

        if state["type"] == "video_url":

            result = downloader.video(
                url=url,
                quality=state["quality"]
            )

        else:

            result = downloader.mp3(
                url=url,
                quality=state["quality"]
            )

        if event.is_set():
            raise DownloadCancelled()

        if not result.get("success"):

            bot.send_message(
                chat_id,
                (
                    "❌ <b>Download Failed</b>\n\n"
                    f"<code>"
                    f"{result.get('error', 'Unknown error')[:1000]}"
                    f"</code>"
                ),
                reply_markup=user_menu(
                    user_id
                )
            )

            return

        path = result["path"]

        if not os.path.exists(path):

            raise RuntimeError(
                "Output file does not exist."
            )

        try:

            bot.edit_message_text(
                "📤 <b>Uploading to Telegram...</b>",
                chat_id,
                status_message.message_id,
                parse_mode="HTML"
            )

        except Exception:
            pass

        if state["type"] == "video_url":

            with open(
                path,
                "rb"
            ) as video:

                bot.send_video(
                    chat_id,
                    video,
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
            ) as audio:

                bot.send_audio(
                    chat_id,
                    audio,
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
            "✅ <b>Completed!</b>",
            reply_markup=user_menu(
                user_id
            )
        )

    except DownloadCancelled:

        bot.send_message(
            chat_id,
            "❌ <b>Download cancelled.</b>",
            reply_markup=user_menu(
                user_id
            )
        )

    except Exception as error:

        bot.send_message(
            chat_id,
            (
                "❌ <b>Upload/Download Error</b>\n\n"
                f"<code>{str(error)[:1000]}</code>"
            ),
            reply_markup=user_menu(
                user_id
            )
        )

    finally:

        if path:
            cleanup(path)

        ACTIVE_DOWNLOADS.pop(
            user_id,
            None
        )

        CANCEL_EVENTS.pop(
            user_id,
            None
        )


# =========================================================
# ACTIVATE KEY
# =========================================================

@bot.message_handler(
    func=lambda m:
        m.text == "🔑 Activate Key"
)
def activate_button(message):

    USER_STATES[
        message.from_user.id
    ] = {
        "type": "activate_key"
    }

    bot.send_message(
        message.chat.id,
        "🔑 <b>Send License Key</b>",
        reply_markup=cancel_menu()
    )


# =========================================================
# ACTIVATE KEY STATE
# =========================================================

@bot.message_handler(
    func=lambda m:
        USER_STATES.get(
            m.from_user.id,
            {}
        ).get("type")
        == "activate_key"
)
def activate_process(message):

    user_id = message.from_user.id

    success, result = database.activate_license(
        user_id,
        message.text
    )

    USER_STATES.pop(
        user_id,
        None
    )

    bot.send_message(
        message.chat.id,
        result,
        reply_markup=user_menu(
            user_id
        )
    )


# =========================================================
# ACCOUNT
# =========================================================

@bot.message_handler(
    func=lambda m:
        m.text == "👤 My Account"
)
def account(message):

    row = database.get_user(
        message.from_user.id
    )

    downloads = (
        row["downloads"]
        if row
        else 0
    )

    license_status = (
        "🟢 Active"
        if can_download(
            message.from_user.id
        )
        else "🔴 Inactive"
    )

    bot.send_message(
        message.chat.id,
        (
            "👤 <b>My Account</b>\n\n"
            f"🆔 <code>{message.from_user.id}</code>\n"
            f"👤 @{message.from_user.username or 'None'}\n"
            f"🔐 License: {license_status}\n"
            f"📥 Downloads: {downloads}"
        ),
        reply_markup=user_menu(
            message.from_user.id
        )
    )


# =========================================================
# MY DOWNLOADS
# =========================================================

@bot.message_handler(
    func=lambda m:
        m.text == "📊 My Downloads"
)
def my_downloads(message):

    row = database.get_user(
        message.from_user.id
    )

    count = (
        row["downloads"]
        if row
        else 0
    )

    bot.send_message(
        message.chat.id,
        (
            "📊 <b>My Downloads</b>\n\n"
            f"📥 Total: <b>{count}</b>"
        ),
        reply_markup=user_menu(
            message.from_user.id
        )
    )


# =========================================================
# HELP
# =========================================================

@bot.message_handler(
    func=lambda m:
        m.text == "❓ Help"
)
def help_button(message):

    bot.send_message(
        message.chat.id,
        (
            "❓ <b>NUTHH Downloader</b>\n\n"
            "🎬 Download Video\n"
            "🎵 Download MP3\n"
            "🔄 Retry\n"
            "📥 Resume\n"
            "📊 Progress\n"
            "❌ Cancel\n"
            "⚙️ FFmpeg processing"
        ),
        reply_markup=user_menu(
            message.from_user.id
        )
    )


# =========================================================
# KEY CONTROL
# =========================================================

@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "🔑 Key Control"
)
def key_control(message):

    bot.send_message(
        message.chat.id,
        "🔑 <b>License Key Control</b>",
        reply_markup=key_menu()
    )


# =========================================================
# GENERATE KEY
# =========================================================

@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "➕ Generate Key"
)
def generate_key(message):

    USER_STATES[
        message.from_user.id
    ] = {
        "type": "generate_key"
    }

    bot.send_message(
        message.chat.id,
        "⏰ <b>Select License Duration</b>",
        reply_markup=duration_menu()
    )


# =========================================================
# CREATE KEY
# =========================================================

@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text in DURATIONS
)
def create_key(message):

    minutes = DURATIONS[
        message.text
    ]

    try:

        key = database.generate_license(
            minutes
        )

        if minutes is None:

            duration = "♾️ Lifetime"

        elif minutes < 60:

            duration = f"{minutes} minutes"

        elif minutes < 1440:

            duration = (
                f"{minutes // 60} hours"
            )

        else:

            duration = (
                f"{minutes // 1440} days"
            )

        USER_STATES.pop(
            message.from_user.id,
            None
        )

        bot.send_message(
            message.chat.id,
            (
                "✅ <b>License Created</b>\n\n"
                f"🔑 <code>{key}</code>\n\n"
                f"⏰ Duration: <b>{duration}</b>\n"
                "👥 Users: Unlimited\n"
                "📱 Devices: Unlimited"
            ),
            reply_markup=key_menu()
        )

    except Exception as error:

        bot.send_message(
            message.chat.id,
            (
                "❌ <b>Key Creation Failed</b>\n\n"
                f"<code>{str(error)}</code>"
            ),
            reply_markup=key_menu()
        )


# =========================================================
# ALL KEYS
# =========================================================

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
            "📋 No license keys.",
            reply_markup=key_menu()
        )

        return

    text = "📋 <b>License Keys</b>\n\n"

    for row in rows[:50]:

        status = (
            "🟢 Enabled"
            if row["enabled"]
            else "🔴 Disabled"
        )

        expiry = (
            "♾️ Lifetime"
            if row["expires_at"] is None
            else row["expires_at"][:19]
        )

        text += (
            f"{status}\n"
            f"🔑 <code>{row['license_key']}</code>\n"
            f"⏰ {expiry}\n\n"
        )

    bot.send_message(
        message.chat.id,
        text[:4000],
        reply_markup=key_menu()
    )


# =========================================================
# SEARCH KEY
# =========================================================

@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "🔍 Search Key"
)
def search_key(message):

    USER_STATES[
        message.from_user.id
    ] = {
        "type": "search_key"
    }

    bot.send_message(
        message.chat.id,
        "🔍 Send license key:",
        reply_markup=key_menu()
    )


# =========================================================
# EXTEND KEY
# =========================================================

@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "⏰ Extend Key"
)
def extend_key_start(message):

    USER_STATES[
        message.from_user.id
    ] = {
        "type": "extend_key"
    }

    bot.send_message(
        message.chat.id,
        "🔑 Send license key:",
        reply_markup=key_menu()
    )


# =========================================================
# ENABLE
# =========================================================

@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "🟢 Enable Key"
)
def enable_key_start(message):

    USER_STATES[
        message.from_user.id
    ] = {
        "type": "enable_key"
    }

    bot.send_message(
        message.chat.id,
        "🔑 Send license key:",
        reply_markup=key_menu()
    )


# =========================================================
# DISABLE
# =========================================================

@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "🔴 Disable Key"
)
def disable_key_start(message):

    USER_STATES[
        message.from_user.id
    ] = {
        "type": "disable_key"
    }

    bot.send_message(
        message.chat.id,
        "🔑 Send license key:",
        reply_markup=key_menu()
    )


# =========================================================
# DELETE
# =========================================================

@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "🗑️ Delete Key"
)
def delete_key_start(message):

    USER_STATES[
        message.from_user.id
    ] = {
        "type": "delete_key"
    }

    bot.send_message(
        message.chat.id,
        "🔑 Send license key:",
        reply_markup=key_menu()
    )


# =========================================================
# KEY STATE HANDLER
# =========================================================

@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and USER_STATES.get(
            m.from_user.id,
            {}
        ).get("type")
        in [
            "search_key",
            "extend_key",
            "enable_key",
            "disable_key",
            "delete_key"
        ]
)
def key_state(message):

    user_id = message.from_user.id

    state = USER_STATES.get(
        user_id
    )

    action = state["type"]

    key = message.text.strip()

    if action == "search_key":

        row = database.get_license(
            key
        )

        USER_STATES.pop(
            user_id,
            None
        )

        if not row:

            text = "❌ Key not found."

        else:

            status = (
                "🟢 Enabled"
                if row["enabled"]
                else "🔴 Disabled"
            )

            expiry = (
                "♾️ Lifetime"
                if row["expires_at"] is None
                else row["expires_at"]
            )

            text = (
                "🔍 <b>Key Information</b>\n\n"
                f"🔑 <code>{row['license_key']}</code>\n"
                f"📌 {status}\n"
                f"⏰ {expiry}"
            )

        bot.send_message(
            message.chat.id,
            text,
            reply_markup=key_menu()
        )

        return

    if action == "enable_key":

        success = database.enable_license(
            key
        )

        USER_STATES.pop(
            user_id,
            None
        )

        bot.send_message(
            message.chat.id,
            (
                "🟢 Key enabled."
                if success
                else "❌ Key not found."
            ),
            reply_markup=key_menu()
        )

        return

    if action == "disable_key":

        success = database.disable_license(
            key
        )

        USER_STATES.pop(
            user_id,
            None
        )

        bot.send_message(
            message.chat.id,
            (
                "🔴 Key disabled."
                if success
                else "❌ Key not found."
            ),
            reply_markup=key_menu()
        )

        return

    if action == "delete_key":

        success = database.delete_license(
            key
        )

        USER_STATES.pop(
            user_id,
            None
        )

        bot.send_message(
            message.chat.id,
            (
                "🗑️ Key deleted."
                if success
                else "❌ Key not found."
            ),
            reply_markup=key_menu()
        )

        return

    if action == "extend_key":

        try:

            minutes = int(key)

            USER_STATES[
                user_id
            ] = {
                "type": "extend_key_duration",
                "key": minutes
            }

            bot.send_message(
                message.chat.id,
                "🔑 Now send the license key.",
                reply_markup=key_menu()
            )

        except ValueError:

            bot.send_message(
                message.chat.id,
                "❌ Enter duration in minutes.",
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
        and m.text == "▶️ Start Bot"
)
def start_bot(message):

    global BOT_RUNNING

    BOT_RUNNING = True

    bot.send_message(
        message.chat.id,
        "🟢 <b>Bot is running.</b>",
        reply_markup=bot_control_menu()
    )


@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "⏸️ Stop Bot"
)
def stop_bot(message):

    global BOT_RUNNING

    BOT_RUNNING = False

    bot.send_message(
        message.chat.id,
        (
            "⏸️ <b>Bot stopped for users.</b>\n\n"
            "👑 Owner controls are still available."
        ),
        reply_markup=bot_control_menu()
    )


@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "📊 Bot Status"
)
def bot_status(message):

    status = (
        "🟢 Running"
        if BOT_RUNNING
        else "🔴 Stopped"
    )

    bot.send_message(
        message.chat.id,
        f"🤖 Status: <b>{status}</b>",
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

    bot.send_message(
        message.chat.id,
        (
            "📊 <b>Statistics</b>\n\n"
            f"👥 Users: <b>{database.total_users()}</b>\n"
            f"📥 Downloads: <b>{database.total_downloads()}</b>\n"
            f"🔑 Keys: <b>{database.license_count()}</b>\n"
            f"🟢 Active Keys: "
            f"<b>{database.active_license_count()}</b>"
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
def users_menu(message):

    bot.send_message(
        message.chat.id,
        "👥 <b>User Management</b>",
        reply_markup=user_management_menu()
    )


@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "👥 All Users"
)
def all_users(message):

    rows = database.all_users()

    if not rows:

        text = "No users."

    else:

        text = "👥 <b>Users</b>\n\n"

        for row in rows[:50]:

            status = (
                "🚫"
                if row["blocked"]
                else "🟢"
            )

            text += (
                f"{status} "
                f"<code>{row['user_id']}</code> "
                f"{row['username']}\n"
            )

    bot.send_message(
        message.chat.id,
        text[:4000],
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
            f"Users: <b>{database.total_users()}</b>"
        ),
        reply_markup=user_management_menu()
    )


# =========================================================
# SETTINGS
# =========================================================

@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "⚙️ Settings"
)
def settings(message):

    bot.send_message(
        message.chat.id,
        (
            "⚙️ <b>Settings</b>\n\n"
            f"🔄 Retries: {config.MAX_RETRIES}\n"
            f"⏱ Timeout: {config.DOWNLOAD_TIMEOUT}s\n"
            "🎬 Video: yt-dlp\n"
            "🎞️ Processing: FFmpeg\n"
            "💾 Database: SQLite"
        ),
        reply_markup=owner_menu()
    )


# =========================================================
# OWNER MENU
# =========================================================

@bot.message_handler(
    func=lambda m:
        is_owner(m.from_user.id)
        and m.text == "🔙 Owner Menu"
)
def owner_menu_back(message):

    USER_STATES.pop(
        message.from_user.id,
        None
    )

    database.set_mode(
        message.from_user.id,
        "owner"
    )

    bot.send_message(
        message.chat.id,
        "👑 <b>Owner Control Panel</b>",
        reply_markup=owner_menu()
    )


# =========================================================
# FALLBACK
# =========================================================

@bot.message_handler(
    func=lambda m: True
)
def fallback(message):

    register(message)

    user_id = message.from_user.id

    if (
        not is_owner(user_id)
        and not BOT_RUNNING
    ):

        bot.send_message(
            message.chat.id,
            "⏸️ Bot is currently stopped.",
            reply_markup=user_menu(
                user_id
            )
        )

        return

    if is_owner(user_id):

        mode = database.get_mode(
            user_id
        )

        if mode == "owner":

            bot.send_message(
                message.chat.id,
                "👇 Use Owner Menu.",
                reply_markup=owner_menu()
            )

        else:

            bot.send_message(
                message.chat.id,
                "👇 Use User Menu.",
                reply_markup=user_menu(
                    user_id
                )
            )

    else:

        bot.send_message(
            message.chat.id,
            "👇 Please use the menu buttons.",
            reply_markup=user_menu(
                user_id
            )
        )


# =========================================================
# RUN
# =========================================================

print(
    "======================================"
)

print(
    " NUTHH TikTok Downloader Bot"
)

print(
    " Bot is running..."
)

print(
    "======================================"
)


bot.infinity_polling(
    skip_pending=True,
    timeout=60,
    long_polling_timeout=60
)
