# Query & Comment Workflow Test Suite

## Overview
Comprehensive E2E test suite for the QueryBaseModule workflow including attachment handling with various filename patterns.

## Test Coverage

### Test Cases

#### TC-QW-001: Create Query Without Attachments
**Objective:** Verify that an author can create a query without attachments

**Steps:**
1. Get initial query count
2. Create query with content only
3. Verify query created successfully
4. Verify counts updated correctly

**Expected Results:**
- Query created with status "open"
- Total query count increases by 1
- Open query count increases by 1
- No attachments present

---

#### TC-QW-002: Create Comment Without Attachments
**Objective:** Verify that an author can create a comment without attachments

**Steps:**
1. Get initial comment count
2. Set process to "comment"
3. Create comment with content only
4. Verify comment created successfully

**Expected Results:**
- Comment created with status "comment"
- Comment count increases by 1
- No attachments present

---

#### TC-QW-003: Create Query With Single Image Attachment
**Objective:** Verify query creation with single TIF image attachment

**Test Data:**
- Filename: `Fig1_R3_Final_V2.tif`

**Steps:**
1. Create mock attachment with TIF file
2. Create query with attachment
3. Verify attachment metadata
4. Verify filename pattern parsing

**Expected Results:**
- Query created successfully
- Attachment count = 1
- Filename pattern correctly parsed:
  - Revision: R3
  - Version: V2
  - Has "Final" keyword
  - Extension: .tif

---

#### TC-QW-004: Create Query With Multiple Mixed Attachments
**Objective:** Verify query creation with multiple attachments of different types

**Test Data:**
- `Fig1_R3_Final_V2.tif` (Image)
- `Supplementary_Material_R2.pdf` (PDF)
- `Chart_Data_v3.png` (Image)

**Steps:**
1. Create multiple mock attachments
2. Create query with all attachments
3. Verify attachment count
4. Analyze attachment patterns

**Expected Results:**
- Query created successfully
- Attachment count = 3
- Correct file type detection (2 images, 1 PDF)
- Pattern analysis shows revision/version info

---

#### TC-QW-005: Editor Replies to Query Without Attachments
**Objective:** Verify editor can reply to query without attachments

**Steps:**
1. Create initial query (author)
2. Add response (editor)
3. Verify response added
4. Verify query status changed to "closed"

**Expected Results:**
- Response added successfully
- Response count = 1
- Query status = "closed"
- No attachments in response

---

#### TC-QW-006: Editor Replies With PDF Attachment
**Objective:** Verify editor can reply with PDF attachment

**Test Data:**
- Filename: `Supplementary_Material_R2.pdf`

**Steps:**
1. Create initial query
2. Add response with PDF attachment
3. Verify attachment added
4. Verify filename pattern

**Expected Results:**
- Response added successfully
- Attachment count = 1
- Extension = .pdf
- Filename contains "Supplementary" and "R2"

---

#### TC-QW-007: Validate Filename Patterns
**Objective:** Verify filename pattern parsing for various formats

**Test Data:**
```javascript
[
  { file: 'Fig1_R3_Final_V2.tif', revision: 'R3', version: 'V2', hasFinal: true },
  { file: 'Fig1Final_V2.tif', revision: null, version: 'V2', hasFinal: true },
  { file: 'Figure_2_Revised.jpg', revision: null, version: null, hasFinal: false },
  { file: 'Supplementary_Material_R2.pdf', revision: 'R2', version: null, hasFinal: false }
]
```

**Expected Results:**
- All patterns parsed correctly
- Revision numbers extracted when present
- Version numbers extracted when present
- Keywords (Final, Revised, Supplementary) detected

---

#### TC-QW-008: Update Query With Attachments
**Objective:** Verify author can update query to add attachments

**Steps:**
1. Create query without attachments
2. Update query to add attachment
3. Verify attachment added
4. Verify content updated

**Expected Results:**
- Query updated successfully
- Attachment count changes from 0 to 1
- Content updated correctly

---

#### TC-QW-009: Delete Response With Attachments
**Objective:** Verify response with attachments can be deleted

**Steps:**
1. Create query
2. Add response with attachment
3. Delete response
4. Verify response removed
5. Verify query status reverted

**Expected Results:**
- Response deleted successfully
- Response count = 0
- Query status reverted to "open"
- Attachment properly cleaned up

---

#### TC-QW-010: Attachment Module Integration
**Objective:** Verify AttachmentModule is properly integrated

**Checks:**
- AttachmentModule exists
- setupFileInput method available
- validateFile method available
- uploadFiles method available
- formatAttachmentResponse method available
- normalizeAttachments method available

**Expected Results:**
- All methods present and accessible
- Module properly initialized

---

## Filename Pattern Specifications

### Supported Patterns

#### Revision Patterns
- `R1`, `R2`, `R3`, etc.
- Example: `Figure_R2.tif`

#### Version Patterns
- `V1`, `V2`, `V3`, etc.
- `v1`, `v2`, `v3`, etc.
- Example: `Document_V2.pdf`

#### Status Keywords
- `Final` - Final version
- `Draft` - Draft version
- `Revised` - Revised version
- `Updated` - Updated version

#### Figure Patterns
- `Fig1`, `Fig2`, `Figure_1`, `Figure_2`
- Example: `Fig1_R3_Final_V2.tif`

#### Supplementary Patterns
- `Supplementary`, `Supp`
- Example: `Supplementary_Material_R2.pdf`

### Complex Pattern Examples

```
Fig1_R3_Final_V2.tif
├─ Figure: 1
├─ Revision: R3
├─ Status: Final
├─ Version: V2
└─ Extension: .tif

Supplementary_Material_R2.pdf
├─ Type: Supplementary
├─ Revision: R2
└─ Extension: .pdf

Chart_Data_v3.png
├─ Version: v3
└─ Extension: .png

Figure_2_Revised.jpg
├─ Figure: 2
├─ Status: Revised
└─ Extension: .jpg
```

---

## File Type Support

### Images
- `.tif`, `.tiff` - TIFF images
- `.jpg`, `.jpeg` - JPEG images
- `.png` - PNG images
- `.gif` - GIF images
- `.bmp` - Bitmap images
- `.svg` - SVG vector images

### Documents
- `.pdf` - PDF documents
- `.doc` - Microsoft Word (legacy)
- `.docx` - Microsoft Word
- `.odt` - OpenDocument Text
- `.rtf` - Rich Text Format

### Validation Rules
- Maximum single file size: 100 MB
- Maximum total size (multiple files): 500 MB
- Invalid extensions: `.exe`, `.bat`, `.cmd`, `.sh`, `.dll`

---

## Running the Tests

### Prerequisites
```bash
npm install @playwright/test
```

### Run All Tests
```bash
npx playwright test tests/e2e/query-workflow.spec.js
```

### Run Specific Test
```bash
npx playwright test tests/e2e/query-workflow.spec.js -g "TC-QW-001"
```

### Run in Debug Mode
```bash
npx playwright test tests/e2e/query-workflow.spec.js --debug
```

### Generate Report
```bash
npx playwright test tests/e2e/query-workflow.spec.js --reporter=html
```

---

## Test Data

### Mock Attachments
Test files are mocked and don't require actual file uploads. The test suite uses:

```javascript
const TEST_FILES = {
    images: {
        tif: 'Fig1_R3_Final_V2.tif',
        tif_alt: 'Fig1Final_V2.tif',
        jpg: 'Figure_2_Revised.jpg',
        png: 'Chart_Data_v3.png'
    },
    documents: {
        pdf: 'Supplementary_Material_R2.pdf',
        pdf_alt: 'References_Updated.pdf',
        doc: 'Manuscript_Draft_v4.doc',
        docx: 'Author_Response.docx'
    },
    mixed: [
        'Fig1_R3_Final_V2.tif',
        'Supplementary_Material_R2.pdf',
        'Chart_Data_v3.png'
    ]
};
```

---

## Helper Functions

### Attachment Helpers
Located in `tests/e2e/helpers/attachment-helpers.js`

#### generateMockAttachment(filename, options)
Creates mock attachment object for testing

#### parseFilenamePattern(filename)
Parses filename to extract metadata (revision, version, etc.)

#### validateFileAgainstRules(file, rules)
Validates file against size and extension rules

#### getTestFilePatterns()
Returns comprehensive set of test file patterns

#### verifyAttachmentRendering(page, queryId)
Verifies attachment is properly rendered in DOM

---

## Troubleshooting

### Common Issues

#### Test Timeout
If tests timeout, increase the timeout value:
```javascript
test.setTimeout(180000); // 3 minutes
```

#### Module Not Initialized
Ensure `waitForQueryPanelReady()` completes before running tests:
```javascript
await waitForQueryPanelReady(page);
```

#### Attachment Upload Fails
Check that `AttachmentModule` is properly initialized:
```javascript
const moduleCheck = await page.evaluate(() => {
    return !!window.queryModule?.attachmentModule;
});
```

---

## CI/CD Integration

### GitHub Actions Example
```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: npx playwright install
      - run: npx playwright test tests/e2e/query-workflow.spec.js
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
```

---

## Future Enhancements

### Planned Test Cases
- [ ] TC-QW-011: Bulk attachment upload
- [ ] TC-QW-012: Attachment download verification
- [ ] TC-QW-013: Attachment deletion with confirmation
- [ ] TC-QW-014: Invalid file type rejection
- [ ] TC-QW-015: File size limit validation
- [ ] TC-QW-016: Concurrent attachment uploads
- [ ] TC-QW-017: Attachment preview functionality
- [ ] TC-QW-018: Attachment metadata editing

---

## References

- [Playwright Documentation](https://playwright.dev/)
- [Query Module Source](../../src/js/query.js)
- [Test Helpers](./helpers/test-helpers.js)
- [Attachment Helpers](./helpers/attachment-helpers.js)
