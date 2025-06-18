import pymupdf  # PyMuPDF
import re
import csv

### Configuration: level of extractions
article = re.compile(r'Article\s+(\d+)\s*')
requirement = re.compile(r'^(\d+)\.\s*(.*)')
s_requirement = re.compile(r'^(\d+)\.\s*(.*)')
ss_requirement = re.compile(r'^\((i+)\)\s*(.*)')

### lines to ignore ###
IGNORE = {'5.5.2017', 'L 117/21', 'Official Journal of the European Union', 'EN'}


def extract_articles_with_pages(doc):
    articles = []
    current_article = None

    for page_number in range(len(doc)):
        page = doc[page_number]
        text = page.get_text()
        lines = text.split('\n')

        for i, line in enumerate(lines):
            if any(line.startswith(ign) for ign in IGNORE): continue

            article_match = re.fullmatch(article, line)
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
    lettered_pattern = re.compile(r'^\(([a-z]+)\)\s*(.*)')

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
                    'Requirement_ID': 'chapter_02_' + article['article_number'].lower() + '_req' + current_parent_id,
                    'Article': article['article_number'],
                    'Title': article['title'],
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
                'Requirement_ID': 'chapter_02_' + article['article_number'].lower() + '_req' + current_parent_id + sub_id,
                'Article': article['article_number'],
                'Title': article['title'],
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
            'Requirement_ID': 'chapter_02_' + article['article_number'].lower() + '_req' + current_parent_id,
            'Article': article['article_number'],
            'Title': article['title'],
            'Parent': '',
            'Requirement Text': current_parent_text,
            'References': '; '.join(references),
            'Page': article['start_page']
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
            'Requirement_ID', 'Article', 'Title', 'Parent', 'Requirement Text', 'References', 'Page'
        ])
        writer.writeheader()
        for row in all_requirements:
            writer.writerow(row)

    return f"{output_csv}", len(all_requirements)
