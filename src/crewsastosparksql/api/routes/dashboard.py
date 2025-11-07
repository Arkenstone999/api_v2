from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from crewsastosparksql.api.dependencies import get_db, get_current_user, check_rate_limit
from crewsastosparksql.api import db_models

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class DashboardStats(BaseModel):
    total_projects: int
    active_projects: int
    completed_projects: int
    total_tasks: int
    pending_tasks: int
    converted_tasks: int
    failed_tasks: int


class RecentActivity(BaseModel):
    project_id: str
    project_name: str
    task_id: str
    file_name: str
    status: str
    updated_at: str


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_activity: List[RecentActivity]


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
    rate_limit: dict = Depends(check_rate_limit)
):
    total_projects = db.query(func.count(db_models.Project.id)).filter(
        db_models.Project.user_id == current_user.id
    ).scalar() or 0

    active_projects = db.query(func.count(db_models.Project.id)).filter(
        db_models.Project.user_id == current_user.id,
        db_models.Project.status.in_([
            db_models.ProjectStatus.READY,
            db_models.ProjectStatus.CONVERTING
        ])
    ).scalar() or 0

    completed_projects = db.query(func.count(db_models.Project.id)).filter(
        db_models.Project.user_id == current_user.id,
        db_models.Project.status == db_models.ProjectStatus.COMPLETED
    ).scalar() or 0

    total_tasks = db.query(func.count(db_models.ConversionTask.id)).join(
        db_models.Project
    ).filter(
        db_models.Project.user_id == current_user.id
    ).scalar() or 0

    pending_tasks = db.query(func.count(db_models.ConversionTask.id)).join(
        db_models.Project
    ).filter(
        db_models.Project.user_id == current_user.id,
        db_models.ConversionTask.status == db_models.TaskStatus.PENDING
    ).scalar() or 0

    converted_tasks = db.query(func.count(db_models.ConversionTask.id)).join(
        db_models.Project
    ).filter(
        db_models.Project.user_id == current_user.id,
        db_models.ConversionTask.status.in_([
            db_models.TaskStatus.CONVERTED,
            db_models.TaskStatus.REVIEWED,
            db_models.TaskStatus.APPROVED
        ])
    ).scalar() or 0

    failed_tasks = total_tasks - pending_tasks - converted_tasks

    recent_tasks = db.query(db_models.ConversionTask).join(
        db_models.Project
    ).filter(
        db_models.Project.user_id == current_user.id
    ).order_by(
        db_models.ConversionTask.updated_at.desc()
    ).limit(10).all()

    recent_activity = []
    for task in recent_tasks:
        project = db.query(db_models.Project).filter(
            db_models.Project.id == task.project_id
        ).first()

        if project:
            recent_activity.append(RecentActivity(
                project_id=project.id,
                project_name=project.name,
                task_id=task.id,
                file_name=task.file_name,
                status=task.status.value,
                updated_at=task.updated_at.isoformat()
            ))

    return DashboardResponse(
        stats=DashboardStats(
            total_projects=total_projects,
            active_projects=active_projects,
            completed_projects=completed_projects,
            total_tasks=total_tasks,
            pending_tasks=pending_tasks,
            converted_tasks=converted_tasks,
            failed_tasks=failed_tasks
        ),
        recent_activity=recent_activity
    )
