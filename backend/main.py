from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.jobs import JOBS, new_job, update_job, run_in_thread
import time

app = FastAPI(title="YT Transcript Search Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True, "message": "Backend is running"}


class PrepareRequest(BaseModel):
    channel: str

@app.post("/prepare")
def prepare(req: PrepareRequest):
    job_id = new_job(message=f'Preparing channel: {req.channel}')
    update_job(job_id, status="running", progress=1)

    def worker():
        try:
            for i in range(1, 11):
                time.sleep(1)
                update_job(job_id, message=f"Working... {i}/10", progress=i * 10)
            update_job(job_id, status="done", message="Done", progress=100)
        except Exception as e:
            update_job(job_id, status="error", message="Error", error=str(e), progress=100)

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