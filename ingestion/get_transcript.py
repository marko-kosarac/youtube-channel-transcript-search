import json
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi


SR_LANGS = ["sr", "sr-Latn", "sr-Cyrl"]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _out_path(video_id: str) -> Path:
    transcripts_dir = _repo_root() / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    return transcripts_dir / f"{video_id}.json"


def _save_json(video_id: str, data: list) -> None:
    path = _out_path(video_id)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _is_locked_error(msg: str) -> bool:
    s = (msg or "").lower()
    keywords = [
        "members-only",
        "private",
        "unavailable",
        "this video is available to this channel's members",
        "join this channel to get access",
    ]
    return any(k in s for k in keywords)


def try_download_transcript(video_id: str, debug_print: bool = True) -> bool:
    """
    Pokušava da:
      1) utvrdi da li transcript postoji (list)
      2) preuzme srpski (manual -> auto)
      3) snimi transcripts/<video_id>.json

    Vraća True ako je transkript snimljen (ili već postoji fajl).
    Vraća False ako nema transkripta ili je video zaključan / blokiran / greška.
    """
    out = _out_path(video_id)

    # Ako već postoji -> preskoči
    if out.exists():
        if debug_print:
            print(f"✅ Transcript already exists: {out.name}")
        return True

    api = YouTubeTranscriptApi()

    try:
        # 1) LIST: ovo je ključni korak da ZNAŠ da li postoji transcript
        transcript_list = api.list(video_id)

        # (Opcionalno) debug ispis dostupnih jezika
        if debug_print:
            available = []
            for t in transcript_list:
                # t.language_code, t.is_generated, t.is_translatable
                kind = "auto" if t.is_generated else "manual"
                available.append(f"{t.language_code}:{kind}")
            print(f"📌 {video_id} transcripts available: {', '.join(available)}")

        # 2) Pokušaj srpski MANUAL
        transcript = None
        try:
            transcript = transcript_list.find_manually_created_transcript(SR_LANGS)
            if debug_print:
                print(f"✅ Using Serbian MANUAL transcript for {video_id}")
        except Exception:
            pass

        # 3) Ako nema manual, pokušaj srpski AUTO
        if transcript is None:
            try:
                transcript = transcript_list.find_generated_transcript(SR_LANGS)
                if debug_print:
                    print(f"✅ Using Serbian AUTO transcript for {video_id}")
            except Exception:
                pass

        # 4) Ako nema srpski uopšte
        if transcript is None:
            if debug_print:
                print(f"⚠️ Transcript exists but NOT in Serbian for {video_id} (will fallback to audio/Whisper).")
            return False

        # 5) Download segmenta: lista dict-ova sa text/start/duration
        data = transcript.fetch()
        _save_json(video_id, data)

        if debug_print:
            print(f"💾 Saved transcript: {out.name}")
        return True

    except Exception as e:
        # Ako list() ne uspije, to može biti:
        # - video zaključan (members-only/private)
        # - mrežni problem
        # - YouTube promijenio nešto
        msg = str(e)
        if _is_locked_error(msg):
            if debug_print:
                print(f"⛔ Locked/private video, cannot get transcript for {video_id}")
            return False

        if debug_print:
            print(f"⚠️ Transcript check failed for {video_id}: {type(e).__name__}")
        return False


# ručno testiranje:
# py ingestion\get_transcript.py VIDEO_ID
def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: py ingestion\\get_transcript.py VIDEO_ID")
        return
    try_download_transcript(sys.argv[1].strip(), debug_print=True)


if __name__ == "__main__":
    main()
