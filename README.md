![Python](https://img.shields.io/badge/Python-3.11-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red)

# 🧠 AI Resume Prescoring Assistant

Web application for automated resume evaluation using AI.

The system analyzes candidate resumes against a job description and provides structured scoring, strengths, weaknesses, and a summary.

---

## 🚀 Features

- Upload resume in **PDF or TXT format**
- Input job description directly in the interface
- Two evaluation modes:
  - **Soft mode** — flexible matching
  - **Strict mode** — precise and demanding scoring
- Automatic resume parsing
- AI-powered analysis including:
  - Overall score
  - Strengths of the candidate
  - Weaknesses / gaps
  - Short professional summary
- Comparison table for all processed candidates

---

## 🧩 How it works

1. User uploads a resume (PDF or TXT)
2. Enters a job description
3. Selects evaluation mode (soft / strict)
4. System parses the resume
5. AI evaluates match between resume and vacancy
6. Results are displayed and saved for comparison

---

## 🛠️ Technologies

- Python
- Streamlit
- OpenAI API (or other LLM)
- PDF/TXT parsing libraries

---

## 📊 Output example
Candidate score (e.g. 78/100)
Strengths (skills, experience match)
Weaknesses (missing requirements)
Short professional summary
Candidate comparison table

---

## 🎯 Use cases
HR pre-screening
Recruitment automation
Candidate ranking
Resume quality analysis

---

## 📦 Installation

```bash

git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
pip install -r requirements.txt
