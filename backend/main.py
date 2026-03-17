from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import subprocess
import sys
import threading
from pathlib import Path
import json

from backend.status import read_status, write_status


app = FastAPI(title="YT Transcript Search Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def log_file() -> Path:
    path = project_root() / "data" / "status" / "pipeline.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def search_results_file() -> Path:
    path = project_root() / "data" / "search_results" / "results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


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
    write_status("running", "Pokretanje...", 1)

    def worker():
        try:
            root = project_root()
            pipeline_path = root / "src" / "ingestion" / "pipeline.py"

            log_file().write_text("", encoding="utf-8")

            proc = subprocess.Popen(
                [sys.executable, str(pipeline_path), req.channel],
                cwd=str(root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = proc.communicate()

            log_file().write_text(
                f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}",
                encoding="utf-8"
            )

            if proc.returncode != 0:
                err = stderr.strip() or stdout.strip() or "Pipeline failed"
                write_status("error", "Pipeline nije uspeo.", 100, err)
                return

            current = read_status()
            if current.get("status") == "running":
                write_status("done", "Obrada kanala završena.", 100)

        except Exception as e:
            write_status("error", "Greška pri pokretanju pipeline-a.", 100, str(e))

    threading.Thread(target=worker, daemon=True).start()
    return {"ok": True, "message": "Priprema kanala je pokrenuta"}


@app.get("/status")
def get_status():
    return read_status()


@app.get("/videos")
def get_videos():
    path = project_root() / "data" / "channel_videos" / "videos.json"

    if not path.exists():
        return []

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


@app.get("/search")
def search(query: str = Query(..., min_length=1)):
    root = project_root()
    search_engine_path = root / "src" / "ingestion" / "search_engine.py"

    try:
        proc = subprocess.run(
            [sys.executable, str(search_engine_path), query],
            cwd=str(root),
            capture_output=True,
            text=True
        )

        if proc.returncode != 0:
            err = proc.stderr.strip() or proc.stdout.strip() or "Search failed"
            return {
                "ok": False,
                "message": "Pretraga nije uspela.",
                "error": err,
                "query": query,
                "count": 0,
                "results": []
            }

        results_path = search_results_file()

        if not results_path.exists():
            return {
                "ok": True,
                "message": "Nema rezultata.",
                "query": query,
                "count": 0,
                "results": []
            }

        data = json.loads(results_path.read_text(encoding="utf-8"))

        return {
            "ok": True,
            "message": "Pretraga završena.",
            "query": data.get("query", query),
            "mode": data.get("mode", "unknown"),
            "count": data.get("count", 0),
            "results": data.get("results", [])
        }

    except Exception as e:
        return {
            "ok": False,
            "message": "Greška pri pokretanju search engine-a.",
            "error": str(e),
            "query": query,
            "count": 0,
            "results": []
        }