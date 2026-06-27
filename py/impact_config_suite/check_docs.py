from pathlib import Path
from manage_documents_v3.modules.database import DocumentDatabase

project_path = Path(r'D:\NEW_GEN\LIVE_SUPPORT_2026\FOOTNOTES\From-2026-1st-to-now')
db = DocumentDatabase(project_path)
print(f'Total documents: {len(db.get_all())}')

# Show first 3 details
for docid, doc in list(db.get_all().items())[:3]:
    print(f'Doc: {docid}')
    files = doc.get('files', {})
    print(f"  HTML: {files.get('original_html', 'N/A')}")
    print(f"  XML: {files.get('original_xml', 'N/A')}")
    print(f"  Updated: {files.get('updated_html', 'N/A')}")
