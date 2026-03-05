from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import subprocess
import sys
from pathlib import Path

from backend.jobs import JOBS, new_job, update_job, run_in_thread

app = FastAPI(title="YT Transcript Search Backend")

# Angular dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------
# Health
# -------------------------
@app.get("/health")
def health():
    return {"ok": True, "message": "Backend is running"}


# -------------------------
# Prepare (run pipeline)
# -------------------------
class PrepareRequest(BaseModel):
    channel: str


@app.post("/prepare")
def prepare(req: PrepareRequest):
    job_id = new_job(message=f'Preparing channel: {req.channel}')
    update_job(job_id, status="running", progress=1)

    def worker():
        try:
            update_job(job_id, message="Starting pipeline...", progress=5)

            # project root = parent of /backend
            root = Path(__file__).resolve().parents[1]
            pipeline_path = root / "src" / "ingestion" / "pipeline.py"

            # run: python src/ingestion/pipeline.py "<channel_url>"
            proc = subprocess.run(
                [sys.executable, str(pipeline_path), req.channel],
                capture_output=True,
                text=True,
            )

            if proc.returncode != 0:
                # show stderr (and stdout if stderr empty)
                err = (proc.stderr or "").strip() or (proc.stdout or "").strip()
                update_job(
                    job_id,
                    status="error",
                    message="Pipeline failed",
                    error=err,
                    progress=100,
                )
                return

            update_job(
                job_id,
                status="done",
                message="Channel processing finished",
                progress=100,
            )

        except Exception as e:
            update_job(
                job_id,
                status="error",
                message="Exception during pipeline",
                error=str(e),
                progress=100,
            )

    run_in_thread(worker)
    return {"job_id": job_id}


@app.get("/status/{job_id}")
def status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return {"error": "job not found"}
    return {
        "job_id": job_id,
        "status": job.status,
        "message": job.message,
        "progress": job.progress,
        "error": job.error,
    }