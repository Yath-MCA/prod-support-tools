# Data Transfer Module

OCI File Download & MongoDB Insert Tool.

## Features

- Download files from OCI bucket
- Auto-move folders after download
- MongoDB record management
- JSON validation with signoff detection
- Real-time console output

## Dependencies

```
pymongo>=4.3.0
```

## Usage

```bash
python main.py
# Select "Data Transfer" tab
```

## Download Flow

1. Enter UniqueId
2. Click "Download from OCI"
3. Console shows real-time progress
4. After download completes:
   - Files move from `C:\_IMPACT\_LOCAL_FILES\IMPACT\{UniqueId}`
   - To: `C:\_IMPACT\_LOCAL_FILES\{UniqueId}`

## MongoDB Operations

### Record Format

```json
{
  "uniqueId": "unique-123",
  "filename": "document.pdf",
  "status": "pending",
  "signoff": true  // Optional - auto-sets status to "active"
}
```

### Signoff Detection

If JSON contains any of these fields with a truthy value:
- `signoff`
- `signOff`
- `signedOff`
- `approved`
- `approval`

Status will be automatically set to `active`.

### MongoDB Schema

```python
Database: impact_db
Collection: rfilelist

Document structure:
{
  "_id": ObjectId,
  "uniqueId": str,
  "filename": str,
  "status": "active" | "pending" | etc,
  "signoff": bool,
  "createdAt": ISO datetime string
}
```

## Console Logging

All operations log to the console:
- Timestamp prefixes: `[HH:MM:SS]`
- `[SUCCESS]` - Successful operations
- `[FAILED]` - Failed operations
- `[ERROR]` - Exception errors
- `[VALIDATE]` - JSON validation messages
- `[MONGO]` - MongoDB operations
