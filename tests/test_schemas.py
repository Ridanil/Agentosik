"""
Базовые тесты (п.19 ТЗ, этап 6). Запуск: pytest tests/
"""
import pytest
from pydantic import ValidationError

from ai.schemas import AnalysisResult, ParsedQuery


def test_analysis_result_valid():
    result = AnalysisResult(
        relevant=True,
        relevance_score=0.9,
        quote="пример цитаты",
        explanation="объяснение",
        confidence="high",
    )
    assert result.relevant is True


def test_analysis_result_rejects_bad_score():
    with pytest.raises(ValidationError):
        AnalysisResult(
            relevant=True,
            relevance_score=1.5,  # вне диапазона 0..1
            quote="x",
            explanation="y",
            confidence="high",
        )


def test_analysis_result_rejects_bad_confidence():
    with pytest.raises(ValidationError):
        AnalysisResult(
            relevant=True,
            relevance_score=0.5,
            quote="x",
            explanation="y",
            confidence="очень высокая",  # не входит в Literal
        )


def test_parsed_query_defaults():
    q = ParsedQuery()
    assert q.keywords == []
    assert q.selected_sources == []
