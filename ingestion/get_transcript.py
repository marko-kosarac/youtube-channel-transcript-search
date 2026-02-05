import json
import time
import random
from pathlib import Path
from typing import Literal, Tuple

from youtube_transcript_api import YouTubeTranscriptApi

SR_LANGS = ["sr", "sr-Latn", "sr-Cyrl"]

_NEXT_ALLOWED_TS = 0.0

def _polite_wait(min_s: float = 7.0, max_s: float = 12.0) -> None:
    global _NEXT_ALLOWED_TS
    now = time.time()
    if now < _NEXT_ALLOWED_TS:
        time.sleep(_NEXT_ALLOWED_TS - now)
    _NEXT_ALLOWED_TS = time.time() + random.uniform(min_s, max_s)

Status = Literal["saved", "cached", "no_transcript", "rate_limited", "ip_blocked", "error"]

def try_download_transcript(video_id: str) -> Tuple[bool, Status, str | None]:
    repo_root = Path(__file__).resolve().parents[1]
    out_dir = repo_root / "transcripts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{video_id}.json"

    if out_path.exists():
        return True, "cached", None

    api = YouTubeTranscriptApi()

    delay = 30.0

    for attempt in range(1, 6):
        try:
            _polite_wait(7, 12)

            fetched = api.fetch(video_id, languages=SR_LANGS)
            data = fetched.to_raw_data()

            out_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            print(f"✅ Transcript saved: {out_path.name}")
            return True, "saved", None

        except Exception as e:
            msg = str(e)
            msg_l = msg.lower()

            if "notranscriptfound" in msg_l or "no transcript" in msg_l:
                print(f"ℹ️ No transcript for {video_id}")
                return False, "no_transcript", msg

            if "429" in msg_l or "too many requests" in msg_l:
                sleep_s = delay + random.uniform(0, 5)
                print(f"⏳ 429 rate limit for {video_id}. Sleep {sleep_s:.1f}s (attempt {attempt}/5)")
                time.sleep(sleep_s)
                delay = min(delay * 2, 20 * 60)
                continue

            if "ipblocked" in msg_l or "requestblocked" in msg_l or "blocking requests from your ip" in msg_l:
                print(f"⛔ IP BLOCKED for {video_id}. Stop run and try later / change IP.")
                return False, "ip_blocked", msg

            print(f"⚠️ Transcript failed: {type(e).__name__}: {msg}")
            return False, "error", msg

    print("❌ Transcript retries exceeded.")
    return False, "rate_limited", "retries exceeded"
