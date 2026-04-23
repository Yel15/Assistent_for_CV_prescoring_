import re
from pypdf import PdfReader


MAX_TEXT_LENGTH = 3000


def clean_text(text: str) -> str:
    """Очистка текста"""
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned[:MAX_TEXT_LENGTH]


def extract_text_from_pdf(file) -> str:
    try:
        file.seek(0)

        reader = PdfReader(file)
        text = []

        for page in reader.pages:
            text.append(page.extract_text() or "")

        return "\n".join(text)

    except Exception as e:
        print("PDF ERROR:", e)
        return ""


def extract_resume_text(uploaded_file, max_length=3000) -> str:
    """Главная функция извлечения текста"""

    file_type = uploaded_file.name.lower()

    if file_type.endswith(".pdf"):
        raw_text = extract_text_from_pdf(uploaded_file)

    elif file_type.endswith(".txt"):
        raw_text = uploaded_file.read().decode("utf-8")

    else:
        return ""

    cleaned = clean_text(raw_text)

    return cleaned[:max_length]