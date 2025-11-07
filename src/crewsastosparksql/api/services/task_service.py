import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from crewsastosparksql.api import db_models


class TaskService:
    @staticmethod
    def create_task(db: Session, project_id: str, file_name: str, source_code: str) -> db_models.ConversionTask:
        task_id = str(uuid.uuid4())

        task = db_models.ConversionTask(
            id=task_id,
            project_id=project_id,
            file_name=file_name,
            source_code=source_code,
            target_code="",
            rationale="",
            status=db_models.TaskStatus.PENDING,
            version=1
        )

        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def get_task(db: Session, task_id: str) -> Optional[db_models.ConversionTask]:
        return db.query(db_models.ConversionTask).filter(
            db_models.ConversionTask.id == task_id
        ).first()

    @staticmethod
    def list_project_tasks(db: Session, project_id: str) -> List[db_models.ConversionTask]:
        return db.query(db_models.ConversionTask).filter(
            db_models.ConversionTask.project_id == project_id
        ).order_by(db_models.ConversionTask.created_at).all()

    @staticmethod
    def update_task(db: Session, task: db_models.ConversionTask,
                   status: Optional[str] = None,
                   target_code: Optional[str] = None,
                   rationale: Optional[str] = None,
                   started_at: Optional[datetime] = None,
                   completed_at: Optional[datetime] = None,
                   error_message: Optional[str] = None) -> db_models.ConversionTask:
        if status:
            task.status = db_models.TaskStatus(status)
        if target_code is not None:
            task.target_code = target_code
            task.version += 1
        if rationale is not None:
            task.rationale = rationale
        if started_at:
            task.started_at = started_at
        if completed_at:
            task.completed_at = completed_at
        if error_message is not None:
            task.error_message = error_message

        task.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def create_comment(db: Session, task_id: str, author: str, content: str,
                      line_number: Optional[int] = None) -> db_models.Comment:
        comment_id = str(uuid.uuid4())

        comment = db_models.Comment(
            id=comment_id,
            task_id=task_id,
            author=author,
            content=content,
            line_number=line_number,
            resolved=False
        )

        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment

    @staticmethod
    def get_task_comments(db: Session, task_id: str) -> List[db_models.Comment]:
        return db.query(db_models.Comment).filter(
            db_models.Comment.task_id == task_id
        ).order_by(db_models.Comment.created_at).all()

    @staticmethod
    def update_comment(db: Session, comment: db_models.Comment, resolved: bool) -> db_models.Comment:
        comment.resolved = resolved
        db.commit()
        db.refresh(comment)
        return comment
