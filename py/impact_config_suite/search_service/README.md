# Search Service

Distributed Search API for IMPACT configuration files.

## Features

- FastAPI-based REST API
- Document fetching by date range
- Batch file copying
- Multi-term search in HTML/XML files
- Web UI for manual operations

## Dependencies

```
fastapi>=0.100.0
uvicorn>=0.22.0
pydantic>=2.0.0
jinja2>=3.1.0
```

## Usage

### Start Service

```bash
# Via GUI (search_tab.py)
python main.py
# Select "Search" tab

# Via command line
python -m search_service.run
# or
uvicorn search_service.app.app:app --host 0.0.0.0 --port 7000
```

### Access Web UI

Open browser: http://127.0.0.1:7000/ui

## API Endpoints

### POST /fetch

Fetch document IDs by date range.

```json
{
  "days": 7,           // Days back from today
  "date_str": "2024-01-15",  // OR specific date
  "root_folder": "/custom/path"  // Optional override
}
```

**Response**:
```json
{
  "batches": ["D:/SEARCH_API/BATCH_LISTS_xxx/1_250.txt"],
  "output_folder": "D:/SEARCH_API/BATCH_LISTS_xxx"
}
```

### POST /copy

Copy files from batch file.

```json
{
  "batch_file": "D:/SEARCH_API/.../1_250.txt",
  "root_folder": "/custom/path"
}
```

**Response**:
```json
{
  "copied": 200,
  "skipped": 50,
  "total": 250,
  "destination": "D:/SEARCH_API/.../BK_FILES/1_250"
}
```

### POST /search

Search terms in batch files.

```json
{
  "batch_folder": "D:/SEARCH_API/.../BK_FILES/1_250",
  "search_terms": ["pattern1", "pattern2"]
}
```

**Response**:
```json
{
  "results": [
    {
      "client": "ACS",
      "file_id": "12345",
      "doc_id": "unique-123",
      "found_keys": ["term_1", "term_2"]
    }
  ]
}
```

## Configuration

Edit `search_service/app/services/file_search.py`:
```python
ROOT_FOLDER = r"D:\IMPACT"   # Default scan folder
OUTPUT_BASE = r"D:\SEARCH_API"  # Output location
BATCH_SIZE = 250  # Documents per batch
```
