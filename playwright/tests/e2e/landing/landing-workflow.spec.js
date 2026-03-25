/**
 * Landing Page Workflow Tests
 *
 * Covers all status × client routing branches defined in:
 *   docs/workflow-access-ai-agent-prompt.md
 *
 * Two test layers:
 *   A) Mocked API  — fast, deterministic, tests every branch
 *   B) Real URL    — requires links.json populated with real keys
 *
 * Priority order (per spec doc):
 *   Non-PLOS active → signoff → deactive/file_deleted → PLOS (lowest)
 */

import { test, expect } from '@playwright/test';
import {
    getLandingSignalState,
    classifyStatus,
    pickLink,
    waitForStatusAlert,
    dismissAlert,
    getLandingPageContent
} from '../helpers/landing-signal.helper.js';
import { waitForPageFullyLoaded, logStep, takeScreenshot } from '../helpers/test-helpers.js';
import config from '../fixtures/test-config.js';

// ---------------------------------------------------------------------------
// Shared mock helpers
// ---------------------------------------------------------------------------

/**
 * Intercept the server key-validation API and return a fake response.
 * TODO: Replace the route pattern below with the actual API endpoint (e.g. /api/validate or /validateurl).
 */
async function mockApiResponse(page, overrides = {}) {
    const defaults = {
        status:       'active',
        author_count: 1,
        client:       'lww',
        role:         'author',
        emailList:    [],
        title:        'Test Article Title',
        authorname:   'John Doe',
        signedAt:     null
    };

    const body = { ...defaults, ...overrides };

    await page.route('**/api/validate**', route => {
        route.fulfill({
            status:      200,
            contentType: 'application/json',
            body:        JSON.stringify(body)
        });
    });

    // Also intercept the HTML page load if the key validation is inline
    await page.route('**/validateurl**', route => {
        route.continue();
    });
}

// ---------------------------------------------------------------------------
// A) Mocked API Tests — status routing
// ---------------------------------------------------------------------------

/* test.describe('Landing Workflow — Mocked API (status routing)', () => {

    test.setTimeout(60000);

    // ------------------------------------------------------------------
    // ACTIVE — Non-PLOS, single author → confirm dialog (Accept / Cancel)
    // ------------------------------------------------------------------
    test('[TC_LP_001] @smoke Active + LWW + single author — shows accept button', async ({ page }) => {
        logStep('TC_LP_001: Active/LWW/single-author', 'start');

        await mockApiResponse(page, { status: 'active', client: 'lww', author_count: 1 });
        await page.goto('/', { waitUntil: 'domcontentloaded' });
        await waitForPageFullyLoaded(page);

        const signal = await getLandingSignalState(page);
        logStep(`Signal: ${JSON.stringify(signal)}`, 'info');

        expect(signal.submitVisible, 'Accept button must be visible for active flow').toBe(true);
        expect(signal.hasAlert, 'No blocking alert expected for active flow').toBe(false);
        expect(signal.strictProofContext, 'strictProofContext must be true').toBe(true);

        // Content validation
        const content = await getLandingPageContent(page);
        expect(content.title1, 'title1 must not be empty').toBeTruthy();
        expect(content.authorname, 'authorname must not be empty').toBeTruthy();

        await takeScreenshot(page, 'tc-lp-001-active-lww');
        logStep('TC_LP_001 PASSED', 'success');
    });

    test('[TC_LP_002] Active + OUP + single author — shows accept button', async ({ page }) => {
        logStep('TC_LP_002: Active/OUP/single-author', 'start');

        await mockApiResponse(page, { status: 'active', client: 'oup', author_count: 1 });
        await page.goto('/', { waitUntil: 'domcontentloaded' });
        await waitForPageFullyLoaded(page);

        const signal = await getLandingSignalState(page);
        expect(signal.submitVisible).toBe(true);
        expect(signal.hasAlert).toBe(false);

        await takeScreenshot(page, 'tc-lp-002-active-oup');
        logStep('TC_LP_002 PASSED', 'success');
    });

    test('[TC_LP_003] Active + MEDKNOW + single author — shows accept button', async ({ page }) => {
        logStep('TC_LP_003: Active/MEDKNOW/single-author', 'start');

        await mockApiResponse(page, { status: 'active', client: 'medknow', author_count: 1 });
        await page.goto('/', { waitUntil: 'domcontentloaded' });
        await waitForPageFullyLoaded(page);

        const signal = await getLandingSignalState(page);
        expect(signal.submitVisible).toBe(true);
        expect(signal.hasAlert).toBe(false);

        logStep('TC_LP_003 PASSED', 'success');
    });

    // ------------------------------------------------------------------
    // ACTIVE — multi-author → email picker
    // ------------------------------------------------------------------
    test('[TC_LP_004] Active + multiple authors — shows email verification', async ({ page }) => {
        logStep('TC_LP_004: Active/multi-author', 'start');

        await mockApiResponse(page, {
            status:       'active',
            client:       'lww',
            author_count: 3,
            emailList:    ['author1@test.com', 'author2@test.com', 'author3@test.com']
        });
        await page.goto('/', { waitUntil: 'domcontentloaded' });
        await waitForPageFullyLoaded(page);

        const emailDialog = page.locator(config.multiAuthor.dialog);
        const emailInput  = page.locator(config.multiAuthor.emailInput);

        await expect(emailDialog, 'Email picker dialog must appear for multi-author').toBeVisible({ timeout: 10000 });
        await expect(emailInput).toBeVisible();

        await takeScreenshot(page, 'tc-lp-004-multi-author');
        logStep('TC_LP_004 PASSED', 'success');
    });

    // ------------------------------------------------------------------
    // ACTIVE — PLOS single author → access code dialog (lowest priority)
    // ------------------------------------------------------------------
    test('[TC_LP_005] Active + PLOS + single author — shows access code dialog', async ({ page }) => {
        logStep('TC_LP_005: Active/PLOS/single-author', 'start');

        await mockApiResponse(page, { status: 'active', client: 'plos', author_count: 1 });
        await page.goto('/', { waitUntil: 'domcontentloaded' });
        await waitForPageFullyLoaded(page);

        const accessDialog = page.locator(config.plosAccessCode.dialog);
        const codeInput    = page.locator(config.plosAccessCode.input);

        await expect(accessDialog, 'Access code dialog must appear for PLOS').toBeVisible({ timeout: 10000 });
        await expect(codeInput).toBeVisible();

        await takeScreenshot(page, 'tc-lp-005-plos-access-code');
        logStep('TC_LP_005 PASSED', 'success');
    });

    // ------------------------------------------------------------------
    // SIGNOFF — editor access blocked, redirect to read-only
    // ------------------------------------------------------------------
    test('[TC_LP_006] @smoke Signoff — blocks editor access, shows alert', async ({ page }) => {
        logStep('TC_LP_006: Signoff flow', 'start');

        await mockApiResponse(page, { status: 'signoff', client: 'lww', role: 'editor' });
        await page.goto('/', { waitUntil: 'domcontentloaded' });

        await waitForStatusAlert(page);

        const signal = await getLandingSignalState(page);
        logStep(`Signal: ${JSON.stringify(signal)}`, 'info');

        expect(signal.hasAlert, 'Blocking alert must be shown for signoff').toBe(true);
        expect(signal.submitVisible, 'Submit button must NOT be visible on signoff').toBe(false);

        const detectedStatus = classifyStatus(signal);
        expect(detectedStatus).toBe('signoff');

        // Dismiss alert → should redirect to read-only page
        await dismissAlert(page);
        await page.waitForLoadState('domcontentloaded');

        const readOnlyMarker = page.locator(config.readOnly.pageMarker);
        await expect(readOnlyMarker).toBeVisible({ timeout: 10000 });

        await takeScreenshot(page, 'tc-lp-006-signoff');
        logStep('TC_LP_006 PASSED', 'success');
    });

    // ------------------------------------------------------------------
    // SIGNOFF — LWW + author role → show sign time in read-only header
    // ------------------------------------------------------------------
    test('[TC_LP_007] Signoff + LWW + author role — shows author sign time', async ({ page }) => {
        logStep('TC_LP_007: Signoff/LWW/author sign time', 'start');

        await mockApiResponse(page, {
            status:   'signoff',
            client:   'lww',
            role:     'author',
            signedAt: '2026-03-25T10:30:00Z'
        });
        await page.goto('/', { waitUntil: 'domcontentloaded' });

        await waitForStatusAlert(page);
        await dismissAlert(page);
        await page.waitForLoadState('domcontentloaded');

        // LWW author signoff must show sign time on read-only header
        const signTimeLabel = page.locator(config.lwwSignoff.signTimeLabel);
        await expect(signTimeLabel, 'Author sign time must be visible for LWW author signoff').toBeVisible({ timeout: 10000 });

        await takeScreenshot(page, 'tc-lp-007-lww-signtime');
        logStep('TC_LP_007 PASSED', 'success');
    });

    // ------------------------------------------------------------------
    // DEACTIVE — blocks editor, redirects to archive
    // ------------------------------------------------------------------
    test('[TC_LP_008] @smoke Deactive — blocks editor access, redirects to archive', async ({ page }) => {
        logStep('TC_LP_008: Deactive flow', 'start');

        await mockApiResponse(page, { status: 'deactive', client: 'oup' });
        await page.goto('/', { waitUntil: 'domcontentloaded' });

        await waitForStatusAlert(page);

        const signal = await getLandingSignalState(page);
        const detectedStatus = classifyStatus(signal);

        expect(signal.hasAlert).toBe(true);
        expect(signal.submitVisible).toBe(false);
        expect(detectedStatus).toBe('deactive');

        await dismissAlert(page);
        await page.waitForLoadState('domcontentloaded');

        const archiveMarker = page.locator(config.archive.pageMarker);
        await expect(archiveMarker).toBeVisible({ timeout: 10000 });

        await takeScreenshot(page, 'tc-lp-008-deactive');
        logStep('TC_LP_008 PASSED', 'success');
    });

    // ------------------------------------------------------------------
    // FILE_DELETED — same outcome as deactive
    // ------------------------------------------------------------------
    test('[TC_LP_009] File deleted — blocks editor access, redirects to archive', async ({ page }) => {
        logStep('TC_LP_009: File deleted flow', 'start');

        await mockApiResponse(page, { status: 'file_deleted', client: 'medknow' });
        await page.goto('/', { waitUntil: 'domcontentloaded' });

        await waitForStatusAlert(page);

        const signal        = await getLandingSignalState(page);
        const detectedStatus = classifyStatus(signal);

        expect(signal.hasAlert).toBe(true);
        expect(['deactive', 'file_deleted']).toContain(detectedStatus);

        await dismissAlert(page);
        const archiveMarker = page.locator(config.archive.pageMarker);
        await expect(archiveMarker).toBeVisible({ timeout: 10000 });

        await takeScreenshot(page, 'tc-lp-009-file-deleted');
        logStep('TC_LP_009 PASSED', 'success');
    });

}); */

// ---------------------------------------------------------------------------
// B) Real URL Tests — requires links.json populated with actual keys
// ---------------------------------------------------------------------------

test.describe('Landing Workflow', () => {

    // Page is shared — navigate once in beforeAll, all tests inspect the same loaded page
    test.describe.configure({ mode: 'serial' });
    test.setTimeout(30000);

    let sharedPage;

    test.beforeAll(async ({ browser, baseURL }) => {
        const url = pickLink('medknow', 'author', 'active') || baseURL;
        const context = await browser.newContext();
        sharedPage = await context.newPage();

        logStep(`Loading: ${url}`, 'start');
        await sharedPage.goto(url, { waitUntil: 'domcontentloaded' });

        // Wait for key validation to complete:
        //   - window.SHARED_KEY is set  → active / signoff processing done
        //   - .swal2-container visible  → blocking alert (signoff / deactive) appeared
        await sharedPage.waitForFunction(
            () => window.SHARED_KEY != null || document.querySelector('.swal2-container') != null,
            { timeout: 15000 }
        ).catch(() => { logStep('SHARED_KEY wait timed out — page may still be loading', 'warning'); });

        logStep('Page ready — running workflow checks', 'success');
    });

    test.afterAll(async () => {
        await sharedPage?.context().close();
    });

    // ------------------------------------------------------------------
    // TC_LP_W01: Signal state — detect active / signoff / deactive
    // ------------------------------------------------------------------
    test('[TC_LP_W01] Detect landing page workflow status', async () => {
        const signal = await getLandingSignalState(sharedPage);
        const detectedStatus = classifyStatus(signal);

        logStep(`URL:    ${signal.url}`, 'info');
        logStep(`Status: ${detectedStatus}`, 'check');
        logStep(`Signal: ${JSON.stringify(signal)}`, 'info');

        expect(['active', 'signoff', 'deactive', 'file_deleted'],
            `Unknown status detected: ${detectedStatus}`
        ).toContain(detectedStatus);

        await takeScreenshot(sharedPage, `wf-status-${detectedStatus}`);
    });

    // ------------------------------------------------------------------
    // TC_LP_W02: Active flow — accept button + content present
    // ------------------------------------------------------------------
    test('[TC_LP_W02] Active flow — accept button and content visible', async () => {
        const signal = await getLandingSignalState(sharedPage);

        if (classifyStatus(signal) !== 'active') {
            test.skip(true, `Page is not in active state (${classifyStatus(signal)}) — skip active checks`);
            return;
        }

        expect(signal.submitVisible, 'Accept button must be visible').toBe(true);
        expect(signal.strictProofContext, 'URL must contain key and submit must be visible').toBe(true);

        const content = await getLandingPageContent(sharedPage);
        logStep(`title1: "${content.title1}"`, 'info');
        logStep(`author: "${content.authorname}"`, 'info');

        expect(content.title1, 'title1 must not be empty').toBeTruthy();
        expect(content.authorname, 'authorname must not be empty').toBeTruthy();

        await takeScreenshot(sharedPage, 'wf-active-content');
    });

    // ------------------------------------------------------------------
    // TC_LP_W03: Client icon — visible and not broken
    // ------------------------------------------------------------------
    test('[TC_LP_W03] Client icon loaded and not broken', async () => {
        const clientIcon = sharedPage.locator(config.landing.clientIcon);
        await expect(clientIcon).toBeVisible();

        const healthy = await clientIcon.evaluate(
            img => img.complete && img.naturalWidth > 0
        ).catch(() => false);

        expect(healthy, 'Client icon must not be broken (naturalWidth > 0)').toBe(true);
        logStep(`Client icon src: ${await clientIcon.getAttribute('src')}`, 'info');
    });

    // ------------------------------------------------------------------
    // TC_LP_W04: SHARED_KEY — client and role resolved from server
    // ------------------------------------------------------------------
    test('[TC_LP_W04] SHARED_KEY populated with client and role', async () => {
        const signal = await getLandingSignalState(sharedPage);

        logStep(`SHARED_KEY: ${JSON.stringify(signal.sharedKey)}`, 'info');

        expect(signal.sharedKey, 'window.SHARED_KEY must be set by server response').toBeTruthy();
        expect(signal.sharedKey.client, 'SHARED_KEY.client must not be empty').toBeTruthy();
        expect(signal.sharedKey.rolename, 'SHARED_KEY.rolename must not be empty').toBeTruthy();
    });

    // ------------------------------------------------------------------
    // TC_LP_W05: Signoff flow — alert visible, submit hidden
    // ------------------------------------------------------------------
    test('[TC_LP_W05] Signoff flow — alert blocks editor access', async () => {
        const signal = await getLandingSignalState(sharedPage);

        if (classifyStatus(signal) !== 'signoff') {
            test.skip(true, `Page is not in signoff state — skip signoff checks`);
            return;
        }

        expect(signal.hasAlert, 'Blocking alert must be visible for signoff').toBe(true);
        expect(signal.submitVisible, 'Accept button must NOT be visible on signoff').toBe(false);

        logStep(`Alert title: "${signal.alertTitle}"`, 'info');
        logStep(`Alert text:  "${signal.alertText}"`, 'info');

        await takeScreenshot(sharedPage, 'wf-signoff-alert');
    });

    // ------------------------------------------------------------------
    // TC_LP_W06: Deactive / file_deleted — alert visible, submit hidden
    // ------------------------------------------------------------------
    test('[TC_LP_W06] Deactive/file_deleted — alert blocks editor access', async () => {
        const signal = await getLandingSignalState(sharedPage);
        const status = classifyStatus(signal);

        if (!['deactive', 'file_deleted'].includes(status)) {
            test.skip(true, `Page is not in deactive/file_deleted state — skip`);
            return;
        }

        expect(signal.hasAlert, 'Blocking alert must be visible').toBe(true);
        expect(signal.submitVisible, 'Accept button must NOT be visible').toBe(false);

        logStep(`Alert title: "${signal.alertTitle}"`, 'info');
        await takeScreenshot(sharedPage, `wf-${status}-alert`);
    });

});
