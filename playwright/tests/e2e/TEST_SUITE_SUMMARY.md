# Query Workflow Test Suite - Summary

## 📦 What Was Created

### Test Files
1. **`query-workflow.spec.js`** - Main test suite with 10 comprehensive test cases
2. **`attachment-helpers.js`** - Helper utilities for attachment testing
3. **`QUERY_WORKFLOW_TESTS.md`** - Detailed test documentation
4. **`WORKFLOW_DIAGRAM.md`** - Visual workflow diagrams (ASCII art)
5. **`README_QUICK_START.md`** - Quick start guide

---

## 🎯 Test Coverage

### Test Cases Overview

| ID | Test Case | Type | Attachments | Status |
|----|-----------|------|-------------|--------|
| TC-QW-001 | Create query without attachments | Query | ❌ | ✅ Ready |
| TC-QW-002 | Create comment without attachments | Comment | ❌ | ✅ Ready |
| TC-QW-003 | Create query with single TIF image | Query | ✅ 1 file | ✅ Ready |
| TC-QW-004 | Create query with multiple mixed files | Query | ✅ 3 files | ✅ Ready |
| TC-QW-005 | Editor reply without attachments | Reply | ❌ | ✅ Ready |
| TC-QW-006 | Editor reply with PDF attachment | Reply | ✅ 1 file | ✅ Ready |
| TC-QW-007 | Validate filename patterns | Validation | ✅ Multiple | ✅ Ready |
| TC-QW-008 | Update query to add attachments | Update | ✅ 1 file | ✅ Ready |
| TC-QW-009 | Delete response with attachments | Delete | ✅ 1 file | ✅ Ready |
| TC-QW-010 | Verify AttachmentModule integration | Integration | N/A | ✅ Ready |

---

## 📋 Filename Patterns Tested

### Pattern Categories

#### 1. Revision Patterns
```
Fig1_R3_Final_V2.tif          → R3 (Revision 3)
Supplementary_Material_R2.pdf → R2 (Revision 2)
Graph_Results_R1.jpg          → R1 (Revision 1)
```

#### 2. Version Patterns
```
Fig1Final_V2.tif              → V2 (Version 2)
Chart_Data_v3.png             → v3 (Version 3)
Manuscript_Draft_v4.doc       → v4 (Version 4)
```

#### 3. Status Keywords
```
Fig1_R3_Final_V2.tif          → Final
Manuscript_Draft_v4.doc       → Draft
Figure_2_Revised.jpg          → Revised
References_Updated.pdf        → Updated
```

#### 4. Type Identifiers
```
Fig1_R3_Final_V2.tif          → Figure 1
Supplementary_Material_R2.pdf → Supplementary
Chart_Data_v3.png             → Chart
```

### Supported File Extensions

**Images:**
- `.tif`, `.tiff` - TIFF images
- `.jpg`, `.jpeg` - JPEG images
- `.png` - PNG images
- `.gif` - GIF images
- `.bmp` - Bitmap images
- `.svg` - SVG vector images

**Documents:**
- `.pdf` - PDF documents
- `.doc` - Microsoft Word (legacy)
- `.docx` - Microsoft Word
- `.odt` - OpenDocument Text
- `.rtf` - Rich Text Format

---

## 🔧 Helper Functions

### Attachment Helpers (`attachment-helpers.js`)

```javascript
// Generate mock attachment
generateMockAttachment(filename, options)

// Parse filename pattern
parseFilenamePattern(filename)
// Returns: { revision, version, isFinal, extension, isImage, isPDF, ... }

// Validate file against rules
validateFileAgainstRules(file, rules)

// Get test file patterns
getTestFilePatterns()

// Wait for upload completion
waitForAttachmentUpload(page, storeId, timeout)

// Get attachment store status
getAttachmentStoreStatus(page, storeId)

// Simulate file selection
simulateFileSelection(page, storeId, mockFiles)

// Verify attachment rendering
verifyAttachmentRendering(page, queryId)

// Test download functionality
testAttachmentDownload(page, attachmentUrl)
```

---

## 🚀 Quick Start Commands

### Basic Usage
```bash
# Install dependencies
npm install @playwright/test
npx playwright install

# Run all tests
npx playwright test tests/e2e/query-workflow.spec.js

# Run specific test
npx playwright test tests/e2e/query-workflow.spec.js -g "TC-QW-003"

# Debug mode
npx playwright test tests/e2e/query-workflow.spec.js --debug

# Generate report
npx playwright test tests/e2e/query-workflow.spec.js --reporter=html
npx playwright show-report
```

### Advanced Usage
```bash
# Parallel execution
npx playwright test tests/e2e/query-workflow.spec.js --workers=4

# Headed mode (see browser)
npx playwright test tests/e2e/query-workflow.spec.js --headed

# Specific browser
npx playwright test tests/e2e/query-workflow.spec.js --project=chromium

# With trace
npx playwright test tests/e2e/query-workflow.spec.js --trace on
```

---

## 📊 Test Workflow

### Author Creates Query (With Attachments)

```
1. Author clicks "Add Query"
   ↓
2. Query Dialog opens
   ↓
3. Author enters content
   ↓
4. Author selects files:
   - Fig1_R3_Final_V2.tif
   - Supplementary_Material_R2.pdf
   ↓
5. AttachmentModule validates files:
   ✓ Extension valid
   ✓ Size < 100MB
   ✓ Not executable
   ↓
6. Files uploaded to server
   ↓
7. QueryBaseModule.createQuery() called
   ↓
8. Query stored in _state.queries
   ↓
9. DOM updated with query element
   ↓
10. Panel refreshed
   ↓
11. Event "query-created" emitted
```

### Editor Replies to Query

```
1. Editor clicks on Query AQ1
   ↓
2. Query Dialog opens (view mode)
   ↓
3. Editor enters reply
   ↓
4. Editor optionally attaches files
   ↓
5. Editor checks "Close Query"
   ↓
6. QueryBaseModule.addResponse() called
   ↓
7. Response added to query.responses[]
   ↓
8. Query status changed to "closed"
   ↓
9. DOM updated
   ↓
10. Panel refreshed
   ↓
11. Event "response-added" emitted
```

---

## 🧪 Test Execution Flow

```
Test Start
    ↓
beforeEach Hook
    ├─ Navigate to page
    ├─ Wait for full load
    ├─ Click accept button
    ├─ Wait for editor ready
    └─ Wait for query panel ready
    ↓
Test Execution
    ├─ Get initial state
    ├─ Perform action (create/update/delete)
    ├─ Verify state updated
    ├─ Verify DOM updated
    ├─ Verify panel updated
    └─ Take screenshot
    ↓
Test Complete
```

---

## ✅ Validation Checks

### State Synchronization
- ✓ DOM count matches state count
- ✓ Panel count matches state count
- ✓ Individual query status matches
- ✓ Attachment data synchronized

### Attachment Validation
- ✓ File extension allowed
- ✓ File size within limits
- ✓ Filename pattern parsed correctly
- ✓ Attachment rendered in DOM
- ✓ Attachment visible in panel

### Query/Comment Lifecycle
- ✓ Created with correct status
- ✓ Updated successfully
- ✓ Responses added correctly
- ✓ Deleted properly (soft/hard delete)
- ✓ Events emitted correctly

---

## 📈 Expected Results

### Successful Test Run
```
Running 10 tests using 1 worker

🚀 Starting TC-QW-001: Create Query Without Attachments
ℹ️  Initial query count: 0
✅ Query created: AQ1
✅ TC-QW-001 PASSED

🚀 Starting TC-QW-002: Create Comment Without Attachments
✅ TC-QW-002 PASSED

🚀 Starting TC-QW-003: Create Query With Single Image
ℹ️  Testing with filename: Fig1_R3_Final_V2.tif
✅ Query created with attachment: Fig1_R3_Final_V2.tif
✅ TC-QW-003 PASSED

... (7 more tests)

✅ 10 passed (48s)
```

---

## 🐛 Common Issues & Solutions

### Issue 1: Test Timeout
**Symptom**: Test times out waiting for module

**Solution**:
```javascript
test.setTimeout(180000); // Increase timeout
await waitForQueryPanelReady(page); // Ensure proper wait
```

### Issue 2: Module Not Found
**Symptom**: `queryModule not available` error

**Solution**:
```javascript
// Verify module exists
const exists = await page.evaluate(() => !!window.queryModule);
if (!exists) {
    await page.waitForFunction(() => !!window.queryModule, { timeout: 30000 });
}
```

### Issue 3: Attachment Upload Fails
**Symptom**: Attachment validation fails

**Solution**:
```javascript
// Check AttachmentModule
const moduleCheck = await page.evaluate(() => ({
    exists: !!window.queryModule?.attachmentModule,
    hasValidate: typeof window.queryModule?.attachmentModule?.validateFile === 'function'
}));
```

---

## 📚 Documentation Files

### 1. QUERY_WORKFLOW_TESTS.md
- Detailed test case descriptions
- Expected results for each test
- Filename pattern specifications
- File type support matrix
- Troubleshooting guide

### 2. WORKFLOW_DIAGRAM.md
- System architecture diagram
- Query creation workflow
- Editor reply workflow
- Comment creation workflow
- Filename pattern analysis
- State management structure
- Event flow diagram

### 3. README_QUICK_START.md
- Quick start commands
- Test execution options
- Debugging tips
- CI/CD integration examples
- Common use cases

---

## 🎯 Key Features

### Comprehensive Coverage
- ✅ 10 test cases covering all major workflows
- ✅ Both attachment and non-attachment scenarios
- ✅ Multiple file types (images, PDFs, documents)
- ✅ Various filename patterns tested
- ✅ State synchronization validation

### Realistic Testing
- ✅ Mock attachments with realistic filenames
- ✅ Pattern parsing validation
- ✅ File size and extension validation
- ✅ Multi-file upload scenarios
- ✅ Update and delete operations

### Developer-Friendly
- ✅ Clear test names and descriptions
- ✅ Detailed logging with emojis
- ✅ Automatic screenshots on completion
- ✅ Comprehensive error messages
- ✅ Easy to extend and customize

---

## 🔄 Integration Points

### QueryBaseModule Methods Tested
```javascript
- createQuery()
- updateQueryOrCommentItem()
- deleteQueryOrComment()
- addResponse()
- updateResponse()
- deleteResponse()
- getQuery()
- getCounts()
```

### AttachmentModule Methods Tested
```javascript
- setupFileInput()
- validateFile()
- uploadFiles()
- formatAttachmentResponse()
- normalizeAttachments()
```

### Events Tested
```javascript
- query-created
- query-updated
- query-deleted
- response-added
- response-updated
- response-deleted
```

---

## 🚀 Next Steps

### Immediate Actions
1. ✅ Review test files created
2. ✅ Install Playwright dependencies
3. ✅ Run tests to verify setup
4. ✅ Review test results

### Future Enhancements
- [ ] Add tests for bulk operations
- [ ] Add tests for concurrent users
- [ ] Add tests for network failures
- [ ] Add tests for large file uploads
- [ ] Add visual regression tests
- [ ] Add performance benchmarks

---

## 📞 Support

### Resources
- **Playwright Docs**: https://playwright.dev/
- **Source Code**: `src/js/query.js`
- **Test Helpers**: `tests/e2e/helpers/test-helpers.js`
- **Attachment Helpers**: `tests/e2e/helpers/attachment-helpers.js`

### Getting Help
1. Check documentation files
2. Review workflow diagrams
3. Run tests in debug mode
4. Check console logs
5. Review screenshots

---

## ✨ Summary

You now have a **complete, production-ready test suite** for the QueryBaseModule workflow including:

✅ **10 comprehensive test cases**
✅ **Attachment handling with realistic filename patterns**
✅ **Helper utilities for easy testing**
✅ **Detailed documentation and diagrams**
✅ **Quick start guide for immediate use**
✅ **CI/CD integration examples**

**All tests are ready to run!** 🎉

```bash
npx playwright test tests/e2e/query-workflow.spec.js
```

---

**Created**: 2026-02-07
**Version**: 1.0
**Status**: ✅ Ready for Production
