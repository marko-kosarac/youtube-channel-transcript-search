import time
import random
import sys
import json
from pathlib import Path

from video_fetch import fetch_video_ids, fetch_videos_metadata
from video_transcription import try_download_transcript
from audio_download import download_audio
from whisper_transcription import transcribe_audio

LIMIT = 5
WHISPER_MODEL = "medium"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def status_file() -> Path:
    path = repo_root() / "data" / "status" / "current_status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def videos_file() -> Path:
    path = repo_root() / "data" / "channel_videos" / "videos.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_status(
    status: str,
    message: str,
    progress: int = 0,
    error: str | None = None,
    videos_ready: bool = False,
):
    payload = {
        "status": status,
        "message": message,
        "progress": progress,
        "error": error,
        "videos_ready": videos_ready,
    }
    status_file().write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def save_videos_metadata(videos: list[dict]):
    videos_file().write_text(
        json.dumps(videos, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def yt_transcript_exists(video_id: str) -> bool:
    return (repo_root() / "data" / "transcripts" / f"{video_id}.json").exists()


def whisper_transcript_exists(video_id: str) -> bool:
    return (repo_root() / "data" / "transcripts" / f"{video_id}.json").exists()


def audio_exists(video_id: str) -> bool:
    return (repo_root() / "data" / "audio" / f"{video_id}.mp3").exists()


def jitter_sleep(a: float, b: float):
    time.sleep(a + random.random() * (b - a))


def main():

    channel_url = sys.argv[1].strip()

    try:
        write_status("running", "Preuzimanje liste videa...", 5, None, False)

        ids = fetch_video_ids(channel_url)
        videos = fetch_videos_metadata(channel_url)

        if LIMIT is not None:
            videos = videos[:LIMIT]
        save_videos_metadata(videos)

        if LIMIT is not None:
            ids = ids[:LIMIT]
            print(f"Processing first {len(ids)} videos (LIMIT={LIMIT}).\n")

        total = len(ids)

        if total == 0:
            write_status("done", "Nema videa za obradu.", 100, None, True)
            print("\nDone.")
            return

        write_status(
            "running",
            "Videi su učitani. Obrada transkripata je u toku...",
            10,
            None,
            True,
        )

        for idx, vid in enumerate(ids, start=1):
            base_progress = int(((idx - 1) / total) * 80) + 10

            write_status(
                "running",
                f"Obrada videa",
                base_progress,
                None,
                True,
            )

            if yt_transcript_exists(vid):
                print(f"[{idx}] {vid}: YouTube transcript cached")
                continue

            if whisper_transcript_exists(vid):
                print(f"[{idx}] {vid}: Whisper transcript cached")
                continue

            write_status(
                "running",
                f"Preuzimanje transkripta",
                base_progress + 1,
                None,
                True,
            )

            jitter_sleep(7, 12)

            ok, status, err = try_download_transcript(vid)
            print(f"[{idx}] {vid}: transcript -> {status}")

            if status == "ip_blocked":
                msg = f"IP blocked detected while checking transcript for video {vid}."
                write_status("error", msg, base_progress + 1, err or "ip_blocked", True)
                print("\nIP blocked detected.")
                return

            if ok:
                continue

            if not audio_exists(vid):
                write_status(
                    "running",
                    f"Preuzimanje audio fajlova",
                    base_progress + 8,
                    None,
                    True,
                )

                jitter_sleep(4, 8)

                audio_ok, audio_err = download_audio(vid)
                if not audio_ok:
                    print(f"Audio failed for {vid}: {audio_err}")
                    continue
            else:
                print(f"[{idx}] {vid}: audio cached")

            write_status(
                "running",
                f"Whisper transkripcija za video {idx}/{total}",
                base_progress + 15,
                None,
                True,
            )

            print(f"[{idx}] {vid}: running Whisper ({WHISPER_MODEL})...")
            whisper_ok = transcribe_audio(vid, model_name=WHISPER_MODEL)

            if whisper_ok:
                write_status(
                    "running",
                    f"Whisper transcript sačuvan za video {idx}/{total}",
                    base_progress + 20,
                    None,
                    True,
                )
            else:
                print(f"Whisper failed for {vid}")
                write_status(
                    "running",
                    f"Whisper nije uspio za video {idx}/{total}: {vid}",
                    base_progress + 20,
                    None,
                    True,
                )

        write_status("done", "Obrada kanala završena.", 100, None, True)
        print("\nDone.")

    except Exception as e:
        write_status("error", "Greška tokom obrade kanala.", 100, str(e), False)
        raise


if __name__ == "__main__":
    main()