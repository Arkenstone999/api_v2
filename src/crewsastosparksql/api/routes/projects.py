from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from crewsastosparksql.api.dependencies import get_db, get_current_user, check_rate_limit
from crewsastosparksql.api import db_models
from crewsastosparksql.api.services.project_service import ProjectService
from crewsastosparksql.api.services.task_service import TaskService
from crewsastosparksql.api.services.translation_service import TranslationService

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    description: str
    source_type: str
    target_type: str


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    progress: int | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    sourceType: str
    targetType: str
    progress: int
    fileCount: int
    dependencies: int
    createdAt: str
    updatedAt: str


def _to_response(project: db_models.Project) -> ProjectResponse:
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
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
    rate_limit: dict = Depends(check_rate_limit)
):
    try:
        project = ProjectService.create_project(
            db, current_user.id, project_data.name, project_data.description,
            project_data.source_type, project_data.target_type
        )
        return _to_response(project)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
    rate_limit: dict = Depends(check_rate_limit)
):
    projects = ProjectService.list_projects(db, current_user.id)
    return [_to_response(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
    rate_limit: dict = Depends(check_rate_limit)
):
    project = ProjectService.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _to_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    update_data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
    rate_limit: dict = Depends(check_rate_limit)
):
    project = ProjectService.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        project = ProjectService.update_project(
            db, project,
            name=update_data.name,
            description=update_data.description,
            status=update_data.status,
            progress=update_data.progress
        )
        return _to_response(project)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
    rate_limit: dict = Depends(check_rate_limit)
):
    project = ProjectService.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    ProjectService.delete_project(db, project)


@router.post("/{project_id}/files", status_code=202)
async def upload_project_files(
    project_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
    rate_limit: dict = Depends(check_rate_limit)
):
    project = ProjectService.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    for file in files:
        if not file.filename or not file.filename.endswith(".sas"):
            raise HTTPException(status_code=400, detail=f"Only .sas files accepted")

    tasks_created = 0
    for file in files:
        try:
            content = await file.read()
            sas_code = content.decode("utf-8")
            if not sas_code.strip():
                continue
            TaskService.create_task(db, project_id, file.filename, sas_code)
            tasks_created += 1
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail=f"File {file.filename} is not valid UTF-8")

    if tasks_created == 0:
        raise HTTPException(status_code=400, detail="No valid SAS files uploaded")

    ProjectService.update_file_count(db, project, tasks_created)
    return {"message": f"Uploaded {tasks_created} file(s)", "file_count": tasks_created}


@router.get("/{project_id}/tasks")
def list_project_tasks(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
    rate_limit: dict = Depends(check_rate_limit)
):
    project = ProjectService.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = TaskService.list_project_tasks(db, project_id)
    return [
        {
            "id": task.id,
            "file_name": task.file_name,
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
            "has_translation": bool(task.target_code)
        }
        for task in tasks
    ]


@router.post("/{project_id}/translate", status_code=202)
async def translate_project(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
    rate_limit: dict = Depends(check_rate_limit)
):
    project = ProjectService.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = TaskService.list_project_tasks(db, project_id)
    if not tasks:
        raise HTTPException(status_code=400, detail="No tasks to translate")

    ProjectService.update_project(db, project, status="converting", progress=0)

    task_ids = [task.id for task in tasks]
    background_tasks.add_task(_translate_all_tasks, project_id, task_ids)

    return {"message": "Translation started", "project_id": project_id, "status": "translating"}


def _translate_all_tasks(project_id: str, task_ids: List[str]):
    from pathlib import Path
    from datetime import datetime, timezone
    from crewsastosparksql.api.database import SessionLocal

    db = SessionLocal()
    try:
        tasks = [db.query(db_models.ConversionTask).filter(db_models.ConversionTask.id == tid).first() for tid in task_ids]
        tasks = [t for t in tasks if t is not None]

        output_dir = str(Path(__file__).parent.parent.parent.parent.parent)
        translation_service = TranslationService(output_dir)

        total = len(tasks)
        for idx, task in enumerate(tasks):
            try:
                TaskService.update_task(db, task, status="converting", started_at=datetime.now(timezone.utc))

                result = translation_service.translate(task.source_code, f"{project_id}_{task.id}")

                TaskService.update_task(
                    db, task,
                    status="converted",
                    target_code=result.code,
                    rationale=result.rationale,
                    completed_at=datetime.now(timezone.utc)
                )
            except Exception as e:
                TaskService.update_task(
                    db, task,
                    status="pending",
                    error_message=str(e),
                    completed_at=datetime.now(timezone.utc)
                )

            progress = int(((idx + 1) / total) * 100)
            project = db.query(db_models.Project).filter(db_models.Project.id == project_id).first()
            if project:
                ProjectService.update_project(db, project, progress=progress)

        project = db.query(db_models.Project).filter(db_models.Project.id == project_id).first()
        if project:
            ProjectService.update_project(db, project, status="completed", progress=100)
    finally:
        db.close()
