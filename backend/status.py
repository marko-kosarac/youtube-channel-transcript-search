import json
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def status_file() -> Path:
    status_dir = project_root() / "data" / "status"
    status_dir.mkdir(parents=True, exist_ok=True)
    return status_dir / "current_status.json"


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


def read_status():
    path = status_file()

    if not path.exists():
        return {
            "status": "idle",
            "message": "Nije pokrenuto",
            "progress": 0,
            "error": None,
            "videos_ready": False,
        }

    try:
        data = json.loads(path.read_text(encoding="utf-8"))

        if "videos_ready" not in data:
            data["videos_ready"] = False

        return data
    except Exception:
        return {
            "status": "error",
            "message": "Status fajl je neispravan.",
            "progress": 100,
            "error": "Neuspjelo čitanje current_status.json fajla.",
            "videos_ready": False,
        }