import os
import glob
import time
import threading

import yt_dlp

from config import (
    TEMP_DIR,
    COMPLETED_DIR,
    MAX_RETRIES,
    DOWNLOAD_TIMEOUT
)


class DownloadCancelled(Exception):
    pass


def clean_name(name):

    if not name:
        return "NUTHH_Download"

    allowed = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        " _-."
    )

    result = "".join(
        char for char in name
        if char in allowed
    )

    result = result.strip()

    return result[:100] or "NUTHH_Download"


def bytes_text(value):

    if not value:
        return "0 B"

    value = float(value)

    units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB"
    ]

    for unit in units:

        if value < 1024:
            return f"{value:.1f} {unit}"

        value /= 1024

    return f"{value:.1f} PB"


def speed_text(value):

    if not value:
        return "0 B/s"

    return bytes_text(value) + "/s"


def eta_text(seconds):

    if seconds is None:
        return "--:--"

    try:

        seconds = int(seconds)

        hours = seconds // 3600

        minutes = (
            seconds % 3600
        ) // 60

        secs = seconds % 60

        if hours:
            return (
                f"{hours:02d}:"
                f"{minutes:02d}:"
                f"{secs:02d}"
            )

        return (
            f"{minutes:02d}:"
            f"{secs:02d}"
        )

    except Exception:

        return "--:--"


def remove_file(path):

    try:

        if path and os.path.exists(path):
            os.remove(path)

    except Exception:
        pass


def video_format(quality):

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

    # Source / highest available
    return (
        "bestvideo+bestaudio/"
        "best"
    )


class Downloader:

    def __init__(
        self,
        progress_callback=None,
        cancel_event=None
    ):

        self.progress_callback = (
            progress_callback
        )

        self.cancel_event = (
            cancel_event
        )

    def check_cancel(self):

        if self.cancel_event:

            if self.cancel_event.is_set():
                raise DownloadCancelled()

    def hook(self, data):

        self.check_cancel()

        status = data.get("status")

        if status == "downloading":

            downloaded = data.get(
                "downloaded_bytes",
                0
            )

            total = (
                data.get("total_bytes")
                or data.get(
                    "total_bytes_estimate"
                )
                or 0
            )

            percent = 0

            if total:
                percent = (
                    downloaded / total
                ) * 100

            info = {
                "status": "downloading",
                "percent": percent,
                "downloaded": bytes_text(
                    downloaded
                ),
                "total": bytes_text(
                    total
                ),
                "speed": speed_text(
                    data.get("speed")
                ),
                "eta": eta_text(
                    data.get("eta")
                )
            }

            if self.progress_callback:
                self.progress_callback(info)

        elif status == "finished":

            if self.progress_callback:

                self.progress_callback({
                    "status": "processing"
                })

    def _download(
        self,
        url,
        output,
        format_string,
        audio=False,
        mp3_quality="192"
    ):

        self.check_cancel()

        options = {

            "outtmpl": output,

            "format": format_string,

            "noplaylist": True,

            "retries": MAX_RETRIES,

            "fragment_retries": MAX_RETRIES,

            "file_access_retries": MAX_RETRIES,

            "extractor_retries": MAX_RETRIES,

            "socket_timeout": DOWNLOAD_TIMEOUT,

            "continuedl": True,

            "overwrites": False,

            "nopart": False,

            "concurrent_fragment_downloads": 4,

            "progress_hooks": [
                self.hook
            ],

            "quiet": True,

            "no_warnings": True,

            "restrictfilenames": True,

            "windowsfilenames": True,

            "cachedir": False,

            "noplaylist": True,

            "ignoreerrors": False,

            "geo_bypass": True,

            "http_headers": {
                "User-Agent":
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/154.0 Safari/537.36"
            }
        }

        if audio:

            options["format"] = (
                "bestaudio/best"
            )

            options["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(
                    mp3_quality
                )
            }]

        else:

            options["merge_output_format"] = "mp4"

        with yt_dlp.YoutubeDL(
            options
        ) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

        return info

    def _find_files(self, prefix):

        return glob.glob(
            os.path.join(
                TEMP_DIR,
                prefix + "*"
            )
        )

    def video(
        self,
        url,
        quality="720"
    ):

        timestamp = str(
            int(time.time() * 1000)
        )

        prefix = (
            "video_"
            + timestamp
        )

        output = os.path.join(
            TEMP_DIR,
            prefix + "_%(title).100s.%(ext)s"
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
                    output=output,
                    format_string=video_format(
                        quality
                    ),
                    audio=False
                )

                self.check_cancel()

                title = info.get(
                    "title",
                    "NUTHH_Video"
                )

                files = self._find_files(
                    prefix
                )

                files = [
                    x for x in files
                    if os.path.isfile(x)
                    and not x.endswith(".part")
                ]

                if not files:

                    raise RuntimeError(
                        "Downloaded file was not found."
                    )

                source = max(
                    files,
                    key=os.path.getmtime
                )

                ext = os.path.splitext(
                    source
                )[1]

                destination = os.path.join(
                    COMPLETED_DIR,
                    clean_name(title)
                    + "_"
                    + timestamp
                    + ext
                )

                os.replace(
                    source,
                    destination
                )

                return {
                    "success": True,
                    "path": destination,
                    "title": title,
                    "duration": info.get(
                        "duration",
                        0
                    )
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
                        "error": str(error)
                    })

                if attempt < MAX_RETRIES:

                    time.sleep(
                        min(
                            30,
                            attempt * 3
                        )
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

        timestamp = str(
            int(time.time() * 1000)
        )

        prefix = (
            "audio_"
            + timestamp
        )

        output = os.path.join(
            TEMP_DIR,
            prefix + "_%(title).100s.%(ext)s"
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
                    output=output,
                    format_string="bestaudio/best",
                    audio=True,
                    mp3_quality=quality
                )

                self.check_cancel()

                title = info.get(
                    "title",
                    "NUTHH_Audio"
                )

                files = self._find_files(
                    prefix
                )

                files = [
                    x for x in files
                    if os.path.isfile(x)
                    and not x.endswith(".part")
                ]

                if not files:

                    raise RuntimeError(
                        "MP3 file was not found."
                    )

                mp3_files = [
                    x for x in files
                    if x.lower().endswith(".mp3")
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

                destination = os.path.join(
                    COMPLETED_DIR,
                    clean_name(title)
                    + "_"
                    + timestamp
                    + ".mp3"
                )

                os.replace(
                    source,
                    destination
                )

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
                        "error": str(error)
                    })

                if attempt < MAX_RETRIES:

                    time.sleep(
                        min(
                            30,
                            attempt * 3
                        )
                    )

        return {
            "success": False,
            "error": str(last_error)
        }


def cleanup(path):

    remove_file(path)
