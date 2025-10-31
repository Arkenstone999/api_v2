"""Dashboard API routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from crewsastosparksql.api.database import get_db
from crewsastosparksql.api import db_models
from crewsastosparksql.api.models import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get aggregate statistics for the dashboard."""

    # Count active projects (not completed)
    active_projects = db.query(func.count(db_models.Project.id)).filter(
        db_models.Project.status != db_models.ProjectStatus.COMPLETED
    ).scalar() or 0

    # Count all tasks (files converted)
    files_converted = db.query(func.count(db_models.ConversionTask.id)).scalar() or 0

    # Sum dependencies from all projects
    dependencies_mapped = db.query(func.sum(db_models.Project.dependencies_count)).scalar() or 0

    # Simple average conversion time (placeholder)
    avg_conversion_time = "2.3h"

    return DashboardStats(
        active_projects=active_projects,
        files_converted=files_converted,
        dependencies_mapped=dependencies_mapped,
        avg_conversion_time=avg_conversion_time
    )
