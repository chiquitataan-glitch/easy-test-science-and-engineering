import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MembershipHistory(Base):
    __tablename__ = "membership_history"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    userId: Mapped[str] = mapped_column(UUID(as_uuid=False))
    changeType: Mapped[str] = mapped_column(String(50))
    membershipType: Mapped[str] = mapped_column(String(50))
    startDate: Mapped[datetime] = mapped_column(DateTime)
    endDate: Mapped[datetime | None] = mapped_column(DateTime)
    triggeredBy: Mapped[str] = mapped_column(String(50))
    inviteCodeId: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    createdAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
