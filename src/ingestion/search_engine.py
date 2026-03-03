import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


_SR_MAP = str.maketrans({
    "č": "c", "ć": "c", "š": "s", "ž": "z", "đ": "d",
    "Č": "c", "Ć": "c", "Š": "s", "Ž": "z", "Đ": "d",
})

def normalize_sr(s: str) -> str:
    s = (s or "").translate(_SR_MAP).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s


def format_mmss(seconds: float) -> str:
    sec = max(0, int(seconds))
    m = sec // 60
    s = sec % 60
    return f"{m:02d}:{s:02d}"

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
        if w.endswith(suf):
            stem = w[:-len(suf)]
            if len(stem) >= 4:
                return stem
            return w

    return w

_SUFFIX_GROUP = r"(a|e|u|i|o|om|em|ama|ima|ovima|evima)?"

def build_exact_pattern(query: str) -> re.Pattern:
    q = normalize_sr(query).strip()
    return re.compile(rf"\b{re.escape(q)}\b")

def build_forms_pattern(query: str) -> re.Pattern:
    stem = guess_sr_stem(query)
    return re.compile(rf"\b{re.escape(stem)}{_SUFFIX_GROUP}\b")


@dataclass
class Hit:
    video_id: str
    t: float
    mmss: str
    snippet: str
    url: str


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

def _search_youtube_list(video_id: str, items: List[Dict[str, Any]], pattern: re.Pattern) -> List[Hit]:
    hits: List[Hit] = []
    for it in items:
        text = it.get("text") or ""
        start = float(it.get("start") or 0.0)

        if pattern.search(normalize_sr(text)):
            hits.append(Hit(
                video_id=video_id,
                t=start,
                mmss=format_mmss(start),
                snippet=text.strip(),
                url=f"https://www.youtube.com/watch?v={video_id}&t={int(start)}s"
            ))
    return hits


def _search_whisper(video_id: str, payload: Dict[str, Any], pattern: re.Pattern) -> List[Hit]:
    hits: List[Hit] = []
    segments = payload.get("segments") or []

    for seg in segments:
        text = (seg.get("text") or "").strip()
        start = float(seg.get("start") or 0.0)

        if pattern.search(normalize_sr(text)):
            hits.append(Hit(
                video_id=video_id,
                t=start,
                mmss=format_mmss(start),
                snippet=text,
                url=f"https://www.youtube.com/watch?v={video_id}&t={int(start)}s"
            ))
    return hits


def search_file(path: Path, pattern: re.Pattern) -> List[Hit]:
    video_id = path.stem
    data = load_json(path)

    if isinstance(data, list):
        return _search_youtube_list(video_id, data, pattern)

    if isinstance(data, dict) and isinstance(data.get("segments"), list):
        return _search_whisper(video_id, data, pattern)

    return []


def search_all(pattern: re.Pattern) -> List[Hit]:
    hits: List[Hit] = []
    for p in iter_transcript_files():
        hits.extend(search_file(p, pattern))
    return hits


def search(query: str) -> Tuple[List[Hit], str]:
    exact_pat = build_exact_pattern(query)
    hits = search_all(exact_pat)
    if hits:
        return hits, "exact"

    forms_pat = build_forms_pattern(query)
    hits = search_all(forms_pat)
    return hits, "forms"

def save_results_to_json(hits: List[Hit], query: str, mode: str):
    root = project_root()
    results_dir = root / "data" / "search_results"
    results_dir.mkdir(parents=True, exist_ok=True)

    results_file = results_dir / "results.json"

    if results_file.exists():
        results_file.unlink()

    output = {
        "query": query,
        "mode": mode,
        "count": len(hits),
        "results": [
            {
                "video_id": h.video_id,
                "seconds": int(h.t),
                "timestamp": h.mmss,
                "url": h.url,
                "snippet": h.snippet
            }
            for h in hits
        ]
    }

    results_file.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"\n📁 Results saved to: {results_file}")


def main():
    query = sys.argv[1].strip()
    hits, mode = search(query)
    save_results_to_json(hits, query, mode)

    if not hits:
        print("No matches.")
        return

    hits.sort(key=lambda h: (h.video_id, h.t))

    print(f'Found {len(hits)} match(es) for "{query}":\n')
    for h in hits:
        print(f"- {h.video_id} @ {h.mmss} | {h.url}")
        sn = h.snippet.replace("\n", " ").strip()
        if len(sn) > 180:
            sn = sn[:180] + "..."
        print(f"  {sn}\n")


if __name__ == "__main__":
    main()