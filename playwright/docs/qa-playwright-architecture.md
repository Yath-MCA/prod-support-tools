# QA Test Architecture: Playwright (TypeScript) + BrowserStack + Supabase

## Overview

This document covers the complete QA pipeline for testing a WebApp with dynamic content, CKEditor, and 2-way binding — using Playwright (TypeScript) as the primary test framework, integrated with Google Sheets (master test case management), BrowserStack (cross-browser testing), Supabase (result storage), and CSV export.

---

## Why Playwright (TypeScript)

| Your App Feature | Why TS Wins |
|---|---|
| CKEditor | `page.evaluate(() => editor.getData())` — direct JS API access |
| 2-way binding TOC ↔ thumbnail | `page.waitForFunction()` watches DOM state natively |
| Dynamic landing page | Auto-wait built-in, no `Thread.sleep` |
| Google Sheets read/write | `googleapis` npm — 5 lines vs Java's 50 |
| Supabase insert | Official `@supabase/supabase-js` SDK |
| HTML report | Built-in Playwright reporter |

---

## Data Flow Architecture

```
Google Sheet (QA master)
        ↓  googleapis read at test start
  Test Data Layer — fetchTestCases() → TestCase[]
        ↓  each test tagged with TC_ID
  Playwright Test Suite
        ↓                    ↓
  Local browsers       BrowserStack
  Chrome/Firefox/Safari    Cross-browser · real devices
        ↓                    ↓
         test-results.json (Playwright native + TC_IDs)
        ↓           ↓              ↓
  results.csv   Supabase DB    HTML report
                    ↓
           Sheet writeback (Pass/Fail per TC_ID row)
```

---

## Project Structure

```
playwright-webapp-tests/
├── playwright.config.ts
├── browserstack.config.ts
├── .env
│
├── src/
│   ├── sheets/
│   │   └── googleSheets.ts        # Read TC metadata, write results back
│   │
│   ├── db/
│   │   └── supabase.ts            # Insert run results
│   │
│   ├── reporters/
│   │   └── csvReporter.ts         # JSON → CSV transformer
│   │
│   ├── pages/                     # Page Object Models
│   │   ├── LandingPage.ts
│   │   ├── EditorPage.ts
│   │   └── CKEditorPage.ts        # CKEditor-specific helpers
│   │
│   └── utils/
│       └── testMapper.ts          # Maps TC_ID → test result
│
├── tests/
│   ├── landing/
│   │   └── dynamic-content.spec.ts
│   ├── editor/
│   │   ├── toc-thumbnail.spec.ts
│   │   └── two-way-binding.spec.ts
│   └── ckeditor/
│       └── editor-modules.spec.ts
│
├── test-results/                  # Auto-generated
│   ├── results.json
│   └── results.csv
│
└── scripts/
    └── posttest.ts                # Runs after suite: CSV + Supabase + Sheet writeback
```

---

## Setup

```bash
mkdir playwright-webapp-tests && cd playwright-webapp-tests
npm init -y
npm install -D @playwright/test typescript ts-node
npm install googleapis @supabase/supabase-js csv-writer dotenv
npx playwright install
```

### `.env`

```env
BROWSERSTACK_USERNAME=your_username
BROWSERSTACK_ACCESS_KEY=your_access_key
BASE_URL=https://your-app.com
GOOGLE_SHEET_ID=your_sheet_id
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
```

### `package.json` scripts

```json
{
  "scripts": {
    "test":       "npx playwright test",
    "test:bs":    "npx playwright test --config=browserstack.config.ts",
    "posttest":   "ts-node scripts/posttest.ts",
    "report":     "npx playwright show-report"
  }
}
```

> `posttest` runs **automatically** after every `npm test` — zero manual steps.

---

## Configuration

### `playwright.config.ts` (Local)

```typescript
import { defineConfig, devices } from '@playwright/test';
import 'dotenv/config';

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  retries: 1,
  reporter: [['html'], ['json', { outputFile: 'test-results/results.json' }]],
  use: {
    baseURL: process.env.BASE_URL,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox',  use: { ...devices['Desktop Firefox'] } },
    { name: 'safari',   use: { ...devices['Desktop Safari'] } },
  ],
});
```

### `browserstack.config.ts`

```typescript
import { defineConfig } from '@playwright/test';
import 'dotenv/config';

const caps = {
  browser: 'chrome',
  browser_version: 'latest',
  os: 'Windows',
  os_version: '11',
  'browserstack.username': process.env.BROWSERSTACK_USERNAME,
  'browserstack.accessKey': process.env.BROWSERSTACK_ACCESS_KEY,
  'browserstack.local': false,
  name: 'Playwright Suite',
  build: `Build-${Date.now()}`,
};

export default defineConfig({
  testDir: './tests',
  reporter: [['html'], ['json', { outputFile: 'test-results/results.json' }]],
  use: {
    connectOptions: {
      wsEndpoint: `wss://cdp.browserstack.com/playwright?caps=${encodeURIComponent(JSON.stringify(caps))}`,
    },
  },
});
```

---

## Google Sheet Structure

QA maintains columns A–E. Columns F–H are written back automatically after each run.

| A: TC_ID | B: Module | C: Title | D: Priority | E: Status | F: Last Run | G: Duration |
|---|---|---|---|---|---|---|
| TC_001 | landing | Hero loads dynamically | P1 | | | |
| TC_002 | editor | TOC syncs with heading | P1 | | | |
| TC_003 | ckeditor | Bold formatting applies | P2 | | | |

### `src/sheets/googleSheets.ts`

```typescript
import { google } from 'googleapis';

const SHEET_ID = process.env.GOOGLE_SHEET_ID!;
const RANGE    = 'Sheet1!A2:G';

const auth = new google.auth.GoogleAuth({
  keyFile: 'service-account.json',
  scopes: ['https://www.googleapis.com/auth/spreadsheets'],
});

export interface TestCase {
  tcId: string;
  module: string;
  title: string;
  priority: string;
  rowIndex: number;
}

export async function fetchTestCases(): Promise<TestCase[]> {
  const sheets = google.sheets({ version: 'v4', auth });
  const res = await sheets.spreadsheets.values.get({ spreadsheetId: SHEET_ID, range: RANGE });
  return (res.data.values || []).map((row, i) => ({
    tcId:     row[0],
    module:   row[1],
    title:    row[2],
    priority: row[3],
    rowIndex: i + 2,  // 1-indexed, offset by header row
  }));
}

export async function writeResultsToSheet(results: TestResult[]) {
  const sheets = google.sheets({ version: 'v4', auth });
  const data = results.map(r => ({
    range: `Sheet1!E${r.rowIndex}:G${r.rowIndex}`,
    values: [[r.status.toUpperCase(), new Date().toISOString(), `${r.duration_ms}ms`]],
  }));
  await sheets.spreadsheets.values.batchUpdate({
    spreadsheetId: SHEET_ID,
    requestBody: { valueInputOption: 'RAW', data },
  });
}
```

---

## Supabase Schema

```sql
-- Test runs table
CREATE TABLE test_runs (
  run_id      text PRIMARY KEY,
  build       text,
  environment text,         -- 'local' | 'browserstack'
  started_at  timestamptz,
  finished_at timestamptz
);

-- Test results table
CREATE TABLE test_results (
  id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  run_id      text REFERENCES test_runs(run_id),
  tc_id       text NOT NULL,    -- matches Google Sheet col A
  module      text,             -- landing | editor | ckeditor
  title       text,
  status      text,             -- passed | failed | skipped
  duration_ms int,
  browser     text,
  os          text,
  error       text,
  screenshot  text,
  created_at  timestamptz DEFAULT now()
);
```

### `src/db/supabase.ts`

```typescript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_KEY!
);

export async function insertRun(results: TestResult[]) {
  const runId = `run_${Date.now()}`;

  await supabase.from('test_runs').insert({
    run_id: runId,
    environment: process.env.CI ? 'browserstack' : 'local',
    started_at: new Date().toISOString(),
  });

  const rows = results.map(r => ({ ...r, run_id: runId }));
  await supabase.from('test_results').insert(rows);
}
```

---

## CSV Output Format

```csv
run_id,tc_id,module,title,status,duration_ms,browser,os,error,screenshot
run_1711324800,TC_001,landing,Hero loads dynamically,passed,1203,chromium,local,,
run_1711324800,TC_002,editor,TOC syncs with heading,failed,3401,chromium,local,Expected h2 visible,screenshots/TC_002.png
run_1711324800,TC_003,ckeditor,Bold formatting applies,passed,890,chromium,local,,
```

### `src/reporters/csvReporter.ts`

```typescript
import { createObjectCsvWriter } from 'csv-writer';

export async function writeCSV(results: TestResult[], path: string) {
  const writer = createObjectCsvWriter({
    path,
    header: [
      { id: 'run_id',      title: 'run_id' },
      { id: 'tc_id',       title: 'tc_id' },
      { id: 'module',      title: 'module' },
      { id: 'title',       title: 'title' },
      { id: 'status',      title: 'status' },
      { id: 'duration_ms', title: 'duration_ms' },
      { id: 'browser',     title: 'browser' },
      { id: 'os',          title: 'os' },
      { id: 'error',       title: 'error' },
      { id: 'screenshot',  title: 'screenshot' },
    ],
  });
  await writer.writeRecords(results);
}
```

---

## Page Object Models

### `src/pages/CKEditorPage.ts`

```typescript
import { Page, expect } from '@playwright/test';

export class CKEditorPage {

  // Type text inside CKEditor (handles iframe + contenteditable)
  async typeInEditor(page: Page, text: string) {
    const editorFrame = page.frameLocator('.ck-editor iframe').first();
    const body = editorFrame.locator('body');
    await body.click();
    await body.type(text);
  }

  // Apply bold via keyboard shortcut and verify toolbar state
  async applyBold(page: Page) {
    await page.keyboard.press('Control+b');
    await expect(
      page.locator('.ck-button[aria-label="Bold"]')
    ).toHaveAttribute('aria-pressed', 'true');
  }

  // Get raw HTML content from CKEditor 5 API
  async getEditorContent(page: Page): Promise<string> {
    return page.evaluate(() => (window as any).editor.getData());
  }

  // Insert heading and verify TOC updates
  async insertHeadingAndVerifyTOC(page: Page, level: string, text: string) {
    await page.locator('.ck-heading-dropdown').click();
    await page.locator(`[data-value="${level}"]`).click();
    await page.keyboard.type(text);

    // Wait for 2-way binding to sync
    await page.waitForFunction((t) => {
      const toc = document.querySelector('.toc-container');
      return toc?.textContent?.includes(t);
    }, text);

    await expect(page.locator('.toc-container')).toContainText(text);
  }

  // Verify thumbnail updates when content changes
  async verifyThumbnailSync(page: Page) {
    const editorContent = await this.getEditorContent(page);
    const thumbnailContent = await page.locator('.thumbnail-preview').textContent();
    expect(thumbnailContent).toContain(editorContent.substring(0, 50));
  }
}
```

### `src/pages/LandingPage.ts`

```typescript
import { Page, expect } from '@playwright/test';

export class LandingPage {

  async waitForDynamicContent(page: Page) {
    // Wait for skeleton loaders to disappear
    await page.waitForSelector('.skeleton', { state: 'detached' });
    await expect(page.locator('[data-testid="hero-section"]')).toBeVisible();
  }

  async verifyHeroContent(page: Page) {
    await this.waitForDynamicContent(page);
    const hero = page.locator('[data-testid="hero-section"]');
    await expect(hero).not.toBeEmpty();
  }
}
```

---

## Sample Tests

### `tests/ckeditor/editor-modules.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { CKEditorPage } from '../../src/pages/CKEditorPage';

const ck = new CKEditorPage();

test.describe('CKEditor modules', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/editor');
    await page.waitForSelector('.ck-editor__editable', { state: 'visible' });
  });

  test('TC_003 — bold formatting applies', async ({ page }) => {
    await ck.typeInEditor(page, 'Hello World');
    await page.keyboard.press('Control+a');
    await ck.applyBold(page);
    const content = await ck.getEditorContent(page);
    expect(content).toContain('<strong>Hello World</strong>');
  });

  test('TC_004 — heading inserts into TOC', async ({ page }) => {
    await ck.insertHeadingAndVerifyTOC(page, 'heading2', 'Introduction');
  });

  test('TC_005 — thumbnail syncs with editor content', async ({ page }) => {
    await ck.typeInEditor(page, 'Preview content for thumbnail');
    await ck.verifyThumbnailSync(page);
  });
});
```

### `tests/editor/two-way-binding.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('2-way binding — TOC + Thumbnail', () => {

  test('TC_002 — TOC updates when heading changes', async ({ page }) => {
    await page.goto('/editor');

    // Add a heading
    await page.locator('.ck-editor__editable').click();
    await page.keyboard.type('My Section Title');

    // Watch for DOM update via waitForFunction
    await page.waitForFunction(() => {
      return document.querySelector('.toc-item')?.textContent?.includes('My Section Title');
    });

    await expect(page.locator('.toc-container')).toContainText('My Section Title');
  });
});
```

---

## Post-Test Pipeline

### `scripts/posttest.ts`

```typescript
import { readFileSync } from 'fs';
import { writeCSV }         from '../src/reporters/csvReporter';
import { insertRun }        from '../src/db/supabase';
import { writeResultsToSheet, fetchTestCases } from '../src/sheets/googleSheets';

interface PlaywrightResult {
  suites: Array<{
    specs: Array<{
      title: string;
      tests: Array<{ status: string; duration: number; results: any[] }>;
    }>;
  }>;
}

async function main() {
  const raw: PlaywrightResult = JSON.parse(
    readFileSync('./test-results/results.json', 'utf8')
  );

  const testCases = await fetchTestCases();
  const tcMap = Object.fromEntries(testCases.map(tc => [tc.title, tc]));

  const results = raw.suites.flatMap(suite =>
    suite.specs.map(spec => {
      const test = spec.tests[0];
      const tc   = tcMap[spec.title] || {};
      return {
        tc_id:       tc.tcId       || 'UNKNOWN',
        module:      tc.module     || 'unknown',
        title:       spec.title,
        status:      test.status,
        duration_ms: test.duration,
        browser:     test.results[0]?.workerIndex?.toString() || 'chromium',
        os:          process.platform,
        error:       test.results[0]?.error?.message || '',
        screenshot:  test.results[0]?.attachments?.[0]?.path || '',
        rowIndex:    tc.rowIndex,
      };
    })
  );

  await Promise.all([
    writeCSV(results, './test-results/results.csv'),
    insertRun(results),
    writeResultsToSheet(results),
  ]);

  console.log(`✓ ${results.length} results → CSV + Supabase + Sheet`);
}

main().catch(console.error);
```

---

## Implementation Order

Build the pipeline in this sequence:

1. **`googleSheets.ts`** — read TC metadata at test start, writeback after
2. **`CKEditorPage.ts`** — all CKEditor interactions (type, bold, getContent, iframe)
3. **`supabase.ts`** — insert test_runs and test_results
4. **`csvReporter.ts`** — JSON → CSV with exact column schema
5. **`browserstack.config.ts`** — connect with build tagging
6. **`posttest.ts`** — wire all three outputs together

---

## Key Decisions Summary

- **Framework**: Playwright (TypeScript) over Java + TestNG — better CKEditor support, native JS API access, simpler Google Sheets / Supabase integration
- **Result storage**: Supabase (PostgreSQL) for analytics + traceability, CSV for stakeholder exports, HTML report for dev debugging
- **Master test cases**: Google Sheets remains QA-owned; results write back automatically per TC_ID row
- **BrowserStack**: Used via `connectOptions` wsEndpoint in a separate config — same test code, different runner
- **`posttest` hook**: Eliminates manual steps — CSV, Supabase insert, and Sheet writeback all trigger automatically after `npm test`
