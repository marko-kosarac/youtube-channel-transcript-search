# import subprocess
# import sys

# CHANNEL_URL = "https://www.youtube.com/@TragBiljke/videos"

# def main():
#     print("Fetching video IDs from channel...\n")

#     command = [
#         sys.executable, "-m", "yt_dlp",
#         "--flat-playlist",
#         "--print", "%(id)s",
#         CHANNEL_URL
#     ]

#     result = subprocess.run(command, capture_output=True, text=True)

#     if result.returncode != 0:
#         print("Error running yt-dlp:\n")
#         print(result.stderr)
#         return

#     video_ids = result.stdout.strip().splitlines()

#     print("First 10 video IDs:\n")
#     for vid in video_ids[:10]:
#         print(vid)

#     print(f"\nTotal videos listed: {len(video_ids)}")

# if __name__ == "__main__":
#     main()

import subprocess
import sys

# Kanal koji obrađuješ (možeš promijeniti)
# CHANNEL_URL = "https://www.youtube.com/@dvaipopsihijatra/videos"
CHANNEL_URL = "https://www.youtube.com/@TragBiljke/videos"
# CHANNEL_URL = "https://www.youtube.com/@nedeljkostankovic3929/videos"



def fetch_video_ids() -> list[str]:
    """
    Izvuče video ID-eve sa kanala koristeći yt-dlp.
    Ne skida ništa, samo listu.
    """
    command = [
        sys.executable, "-m", "yt_dlp",
        "--flat-playlist",
        "--print", "%(id)s",
        CHANNEL_URL
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError("yt-dlp error:\n" + result.stderr)

    ids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return ids


# Ako pokreneš ovaj fajl direktno, samo će ispisati prvih 10 ID-eva
def main():
    ids = fetch_video_ids()
    print(f"Found {len(ids)} videos. First 10 IDs:\n")
    for vid in ids[:30]:
        print(vid)


if __name__ == "__main__":
    main()

