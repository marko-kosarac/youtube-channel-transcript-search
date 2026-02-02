import json
from pathlib import Path
import sys

from youtube_transcript_api import YouTubeTranscriptApi


def main():
    # Pokretanje:
    # py ingestion\get_transcript.py VIDEO_ID
    if len(sys.argv) < 2:
        print("Usage: py ingestion\\get_transcript.py VIDEO_ID")
        return

    video_id = sys.argv[1].strip()

    # Root folder repoa = parent od "ingestion" foldera
    repo_root = Path(__file__).resolve().parents[1]
    transcripts_dir = repo_root / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    out_path = transcripts_dir / f"{video_id}.json"

    api = YouTubeTranscriptApi()

    # Prvo pokušaj srpski (razne varijante)
    preferred_languages = ["sr", "sr-Latn", "sr-Cyrl"]

    try:
        fetched = api.fetch(video_id, languages=preferred_languages)
        raw_data = fetched.to_raw_data()

        with out_path.open("w", encoding="utf-8") as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)

        print(f"✅ Saved Serbian transcript: {out_path}")
        return

    except Exception as e:
        print("⚠️ Serbian transcript not available (sr/sr-Latn/sr-Cyrl).")
        print(f"Details: {e}")
        print("\nIf you want, we can add a fallback to auto/other languages or Whisper.\n")


if __name__ == "__main__":
    main()
