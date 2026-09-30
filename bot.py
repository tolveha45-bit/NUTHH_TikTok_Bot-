import os
import html
import time
import threading
import telebot

from telebot import types

import config
import database
import license
import downloader


# =========================================================
# NUTHH TELEGRAM DOWNLOADER BOT
# =========================================================

BOT_TOKEN = config.BOT_TOKEN
OWNER_ID = int(config.OWNER_ID)

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML",
    threaded=True
)

# Bot running state
BOT_RUNNING = True

# User temporary states
USER_STATES = {}

# Download locks
DOWNLOAD_LOCKS = {}

# Store download retry information
LAST_DOWNLOAD = {}


# =========================================================
# STATE HELPERS
# =========================================================

def set_state(user_id, state, data=None):
    USER_STATES[user_id] = {
        "state": state,
        "data": data or {}
    }


def get_state(user_id):
    return USER_STATES.get(user_id)


def clear_state(user_id):
    USER_STATES.pop(user_id, None)


# =========================================================
# DOWNLOAD LOCK
# =========================================================

def is_downloading(user_id):
    return user_id in DOWNLOAD_LOCKS


def start_download_lock(user_id):
    DOWNLOAD_LOCKS[user_id] = True


def stop_download_lock(user_id):
    DOWNLOAD_LOCKS.pop(user_id, None)


# =========================================================
# USER MODE
# =========================================================

def is_owner(user_id):
    return int(user_id) == OWNER_ID


def get_user_mode(user_id):
    if not is_owner(user_id):
        return "user"

    try:
        mode = database.get_user_mode(user_id)

        if mode:
            return mode

    except Exception:
        pass

    return "owner"


def set_user_mode(user_id, mode):
    try:
        database.set_user_mode(user_id, mode)
    except Exception:
        pass


# =========================================================
# BOT STATUS
# =========================================================

def bot_is_running():
    return BOT_RUNNING


def set_bot_status(status):
    global BOT_RUNNING
    BOT_RUNNING = bool(status)


# =========================================================
# KEYBOARDS
# =========================================================

def user_menu():
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.row(
        "🎬 Download Video",
        "🎵 Download MP3"
    )

    keyboard.row(
        "🔑 Activate Key",
        "📋 My License"
    )

    keyboard.row(
        "🔄 Retry Last Download",
        "ℹ️ Help"
    )

    if is_owner_from_context():
        pass

    return keyboard


def owner_menu():
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.row(
        "🎬 Download Video",
        "🎵 Download MP3"
    )

    keyboard.row(
        "🔑 License Control",
        "👥 User Management"
    )

    keyboard.row(
        "📊 Statistics",
        "⚙️ Bot Control"
    )

    keyboard.row(
        "👤 User Mode"
    )

    return keyboard


def owner_mode_menu():
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.row(
        "🎬 Download Video",
        "🎵 Download MP3"
    )

    keyboard.row(
        "🔑 License Control",
        "👥 User Management"
    )

    keyboard.row(
        "📊 Statistics",
        "⚙️ Bot Control"
    )

    keyboard.row(
        "👤 User Mode"
    )

    return keyboard


def user_mode_menu():
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.row(
        "🎬 Download Video",
        "🎵 Download MP3"
    )

    keyboard.row(
        "🔑 Activate Key",
        "📋 My License"
    )

    keyboard.row(
        "🔄 Retry Last Download",
        "ℹ️ Help"
    )

    if is_owner_from_context():
        keyboard.row(
            "👑 Owner Mode"
        )

    return keyboard


def is_owner_from_context():
    return False


# =========================================================
# QUALITY BUTTONS
# =========================================================

def video_quality_menu():
    keyboard = types.InlineKeyboardMarkup()

    keyboard.row(
        types.InlineKeyboardButton(
            "📱 Smooth",
            callback_data="video_smooth"
        ),
        types.InlineKeyboardButton(
            "720p",
            callback_data="video_720"
        )
    )

    keyboard.row(
        types.InlineKeyboardButton(
            "1080p",
            callback_data="video_1080"
        ),
        types.InlineKeyboardButton(
            "4K / Source",
            callback_data="video_source"
        )
    )

    keyboard.row(
        types.InlineKeyboardButton(
            "❌ Cancel",
            callback_data="cancel_download"
        )
    )

    return keyboard


def mp3_quality_menu():
    keyboard = types.InlineKeyboardMarkup()

    keyboard.row(
        types.InlineKeyboardButton(
            "🎵 128 kbps",
            callback_data="mp3_128"
        ),
        types.InlineKeyboardButton(
            "🎵 192 kbps",
            callback_data="mp3_192"
        )
    )

    keyboard.row(
        types.InlineKeyboardButton(
            "🎵 320 kbps",
            callback_data="mp3_320"
        )
    )

    keyboard.row(
        types.InlineKeyboardButton(
            "❌ Cancel",
            callback_data="cancel_download"
        )
    )

    return keyboard


# =========================================================
# LICENSE MENU
# =========================================================

def license_menu():
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.row(
        "➕ Generate Key",
        "🔍 Search Key"
    )

    keyboard.row(
        "⏱ Extend Key",
        "🚫 Disable Key"
    )

    keyboard.row(
        "🟢 Enable Key",
        "🗑 Delete Key"
    )

    keyboard.row(
        "📋 List Keys",
        "📊 Key Statistics"
    )

    keyboard.row(
        "🔙 Owner Menu"
    )

    return keyboard


# =========================================================
# USER MANAGEMENT MENU
# =========================================================

def user_management_menu():
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.row(
        "👥 List Users",
        "🔍 Search User"
    )

    keyboard.row(
        "🚫 Ban User",
        "🟢 Unban User"
    )

    keyboard.row(
        "🔙 Owner Menu"
    )

    return keyboard


# =========================================================
# BOT CONTROL MENU
# =========================================================

def bot_control_menu():
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.row(
        "▶️ Start Bot",
        "⏹ Stop Bot"
    )

    keyboard.row(
        "📊 Bot Status",
        "🔙 Owner Menu"
    )

    return keyboard


# =========================================================
# /START
# =========================================================

@bot.message_handler(commands=["start"])
def start_command(message):

    user_id = message.from_user.id

    try:
        database.register_user(
            user_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name or "",
            last_name=message.from_user.last_name or ""
        )
    except Exception:
        pass

    clear_state(user_id)

    # Owner
    if is_owner(user_id):

        mode = get_user_mode(user_id)

        if mode == "user":
            bot.send_message(
                message.chat.id,
                "👤 <b>User Mode</b>\n\n"
                "You are currently using User Mode.",
                reply_markup=user_mode_menu()
            )
            return

        bot.send_message(
            message.chat.id,
            "👑 <b>NUTHH Downloader</b>\n\n"
            "Owner Mode activated.",
            reply_markup=owner_menu()
        )
        return

    # Normal user
    bot.send_message(
        message.chat.id,
        "👋 <b>Welcome to NUTHH Downloader</b>\n\n"
        "Please activate a valid license before downloading.",
        reply_markup=user_menu()
    )


# =========================================================
# /HELP
# =========================================================

@bot.message_handler(commands=["help"])
def help_command(message):

    text = (
        "ℹ️ <b>NUTHH Downloader Help</b>\n\n"
        "🎬 Download Video\n"
        "Download video with quality selection.\n\n"
        "🎵 Download MP3\n"
        "Convert video audio to MP3.\n\n"
        "🔑 Activate Key\n"
        "Activate your license key.\n\n"
        "🔄 Retry Last Download\n"
        "Retry the previous download.\n\n"
        "All functions are available from the buttons."
    )

    bot.send_message(
        message.chat.id,
        text
    )


# =========================================================
# OWNER MODE
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "👤 User Mode"
)
def owner_to_user_mode(message):

    set_user_mode(
        message.from_user.id,
        "user"
    )

    bot.send_message(
        message.chat.id,
        "👤 <b>User Mode Activated</b>\n\n"
        "Owner controls are hidden.\n"
        "You can switch back using 👑 Owner Mode.",
        reply_markup=user_mode_menu()
    )


# =========================================================
# USER -> OWNER MODE
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "👑 Owner Mode"
)
def user_to_owner_mode(message):

    set_user_mode(
        message.from_user.id,
        "owner"
    )

    bot.send_message(
        message.chat.id,
        "👑 <b>Owner Mode Activated</b>",
        reply_markup=owner_menu()
    )


# =========================================================
# LICENSE CHECK
# =========================================================

def check_license(user_id):

    try:
        return database.has_valid_license(user_id)
    except Exception:
        return False


# =========================================================
# DOWNLOAD VIDEO BUTTON
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🎬 Download Video"
)
def download_video_button(message):

    user_id = message.from_user.id

    if not bot_is_running() and not is_owner(user_id):

        bot.send_message(
            message.chat.id,
            "⏹ <b>Bot is currently stopped.</b>\n\n"
            "Please try again later."
        )

        return

    if not is_owner(user_id):

        if not check_license(user_id):

            bot.send_message(
                message.chat.id,
                "🔒 <b>License Required</b>\n\n"
                "Please activate a valid license first.",
                reply_markup=user_mode_menu()
            )

            return

    set_state(
        user_id,
        "waiting_video_url"
    )

    bot.send_message(
        message.chat.id,
        "🎬 <b>Download Video</b>\n\n"
        "Send the video URL.",
        reply_markup=types.ReplyKeyboardRemove()
    )


# =========================================================
# DOWNLOAD MP3 BUTTON
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🎵 Download MP3"
)
def download_mp3_button(message):

    user_id = message.from_user.id

    if not bot_is_running() and not is_owner(user_id):

        bot.send_message(
            message.chat.id,
            "⏹ <b>Bot is currently stopped.</b>"
        )

        return

    if not is_owner(user_id):

        if not check_license(user_id):

            bot.send_message(
                message.chat.id,
                "🔒 <b>License Required</b>\n\n"
                "Please activate a valid license first.",
                reply_markup=user_mode_menu()
            )

            return

    set_state(
        user_id,
        "waiting_mp3_url"
    )

    bot.send_message(
        message.chat.id,
        "🎵 <b>Download MP3</b>\n\n"
        "Send the video URL.",
        reply_markup=types.ReplyKeyboardRemove()
    )


# =========================================================
# ACTIVATE LICENSE
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🔑 Activate Key"
)
def activate_key_button(message):

    set_state(
        message.from_user.id,
        "activate_key"
    )

    bot.send_message(
        message.chat.id,
        "🔑 <b>Activate License</b>\n\n"
        "Please send your license key."
    )


# =========================================================
# MY LICENSE
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "📋 My License"
)
def my_license_button(message):

    user_id = message.from_user.id

    try:
        licenses = database.get_user_licenses(user_id)
    except Exception:
        licenses = []

    if not licenses:

        bot.send_message(
            message.chat.id,
            "🔒 You do not have an active license."
        )

        return

    text = "📋 <b>Your License</b>\n\n"

    for item in licenses:

        try:
            key = item["key"]
            status = item["status"]
            expires = item["expires_at"]

        except Exception:
            continue

        text += (
            f"🔑 <code>{html.escape(str(key))}</code>\n"
            f"Status: {html.escape(str(status))}\n"
            f"Expires: {html.escape(str(expires))}\n\n"
        )

    bot.send_message(
        message.chat.id,
        text
    )


# =========================================================
# RETRY LAST DOWNLOAD
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🔄 Retry Last Download"
)
def retry_last_download(message):

    user_id = message.from_user.id

    if not is_owner(user_id) and not check_license(user_id):

        bot.send_message(
            message.chat.id,
            "🔒 Valid license required."
        )

        return

    last = LAST_DOWNLOAD.get(user_id)

    if not last:

        bot.send_message(
            message.chat.id,
            "ℹ️ There is no previous download to retry."
        )

        return

    if last["type"] == "video":

        set_state(
            user_id,
            "retry_video_quality",
            {
                "url": last["url"]
            }
        )

        bot.send_message(
            message.chat.id,
            "🔄 <b>Select video quality:</b>",
            reply_markup=video_quality_menu()
        )

    else:

        set_state(
            user_id,
            "retry_mp3_quality",
            {
                "url": last["url"]
            }
        )

        bot.send_message(
            message.chat.id,
            "🔄 <b>Select MP3 quality:</b>",
            reply_markup=mp3_quality_menu()
        )


# =========================================================
# URL STATE HANDLER
# =========================================================

@bot.message_handler(
    func=lambda message:
    get_state(message.from_user.id) is not None
)
def state_handler(message):

    user_id = message.from_user.id
    state_data = get_state(user_id)

    if not state_data:
        return

    state = state_data["state"]
    data = state_data["data"]

    # -----------------------------------------------------
    # ACTIVATE KEY
    # -----------------------------------------------------

    if state == "activate_key":

        key = message.text.strip()

        try:
            result = license.activate_license(
                user_id,
                key
            )
        except Exception as error:
            result = {
                "success": False,
                "message": str(error)
            }

        clear_state(user_id)

        if result.get("success"):

            bot.send_message(
                message.chat.id,
                "✅ <b>License Activated</b>\n\n"
                "You can now download videos.",
                reply_markup=user_mode_menu()
            )

        else:

            bot.send_message(
                message.chat.id,
                "❌ <b>License Activation Failed</b>\n\n"
                f"{html.escape(str(result.get('message', 'Invalid key.')))}",
                reply_markup=user_mode_menu()
            )

        return

    # -----------------------------------------------------
    # VIDEO URL
    # -----------------------------------------------------

    if state == "waiting_video_url":

        url = message.text.strip()

        if not url.startswith(("http://", "https://")):

            bot.send_message(
                message.chat.id,
                "❌ Please send a valid URL."
            )

            return

        set_state(
            user_id,
            "video_quality",
            {
                "url": url
            }
        )

        bot.send_message(
            message.chat.id,
            "🎬 <b>Select Video Quality</b>",
            reply_markup=video_quality_menu()
        )

        return

    # -----------------------------------------------------
    # MP3 URL
    # -----------------------------------------------------

    if state == "waiting_mp3_url":

        url = message.text.strip()

        if not url.startswith(("http://", "https://")):

            bot.send_message(
                message.chat.id,
                "❌ Please send a valid URL."
            )

            return

        set_state(
            user_id,
            "mp3_quality",
            {
                "url": url
            }
        )

        bot.send_message(
            message.chat.id,
            "🎵 <b>Select MP3 Quality</b>",
            reply_markup=mp3_quality_menu()
        )

        return


# =========================================================
# CALLBACK QUERY
# =========================================================

@bot.callback_query_handler(
    func=lambda call: True
)
def callback_handler(call):

    user_id = call.from_user.id

    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    # -----------------------------------------------------
    # CANCEL
    # -----------------------------------------------------

    if call.data == "cancel_download":

        clear_state(user_id)

        try:
            bot.edit_message_text(
                "❌ Download cancelled.",
                call.message.chat.id,
                call.message.message_id
            )
        except Exception:
            bot.send_message(
                call.message.chat.id,
                "❌ Download cancelled."
            )

        return

    # -----------------------------------------------------
    # VIDEO QUALITY
    # -----------------------------------------------------

    if call.data.startswith("video_"):

        quality = call.data.replace(
            "video_",
            ""
        )

        state_data = get_state(user_id)

        if not state_data:
            bot.send_message(
                call.message.chat.id,
                "❌ Session expired. Please start again."
            )
            return

        url = state_data["data"].get("url")

        if not url:
            bot.send_message(
                call.message.chat.id,
                "❌ URL not found."
            )
            clear_state(user_id)
            return

        clear_state(user_id)

        start_download(
            user_id=user_id,
            chat_id=call.message.chat.id,
            url=url,
            download_type="video",
            quality=quality
        )

        return

    # -----------------------------------------------------
    # MP3 QUALITY
    # -----------------------------------------------------

    if call.data.startswith("mp3_"):

        quality = call.data.replace(
            "mp3_",
            ""
        )

        state_data = get_state(user_id)

        if not state_data:
            bot.send_message(
                call.message.chat.id,
                "❌ Session expired."
            )
            return

        url = state_data["data"].get("url")

        if not url:
            bot.send_message(
                call.message.chat.id,
                "❌ URL not found."
            )
            clear_state(user_id)
            return

        clear_state(user_id)

        start_download(
            user_id=user_id,
            chat_id=call.message.chat.id,
            url=url,
            download_type="mp3",
            quality=quality
        )

        return


# =========================================================
# DOWNLOAD THREAD
# =========================================================

def start_download(
    user_id,
    chat_id,
    url,
    download_type,
    quality
):

    if is_downloading(user_id):

        bot.send_message(
            chat_id,
            "⏳ You already have a download running.\n\n"
            "Please wait until it finishes."
        )

        return

    start_download_lock(user_id)

    LAST_DOWNLOAD[user_id] = {
        "url": url,
        "type": download_type,
        "quality": quality
    }

    thread = threading.Thread(
        target=download_worker,
        args=(
            user_id,
            chat_id,
            url,
            download_type,
            quality
        ),
        daemon=True
    )

    thread.start()


# =========================================================
# DOWNLOAD WORKER
# =========================================================

def download_worker(
    user_id,
    chat_id,
    url,
    download_type,
    quality
):

    progress_message = None

    try:

        progress_message = bot.send_message(
            chat_id,
            "⏳ <b>Preparing download...</b>\n"
            "Please wait."
        )

        def progress_callback(info):

            nonlocal progress_message

            try:

                status = info.get("status")

                if status == "downloading":

                    downloaded = info.get(
                        "downloaded_bytes",
                        0
                    )

                    total = info.get(
                        "total_bytes"
                    ) or info.get(
                        "total_bytes_estimate"
                    ) or 0

                    speed = info.get(
                        "speed"
                    )

                    eta = info.get(
                        "eta"
                    )

                    if total:

                        percent = (
                            downloaded /
                            total *
                            100
                        )

                        percent = min(
                            100,
                            max(0, percent)
                        )

                    else:

                        percent = 0

                    if speed:

                        speed_mb = (
                            speed / 1024 / 1024
                        )

                        speed_text = (
                            f"{speed_mb:.2f} MB/s"
                        )

                    else:

                        speed_text = "N/A"

                    if eta is not None:
                        eta_text = f"{eta}s"
                    else:
                        eta_text = "N/A"

                    text = (
                        "⬇️ <b>Downloading...</b>\n\n"
                        f"Progress: <b>{percent:.1f}%</b>\n"
                        f"Speed: <b>{speed_text}</b>\n"
                        f"ETA: <b>{eta_text}</b>"
                    )

                    try:

                        bot.edit_message_text(
                            text,
                            chat_id,
                            progress_message.message_id
                        )

                    except Exception:
                        pass

                elif status == "finished":

                    try:

                        bot.edit_message_text(
                            "🔄 <b>Download complete.</b>\n"
                            "Processing file with FFmpeg...",
                            chat_id,
                            progress_message.message_id
                        )

                    except Exception:
                        pass

            except Exception:
                pass

        # -------------------------------------------------
        # VIDEO
        # -------------------------------------------------

        if download_type == "video":

            result = downloader.download_video(
                url=url,
                quality=quality,
                progress_callback=progress_callback
            )

        # -------------------------------------------------
        # MP3
        # -------------------------------------------------

        else:

            result = downloader.download_mp3(
                url=url,
                quality=quality,
                progress_callback=progress_callback
            )

        if not result:

            raise RuntimeError(
                "Downloader returned no result."
            )

        success = result.get(
            "success",
            False
        )

        if not success:

            error_message = result.get(
                "error",
                "Download failed."
            )

            raise RuntimeError(
                str(error_message)
            )

        file_path = result.get(
            "file_path"
        )

        title = result.get(
            "title",
            "NUTHH Download"
        )

        if not file_path:

            raise RuntimeError(
                "Downloaded file path was not returned."
            )

        if not os.path.exists(file_path):

            raise RuntimeError(
                "Downloaded file does not exist."
            )

        # -------------------------------------------------
        # SEND FILE
        # -------------------------------------------------

        safe_title = html.escape(
            str(title)
        )

        try:

            bot.edit_message_text(
                "📤 <b>Uploading to Telegram...</b>",
                chat_id,
                progress_message.message_id
            )

        except Exception:
            pass

        if download_type == "video":

            with open(
                file_path,
                "rb"
            ) as video_file:

                bot.send_video(
                    chat_id,
                    video_file,
                    caption=(
                        "✅ <b>Download Complete</b>\n\n"
                        f"🎬 {safe_title}\n"
                        f"📺 Quality: {html.escape(str(quality))}"
                    ),
                    supports_streaming=True,
                    timeout=300
                )

        else:

            with open(
                file_path,
                "rb"
            ) as audio_file:

                bot.send_audio(
                    chat_id,
                    audio_file,
                    caption=(
                        "✅ <b>MP3 Complete</b>\n\n"
                        f"🎵 {safe_title}\n"
                        f"🎧 Quality: {html.escape(str(quality))} kbps"
                    ),
                    timeout=300
                )

        try:
            database.record_download(
                user_id=user_id,
                url=url,
                download_type=download_type,
                quality=quality
            )
        except Exception:
            pass

        try:

            bot.send_message(
                chat_id,
                "✅ <b>Finished.</b>",
                reply_markup=(
                    owner_menu()
                    if is_owner(user_id)
                    and get_user_mode(user_id) == "owner"
                    else user_mode_menu()
                )
            )

        except Exception:
            pass

    except Exception as error:

        error_text = str(error)

        print(
            f"[DOWNLOAD ERROR] "
            f"user={user_id}: {error_text}"
        )

        try:

            bot.send_message(
                chat_id,
                "❌ <b>Download Failed</b>\n\n"
                f"{html.escape(error_text[:1500])}\n\n"
                "You can use 🔄 Retry Last Download."
            )

        except Exception:
            pass

    finally:

        stop_download_lock(user_id)

        # Auto cleanup
        try:

            if "file_path" in locals():
                if file_path and os.path.exists(file_path):
                    downloader.cleanup_file(
                        file_path
                    )

        except Exception as cleanup_error:

            print(
                f"[CLEANUP ERROR] "
                f"{cleanup_error}"
            )


# =========================================================
# LICENSE CONTROL
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "🔑 License Control"
)
def license_control(message):

    clear_state(
        message.from_user.id
    )

    bot.send_message(
        message.chat.id,
        "🔑 <b>License Control</b>",
        reply_markup=license_menu()
    )


# =========================================================
# GENERATE KEY
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "➕ Generate Key"
)
def generate_key_button(message):

    set_state(
        message.from_user.id,
        "generate_key"
    )

    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.row(
        "1 Minute",
        "10 Minutes"
    )

    keyboard.row(
        "1 Hour",
        "1 Day"
    )

    keyboard.row(
        "7 Days",
        "30 Days"
    )

    keyboard.row(
        "90 Days",
        "1 Year"
    )

    keyboard.row(
        "Lifetime",
        "🔙 License Control"
    )

    bot.send_message(
        message.chat.id,
        "➕ <b>Generate License Key</b>\n\n"
        "Select duration:",
        reply_markup=keyboard
    )


# =========================================================
# GENERATE KEY DURATION
# =========================================================

DURATION_MAP = {
    "1 Minute": 1,
    "10 Minutes": 10,
    "1 Hour": 60,
    "1 Day": 1440,
    "7 Days": 10080,
    "30 Days": 43200,
    "90 Days": 129600,
    "1 Year": 525600,
}


@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text in DURATION_MAP
)
def generate_key_duration(message):

    user_id = message.from_user.id

    try:

        minutes = DURATION_MAP[
            message.text
        ]

        result = license.generate_key(
            duration_minutes=minutes
        )

        if isinstance(result, dict):

            key = result.get(
                "key",
                "Unknown"
            )

            expires = result.get(
                "expires_at",
                "Unknown"
            )

        else:

            key = str(result)
            expires = "Unknown"

        bot.send_message(
            message.chat.id,
            "✅ <b>License Key Created</b>\n\n"
            f"🔑 <code>{html.escape(str(key))}</code>\n"
            f"⏱ Duration: {html.escape(message.text)}\n"
            f"📅 Expires: {html.escape(str(expires))}",
            reply_markup=license_menu()
        )

    except Exception as error:

        bot.send_message(
            message.chat.id,
            "❌ <b>Could not generate key.</b>\n\n"
            f"{html.escape(str(error))}",
            reply_markup=license_menu()
        )

    finally:

        clear_state(user_id)


# =========================================================
# SEARCH KEY
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "🔍 Search Key"
)
def search_key_button(message):

    set_state(
        message.from_user.id,
        "search_key"
    )

    bot.send_message(
        message.chat.id,
        "🔍 Send the license key to search."
    )


# =========================================================
# EXTEND KEY
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "⏱ Extend Key"
)
def extend_key_button(message):

    set_state(
        message.from_user.id,
        "extend_key"
    )

    bot.send_message(
        message.chat.id,
        "⏱ Send the license key you want to extend."
    )


# =========================================================
# EXTEND DURATION
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "⏱ 1 Day"
)
def extend_one_day(message):

    state_data = get_state(
        message.from_user.id
    )

    if not state_data:
        return

    if state_data["state"] != "extend_duration":
        return

    process_extend_key(
        message,
        1440
    )


@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "⏱ 7 Days"
)
def extend_seven_days(message):

    state_data = get_state(
        message.from_user.id
    )

    if not state_data:
        return

    if state_data["state"] != "extend_duration":
        return

    process_extend_key(
        message,
        10080
    )


@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "⏱ 30 Days"
)
def extend_thirty_days(message):

    state_data = get_state(
        message.from_user.id
    )

    if not state_data:
        return

    if state_data["state"] != "extend_duration":
        return

    process_extend_key(
        message,
        43200
    )


@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "⏱ 1 Year"
)
def extend_one_year(message):

    state_data = get_state(
        message.from_user.id
    )

    if not state_data:
        return

    if state_data["state"] != "extend_duration":
        return

    process_extend_key(
        message,
        525600
    )


def process_extend_key(message, minutes):

    user_id = message.from_user.id

    state_data = get_state(user_id)

    if not state_data:
        return

    key = state_data["data"].get(
        "key"
    )

    if not key:

        bot.send_message(
            message.chat.id,
            "❌ Key not found."
        )

        clear_state(user_id)
        return

    try:

        result = license.extend_key(
            key,
            minutes
        )

        if isinstance(result, dict):
            success = result.get(
                "success",
                False
            )
            msg = result.get(
                "message",
                ""
            )
        else:
            success = True
            msg = str(result)

        if success:

            bot.send_message(
                message.chat.id,
                "✅ <b>License Extended</b>\n\n"
                f"🔑 <code>{html.escape(key)}</code>\n"
                f"⏱ Added: {minutes} minutes\n"
                f"{html.escape(str(msg))}",
                reply_markup=license_menu()
            )

        else:

            bot.send_message(
                message.chat.id,
                "❌ Extension failed.\n\n"
                f"{html.escape(str(msg))}",
                reply_markup=license_menu()
            )

    except Exception as error:

        bot.send_message(
            message.chat.id,
            "❌ Extension failed.\n\n"
            f"{html.escape(str(error))}",
            reply_markup=license_menu()
        )

    clear_state(user_id)


# =========================================================
# DISABLE KEY
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "🚫 Disable Key"
)
def disable_key_button(message):

    set_state(
        message.from_user.id,
        "disable_key"
    )

    bot.send_message(
        message.chat.id,
        "🚫 Send the key to disable."
    )


# =========================================================
# ENABLE KEY
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "🟢 Enable Key"
)
def enable_key_button(message):

    set_state(
        message.from_user.id,
        "enable_key"
    )

    bot.send_message(
        message.chat.id,
        "🟢 Send the key to enable."
    )


# =========================================================
# DELETE KEY
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "🗑 Delete Key"
)
def delete_key_button(message):

    set_state(
        message.from_user.id,
        "delete_key"
    )

    bot.send_message(
        message.chat.id,
        "🗑 Send the key to delete."
    )


# =========================================================
# LIST KEYS
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "📋 List Keys"
)
def list_keys_button(message):

    try:

        keys = database.get_all_license_keys()

        if not keys:

            bot.send_message(
                message.chat.id,
                "📋 No license keys found."
            )

            return

        text = "📋 <b>License Keys</b>\n\n"

        for item in keys[:50]:

            if isinstance(item, dict):

                key = item.get(
                    "key",
                    ""
                )

                status = item.get(
                    "status",
                    ""
                )

                expires = item.get(
                    "expires_at",
                    ""
                )

                text += (
                    f"🔑 <code>{html.escape(str(key))}</code>\n"
                    f"Status: {html.escape(str(status))}\n"
                    f"Expires: {html.escape(str(expires))}\n\n"
                )

        bot.send_message(
            message.chat.id,
            text
        )

    except Exception as error:

        bot.send_message(
            message.chat.id,
            "❌ Could not load keys.\n\n"
            f"{html.escape(str(error))}"
        )


# =========================================================
# KEY STATISTICS
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "📊 Key Statistics"
)
def key_statistics(message):

    try:

        stats = database.get_license_statistics()

        text = (
            "📊 <b>License Statistics</b>\n\n"
            f"🔑 Total Keys: {stats.get('total', 0)}\n"
            f"🟢 Active: {stats.get('active', 0)}\n"
            f"🚫 Disabled: {stats.get('disabled', 0)}\n"
            f"👥 Activated Users: {stats.get('users', 0)}"
        )

        bot.send_message(
            message.chat.id,
            text
        )

    except Exception as error:

        bot.send_message(
            message.chat.id,
            "❌ Could not load statistics.\n\n"
            f"{html.escape(str(error))}"
        )


# =========================================================
# USER MANAGEMENT
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "👥 User Management"
)
def user_management(message):

    clear_state(
        message.from_user.id
    )

    bot.send_message(
        message.chat.id,
        "👥 <b>User Management</b>",
        reply_markup=user_management_menu()
    )


# =========================================================
# LIST USERS
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "👥 List Users"
)
def list_users(message):

    try:

        users = database.get_all_users()

        if not users:

            bot.send_message(
                message.chat.id,
                "👥 No users found."
            )

            return

        text = "👥 <b>Users</b>\n\n"

        for user in users[:50]:

            if isinstance(user, dict):

                uid = user.get(
                    "user_id",
                    ""
                )

                username = user.get(
                    "username",
                    ""
                )

                name = user.get(
                    "first_name",
                    ""
                )

                banned = user.get(
                    "banned",
                    False
                )

                status = (
                    "🚫 Banned"
                    if banned
                    else "🟢 Active"
                )

                text += (
                    f"ID: <code>{uid}</code>\n"
                    f"Username: @{html.escape(str(username))}\n"
                    f"Name: {html.escape(str(name))}\n"
                    f"Status: {status}\n\n"
                )

        bot.send_message(
            message.chat.id,
            text
        )

    except Exception as error:

        bot.send_message(
            message.chat.id,
            "❌ Could not load users.\n\n"
            f"{html.escape(str(error))}"
        )


# =========================================================
# SEARCH USER
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "🔍 Search User"
)
def search_user_button(message):

    set_state(
        message.from_user.id,
        "search_user"
    )

    bot.send_message(
        message.chat.id,
        "🔍 Send User ID or username."
    )


# =========================================================
# BAN USER
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "🚫 Ban User"
)
def ban_user_button(message):

    set_state(
        message.from_user.id,
        "ban_user"
    )

    bot.send_message(
        message.chat.id,
        "🚫 Send the User ID to ban."
    )


# =========================================================
# UNBAN USER
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "🟢 Unban User"
)
def unban_user_button(message):

    set_state(
        message.from_user.id,
        "unban_user"
    )

    bot.send_message(
        message.chat.id,
        "🟢 Send the User ID to unban."
    )


# =========================================================
# STATISTICS
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "📊 Statistics"
)
def statistics_button(message):

    try:

        stats = database.get_statistics()

        text = (
            "📊 <b>NUTHH Statistics</b>\n\n"
            f"👥 Users: {stats.get('users', 0)}\n"
            f"⬇️ Downloads: {stats.get('downloads', 0)}\n"
            f"🎬 Videos: {stats.get('videos', 0)}\n"
            f"🎵 MP3: {stats.get('mp3', 0)}"
        )

        bot.send_message(
            message.chat.id,
            text
        )

    except Exception as error:

        bot.send_message(
            message.chat.id,
            "❌ Statistics unavailable.\n\n"
            f"{html.escape(str(error))}"
        )


# =========================================================
# BOT CONTROL
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "⚙️ Bot Control"
)
def bot_control(message):

    bot.send_message(
        message.chat.id,
        "⚙️ <b>Bot Control</b>",
        reply_markup=bot_control_menu()
    )


# =========================================================
# START BOT
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "▶️ Start Bot"
)
def start_bot_button(message):

    set_bot_status(True)

    bot.send_message(
        message.chat.id,
        "▶️ <b>Bot Started</b>\n\n"
        "Users can now use the downloader.",
        reply_markup=bot_control_menu()
    )


# =========================================================
# STOP BOT
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "⏹ Stop Bot"
)
def stop_bot_button(message):

    set_bot_status(False)

    bot.send_message(
        message.chat.id,
        "⏹ <b>Bot Stopped</b>\n\n"
        "User downloading is disabled.\n"
        "Owner controls remain available.",
        reply_markup=bot_control_menu()
    )


# =========================================================
# BOT STATUS
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "📊 Bot Status"
)
def bot_status_button(message):

    if BOT_RUNNING:

        status = "🟢 RUNNING"

    else:

        status = "🔴 STOPPED"

    bot.send_message(
        message.chat.id,
        f"⚙️ <b>Bot Status</b>\n\n"
        f"Status: {status}"
    )


# =========================================================
# OWNER MENU BACK
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "🔙 Owner Menu"
)
def owner_menu_back(message):

    clear_state(
        message.from_user.id
    )

    set_user_mode(
        message.from_user.id,
        "owner"
    )

    bot.send_message(
        message.chat.id,
        "👑 <b>Owner Menu</b>",
        reply_markup=owner_menu()
    )


# =========================================================
# LICENSE CONTROL BACK
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
    and message.text == "🔙 License Control"
)
def license_control_back(message):

    clear_state(
        message.from_user.id
    )

    bot.send_message(
        message.chat.id,
        "🔑 <b>License Control</b>",
        reply_markup=license_menu()
    )


# =========================================================
# SEARCH / EXTEND / KEY ACTION STATES
# =========================================================

@bot.message_handler(
    func=lambda message:
    is_owner(message.from_user.id)
)
def owner_state_handler(message):

    user_id = message.from_user.id
    state_data = get_state(user_id)

    if not state_data:
        return

    state = state_data["state"]

    # -----------------------------------------------------
    # SEARCH KEY
    # -----------------------------------------------------

    if state == "search_key":

        key = message.text.strip()

        try:

            result = database.get_license_by_key(
                key
            )

            if not result:

                bot.send_message(
                    message.chat.id,
                    "❌ Key not found."
                )

            else:

                bot.send_message(
                    message.chat.id,
                    "🔍 <b>Key Information</b>\n\n"
                    f"🔑 <code>{html.escape(str(result.get('key', key)))}</code>\n"
                    f"Status: {html.escape(str(result.get('status', '')))}\n"
                    f"Expires: {html.escape(str(result.get('expires_at', '')))}\n"
                    f"Activations: {result.get('activations', 0)}"
                )

        except Exception as error:

            bot.send_message(
                message.chat.id,
                "❌ Search failed.\n\n"
                f"{html.escape(str(error))}"
            )

        clear_state(user_id)
        return

    # -----------------------------------------------------
    # EXTEND KEY
    # -----------------------------------------------------

    if state == "extend_key":

        key = message.text.strip()

        set_state(
            user_id,
            "extend_duration",
            {
                "key": key
            }
        )

        keyboard = types.ReplyKeyboardMarkup(
            resize_keyboard=True
        )

        keyboard.row(
            "⏱ 1 Day",
            "⏱ 7 Days"
        )

        keyboard.row(
            "⏱ 30 Days",
            "⏱ 1 Year"
        )

        keyboard.row(
            "🔙 License Control"
        )

        bot.send_message(
            message.chat.id,
            "⏱ <b>Select extension duration:</b>",
            reply_markup=keyboard
        )

        return

    # -----------------------------------------------------
    # DISABLE KEY
    # -----------------------------------------------------

    if state == "disable_key":

        key = message.text.strip()

        try:

            result = license.disable_key(
                key
            )

            bot.send_message(
                message.chat.id,
                "🚫 <b>Key Disabled</b>\n\n"
                f"🔑 <code>{html.escape(key)}</code>\n\n"
                f"{html.escape(str(result))}",
                reply_markup=license_menu()
            )

        except Exception as error:

            bot.send_message(
                message.chat.id,
                "❌ Could not disable key.\n\n"
                f"{html.escape(str(error))}",
                reply_markup=license_menu()
            )

        clear_state(user_id)
        return

    # -----------------------------------------------------
    # ENABLE KEY
    # -----------------------------------------------------

    if state == "enable_key":

        key = message.text.strip()

        try:

            result = license.enable_key(
                key
            )

            bot.send_message(
                message.chat.id,
                "🟢 <b>Key Enabled</b>\n\n"
                f"🔑 <code>{html.escape(key)}</code>\n\n"
                f"{html.escape(str(result))}",
                reply_markup=license_menu()
            )

        except Exception as error:

            bot.send_message(
                message.chat.id,
                "❌ Could not enable key.\n\n"
                f"{html.escape(str(error))}",
                reply_markup=license_menu()
            )

        clear_state(user_id)
        return

    # -----------------------------------------------------
    # DELETE KEY
    # -----------------------------------------------------

    if state == "delete_key":

        key = message.text.strip()

        try:

            result = license.delete_key(
                key
            )

            bot.send_message(
                message.chat.id,
                "🗑 <b>Key Deleted</b>\n\n"
                f"🔑 <code>{html.escape(key)}</code>\n\n"
                f"{html.escape(str(result))}",
                reply_markup=license_menu()
            )

        except Exception as error:

            bot.send_message(
                message.chat.id,
                "❌ Could not delete key.\n\n"
                f"{html.escape(str(error))}",
                reply_markup=license_menu()
            )

        clear_state(user_id)
        return

    # -----------------------------------------------------
    # SEARCH USER
    # -----------------------------------------------------

    if state == "search_user":

        query = message.text.strip()

        try:

            result = database.search_user(
                query
            )

            if not result:

                bot.send_message(
                    message.chat.id,
                    "❌ User not found."
                )

            else:

                bot.send_message(
                    message.chat.id,
                    "🔍 <b>User Found</b>\n\n"
                    f"ID: <code>{result.get('user_id', '')}</code>\n"
                    f"Username: @{html.escape(str(result.get('username', '')))}\n"
                    f"Name: {html.escape(str(result.get('first_name', '')))}"
                )

        except Exception as error:

            bot.send_message(
                message.chat.id,
                "❌ Search failed.\n\n"
                f"{html.escape(str(error))}"
            )

        clear_state(user_id)
        return

    # -----------------------------------------------------
    # BAN USER
    # -----------------------------------------------------

    if state == "ban_user":

        try:

            target_id = int(
                message.text.strip()
            )

            if target_id == OWNER_ID:

                bot.send_message(
                    message.chat.id,
                    "❌ Owner cannot be banned."
                )

            else:

                database.set_user_banned(
                    target_id,
                    True
                )

                bot.send_message(
                    message.chat.id,
                    "🚫 <b>User Banned</b>\n\n"
                    f"User ID: <code>{target_id}</code>"
                )

        except Exception as error:

            bot.send_message(
                message.chat.id,
                "❌ Invalid User ID.\n\n"
                f"{html.escape(str(error))}"
            )

        clear_state(user_id)
        return

    # -----------------------------------------------------
    # UNBAN USER
    # -----------------------------------------------------

    if state == "unban_user":

        try:

            target_id = int(
                message.text.strip()
            )

            database.set_user_banned(
                target_id,
                False
            )

            bot.send_message(
                message.chat.id,
                "🟢 <b>User Unbanned</b>\n\n"
                f"User ID: <code>{target_id}</code>"
            )

        except Exception as error:

            bot.send_message(
                message.chat.id,
                "❌ Invalid User ID.\n\n"
                f"{html.escape(str(error))}"
            )

        clear_state(user_id)
        return


# =========================================================
# BAN CHECK
# =========================================================

@bot.message_handler(
    func=lambda message: True,
    content_types=[
        "text",
        "photo",
        "video",
        "audio",
        "document"
    ]
)
def fallback_handler(message):

    user_id = message.from_user.id

    # Owner always allowed
    if is_owner(user_id):
        return

    # Check banned user
    try:

        if database.is_user_banned(user_id):

            bot.send_message(
                message.chat.id,
                "🚫 <b>Your account is blocked.</b>"
            )

            return

    except Exception:
        pass

    # Bot stopped
    if not BOT_RUNNING:

        bot.send_message(
            message.chat.id,
            "⏹ <b>Downloader is currently stopped.</b>"
        )

        return

    # Unknown message
    bot.send_message(
        message.chat.id,
        "ℹ️ Please use the menu buttons.",
        reply_markup=user_menu()
    )


# =========================================================
# RUN BOT
# =========================================================

if __name__ == "__main__":

    print("=" * 50)
    print("NUTHH TikTok Downloader Bot")
    print("=" * 50)
    print("Bot is starting...")
    print("Repeated-message warning: DISABLED")
    print("Spam warning system: DISABLED")
    print("Owner ID:", OWNER_ID)
    print("=" * 50)

    while True:

        try:

            bot.infinity_polling(
                skip_pending=True,
                timeout=60,
                long_polling_timeout=60
            )

        except KeyboardInterrupt:

            print("Bot stopped by user.")
            break

        except Exception as error:

            print(
                "[BOT ERROR]",
                error
            )

            print(
                "Restarting polling in 5 seconds..."
            )

            time.sleep(5)
