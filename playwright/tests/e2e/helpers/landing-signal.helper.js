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

// Primary source: tests/e2e/data/links.json  (client → role name → status)
const linksPath = path.join(__dirname, '..', 'data', 'links.json');

// Fallback source: assets/links.json  (client → roleId → status — fully populated)
const assetsLinksPath = path.join(__dirname, '..', '..', '..', 'assets', 'links.json');
const rolesPath = path.join(__dirname, '..', '..', '..', 'assets', 'roles_details.js');

/**
 * Build a roleId → pubkit_name map from assets/roles_details.js.
 * e.g. "5b53536b4c4a803e9a5abf70" → "author"
 *
 * roles_details.js uses unquoted JS object keys — not valid JSON.
 * Use a targeted regex to extract only the fields we need.
 */
function buildRoleIdMap() {
    let raw;
    try { raw = readFileSync(rolesPath, 'utf8'); } catch { return {}; }
    const map = {};
    const re = /"([a-f0-9]{24})":\s*\{[^}]*pubkit_name:\s*"([^"]+)"/g;
    let m;
    while ((m = re.exec(raw)) !== null) {
        map[m[1]] = m[2].toLowerCase();
    }
    return map;
}

/**
 * Resolve URLs from assets/links.json using roleId → role name mapping.
 * Returns all URLs for client + role + status, or [] if none found.
 */
function pickFromAssets(client, role, status) {
    let assetLinks;
    try {
        assetLinks = JSON.parse(readFileSync(assetsLinksPath, 'utf8'));
    } catch {
        return [];
    }

    const roleIdMap = buildRoleIdMap();                  // id → "author" | "editor" …
    const clientData = assetLinks?.urls?.[client] || {};  // legacy: { roleId: { status: [...] } }
    const all = [];

    for (const [roleId, statusMap] of Object.entries(clientData)) {
        const resolvedRole = roleIdMap[roleId] || roleId;
        if (resolvedRole.toLowerCase() !== role.toLowerCase()) continue;
        const urls = statusMap[status] || [];
        all.push(...urls);
    }

    return all;
}

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
        const submitBtn = document.querySelector('#ValidateBtnOpt');
        const submitVisible = !!(submitBtn && submitBtn.offsetParent !== null);

        const alertContainer = document.querySelector('.swal2-container');
        const hasAlert = !!(alertContainer && alertContainer.offsetParent !== null);

        const alertTitle = document.querySelector('.swal2-title')?.textContent?.trim() || '';
        const alertText = document.querySelector('.swal2-html-container')?.textContent?.trim() || '';

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
 * Pick a URL for the given client + role + status.
 *
 * Resolution order:
 *   1. tests/e2e/data/links.json  (client → role name → status)
 *   2. assets/links.json          (client → roleId → status, resolved via roles_details.js)
 *
 * Returns a random URL from the matched pool, or null if none found.
 */
export function pickLink(client, role, status) {
    // 1 — check primary source
    let candidates = [];
    try {
        const links = JSON.parse(readFileSync(linksPath, 'utf8'));
        candidates = links[client]?.[role]?.[status] || [];
    } catch { /* file missing or malformed — fall through */ }

    // 2 — fallback to assets/links.json resolved via roleId map
    if (!candidates.length) {
        candidates = pickFromAssets(client, role, status);
    }

    if (!candidates.length) return null;
    return candidates[Math.floor(Math.random() * candidates.length)];
}

/**
 * Pick a URL from data/links.json only — no assets fallback.
 * Use this when you need a URL with a known, confirmed status
 * (e.g. signoff / deactive) and don't want stale assets URLs.
 *
 * Returns null if not found in data/links.json.
 */
export function pickLinkFromData(client, role, status) {
    try {
        const links = JSON.parse(readFileSync(linksPath, 'utf8'));
        const candidates = links[client]?.[role]?.[status] || [];
        if (!candidates.length) return null;
        return candidates[Math.floor(Math.random() * candidates.length)];
    } catch { return null; }
}

/**
 * Return ALL URLs for client + role + status (both sources merged).
 * Useful for running tests against the full URL pool.
 */
export function getAllLinks(client, role, status) {
    const primary = (() => {
        try {
            const links = JSON.parse(readFileSync(linksPath, 'utf8'));
            return links[client]?.[role]?.[status] || [];
        } catch { return []; }
    })();

    const fallback = pickFromAssets(client, role, status);

    // deduplicate
    return [...new Set([...primary, ...fallback])];
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
        title1: document.querySelector('#title1')?.textContent?.trim() || '',
        title2: document.querySelector('#title2')?.textContent?.trim() || '',
        authorname: document.querySelector('#authorname')?.textContent?.trim() || '',
        supportEmail: document.querySelector('#support_mail_id')?.textContent?.trim() || '',
        clientIconSrc: document.querySelector('.navbar-brand img')?.src || ''
    }));
}
