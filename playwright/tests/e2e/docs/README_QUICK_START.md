# Query Workflow Tests - Quick Start Guide

## 📋 Overview

This test suite validates the QueryBaseModule workflow including:
- ✅ Query creation (with/without attachments)
- ✅ Comment creation
- ✅ Editor replies
- ✅ Attachment handling (images, PDFs, documents)
- ✅ Filename pattern validation (`Fig1_R3_Final_V2.tif`, etc.)
- ✅ State synchronization

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
npm install @playwright/test
npx playwright install
```

### 2. Run All Tests
```bash
npx playwright test tests/e2e/query-workflow.spec.js
```

### 3. Run Specific Test
```bash
# Run by test name
npx playwright test tests/e2e/query-workflow.spec.js -g "TC-QW-001"

# Run by pattern
npx playwright test tests/e2e/query-workflow.spec.js -g "attachment"
```

### 4. Debug Mode
```bash
npx playwright test tests/e2e/query-workflow.spec.js --debug
```

### 5. View Report
```bash
npx playwright test tests/e2e/query-workflow.spec.js --reporter=html
npx playwright show-report
```

---

## 📁 Test Files

```
tests/e2e/
├── query-workflow.spec.js          # Main test suite (10 test cases)
├── query-comment.spec.js           # Existing sync tests
├── helpers/
│   ├── test-helpers.js             # Core helper functions
│   └── attachment-helpers.js       # Attachment-specific helpers
├── fixtures/
│   └── test-config.js              # Test configuration
├── QUERY_WORKFLOW_TESTS.md         # Detailed test documentation
├── WORKFLOW_DIAGRAM.md             # Visual workflow diagrams
└── README_QUICK_START.md           # This file
```

---

## 🧪 Test Cases

| Test ID | Description | Attachments |
|---------|-------------|-------------|
| TC-QW-001 | Create query without attachments | ❌ |
| TC-QW-002 | Create comment without attachments | ❌ |
| TC-QW-003 | Create query with single TIF image | ✅ |
| TC-QW-004 | Create query with multiple mixed files | ✅ |
| TC-QW-005 | Editor reply without attachments | ❌ |
| TC-QW-006 | Editor reply with PDF attachment | ✅ |
| TC-QW-007 | Validate filename patterns | ✅ |
| TC-QW-008 | Update query to add attachments | ✅ |
| TC-QW-009 | Delete response with attachments | ✅ |
| TC-QW-010 | Verify AttachmentModule integration | N/A |

---

## 📝 Filename Patterns Tested

### Image Files
```
Fig1_R3_Final_V2.tif       ✓ Revision R3, Version V2, Final
Fig1Final_V2.tif           ✓ Version V2, Final
Figure_2_Revised.jpg       ✓ Revised status
Chart_Data_v3.png          ✓ Version v3
```

### Document Files
```
Supplementary_Material_R2.pdf   ✓ Supplementary, Revision R2
References_Updated.pdf          ✓ Updated status
Manuscript_Draft_v4.doc         ✓ Draft, Version v4
Author_Response.docx            ✓ Standard document
```

### Pattern Components
- **Revision**: `R1`, `R2`, `R3`, etc.
- **Version**: `V1`, `V2`, `v3`, etc.
- **Status**: `Final`, `Draft`, `Revised`, `Updated`
- **Type**: `Figure`, `Supplementary`, `Chart`, etc.

---

## 🔧 Configuration

### Test Timeouts
```javascript
test.setTimeout(180000); // 3 minutes for attachment tests
```

### File Size Limits
- Single file: 100 MB
- Multiple files total: 500 MB

### Supported Extensions
- **Images**: `.tif`, `.tiff`, `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.svg`
- **Documents**: `.pdf`, `.doc`, `.docx`, `.odt`, `.rtf`

---

## 📊 Test Execution

### Parallel Execution
```bash
# Run tests in parallel (faster)
npx playwright test tests/e2e/query-workflow.spec.js --workers=4
```

### Sequential Execution
```bash
# Run tests one at a time (more stable)
npx playwright test tests/e2e/query-workflow.spec.js --workers=1
```

### Headed Mode (See Browser)
```bash
npx playwright test tests/e2e/query-workflow.spec.js --headed
```

### Specific Browser
```bash
# Chromium only
npx playwright test tests/e2e/query-workflow.spec.js --project=chromium

# All browsers
npx playwright test tests/e2e/query-workflow.spec.js --project=chromium --project=firefox --project=webkit
```

---

## 🐛 Debugging

### Debug Specific Test
```bash
npx playwright test tests/e2e/query-workflow.spec.js -g "TC-QW-003" --debug
```

### Trace Viewer
```bash
# Record trace
npx playwright test tests/e2e/query-workflow.spec.js --trace on

# View trace
npx playwright show-trace trace.zip
```

### Screenshots
Screenshots are automatically saved to `tests/reports/screenshots/` on test completion.

### Console Logs
Enable verbose logging:
```bash
DEBUG=pw:api npx playwright test tests/e2e/query-workflow.spec.js
```

---

## ✅ Expected Output

### Successful Test Run
```
Running 10 tests using 1 worker

  ✓ TC-QW-001 - Author creates query without attachments (5s)
  ✓ TC-QW-002 - Author creates comment without attachments (4s)
  ✓ TC-QW-003 - Author creates query with single TIF image (6s)
  ✓ TC-QW-004 - Author creates query with multiple mixed attachments (7s)
  ✓ TC-QW-005 - Editor replies to query without attachments (5s)
  ✓ TC-QW-006 - Editor replies with PDF attachment (6s)
  ✓ TC-QW-007 - Validate various filename patterns (3s)
  ✓ TC-QW-008 - Author updates query to add attachments (5s)
  ✓ TC-QW-009 - Delete response containing attachments (5s)
  ✓ TC-QW-010 - Verify AttachmentModule integration (2s)

  10 passed (48s)
```

---

## 🔍 Troubleshooting

### Test Timeout
**Problem**: Test times out waiting for module initialization

**Solution**:
```javascript
// Increase timeout in test file
test.setTimeout(180000); // 3 minutes
```

### Module Not Found
**Problem**: `queryModule not available` error

**Solution**:
```javascript
// Ensure proper wait
await waitForQueryPanelReady(page);

// Verify module exists
const exists = await page.evaluate(() => !!window.queryModule);
console.log('Module exists:', exists);
```

### Attachment Upload Fails
**Problem**: Attachment validation or upload fails

**Solution**:
```javascript
// Check AttachmentModule
const moduleCheck = await page.evaluate(() => {
    return {
        exists: !!window.queryModule?.attachmentModule,
        methods: Object.keys(window.queryModule?.attachmentModule || {})
    };
});
console.log('AttachmentModule:', moduleCheck);
```

### DOM Not Updated
**Problem**: Query created but not visible in panel

**Solution**:
```javascript
// Add explicit wait
await page.waitForTimeout(1000);

// Verify DOM element
const exists = await page.evaluate((id) => {
    return !!document.getElementById(id);
}, queryId);
```

---

## 📈 CI/CD Integration

### GitHub Actions
```yaml
name: Query Workflow Tests

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
      - run: npx playwright install --with-deps
      - run: npx playwright test tests/e2e/query-workflow.spec.js
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 30
```

---

## 📚 Additional Resources

- **Detailed Documentation**: [QUERY_WORKFLOW_TESTS.md](./QUERY_WORKFLOW_TESTS.md)
- **Workflow Diagrams**: [WORKFLOW_DIAGRAM.md](./WORKFLOW_DIAGRAM.md)
- **Playwright Docs**: https://playwright.dev/
- **Source Code**: `../../src/js/query.js`

---

## 🎯 Common Use Cases

### Test Single Functionality
```bash
# Test only attachment handling
npx playwright test tests/e2e/query-workflow.spec.js -g "attachment"

# Test only creation
npx playwright test tests/e2e/query-workflow.spec.js -g "create"

# Test only replies
npx playwright test tests/e2e/query-workflow.spec.js -g "reply"
```

### Generate Test Report
```bash
# HTML report
npx playwright test tests/e2e/query-workflow.spec.js --reporter=html

# JSON report
npx playwright test tests/e2e/query-workflow.spec.js --reporter=json

# JUnit report (for CI)
npx playwright test tests/e2e/query-workflow.spec.js --reporter=junit
```

### Watch Mode (Re-run on Changes)
```bash
npx playwright test tests/e2e/query-workflow.spec.js --watch
```

---

## 💡 Tips

1. **Run tests in headed mode first** to see what's happening
2. **Use screenshots** to debug visual issues
3. **Check console logs** for JavaScript errors
4. **Verify module initialization** before running tests
5. **Use trace viewer** for complex debugging scenarios

---

## 🆘 Getting Help

If tests fail:

1. Check the screenshot in `tests/reports/screenshots/`
2. Review console logs for errors
3. Run in debug mode: `--debug`
4. Check module initialization: `window.queryModule`
5. Verify DOM elements exist
6. Check network requests in browser DevTools

---

## ✨ Next Steps

After running tests successfully:

1. Review test coverage
2. Add custom test cases for your use case
3. Integrate with CI/CD pipeline
4. Set up automated test runs
5. Monitor test results over time

---

**Happy Testing! 🎉**
