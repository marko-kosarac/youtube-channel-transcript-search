import json
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


# Jezici koje tretiramo kao "transkript" (original) za naš region:
# sr-Latn je najčešći na balkanskim kanalima, ali dodajemo i sr/sr-Cyrl + fallback bs/hr
SUB_LANGS = "sr-Latn,sr,sr-Cyrl,bs,hr"

# Rate-limit retry
MAX_RETRIES_429 = 5
BASE_WAIT_SECONDS = 8  # osnovno čekanje za backoff

# Ako ti YouTube često blokira, možeš uključiti cookies iz browsera (ako si ulogovan)
USE_COOKIES_FROM_BROWSER = False
COOKIES_BROWSER = "chrome"  # "chrome" ili "edge" (kako ti odgovara)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _find_ffmpeg_location() -> str | None:
    """
    Vrati folder gdje je ffmpeg.exe (npr. C:\\...\\bin), ili None ako nije u PATH-u.
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        return None
    return str(Path(ffmpeg_path).parent)


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def _is_429(msg: str) -> bool:
    s = (msg or "").lower()
    return "http error 429" in s or "too many requests" in s


def _is_locked(msg: str) -> bool:
    s = (msg or "").lower()
    return any(k in s for k in [
        "members-only",
        "this video is available to this channel's members",
        "private video",
        "unavailable",
        "has been removed",
        "sign in to confirm",
        "join this channel to get access",
    ])


def _vtt_to_segments(vtt_text: str) -> list[dict]:
    """
    Minimal VTT parser -> [{"start": seconds, "duration": seconds, "text": "..."}]
    Dovoljno za MVP i kasniju pretragu.
    """
    lines = [l.strip("\ufeff") for l in vtt_text.splitlines()]
    segments = []
    i = 0

    def ts_to_sec(ts: str) -> float:
        parts = ts.replace(",", ".").split(":")
        if len(parts) == 3:
            h, m, s = parts
        else:
            h = "0"
            m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)

    time_re = re.compile(
        r"(\d{2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3})\s*-->\s*"
        r"(\d{2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3})"
    )

    while i < len(lines):
        m = time_re.search(lines[i])
        if not m:
            i += 1
            continue

        start = ts_to_sec(m.group(1))
        end = ts_to_sec(m.group(2))
        i += 1

        text_lines = []
        while i < len(lines) and lines[i] and not time_re.search(lines[i]):
            if not lines[i].startswith(("NOTE", "WEBVTT")):
                text_lines.append(lines[i])
            i += 1

        text = " ".join(text_lines).strip()
        if text:
            segments.append({"start": start, "duration": max(0.0, end - start), "text": text})

        i += 1

    return segments


def try_download_transcript_via_ytdlp(video_id: str, debug: bool = True) -> bool:
    """
    Pokušaj da preuzmeš "transkript" preko yt-dlp subtitle track-a (VTT),
    zatim ga pretvoriš u JSON segmente i snimiš u transcripts/<id>.json.
    Return True ako uspije ili ako već postoji fajl.
    """
    repo_root = _repo_root()
    transcripts_dir = repo_root / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    out_json = transcripts_dir / f"{video_id}.json"
    if out_json.exists():
        if debug:
            print(f"✅ Transcript already exists: {out_json.name}")
        return True

    ffmpeg_loc = _find_ffmpeg_location()
    if not ffmpeg_loc:
        if debug:
            print("❌ ffmpeg not visible in this terminal PATH. Restart terminal/VS Code.")
        return False

    url = f"https://www.youtube.com/watch?v={video_id}"

    base = [
        sys.executable, "-m", "yt_dlp",
        "--js-runtimes", "node",
        "--remote-components", "ejs:github",
        "--ffmpeg-location", ffmpeg_loc,
    ]

    if USE_COOKIES_FROM_BROWSER:
        base += ["--cookies-from-browser", COOKIES_BROWSER]

    # log fajlovi (da uvijek znaš šta se desilo)
    list_log = transcripts_dir / f"{video_id}.list-subs.txt"
    err_log = transcripts_dir / f"{video_id}.captions-error.txt"

    # 1) list-subs (nije obavezno, ali pomaže za dokaz i debug)
    list_cmd = base + ["--list-subs", "--skip-download", url]
    listed = _run(list_cmd)
    list_log.write_text((listed.stdout or "") + "\n\nSTDERR:\n" + (listed.stderr or ""), encoding="utf-8")

    # 2) download subs + auto-subs (original govor), bez prevoda
    dl_cmd = base + [
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", SUB_LANGS,
        "--sub-format", "vtt",
        "-o", str(transcripts_dir / "%(id)s.%(ext)s"),
        url,
    ]

    attempt = 1
    while True:
        res = _run(dl_cmd)

        if res.returncode == 0:
            break

        stderr = (res.stderr or "").strip()

        # members/private -> odmah preskoči
        if _is_locked(stderr):
            if debug:
                print(f"⛔ Skipped locked/private: {video_id}")
            return False

        # 429 -> retry sa backoff + jitter
        if _is_429(stderr) and attempt <= MAX_RETRIES_429:
            wait_s = min(300, (2 ** attempt) * BASE_WAIT_SECONDS) + random.randint(0, 10)
            if debug:
                print(f"⏳ 429 Too Many Requests for {video_id}. Waiting {wait_s}s then retry {attempt}/{MAX_RETRIES_429}...")
            time.sleep(wait_s)
            attempt += 1
            continue

        # ostale greške -> snimi log i odustani
        err_log.write_text((res.stdout or "") + "\n\nSTDERR:\n" + (res.stderr or ""), encoding="utf-8")
        if debug:
            print(f"⚠️ yt-dlp captions failed for {video_id} (see {err_log.name})")
        return False

    # 3) Nađi bilo koji VTT skinut za ovaj video
    candidates = sorted(transcripts_dir.glob(f"{video_id}.*.vtt"))

    if not candidates:
        # nema titlova u traženim jezicima
        if debug:
            print(f"⚠️ No VTT subtitles downloaded for {video_id} (see {list_log.name})")
        return False

    # Odabir: preferiraj sr-Latn, pa sr, pa sr-Cyrl, pa bs/hr
    preferred_order = ["sr-Latn", "sr", "sr-Cyrl", "bs", "hr"]
    chosen = None
    for lang in preferred_order:
        for p in candidates:
            if f".{lang}.vtt" in p.name:
                chosen = p
                break
        if chosen:
            break
    if not chosen:
        chosen = candidates[0]

    vtt_text = chosen.read_text(encoding="utf-8", errors="ignore")
    segments = _vtt_to_segments(vtt_text)
    out_json.write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")

    # očisti vtt fajlove (da ostane samo json)
    for p in candidates:
        try:
            p.unlink()
        except Exception:
            pass

    if debug:
        print(f"✅ Transcript saved: {out_json.name} (source: {chosen.name})")
    return True


def polite_pause(min_s: float = 3.0, max_s: float = 8.0) -> None:
    """
    Pauza između videa da smanji 429.
    """
    time.sleep(random.uniform(min_s, max_s))
