from pathlib import Path
from manage_documents_v3.modules.database import DocumentDatabase
from manage_documents_v3.modules.scanner import DocumentScanner

project_path = Path(r'D:\NEW_GEN\LIVE_SUPPORT_2026\FOOTNOTES\From-2026-1st-to-now')

print('Creating database...')
db = DocumentDatabase(project_path)

print('Creating scanner...')
scanner = DocumentScanner(db, log_callback=print)

print('Scanning (this may take a moment)...')
count = scanner.scan()
print(f'Scan complete! Found {count} documents.')

print(f'Saving database...')
db.save()

print(f'\nTotal in database: {len(db.get_all())}')
print('\nFirst 3 documents:')
for docid, doc in list(db.get_all().items())[:3]:
    print(f'  {docid}')
    files = doc.get('files', {})
    print(f"    HTML: {files.get('original_html', 'N/A')}")
    print(f"    XML: {files.get('original_xml', 'N/A')}")
    print(f"    Updated: {files.get('updated_html', 'N/A')}")
