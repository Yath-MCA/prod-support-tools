import { test, expect } from "@playwright/test";
import { loadSelectors } from "./helpers/config.helper.js";
import {
    initializeLandingEditorSession,
    cleanupLandingEditorSession
} from "./helpers/session-baseline.helper.js";

const selectors = loadSelectors("landing");

// Global state - shared across all tests
let sharedContext = {
    page: null,
    DOC_ID: null,
    context: null,
    isInitialized: false,
    setupError: null,
    checkpoints: {}
};

function ensureReady() {
    if (sharedContext.setupError) {
        throw new Error(sharedContext.setupError);
    }
    if (!sharedContext.isInitialized || !sharedContext.page) {
        throw new Error("Baseline setup did not complete");
    }
}

test.describe("Landing → Proofing Page Validation", () => {

    // -------------------------------------------------
    // SETUP: Initialize browser & load landing page ONCE
    // -------------------------------------------------
    test.beforeAll(async ({ browser, baseURL }) => {
        const session = await initializeLandingEditorSession({ browser, baseURL, selectors });
        sharedContext.page = session.page;
        sharedContext.DOC_ID = session.DOC_ID;
        sharedContext.context = session.context;
        sharedContext.isInitialized = session.isInitialized;
        sharedContext.setupError = session.setupError;
        sharedContext.checkpoints = session.checkpoints || {};
    });

    // -------------------------------------------------
    // TEST 1: Landing page validation
    // -------------------------------------------------
    test("TEST 1: Landing page should load correctly", async () => {
        ensureReady();
        expect(sharedContext.checkpoints.landingLoaded).toBeTruthy();
        expect(sharedContext.checkpoints.landingValidated).toBeTruthy();
    });

    // -------------------------------------------------
    // TEST 2: Submit → redirect to editor
    // -------------------------------------------------
    test("TEST 2: Submit should redirect to editor page", async () => {
        ensureReady();
        expect(sharedContext.checkpoints.redirectedToEditor).toBeTruthy();
        await expect(sharedContext.page.locator("iframe.cke_wysiwyg_frame")).toBeVisible();
    });

    // -------------------------------------------------
    // TEST 3: Resolve DOC_ID
    // -------------------------------------------------
    test("TEST 3: DOC_ID should be resolved", async () => {
        ensureReady();
        expect(sharedContext.checkpoints.docResolved).toBeTruthy();
        expect(sharedContext.DOC_ID).toBeTruthy();
    });

    // -------------------------------------------------
    // TEST 4: Editor localStorage context
    // -------------------------------------------------
    test("TEST 4: Editor localStorage context should be valid", async () => {
        ensureReady();
        expect(sharedContext.checkpoints.contextValidated).toBeTruthy();
        expect(sharedContext.context.USER_INFO).toBeTruthy();
    });

    

  

    // -------------------------------------------------
    // CLEANUP: Close browser after all tests
    // -------------------------------------------------
    test.afterAll(async () => {
        await cleanupLandingEditorSession(sharedContext.page);
    });
});