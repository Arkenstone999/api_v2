"""Job management and async execution."""
import os
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from crewsastosparksql.api.models import JobStatus
from crewsastosparksql.crew import Crewsastosparksql
from crewsastosparksql.main import ensure_task_dirs
from crewsastosparksql.validation import TaskValidator

logger = logging.getLogger(__name__)


class JobInfo:
    """Job state information."""
    def __init__(self, job_id: str, job_name: str, sas_file_name: str, sas_file_path: str):
        self.job_id = job_id
        self.job_name = job_name
        self.sas_file_name = sas_file_name
        self.sas_file_path = sas_file_path
        self.status = JobStatus.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.result: Optional[str] = None


class JobManager:
    """Manages job execution and state."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.jobs: Dict[str, JobInfo] = {}
        self.executor = ThreadPoolExecutor(max_workers=3)  # Limit concurrent jobs
        logger.info(f"JobManager initialized with output_dir: {output_dir}")

    def create_job(self, sas_file_path: str, job_name: str) -> str:
        """Create a new job and return job_id."""
        job_id = str(uuid.uuid4())
        sas_file_name = os.path.basename(sas_file_path)

        job_info = JobInfo(job_id, job_name, sas_file_name, sas_file_path)
        self.jobs[job_id] = job_info

        logger.info(f"Created job {job_id} for {job_name}")
        return job_id

    def get_job(self, job_id: str) -> Optional[JobInfo]:
        """Get job information by ID."""
        return self.jobs.get(job_id)

    def list_jobs(self) -> list[JobInfo]:
        """List all jobs, sorted by creation time."""
        return sorted(self.jobs.values(), key=lambda j: j.created_at, reverse=True)

    async def execute_job(self, job_id: str):
        """Execute a job asynchronously."""
        job = self.jobs.get(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = JobStatus.RUNNING
        job.started_at = datetime.now()
        logger.info(f"Starting job {job_id}: {job.job_name}")

        try:
            # Run crew execution in thread pool (CrewAI is synchronous)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._run_crew,
                job
            )

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            job.result = str(result)
            logger.info(f"Job {job_id} completed successfully")

        except Exception as e:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now()
            job.error_message = str(e)
            logger.exception(f"Job {job_id} failed: {e}")

    def _run_crew(self, job: JobInfo) -> str:
        """Execute the crew workflow (runs in thread pool)."""
        ensure_task_dirs(self.output_dir, job.job_name)

        inputs = {
            "sas_file_path": job.sas_file_path,
            "job_name": job.job_name,
            "current_year": str(datetime.now().year),
        }

        max_retries = 2
        result = None

        for attempt in range(max_retries):
            try:
                logger.info(f"Running crew for job {job.job_name} (attempt {attempt + 1}/{max_retries})")

                crew = Crewsastosparksql(output_dir=self.output_dir)
                result = crew.crew().kickoff(inputs=inputs)

                validator = TaskValidator(self.output_dir, job.job_name)
                validation_results = validator.validate_all()

                failed_tasks = [task for task, success in validation_results.items() if not success]

                if not failed_tasks:
                    logger.info(f"All tasks validated successfully for job {job.job_name}")
                    return str(result)

                logger.warning(f"Tasks failed validation: {failed_tasks}")

                if "translate_code" in failed_tasks:
                    logger.info("Attempting to fix translate_code file path issue")
                    if validator.fix_translate_code():
                        validation_results["translate_code"] = True
                        failed_tasks.remove("translate_code")

                if not failed_tasks:
                    logger.info(f"All tasks validated after fixes for job {job.job_name}")
                    return str(result)

                if attempt < max_retries - 1:
                    logger.warning(f"Retrying crew execution due to failed tasks: {failed_tasks}")
                else:
                    raise Exception(f"Tasks failed validation after all retries: {failed_tasks}")

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Crew execution failed (attempt {attempt + 1}): {e}")
                else:
                    raise

        return str(result) if result else "Crew execution completed with warnings"

    def get_job_results(self, job_id: str) -> Optional[Dict]:
        """Get job results including task outputs."""
        job = self.jobs.get(job_id)
        if not job:
            return None

        results = {
            "job_id": job.job_id,
            "status": job.status,
            "job_name": job.job_name,
            "tasks": {},
            "logs": None
        }

        if job.status != JobStatus.COMPLETED:
            return results

        # Read task outputs
        tasks_dir = Path(self.output_dir) / "jobs" / job.job_name / "tasks"
        if tasks_dir.exists():
            for task_dir in tasks_dir.iterdir():
                if task_dir.is_dir():
                    task_name = task_dir.name
                    results["tasks"][task_name] = {}

                    # Read all files in task directory
                    for file_path in task_dir.iterdir():
                        if file_path.is_file():
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    results["tasks"][task_name][file_path.name] = f.read()
                            except Exception as e:
                                logger.warning(f"Could not read {file_path}: {e}")

        # Read workflow log
        log_file = Path(self.output_dir) / "jobs" / job.job_name / "logs" / "workflow.log"
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    results["logs"] = f.read()
            except Exception as e:
                logger.warning(f"Could not read log file: {e}")

        return results
