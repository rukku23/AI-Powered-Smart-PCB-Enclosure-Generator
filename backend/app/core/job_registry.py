"""
EnclosureAI — Job Registry
In-memory job tracking with concurrency control and stale job cleanup.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("enclosureai.core.job_registry")

MAX_CONCURRENT_JOBS = 3


@dataclass
class JobStatus:
    """Status record for a generation job."""
    job_id: str
    status: str = "pending"   # pending | running | complete | error
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    attempt: int = 0
    error: Optional[str] = None
    stl_path: Optional[str] = None
    job_data: dict = field(default_factory=dict)

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
        self.updated_at = time.time()


class JobRegistry:
    """
    In-memory job registry with concurrency semaphore.
    Thread-safe for asyncio coroutines.
    """

    def __init__(self, max_concurrent: int = MAX_CONCURRENT_JOBS):
        self._jobs: dict[str, JobStatus] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._lock = asyncio.Lock()

    async def register(self, job_id: str) -> JobStatus:
        """Register a new job."""
        async with self._lock:
            status = JobStatus(job_id=job_id)
            self._jobs[job_id] = status
            logger.info(f"Job registered: {job_id}")
            return status

    async def update(self, job_id: str, **kwargs) -> None:
        """Update job status fields."""
        async with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(**kwargs)

    def get(self, job_id: str) -> Optional[JobStatus]:
        """Get job status (sync-safe read)."""
        return self._jobs.get(job_id)

    async def acquire(self) -> None:
        """Acquire a concurrency slot."""
        await self._semaphore.acquire()

    def release(self) -> None:
        """Release a concurrency slot."""
        self._semaphore.release()

    async def cleanup_old_jobs(self, max_age_hours: int = 2) -> int:
        """Remove jobs older than max_age_hours. Returns count removed."""
        cutoff = time.time() - (max_age_hours * 3600)
        removed = 0
        async with self._lock:
            stale = [jid for jid, js in self._jobs.items() if js.created_at < cutoff]
            for jid in stale:
                del self._jobs[jid]
                removed += 1
        if removed:
            logger.info(f"Cleaned up {removed} stale jobs")
        return removed

    @property
    def active_count(self) -> int:
        return sum(1 for j in self._jobs.values() if j.status == "running")

    @property
    def total_count(self) -> int:
        return len(self._jobs)

    def to_dict(self, job_id: str) -> Optional[dict]:
        """Serialize job status to dict for API response."""
        js = self._jobs.get(job_id)
        if not js:
            return None
        return {
            "job_id": js.job_id,
            "status": js.status,
            "attempt": js.attempt,
            "error": js.error,
            "stl_path": js.stl_path,
            "created_at": js.created_at,
            "updated_at": js.updated_at,
        }


# Global singleton
job_registry = JobRegistry()
