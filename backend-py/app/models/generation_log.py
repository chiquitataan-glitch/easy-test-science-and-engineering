import uuid
from datetime import datetime

from sqlalchemy import String, Integer, ForeignKey, Index, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GenerationLog(Base):
    __tablename__ = "generation_logs"
    __table_args__ = (
        Index("ix_generation_logs_user_id", "userId"),
        Index("ix_generation_logs_paper_id", "paperId"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    userId: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    paperId: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("generated_papers.id", ondelete="SET NULL"))
    docIds: Mapped[dict] = mapped_column(JSON)
    questionCount: Mapped[int | None] = mapped_column(Integer)
    tokenUsed: Mapped[int | None] = mapped_column(Integer)
    durationMs: Mapped[int | None] = mapped_column(Integer)
    retrievalK: Mapped[int | None] = mapped_column(Integer)
    mode: Mapped[str] = mapped_column(String(50), default="rag")
    status: Mapped[str] = mapped_column(String(50))
    errorMessage: Mapped[str | None] = mapped_column(Text)
    createdAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="generationLogs")
    paper: Mapped["GeneratedPaper | None"] = relationship(back_populates="generationLogs")
