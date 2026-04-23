"""Логика эвристической оценки и хранения истории."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Dict, Iterable, List

from app.models import AssessmentResponse, HistoryEntry


HISTORY_FILE = Path("data/history/history.json")

SOFT_SKILLS = (
    "communication",
    "teamwork",
    "leadership",
    "adaptability",
    "initiative",
    "problem-solving",
    "creativity",
    "trust",
    "empathy",
    "critical thinking",
    "коммуникация",
    "командная работа",
    "лидерство",
    "адаптивность",
    "инициативность",
    "ответственность",
    "критическое мышление",
)


def _normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """Нормализует веса так, чтобы их сумма стала равна 1."""
    total = sum(weights.values())
    if not total:
        logging.debug("Сумма весов равна нулю, используются значения по умолчанию.")
        return {"hard": 0.6, "experience": 0.25, "soft": 0.15}

    return {key: value / total for key, value in weights.items()}


def _token_set(text: str) -> Iterable[str]:
    """Извлекает уникальные токены длиной от 4 символов."""
    return set(
        token.lower()
        for token in re.findall(r"\b[\wа-яёА-ЯЁ+\-#\.]{4,}\b", text)
        if len(token) >= 4
    )


def calculate_hard_skill_score(vacancy: str, resume: str) -> float:
    """Считает процент пересечения токенов вакансии и резюме."""
    vacancy_tokens = _token_set(vacancy)
    resume_tokens = _token_set(resume)

    if not vacancy_tokens:
        return 0.0

    match_count = len(vacancy_tokens & resume_tokens)
    return round((match_count / len(vacancy_tokens)) * 100, 2)


def calculate_experience_score(resume: str) -> float:
    """Ищет упоминания лет опыта и масштабирует результат к диапазону 0-100."""
    years = [
        float(match)
        for match in re.findall(
            r"(\d+(?:\.\d+)?)\s*(?:years?|лет|yrs|года|год)",
            resume,
            flags=re.IGNORECASE,
        )
    ]

    extracted = max(years, default=0.0)
    scaled = min(extracted, 15.0) / 15.0
    return round(scaled * 100, 2)


def calculate_soft_skill_score(resume: str) -> float:
    """Считает процент найденных soft skills из словаря."""
    normalized_text = resume.lower()
    matches = sum(1 for skill in SOFT_SKILLS if skill in normalized_text)

    if not SOFT_SKILLS:
        return 0.0

    return round((matches / len(SOFT_SKILLS)) * 100, 2)


def calculate_heuristic_score(
    vacancy: str,
    resume: str,
    weights: Dict[str, float] | None = None,
) -> Dict[str, float]:
    """Возвращает детализацию эвристической оценки."""
    if weights is None:
        weights = {"hard": 0.6, "experience": 0.25, "soft": 0.15}

    normalized_weights = _normalize_weights(weights)

    hard = calculate_hard_skill_score(vacancy, resume)
    experience = calculate_experience_score(resume)
    soft = calculate_soft_skill_score(resume)

    weighted = (
        hard * normalized_weights["hard"]
        + experience * normalized_weights["experience"]
        + soft * normalized_weights["soft"]
    )

    return {
        "hard": hard,
        "experience": experience,
        "soft": soft,
        "heuristic": round(weighted, 2),
        "ratios": normalized_weights,
    }


def calculate_final_score(heuristic_score: float, gpt_score: int) -> int:
    """Смешивает эвристику и GPT-оценку."""
    final = (heuristic_score * 0.4) + (gpt_score * 0.5)
    return min(100, max(0, int(round(final))))


def extract_candidate_name(resume_text: str) -> str:
    """Пытается взять имя кандидата из первой осмысленной строки."""
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    if not lines:
        return "Unknown candidate"

    first_line = lines[0]
    return first_line[:100]


def load_history() -> List[HistoryEntry]:
    """Загружает историю из JSON, если файл существует."""
    if not HISTORY_FILE.exists():
        return []

    try:
        with HISTORY_FILE.open("r", encoding="utf-8") as handler:
            data = json.load(handler)
        return [HistoryEntry.model_validate(entry) for entry in data]
    except Exception:
        logging.exception("Не удалось загрузить историю оценок")
        return []


def _persist_history(history: List[HistoryEntry]) -> None:
    """Сохраняет историю в JSON."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    with HISTORY_FILE.open("w", encoding="utf-8") as handler:
        sanitized = []
        for entry in history:
            record = entry.model_dump()
            record["timestamp"] = entry.timestamp.isoformat()
            sanitized.append(record)

        json.dump(sanitized, handler, ensure_ascii=False, indent=2)


def append_history(entry: HistoryEntry) -> None:
    """Добавляет запись в историю."""
    history = load_history()
    history.append(entry)
    _persist_history(history)


def build_history_entry(
    candidate_name: str,
    vacancy: str,
    assessment: AssessmentResponse,
    heuristic_details: Dict[str, float],
    final_score: int,
) -> HistoryEntry:
    """Собирает объект истории из результата анализа."""
    return HistoryEntry(
        candidate_name=candidate_name,
        vacancy_snippet=vacancy.strip()[:300],
        final_score=final_score,
        gpt_score=assessment.score,
        heuristic_score=heuristic_details["heuristic"],
        ratios={
            "hard": round(heuristic_details["ratios"]["hard"], 2),
            "experience": round(heuristic_details["ratios"]["experience"], 2),
            "soft": round(heuristic_details["ratios"]["soft"], 2),
        },
        gpt_response=assessment,
    )
def clear_history() -> None:
    """Полностью очищает историю оценок."""
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()

def build_comparison_table() -> List[Dict]:
    """Формирует таблицу сравнения кандидатов на основе истории."""
    history = load_history()

    rows = []
    for entry in history:
        rows.append(
            {
                "candidate_name": entry.candidate_name,
                "final_score": entry.final_score,
                "gpt_score": entry.gpt_score,
                "heuristic_score": entry.heuristic_score,
                "hard_weight": entry.ratios.get("hard", 0),
                "experience_weight": entry.ratios.get("experience", 0),
                "soft_weight": entry.ratios.get("soft", 0),
                "summary": entry.gpt_response.summary,
                "timestamp": entry.timestamp.strftime("%Y-%m-%d %H:%M"),
            }
        )

    rows.sort(key=lambda x: x["final_score"], reverse=True)
    return rows
