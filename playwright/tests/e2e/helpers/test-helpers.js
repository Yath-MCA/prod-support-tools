/**
 * Test Helper Functions for IMPACT Editor E2E Tests
 */

import config from '../fixtures/test-config.js';

/**
 * Wait for page to be fully loaded.
 * Checks for InitialLoadDialog.FullyLoaded flag.
 */
export async function waitForPageFullyLoaded(page, timeout = config.timeouts.pageLoad) {
    console.log('⏳ Waiting for page to fully load...');

    await page.waitForLoadState('domcontentloaded');
    await page.waitForLoadState('networkidle', { timeout });

    await page.waitForFunction(() => {
        return (
            typeof window.InitialLoadDialog !== 'undefined' &&
            window.InitialLoadDialog.FullyLoaded === true
        );
    }, { timeout });

    const overlay = page.locator(config.initialLoad.overlay);
    await overlay.waitFor({ state: 'hidden', timeout: 10000 }).catch(() => {
        console.log('Loading overlay already hidden or not present');
    });

    console.log('✅ Page fully loaded');
}

/**
 * Wait for CKEditor (GlobalEditor) to be ready.
 */
export async function waitForEditorReady(page, timeout = config.timeouts.editorReady) {
    console.log('⏳ Waiting for editor to be ready...');

    await page.waitForFunction(() => {
        return (
            typeof GlobalEditor !== 'undefined' &&
            GlobalEditor !== null &&
            GlobalEditor.document &&
            GlobalEditor.document.$
        );
    }, { timeout });

    const editorInstance = page.locator(config.editor6.editorInstance).first();
    await editorInstance.waitFor({ state: 'visible', timeout: 10000 });

    console.log('✅ Editor is ready');
}

/**
 * Wait for query panel module to be initialised.
 */
export async function waitForQueryPanelReady(page, timeout = config.timeouts.panelLoad) {
    console.log('⏳ Waiting for query panel to be ready...');

    await page.waitForFunction(() => {
        return (
            typeof window.queryModule !== 'undefined' &&
            window.queryModule !== null &&
            window.queryModule.initialized === true
        );
    }, { timeout });

    console.log('✅ Query panel is ready');
}

/**
 * Get editor statistics from the page.
 */
export async function getEditorStats(page) {
    return page.evaluate(() => {
        const stats = {
            editorExists:           false,
            editorDocument:         false,
            queryModuleExists:      false,
            queryModuleInitialized: false,
            panelModuleExists:      false
        };

        if (typeof GlobalEditor !== 'undefined' && GlobalEditor) {
            stats.editorExists    = true;
            stats.editorDocument  = !!(GlobalEditor.document && GlobalEditor.document.$);
        }

        if (typeof window.queryModule !== 'undefined' && window.queryModule) {
            stats.queryModuleExists      = true;
            stats.queryModuleInitialized = window.queryModule.initialized === true;
            stats.panelModuleExists      = !!(window.queryModule.panelModule);
        }

        return stats;
    });
}

/**
 * Get query counts from the editor DOM and queryModule state.
 */
export async function getQueryCounts(page) {
    return page.evaluate(() => {
        const counts = {
            total:   0,
            open:    0,
            closed:  0,
            comments: 0,
            inState: { queries: 0, comments: 0 }
        };

        const editorDoc = GlobalEditor && GlobalEditor.document && GlobalEditor.document.$
            ? GlobalEditor.document.$
            : document;

        const allQueries = editorDoc.querySelectorAll(
            '[data-class="ckcommentsfull"]:not([data-ignore-comment])'
        );

        allQueries.forEach(query => {
            const status = (query.getAttribute('data-status') || '').toLowerCase();
            if (status === 'comment' || status === 'note') {
                counts.comments++;
            } else {
                counts.total++;
                if (status === 'open')   counts.open++;
                else if (status === 'closed') counts.closed++;
            }
        });

        if (typeof window.queryModule !== 'undefined' && window.queryModule._state) {
            const state = window.queryModule._state;
            counts.inState.queries  = state.queries  ? state.queries.size  : 0;
            counts.inState.comments = state.comments ? state.comments.size : 0;
        }

        return counts;
    });
}

/**
 * Get query panel status from queryModule.
 */
export async function getQueryPanelStatus(page) {
    return page.evaluate(() => {
        const status = {
            isVisible:      false,
            isInitialized:  false,
            hasQueries:     false,
            hasComments:    false,
            counts:         null,
            cacheStats:     null
        };

        if (typeof window.queryModule !== 'undefined' && window.queryModule) {
            const qm = window.queryModule;
            status.isInitialized = qm.initialized === true;

            if (qm.panelModule) {
                status.isVisible = true;
                if (typeof qm.getCounts === 'function')                  status.counts     = qm.getCounts();
                if (typeof qm.panelModule.getCacheStats === 'function')  status.cacheStats = qm.panelModule.getCacheStats();
            }

            if (qm._state) {
                status.hasQueries  = qm._state.queries  && qm._state.queries.size  > 0;
                status.hasComments = qm._state.comments && qm._state.comments.size > 0;
            }
        }

        return status;
    });
}

/**
 * Click the accept button on the landing page.
 * Uses the selector from test-config landing.acceptButton.
 */
export async function clickAcceptButton(page) {
    console.log('🖱️ Looking for accept button...');
    const acceptBtn = page.locator(config.landing.acceptButton).first();
    await acceptBtn.waitFor({ state: 'visible', timeout: config.timeouts.elementVisible });
    await acceptBtn.click();
    console.log('✅ Accept button clicked');
}

/**
 * Take a named screenshot saved to tests/reports/screenshots/.
 */
export async function takeScreenshot(page, name) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename  = `${name}-${timestamp}.png`;
    await page.screenshot({ path: `tests/reports/screenshots/${filename}`, fullPage: true });
    console.log(`📸 Screenshot saved: ${filename}`);
}

/**
 * Log a test step with a status icon.
 */
export function logStep(step, status = 'info') {
    const icons = {
        start:   '🚀',
        info:    'ℹ️',
        success: '✅',
        error:   '❌',
        warning: '⚠️',
        wait:    '⏳',
        check:   '🔍'
    };
    console.log(`${icons[status] || icons.info} ${step}`);
}

export { config };
