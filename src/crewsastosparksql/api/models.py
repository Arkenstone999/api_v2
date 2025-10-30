"""Pydantic models for API requests and responses."""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobSubmitResponse(BaseModel):
    """Response after submitting a job."""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    message: str = Field(..., description="Human-readable message")


class JobStatusResponse(BaseModel):
    """Job status information."""
    job_id: str
    status: JobStatus
    job_name: str
    sas_file_name: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class JobResultsResponse(BaseModel):
    """Complete job results."""
    job_id: str
    status: JobStatus
    job_name: str
    tasks: Dict[str, Any] = Field(default_factory=dict, description="Task outputs by task name")
    logs: Optional[str] = None


class JobListItem(BaseModel):
    """Summary item for job listing."""
    job_id: str
    job_name: str
    status: JobStatus
    created_at: datetime
    completed_at: Optional[datetime] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
