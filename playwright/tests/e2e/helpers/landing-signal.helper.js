/**
 * Landing Page Signal Helpers
 *
 * Ported from LandingPageTest.java → getLandingSignalState()
 * Detects which workflow branch the landing page is in
 * based on DOM state after server validates the URL key.
 */

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import path from 'path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const linksPath = path.join(__dirname, '..', 'data', 'links.json');

/**
 * Evaluate the landing page DOM to determine workflow state.
 *
 * Returns:
 *  - submitVisible    — #ValidateBtnOpt is present and visible  (active non-PLOS flow)
 *  - hasAlert         — SweetAlert2 dialog is blocking the page  (signoff / deactive)
 *  - alertTitle       — Text content of .swal2-title
 *  - alertText        — Text content of .swal2-html-container
 *  - strictProofContext — URL contains "key" AND submit button is visible
 *  - url              — current page URL
 *  - sharedKey        — window.SHARED_KEY (client, rolename, article_id …)
 */
export async function getLandingSignalState(page) {
    return page.evaluate(() => {
        const submitBtn    = document.querySelector('#ValidateBtnOpt');
        const submitVisible = !!(submitBtn && submitBtn.offsetParent !== null);

        const alertContainer = document.querySelector('.swal2-container');
        const hasAlert = !!(alertContainer && alertContainer.offsetParent !== null);

        const alertTitle = document.querySelector('.swal2-title')?.textContent?.trim() || '';
        const alertText  = document.querySelector('.swal2-html-container')?.textContent?.trim() || '';

        const url = window.location.href;
        const strictProofContext = url.includes('key') && submitVisible;

        return {
            submitVisible,
            hasAlert,
            alertTitle,
            alertText,
            strictProofContext,
            url,
            sharedKey: window.SHARED_KEY || null
        };
    });
}

/**
 * Classify the workflow status from a signal state object.
 *
 * Returns: 'active' | 'signoff' | 'deactive' | 'file_deleted' | 'unknown'
 */
export function classifyStatus(signal) {
    if (!signal.hasAlert && signal.submitVisible) return 'active';

    if (signal.hasAlert) {
        const combined = `${signal.alertTitle} ${signal.alertText}`.toLowerCase();
        if (combined.includes('sign') || combined.includes('approved') || combined.includes('read-only')) {
            return 'signoff';
        }
        if (combined.includes('deleted') || combined.includes('file')) {
            return 'file_deleted';
        }
        if (combined.includes('deactive') || combined.includes('archive') || combined.includes('no longer')) {
            return 'deactive';
        }
    }

    return 'unknown';
}

/**
 * Pick a URL from links.json for the given client + role + status.
 * Falls back to null if no URLs are configured.
 */
export function pickLink(client, role, status) {
    const links = JSON.parse(readFileSync(linksPath, 'utf8'));
    const candidates = links[client]?.[role]?.[status] || [];
    if (!candidates.length) return null;
    // Pick a random entry from the list (matches Java's random selection pattern)
    return candidates[Math.floor(Math.random() * candidates.length)];
}

/**
 * Navigate to a landing page URL and verify the role matches via window.SHARED_KEY.
 * Returns the URL if role matches, null otherwise.
 *
 * Mirrors LandingPageTest.java → pickLinkForRole()
 */
export async function navigateAndVerifyRole(page, url, expectedRole) {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
    await page.waitForTimeout(2500);

    const foundRole = await page.evaluate(() => window.SHARED_KEY?.rolename).catch(() => null);
    if (!foundRole) return false;
    return foundRole.toLowerCase() === expectedRole.toLowerCase();
}

/**
 * Wait for the SweetAlert2 dialog to appear.
 */
export async function waitForStatusAlert(page, timeout = 15000) {
    await page.waitForSelector('.swal2-container', { state: 'visible', timeout });
}

/**
 * Click the OK / confirm button on a SweetAlert2 dialog.
 */
export async function dismissAlert(page) {
    const btn = page.locator('.swal2-confirm');
    await btn.waitFor({ state: 'visible', timeout: 10000 });
    await btn.click();
}

/**
 * Read article metadata displayed on the landing page.
 */
export async function getLandingPageContent(page) {
    return page.evaluate(() => ({
        title1:     document.querySelector('#title1')?.textContent?.trim()     || '',
        title2:     document.querySelector('#title2')?.textContent?.trim()     || '',
        authorname: document.querySelector('#authorname')?.textContent?.trim() || '',
        supportEmail: document.querySelector('#support_mail_id')?.textContent?.trim() || '',
        clientIconSrc: document.querySelector('.navbar-brand img')?.src || ''
    }));
}
