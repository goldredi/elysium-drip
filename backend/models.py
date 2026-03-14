import datetime
from sqlalchemy import String, DateTime, Boolean, Text, Integer, BigInteger, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), nullable=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=True, unique=True)
    telegram_username: Mapped[str] = mapped_column(String(64), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=True)
    access_code_used: Mapped[str] = mapped_column(String(64), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    can_create_languages: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
    last_seen: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    languages: Mapped[list["Language"]] = relationship(back_populates="creator", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_users_telegram_id", "telegram_id"),
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="sessions")


class Language(Base):
    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(primary_key=True)
    lang_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_data: Mapped[dict] = mapped_column(JSON)
    token_b64: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(8), default="ru")
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

    creator: Mapped["User"] = relationship(back_populates="languages")


class EncodeLog(Base):
    __tablename__ = "encode_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    language_id: Mapped[str] = mapped_column(String(64), nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    emoji_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(16), default="web")  # web | bot_inline | bot_dm
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )


class AccessKey(Base):
    __tablename__ = "access_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    used_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    used_by_username: Mapped[str] = mapped_column(String(128), nullable=True)
    used_by_telegram: Mapped[str] = mapped_column(String(64), nullable=True)
    used_by_ip: Mapped[str] = mapped_column(String(45), nullable=True)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
    used_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)
