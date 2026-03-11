from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, delete, update
from sqlalchemy.orm import sessionmaker

from db.models import Artifact, Project, Run
from utils.json_utils import safe_json_dumps


class Repository:
    """DB operations for projects, artifacts, and runs."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    # -------- Projects --------

    def list_projects(self) -> List[Project]:
        """Return all projects sorted by created_at desc."""
        with self.session_factory() as s:
            res = s.execute(select(Project).order_by(Project.created_at.desc()))
            return list(res.scalars().all())

    def create_project(self, name: str) -> Project:
        """Create a new project. If name exists, raises ValueError."""
        name = (name or "").strip()
        if not name:
            raise ValueError("Project name cannot be empty.")
        with self.session_factory() as s:
            existing = s.execute(select(Project).where(Project.name == name)).scalar_one_or_none()
            if existing:
                raise ValueError("Project with this name already exists.")
            p = Project(name=name)
            s.add(p)
            s.commit()
            s.refresh(p)
            return p

    def rename_project(self, project_id: int, new_name: str) -> None:
        """Rename project (unique by name)."""
        new_name = (new_name or "").strip()
        if not new_name:
            raise ValueError("New name cannot be empty.")
        with self.session_factory() as s:
            existing = s.execute(select(Project).where(Project.name == new_name)).scalar_one_or_none()
            if existing:
                raise ValueError("Project with this name already exists.")
            s.execute(update(Project).where(Project.id == project_id).values(name=new_name))
            s.commit()

    def delete_project(self, project_id: int) -> None:
        """Delete project and cascade delete artifacts/runs."""
        with self.session_factory() as s:
            s.execute(delete(Project).where(Project.id == project_id))
            s.commit()

    def get_project(self, project_id: int) -> Optional[Project]:
        """Get project by id."""
        with self.session_factory() as s:
            return s.execute(select(Project).where(Project.id == project_id)).scalar_one_or_none()

    # -------- Artifacts / Runs --------

    def add_artifact(self, project_id: int, module: str, input_text: str, output_text: str,
                     meta: Dict[str, Any] | None = None) -> Artifact:
        """Insert an artifact (saved interaction result)."""
        meta_json = safe_json_dumps(meta or {})
        with self.session_factory() as s:
            a = Artifact(
                project_id=project_id,
                module=module,
                input_text=input_text or "",
                output_text=output_text or "",
                meta_json=meta_json
            )
            s.add(a)
            s.commit()
            s.refresh(a)
            return a

    def list_artifacts(self, project_id: int, module: Optional[str] = None, limit: int = 200) -> List[Artifact]:
        """List artifacts for a project, optionally filtered by module."""
        with self.session_factory() as s:
            q = select(Artifact).where(Artifact.project_id == project_id).order_by(Artifact.created_at.desc())
            if module:
                q = q.where(Artifact.module == module)
            q = q.limit(limit)
            return list(s.execute(q).scalars().all())

    def add_run(self, project_id: int, sql_text: str, status: str,
                error_text: str = "", result: Dict[str, Any] | None = None) -> Run:
        """Insert a SQL run record."""
        result_json = safe_json_dumps(result or {})
        with self.session_factory() as s:
            r = Run(
                project_id=project_id,
                sql_text=sql_text or "",
                status=status,
                error_text=error_text or "",
                result_json=result_json
            )
            s.add(r)
            s.commit()
            s.refresh(r)
            return r

    def list_runs(self, project_id: int, limit: int = 200) -> List[Run]:
        """List SQL runs for a project."""
        with self.session_factory() as s:
            q = select(Run).where(Run.project_id == project_id).order_by(Run.created_at.desc()).limit(limit)
            return list(s.execute(q).scalars().all())