import streamlit as st
import os
import pandas as pd
import fitz
#import pymupdf  # PyMuPDF
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
    requirements = []
    body_lines = article['body'].splitlines()
    current_parent_id = None
    current_parent_text = ""

    # Pattern to detect numbered and lettered requirement IDs
    numbered_pattern = re.compile(r'^(\d+)\.\s*(.*)')
    lettered_pattern = re.compile(r'^\(([a-z])\)\s*(.*)')

    for line in body_lines:
        line = line.strip()
        if not line:
            continue

        numbered_match = numbered_pattern.match(line)
        lettered_match = lettered_pattern.match(line)

        if numbered_match:
            if current_parent_id and current_parent_text:
                references = re.findall(r'\b(Article\s+\d+|Annex\s+[A-Z]+)\b', current_parent_text)
                requirements.append({
                    'Article': article['article_number'],
                    'Title': article['title'],
                    'Requirement_ID': current_parent_id,
                    'Parent': '',
                    'Requirement Text': current_parent_text,
                    'References': '; '.join(references),
                    'Page': article['start_page']
                })
            current_parent_id = numbered_match.group(1) + '.'
            current_parent_text = numbered_match.group(2).strip()
        elif lettered_match and current_parent_id:
            sub_id = f"({lettered_match.group(1)})"
            text = lettered_match.group(2).strip()
            references = re.findall(r'\b(Article\s+\d+|Annex\s+[A-Z]+)\b', text)
            requirements.append({
                'Article': article['article_number'],
                'Title': article['title'],
                'Requirement_ID': sub_id,
                'Parent': current_parent_id,
                'Requirement Text': text,
                'References': '; '.join(references),
                'Page': article['start_page']
            })
        else:
            if current_parent_id:
                current_parent_text += ' ' + line

    if current_parent_id and current_parent_text:
        references = re.findall(r'\b(Article\s+\d+|Annex\s+[A-Z]+)\b', current_parent_text)
        requirements.append({
            'Article': article['article_number'],
            'Title': article['title'],
            'Requirement_ID': current_parent_id,
            'Parent': '',
            'Requirement Text': current_parent_text,
            'References': '; '.join(references),
            'Page': article['start_page']
        })

    return requirements

def extract_requirements(pdf_path, output_csv='requirements.csv'):
    doc = pymupdf.open(pdf_path)
    print('sus')
    articles = extract_articles_with_pages(doc)

    all_requirements = []
    for article in articles:
        all_requirements.extend(extract_requirements_from_article(article))

    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'Article', 'Title', 'Requirement_ID', 'Parent', 'Requirement Text', 'References', 'Page'
        ])
        writer.writeheader()
        for row in all_requirements:
            writer.writerow(row)

    return f"{output_csv}", len(all_requirements)


st.set_page_config(page_title="Requirements extraction")

st.title("Requirements extraction")

# 1. Загрузка PDF
uploaded_file = st.file_uploader("Выберите PDF-файл с требованиями", type="pdf")

# 2. Имя CSV-файла по умолчанию
default_csv_name = ""
if uploaded_file:
    base_name = os.path.splitext(uploaded_file.name)[0]
    default_csv_name = f"_csv/{base_name}.csv"

csv_filename = st.text_input("Имя выходного CSV-файла", value=default_csv_name)

# 3. Кнопка Analyze
if st.button("Analyze") and uploaded_file and csv_filename:
    try:
        # Запускаем извлечение требований
        _,count = extract_requirements(uploaded_file.name, csv_filename)
        st.success(f"Извлечено требований: {count}")
        st.info(f"Результаты сохранены в файл: {csv_filename}")
    except Exception as e:
        st.error(f"Ошибка при анализе: {e}")

# 4. Кнопка Show results
if st.button("Show results") and csv_filename and os.path.exists(csv_filename):
    try:
        df = pd.read_csv(csv_filename)
        st.dataframe(df)
    except Exception as e:
        st.error(f"Не удалось загрузить CSV: {e}")
