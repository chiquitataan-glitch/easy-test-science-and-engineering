import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InviteCode(Base):
    __tablename__ = "invite_codes"
    __table_args__ = (
        Index("ix_invite_codes_created_by", "createdBy"),
        Index("ix_invite_codes_used_by", "usedBy"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(50), unique=True)
    status: Mapped[str] = mapped_column(String(50), default="unused")
    membershipType: Mapped[str] = mapped_column(String(50))
    createdBy: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    createdAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expireAt: Mapped[datetime] = mapped_column(DateTime)
    usedBy: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"))
    usedAt: Mapped[datetime | None] = mapped_column(DateTime)

    creator: Mapped["User"] = relationship(back_populates="createdInviteCodes", foreign_keys=[createdBy])
    user: Mapped["User | None"] = relationship(back_populates="usedInviteCodes", foreign_keys=[usedBy])
