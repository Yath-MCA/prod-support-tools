/**
 * E2E Test Suite: Query & Comment Module
 * 
 * Verifies that the counts and statuses of queries and comments in the editor 
 * match what is displayed in the Query/Comment panel and the internal module state.
 */

import { test, expect } from '@playwright/test';
import fs from 'fs';
import {
    waitForEditorReady,
    waitForQueryPanelReady,
    getQueryCounts,
    getQueryPanelStatus,
    takeScreenshot,
    logStep,
    config
} from '../helpers/test-helpers.js';

const allSelectors = JSON.parse(fs.readFileSync('./tests/e2e/data/selectors.json', 'utf8'));
const landingSelectors = allSelectors.landing;

let initializeLandingEditorSession;
let cleanupLandingEditorSession;

const shared = {
    page: null,
    setupError: null,
    ready: false
};

function ensureReady() {
    if (shared.setupError) {
        throw new Error(shared.setupError);
    }
    if (!shared.ready || !shared.page) {
        throw new Error('Query/comment shared baseline setup did not complete');
    }
}

test.describe.serial('Query & Comment Module Synchronization Tests', () => {

    // Test timeout for this suite
    test.setTimeout(120000);

    test.beforeAll(async ({ browser, baseURL }) => {
        logStep('Preparing for Query & Comment test', 'start');

        const baseline = await import('./helpers/session-baseline.helper.js');
        initializeLandingEditorSession = baseline.initializeLandingEditorSession;
        cleanupLandingEditorSession = baseline.cleanupLandingEditorSession;

        const session = await initializeLandingEditorSession({
            browser,
            baseURL,
            selectors: landingSelectors
        });

        shared.page = session.page;
        shared.setupError = session.setupError;
        shared.ready = session.isInitialized;

        ensureReady();

        await waitForEditorReady(shared.page);
        await waitForQueryPanelReady(shared.page);
    });

    test.afterAll(async () => {
        if (cleanupLandingEditorSession) {
            await cleanupLandingEditorSession(shared.page);
        }
    });

    test('TC-QC-001 - Verify Initial Count and Status Synchronization', async () => {
        ensureReady();
        const page = shared.page;
        logStep('Starting TC-QC-001: Count and Status Sync Check', 'start');

        // 1. Get counts from Editor DOM (The source of truth)
        const domCounts = await getQueryCounts(page);
        logStep(`DOM Counts: Total Queries=${domCounts.total}, Open=${domCounts.open}, Closed=${domCounts.closed}, Comments=${domCounts.comments}`, 'info');

        // 2. Get counts from Internal State (queryModule._state)
        const panelStatus = await getQueryPanelStatus(page);
        const stateCounts = panelStatus.counts;
        logStep(`Internal State Counts: Total Queries=${stateCounts.total}, Open=${stateCounts.open}, Closed=${stateCounts.closed}, Comments=${stateCounts.comments}`, 'info');

        // 3. Get counts from UI Panel (What the user sees)
        const uiCounts = await page.evaluate((selectors) => {
            const getCount = (selector) => {
                const el = document.querySelector(selector);
                return el ? parseInt(el.textContent.replace(/\D/g, '') || '0', 10) : 0;
            };

            return {
                total: getCount(selectors.totalCount),
                open: getCount(selectors.openCount),
                closed: getCount(selectors.closedCount),
                comments: getCount(selectors.commentCount)
            };
        }, config.queryPanel);

        logStep(`UI Panel Counts: Total Queries=${uiCounts.total}, Open=${uiCounts.open}, Closed=${uiCounts.closed}, Comments=${uiCounts.comments}`, 'info');

        // --- Assertions: DOM vs State ---
        logStep('Verifying DOM vs Internal State synchronization...', 'check');
        expect(stateCounts.total).toBe(domCounts.total);
        expect(stateCounts.open).toBe(domCounts.open);
        expect(stateCounts.closed).toBe(domCounts.closed);
        expect(stateCounts.comments).toBe(domCounts.comments);

        // --- Assertions: State vs UI Panel ---
        logStep('Verifying Internal State vs UI Panel synchronization...', 'check');
        // Note: Sometimes UI might show total as open + closed or just a main count.
        // We expect them to be synchronized.
        expect(uiCounts.total).toBe(stateCounts.total);
        expect(uiCounts.open).toBe(stateCounts.open);
        expect(uiCounts.closed).toBe(stateCounts.closed);
        expect(uiCounts.comments).toBe(stateCounts.comments);

        logStep('TC-QC-001 synchronization check PASSED', 'success');
        await takeScreenshot(page, 'tc-qc-001-sync-success');
    });

    test('TC-QC-002 - Verify individual Query/Comment status and labels', async () => {
        ensureReady();
        const page = shared.page;
        logStep('Starting TC-QC-002: Individual Status and Label Check', 'start');

        // Get detailed mapping from DOM and State
        const syncDetails = await page.evaluate(() => {
            const results = {
                mismatches: [],
                queries: [],
                comments: []
            };

            if (!window.queryModule || !window.queryModule._state) {
                return { error: 'queryModule not initialized' };
            }

            const state = window.queryModule._state;
            const editorDoc = GlobalEditor.document.$;
            const domElements = editorDoc.querySelectorAll('[data-class="ckcommentsfull"]:not([data-ignore-comment])');

            domElements.forEach(el => {
                const id = el.getAttribute('id');
                const label = el.getAttribute('data-label');
                const status = (el.getAttribute('data-status') || '').toLowerCase();
                const isComment = status === 'comment' || status === 'note' || (label && label.startsWith('C'));

                const stateMap = isComment ? state.comments : state.queries;
                const stateItem = stateMap.get(id);

                const itemInfo = {
                    id,
                    label,
                    domStatus: status,
                    stateStatus: stateItem ? stateItem.status : 'MISSING',
                    match: stateItem && stateItem.status === status
                };

                if (!itemInfo.match) {
                    results.mismatches.push(itemInfo);
                }

                if (isComment) results.comments.push(itemInfo);
                else results.queries.push(itemInfo);
            });

            return results;
        });

        if (syncDetails.error) {
            throw new Error(syncDetails.error);
        }

        logStep(`Found ${syncDetails.queries.length} queries and ${syncDetails.comments.length} comments in DOM`, 'info');

        if (syncDetails.mismatches.length > 0) {
            logStep(`Found ${syncDetails.mismatches.length} status mismatches!`, 'error');
            console.table(syncDetails.mismatches);
        }

        expect(syncDetails.mismatches.length).toBe(0);
        logStep('All individual queries and comments are synchronized with internal state', 'success');

        // Check panel list items
        const panelItemsCount = await page.locator(config.queryPanel.queryItem).count();
        logStep(`Items found in UI Panel list: ${panelItemsCount}`, 'info');

        // The number of items in the panel should match total queries + comments (unless filtered)
        const totalExpected = syncDetails.queries.length + syncDetails.comments.length;

        // Note: Some panels might only show queries or comments depending on current active tab
        // Let's check which tab is active
        const activeTab = await page.evaluate((selectors) => {
            const queriesTab = document.querySelector(selectors.tabQueries);
            const commentsTab = document.querySelector(selectors.tabComments);

            if (queriesTab && (queriesTab.classList.contains('active') || queriesTab.classList.contains('selected'))) return 'queries';
            if (commentsTab && (commentsTab.classList.contains('active') || commentsTab.classList.contains('selected'))) return 'comments';
            return 'unknown';
        }, config.queryPanel);

        logStep(`Active tab in panel: ${activeTab}`, 'info');

        if (activeTab === 'queries') {
            expect(panelItemsCount).toBe(syncDetails.queries.length);
        } else if (activeTab === 'comments') {
            expect(panelItemsCount).toBe(syncDetails.comments.length);
        }

        logStep('TC-QC-002 status and label check PASSED', 'success');
    });

});
