import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Float, Integer, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import PaperStatus, ClientType


class GeneratedPaper(Base):
    __tablename__ = "generated_papers"
    __table_args__ = (
        Index("ix_generated_papers_user_id", "userId"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    userId: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    documentIds: Mapped[dict] = mapped_column(JSON)
    courseName: Mapped[str] = mapped_column(String(500))
    paperTitle: Mapped[str | None] = mapped_column(String(500))
    paperJson: Mapped[dict] = mapped_column(JSON)
    rawResponse: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100))
    sourceChunks: Mapped[dict | None] = mapped_column(JSON)
    durationSeconds: Mapped[float | None] = mapped_column(Float)
    failReason: Mapped[str | None] = mapped_column(Text)
    config: Mapped[dict | None] = mapped_column(JSON)
    qualityReport: Mapped[dict | None] = mapped_column(JSON)
    knowledgeSummary: Mapped[dict | None] = mapped_column(JSON)
    promptVersion: Mapped[str | None] = mapped_column(String(50))
    modelName: Mapped[str | None] = mapped_column(String(100))
    tokenUsage: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[PaperStatus] = mapped_column(String(50), default=PaperStatus.pending)
    clientType: Mapped[ClientType] = mapped_column(String(50), default=ClientType.web)
    originalPaperId: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("generated_papers.id"))
    createdAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="generatedPapers")
    paperQuestions: Mapped[list["PaperQuestion"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    generationLogs: Mapped[list["GenerationLog"]] = relationship(back_populates="paper")
    originalPaper: Mapped["GeneratedPaper | None"] = relationship(remote_side=[id], back_populates="regenerations")
    regenerations: Mapped[list["GeneratedPaper"]] = relationship(back_populates="originalPaper")
