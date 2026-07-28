import os
import uuid

from config import TEMP_DIR

os.makedirs(TEMP_DIR, exist_ok=True)


def new_job_id() -> str:
    return uuid.uuid4().hex[:10]


def job_path(job_id: str, ext: str) -> str:
    return os.path.join(TEMP_DIR, f"{job_id}.{ext.lstrip('.')}")


def cleanup(*paths):
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except OSError:
            pass
