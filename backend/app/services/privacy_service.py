from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.connection import SessionLocal
from app.database.models import PrivacySetting
from app.schemas.privacy import PrivacyPolicy, PrivacyPolicyUpdate


class PrivacyService:
    def _get_or_create_record(self, db: Session) -> PrivacySetting:
        record = db.query(PrivacySetting).filter(PrivacySetting.id == 1).first()
        if not record:
            record = PrivacySetting(
                id=1,
                camera_enabled=settings.camera_enabled,
                microphone_enabled=settings.microphone_enabled,
                memory_enabled=settings.memory_enabled,
                local_ai_mode=settings.local_ai_mode,
                cloud_enabled=settings.cloud_fallback,
                retention_days=0,
                telemetry_enabled=False,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
        return record

    def get_policy(self, db: Session | None = None) -> PrivacyPolicy:
        if db is not None:
            record = self._get_or_create_record(db)
            return PrivacyPolicy.model_validate(record)

        with SessionLocal() as session:
            record = self._get_or_create_record(session)
            return PrivacyPolicy.model_validate(record)

    def update_policy(self, update: PrivacyPolicyUpdate, db: Session | None = None) -> PrivacyPolicy:
        data = update.model_dump(exclude_unset=True)

        def _apply(session: Session) -> PrivacyPolicy:
            record = self._get_or_create_record(session)
            for key, value in data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.commit()
            session.refresh(record)
            return PrivacyPolicy.model_validate(record)

        if db is not None:
            return _apply(db)

        with SessionLocal() as session:
            return _apply(session)

    def is_memory_enabled(self, db: Session | None = None) -> bool:
        return self.get_policy(db).memory_enabled

    def is_camera_enabled(self, db: Session | None = None) -> bool:
        return self.get_policy(db).camera_enabled

    def is_mic_enabled(self, db: Session | None = None) -> bool:
        return self.get_policy(db).microphone_enabled

    def is_cloud_enabled(self, db: Session | None = None) -> bool:
        return self.get_policy(db).cloud_enabled


privacy_service = PrivacyService()
