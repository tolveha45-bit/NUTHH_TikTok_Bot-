import os
import threading
import time
from datetime import datetime

import telebot
from telebot import types

import database
from config import BOT_TOKEN, OWNER_ID
from license import can_download
from downloader import download_video, download_mp3


bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

database.init_db()


# =========================================================
# GLOBAL BOT STATE
# =========================================================

BOT_RUNNING = True

user_states = {}
download_lock = threading.Lock()


# =========================================================
# HELPERS
# =========================================================

def is_owner(user_id):
    return user_id == OWNER_ID


def is_admin_mode(user_id):
    return is_owner(user_id) and database.get_mode(user_id) == "owner"


def bot_is_running():
    return BOT_RUNNING


def set_bot_status(value):
    global BOT_RUNNING
    BOT_RUNNING = value


def safe_edit(chat_id, message_id, text, reply_markup=None):
    try:
        bot.edit_message_text(
            text,
            chat_id,
            message_id,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception:
        pass


def main_menu(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton(
            "🎬 Download Video",
            callback_data="download_video"
        ),
        types.InlineKeyboardButton(
            "🎵 Download MP3",
            callback_data="download_mp3"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "🔑 Activate Key",
            callback_data="activate_key"
        ),
        types.InlineKeyboardButton(
            "👤 My Account",
            callback_data="my_account"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "📖 Help",
            callback_data="help"
        ),
        types.InlineKeyboardButton(
            "ℹ️ About",
            callback_data="about"
        )
    )

    if is_owner(user_id):
        if database.get_mode(user_id) == "owner":
            markup.add(
                types.InlineKeyboardButton(
                    "👤 Switch to User Mode",
                    callback_data="switch_user"
                )
            )
        else:
            markup.add(
                types.InlineKeyboardButton(
                    "👑 Switch to Owner Mode",
                    callback_data="switch_owner"
                )
            )

    return markup


def owner_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton(
            "🔑 Key Control",
            callback_data="key_control"
        ),
        types.InlineKeyboardButton(
            "🤖 Bot Control",
            callback_data="bot_control"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "👥 User Management",
            callback_data="user_management"
        ),
        types.InlineKeyboardButton(
            "📊 Statistics",
            callback_data="statistics"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⚙️ Bot Settings",
            callback_data="settings"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "👤 Switch to User Mode",
            callback_data="switch_user"
        )
    )

    return markup


def back_button(callback="main"):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "🔙 Back",
            callback_data=callback
        )
    )
    return markup


# =========================================================
# /START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):
    database.register_user(message.from_user)

    if database.is_banned(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "🚫 You are banned from using this bot."
        )
        return

    if not BOT_RUNNING and not is_owner(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "🔴 Bot is temporarily stopped.\nPlease try again later."
        )
        return

    mode = database.get_mode(message.from_user.id)

    if is_owner(message.from_user.id) and mode == "owner":
        bot.send_message(
            message.chat.id,
            "👑 <b>NUTHH OWNER PANEL</b>\n\n"
            "Choose an option:",
            reply_markup=owner_menu()
        )
        return

    bot.send_message(
        message.chat.id,
        "🤖 <b>NUTHH TIKTOK DOWNLOADER</b>\n\n"
        "🎬 Video Downloader\n"
        "🎵 MP3 Downloader\n"
        "⚡ Fast & Smooth\n\n"
        "Choose an option:",
        reply_markup=main_menu(message.from_user.id)
    )


# =========================================================
# CALLBACK HANDLER
# =========================================================

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    database.register_user(call.from_user)

    if database.is_banned(user_id):
        bot.answer_callback_query(
            call.id,
            "You are banned.",
            show_alert=True
        )
        return

    data = call.data

    # -----------------------------------------
    # MODE SWITCH
    # -----------------------------------------

    if data == "switch_user":

        if not is_owner(user_id):
            return

        database.set_mode(user_id, "user")

        bot.edit_message_text(
            "👤 <b>USER MODE</b>\n\n"
            "You are now using the bot as a normal user.",
            chat_id,
            call.message.message_id,
            reply_markup=main_menu(user_id)
        )

        return

    if data == "switch_owner":

        if not is_owner(user_id):
            return

        database.set_mode(user_id, "owner")

        bot.edit_message_text(
            "👑 <b>OWNER MODE</b>\n\n"
            "Owner controls are now enabled.",
            chat_id,
            call.message.message_id,
            reply_markup=owner_menu()
        )

        return

    # -----------------------------------------
    # MAIN MENU
    # -----------------------------------------

    if data == "main":
        bot.edit_message_text(
            "🤖 <b>NUTHH MENU</b>",
            chat_id,
            call.message.message_id,
            reply_markup=main_menu(user_id)
        )
        return

    # -----------------------------------------
    # ACTIVATE KEY
    # -----------------------------------------

    if data == "activate_key":

        user_states[user_id] = {
            "state": "waiting_key"
        }

        bot.edit_message_text(
            "🔑 <b>ACTIVATE LICENSE KEY</b>\n\n"
            "Please send your license key.\n\n"
            "Example:\n"
            "<code>NUTHH-XXXX-XXXX-XXXX</code>",
            chat_id,
            call.message.message_id,
            reply_markup=back_button()
        )

        return

    # -----------------------------------------
    # ACCOUNT
    # -----------------------------------------

    if data == "my_account":

        active = can_download(user_id)

        status = "🟢 ACTIVE" if active else "🔴 NO ACTIVE LICENSE"

        bot.edit_message_text(
            f"👤 <b>MY ACCOUNT</b>\n\n"
            f"🆔 User ID: <code>{user_id}</code>\n"
            f"🔐 License: {status}",
            chat_id,
            call.message.message_id,
            reply_markup=back_button()
        )

        return

    # -----------------------------------------
    # VIDEO
    # -----------------------------------------

    if data == "download_video":

        if not can_download(user_id):
            bot.answer_callback_query(
                call.id,
                "🔒 Activate a valid key first.",
                show_alert=True
            )
            return

        markup = types.InlineKeyboardMarkup(row_width=2)

        markup.add(
            types.InlineKeyboardButton(
                "⚡ Smooth",
                callback_data="quality_smooth"
            ),
            types.InlineKeyboardButton(
                "720p",
                callback_data="quality_720"
            )
        )

        markup.add(
            types.InlineKeyboardButton(
                "1080p",
                callback_data="quality_1080"
            ),
            types.InlineKeyboardButton(
                "4K",
                callback_data="quality_4k"
            )
        )

        markup.add(
            types.InlineKeyboardButton(
                "🔙 Back",
                callback_data="main"
            )
        )

        bot.edit_message_text(
            "🎬 <b>SELECT VIDEO QUALITY</b>",
            chat_id,
            call.message.message_id,
            reply_markup=markup
        )

        return

    # -----------------------------------------
    # QUALITY
    # -----------------------------------------

    if data.startswith("quality_"):

        if not can_download(user_id):
            bot.answer_callback_query(
                call.id,
                "🔒 License expired or disabled.",
                show_alert=True
            )
            return

        quality = data.replace("quality_", "")

        user_states[user_id] = {
            "state": "waiting_video_url",
            "quality": quality
        }

        names = {
            "smooth": "⚡ Smooth",
            "720": "720p",
            "1080": "1080p",
            "4k": "4K"
        }

        bot.edit_message_text(
            f"🎬 <b>QUALITY: {names.get(quality, quality)}</b>\n\n"
            "📎 Send your TikTok URL:",
            chat_id,
            call.message.message_id,
            reply_markup=back_button()
        )

        return

    # -----------------------------------------
    # MP3
    # -----------------------------------------

    if data == "download_mp3":

        if not can_download(user_id):
            bot.answer_callback_query(
                call.id,
                "🔒 Activate a valid key first.",
                show_alert=True
            )
            return

        markup = types.InlineKeyboardMarkup(row_width=3)

        markup.add(
            types.InlineKeyboardButton(
                "128 kbps",
                callback_data="mp3_128"
            ),
            types.InlineKeyboardButton(
                "192 kbps",
                callback_data="mp3_192"
            ),
            types.InlineKeyboardButton(
                "320 kbps",
                callback_data="mp3_320"
            )
        )

        markup.add(
            types.InlineKeyboardButton(
                "🔙 Back",
                callback_data="main"
            )
        )

        bot.edit_message_text(
            "🎵 <b>SELECT MP3 QUALITY</b>",
            chat_id,
            call.message.message_id,
            reply_markup=markup
        )

        return

    if data.startswith("mp3_"):

        if not can_download(user_id):
            bot.answer_callback_query(
                call.id,
                "🔒 License expired or disabled.",
                show_alert=True
            )
            return

        bitrate = data.replace("mp3_", "")

        user_states[user_id] = {
            "state": "waiting_mp3_url",
            "bitrate": bitrate
        }

        bot.edit_message_text(
            f"🎵 <b>MP3 {bitrate} kbps</b>\n\n"
            "📎 Send your TikTok URL:",
            chat_id,
            call.message.message_id,
            reply_markup=back_button()
        )

        return

    # -----------------------------------------
    # HELP / ABOUT
    # -----------------------------------------

    if data == "help":

        bot.edit_message_text(
            "📖 <b>HELP</b>\n\n"
            "1️⃣ Activate a valid license key.\n"
            "2️⃣ Choose Video or MP3.\n"
            "3️⃣ Select quality.\n"
            "4️⃣ Send a supported TikTok URL.\n"
            "5️⃣ Wait for the download.",
            chat_id,
            call.message.message_id,
            reply_markup=back_button()
        )

        return

    if data == "about":

        bot.edit_message_text(
            "ℹ️ <b>ABOUT NUTHH BOT</b>\n\n"
            "TikTok Video & Audio Downloader\n"
            "Powered by Python + yt-dlp.",
            chat_id,
            call.message.message_id,
            reply_markup=back_button()
        )

        return

    # =====================================================
    # OWNER AREA
    # =====================================================

    if not is_admin_mode(user_id):
        bot.answer_callback_query(
            call.id,
            "Owner mode required.",
            show_alert=True
        )
        return

    # -----------------------------------------
    # KEY CONTROL
    # -----------------------------------------

    if data == "key_control":

        markup = types.InlineKeyboardMarkup(row_width=2)

        markup.add(
            types.InlineKeyboardButton(
                "➕ Generate Key",
                callback_data="generate_key"
            ),
            types.InlineKeyboardButton(
                "📋 All Keys",
                callback_data="all_keys"
            )
        )

        markup.add(
            types.InlineKeyboardButton(
                "⏳ Extend Key",
                callback_data="extend_key"
            ),
            types.InlineKeyboardButton(
                "⏸️ Disable Key",
                callback_data="disable_key"
            )
        )

        markup.add(
            types.InlineKeyboardButton(
                "▶️ Enable Key",
                callback_data="enable_key"
            ),
            types.InlineKeyboardButton(
                "🗑️ Delete Key",
                callback_data="delete_key"
            )
        )

        markup.add(
            types.InlineKeyboardButton(
                "🔙 Back",
                callback_data="owner_home"
            )
        )

        bot.edit_message_text(
            "🔑 <b>KEY CONTROL</b>",
            chat_id,
            call.message.message_id,
            reply_markup=markup
        )

        return

    # -----------------------------------------
    # GENERATE KEY
    # -----------------------------------------

    if data == "generate_key":

        markup = types.InlineKeyboardMarkup(row_width=3)

        durations = [
            ("1 Minute", 1),
            ("5 Minutes", 5),
            ("10 Minutes", 10),
            ("30 Minutes", 30),
            ("1 Hour", 60),
            ("6 Hours", 360),
            ("12 Hours", 720),
            ("1 Day", 1440),
            ("7 Days", 10080),
            ("30 Days", 43200),
            ("90 Days", 129600),
            ("♾️ Lifetime", 0),
        ]

        for name, minutes in durations:
            markup.add(
                types.InlineKeyboardButton(
                    name,
                    callback_data=f"gen_{minutes}"
                )
            )

        markup.add(
            types.InlineKeyboardButton(
                "🔙 Back",
                callback_data="key_control"
            )
        )

        bot.edit_message_text(
            "🔑 <b>GENERATE KEY</b>\n\n"
            "Select duration:\n"
            "👥 Users: ♾️ Unlimited\n"
            "💻 Devices: ♾️ Unlimited",
            chat_id,
            call.message.message_id,
            reply_markup=markup
        )

        return

    if data.startswith("gen_"):

        value = int(data.replace("gen_", ""))

        minutes = None if value == 0 else value

        key, expires = database.generate_license(minutes)

        if expires:
            expiry = datetime.fromisoformat(expires)
            expiry_text = expiry.strftime("%d/%m/%Y %H:%M UTC")
            duration_text = f"{value} minutes"
        else:
            expiry_text = "♾️ Lifetime"
            duration_text = "♾️ Lifetime"

        bot.edit_message_text(
            "🔑 <b>KEY CREATED</b>\n\n"
            f"<code>{key}</code>\n\n"
            f"🟢 Status: ACTIVE\n"
            f"⏱️ Duration: {duration_text}\n"
            f"👥 Users: ♾️ Unlimited\n"
            f"💻 Devices: ♾️ Unlimited\n"
            f"⏰ Expires: {expiry_text}",
            chat_id,
            call.message.message_id,
            reply_markup=back_button("key_control")
        )

        return

    # -----------------------------------------
    # ALL KEYS
    # -----------------------------------------

    if data == "all_keys":

        rows = database.list_licenses()

        if not rows:
            text = "📋 <b>ALL KEYS</b>\n\nNo keys found."
        else:
            text = "📋 <b>ALL KEYS</b>\n\n"

            for row in rows[:30]:

                status = "🟢" if row["active"] else "🔴"

                if row["expires_at"]:
                    expires = datetime.fromisoformat(
                        row["expires_at"]
                    ).strftime("%d/%m/%Y %H:%M")
                else:
                    expires = "♾️"

                text += (
                    f"{status} <code>{row['key']}</code>\n"
                    f"⏰ {expires}\n\n"
                )

        bot.edit_message_text(
            text,
            chat_id,
            call.message.message_id,
            reply_markup=back_button("key_control")
        )

        return

    # -----------------------------------------
    # DISABLE
    # -----------------------------------------

    if data == "disable_key":

        user_states[user_id] = {
            "state": "disable_key"
        }

        bot.edit_message_text(
            "⏸️ <b>DISABLE KEY</b>\n\n"
            "Send the key:",
            chat_id,
            call.message.message_id,
            reply_markup=back_button("key_control")
        )

        return

    # -----------------------------------------
    # ENABLE
    # -----------------------------------------

    if data == "enable_key":

        user_states[user_id] = {
            "state": "enable_key"
        }

        bot.edit_message_text(
            "▶️ <b>ENABLE KEY</b>\n\n"
            "Send the key:",
            chat_id,
            call.message.message_id,
            reply_markup=back_button("key_control")
        )

        return

    # -----------------------------------------
    # DELETE
    # -----------------------------------------

    if data == "delete_key":

        user_states[user_id] = {
            "state": "delete_key"
        }

        bot.edit_message_text(
            "🗑️ <b>DELETE KEY</b>\n\n"
            "Send the key:",
            chat_id,
            call.message.message_id,
            reply_markup=back_button("key_control")
        )

        return

    # -----------------------------------------
    # EXTEND
    # -----------------------------------------

    if data == "extend_key":

        user_states[user_id] = {
            "state": "extend_key_key"
        }

        bot.edit_message_text(
            "⏳ <b>EXTEND KEY</b>\n\n"
            "Send the key:",
            chat_id,
            call.message.message_id,
            reply_markup=back_button("key_control")
        )

        return

    # -----------------------------------------
    # BOT CONTROL
    # -----------------------------------------

    if data == "bot_control":

        status = "🟢 RUNNING" if BOT_RUNNING else "🔴 STOPPED"

        markup = types.InlineKeyboardMarkup(row_width=2)

        markup.add(
            types.InlineKeyboardButton(
                "⛔ Stop Bot",
                callback_data="stop_bot"
            ),
            types.InlineKeyboardButton(
                "▶️ Start Bot",
                callback_data="start_bot"
            )
        )

        markup.add(
            types.InlineKeyboardButton(
                "🔄 Refresh",
                callback_data="bot_control"
            )
        )

        markup.add(
            types.InlineKeyboardButton(
                "🔙 Back",
                callback_data="owner_home"
            )
        )

        bot.edit_message_text(
            f"🤖 <b>BOT CONTROL</b>\n\n"
            f"Status: {status}",
            chat_id,
            call.message.message_id,
            reply_markup=markup
        )

        return

    if data == "stop_bot":

        set_bot_status(False)

        bot.edit_message_text(
            "🤖 <b>BOT STATUS</b>\n\n"
            "🔴 STOPPED\n\n"
            "User downloads are disabled.",
            chat_id,
            call.message.message_id,
            reply_markup=back_button("bot_control")
        )

        return

    if data == "start_bot":

        set_bot_status(True)

        bot.edit_message_text(
            "🤖 <b>BOT STATUS</b>\n\n"
            "🟢 RUNNING\n\n"
            "Users can use the bot again.",
            chat_id,
            call.message.message_id,
            reply_markup=back_button("bot_control")
        )

        return

    # -----------------------------------------
    # USER MANAGEMENT
    # -----------------------------------------

    if data == "user_management":

        users = database.count_users()

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "🔙 Back",
                callback_data="owner_home"
            )
        )

        bot.edit_message_text(
            f"👥 <b>USER MANAGEMENT</b>\n\n"
            f"👤 Total Users: {users}",
            chat_id,
            call.message.message_id,
            reply_markup=markup
        )

        return

    # -----------------------------------------
    # STATISTICS
    # -----------------------------------------

    if data == "statistics":

        users = database.count_users()
        licenses = database.count_licenses()
        active = database.count_active_licenses()
        activations = database.count_activations()

        bot.edit_message_text(
            "📊 <b>BOT STATISTICS</b>\n\n"
            f"👥 Users: {users}\n"
            f"🔑 Total Keys: {licenses}\n"
            f"🟢 Active Keys: {active}\n"
            f"🔐 Activations: {activations}",
            chat_id,
            call.message.message_id,
            reply_markup=back_button("owner_home")
        )

        return

    # -----------------------------------------
    # SETTINGS
    # -----------------------------------------

    if data == "settings":

        bot.edit_message_text(
            "⚙️ <b>BOT SETTINGS</b>\n\n"
            "🎬 Video: Enabled\n"
            "🎵 MP3: Enabled\n"
            "⚡ Retry: Enabled\n"
            "🧹 Cleanup: Enabled\n"
            "♾️ Unlimited Key Users: Enabled",
            chat_id,
            call.message.message_id,
            reply_markup=back_button("owner_home")
        )

        return

    # -----------------------------------------
    # OWNER HOME
    # -----------------------------------------

    if data == "owner_home":

        bot.edit_message_text(
            "👑 <b>OWNER PANEL</b>\n\n"
            "Choose an option:",
            chat_id,
            call.message.message_id,
            reply_markup=owner_menu()
        )

        return


# =========================================================
# TEXT MESSAGE HANDLER
# =========================================================

@bot.message_handler(content_types=["text"])
def text_handler(message):

    user_id = message.from_user.id
    text = message.text.strip()

    database.register_user(message.from_user)

    if database.is_banned(user_id):
        bot.send_message(
            message.chat.id,
            "🚫 You are banned."
        )
        return

    state_data = user_states.get(user_id)

    if not state_data:
        bot.send_message(
            message.chat.id,
            "Please use the menu below:",
            reply_markup=main_menu(user_id)
        )
        return

    state = state_data.get("state")

    # =====================================================
    # ACTIVATE LICENSE
    # =====================================================

    if state == "waiting_key":

        ok, result = database.activate_license(
            text,
            user_id
        )

        user_states.pop(user_id, None)

        bot.send_message(
            message.chat.id,
            result,
            reply_markup=main_menu(user_id)
        )

        return

    # =====================================================
    # VIDEO URL
    # =====================================================

    if state == "waiting_video_url":

        if not can_download(user_id):
            user_states.pop(user_id, None)

            bot.send_message(
                message.chat.id,
                "🔒 Your license is no longer valid."
            )
            return

        quality = state_data["quality"]

        user_states.pop(user_id, None)

        download_message = bot.send_message(
            message.chat.id,
            "⏳ Preparing download..."
        )

        threading.Thread(
            target=process_video,
            args=(
                message,
                text,
                quality,
                download_message.message_id
            ),
            daemon=True
        ).start()

        return

    # =====================================================
    # MP3 URL
    # =====================================================

    if state == "waiting_mp3_url":

        if not can_download(user_id):
            user_states.pop(user_id, None)

            bot.send_message(
                message.chat.id,
                "🔒 Your license is no longer valid."
            )
            return

        bitrate = state_data["bitrate"]

        user_states.pop(user_id, None)

        download_message = bot.send_message(
            message.chat.id,
            "⏳ Preparing MP3..."
        )

        threading.Thread(
            target=process_mp3,
            args=(
                message,
                text,
                bitrate,
                download_message.message_id
            ),
            daemon=True
        ).start()

        return

    # =====================================================
    # OWNER KEY CONTROL INPUT
    # =====================================================

    if is_admin_mode(user_id):

        if state == "disable_key":

            result = database.disable_license(text)

            user_states.pop(user_id, None)

            bot.send_message(
                message.chat.id,
                "⏸️ Key disabled successfully."
                if result else
                "❌ Key not found.",
                reply_markup=owner_menu()
            )

            return

        if state == "enable_key":

            result = database.enable_license(text)

            user_states.pop(user_id, None)

            bot.send_message(
                message.chat.id,
                "▶️ Key enabled successfully."
                if result else
                "❌ Key not found.",
                reply_markup=owner_menu()
            )

            return

        if state == "delete_key":

            result = database.delete_license(text)

            user_states.pop(user_id, None)

            bot.send_message(
                message.chat.id,
                "🗑️ Key deleted."
                if result else
                "❌ Key not found.",
                reply_markup=owner_menu()
            )

            return

        if state == "extend_key_key":

            if database.get_license(text):

                user_states[user_id] = {
                    "state": "extend_key_minutes",
                    "key": text
                }

                bot.send_message(
                    message.chat.id,
                    "⏳ Send extension in minutes.\n\n"
                    "Example: <code>1440</code> = 1 day"
                )

            else:

                user_states.pop(user_id, None)

                bot.send_message(
                    message.chat.id,
                    "❌ Key not found.",
                    reply_markup=owner_menu()
                )

            return

        if state == "extend_key_minutes":

            try:
                minutes = int(text)

                if minutes <= 0:
                    raise ValueError

                key = state_data["key"]

                result = database.extend_license(
                    key,
                    minutes
                )

                user_states.pop(user_id, None)

                bot.send_message(
                    message.chat.id,
                    "⏳ Key extended successfully."
                    if result else
                    "❌ Failed to extend key.",
                    reply_markup=owner_menu()
                )

            except ValueError:

                bot.send_message(
                    message.chat.id,
                    "❌ Enter a valid positive number."
                )

            return


# =========================================================
# VIDEO PROCESS
# =========================================================

def process_video(message, url, quality, status_message_id):

    chat_id = message.chat.id

    try:

        if not bot_is_running() and not is_owner(message.from_user.id):
            bot.edit_message_text(
                "🔴 Bot is stopped.",
                chat_id,
                status_message_id
            )
            return

        last_update = [0]

        def progress(data):

            now = time.time()

            if now - last_update[0] < 2:
                return

            last_update[0] = now

            if data["status"] == "downloading":

                percent = data.get("_percent_str", "?")
                speed = data.get("_speed_str", "?")
                eta = data.get("_eta_str", "?")

                try:
                    bot.edit_message_text(
                        f"⬇️ <b>Downloading</b>\n\n"
                        f"📊 {percent}\n"
                        f"⚡ Speed: {speed}\n"
                        f"⏱️ ETA: {eta}",
                        chat_id,
                        status_message_id
                    )
                except Exception:
                    pass

        filename = download_video(
            url,
            quality,
            progress
        )

        if not os.path.exists(filename):
            raise FileNotFoundError(
                "Downloaded file does not exist."
            )

        bot.edit_message_text(
            "📤 Uploading video...",
            chat_id,
            status_message_id
        )

        with open(filename, "rb") as video:

            bot.send_video(
                chat_id,
                video,
                caption=(
                    "🎬 <b>NUTHH Downloader</b>\n"
                    f"Quality: {quality}"
                ),
                supports_streaming=True
            )

        try:
            os.remove(filename)
        except OSError:
            pass

        bot.delete_message(
            chat_id,
            status_message_id
        )

    except Exception as e:

        try:
            bot.edit_message_text(
                f"❌ <b>Download Failed</b>\n\n"
                f"<code>{str(e)[:1000]}</code>",
                chat_id,
                status_message_id
            )
        except Exception:
            pass


# =========================================================
# MP3 PROCESS
# =========================================================

def process_mp3(message, url, bitrate, status_message_id):

    chat_id = message.chat.id

    try:

        if not bot_is_running() and not is_owner(message.from_user.id):
            bot.edit_message_text(
                "🔴 Bot is stopped.",
                chat_id,
                status_message_id
            )
            return

        last_update = [0]

        def progress(data):

            now = time.time()

            if now - last_update[0] < 2:
                return

            last_update[0] = now

            if data["status"] == "downloading":

                percent = data.get("_percent_str", "?")
                speed = data.get("_speed_str", "?")
                eta = data.get("_eta_str", "?")

                try:
                    bot.edit_message_text(
                        f"🎵 <b>Downloading MP3</b>\n\n"
                        f"📊 {percent}\n"
                        f"⚡ Speed: {speed}\n"
                        f"⏱️ ETA: {eta}",
                        chat_id,
                        status_message_id
                    )
                except Exception:
                    pass

        filename = download_mp3(
            url,
            bitrate,
            progress
        )

        if not os.path.exists(filename):
            raise FileNotFoundError(
                "MP3 file not found."
            )

        bot.edit_message_text(
            "📤 Uploading MP3...",
            chat_id,
            status_message_id
        )

        with open(filename, "rb") as audio:

            bot.send_audio(
                chat_id,
                audio,
                caption=(
                    "🎵 <b>NUTHH Downloader</b>\n"
                    f"MP3: {bitrate} kbps"
                )
            )

        try:
            os.remove(filename)
        except OSError:
            pass

        bot.delete_message(
            chat_id,
            status_message_id
        )

    except Exception as e:

        try:
            bot.edit_message_text(
                f"❌ <b>MP3 Download Failed</b>\n\n"
                f"<code>{str(e)[:1000]}</code>",
                chat_id,
                status_message_id
            )
        except Exception:
            pass


# =========================================================
# RUN BOT
# =========================================================

if __name__ == "__main__":

    print("===================================")
    print(" NUTHH TikTok Downloader Bot")
    print("===================================")
    print(f"Owner ID: {OWNER_ID}")
    print("Bot is starting...")

    database.register_user(
        type(
            "Owner",
            (),
            {
                "id": OWNER_ID,
                "username": "",
                "first_name": "Owner"
            }
        )()
    )

    database.set_mode(
        OWNER_ID,
        "owner"
    )

    bot.infinity_polling(
        skip_pending=True,
        timeout=60,
        long_polling_timeout=60
    )
