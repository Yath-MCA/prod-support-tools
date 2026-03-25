# IMPACT Search API - Advanced File Discovery System

A powerful, modern file search system built with **FastAPI** and featuring a stunning user interface for searching and managing document files across your server.

![IMPACT Search UI](https://img.shields.io/badge/Status-Production_Ready-success)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688)

## 🎯 Overview

IMPACT Search is a comprehensive file discovery system designed to help you efficiently search through large document repositories. It provides batch processing capabilities, intelligent file copying, and advanced content search with a premium glass-morphism UI.

## ✨ Features

### 🔍 **Advanced Search Capabilities**
- **Batch Document Fetching**: Automatically scan and create batches of documents based on modification dates
- **Intelligent File Copying**: Copy relevant files (`*_updated.html` and `impact_config.xml`) in organized batches
- **Content Search**: Search within HTML files using multiple search terms with regex support
- **Email Extraction**: Automatically parse and extract author email addresses from XML configs
- **Smart Filtering**: Skip development files (pubkitdev) automatically

### 🎨 **Premium User Interface**
- **Modern Design**: Glass-morphism effects with animated gradient backgrounds
- **Responsive Layout**: Works perfectly on desktop, tablet, and mobile devices
- **Interactive Elements**: Smooth animations and hover effects
- **Real-time Feedback**: Toast notifications and loading overlays
- **Pagination**: Handle large result sets with ease
- **Dark Theme**: Easy on the eyes with vibrant accent colors

### 🚀 **Technical Highlights**
- **FastAPI Backend**: High-performance async API framework
- **RESTful API**: Clean, documented endpoints for all operations
- **Jinja2 Templates**: Server-side rendering for the UI
- **AJAX Requests**: Seamless user experience without page reloads
- **Structured Results**: JSON responses with detailed metadata

## 📋 Requirements

- Python 3.8 or higher
- FastAPI
- Uvicorn (ASGI server)
- Pydantic
- Jinja2

## 📦 Installation

1. **Clone or navigate to the project directory**:
   ```bash
   cd d:/PERSONAL/LIVE_PROJECTS/IMPACT/search_api/file-search-app
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure paths** (Optional):
   Edit `app/services/file_search.py` to customize:
   ```python
   ROOT_FOLDER = r"D:\IMPACT"      # Source directory
   OUTPUT_BASE = r"D:\SEARCH_API"   # Output directory for batches
   BATCH_SIZE = 250                  # Files per batch
   ```

## 🚀 Usage

### Starting the Server

```bash
python run.py
```

The server will start on `http://localhost:7000` with hot-reload enabled.

### Accessing the UI

Open your browser and navigate to:
```
http://localhost:7000/
```

or

```
http://localhost:7000/ui
```

### Using the Interface

#### 1. **Fetch Documents**
- Select date filter type (Last N Days or Specific Date)
- Enter the number of days or select a date
- Click "Fetch Documents"
- View generated batch files in the results

#### 2. **Copy Batch Files**
- Enter the full path to a batch file (e.g., `D:\SEARCH_API\BATCH_LISTS_...\1_250.txt`)
- Click "Copy Files"
- View statistics: copied, skipped, and total files

#### 3. **Search in Batch**
- Enter the batch folder path (where files were copied)
- Add search terms (one per line)
- Click "Search Now"
- Browse results with pagination
- Copy document IDs with one click

## 🔌 API Endpoints

### POST `/fetch`
Fetch documents modified after a specific date.

**Request Body**:
```json
{
  "days": 7,
  "date_str": "2024-01-01"  // Optional, use either days or date_str
}
```

**Response**:
```json
{
  "batches": [
    "D:\\SEARCH_API\\... \\1_250.txt",
    "D:\\SEARCH_API\\...\\251_500.txt"
  ],
  "output_folder": "D:\\SEARCH_API\\BATCH_LISTS_20240101_120000"
}
```

### POST `/copy`
Copy files from a batch to an organized folder.

**Request Body**:
```json
{
  "batch_file": "D:\\SEARCH_API\\BATCH_LISTS_...\\1_250.txt"
}
```

**Response**:
```json
{
  "copied": 245,
  "skipped": 5,
  "total": 250,
  "destination": "D:\\SEARCH_API\\...\\BK_FILES\\1_250"
}
```

### POST `/search`
Search for terms within batch files.

**Request Body**:
```json
{
  "batch_folder": "D:\\SEARCH_API\\...\\BK_FILES\\1_250",
  "search_terms": ["error", "warning", "critical"]
}
```

**Response**:
```json
{
  "results": [
    {
      "doc_id": "12345",
      "client": "ClientName",
      "file_id": "FILE-001",
      "emails": ["author@example.com"],
      "found_keys": ["term_1", "term_3"]
    }
  ]
}
```

### GET `/` or `/ui`
Serves the main user interface.

## 📁 Project Structure

```
file-search-app/
├── app/
│   ├── __init__.py
│   ├── app.py                 # FastAPI application setup
│   ├── routes/
│   │   ├── __init__.py
│   │   └── search_routes.py   # API routes and UI endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   └── file_search.py     # Core search logic
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css      # Premium UI styles
│   │   └── js/
│   │       └── app.js         # Frontend JavaScript
│   └── templates/
│       └── index.html         # Main UI template
├── run.py                     # Server entry point
└── requirements.txt           # Python dependencies
```

## 🎨 UI Features

### Design System
- **Color Palette**: HSL-based modern colors with vibrant accents
- **Typography**: Inter font family for clean, modern text
- **Spacing**: Consistent spacing scale using CSS custom properties
- **Animations**: Smooth transitions and floating background orbs
- **Glass Morphism**: Backdrop blur effects for cards
- **Responsive**: Mobile-first design with breakpoints

### Interactive Elements
- **Toast Notifications**: Success, error, and warning messages
- **Loading Overlays**: Visual feedback during async operations
- **Hover Effects**: Interactive buttons and cards
- **Copy to Clipboard**: Quick copy functionality for paths and IDs
- **Pagination**: Navigate through large result sets

## 🔧 Configuration

### Customizing Search Paths

Edit `app/services/file_search.py`:

```python
ROOT_FOLDER = r"D:\IMPACT"          # 📂 Where to scan for files
OUTPUT_BASE = r"D:\SEARCH_API"      # 📁 Where to save batches
BATCH_SIZE = 250                     # 📊 Files per batch
```

### Server Configuration

Edit `run.py` to change host/port:

```python
uvicorn.run(
    "app.app:app", 
    host="0.0.0.0",  # Change to "127.0.0.1" for local only
    port=7000,       # Change port number
    reload=True      # Disable in production
)
```

## 📊 How It Works

### 1. **Document Fetching**
- Scans `ROOT_FOLDER` for directories
- Filters by modification date
- Creates batch files with document IDs
- Organizes batches by timestamp

### 2. **File Copying**
- Reads document IDs from batch file
- Copies `*_updated.html` and `impact_config.xml`
- Renames files with document ID prefix
- Creates organized folder structure

### 3. **Content Search**
- Parses XML config for metadata
- Extracts client, file-id, and emails
- Searches HTML content for terms
- Returns structured results with matches

## 🌟 Best Practices

- **Use specific date ranges** for faster batch generation
- **Review batch sizes** before copying large file sets
- **Use simple search terms** for better performance
- **Monitor destination paths** to avoid disk space issues
- **Test with small batches** before processing large datasets

## 🐛 Troubleshooting

### Server Won't Start
```bash
# Check if port 7000 is already in use
netstat -ano | findstr :7000

# Kill the process or change the port in run.py
```

### Files Not Found
```bash
# Verify paths are accessible
dir "D:\IMPACT"
dir "D:\SEARCH_API"
```

### CSS Not Loading
```bash
# Make sure static files directory exists
dir "app\static\css"
dir "app\static\js"
```

## 📝 License

This project is proprietary and confidential.

## 👥 Support

For issues or questions, contact your development team.

---

**Built with ❤️ using FastAPI, modern web technologies, and a focus on user experience**
