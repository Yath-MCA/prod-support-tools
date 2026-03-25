# How to Run Tests (IMPACT E2E)

## 1) Prerequisites

- Node.js + npm installed
- Playwright browsers installed
- Local app available at configured `baseURL` (usually localhost)

## 2) Verify npm registry and local install

Run these commands from project root:

```bash
npm config get registry
npm install
npm run test:install
```

Expected registry:

```text
https://registry.npmjs.org/
```

> In this workspace, `node_modules/` and `package-lock.json` already exist, so local npm dependencies are present.

## 3) Quick run commands

### Core Playwright

```bash
npm test
npm run test:ui
npm run test:headed
npm run test:debug
```

### Module-wise

```bash
npm run test:module:query
npm run test:module:comment
npm run test:module:query-comment
```

### Insert Comment Basic (TC_IC_001 to TC_IC_010)

```bash
npm run test:insert-comment:basic
```

### Workflow runs

```bash
npm run test:workflow:basic
npm run test:workflow:regression
npm run test:workflow:full
```

### Execution matrix

Dry run (preview command):

```bash
npm run test:matrix:dry -- --workflow author-editor-collator --role Author --testingType comment-basic --browser chrome
```

Actual run:

```bash
npm run test:matrix -- --workflow author-editor-collator --role Author --testingType comment-basic --browser chrome
npm run test:matrix -- --workflow editor-author-collator --role Editor --testingType query-regression --browser edge
npm run test:matrix -- --workflow author-editor-collator --role Collator --testingType all-regression --browser firebox
```

## 4) Run single specs directly (useful for smoke)

```bash
npx playwright test tests/e2e/query-workflow.spec.js
npx playwright test tests/e2e/query-comment.spec.js
npx playwright test tests/e2e/cjk-validator.spec.js
npx playwright test tests/e2e/landing-editor-module-basic.spec.js
npx playwright test tests/e2e/landing-to-editor6.spec.js
```

## 5) Reports

Open HTML report:

```bash
npm run test:report
```

Typical artifacts:

- `tests/reports/...` (date/time based folders)
- `test-results/...`
- module/workflow custom JSON/CSV status files in `tests/reports/module-status` and `tests/reports/workflow-status`

## 6) Troubleshooting

### `ERR_CONNECTION_REFUSED`

- Ensure local server is running and `baseURL` is correct.

### Stuck on landing page

- Some flows require clicking `AGREE & CONTINUE`/accept before editor loads.

### Browser project mismatch

- Use default Chromium first.
- For Edge use configured Playwright project/channel.
- Opera/Brave require custom Playwright project with `executablePath`.

## 7) Recommended smoke order

```bash
npm run test:workflow:basic
npm run test:insert-comment:basic
npm run test:module:query-comment
```

Then scale to:

```bash
npm run test:workflow:regression
npm run test:workflow:full
```
