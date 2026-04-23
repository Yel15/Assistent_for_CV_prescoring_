import pandas as pd
import streamlit as st

from app.llm_service import get_assessment
from app.resume_parser import extract_resume_text
from app.scoring import (
    append_history,
    build_comparison_table,
    build_history_entry,
    calculate_final_score,
    calculate_heuristic_score,
    clear_history,
    extract_candidate_name,
    load_history,
)


def highlight_best_candidates(row):
    final_score = row.get("Final Score", 0)

    if final_score >= 80:
        return ["background-color: #d4edda"] * len(row)
    if final_score >= 65:
        return ["background-color: #fff3cd"] * len(row)
    return [""] * len(row)


def reset_to_upload():
    keys_to_clear = [
        "vacancy_text",
        "uploaded_file_key",
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()


def run_app():
    st.set_page_config(page_title="CV Prescoring Assistant", layout="wide")

    if "uploaded_file_key" not in st.session_state:
        st.session_state["uploaded_file_key"] = 0

    st.title("AI ассистент прескоринга резюме")

    st.subheader("Описание вакансии")
    vacancy_text = st.text_area(
        "Вставьте текст вакансии",
        height=200,
        key="vacancy_text",
    )

    st.subheader("Загрузка резюме")

    st.info("Рекомендуемый формат: PDF или TXT")

    uploaded_file = st.file_uploader(
        "Загрузите файл резюме",
        type=["pdf", "txt"]
    )

    st.subheader("Режим оценки")

    mode = st.radio(
        "Выбери стиль оценки",
        options=["soft", "strict"],
        format_func=lambda x: "Мягкий HR" if x == "soft" else "Строгий HR",
    )

    if st.button("Оценить кандидата"):
        if not vacancy_text.strip():
            st.warning("Добавь описание вакансии.")
            return

        if not uploaded_file:
            st.warning("Загрузи резюме.")
            return

        try:
            max_len = 3500
            resume_text = extract_resume_text(uploaded_file, max_length=max_len)

            if st.checkbox("Показать debug"):
                st.write(...)

            if not resume_text.strip():
                st.error("Не удалось извлечь текст из резюме.")
                return

            candidate_name = extract_candidate_name(resume_text)

            st.success("Текст резюме успешно извлечен.")

            if len(resume_text) >= max_len:
                st.info(f"Текст резюме обрезан до {max_len} символов.")

            with st.expander("Посмотреть извлеченный текст резюме"):
                st.text_area(
                    "Результат извлечения",
                    resume_text,
                    height=250,
                )

            with st.spinner("AI анализирует резюме..."):
                assessment = get_assessment(
                    vacancy_text,
                    resume_text,
                    mode=mode
                )

            heuristic_details = calculate_heuristic_score(vacancy_text, resume_text)
            final_score = calculate_final_score(
                heuristic_score=heuristic_details["heuristic"],
                gpt_score=assessment.score,
            )

            history_entry = build_history_entry(
                candidate_name=candidate_name,
                vacancy=vacancy_text,
                assessment=assessment,
                heuristic_details=heuristic_details,
                final_score=final_score,
            )
            append_history(history_entry)

            st.subheader("Результат прескоринга")

            col1, col2, col3 = st.columns(3)
            col1.metric("GPT Score", f"{assessment.score}/100")
            col2.metric("Heuristic Score", f'{heuristic_details["heuristic"]}/100')
            col3.metric("Final Score", f"{final_score}/100")

            st.markdown("### Детализация эвристики")
            st.write(f'Hard skills: {heuristic_details["hard"]}/100')
            st.write(f'Experience: {heuristic_details["experience"]}/100')
            st.write(f'Soft skills: {heuristic_details["soft"]}/100')

            st.markdown("### Кандидат")
            st.write(candidate_name)

            st.markdown("### Сильные стороны")
            if assessment.strong_sides:
                for item in assessment.strong_sides:
                    st.write(f"- {item}")
            else:
                st.write("Нет данных.")

            st.markdown("### Слабые стороны")
            if assessment.weak_sides:
                for item in assessment.weak_sides:
                    st.write(f"- {item}")
            else:
                st.write("Нет данных.")

            st.markdown("### Недостающие навыки")
            if assessment.missing_skills:
                for item in assessment.missing_skills:
                    st.write(f"- {item}")
            else:
                st.write("Нет данных.")

            st.markdown("### Итоговое резюме")
            st.write(assessment.summary)

            st.success("Результат сохранен в историю.")

        except Exception as e:
            st.error(f"Ошибка при обработке файла или выполнении анализа: {e}")

    st.divider()

    col_history, col_clear = st.columns([3, 1])

    with col_history:
        st.subheader("История оценок")

    with col_clear:
        if st.button("Очистить историю"):
            clear_history()
            st.success("История очищена.")
            st.rerun()

    history = load_history()

    if not history:
        st.info("История пока пуста.")
    else:
        history = sorted(history, key=lambda x: x.timestamp, reverse=True)

        for entry in history[:10]:
            with st.expander(
                f"{entry.candidate_name} | Final: {entry.final_score}/100 | "
                f"{entry.timestamp.strftime('%Y-%m-%d %H:%M')}"
            ):
                st.write(f"**Final score:** {entry.final_score}/100")
                st.write(f"**GPT score:** {entry.gpt_score}/100")
                st.write(f"**Heuristic score:** {entry.heuristic_score}/100")

                if entry.ratios:
                    st.write("**Weights:**")
                    st.write(
                        f"Hard: {entry.ratios.get('hard', 0)} | "
                        f"Experience: {entry.ratios.get('experience', 0)} | "
                        f"Soft: {entry.ratios.get('soft', 0)}"
                    )

                st.write("**Фрагмент вакансии:**")
                st.write(entry.vacancy_snippet)

                st.write("**Итоговое резюме GPT:**")
                st.write(entry.gpt_response.summary)

    st.divider()
    st.subheader("Сравнение кандидатов")

    comparison_rows = build_comparison_table()

    if not comparison_rows:
        st.info("Пока нет данных для сравнения кандидатов.")
    else:
        df = pd.DataFrame(comparison_rows)

        df = df[
            [
                "candidate_name",
                "final_score",
                "gpt_score",
                "heuristic_score",
                "timestamp",
                "summary",
            ]
        ]

        df = df.rename(
            columns={
                "candidate_name": "Кандидат",
                "final_score": "Final Score",
                "gpt_score": "GPT Score",
                "heuristic_score": "Heuristic Score",
                "timestamp": "Дата",
                "summary": "Комментарий",
            }
        )

        styled_df = df.style.apply(highlight_best_candidates, axis=1)

        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
        )

        csv_data = df.to_csv(index=False).encode("utf-8-sig")

        col_download, col_back, col_clear_table = st.columns(3)

        with col_download:
            st.download_button(
                label="Скачать таблицу кандидатов (CSV)",
                data=csv_data,
                file_name="candidates_comparison.csv",
                mime="text/csv",
            )

        with col_back:
            if st.button("Вернуться к загрузке резюме"):
                st.session_state["uploaded_file_key"] += 1
                if "vacancy_text" in st.session_state:
                    del st.session_state["vacancy_text"]
                st.rerun()

        with col_clear_table:
            if st.button("Очистить таблицу сравнения"):
                clear_history()
                st.success("Таблица сравнения очищена.")
                st.rerun()