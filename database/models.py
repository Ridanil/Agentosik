"""
Модели данных (не ORM — просто типизированные структуры поверх строк SQLite).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Source(BaseModel):
    id: Optional[int] = None
    telegram_id: Optional[int] = None
    username: str
    title: Optional[str] = None
    enabled: bool = True
    added_at: str
    last_message_id: int = 0
    last_scan_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "Source":
        return cls(
            id=row["id"],
            telegram_id=row["telegram_id"],
            username=row["username"],
            title=row["title"],
            enabled=bool(row["enabled"]),
            added_at=row["added_at"],
            last_message_id=row["last_message_id"] or 0,
            last_scan_at=row["last_scan_at"],
        )


class Message(BaseModel):
    id: Optional[int] = None
    source_id: int
    telegram_message_id: int
    message_date: Optional[str] = None
    author: Optional[str] = None
    text: Optional[str] = None
    message_url: Optional[str] = None
    media_type: Optional[str] = None
    collected_at: str

    @classmethod
    def from_row(cls, row) -> "Message":
        return cls(
            id=row["id"],
            source_id=row["source_id"],
            telegram_message_id=row["telegram_message_id"],
            message_date=row["message_date"],
            author=row["author"],
            text=row["text"],
            message_url=row["message_url"],
            media_type=row["media_type"],
            collected_at=row["collected_at"],
        )


class SearchRecord(BaseModel):
    id: Optional[int] = None
    query: str
    created_at: str
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class ResultRecord(BaseModel):
    id: Optional[int] = None
    search_id: int
    message_id: int
    relevance: float
    quote: str
    explanation: str
    created_at: datetime = Field(default_factory=datetime.now)



def now_iso() -> str:
    return datetime.utcnow().isoformat()
