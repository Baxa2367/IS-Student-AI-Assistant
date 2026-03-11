from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    artifacts = relationship("Artifact", back_populates="project", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="project", cascade="all, delete-orphan")


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    module = Column(String(50), nullable=False)  # sql_lab | er_studio | normalization | code_explainer
    input_text = Column(Text, nullable=False, default="")
    output_text = Column(Text, nullable=False, default="")
    meta_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="artifacts")


class Run(Base):
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    sql_text = Column(Text, nullable=False, default="")
    status = Column(String(20), nullable=False, default="unknown")  # ok | error
    error_text = Column(Text, nullable=False, default="")
    result_json = Column(Text, nullable=False, default="{}")  # headers+rows
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="runs")