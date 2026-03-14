import subprocess
import sys
import json


def fetch_video_ids(channel_url: str) -> list[str]:
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


def fetch_videos_metadata(channel_url: str) -> list[dict]:
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--flat-playlist",
        "--dump-single-json",
        channel_url,
    ]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "").strip() or "yt-dlp failed")

    data = json.loads(r.stdout)
    entries = data.get("entries", [])

    videos = []

    for entry in entries:
        video_id = entry.get("id")
        title = entry.get("title", "Bez naslova")
        duration = entry.get("duration") or 0
        thumbnail = entry.get("thumbnail") or ""
        url = f"https://www.youtube.com/watch?v={video_id}"

        if not video_id:
            continue

        videos.append({
            "video_id": video_id,
            "title": title,
            "duration": duration,
            "thumbnail": thumbnail,
            "url": url
        })

    return videos


if __name__ == "__main__":
    ids = fetch_video_ids(sys.argv[1])
    print(f"Found {len(ids)} video IDs.")
    print(ids[:10])