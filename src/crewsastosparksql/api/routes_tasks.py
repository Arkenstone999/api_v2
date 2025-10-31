"""Conversion tasks and comments API routes."""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from crewsastosparksql.api.database import get_db
from crewsastosparksql.api import db_models
from crewsastosparksql.api.models import (
    TaskResponse,
    TaskUpdate,
    CommentResponse,
    CommentCreate,
)

router = APIRouter(tags=["tasks"])


def task_to_response(task: db_models.ConversionTask, db: Session) -> TaskResponse:
    """Convert database task to response model."""
    # Get comments
    comments = db.query(db_models.Comment).filter(
        db_models.Comment.task_id == task.id
    ).all()

    comment_responses = [
        CommentResponse(
            id=c.id,
            author=c.author,
            content=c.content,
            timestamp=c.created_at.isoformat(),
            lineNumber=c.line_number,
            resolved=c.resolved
        )
        for c in comments
    ]

    return TaskResponse(
        id=task.id,
        projectId=task.project_id,
        fileName=task.file_name,
        sourceCode=task.source_code,
        targetCode=task.target_code,
        status=task.status.value,
        comments=comment_responses,
        version=task.version,
        rationale=task.rationale
    )


@router.get("/api/projects/{project_id}/tasks", response_model=List[TaskResponse])
def list_project_tasks(project_id: str, db: Session = Depends(get_db)):
    """List all conversion tasks for a project."""
    # Check project exists
    project = db.query(db_models.Project).filter(db_models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    tasks = db.query(db_models.ConversionTask).filter(
        db_models.ConversionTask.project_id == project_id
    ).order_by(db_models.ConversionTask.created_at).all()

    return [task_to_response(t, db) for t in tasks]


@router.get("/api/projects/{project_id}/tasks/{task_id}", response_model=TaskResponse)
def get_task(project_id: str, task_id: str, db: Session = Depends(get_db)):
    """Get a specific conversion task."""
    task = db.query(db_models.ConversionTask).filter(
        db_models.ConversionTask.id == task_id,
        db_models.ConversionTask.project_id == project_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return task_to_response(task, db)


@router.patch("/api/projects/{project_id}/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    project_id: str,
    task_id: str,
    update_data: TaskUpdate,
    db: Session = Depends(get_db)
):
    """Update a conversion task."""
    task = db.query(db_models.ConversionTask).filter(
        db_models.ConversionTask.id == task_id,
        db_models.ConversionTask.project_id == project_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Update fields
    if update_data.status is not None:
        try:
            task.status = db_models.TaskStatus(update_data.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {update_data.status}")

    if update_data.target_code is not None:
        task.target_code = update_data.target_code
        task.version += 1

    if update_data.rationale is not None:
        task.rationale = update_data.rationale

    db.commit()
    db.refresh(task)

    return task_to_response(task, db)


@router.post("/api/projects/{project_id}/tasks/{task_id}/regenerate", status_code=202)
def regenerate_task(project_id: str, task_id: str, db: Session = Depends(get_db)):
    """Regenerate/re-run conversion for a task."""
    task = db.query(db_models.ConversionTask).filter(
        db_models.ConversionTask.id == task_id,
        db_models.ConversionTask.project_id == project_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Set status back to pending to trigger re-conversion
    task.status = db_models.TaskStatus.PENDING
    task.target_code = ""
    task.rationale = ""

    db.commit()

    return {
        "message": f"Task {task_id} queued for regeneration",
        "task_id": task_id
    }


# ============================================================================
# Comments endpoints
# ============================================================================

@router.get("/api/tasks/{task_id}/comments", response_model=List[CommentResponse])
def get_task_comments(task_id: str, db: Session = Depends(get_db)):
    """Get all comments for a task."""
    # Check task exists
    task = db.query(db_models.ConversionTask).filter(db_models.ConversionTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    comments = db.query(db_models.Comment).filter(
        db_models.Comment.task_id == task_id
    ).order_by(db_models.Comment.created_at).all()

    return [
        CommentResponse(
            id=c.id,
            author=c.author,
            content=c.content,
            timestamp=c.created_at.isoformat(),
            lineNumber=c.line_number,
            resolved=c.resolved
        )
        for c in comments
    ]


@router.post("/api/tasks/{task_id}/comments", response_model=CommentResponse, status_code=201)
def create_comment(task_id: str, comment_data: CommentCreate, db: Session = Depends(get_db)):
    """Add a comment to a task."""
    # Check task exists
    task = db.query(db_models.ConversionTask).filter(db_models.ConversionTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    comment_id = str(uuid.uuid4())
    db_comment = db_models.Comment(
        id=comment_id,
        task_id=task_id,
        author=comment_data.author,
        content=comment_data.content,
        line_number=comment_data.line_number,
        resolved=False
    )

    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)

    return CommentResponse(
        id=db_comment.id,
        author=db_comment.author,
        content=db_comment.content,
        timestamp=db_comment.created_at.isoformat(),
        lineNumber=db_comment.line_number,
        resolved=db_comment.resolved
    )


@router.patch("/api/comments/{comment_id}", response_model=CommentResponse)
def update_comment(comment_id: str, resolved: bool, db: Session = Depends(get_db)):
    """Mark a comment as resolved or unresolved."""
    comment = db.query(db_models.Comment).filter(db_models.Comment.id == comment_id).first()

    if not comment:
        raise HTTPException(status_code=404, detail=f"Comment {comment_id} not found")

    comment.resolved = resolved
    db.commit()
    db.refresh(comment)

    return CommentResponse(
        id=comment.id,
        author=comment.author,
        content=comment.content,
        timestamp=comment.created_at.isoformat(),
        lineNumber=comment.line_number,
        resolved=comment.resolved
    )
