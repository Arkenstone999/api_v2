from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from crewsastosparksql.api.dependencies import get_db, get_current_user, check_rate_limit
from crewsastosparksql.api import db_models
from crewsastosparksql.api.services.task_service import TaskService
from crewsastosparksql.api.services.project_service import ProjectService
from crewsastosparksql.api.services.translation_service import TranslationService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskResponse(BaseModel):
    id: str
    projectId: str
    fileName: str
    sourceCode: str
    targetCode: str
    status: str
    version: int
    rationale: str
    comments: List["CommentResponse"] = []


class TaskUpdate(BaseModel):
    status: str | None = None
    target_code: str | None = None
    rationale: str | None = None


class CommentResponse(BaseModel):
    id: str
    author: str
    content: str
    timestamp: str
    lineNumber: int | None = None
    resolved: bool


class CommentCreate(BaseModel):
    author: str
    content: str
    line_number: int | None = None


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
    rate_limit: dict = Depends(check_rate_limit)
):
    task = TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    project = ProjectService.get_project(db, task.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    comments = TaskService.get_task_comments(db, task_id)
    return TaskResponse(
        id=task.id,
        projectId=task.project_id,
        fileName=task.file_name,
        sourceCode=task.source_code,
        targetCode=task.target_code,
        status=task.status.value,
        version=task.version,
        rationale=task.rationale,
        comments=[
            CommentResponse(
                id=c.id,
                author=c.author,
                content=c.content,
                timestamp=c.created_at.isoformat(),
                lineNumber=c.line_number,
                resolved=c.resolved
            ) for c in comments
        ]
    )


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    update_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
    rate_limit: dict = Depends(check_rate_limit)
):
    task = TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    project = ProjectService.get_project(db, task.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        task = TaskService.update_task(
            db, task,
            status=update_data.status,
            target_code=update_data.target_code,
            rationale=update_data.rationale
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    comments = TaskService.get_task_comments(db, task_id)
    return TaskResponse(
        id=task.id,
        projectId=task.project_id,
        fileName=task.file_name,
        sourceCode=task.source_code,
        targetCode=task.target_code,
        status=task.status.value,
        version=task.version,
        rationale=task.rationale,
        comments=[
            CommentResponse(
                id=c.id,
                author=c.author,
                content=c.content,
                timestamp=c.created_at.isoformat(),
                lineNumber=c.line_number,
                resolved=c.resolved
            ) for c in comments
        ]
    )


@router.post("/{task_id}/translate", status_code=202)
async def translate_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
    rate_limit: dict = Depends(check_rate_limit)
):
    task = TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    project = ProjectService.get_project(db, task.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    TaskService.update_task(db, task, status="converting")
    background_tasks.add_task(_translate_single_task, task_id, db)

    return {"message": "Translation started", "task_id": task_id}


def _translate_single_task(task_id: str, db: Session):
    from pathlib import Path
    from datetime import datetime, timezone

    task = TaskService.get_task(db, task_id)
    if not task:
        return

    output_dir = str(Path(__file__).parent.parent.parent.parent.parent)
    translation_service = TranslationService(output_dir)

    try:
        TaskService.update_task(db, task, started_at=datetime.now(timezone.utc))
        result = translation_service.translate(task.source_code, f"{task.project_id}_{task_id}")

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


@router.get("/{task_id}/comments", response_model=List[CommentResponse])
def get_task_comments(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
    rate_limit: dict = Depends(check_rate_limit)
):
    task = TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    project = ProjectService.get_project(db, task.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    comments = TaskService.get_task_comments(db, task_id)
    return [
        CommentResponse(
            id=c.id,
            author=c.author,
            content=c.content,
            timestamp=c.created_at.isoformat(),
            lineNumber=c.line_number,
            resolved=c.resolved
        ) for c in comments
    ]


@router.post("/{task_id}/comments", response_model=CommentResponse, status_code=201)
def create_comment(
    task_id: str,
    comment_data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
    rate_limit: dict = Depends(check_rate_limit)
):
    task = TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    project = ProjectService.get_project(db, task.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    comment = TaskService.create_comment(
        db, task_id, comment_data.author, comment_data.content, comment_data.line_number
    )

    return CommentResponse(
        id=comment.id,
        author=comment.author,
        content=comment.content,
        timestamp=comment.created_at.isoformat(),
        lineNumber=comment.line_number,
        resolved=comment.resolved
    )
