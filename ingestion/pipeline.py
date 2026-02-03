from pathlib import Path

from fetch_videos import fetch_video_ids
from download_captions import try_download_transcript_via_ytdlp, polite_pause
from download_audio import download_audio_if_needed


LIMIT = 30  # test


def transcript_exists(video_id: str) -> bool:
    repo_root = Path(__file__).resolve().parents[1]
    return (repo_root / "transcripts" / f"{video_id}.json").exists()


def audio_exists(video_id: str) -> bool:
    repo_root = Path(__file__).resolve().parents[1]
    return (repo_root / "audio" / f"{video_id}.mp3").exists()


def main():
    video_ids = fetch_video_ids()
    print(f"Found {len(video_ids)} video IDs.")
    video_ids = video_ids[:LIMIT]
    print(f"Processing first {len(video_ids)} videos for testing.\n")

    skipped_transcript = 0
    downloaded_transcript = 0
    skipped_audio = 0
    downloaded_audio = 0

    for vid in video_ids:
        # 1) Ako već imamo transkript fajl -> preskoči sve
        if transcript_exists(vid):
            skipped_transcript += 1
            polite_pause()
            continue

        # 2) Pokušaj transkript preko yt-dlp (original govor)
        ok = try_download_transcript_via_ytdlp(vid, debug=True)
        if ok:
            downloaded_transcript += 1
            polite_pause()
            continue

        # 3) Nema transkripta -> skini audio, ali samo ako već ne postoji
        if audio_exists(vid):
            skipped_audio += 1
            polite_pause()
            continue

        audio_ok, err = download_audio_if_needed(vid)
        if audio_ok:
            downloaded_audio += 1
        else:
            print(f"❌ Audio download failed for {vid}: {err}")

        polite_pause()

    print("\n✅ Pipeline finished.")
    print(f"Transcripts: downloaded={downloaded_transcript}, skipped(existing)={skipped_transcript}")
    print(f"Audio: downloaded={downloaded_audio}, skipped(existing)={skipped_audio}")


if __name__ == "__main__":
    main()
