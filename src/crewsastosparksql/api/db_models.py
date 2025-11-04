from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from crewsastosparksql.api.database import Base


class ProjectStatus(str, enum.Enum):
    ANALYZING = "analyzing"
    READY = "ready"
    CONVERTING = "converting"
    REVIEWING = "reviewing"
    COMPLETED = "completed"


class SourceType(str, enum.Enum):
    SAS_CODE = "sas-code"
    SAS_EG = "sas-eg"


class TargetType(str, enum.Enum):
    SQL = "sql"
    PYSPARK = "pyspark"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    CONVERTING = "converting"
    CONVERTED = "converted"
    REVIEWED = "reviewed"
    APPROVED = "approved"


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.ANALYZING, nullable=False)
    source_type = Column(SQLEnum(SourceType), nullable=False)
    target_type = Column(SQLEnum(TargetType), nullable=False)
    progress = Column(Integer, default=0)
    file_count = Column(Integer, default=0)
    dependencies_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owner = relationship("User", back_populates="projects")
    tasks = relationship("ConversionTask", back_populates="project", cascade="all, delete-orphan")
    workflow_steps = relationship("WorkflowStep", back_populates="project", cascade="all, delete-orphan")


class ConversionTask(Base):
    
    __tablename__ = "conversion_tasks"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    file_name = Column(String, nullable=False)
    source_code = Column(Text, nullable=False)
    target_code = Column(Text, default="")
    rationale = Column(Text, default="")
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="tasks")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")


class Comment(Base):
    
    __tablename__ = "comments"

    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("conversion_tasks.id"), nullable=False)
    author = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    line_number = Column(Integer, nullable=True)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    task = relationship("ConversionTask", back_populates="comments")


class WorkflowStep(Base):
    
    __tablename__ = "workflow_steps"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, in-progress, completed, failed
    order = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="workflow_steps")


class User(Base):
    
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    api_key = Column(String, unique=True, nullable=False, index=True)
    monthly_request_limit = Column(Integer, default=1000, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    usage_records = relationship("Usage", back_populates="user", cascade="all, delete-orphan")


class Usage(Base):
    
    __tablename__ = "usage"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    request_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="usage_records")
