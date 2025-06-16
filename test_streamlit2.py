import streamlit as st
import os
import pandas as pd
import pymupdf  # PyMuPDF
import re
import csv

def extract_articles_with_pages(doc):
    articles = []
    current_article = None

    for page_number in range(len(doc)):
        page = doc[page_number]
        text = page.get_text()
        lines = text.split('\n')

        for i, line in enumerate(lines):
            article_match = re.fullmatch(r'Article\s+(\d+)\s*', line)
            if article_match:
                if current_article:
                    articles.append(current_article)
                current_article = {
                    'article_number': f"Article {article_match.group(1)}",
                    'title': lines[i + 1].strip() if i + 1 < len(lines) else '',
                    'body': '',
                    'start_page': page_number + 1
                }
            elif current_article:
                current_article['body'] += line + '\n'

    if current_article:
        articles.append(current_article)

    return articles

def extract_requirements_from_article(article):
    # Requirement clause pattern: starts with a number or letter (e.g., 1., (a))
    pattern = re.compile(r'(?P<id>\(?[0-9a-zA-Z]+\)?\.)\s+(?P<text>.*?)(?=(\n\(?[0-9a-zA-Z]+\)?\.)|\Z)', re.DOTALL)
    matches = pattern.finditer(article['body'])

    requirements = []
    for match in matches:
        req_id = match.group('id').strip()
        text = re.sub(r'\s+', ' ', match.group('text').strip())
        if any(kw in text.lower() for kw in ['shall', 'must', 'is required to', 'are prohibited from', 'shall not']):
            # Extract references to other articles or annexes
            references = re.findall(r'\b(Article\s+\d+|Annex\s+[A-Z]+)\b', text)
            requirements.append({
                'Article': article['article_number'],
                'Title': article['title'],
                'Requirement ID': req_id,
                'Requirement Text': text,
                'References': '; '.join(references),
                'Page Number': article['start_page']
            })
    return requirements

def extract_requirements(pdf_path, output_csv='requirements.csv'):
    doc = pymupdf.open(pdf_path)
    articles = extract_articles_with_pages(doc)

    all_requirements = []
    for article in articles:
        all_requirements.extend(extract_requirements_from_article(article))

    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'Article', 'Title', 'Requirement ID', 'Requirement Text', 'References', 'Page Number'
        ])
        writer.writeheader()
        for row in all_requirements:
            writer.writerow(row)

    output_csv_path = f"/mnt/data/{output_csv}"
    return output_csv_path, len(all_requirements)

# Здесь подключается твоя функция извлечения требований
# Предполагается, что она уже определена где-то в твоем коде
# def extract_requirements(input_pdf: str, output_csv: str) -> int:
#     ...

st.set_page_config(page_title="Requirements extraction")

st.title("Requirements extraction")

# 1. Загрузка PDF
uploaded_file = st.file_uploader("Select PDF-file with requirements", type="pdf")

# 2. Имя CSV-файла по умолчанию
default_csv_name = ""
if uploaded_file:
    base_name = os.path.splitext(uploaded_file.name)[0]
    default_csv_name = f"_csv/{base_name}.csv"

csv_filename = st.text_input("Name of CSV-file", value=default_csv_name)

# 3. Кнопка Analyze
if st.button("Analyze") and uploaded_file and csv_filename:
    try:
        # Запускаем извлечение требований
        _,count = extract_requirements(uploaded_file.name, csv_filename)
        st.success(f"Number of requrements extracted: {count}")
        st.info(f"The results are saved to the file: {csv_filename}")
    except Exception as e:
        st.error(f"Some issues: {e}")

# 4. Кнопка Show results
if st.button("Show results") and csv_filename and os.path.exists(csv_filename):
    try:
        df = pd.read_csv(csv_filename)
        st.dataframe(df)
    except Exception as e:
        st.error(f"Не удалось загрузить CSV: {e}")
