from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    file_refs: Mapped[list[FileRef]] = relationship(back_populates="user", cascade="all, delete-orphan")


class StoredFile(Base):
    """
    物理文件（按 sha256 唯一）——真正落盘的二进制只存一份。
    """
    __tablename__ = "stored_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    refs: Mapped[list[FileRef]] = relationship(back_populates="stored_file", cascade="all, delete-orphan")


class FileRef(Base):
    """
    用户对文件的“引用/拥有关系”。
    同一个用户重复上传同一个 sha 的文件，只会有一条引用记录（或直接返回已有记录）。
    """
    __tablename__ = "file_refs"
    __table_args__ = (
        UniqueConstraint("user_id", "stored_file_id", name="uq_user_stored_file"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    stored_file_id: Mapped[int] = mapped_column(ForeignKey("stored_files.id", ondelete="CASCADE"), index=True, nullable=False)

    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="file_refs")
    stored_file: Mapped[StoredFile] = relationship(back_populates="refs")
