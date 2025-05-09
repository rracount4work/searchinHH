import streamlit as st
import requests
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
import os

# Загружаем переменные из .env
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
Ты — специалист по подбору персонала. Проанализируй каждое резюме, сравни с вакансией.

1. Сначала кратко прокомментируй, что в резюме хорошо, а что вызывает сомнения.
2. Оцени, насколько ясно кандидат описал опыт (понимаем ли, что он делал и чего добился).
3. В конце поставь общую оценку от 1 до 10.

Вывод представь в виде:
- Комментарий
- Понимание опыта: (да/нет/частично)
- Оценка: (число от 1 до 10)
""".strip()

st.title("Сравнительный анализ резюме")

job_description = st.text_area("Введите описание вакансии")
gdoc_link = st.text_input("Вставьте ссылку на Google Документ с резюме (формат .doc, .txt, Google Docs)")

def fetch_text_from_gdoc(url):
    try:
        if "/edit" in url:
            url = url.split("/edit")[0] + "/export?format=txt"
        response = requests.get(url)
        if response.ok:
            return response.text
        else:
            return f"[Ошибка при загрузке файла: {response.status_code}]"
    except Exception as e:
        return f"[Ошибка: {str(e)}]"

def split_resumes(raw_text):
    resumes = []
    current = []
    for line in raw_text.splitlines():
        if line.strip().lower().startswith("резюме"):
            if current:
                resumes.append("\n".join(current).strip())
                current = []
        current.append(line)
    if current:
        resumes.append("\n".join(current).strip())
    return resumes

def analyze_resume(resume_text, job_desc):
    user_prompt = f"# ВАКАНСИЯ\n{job_desc}\n\n# РЕЗЮМЕ\n{resume_text}"
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=1000,
        temperature=0,
    )
    return response.choices[0].message.content

# --- ВОТ ОНА — КНОПКА ---
if st.button("Анализировать резюме"):
    if not gdoc_link:
        st.error("Пожалуйста, вставьте ссылку на Google Docs.")
    else:
        with st.spinner("Загружаем и анализируем резюме..."):
            text = fetch_text_from_gdoc(gdoc_link)
            if text.startswith("[Ошибка"):
                st.error(text)
            else:
                resumes = split_resumes(text)
                results = []
                for i, resume in enumerate(resumes, 1):
                    with st.spinner(f"Анализ резюме {i}..."):
                        result = analyze_resume(resume, job_description)
                        st.markdown(f"### Резюме {i}")
                        st.write(result)
                        score_line = next((line for line in result.splitlines() if "Оценка" in line), None)
                        clarity_line = next((line for line in result.splitlines() if "Понимание опыта" in line), None)
                        results.append({
                            "Резюме": f"Резюме {i}",
                            "Оценка": score_line.split(":")[1].strip() if score_line else "—",
                            "Понимание опыта": clarity_line.split(":")[1].strip() if clarity_line else "—"
                        })
                df = pd.DataFrame(results)
                st.markdown("## Сравнительная таблица")
                st.dataframe(df)
