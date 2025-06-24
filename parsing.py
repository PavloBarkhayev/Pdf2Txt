import pymupdf  # PyMuPDF
import re
import csv

### Configuration: level of extractions
h_elements = [
    {'type': 'chapter', 're_cmp': re.compile(r'^CHAPTER\s+([IVX]+)\s*')},
    {'type': 'article', 're_cmp': re.compile(r'^Article\s+(\d+)\s*$')},
    {'type': 'req', 're_cmp': re.compile(r'^(\d+)\.\s*(.*)')},
    {'type': 'sreq', 're_cmp': re.compile(r'^\(([a-hj-z])\)\s*(.*)')},
    {'type': 'ssreq', 're_cmp': re.compile(r'^\((i+)\)\s*(.*)')}
]

refs = re.compile(r'\b(Article\s+\d+(?:\(\d+\))?|Annex\s+[A-Z]+)\b') #

### Dictionary storing exrtacted requirements with hierachy
res_dct = {
    'id': 'mdr',
    'type': 'doc',
    'title': 'MDR REGULATION (EU) 2017/745 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL',
    'body': [],
    'page': 0,
    'child': [],
    'refs': [],
    'parent': None
}

### lines to ignore ###
IGNORE = {'5.5.2017', 'L 117/21', 'Official Journal of the European Union', 'EN'}

def extract_all(doc):
    cur_arr, cur_ind = [res_dct] + [None] * len(h_elements), 0
    for page_number in range(len(doc)):
        page = doc[page_number]
        text = page.get_text()
        lines = text.split('\n')

        for i, line in enumerate(lines):
            if any(line.startswith(ign) for ign in IGNORE): continue

            new_el = next((k for k,h_dct in enumerate(h_elements,1) if h_dct['re_cmp'].match(line)), None)
            if new_el:
                cur_arr[cur_ind]['refs'] = refs.findall(' '.join(cur_arr[cur_ind]['body']))

                match = h_elements[new_el-1]['re_cmp'].match(line)
                tp = h_elements[new_el-1]['type']
                id = f'{cur_arr[new_el-1]["id"]}+{tp}_{match.group(1)}'
                body = [match.group(2)] if new_el >= 3 else []
                #print(id, body)

                cur_arr[new_el-1]['child'].append({'id': id, 'type': tp, 'title': '', 'body': body, 'page': page_number+1, 'child': [], 'refs': [], 'parent':cur_arr[new_el-1]})
                cur_arr[new_el] = cur_arr[new_el-1]['child'][-1]
                
                cur_arr[new_el+1:] = [None] * (len(h_elements) - new_el)
                cur_ind = new_el
            else:
                if cur_ind == 1:
                    cur_arr[cur_ind]['title'] += line
                if cur_ind == 2 and cur_arr[cur_ind]['title'] == '':
                    cur_arr[cur_ind]['title'] = line
                elif cur_ind == 2:
                    id = f'{cur_arr[cur_ind]["id"]}+req_noid'
                    cur_arr[cur_ind]['child'].append({'id': id, 'type': 'req', 'title': '', 'body': [], 'page': page_number+1, 'child': [], 'refs': [], 'parent':cur_arr[cur_ind]})
                    cur_arr[cur_ind+1] = cur_arr[cur_ind]['child'][-1]
                    cur_ind += 1
                
                cur_arr[cur_ind]['body'] += [line]

    return res_dct
                
def extract_and_write(pdf_path, output_folder='_csv'):
    doc = pymupdf.open(pdf_path)
    structure = extract_all(doc)
    row_counter = 0

    def write_structure(node, writer):
        nonlocal row_counter
        writer.writerow([node['id'], node['type'], node['title'], '\n'.join(node['body']), node['parent']['id'] if node['parent'] else '', '; '.join(node['refs']), node['page']])
        row_counter += node['type'].endswith('req')
        for ch in node['child']:
            write_structure(ch, writer)

    def write_toc(node, writer):
        if not node['type'].endswith('req'):
            writer.writerow([node['id'], node['type'], node['title'], node['parent']['id'] if node['parent'] else '', node['page']])
            for ch in node['child']:
                write_toc(ch, writer)

    with open(f'{output_folder}/requirements.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'type', 'title', 'text', 'parent', 'references', 'page'])
        
        write_structure(structure, writer)

    with open(f'{output_folder}/toc.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'type', 'title', 'parent', 'page'])
        
        write_toc(structure, writer)

    return row_counter
                



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
