# QueryBaseModule Workflow Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      QueryBaseModule (Core)                      │
│                                                                   │
│  Properties:                                                      │
│  • _state (queries, comments, counts)                            │
│  • config (rules, selectors, responses)                          │
│  • editor (GlobalEditor reference)                               │
│  • events (EventTarget)                                          │
└───────────────┬─────────────────────────────────────────────────┘
                │
                │ Manages
                ├──────────────┬──────────────┬──────────────┬────────────────┐
                │              │              │              │                │
                ▼              ▼              ▼              ▼                ▼
    ┌───────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ QueryPanel    │ │ QueryDialog  │ │ QueryRestore │ │ QueryTemplates│ │ Attachment   │
    │ Module        │ │ Module       │ │ Module       │ │              │ │ Module       │
    ├───────────────┤ ├──────────────┤ ├──────────────┤ ├──────────────┤ ├──────────────┤
    │ • render()    │ │ • open()     │ │ • backup()   │ │ • templates  │ │ • upload()   │
    │ • renderItem()│ │ • close()    │ │ • restore()  │ │ • render()   │ │ • validate() │
    │ • refresh()   │ │ • save()     │ │ • compare()  │ │              │ │ • delete()   │
    └───────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

---

## Query Creation Workflow

### Author Creates Query (Without Attachments)

```
┌─────────┐
│ Author  │
└────┬────┘
     │
     │ 1. Click "Add Query"
     ▼
┌─────────────────────┐
│  Query Dialog       │
│  ┌───────────────┐  │
│  │ Content Input │  │
│  └───────────────┘  │
│  [ ] Attach Files   │
│  [Save] [Cancel]    │
└──────────┬──────────┘
           │
           │ 2. Enter content
           │ 3. Click Save
           ▼
┌─────────────────────────────────┐
│ QueryBaseModule.createQuery()   │
│                                  │
│ • Generate ID                    │
│ • Set label (AQ1, AQ2, etc.)    │
│ • Set status = "open"           │
│ • Store in _state.queries       │
│ • Emit "query-created" event    │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ DOM Update                       │
│                                  │
│ <span id="query_xxx"            │
│   data-class="ckcommentsfull"   │
│   data-label="AQ1"              │
│   data-status="open"            │
│   data-user-comment-box="...">  │
│   [Query Content]                │
│ </span>                          │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ Panel Update                     │
│                                  │
│ Query Panel:                     │
│ ┌─────────────────────────────┐ │
│ │ AQ1 [Open]                  │ │
│ │ "Please verify..."          │ │
│ │ Author • 2 min ago          │ │
│ └─────────────────────────────┘ │
│                                  │
│ Counts: Total: 1 | Open: 1      │
└──────────────────────────────────┘
```

---

## Query Creation with Attachments

### Author Creates Query (With Attachments)

```
┌─────────┐
│ Author  │
└────┬────┘
     │
     │ 1. Click "Add Query"
     ▼
┌─────────────────────────────────┐
│  Query Dialog                    │
│  ┌───────────────────────────┐  │
│  │ Content Input             │  │
│  └───────────────────────────┘  │
│  [✓] Attach Files               │
│  ┌───────────────────────────┐  │
│  │ 📎 Fig1_R3_Final_V2.tif   │  │
│  │ 📄 Supp_Material_R2.pdf   │  │
│  └───────────────────────────┘  │
│  [Save] [Cancel]                │
└──────────┬──────────────────────┘
           │
           │ 2. Select files
           │ 3. Validate files
           ▼
┌─────────────────────────────────┐
│ AttachmentModule.validateFile() │
│                                  │
│ Checks:                          │
│ • File extension valid          │
│ • File size < 100MB             │
│ • Total size < 500MB            │
│ • Not executable type           │
└──────────┬──────────────────────┘
           │
           │ ✓ Valid
           ▼
┌─────────────────────────────────┐
│ AttachmentModule.uploadFiles()  │
│                                  │
│ • Upload to server              │
│ • Get file URLs                 │
│ • Format response               │
└──────────┬──────────────────────┘
           │
           │ Upload complete
           ▼
┌─────────────────────────────────┐
│ QueryBaseModule.createQuery()   │
│                                  │
│ queryData = {                    │
│   content: "...",                │
│   attachments: [                 │
│     {                            │
│       file_sn: "Fig1_R3...",    │
│       file_on: "Fig1_R3...",    │
│       url: "https://..."         │
│     },                           │
│     ...                          │
│   ]                              │
│ }                                │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ DOM Update with Attachments     │
│                                  │
│ <span id="query_xxx"            │
│   data-label="AQ1"              │
│   data-status="open"            │
│   data-file-sn="Fig1...||Supp..."│
│   data-file-on="Fig1...||Supp..."│
│   data-db-id="upload_123">      │
│   [Query Content]                │
│ </span>                          │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ Panel with Attachments           │
│                                  │
│ ┌─────────────────────────────┐ │
│ │ AQ1 [Open]                  │ │
│ │ "Please review figures..."  │ │
│ │ Author • 2 min ago          │ │
│ │ 📎 Attachments (2)          │ │
│ │   • Fig1_R3_Final_V2.tif   │ │
│ │   • Supp_Material_R2.pdf   │ │
│ └─────────────────────────────┘ │
└──────────────────────────────────┘
```

---

## Editor Reply Workflow

```
┌─────────┐
│ Editor  │
└────┬────┘
     │
     │ 1. Click on Query AQ1
     ▼
┌─────────────────────────────────┐
│  Query Dialog (View Mode)        │
│  ┌───────────────────────────┐  │
│  │ Original Query:           │  │
│  │ "Please verify..."        │  │
│  │ - Author                  │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │ Reply Input               │  │
│  └───────────────────────────┘  │
│  [ ] Attach Files               │
│  [✓] Close Query                │
│  [Reply] [Cancel]               │
└──────────┬──────────────────────┘
           │
           │ 2. Enter reply
           │ 3. Click Reply
           ▼
┌─────────────────────────────────┐
│ QueryBaseModule.addResponse()   │
│                                  │
│ responseData = {                 │
│   content: "Verified...",        │
│   user: "editor@...",            │
│   role: "Editor",                │
│   closeQuery: true               │
│ }                                │
│                                  │
│ • Build response object          │
│ • Add to query.responses[]      │
│ • Update query.lastResponse     │
│ • Set status = "closed"         │
│ • Emit "response-added"         │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ DOM Update                       │
│                                  │
│ <span id="query_xxx"            │
│   data-status="closed">         │
│   <span data-name="query">      │
│     [Original Query]             │
│   </span>                        │
│   <span data-name="response"    │
│         data-username="editor"  │
│         data-time="1234567890"> │
│     [Editor Response]            │
│   </span>                        │
│ </span>                          │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ Panel Update                     │
│                                  │
│ ┌─────────────────────────────┐ │
│ │ AQ1 [Closed] ✓              │ │
│ │ "Please verify..."          │ │
│ │ └─ "Verified. Looks good."  │ │
│ │ Author → Editor             │ │
│ └─────────────────────────────┘ │
│                                  │
│ Counts: Total: 1 | Closed: 1    │
└──────────────────────────────────┘
```

---

## Comment Creation Workflow

```
┌─────────┐
│ Author  │
└────┬────┘
     │
     │ 1. Click "Add Comment"
     ▼
┌─────────────────────────────────┐
│  Comment Dialog                  │
│  ┌───────────────────────────┐  │
│  │ Comment Input             │  │
│  └───────────────────────────┘  │
│  [Save] [Cancel]                │
└──────────┬──────────────────────┘
           │
           │ 2. Enter comment
           │ 3. Click Save
           ▼
┌─────────────────────────────────┐
│ QueryBaseModule.createQuery()   │
│                                  │
│ • Set _current_process="comment"│
│ • Generate ID                    │
│ • Set label (C1, C2, etc.)      │
│ • Set status = "comment"        │
│ • Store in _state.comments      │
│ • Emit "query-created"          │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ DOM Update                       │
│                                  │
│ <span id="comment_xxx"          │
│   data-class="ckcommentsfull"   │
│   data-label="C1"               │
│   data-status="comment">        │
│   [Comment Content]              │
│ </span>                          │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ Panel Update (Comments Tab)      │
│                                  │
│ ┌─────────────────────────────┐ │
│ │ C1 💬                       │ │
│ │ "Excellent work..."         │ │
│ │ Author • 1 min ago          │ │
│ └─────────────────────────────┘ │
│                                  │
│ Counts: Comments: 1              │
└──────────────────────────────────┘
```

---

## Filename Pattern Analysis

### Pattern Parsing Flow

```
Input: "Fig1_R3_Final_V2.tif"
           │
           ▼
┌─────────────────────────────────┐
│ parseFilenamePattern()           │
│                                  │
│ Regex Patterns:                  │
│ • /Fig(?:ure)?[_\s]?(\d+)/i     │
│ • /R(\d+)/                       │
│ • /V(\d+)/                       │
│ • /Final/i                       │
│ • /Revised?/i                    │
│ • /Supp(?:lementary)?/i         │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ Parsed Result:                   │
│                                  │
│ {                                │
│   filename: "Fig1_R3_Final_V2.tif"│
│   figureNumber: "1",             │
│   revision: "3",                 │
│   version: "2",                  │
│   isFinal: true,                 │
│   isDraft: false,                │
│   isRevised: false,              │
│   isSupplementary: false,        │
│   extension: "tif",              │
│   isImage: true,                 │
│   isPDF: false,                  │
│   isDocument: false              │
│ }                                │
└──────────────────────────────────┘
```

### Filename Pattern Examples

```
┌─────────────────────────────────────────────────────────────┐
│ Pattern: Fig1_R3_Final_V2.tif                               │
├─────────────────────────────────────────────────────────────┤
│ Figure Number:    1                                         │
│ Revision:         R3                                        │
│ Status:           Final                                     │
│ Version:          V2                                        │
│ Extension:        .tif                                      │
│ Type:             Image                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Pattern: Supplementary_Material_R2.pdf                      │
├─────────────────────────────────────────────────────────────┤
│ Type:             Supplementary                             │
│ Revision:         R2                                        │
│ Extension:        .pdf                                      │
│ Type:             Document                                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Pattern: Chart_Data_v3.png                                  │
├─────────────────────────────────────────────────────────────┤
│ Version:          v3                                        │
│ Extension:        .png                                      │
│ Type:             Image                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## State Management

### Query State Structure

```
_state = {
  queries: Map {
    "query_123" => {
      id: "query_123",
      label: "AQ1",
      status: "open",
      content: "Please verify...",
      user: "author@example.com",
      role: "Author",
      timestamp: 1234567890,
      responses: [
        {
          id: "response_456",
          content: "Verified...",
          user: "editor@example.com",
          role: "Editor",
          timestamp: 1234567900,
          attachments: []
        }
      ],
      attachments: [
        {
          file_sn: "Fig1_R3_Final_V2.tif",
          file_on: "Fig1_R3_Final_V2.tif",
          name: "Fig1_R3_Final_V2.tif",
          url: "https://..."
        }
      ],
      lastResponse: { ... },
      editorEl: <DOM Element>,
      sameUserRole: true
    }
  },
  
  comments: Map {
    "comment_789" => {
      id: "comment_789",
      label: "C1",
      status: "comment",
      content: "Excellent work...",
      ...
    }
  },
  
  counts: {
    total: 1,
    open: 0,
    closed: 1,
    comments: 1
  }
}
```

---

## Event Flow

```
User Action
    │
    ▼
┌─────────────────┐
│ UI Event        │
│ (click, input)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ Module Method       │
│ (createQuery, etc.) │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ State Update        │
│ (_state.queries)    │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ DOM Update          │
│ (editor element)    │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Event Emission      │
│ (query-created)     │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Event Handlers      │
│ (panel refresh)     │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ UI Update           │
│ (panel render)      │
└─────────────────────┘
```

---

## Testing Workflow

```
┌──────────────────┐
│ Playwright Test  │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────┐
│ 1. Setup                     │
│ • Navigate to page          │
│ • Wait for full load        │
│ • Wait for editor ready     │
│ • Wait for query panel ready│
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 2. Execute Test Action       │
│ • Create query/comment      │
│ • Add response              │
│ • Upload attachments        │
│ • Update/delete items       │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 3. Verify Results            │
│ • Check state updated       │
│ • Check DOM updated         │
│ • Check panel updated       │
│ • Check counts correct      │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 4. Cleanup                   │
│ • Take screenshot           │
│ • Log results               │
│ • Reset state (if needed)   │
└─────────────────────────────┘
```

---

## Summary

This workflow diagram illustrates:

1. **Module Architecture** - How QueryBaseModule integrates with sub-modules
2. **Query Creation** - Step-by-step process for creating queries with/without attachments
3. **Editor Replies** - How editors respond to queries
4. **Comment System** - Separate workflow for comments
5. **Filename Patterns** - How attachment filenames are parsed and validated
6. **State Management** - Internal data structure organization
7. **Event Flow** - How actions propagate through the system
8. **Testing** - E2E test execution flow

All workflows support both attachment and non-attachment scenarios with comprehensive validation and error handling.
