import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_document_chunks_file_id", "fileId"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    fileId: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("uploaded_files.id", ondelete="CASCADE"))
    chunkIndex: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    charCount: Mapped[int] = mapped_column(Integer)
    tokenEstimate: Mapped[int] = mapped_column(Integer)
    pageNumber: Mapped[int | None] = mapped_column(Integer)
    sectionTitle: Mapped[str | None] = mapped_column(String(500))
    chromaId: Mapped[str | None] = mapped_column(String(255), unique=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    file: Mapped["UploadedFile"] = relationship(back_populates="chunks")
