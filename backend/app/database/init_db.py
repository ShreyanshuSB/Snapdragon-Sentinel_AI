from __future__ import annotations

import logging
from pathlib import Path
from alembic import command
from alembic.config import Config

from app.database.connection import Base, engine
from app.database.models import (
    Attachment,
    Conversation,
    ConversationMessage,
    Memory,
    PrivacySetting,
    Project,
)

logger = logging.getLogger("sentinel.database")


def init_db() -> None:
    """Run Alembic migrations to head, with fallback to metadata.create_all."""
    try:
        backend_dir = Path(__file__).resolve().parent.parent.parent
        ini_path = backend_dir / "alembic.ini"
        if ini_path.exists():
            alembic_cfg = Config(str(ini_path))
            alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
            command.upgrade(alembic_cfg, "head")
            logger.info("Alembic migrations applied successfully.")
            return
    except Exception as e:
        logger.warning(f"Alembic auto-migration failed ({e}), falling back to Base.metadata.create_all.")

    Base.metadata.create_all(bind=engine)


__all__ = [
    "init_db",
    "Memory",
    "Project",
    "Attachment",
    "Conversation",
    "ConversationMessage",
    "PrivacySetting",
]
