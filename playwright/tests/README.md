# IMPACT Editor E2E Tests

Automated end-to-end tests for the IMPACT Editor using **Playwright**.

## 📁 Folder Structure

```
tests/
├── e2e/
│   ├── fixtures/
│   │   ├── test-config.js      # Test configuration and selectors
│   │   └── cjk-test-data.js    # CJK Validator test data
│   ├── helpers/
│   │   └── test-helpers.js     # Helper functions (wait, assertions, CJK, etc.)
│   ├── editor-load.spec.js     # Editor load test file
│   └── cjk-validator.spec.js   # CJK Validator test file
├── reports/
│   ├── html/                   # HTML test reports
│   ├── screenshots/            # Test screenshots
│   └── test-results.json       # JSON test results
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- npm or yarn
- Tomcat server running with IMPACT editor

### Install Dependencies

```bash
npm install
```

### Install Playwright Browsers

```bash
npm run test:install
# or
npx playwright install
```

## 📋 Running Tests

### Run All Tests
```bash
npm test
```

### Run Tests in Headed Mode (see the browser)
```bash
npm run test:headed
```

### Run Tests with UI (Interactive Mode)
```bash
npm run test:ui
```

### Run Tests in Debug Mode
```bash
npm run test:debug
```

### Run Specific Test File
```bash
npx playwright test editor-load.spec.js
npx playwright test cjk-validator.spec.js
```

### Run Specific Test Case
```bash
npx playwright test -g "TC001"
npx playwright test -g "CJK-TC"
```

## 📊 View Test Reports

After running tests:
```bash
npm run test:report
```

## 🛠️ Configuration

### Update Base URL

Edit `playwright.config.js`:
```javascript
use: {
    baseURL: 'http://localhost:8080/impactweb_live',
    // ...
}
```

### Update Test Selectors

Edit `tests/e2e/fixtures/test-config.js` to update:
- URL paths
- Element selectors
- Timeout values
- Test data

## 📝 Test Cases

### Editor Load Tests (editor-load.spec.js)

| Test ID | Description | Status |
|---------|-------------|--------|
| TC001 | Page fully loaded with InitialLoadDialog | ✅ |
| TC002 | Landing page accept button functionality | ✅ |
| TC003 | Editor initialization and ready state | ✅ |
| TC004 | Editor instance count & panel status | ✅ |
| TC005 | Full integration flow | ✅ |

### CJK Validator Tests (cjk-validator.spec.js)

| Test ID | Description | Status |
|---------|-------------|--------|
| CJK-TC001 | CJKValidator class exists and initialized | ✅ |
| CJK-TC002 | Basic CJK ideograph counting | ✅ |
| CJK-TC003 | CJK punctuation exclusion | ✅ |
| CJK-TC004 | Unicode info helper function | ✅ |
| CJK-TC005 | Valid insert tracking | ✅ |
| CJK-TC006 | Valid delete tracking | ✅ |
| CJK-TC007 | Untracked additions detection | ✅ |
| CJK-TC008 | Untracked deletions detection | ✅ |
| CJK-TC009 | Nested del>insert pattern | ✅ |
| CJK-TC010 | Nested insert>del pattern | ✅ |
| CJK-TC011 | Deletion scenario ignore | ✅ |
| CJK-TC012 | debugCJK helper function | ✅ |
| CJK-TC013 | Mixed English/CJK content | ✅ |
| CJK-TC014 | Empty document handling | ✅ |
| CJK-TC015 | Real editor content validation | ✅ |
| CJK-TC016 | Save trigger validation | ✅ |
| CJK-ALERT-001 | Alert dialog integration | ✅ |

### CJK Validator Helper Functions

| Function | Description |
|----------|-------------|
| `waitForCJKValidator()` | Wait for CJKValidator class to be available |
| `runCJKValidation()` | Run validation on current editor content |
| `getCJKValidatorStats()` | Get CJK statistics for current content |
| `triggerCJKValidationAlert()` | Trigger alert dialog for validation failures |
| `storeOriginalContent()` | Store original content for comparison |


## 🔍 Recording Tests

Use Playwright's codegen to record new tests:
```bash
npm run test:codegen
```

This opens a browser where you can:
1. Navigate to your application
2. Perform actions
3. Copy generated code

## ⚙️ Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BASE_URL` | Application base URL | `http://localhost:8080/impactweb_live` |
| `CI` | CI environment flag | `false` |

Example:
```bash
BASE_URL=http://test.example.com npm test
```

## 📸 Screenshots

Screenshots are automatically captured on:
- Test failures
- Named checkpoints (via `takeScreenshot()`)

Location: `tests/reports/screenshots/`

## 🎬 Videos

Videos are captured for failed tests.
Location: `tests/reports/test-results/`

## 🐛 Troubleshooting

### Test Timeout
Increase timeout in test:
```javascript
test.setTimeout(120000); // 120 seconds
```

### Element Not Found
1. Check if selector is correct in `test-config.js`
2. Use `npx playwright codegen` to find correct selector
3. Increase `elementVisible` timeout in config

### Browser Not Installing
```bash
npx playwright install --with-deps chromium
```

## 📚 Resources

- [Playwright Documentation](https://playwright.dev/docs/intro)
- [Playwright API Reference](https://playwright.dev/docs/api/class-playwright)
- [Locator Strategies](https://playwright.dev/docs/locators)
