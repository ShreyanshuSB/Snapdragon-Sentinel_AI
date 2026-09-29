from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.models import Memory, Project
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate


class ProjectService:
    def list_projects(self, db: Session) -> list[ProjectRead]:
        projects = db.query(Project).order_by(Project.name.asc()).all()
        result = []
        for p in projects:
            count = db.query(func.count(Memory.id)).filter(Memory.project_id == p.id).scalar() or 0
            result.append(
                ProjectRead(
                    id=p.id,
                    name=p.name,
                    description=p.description,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                    memory_count=count,
                )
            )
        return result

    def create_project(self, db: Session, payload: ProjectCreate) -> ProjectRead:
        existing = db.query(Project).filter(Project.name.ilike(payload.name.strip())).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project '{payload.name}' already exists.",
            )

        project = Project(name=payload.name.strip(), description=payload.description)
        db.add(project)
        db.commit()
        db.refresh(project)
        return ProjectRead(
            id=project.id,
            name=project.name,
            description=project.description,
            created_at=project.created_at,
            updated_at=project.updated_at,
            memory_count=0,
        )

    def delete_project(self, db: Session, project_id: int) -> dict[str, str]:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found.",
            )
        # Unlink memories from this project
        db.query(Memory).filter(Memory.project_id == project_id).update({"project_id": None})
        db.delete(project)
        db.commit()
        return {"status": "success", "message": f"Project '{project.name}' deleted."}


project_service = ProjectService()
