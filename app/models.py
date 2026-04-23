from __future__ import annotations

from datetime import datetime
from typing import Dict, List
from uuid import uuid4

from pydantic import BaseModel, Field


class AssessmentResponse(BaseModel):
    """Структурированный ответ AI по результатам прескоринга."""

    score: int = Field(..., ge=0, le=100)
    strong_sides: List[str] = Field(default_factory=list)
    weak_sides: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    summary: str


class HistoryEntry(BaseModel):
    """Запись результата анализа для хранения в истории."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    candidate_name: str
    vacancy_snippet: str

    final_score: int = Field(..., ge=0, le=100)
    gpt_score: int = Field(..., ge=0, le=100)
    heuristic_score: float = Field(..., ge=0, le=100)

    ratios: Dict[str, float] = Field(default_factory=dict)

    gpt_response: AssessmentResponse