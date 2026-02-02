import subprocess
import sys

CHANNEL_URL = "https://www.youtube.com/@TragBiljke/videos"

def main():
    print("Fetching video IDs from channel...\n")

    command = [
        sys.executable, "-m", "yt_dlp",
        "--flat-playlist",
        "--print", "%(id)s",
        CHANNEL_URL
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        print("Error running yt-dlp:\n")
        print(result.stderr)
        return

    video_ids = result.stdout.strip().splitlines()

    print("First 10 video IDs:\n")
    for vid in video_ids[:10]:
        print(vid)

    print(f"\nTotal videos listed: {len(video_ids)}")

if __name__ == "__main__":
    main()
