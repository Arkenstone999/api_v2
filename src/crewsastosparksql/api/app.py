import os
import logging
from pathlib import Path
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from crewsastosparksql.api.models import JobSubmitResponse, JobStatusResponse, JobResultsResponse, JobListItem, JobStatus, ErrorResponse
from crewsastosparksql.api.job_manager import JobManager
from crewsastosparksql.api.database import init_db
from crewsastosparksql.api import routes_projects, routes_tasks, routes_dashboard, routes_auth

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="API, La v_3 !", description="Authentification et rate limiting !", version="0.1.0", docs_url="/docs", redoc_url="/redoc")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(routes_auth.router)
app.include_router(routes_projects.router)
app.include_router(routes_tasks.router)
app.include_router(routes_dashboard.router)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
UPLOAD_DIR = PROJECT_ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
job_manager = JobManager(output_dir=str(PROJECT_ROOT))


@app.on_event("startup")
async def startup_event():
    logger.info("Starting CrewSasToSparkSql API")
    logger.info(f"Project root: {PROJECT_ROOT}")
    logger.info(f"Upload directory: {UPLOAD_DIR}")
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")


@app.get("/")
async def root():
    return {"service": "CrewSasToSparkSql API", "version": "0.1.0", "status": "running", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/jobs", response_model=JobSubmitResponse, status_code=202)
async def submit_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="SAS file to translate")
):
    """
    Submit a SAS file for translation.

    The file will be processed asynchronously. Use the returned job_id to check status.
    """
    # Validate file extension
    if not file.filename or not file.filename.endswith(".sas"):
        raise HTTPException(
            status_code=400,
            detail="Only .sas files are accepted"
        )

    try:
        # Save uploaded file
        job_name = Path(file.filename).stem
        file_path = UPLOAD_DIR / file.filename

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info(f"Saved uploaded file: {file_path}")

        # Create job
        job_id = job_manager.create_job(str(file_path), job_name)

        # Start background execution
        background_tasks.add_task(job_manager.execute_job, job_id)

        return JobSubmitResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message=f"Job submitted successfully. Processing {file.filename}"
        )

    except Exception as e:
        logger.exception(f"Error submitting job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit job: {str(e)}")


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a specific job.
    """
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        job_name=job.job_name,
        sas_file_name=job.sas_file_name,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
    )


@app.get("/jobs/{job_id}/results", response_model=JobResultsResponse)
async def get_job_results(job_id: str):
    """
    Get the complete results of a completed job.

    Includes all task outputs, generated code, and logs.
    """
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status not in [JobStatus.COMPLETED, JobStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed. Current status: {job.status}"
        )

    results = job_manager.get_job_results(job_id)

    if not results:
        raise HTTPException(status_code=500, detail="Failed to retrieve job results")

    return JobResultsResponse(**results)


@app.get("/jobs", response_model=List[JobListItem])
async def list_jobs(status: JobStatus | None = None):
    """
    List all jobs, optionally filtered by status.
    """
    jobs = job_manager.list_jobs()

    # Filter by status if provided
    if status:
        jobs = [j for j in jobs if j.status == status]

    return [
        JobListItem(
            job_id=job.job_id,
            job_name=job.job_name,
            status=job.status,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
        for job in jobs
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
