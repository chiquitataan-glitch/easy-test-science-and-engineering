import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Integer, ForeignKey, UniqueConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import IdentityProvider


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    displayName: Mapped[str | None] = mapped_column(String(255))
    avatarUrl: Mapped[str | None] = mapped_column(String(500))
    role: Mapped[str] = mapped_column(String(50), default="user")
    membershipType: Mapped[str] = mapped_column(String(50), default="free")
    membershipExpire: Mapped[datetime | None] = mapped_column(DateTime)
    inviteCodeUsed: Mapped[str | None] = mapped_column(String(50))
    remainingGenerations: Mapped[int] = mapped_column(Integer, default=20)
    quotaResetAt: Mapped[datetime | None] = mapped_column(DateTime)
    createdAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    identities: Mapped[list["UserIdentity"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    uploadedFiles: Mapped[list["UploadedFile"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    generatedPapers: Mapped[list["GeneratedPaper"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    generationLogs: Mapped[list["GenerationLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    createdInviteCodes: Mapped[list["InviteCode"]] = relationship(back_populates="creator", foreign_keys="InviteCode.createdBy", cascade="all, delete-orphan")
    usedInviteCodes: Mapped[list["InviteCode"]] = relationship(back_populates="user", foreign_keys="InviteCode.usedBy")


class UserIdentity(Base):
    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint("provider", "identifier"),
        Index("ix_user_identities_external_id", "externalId"),
        Index("ix_user_identities_openid", "openid"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    userId: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[IdentityProvider] = mapped_column(String(50))
    identifier: Mapped[str] = mapped_column(String(255))
    passwordHash: Mapped[str | None] = mapped_column(String(255))
    externalId: Mapped[str | None] = mapped_column(String(255))
    openid: Mapped[str | None] = mapped_column(String(255))
    unionid: Mapped[str | None] = mapped_column(String(255))
    createdAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="identities")
