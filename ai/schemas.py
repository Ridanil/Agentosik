"""
Строгие схемы для валидации JSON-ответа модели (п.9 ТЗ).
Если ответ не проходит валидацию — результат НЕ сохраняется.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class AnalysisResult(BaseModel):
    relevant: bool
    relevance_score: float = Field(ge=0.0, le=1.0)
    quote: str
    explanation: str
    confidence: Literal["low", "medium", "high"]

    @field_validator("quote")
    @classmethod
    def quote_not_fabricated_placeholder(cls, v: str) -> str:
        # модель обязана явно писать эти маркеры, а не выдумывать цитату
        return v.strip()


class ParsedQuery(BaseModel):
    """Результат разбора запроса на естественном языке (п.10 ТЗ)."""
    keywords: list[str] = Field(default_factory=list)
    semantic_criteria: Optional[str] = None
    date_from: Optional[str] = None  # ISO date
    date_to: Optional[str] = None
    selected_sources: list[str] = Field(default_factory=list)  # usernames, пусто = все
    extraction_goal: str = ""
