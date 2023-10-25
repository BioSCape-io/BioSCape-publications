import os

from pyzotero import zotero
from datetime import datetime

# Written with assistance from ChatGPT

REPLACE_TOKEN = '<!-- TABLE_CONTENT -->'

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
        return ', '.join(formatted)

    def reformat_date(date_str: str) -> str:
        if not date_str:
            return ''

        # Parse the ISO date string
        iso_date = datetime.fromisoformat(date_str)
        # Format it as YYYY-MM-DD
        formatted_date = iso_date.strftime('%Y-%m-%d')
        return formatted_date

    data = d['data']
    return {
        'Title': f"<a href=\"{data['url']}\">{data['title']}</a>",
        'Creators': process_creators(data['creators']),
        'Date': reformat_date(data['date']),
    }

# Get the API key from the environment variable
api_key = os.environ.get('ZOTERO_API_KEY')
zot = zotero.Zotero("2810748", "group", api_key)
items = zot.top(limit=10)
# we've retrieved the latest five top-level items in our library
# we can print each item's item type and ID
input_list = [process_input(e) for e in items]

# Store lines of HTML table in a list
table_lines = []
# Create the table header
header = input_list[0].keys()
table_lines.append('<tr>')
for item in header:
    table_lines.append(f'<th>{item}</th>')
table_lines.append('</tr>')

# Create table rows for each input element
for item in input_list:
    table_lines.append('<tr>')
    for key, value in item.items():
        table_lines.append(f'<td>{value}</td>')
    table_lines.append('</tr>')

# Read the template file into list of lines
with open('template.html', 'r') as f:
    template_lines = f.readlines()

# Write the output file
with open('index.html', 'w') as f:
    for line in template_lines:
        if line.strip() == ('%s' % REPLACE_TOKEN):
            f.writelines(table_lines)
        else:
            f.write(line)