import subprocess
import sys
from pathlib import Path

def download_audio(video_id: str) -> tuple[bool, str | None]:
    repo_root = Path(__file__).resolve().parents[1]
    out_dir = repo_root / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{video_id}.mp3"

    if out_path.exists():
        return True, None

    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        sys.executable, "-m", "yt_dlp",

        "--sleep-interval", "1",
        "--max-sleep-interval", "3",

        "--retries", "5",
        "--fragment-retries", "5",
        "--retry-sleep", "fragment:5",

        "--limit-rate", "750K",

        "-x", "--audio-format", "mp3",
        "-o", str(out_dir / "%(id)s.%(ext)s"),
        url,
    ]

    r = subprocess.run(cmd, capture_output=True, text=True)

    if r.returncode != 0:
        return False, (r.stderr or "").strip() or "yt-dlp audio failed"

    if not out_path.exists():
        return False, "Audio download finished but mp3 file not found."

    print(f"🎧 Audio saved: {out_path.name}")
    return True, None

if __name__ == "__main__":
    user_input = input("Unesi YouTube video ID: ").strip()

    ok, err = download_audio(user_input)

    if ok:
        print("\n✅ DOWNLOAD USPJESAN")
    else:
        print("\n❌ DOWNLOAD FAIL:")
        print(err)
