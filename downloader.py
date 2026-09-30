import os
import glob
import subprocess
import time

import yt_dlp

from config import DOWNLOAD_DIR, MAX_RETRIES, DOWNLOAD_TIMEOUT


os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def cleanup_files(pattern):
    for file in glob.glob(pattern):
        try:
            os.remove(file)
        except OSError:
            pass


def get_info(url):
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        return ydl.extract_info(url, download=False)


def quality_format(quality):
    if quality == "smooth":
        return "bestvideo[height<=480]+bestaudio/best[height<=480]"

    if quality == "720":
        return "bestvideo[height<=720]+bestaudio/best[height<=720]"

    if quality == "1080":
        return "bestvideo[height<=1080]+bestaudio/best[height<=1080]"

    if quality == "4k":
        return "bestvideo[height<=2160]+bestaudio/best[height<=2160]"

    return "bestvideo+bestaudio/best"


def download_video(url, quality="smooth", progress_callback=None):
    output_template = os.path.join(
        DOWNLOAD_DIR,
        "%(id)s.%(ext)s"
    )

    fmt = quality_format(quality)

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):

        try:
            def hook(data):
                if progress_callback:
                    progress_callback(data)

            options = {
                "format": fmt,
                "outtmpl": output_template,
                "merge_output_format": "mp4",
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "retries": 3,
                "fragment_retries": 3,
                "socket_timeout": 30,
                "progress_hooks": [hook],
            }

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

            if not filename.lower().endswith(".mp4"):
                possible = os.path.splitext(filename)[0] + ".mp4"

                if os.path.exists(possible):
                    filename = possible

            return filename

        except Exception as e:
            last_error = e

            if attempt < MAX_RETRIES:
                time.sleep(2)

    raise RuntimeError(
        f"Download failed after {MAX_RETRIES} attempts: {last_error}"
    )


def download_mp3(url, bitrate="192", progress_callback=None):
    output_template = os.path.join(
        DOWNLOAD_DIR,
        "%(id)s.%(ext)s"
    )

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):

        try:
            def hook(data):
                if progress_callback:
                    progress_callback(data)

            options = {
                "format": "bestaudio/best",
                "outtmpl": output_template,
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "retries": 3,
                "fragment_retries": 3,
                "socket_timeout": 30,
                "progress_hooks": [hook],

                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": bitrate,
                    }
                ],
            }

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)

            base = os.path.splitext(
                os.path.join(
                    DOWNLOAD_DIR,
                    f"{info['id']}.{info.get('ext', 'webm')}"
                )
            )[0]

            mp3 = base + ".mp3"

            if os.path.exists(mp3):
                return mp3

            matches = glob.glob(
                os.path.join(
                    DOWNLOAD_DIR,
                    f"{info['id']}.*"
                )
            )

            for item in matches:
                if item.lower().endswith(".mp3"):
                    return item

            raise FileNotFoundError("MP3 output file not found.")

        except Exception as e:
            last_error = e

            if attempt < MAX_RETRIES:
                time.sleep(2)

    raise RuntimeError(
        f"MP3 download failed after {MAX_RETRIES} attempts: {last_error}"
    )
