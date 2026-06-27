# Document Manager v3

## Architecture

- manage_documents.py : Entry point
- config.py           : Settings
- documents.json      : Project database
- process.log         : Execution log

## Modules

- scanner
- organizer
- downloader
- comparer
- reporter
- utils

The intent is for every stage to read/write documents.json so the workflow is resumable.
