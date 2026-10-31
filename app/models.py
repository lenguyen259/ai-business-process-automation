from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ProcessInstance(Base):
    __tablename__ = "process_instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    process_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="draft")
    requester: Mapped[str] = mapped_column(String(128))
    payload_json: Mapped[str] = mapped_column(Text)
    ai_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_refs_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
