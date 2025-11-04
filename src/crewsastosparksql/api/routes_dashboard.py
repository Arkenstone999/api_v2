from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from crewsastosparksql.api.database import get_db
from crewsastosparksql.api import db_models
from crewsastosparksql.api.models import DashboardStats
from crewsastosparksql.api.auth import get_current_user
from crewsastosparksql.api.rate_limit import check_rate_limit

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db), current_user: db_models.User = Depends(get_current_user),
                        rate_limit: dict = Depends(check_rate_limit)):
    active_projects = db.query(func.count(db_models.Project.id)).filter(
        db_models.Project.user_id == current_user.id,
        db_models.Project.status != db_models.ProjectStatus.COMPLETED
    ).scalar() or 0

    files_converted = db.query(func.count(db_models.ConversionTask.id)).join(db_models.Project).filter(
        db_models.Project.user_id == current_user.id
    ).scalar() or 0

    dependencies_mapped = db.query(func.sum(db_models.Project.dependencies_count)).filter(
        db_models.Project.user_id == current_user.id
    ).scalar() or 0

    return DashboardStats(
        active_projects=active_projects,
        files_converted=files_converted,
        dependencies_mapped=dependencies_mapped,
        avg_conversion_time="2.3h"
    )
