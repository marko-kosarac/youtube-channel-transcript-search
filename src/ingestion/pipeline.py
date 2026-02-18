import time
import random
from pathlib import Path

from video_fetch import fetch_video_ids
from video_transcription import try_download_transcript
from audio_download import download_audio
from whisper_transcription import transcribe_audio

LIMIT = 5 
WHISPER_MODEL = "medium"

def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def yt_transcript_exists(video_id: str) -> bool:
    return (repo_root() / "data" / "transcripts" / f"{video_id}.json").exists()

def whisper_transcript_exists(video_id: str) -> bool:
    return (repo_root() / "data" / "transcripts" / f"{video_id}.json").exists()

def audio_exists(video_id: str) -> bool:
    return (repo_root() / "data" / "audio" / f"{video_id}.mp3").exists()

def jitter_sleep(a: float, b: float):
    time.sleep(a + random.random() * (b - a))

def main():
    ids = fetch_video_ids()
    print(f"Found {len(ids)} video IDs.")

    if LIMIT is not None:
        ids = ids[:LIMIT]
        print(f"Processing first {len(ids)} videos (LIMIT={LIMIT}).\n")

    for idx, vid in enumerate(ids, start=1):
        if yt_transcript_exists(vid):
            print(f"[{idx}] {vid}: YouTube transcript cached")
            continue
        if whisper_transcript_exists(vid):
            print(f"[{idx}] {vid}: Whisper transcript cached")
            continue

        jitter_sleep(7, 12)

        ok, status, err = try_download_transcript(vid)
        print(f"[{idx}] {vid}: transcript -> {status}")

        if status == "ip_blocked":
            print("\nIP blocked detected.")
            break

        if ok:
            continue

        if not audio_exists(vid):
            jitter_sleep(4, 8)
            audio_ok, audio_err = download_audio(vid)
            if not audio_ok:
                print(f"Audio failed for {vid}: {audio_err}")
                continue
        else:
            print(f"[{idx}] {vid}: audio cached")

        print(f"[{idx}] {vid}: running Whisper ({WHISPER_MODEL})...")
        whisper_ok = transcribe_audio(vid, model_name=WHISPER_MODEL)
        if not whisper_ok:
            print(f"Whisper failed for {vid}")

    print("\nDone.")

if __name__ == "__main__":
    main()
