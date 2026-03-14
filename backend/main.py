from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import subprocess
import sys
import threading
from pathlib import Path
import json

app = FastAPI(title="YT Transcript Search Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def status_file() -> Path:
    path = project_root() / "data" / "status" / "current_status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def log_file() -> Path:
    path = project_root() / "data" / "status" / "pipeline.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_status(status: str, message: str, progress: int = 0, error: str | None = None):
    payload = {
        "status": status,
        "message": message,
        "progress": progress,
        "error": error,
    }
    status_file().write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


@app.get("/")
def root():
    return {"message": "Backend running"}


@app.get("/health")
def health():
    return {"ok": True, "message": "Backend is running"}


class PrepareRequest(BaseModel):
    channel: str


@app.post("/prepare")
def prepare(req: PrepareRequest):
    write_status("running", "Pokretanje pipeline-a...", 1)

    def worker():
        try:
            root = project_root()
            pipeline_path = root / "src" / "ingestion" / "pipeline.py"

            # log reset
            log_file().write_text("", encoding="utf-8")

            proc = subprocess.Popen(
                [sys.executable, str(pipeline_path), req.channel],
                cwd=str(root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = proc.communicate()

            # upiši log fajl
            log_file().write_text(
                f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}",
                encoding="utf-8"
            )

            if proc.returncode != 0:
                err = stderr.strip() or stdout.strip() or "Pipeline failed"
                write_status("error", "Pipeline nije uspio.", 100, err)
                return

            # Ako pipeline nije sam upisao done, backend neka ga zatvori
            current = json.loads(status_file().read_text(encoding="utf-8"))
            if current.get("status") == "running":
                write_status("done", "Obrada kanala završena.", 100)

        except Exception as e:
            write_status("error", "Greška pri pokretanju pipeline-a.", 100, str(e))

    threading.Thread(target=worker, daemon=True).start()
    return {"ok": True, "message": "Priprema kanala je pokrenuta"}


@app.get("/status")
def get_status():
    path = status_file()
    if not path.exists():
        return {
            "status": "idle",
            "message": "Nije pokrenuto",
            "progress": 0,
            "error": None,
        }

    return json.loads(path.read_text(encoding="utf-8"))

@app.get("/videos")
def get_videos():
    path = project_root() / "data" / "channel_videos" / "videos.json"

    if not path.exists():
        return []

    return json.loads(path.read_text(encoding="utf-8"))