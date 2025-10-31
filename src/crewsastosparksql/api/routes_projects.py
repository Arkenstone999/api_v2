"""Projects API routes."""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from crewsastosparksql.api.database import get_db
from crewsastosparksql.api import db_models
from crewsastosparksql.api.models import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    WorkflowStepResponse,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


def create_default_workflow_steps(db: Session, project_id: str):
    """Create default workflow steps for a new project."""
    steps = [
        {"name": "Upload & Analyze", "description": "SAS files uploaded and dependency analysis completed", "order": 1},
        {"name": "Dependency Mapping", "description": "Extracted and visualized code dependencies", "order": 2},
        {"name": "Code Translation", "description": "AI agents converting SAS code to target platform", "order": 3},
        {"name": "Validation & Testing", "description": "Run parity tests and validate output equivalence", "order": 4},
        {"name": "Team Review", "description": "Collaborative review and approval process", "order": 5},
        {"name": "Deployment", "description": "Deploy to target environment and monitor", "order": 6},
    ]

    for step in steps:
        db_step = db_models.WorkflowStep(
            id=str(uuid.uuid4()),
            project_id=project_id,
            name=step["name"],
            description=step["description"],
            status="pending",
            order=step["order"]
        )
        db.add(db_step)


def project_to_response(project: db_models.Project) -> ProjectResponse:
    """Convert database project to response model."""
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status.value,
        sourceType=project.source_type.value,
        targetType=project.target_type.value,
        progress=project.progress,
        fileCount=project.file_count,
        dependencies=project.dependencies_count,
        createdAt=project.created_at.isoformat(),
        updatedAt=project.updated_at.isoformat()
    )


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(project_data: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project."""
    project_id = str(uuid.uuid4())

    # Validate enums
    try:
        source_type = db_models.SourceType(project_data.source_type)
        target_type = db_models.TargetType(project_data.target_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid type: {str(e)}")

    # Create project
    db_project = db_models.Project(
        id=project_id,
        name=project_data.name,
        description=project_data.description,
        source_type=source_type,
        target_type=target_type,
        status=db_models.ProjectStatus.ANALYZING,
        progress=0,
        file_count=0,
        dependencies_count=0
    )

    db.add(db_project)

    # Create default workflow steps
    create_default_workflow_steps(db, project_id)

    db.commit()
    db.refresh(db_project)

    return project_to_response(db_project)


@router.get("", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    """List all projects."""
    projects = db.query(db_models.Project).order_by(db_models.Project.updated_at.desc()).all()
    return [project_to_response(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    """Get a specific project."""
    project = db.query(db_models.Project).filter(db_models.Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    return project_to_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, update_data: ProjectUpdate, db: Session = Depends(get_db)):
    """Update a project."""
    project = db.query(db_models.Project).filter(db_models.Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    # Update fields
    if update_data.name is not None:
        project.name = update_data.name
    if update_data.description is not None:
        project.description = update_data.description
    if update_data.status is not None:
        try:
            project.status = db_models.ProjectStatus(update_data.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {update_data.status}")
    if update_data.progress is not None:
        project.progress = max(0, min(100, update_data.progress))

    db.commit()
    db.refresh(project)

    return project_to_response(project)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Delete a project."""
    project = db.query(db_models.Project).filter(db_models.Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    db.delete(project)
    db.commit()


@router.post("/{project_id}/files", status_code=202)
async def upload_project_files(
    project_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload SAS files to a project."""
    project = db.query(db_models.Project).filter(db_models.Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    # Validate files
    for file in files:
        if not file.filename or not file.filename.endswith(".sas"):
            raise HTTPException(status_code=400, detail=f"Only .sas files are accepted: {file.filename}")

    # Create tasks for each file
    for file in files:
        content = await file.read()
        source_code = content.decode("utf-8")

        task_id = str(uuid.uuid4())
        db_task = db_models.ConversionTask(
            id=task_id,
            project_id=project_id,
            file_name=file.filename,
            source_code=source_code,
            target_code="",
            rationale="",
            status=db_models.TaskStatus.PENDING,
            version=1
        )
        db.add(db_task)

    # Update project file count
    project.file_count = len(files)
    project.status = db_models.ProjectStatus.READY

    db.commit()

    return {
        "message": f"Uploaded {len(files)} files to project {project_id}",
        "file_count": len(files)
    }


@router.get("/{project_id}/workflow", response_model=List[WorkflowStepResponse])
def get_project_workflow(project_id: str, db: Session = Depends(get_db)):
    """Get workflow steps for a project."""
    project = db.query(db_models.Project).filter(db_models.Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    steps = db.query(db_models.WorkflowStep).filter(
        db_models.WorkflowStep.project_id == project_id
    ).order_by(db_models.WorkflowStep.order).all()

    return steps


@router.patch("/{project_id}/workflow/{step_id}", response_model=WorkflowStepResponse)
def update_workflow_step(
    project_id: str,
    step_id: str,
    status: str,
    db: Session = Depends(get_db)
):
    """Update a workflow step status."""
    step = db.query(db_models.WorkflowStep).filter(
        db_models.WorkflowStep.id == step_id,
        db_models.WorkflowStep.project_id == project_id
    ).first()

    if not step:
        raise HTTPException(status_code=404, detail=f"Workflow step {step_id} not found")

    if status not in ["pending", "in-progress", "completed", "failed"]:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    step.status = status
    db.commit()
    db.refresh(step)

    return step
