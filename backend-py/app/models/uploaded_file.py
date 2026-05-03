import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Float, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import FileStatus, ClientType


class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    __table_args__ = (
        Index("ix_uploaded_files_user_id", "userId"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    userId: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    originalName: Mapped[str] = mapped_column(String(500))
    mimeType: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(Integer)
    path: Mapped[str] = mapped_column(String(1000))
    hash: Mapped[str | None] = mapped_column(String(255))
    storageProvider: Mapped[str] = mapped_column(String(50), default="local")
    storageKey: Mapped[str | None] = mapped_column(String(1000))
    parsedText: Mapped[str | None] = mapped_column(Text)
    parsedAt: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[FileStatus] = mapped_column(String(50), default=FileStatus.pending)
    clientType: Mapped[ClientType] = mapped_column(String(50), default=ClientType.web)
    category: Mapped[str | None] = mapped_column(String(100))
    categoryConfidence: Mapped[float | None] = mapped_column(Float)
    chunkCount: Mapped[int] = mapped_column(Integer, default=0)
    totalChars: Mapped[int] = mapped_column(Integer, default=0)
    errorMessage: Mapped[str | None] = mapped_column(Text)
    createdAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="uploadedFiles")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="file", cascade="all, delete-orphan")
