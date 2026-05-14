import uuid

from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PaperQuestion(Base):
    __tablename__ = "paper_questions"
    __table_args__ = (
        Index("ix_paper_questions_paper_id", "paperId"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    paperId: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("generated_papers.id", ondelete="CASCADE"))
    questionNo: Mapped[int] = mapped_column(Integer)
    questionType: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    options: Mapped[dict | None] = mapped_column(JSON)
    answer: Mapped[str] = mapped_column(Text)
    analysis: Mapped[str | None] = mapped_column(Text)
    knowledgePoints: Mapped[dict | None] = mapped_column(JSON)
    difficulty: Mapped[str | None] = mapped_column(String(20))
    score: Mapped[float | None] = mapped_column(Float)
    sourceChunkIds: Mapped[dict | None] = mapped_column(JSON)
    isCrossDoc: Mapped[bool] = mapped_column(Boolean, default=False)

    paper: Mapped["GeneratedPaper"] = relationship(back_populates="paperQuestions")
