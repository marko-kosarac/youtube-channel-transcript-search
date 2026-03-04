import threading
import uuid
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Job:
    status: str            # queued | running | done | error
    message: str
    progress: int          # 0-100
    error: Optional[str] = None


JOBS: Dict[str, Job] = {}


def new_job(message: str = "Queued") -> str:
    job_id = uuid.uuid4().hex
    JOBS[job_id] = Job(status="queued", message=message, progress=0)
    return job_id


def update_job(job_id: str, *, status: Optional[str] = None, message: Optional[str] = None,
               progress: Optional[int] = None, error: Optional[str] = None) -> None:
    job = JOBS[job_id]
    if status is not None:
        job.status = status
    if message is not None:
        job.message = message
    if progress is not None:
        job.progress = progress
    if error is not None:
        job.error = error


def run_in_thread(target, *args, **kwargs) -> threading.Thread:
    t = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t