"""Pydantic models for API requests and responses."""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
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


# ============================================================================
# Project Models
# ============================================================================

class ProjectCreate(BaseModel):
    """Create project request."""
    name: str
    description: str
    source_type: str  # "sas-code" or "sas-eg"
    target_type: str  # "sql" or "pyspark"


class ProjectUpdate(BaseModel):
    """Update project request."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[int] = None


class ProjectResponse(BaseModel):
    """Project response."""
    id: str
    name: str
    description: str
    status: str
    source_type: str = Field(alias="sourceType")
    target_type: str = Field(alias="targetType")
    progress: int
    file_count: int = Field(alias="fileCount")
    dependencies: int
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")

    class Config:
        populate_by_name = True


# ============================================================================
# Conversion Task Models
# ============================================================================

class CommentResponse(BaseModel):
    """Comment response."""
    id: str
    author: str
    content: str
    timestamp: str
    line_number: Optional[int] = Field(None, alias="lineNumber")
    resolved: bool

    class Config:
        populate_by_name = True


class CommentCreate(BaseModel):
    """Create comment request."""
    author: str
    content: str
    line_number: Optional[int] = None


class TaskResponse(BaseModel):
    """Conversion task response."""
    id: str
    project_id: str = Field(alias="projectId")
    file_name: str = Field(alias="fileName")
    source_code: str = Field(alias="sourceCode")
    target_code: str = Field(alias="targetCode")
    status: str
    comments: List[CommentResponse] = []
    version: int
    rationale: str

    class Config:
        populate_by_name = True


class TaskUpdate(BaseModel):
    """Update task request."""
    status: Optional[str] = None
    target_code: Optional[str] = None
    rationale: Optional[str] = None


# ============================================================================
# Dashboard Models
# ============================================================================

class DashboardStats(BaseModel):
    """Dashboard statistics."""
    active_projects: int
    files_converted: int
    dependencies_mapped: int
    avg_conversion_time: str


# ============================================================================
# Workflow Models
# ============================================================================

class WorkflowStepResponse(BaseModel):
    """Workflow step response."""
    id: str
    name: str
    status: str
    description: str

    class Config:
        from_attributes = True
