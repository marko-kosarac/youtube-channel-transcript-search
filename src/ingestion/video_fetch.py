import subprocess
import sys

CHANNEL_URL = "https://www.youtube.com/@Cile/videos"
# CHANNEL_URL = "https://www.youtube.com/@dvaipopsihijatra/videos"

def fetch_video_ids(channel_url: str = CHANNEL_URL) -> list[str]:
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--flat-playlist",
        "--sleep-interval", "1",
        "--max-sleep-interval", "3",
        "--retries", "5",
        "--print", "%(id)s",
        channel_url,
    ]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "").strip() or "yt-dlp failed")

    return [line.strip() for line in r.stdout.splitlines() if line.strip()]


if __name__ == "__main__":
    ids = fetch_video_ids()
    print(f"Found {len(ids)} video IDs.")
    print(ids[:10])
