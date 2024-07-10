import os

from pyzotero import zotero
from datetime import datetime

# Written with assistance from ChatGPT

# Get the API key from the environment variable
# API key seems to be unnecessary for public libraries
API_KEY = os.environ.get('ZOTERO_API_KEY', "")
LIBRARY_ID = "2810748"
LIBRARY_TYPE = "group"
TARGET_COLLECTION = "U4SW8TCS"
AUTHOR_COUNT_THRESHOLD = 3
REPLACE_TOKEN = '<!-- TABLE_CONTENT -->'

def fix_word_spaces(s: str) -> str:
    words = []
    last_i = 0
    for i, c in enumerate(s):
        if c.isupper():
            words.append(s[last_i:i])
            last_i = i

    if last_i < len(s):
        words.append(s[last_i:])

    return ' '.join([w.capitalize() for w in words])

def process_input(d: dict) -> dict:
    def process_creators(creators: list) -> str:
        formatted = []
        for c in creators:
            first_name = c.get('firstName', None)
            last_name = c.get('lastName', None)
            name = c.get('name', None)

            if first_name and last_name:
                formatted.append(f"{first_name} {last_name}")
            elif first_name:
                formatted.append(first_name)
            elif last_name:
                formatted.append(last_name)
            elif name:
                formatted.append(name)

        if len(formatted) < AUTHOR_COUNT_THRESHOLD:
            return ', '.join(formatted)
        else:
            return f"<span title=\"{', '.join(formatted)}\">{formatted[0]} et al.</span>"

    def reformat_date(date_str: str) -> str:
        if not date_str:
            return ''

        try:
            # Parse the ISO date string
            iso_date = datetime.fromisoformat(date_str.rstrip('Z'))
            # Format it as YYYY-MM-DD
            formatted_date = iso_date.strftime('%Y-%m-%d')
        except ValueError:
            # If the date string is not in ISO format, just return it
            # Could be just year
            formatted_date = date_str

        return formatted_date

    def get_source(data: dict) -> str:
        if data["itemType"] == "journalArticle":
            return data.get('publicationTitle', '')
        elif data["itemType"] == "conferencePaper":
            a = data.get('publicationTitle', '')
            # Some entries have conferenceName instead of publicationTitle
            if len(a) == 0:
                a = data.get('conferenceName', '')
            # Some entries have proceedingsTitle instead
            if len(a) == 0:
                a = data.get('proceedingsTitle', '')
            if len(a) == 0:
                a = data.get('meetingName', '')
            return a
        else:
            return ''

    data = d['data']
    title = data.get('title', '')
    url = data.get('url', '')

    return {
        'Title': f'<a target="_blank" rel="noopener noreferrer" href=\"{url}\">{title}</a>' if len(url) > 0 else title,
        'Item Type': fix_word_spaces(data['itemType']),
        'Journal/Conference/Source': get_source(data),
        'Creators': process_creators(data.get('creators', [])),
        'Date': reformat_date(data.get('date', '')),
    }

zot = zotero.Zotero(LIBRARY_ID, LIBRARY_TYPE, API_KEY)
items = zot.collection_items_top(TARGET_COLLECTION)
input_list = [process_input(e) for e in items]

# Store lines of HTML table in a list
table_lines = []
# Create the table header
header = input_list[0].keys()
table_lines.append('<thead>')
table_lines.append('<tr>')
for item in header:
    table_lines.append(f'<th class="column-{item}">{item}</th>')
table_lines.append('</tr>')
table_lines.append('</thead>')

# Create table rows for each input element
table_lines.append('<tbody id="tableBody">')
for item in input_list:
    table_lines.append('<tr>')
    for key, value in item.items():
        table_lines.append(f'<td class="column-{key}">{value}</td>')
    table_lines.append('</tr>')
table_lines.append('</tbody>')

# Read the template file into list of lines
with open('template.html', 'r') as f:
    template_lines = f.readlines()

# Write the output file
with open('index.html', 'w') as f:
    for line in template_lines:
        if line.strip() == ('%s' % REPLACE_TOKEN):
            f.write(line.rstrip().replace(REPLACE_TOKEN, '')) # Write the indentation
            f.writelines(table_lines)
            f.write('\n')
        else:
            f.write(line)
