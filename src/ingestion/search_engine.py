import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List


# ================== Normalizacija ==================

_SR_MAP = str.maketrans({
    "č": "c", "ć": "c", "š": "s", "ž": "z", "đ": "d",
    "Č": "c", "Ć": "c", "Š": "s", "Ž": "z", "Đ": "d",
})

def normalize_sr(s: str) -> str:
    s = (s or "").translate(_SR_MAP).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s


# ================== Heuristički stem ==================

_SUFFIXES = [
    "ovima", "evima",
    "ama", "ima",
    "om", "em",
    "u", "a", "e", "i", "o",
]

def guess_sr_stem(word: str) -> str:
    w = normalize_sr(word).strip()
    if len(w) <= 4:
        return w
    for suf in _SUFFIXES:
        if w.endswith(suf) and len(w) > len(suf) + 2:
            return w[:-len(suf)]
    return w


# ================== Formatiranje vremena ==================

def format_mmss(seconds: float) -> str:
    sec = max(0, int(seconds))
    m = sec // 60
    s = sec % 60
    return f"{m:02d}:{s:02d}"


@dataclass
class Hit:
    video_id: str
    t: float
    mmss: str
    snippet: str
    url: str


# ================== Učitavanje ==================

def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def transcripts_dir() -> Path:
    return project_root() / "data" / "transcripts"


def iter_transcript_files() -> Iterable[Path]:
    d = transcripts_dir()
    if not d.exists():
        return []
    return sorted(d.glob("*.json"))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# ================== Pretraga ==================

def search_file(path: Path, query: str) -> List[Hit]:
    video_id = path.stem
    data = load_json(path)

    stem = guess_sr_stem(query)
    pattern = re.compile(re.escape(stem))

    hits: List[Hit] = []

    # YouTube transcript API format
    if isinstance(data, list):
        for item in data:
            text = item.get("text", "")
            start = float(item.get("start", 0.0))
            if pattern.search(normalize_sr(text)):
                hits.append(Hit(
                    video_id,
                    start,
                    format_mmss(start),
                    text.strip(),
                    f"https://www.youtube.com/watch?v={video_id}&t={int(start)}s"
                ))

    # Whisper format
    elif isinstance(data, dict) and "segments" in data:
        for seg in data["segments"]:
            text = seg.get("text", "")
            start = float(seg.get("start", 0.0))
            if pattern.search(normalize_sr(text)):
                hits.append(Hit(
                    video_id,
                    start,
                    format_mmss(start),
                    text.strip(),
                    f"https://www.youtube.com/watch?v={video_id}&t={int(start)}s"
                ))

    return hits


def search_all(query: str) -> List[Hit]:
    all_hits: List[Hit] = []
    for path in iter_transcript_files():
        all_hits.extend(search_file(path, query))
    return all_hits


# ================== CLI ==================

def main():
    if len(sys.argv) < 2:
        print('Usage: py ingestion\\search_transcripts.py "Knjiga"')
        sys.exit(1)

    query = sys.argv[1]

    hits = search_all(query)

    if not hits:
        print("No matches.")
        return

    hits.sort(key=lambda h: (h.video_id, h.t))

    print(f'Found {len(hits)} match(es) for "{query}":\n')
    for h in hits:
        print(f"- {h.video_id} @ {h.mmss} | {h.url}")
        print(f"  {h.snippet}\n")


if __name__ == "__main__":
    main()