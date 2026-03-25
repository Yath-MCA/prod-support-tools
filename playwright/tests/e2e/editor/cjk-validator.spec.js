/**
 * E2E Test Suite: CJK Validator
 * 
 * Test Flow:
 * 1. Landing page loads (from config baseURL)
 * 2. ✅ Validate Landing Page Elements (Titles, Icon, Email) using ui-validators
 * 3. Submit/Accept to enter editor
 * 4. Wait for editor ready
 * 5. Run CJK Validation tests
 */

import { test, expect } from "@playwright/test";
import {
    waitForCJKValidator,
    verifyCJKCount
} from "./helpers/ui-validators.js";
import { loadSelectors } from "./helpers/config.helper.js";
import {
    initializeLandingEditorSession,
    cleanupLandingEditorSession
} from "./helpers/session-baseline.helper.js";

const landingSelectors = loadSelectors("landing");

// Shared page across all tests
const shared = {
    page: null,
    setupError: null,
    ready: false,
    checkpoints: {}
};

function ensureReady() {
    if (shared.setupError) {
        throw new Error(shared.setupError);
    }
    if (!shared.ready || !shared.page) {
        throw new Error("CJK baseline setup did not complete");
    }
}

test.describe.serial("CJK Validator Suite (Integrated Flow)", () => {

    test.setTimeout(120000);

    test.beforeAll(async ({ browser, baseURL }) => {
        console.log("🚀 Starting CJK Validator Test Suite");

        const session = await initializeLandingEditorSession({
            browser,
            baseURL,
            selectors: landingSelectors
        });

        shared.page = session.page;
        shared.setupError = session.setupError;
        shared.ready = session.isInitialized;
        shared.checkpoints = session.checkpoints || {};
    });

    // ============================================
    // STEP 1: Landing Page Validation (Pre-requisite)
    // ============================================
    test("Step 1: Validate shared baseline checkpoints", async () => {
        ensureReady();
        expect(shared.checkpoints.landingLoaded).toBeTruthy();
        expect(shared.checkpoints.landingValidated).toBeTruthy();
        expect(shared.checkpoints.redirectedToEditor).toBeTruthy();
        expect(shared.checkpoints.docResolved).toBeTruthy();
        expect(shared.checkpoints.contextValidated).toBeTruthy();

        console.log("✅ Shared baseline checkpoints validated");
    });

    // ============================================
    // STEP 2: Enter Editor
    // ============================================
    test("Step 2: Editor and CJK validator are ready", async () => {
        ensureReady();
        const page = shared.page;
        await expect(page.locator("iframe.cke_wysiwyg_frame")).toBeVisible({ timeout: 15000 });
        await waitForCJKValidator(page);

        console.log("✅ Editor and CJK validator are ready");
    });

    // ============================================
    // STEP 3: CJK Validation Tests
    // ============================================

    test("CJK-TC001 - Class Existence", async () => {
        ensureReady();
        const page = shared.page;
        const exists = await page.evaluate(() => typeof CJKValidator !== "undefined");
        expect(exists).toBe(true);
    });

    test("CJK-TC002 - Basic Counting", async () => {
        ensureReady();
        const page = shared.page;
        await verifyCJKCount(page, "你好世界", 4);
        await verifyCJKCount(page, "Hello World", 0);
    });

    test("CJK-TC003 - Punctuation Exclusion", async () => {
        ensureReady();
        const page = shared.page;
        await verifyCJKCount(page, "【】「」", 0);
        await verifyCJKCount(page, "你好【世界】", 4);
    });

    test("CJK-TC005 - Valid Tracking (Insert)", async () => {
        ensureReady();
        const page = shared.page;
        const result = await page.evaluate(() => {
            const v = new CJKValidator();
            const original = document.createElement("div"); original.innerHTML = "<p>你好</p>";
            const updated = document.createElement("div"); updated.innerHTML = "<p>你好<insert>世界</insert></p>";
            return v.validateDocument(original, updated);
        });
        expect(result.document.isValid).toBe(true);
    });

    test("CJK-TC007 - Untracked Additions", async () => {
        ensureReady();
        const page = shared.page;
        const result = await page.evaluate(() => {
            const v = new CJKValidator();
            const original = document.createElement("div"); original.innerHTML = "<p>你好</p>";
            const updated = document.createElement("div"); updated.innerHTML = "<p>你好世界</p>"; // No tags
            return v.validateDocument(original, updated);
        });
        expect(result.document.isValid).toBe(false);
        expect(result.document.status).toBe("UNTRACKED_ADDITIONS");
    });

    test("CJK-TC009 - Nested Tags (del>insert)", async () => {
        ensureReady();
        const page = shared.page;
        const result = await page.evaluate(() => {
            const v = new CJKValidator();
            const original = document.createElement("div"); original.innerHTML = "";
            const updated = document.createElement("div");
            updated.innerHTML = `<del>text<insert>】</insert></del>`; // Nested pattern
            return v.validateDocument(original, updated);
        });
        // Should ignore or detect issue based on logic
        expect(result.document.nestedTagInfo.hasIssues).toBe(true);
        expect(result.document.nestedTagInfo.patterns).toContain("del>insert");
    });

    test.afterAll(async () => {
        await cleanupLandingEditorSession(shared.page);
    });
});
