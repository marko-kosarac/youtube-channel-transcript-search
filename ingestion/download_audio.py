import subprocess
import sys
from pathlib import Path


def _is_members_only_or_private(msg: str) -> bool:
    s = (msg or "").lower()
    keywords = [
        "members-only",
        "this video is available to this channel's members",
        "private video",
        "unavailable",
        "has been removed",
        "sign in to confirm",
        "join this channel to get access",
    ]
    return any(k in s for k in keywords)


def _missing_ffmpeg(msg: str) -> bool:
    s = (msg or "").lower()
    return "ffprobe and ffmpeg not found" in s or "ffmpeg not found" in s or "ffprobe not found" in s


def download_audio_if_needed(video_id: str) -> tuple[bool, str | None]:
    repo_root = Path(__file__).resolve().parents[1]
    audio_dir = repo_root / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    out_file = audio_dir / f"{video_id}.mp3"
    if out_file.exists():
        return True, None

    url = f"https://www.youtube.com/watch?v={video_id}"

    command = [
        sys.executable, "-m", "yt_dlp",
        "--js-runtimes", "node",
        "--remote-components", "ejs:github",
        "-x", "--audio-format", "mp3",
        "-o", str(audio_dir / "%(id)s.%(ext)s"),
        url,
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return False, "Timeout (yt-dlp took too long)."
    except KeyboardInterrupt:
        return False, "Interrupted by user (Ctrl+C)."

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()

        if _is_members_only_or_private(stderr):
            return False, "Skipped (members-only/private/unavailable)"

        if _missing_ffmpeg(stderr):
            return False, "ffmpeg/ffprobe not found (should be fixed now)."

        return False, stderr

    if not out_file.exists():
        return False, "Audio download finished but mp3 file not found."

    print(f"🎧 Audio saved: {out_file.name}")
    return True, None
