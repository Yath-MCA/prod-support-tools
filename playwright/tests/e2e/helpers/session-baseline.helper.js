import { expect } from "@playwright/test";
import { resolveDocId, getEditorContext } from "./common.helper";
import { logoutSafely } from "./logout.helper";

// ─── Constants ──────────────────────────────────────────────────────────────────
const SESSION = {
    landingTitleTimeout:  7500,
    acceptBtnTimeout:     2500,
    editorIframeTimeout:  15000,
    loadingDialogTimeout: 25000,
    editorSignalTimeout:  12000,
    overallTimeoutMs:     60000,
    maxSubmitAttempts:    2,
    retryDelayMs:         300,
    cleanupRetryDelayMs:  750,
    cleanupAttempts:      2,
};

const EDITOR_URL_PATTERN   = /editor|xmleditor/i;
const LANDING_URL_PATTERN  = /landing|validateurl|login/i;
const EDITOR_IFRAME_SEL    = "iframe.cke_wysiwyg_frame";
const LOADING_DIALOG_SEL   = "#loadingDialog";
// ───────────────────────────────────────────────────────────────────────────────

// ─── Checkpoint Schema ──────────────────────────────────────────────────────────
function makeCheckpoints() {
    return {
        landingLoaded:      false,
        landingValidated:   false,
        redirectedToEditor: false,
        docResolved:        false,
        contextValidated:   false,
    };
}
// ───────────────────────────────────────────────────────────────────────────────

// ─── URL helpers ────────────────────────────────────────────────────────────────
const isEditorUrl  = (page) => EDITOR_URL_PATTERN.test(page.url() || "");
const isLandingUrl = (page) => LANDING_URL_PATTERN.test(page.url() || "");
// ───────────────────────────────────────────────────────────────────────────────

/**
 * Race three editor-ready signals.
 * Resolves as soon as ANY ONE of them fires.
 */
async function waitForEditorSignal(page, timeout = SESSION.editorSignalTimeout) {
    await Promise.any([
        page.waitForURL(EDITOR_URL_PATTERN, { timeout }),
        page.waitForSelector(EDITOR_IFRAME_SEL, { timeout }),
        page.waitForFunction(
            () => typeof GlobalEditor !== "undefined" && !!GlobalEditor?.document?.$,
            { timeout }
        ),
    ]);
}

/**
 * Try to click a locator, escalating through force-click → dispatchEvent.
 */
async function resilientClick(locator) {
    try {
        await locator.click({ timeout: 5000 });
    } catch {
        try {
            await locator.click({ timeout: 5000, force: true });
        } catch {
            await locator.dispatchEvent("click");
        }
    }
}

// ─── Public API ─────────────────────────────────────────────────────────────────

/**
 * Bootstrap a new browser context, load the landing page, submit it, and
 * wait until the CKEditor iframe is visible.
 *
 * Returns a `state` object:
 *   { page, DOC_ID, context, isInitialized, setupError, checkpoints }
 */
export async function initializeLandingEditorSession({ browser, baseURL, selectors }) {
    const state = {
        page:         null,
        DOC_ID:       null,
        context:      null,
        isInitialized: false,
        setupError:   null,
        checkpoints:  makeCheckpoints(),
    };

    try {
        // console.log(`[session-baseline] Initializing landing-editor session with baseURL: ${baseURL}`.split(" "));
        const landingSubmitSelector = selectors.submit;

        // ── 1. Open landing page ─────────────────────────────────────────────
        state.page = await browser.newPage();
        await state.page.goto(baseURL, { waitUntil: "domcontentloaded" });
        state.checkpoints.landingLoaded = true;

        // ── 2. Validate landing UI ───────────────────────────────────────────
        await expect(state.page.locator(selectors.title1))
            .toBeVisible({ timeout: SESSION.landingTitleTimeout });
        await expect(state.page.locator(landingSubmitSelector))
            .toBeVisible({ timeout: SESSION.acceptBtnTimeout });
        state.checkpoints.landingValidated = true;
        console.log("[session-baseline] landing page loaded and validated");

        // ── 3. Submit and wait for editor ────────────────────────────────────
        await submitAndWaitForEditor(state.page, selectors);
        state.checkpoints.redirectedToEditor = true;
        console.log("[session-baseline] redirected to editor");

        // ── 4. Resolve document ID ───────────────────────────────────────────
        state.DOC_ID = await resolveDocId(state.page);
        expect(state.DOC_ID).toBeTruthy();
        state.checkpoints.docResolved = true;
        console.log("[session-baseline] document ID resolved:", state.DOC_ID);

        // ── 5. Resolve editor context (user info, roles, etc.) ───────────────
        state.context = await getEditorContext(state.page, state.DOC_ID);
        expect(state.context?.USER_INFO).toBeTruthy();
        state.checkpoints.contextValidated = true;
        // console.log("[session-baseline] editor context resolved:", state.context);
        state.isInitialized = true;
    } catch (error) {
        state.setupError = error?.message || String(error);
        console.error("[session-baseline] initialization failed:", state.setupError);
        console.error("[session-baseline] checkpoints at failure:", state.checkpoints);
    }

    return state;
}

/**
 * Gracefully log out, clear storage, and close the page.
 * Safe to call even if `page` is already closed or null.
 */
export async function cleanupLandingEditorSession(page) {
    console.log("[session-baseline] starting cleanup of landing-editor session");
    if (!page || page.isClosed()) return;

    const context = page.context();

    // ── 1. Logout ────────────────────────────────────────────────────────────
    for (let attempt = 1; attempt <= SESSION.cleanupAttempts; attempt++) {
        try {
            console.log(`[session-baseline] logout attempt ${attempt}...`);
            await logoutSafely(page);
            if (isLandingUrl(page)) break;
        } catch (error) {
            console.error(`[session-baseline] logout attempt ${attempt} failed:`, error);
        }
        await page.waitForTimeout(SESSION.cleanupRetryDelayMs);
    }

    // ── 2. Clear browser storage ─────────────────────────────────────────────
    try {
        if (!page.isClosed()) {
            await page.evaluate(() => {
                try { localStorage.clear();   } catch { /* noop */ }
                try { sessionStorage.clear(); } catch { /* noop */ }
            }).catch(() => { /* page may have navigated away */ });
        }
    } catch { /* noop */ }

    // ── 3. Clear cookies & close page ───────────────────────────────────────
    await context.clearCookies().catch(() => { });
    if (!page.isClosed()) {
        await page.close().catch(() => { });
    }
}

/**
 * Click the landing submit button and wait until the editor is fully ready.
 * Retries up to `SESSION.maxSubmitAttempts` times within `SESSION.overallTimeoutMs`.
 */
export async function submitAndWaitForEditor(page, selectors) {
    const startedAt = Date.now();
    const landingSubmitSelector = selectors.submit;
    console.log(`[session-baseline] submitting landing page using selector: ${landingSubmitSelector}`);
    for (let attempt = 1; attempt <= SESSION.maxSubmitAttempts; attempt++) {
        // ── Guard: overall deadline ──────────────────────────────────────────
        if (Date.now() - startedAt > SESSION.overallTimeoutMs) {
            throw new Error(
                `Landing-to-editor redirect exceeded ${SESSION.overallTimeoutMs}ms. ` +
                `Current URL: ${page.url()}`
            );
        }

        // ── Locate and click submit ──────────────────────────────────────────
        const submitBtn = page.locator(landingSubmitSelector).first();
        await submitBtn.waitFor({ state: "visible", timeout: 5000 });
        await submitBtn.click({ timeout: 5000 });
        console.log(`[session-baseline] attempt ${attempt}: submit button visible`);

        if (attempt > 1) {
            await page.waitForTimeout(SESSION.retryDelayMs);
        }

        await resilientClick(submitBtn);

        // ── Wait for any editor-ready signal ────────────────────────────────
        try {
            console.log(`[session-baseline] attempt ${attempt}: waiting for editor signal...`);
            await waitForEditorSignal(page, SESSION.editorSignalTimeout);
            console.log(`[session-baseline] attempt ${attempt}: editor signal received`);
        } catch {
            // If we're still on the landing page and have retries left, loop
            if (attempt < SESSION.maxSubmitAttempts && isLandingUrl(page)) {
                console.warn(`[session-baseline] attempt ${attempt}: still on landing, retrying…`);
                continue;
            }
        }

        // ── Wait for any loading overlay to clear ────────────────────────────
        console.log(`[session-baseline] attempt ${attempt}: waiting for loading overlay to clear`);
        const loadingDialog = page.locator(LOADING_DIALOG_SEL).first();
        if (await loadingDialog.isVisible().catch(() => false)) {
            await loadingDialog
                .waitFor({ state: "hidden", timeout: SESSION.loadingDialogTimeout })
                .catch(() => console.warn("[session-baseline] loading dialog did not hide in time"));
        }

        // ── Confirm iframe presence ──────────────────────────────────────────
        await page
            .waitForSelector(EDITOR_IFRAME_SEL, { timeout: SESSION.editorIframeTimeout })
            .catch(() => { });

        if (isEditorUrl(page) || await page.locator(EDITOR_IFRAME_SEL).first().isVisible().catch(() => false)) {
            console.log(`[session-baseline] editor ready after attempt ${attempt}`);
            return;
        }
    }

    throw new Error(
        `Landing-to-editor redirect failed after ${SESSION.maxSubmitAttempts} attempts. ` +
        `Current URL: ${page.url()}`
    );
}