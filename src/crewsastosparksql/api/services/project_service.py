import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from crewsastosparksql.api import db_models


class ProjectService:
    @staticmethod
    def create_project(db: Session, user_id: str, name: str, description: str,
                      source_type: str, target_type: str) -> db_models.Project:
        project_id = str(uuid.uuid4())

        project = db_models.Project(
            id=project_id,
            user_id=user_id,
            name=name,
            description=description,
            source_type=db_models.SourceType(source_type),
            target_type=db_models.TargetType(target_type),
            status=db_models.ProjectStatus.READY,
            progress=0,
            file_count=0,
            dependencies_count=0
        )

        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def get_project(db: Session, project_id: str, user_id: str) -> Optional[db_models.Project]:
        return db.query(db_models.Project).filter(
            db_models.Project.id == project_id,
            db_models.Project.user_id == user_id
        ).first()

    @staticmethod
    def list_projects(db: Session, user_id: str) -> List[db_models.Project]:
        return db.query(db_models.Project).filter(
            db_models.Project.user_id == user_id
        ).order_by(db_models.Project.updated_at.desc()).all()

    @staticmethod
    def update_project(db: Session, project: db_models.Project,
                      name: Optional[str] = None,
                      description: Optional[str] = None,
                      status: Optional[str] = None,
                      progress: Optional[int] = None) -> db_models.Project:
        if name:
            project.name = name
        if description:
            project.description = description
        if status:
            project.status = db_models.ProjectStatus(status)
        if progress is not None:
            project.progress = max(0, min(100, progress))

        project.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def delete_project(db: Session, project: db_models.Project):
        db.delete(project)
        db.commit()

    @staticmethod
    def update_file_count(db: Session, project: db_models.Project, count: int):
        project.file_count = count
        db.commit()
