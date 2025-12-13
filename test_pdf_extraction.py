#!/usr/bin/env python3
"""Test PDF extraction to understand the document format."""

import pdfplumber
import re
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

pdf_path = sys.argv[1] if len(sys.argv) > 1 else 'statements/January 20.pdf'
print(f'Testing PDF: {pdf_path}')
print('='*60)

# Test raw extraction first
print('\n--- RAW TEXT EXTRACTION ---')
with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages[:2]):
        text = page.extract_text()
        if text:
            lines = text.split('\n')
            # Look for transaction-like lines
            for line in lines:
                # Check for Citi format: MM/DD ... $XX.XX
                if re.match(r'^\d{1,2}/\d{1,2}\s+', line) and re.search(r'\$[\d,]+\.\d{2}', line):
                    print(f'  -> {line[:120]}')

# Test with our new patterns
print('\n--- TESTING NEW PATTERNS ---')
def infer_year(filename):
    match = re.search(r'(\d{2})\.pdf$', filename, re.IGNORECASE)
    if match:
        return 2000 + int(match.group(1))
    return 2024

def clean_merchant(merchant):
    merchant = re.sub(r'\s+[A-Z]{2}$', '', merchant.strip())
    merchant = re.sub(r'\s+\d{3}[-.]?\d{3}[-.]?\d{4}\s*$', '', merchant)
    return ' '.join(merchant.split()).strip()

filename = os.path.basename(pdf_path)
year = infer_year(filename)
print(f'Inferred year: {year}')

transactions = []
citi_pattern = r'^(\d{1,2}/\d{1,2})(?:\s+\d{1,2}/\d{1,2})?\s+(.+?)\s+\$(\d[\d,]*\.\d{2})(?:\s|$)'

with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        if text:
            for line in text.split('\n'):
                line = line.strip()
                match = re.match(citi_pattern, line)
                if match:
                    date_str, merchant, amount_str = match.groups()
                    transactions.append({
                        'date': f'{date_str}/{year}',
                        'merchant': clean_merchant(merchant),
                        'amount': float(amount_str.replace(',', ''))
                    })

print(f'\nFound {len(transactions)} transactions:')
for i, t in enumerate(transactions[:10]):
    print(f'{i+1}. {t["date"]} | {t["merchant"][:40]:<40} | ${t["amount"]:.2f}')

if len(transactions) > 10:
    print(f'... and {len(transactions) - 10} more')

print(f'\n✅ Total: {len(transactions)} transactions extracted')

