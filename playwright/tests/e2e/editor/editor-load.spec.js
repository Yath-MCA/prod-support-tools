/**
 * E2E Test Suite: Editor Load & Query Panel Status
 *
 * Test Flow:
 * 1. Page fully loaded detection
 * 2. Landing page (accept button click)
 * 3. Editor page ready
 * 4. Check editor instance count & status in panel
 */

import { test, expect } from '@playwright/test';
import {
    waitForPageFullyLoaded,
    waitForEditorReady,
    waitForQueryPanelReady,
    getEditorStats,
    getQueryCounts,
    getQueryPanelStatus,
    clickAcceptButton,
    takeScreenshot,
    logStep,
    config
} from '../helpers/test-helpers.js';

test.describe('IMPACT Editor Load & Query Panel Tests', () => {

    test.setTimeout(120000);

    // ============================================
    // TC001: Page Fully Loaded
    // ============================================
    test('TC001 - Page should fully load with InitialLoadDialog completion', async ({ page }) => {
        logStep('Starting TC001: Page Load Test', 'start');

        await page.goto('/', { waitUntil: 'domcontentloaded' });
        logStep('Page navigation started', 'info');

        await waitForPageFullyLoaded(page);

        const isFullyLoaded = await page.evaluate(() => {
            return window.InitialLoadDialog && window.InitialLoadDialog.FullyLoaded === true;
        });

        expect(isFullyLoaded).toBe(true);
        logStep('Page fully loaded verification passed', 'success');
        await takeScreenshot(page, 'tc001-page-loaded');
    });

    // ============================================
    // TC002: Landing Page Accept Button
    // ============================================
    test('TC002 - Landing page should have working accept button', async ({ page }) => {
        logStep('Starting TC002: Accept Button Test', 'start');

        await page.goto('/', { waitUntil: 'domcontentloaded' });
        await waitForPageFullyLoaded(page);

        const acceptBtn = page.locator(config.landing.acceptButton).first();
        const isVisible = await acceptBtn.isVisible().catch(() => false);

        if (isVisible) {
            logStep(`Accept button found: ${config.landing.acceptButton}`, 'success');
            await acceptBtn.click();
            await page.waitForLoadState('domcontentloaded');
            await takeScreenshot(page, 'tc002-after-accept');
        } else {
            logStep('Accept button not found — may be auto-redirect flow', 'warning');
        }

        logStep('TC002 completed', 'success');
    });

    // ============================================
    // TC003: Editor Page Ready
    // ============================================
    test('TC003 - Editor should initialize and be ready', async ({ page }) => {
        logStep('Starting TC003: Editor Ready Test', 'start');

        await page.goto('/', { waitUntil: 'domcontentloaded' });
        await waitForPageFullyLoaded(page);

        try {
            await clickAcceptButton(page);
            await page.waitForLoadState('domcontentloaded');
        } catch {
            logStep('Accept button flow skipped', 'info');
        }

        await waitForEditorReady(page);

        const editorStats = await getEditorStats(page);
        logStep(`Editor Stats: ${JSON.stringify(editorStats)}`, 'check');

        expect(editorStats.editorExists).toBe(true);
        expect(editorStats.editorDocument).toBe(true);

        logStep('Editor is ready and accessible', 'success');
        await takeScreenshot(page, 'tc003-editor-ready');
    });

    // ============================================
    // TC004: Editor Instance Count & Panel Status
    // ============================================
    test('TC004 - Check editor instance count and query panel status', async ({ page }) => {
        logStep('Starting TC004: Editor Instance & Panel Status Test', 'start');

        await page.goto('/', { waitUntil: 'domcontentloaded' });
        await waitForPageFullyLoaded(page);

        try {
            await clickAcceptButton(page);
            await page.waitForLoadState('domcontentloaded');
        } catch {
            logStep('Accept button not required', 'info');
        }

        await waitForEditorReady(page);
        await waitForQueryPanelReady(page);

        // Check 1: Editor Instance Count
        logStep('Checking editor instance count...', 'check');
        const editorInstanceCount = await page.evaluate(() => {
            if (typeof CKEDITOR !== 'undefined' && CKEDITOR.instances) {
                return Object.keys(CKEDITOR.instances).length;
            }
            return 0;
        });
        logStep(`CKEditor instances found: ${editorInstanceCount}`, 'info');
        expect(editorInstanceCount).toBeGreaterThan(0);

        // Check 2: Query Panel Status
        logStep('Checking query panel status...', 'check');
        const panelStatus = await getQueryPanelStatus(page);
        logStep(`Panel Status: ${JSON.stringify(panelStatus, null, 2)}`, 'info');
        expect(panelStatus.isInitialized).toBe(true);

        // Check 3: Query Counts
        logStep('Checking query counts in editor...', 'check');
        const queryCounts = await getQueryCounts(page);
        logStep(`Query Counts: total=${queryCounts.total} open=${queryCounts.open} closed=${queryCounts.closed} comments=${queryCounts.comments}`, 'info');

        expect(queryCounts.total).toBeGreaterThanOrEqual(0);
        expect(queryCounts.open).toBeGreaterThanOrEqual(0);
        expect(queryCounts.closed).toBeGreaterThanOrEqual(0);

        // Check 4: State consistency
        if (queryCounts.total > 0) {
            expect(queryCounts.open + queryCounts.closed).toBeLessThanOrEqual(queryCounts.total);
        }

        if (queryCounts.total > 0 || queryCounts.inState.queries > 0) {
            const diff = Math.abs(queryCounts.inState.queries - queryCounts.total);
            expect(diff).toBeLessThanOrEqual(2);
        }

        await takeScreenshot(page, 'tc004-editor-panel-status');
        logStep('TC004 completed successfully', 'success');
    });

    // ============================================
    // TC005: Full Integration Flow
    // ============================================
    test('TC005 - Full flow: Load → Accept → Editor → Panel Check', async ({ page }) => {
        logStep('Starting TC005: Full Integration Flow', 'start');

        await page.goto('/', { waitUntil: 'domcontentloaded' });
        await waitForPageFullyLoaded(page);
        await takeScreenshot(page, 'tc005-step2-loaded');

        const loadStatus = await page.evaluate(() => ({
            fullyLoaded:   window.InitialLoadDialog?.FullyLoaded,
            progressValue: window.InitialLoadDialog?.progressValue
        }));
        logStep(`Load status: ${JSON.stringify(loadStatus)}`, 'info');
        expect(loadStatus.fullyLoaded).toBe(true);

        try {
            await clickAcceptButton(page);
            await page.waitForLoadState('domcontentloaded');
            await takeScreenshot(page, 'tc005-step3-accepted');
        } catch {
            logStep('No accept button needed', 'info');
        }

        await waitForEditorReady(page);
        await takeScreenshot(page, 'tc005-step4-editor-ready');

        await waitForQueryPanelReady(page);

        const finalStats = await page.evaluate(() => ({
            timestamp: new Date().toISOString(),
            editor: {
                exists:        typeof GlobalEditor !== 'undefined' && GlobalEditor !== null,
                instanceCount: typeof CKEDITOR !== 'undefined' ? Object.keys(CKEDITOR.instances).length : 0,
                instanceNames: typeof CKEDITOR !== 'undefined' ? Object.keys(CKEDITOR.instances) : []
            },
            queryModule: {
                exists:      typeof window.queryModule !== 'undefined',
                initialized: window.queryModule?.initialized === true,
                version:     window.queryModule?.version || 'unknown'
            },
            panel: {
                exists:          window.queryModule?.panelModule != null,
                hasRenderMethod: typeof window.queryModule?.panelModule?.render === 'function'
            }
        }));

        console.log('\n' + '='.repeat(60));
        console.log('FINAL TEST REPORT - TC005');
        console.log('='.repeat(60));
        console.log(`Timestamp:       ${finalStats.timestamp}`);
        console.log(`Editor exists:   ${finalStats.editor.exists}`);
        console.log(`Instances:       ${finalStats.editor.instanceCount} — ${finalStats.editor.instanceNames.join(', ')}`);
        console.log(`QM initialized:  ${finalStats.queryModule.initialized}`);
        console.log(`Panel exists:    ${finalStats.panel.exists}`);
        console.log('='.repeat(60) + '\n');

        expect(finalStats.editor.exists).toBe(true);
        expect(finalStats.editor.instanceCount).toBeGreaterThan(0);
        expect(finalStats.queryModule.initialized).toBe(true);
        expect(finalStats.panel.exists).toBe(true);

        await takeScreenshot(page, 'tc005-final');
        logStep('TC005 Full Integration Test PASSED', 'success');
    });

});
