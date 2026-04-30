from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    session_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_access: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    random_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notice_subscription: Mapped["NoticeSubscription | None"] = relationship(
        "NoticeSubscription",
        back_populates="account",
        uselist=False,
        cascade="all, delete-orphan",
    )


class NoticeSubscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = {"schema": "notice"}

    aid: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    subscription: Mapped[str] = mapped_column(Text, nullable=False)

    account: Mapped[Account] = relationship("Account", back_populates="notice_subscription")
