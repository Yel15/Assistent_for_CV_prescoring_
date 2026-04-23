"""Сервис прескоринга резюме через OpenAI с проверкой JSON-ответа."""

import json
import logging
import time
from typing import Optional

from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.models import AssessmentResponse


CLIENT: Optional[OpenAI] = None

if not OPENAI_API_KEY:
    logging.warning("OPENAI_API_KEY is not set. GPT service will not function correctly.")
else:
    CLIENT = OpenAI(api_key=OPENAI_API_KEY)


SYSTEM_PROMPT = (
    "Ты профессиональный HR-аналитик. "
    "Оцени соответствие кандидата вакансии. "
    "Верни валидный JSON строго в указанном формате. "
    "Строковые поля не должны содержать переносов строк. "
    "Если нужен перенос, используй \\n."
)

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

PROMPT_MAP = {
    "soft": BASE_DIR / "prompts" / "prescoring_soft.txt",
    "strict": BASE_DIR / "prompts" / "prescoring_strict.txt",
}

def load_prompt(vacancy: str, resume: str, mode: str) -> str:
    prompt_path = PROMPT_MAP.get(mode)

    if not prompt_path or not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found for mode: {mode}")

    template = prompt_path.read_text(encoding="utf-8")

    return template.format(
        vacancy=vacancy,
        resume=resume,
    )

def _extract_json_payload(raw_text: str) -> str:
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw_text[start:end + 1]
    return raw_text


def _strip_code_block(text: str) -> str:
    trimmed = text.strip()
    if trimmed.startswith("```") and trimmed.endswith("```"):
        return trimmed.strip("`\n ")
    return trimmed


def _sanitize_json(raw: str) -> str:
    buffer = []
    in_string = False
    escaped = False

    for char in raw:
        if char == '"' and not escaped:
            in_string = not in_string

        if char == "\\" and not escaped:
            escaped = True
            buffer.append(char)
            continue

        if char == "\r" and in_string:
            buffer.append("\\r")
            escaped = False
            continue

        if char == "\n" and in_string:
            buffer.append("\\n")
            escaped = False
            continue

        buffer.append(char)
        escaped = False

    return "".join(buffer)


def _repair_json(payload: str) -> str:
    if payload.count('"') % 2 != 0:
        payload += '"'

    open_braces = payload.count("{") - payload.count("}")
    if open_braces > 0:
        payload += "}" * open_braces

    return payload


def get_assessment(vacancy: str, resume: str, mode: str = "soft", retries: int = 3):
    """Запрашивает оценку у OpenAI и валидирует ответ через AssessmentResponse."""

    if not vacancy or not resume:
        raise ValueError("Vacancy and resume text are required.")

    if CLIENT is None:
        raise RuntimeError("OPENAI_API_KEY отсутствует в .env.")

    prompt = load_prompt(vacancy, resume, mode)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    for attempt in range(1, retries + 1):
        try:
            response = CLIENT.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.2,
            )
        except OpenAIError as error:
            logging.exception("OpenAI API request failed: %s", error)
            if attempt == retries:
                raise RuntimeError("Ошибка при обращении к OpenAI API.") from error
            time.sleep(1)
            continue

        content = response.choices[0].message.content
        if not content:
            if attempt == retries:
                raise RuntimeError("Модель вернула пустой ответ.")
            time.sleep(1)
            continue

        payload = _strip_code_block(content)
        payload = _extract_json_payload(payload)
        payload = payload.strip()
        payload = _sanitize_json(payload)
        payload = _repair_json(payload)

        try:
            parsed = json.loads(payload, strict=False)
            assessment = AssessmentResponse.model_validate(parsed)
            return assessment
        except (json.JSONDecodeError, ValidationError) as error:
            logging.warning(
                "GPT response validation failed on attempt %s: %s",
                attempt,
                error,
            )
            if attempt == retries:
                raise RuntimeError(
                    "Не удалось получить валидный JSON-ответ от модели."
                ) from error
            time.sleep(1)
            continue

    raise RuntimeError("Не удалось получить оценку от GPT.")