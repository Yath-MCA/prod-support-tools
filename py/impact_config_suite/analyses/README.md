# Analyses Module

Content Analysis Engine for IMPACT documents.

## Features

- DOM/XPath query-based parsing for accurate element extraction
- Chapter, figure, table, footnote, and reference extraction
- Citation mapping and analysis
- HTML report generation with tabbed interface
- JSON data export for further processing
- Cache system for performance optimization

## Dependencies

```
lxml>=4.9.0
```

## Usage

```python
from analyses.book_analyzer import (
    Config, Logger, Cache, ContentAnalyzer, 
    ConfigParser, ReportGenerator
)

# Initialize components
config = Config()
logger = Logger(config)
cache = Cache(config.CACHE_FILE)
analyzer = ContentAnalyzer(cache, logger)
config_parser = ConfigParser(logger)

# Analyze a document
data = analyzer.analyze("/path/to/doc", "doc_id")

# Generate report
report = ReportGenerator.build_doc_blocks([{"id": "doc_id", "data": data}])
```

## Configuration

Settings are stored in `Documents/IMPACT_ConfigSuite/analyses/`:
- `analyzer_config.json` - User preferences
- `analyzer_cache.json` - Analysis cache
- `logs/` - Daily log files

## Report Structure

HTML reports include:
- Document metadata (client, file ID)
- Chapter breakdown with statistics
- Figure/Table/Reference tabbed views
- Citation counts and samples
