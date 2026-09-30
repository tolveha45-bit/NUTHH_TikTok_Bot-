import os
import glob
import time
import threading
from typing import Callable, Optional

import yt_dlp

from config import (
    TEMP_DIR,
    COMPLETED_DIR,
    MAX_RETRIES,
    DOWNLOAD_TIMEOUT
)


class DownloadCancelled(Exception):
    pass


def format_bytes(value):
    if not value:
        return "0 B"

    units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB"
    ]

    size = float(value)

    for unit in units:
        if size < 1024:
            return f"{size:.1f} {unit}"

        size /= 1024

    return f"{size:.1f} PB"


def format_speed(value):
    if not value:
        return "0 B/s"

    return format_bytes(value) + "/s"


def format_eta(seconds):
    if seconds is None:
        return "--:--"

    try:
        seconds = int(seconds)

        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60

        if h:
            return f"{h:02d}:{m:02d}:{s:02d}"

        return f"{m:02d}:{s:02d}"

    except Exception:
        return "--:--"


def cleanup_files(folder):
    try:
        for path in glob.glob(
            os.path.join(folder, "*")
        ):
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except Exception:
                pass

    except Exception:
        pass


def quality_format(quality):
    quality = str(quality).lower()

    if quality == "smooth":
        return (
            "bestvideo[height<=480]+bestaudio/"
            "best[height<=480]/"
            "best"
        )

    if quality == "720":
        return (
            "bestvideo[height<=720]+bestaudio/"
            "best[height<=720]/"
            "best"
        )

    if quality == "1080":
        return (
            "bestvideo[height<=1080]+bestaudio/"
            "best[height<=1080]/"
            "best"
        )

    if quality in ("4k", "source"):
        return (
            "bestvideo+bestaudio/"
            "best"
        )

    return "bestvideo+bestaudio/best"


class Downloader:

    def __init__(
        self,
        progress_callback: Optional[Callable] = None,
        cancel_event: Optional[threading.Event] = None
    ):
        self.progress_callback = progress_callback
        self.cancel_event = cancel_event

    def check_cancel(self):
        if self.cancel_event:
            if self.cancel_event.is_set():
                raise DownloadCancelled()

    def progress_hook(self, data):

        self.check_cancel()

        status = data.get("status")

        if status == "downloading":

            downloaded = data.get(
                "downloaded_bytes",
                0
            )

            total = (
                data.get("total_bytes")
                or data.get("total_bytes_estimate")
                or 0
            )

            percentage = 0

            if total:
                percentage = downloaded / total * 100

            speed = data.get(
                "speed",
                0
            )

            eta = data.get(
                "eta"
            )

            info = {
                "status": "downloading",
                "percent": percentage,
                "downloaded": format_bytes(downloaded),
                "total": format_bytes(total),
                "speed": format_speed(speed),
                "eta": format_eta(eta)
            }

            if self.progress_callback:
                self.progress_callback(info)

        elif status == "finished":

            if self.progress_callback:
                self.progress_callback({
                    "status": "processing",
                    "percent": 100,
                    "downloaded": "",
                    "total": "",
                    "speed": "",
                    "eta": ""
                })

    def _download(
        self,
        url,
        output_template,
        format_string,
        audio=False
    ):

        self.check_cancel()

        options = {
            "outtmpl": output_template,

            "format": format_string,

            "noplaylist": True,

            "retries": MAX_RETRIES,

            "fragment_retries": MAX_RETRIES,

            "file_access_retries": MAX_RETRIES,

            "extractor_retries": MAX_RETRIES,

            "socket_timeout": DOWNLOAD_TIMEOUT,

            "http_chunk_size": 10 * 1024 * 1024,

            "continuedl": True,

            "overwrites": False,

            "nopart": False,

            "concurrent_fragment_downloads": 4,

            "progress_hooks": [
                self.progress_hook
            ],

            "quiet": True,

            "no_warnings": True,

            "restrictfilenames": True,

            "windowsfilenames": True,

            "cachedir": False,

            "writethumbnail": False,

            "writeinfojson": False,

            "writesubtitles": False,

            "ignoreerrors": False,

            "postprocessors": []
        }

        if audio:
            options["format"] = (
                "bestaudio/best"
            )

            options["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": self.mp3_quality
            }]

        else:
            options["merge_output_format"] = "mp4"

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(
                url,
                download=True
            )

        return info

    def video(
        self,
        url,
        quality="720",
        mp3_quality="192"
    ):

        self.mp3_quality = mp3_quality

        timestamp = int(time.time())

        output_template = os.path.join(
            TEMP_DIR,
            f"{timestamp}_%(title).80s.%(ext)s"
        )

        fmt = quality_format(quality)

        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):

            try:

                self.check_cancel()

                if self.progress_callback:
                    self.progress_callback({
                        "status": "starting",
                        "attempt": attempt,
                        "max_attempts": MAX_RETRIES
                    })

                info = self._download(
                    url=url,
                    output_template=output_template,
                    format_string=fmt,
                    audio=False
                )

                self.check_cancel()

                title = (
                    info.get("title")
                    or "NUTHH_Video"
                )

                files = glob.glob(
                    os.path.join(
                        TEMP_DIR,
                        f"{timestamp}_*"
                    )
                )

                if not files:
                    raise RuntimeError(
                        "Downloaded file not found."
                    )

                source = max(
                    files,
                    key=os.path.getmtime
                )

                extension = os.path.splitext(
                    source
                )[1]

                safe_name = "".join(
                    c for c in title
                    if c.isalnum()
                    or c in " ._-"
                ).strip()

                if not safe_name:
                    safe_name = "NUTHH_Video"

                destination = os.path.join(
                    COMPLETED_DIR,
                    f"{safe_name}_{timestamp}{extension}"
                )

                os.replace(
                    source,
                    destination
                )

                if self.progress_callback:
                    self.progress_callback({
                        "status": "done",
                        "title": title,
                        "path": destination,
                        "duration": info.get("duration", 0)
                    })

                return {
                    "success": True,
                    "path": destination,
                    "title": title,
                    "duration": info.get("duration", 0)
                }

            except DownloadCancelled:
                raise

            except Exception as error:

                last_error = error

                if self.progress_callback:
                    self.progress_callback({
                        "status": "retry",
                        "attempt": attempt,
                        "max_attempts": MAX_RETRIES,
                        "error": str(error)[:200]
                    })

                if attempt < MAX_RETRIES:
                    time.sleep(
                        min(30, attempt * 3)
                    )

        return {
            "success": False,
            "error": str(last_error)
        }

    def mp3(
        self,
        url,
        quality="192"
    ):

        self.mp3_quality = str(quality)

        timestamp = int(time.time())

        output_template = os.path.join(
            TEMP_DIR,
            f"{timestamp}_%(title).80s.%(ext)s"
        )

        last_error = None

        for attempt in range(
            1,
            MAX_RETRIES + 1
        ):

            try:

                self.check_cancel()

                if self.progress_callback:
                    self.progress_callback({
                        "status": "starting",
                        "attempt": attempt,
                        "max_attempts": MAX_RETRIES
                    })

                info = self._download(
                    url=url,
                    output_template=output_template,
                    format_string="bestaudio/best",
                    audio=True
                )

                self.check_cancel()

                title = (
                    info.get("title")
                    or "NUTHH_Audio"
                )

                files = glob.glob(
                    os.path.join(
                        TEMP_DIR,
                        f"{timestamp}_*"
                    )
                )

                if not files:
                    raise RuntimeError(
                        "MP3 file not found."
                    )

                mp3_files = [
                    f for f in files
                    if f.lower().endswith(".mp3")
                ]

                source = (
                    max(
                        mp3_files,
                        key=os.path.getmtime
                    )
                    if mp3_files
                    else max(
                        files,
                        key=os.path.getmtime
                    )
                )

                safe_name = "".join(
                    c for c in title
                    if c.isalnum()
                    or c in " ._-"
                ).strip()

                if not safe_name:
                    safe_name = "NUTHH_Audio"

                destination = os.path.join(
                    COMPLETED_DIR,
                    f"{safe_name}_{timestamp}.mp3"
                )

                os.replace(
                    source,
                    destination
                )

                if self.progress_callback:
                    self.progress_callback({
                        "status": "done",
                        "title": title,
                        "path": destination
                    })

                return {
                    "success": True,
                    "path": destination,
                    "title": title
                }

            except DownloadCancelled:
                raise

            except Exception as error:

                last_error = error

                if self.progress_callback:
                    self.progress_callback({
                        "status": "retry",
                        "attempt": attempt,
                        "max_attempts": MAX_RETRIES,
                        "error": str(error)[:200]
                    })

                if attempt < MAX_RETRIES:
                    time.sleep(
                        min(30, attempt * 3)
                    )

        return {
            "success": False,
            "error": str(last_error)
        }


def cleanup_completed_file(path):

    try:
        if path and os.path.exists(path):
            os.remove(path)

    except Exception:
        pass
