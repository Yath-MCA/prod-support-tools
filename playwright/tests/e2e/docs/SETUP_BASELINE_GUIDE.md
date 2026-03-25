# Common E2E Baseline Setup (BeforeAll/AfterAll)

Use the same baseline flow for any module/regression/full suite:

1. **SETUP: Initialize browser & load landing page ONCE**
2. **TEST 1 equivalent (in setup): Landing page validation**
3. **TEST 2 equivalent (in setup): Submit → redirect to editor**
4. **TEST 3 equivalent (in setup): Resolve DOC_ID**
5. **TEST 4 equivalent (in setup): Editor localStorage context**
6. **CLEANUP: Close browser after all tests**

## Shared helper

- Setup helper: `tests/e2e/helpers/session-baseline.helper.js`
- Teardown helper: `tests/e2e/helpers/session-baseline.helper.js`

### APIs

- `initializeLandingEditorSession({ browser, baseURL, selectors })`
  - returns `{ page, DOC_ID, context, isInitialized, setupError }`
- `cleanupLandingEditorSession(page)`
  - uses `logoutSafely`
  - clears local/session storage + cookies
  - closes page safely

## Usage pattern in any suite

```js
import { loadSelectors } from "./helpers/config.helper";
import {
  initializeLandingEditorSession,
  cleanupLandingEditorSession
} from "./helpers/session-baseline.helper";

const selectors = loadSelectors("landing");
const shared = { page: null, setupError: null, ready: false };

test.beforeAll(async ({ browser, baseURL }) => {
  const session = await initializeLandingEditorSession({ browser, baseURL, selectors });
  shared.page = session.page;
  shared.setupError = session.setupError;
  shared.ready = session.isInitialized;
});

test.afterAll(async () => {
  await cleanupLandingEditorSession(shared.page);
});
```

## Already integrated

- `tests/e2e/insert-comment-basic.spec.js`
- `tests/e2e/landing-editor-module-basic.spec.js`
- `tests/e2e/landing-to-editor-query.spec.js`
- `tests/e2e/landing-to-editor-comment.spec.js`
- `tests/e2e/landing-to-editor6.spec.js`
- `tests/e2e/query-workflow.spec.js`
- `tests/e2e/query-comment.spec.js`
- `tests/e2e/cjk-validator.spec.js`

## Suggestion for regression/full

For each suite in regression/full pipelines, remove duplicated setup/cleanup code and call this helper. This guarantees:

- same baseline behavior everywhere
- stable logout/session cleanup
- less flaky test chaining

### Remaining suites (optional migration)

- None in current phase.

All previously identified phase-2 suites are now aligned to the shared baseline lifecycle.
