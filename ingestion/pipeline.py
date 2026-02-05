import time
import random
from pathlib import Path

from fetch_videos import fetch_video_ids
from get_transcript import try_download_transcript
from download_audio import download_audio

LIMIT = 5  # None kad pustiš full run

def transcript_exists(video_id: str) -> bool:
    repo_root = Path(__file__).resolve().parents[1]
    return (repo_root / "transcripts" / f"{video_id}.json").exists()

def audio_exists(video_id: str) -> bool:
    repo_root = Path(__file__).resolve().parents[1]
    return (repo_root / "audio" / f"{video_id}.mp3").exists()

def main():
    ids = fetch_video_ids()
    print(f"Found {len(ids)} video IDs.")

    if LIMIT is not None:
        ids = ids[:LIMIT]
        print(f"Processing first {len(ids)} videos (LIMIT={LIMIT}).\n")

    for idx, vid in enumerate(ids, start=1):
        time.sleep(7 + random.random() * 5)  # 7–12s

        if transcript_exists(vid):
            print(f"[{idx}] {vid}: transcript cached")
            continue

        ok, status, err = try_download_transcript(vid)
        print(f"[{idx}] {vid}: transcript -> {status}")

        if status == "ip_blocked":
            print("\n⛔ IP blocked detected. Prekidam da ne pogoršam ban.")
            print("   Savjet: promijeni IP (restart router / reconnect) ili koristi mobilni hotspot.\n")
            break

        if ok:
            continue

        if audio_exists(vid):
            print(f"[{idx}] {vid}: audio cached")
            continue

        time.sleep(4 + random.random() * 4)  # 4–8s

        audio_ok, audio_err = download_audio(vid)
        if not audio_ok:
            print(f"❌ Audio failed for {vid}: {audio_err}")

    print("\n✅ Done.")

if __name__ == "__main__":
    main()
