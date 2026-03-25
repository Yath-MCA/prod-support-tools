import path from "path";
import { test, expect } from "@playwright/test";
import { loadSelectors } from "../helpers/config.helper.js";
import {
    initializeLandingEditorSession,
    cleanupLandingEditorSession
} from "../helpers/session-baseline.helper.js";
import {
    createModuleStatusTracker,
    finalizeModuleStatusReport,
    updateTemplateExecutionStatus
} from "../helpers/module-status.helper.js";

const selectors = loadSelectors("landing");
const templatePath = path.resolve(process.cwd(), "tests/e2e/config/master-template.query-comment.json");

const tracker = createModuleStatusTracker("query", {
    workflow: "Author → Editor → Collator",
    source: "Testcase_2026 - S640.csv"
});

const sharedContext = {
    page: null,
    DOC_ID: null,
    context: null,
    ready: false,
    setupError: null
};

function assertReady() {
    if (sharedContext.setupError) {
        throw new Error(sharedContext.setupError);
    }
    if (!sharedContext.ready || !sharedContext.page) {
        throw new Error("Query module setup did not complete");
    }
}

test.describe.serial("Landing → Editor → Query Module", () => {
    test.beforeAll(async ({ browser, baseURL }) => {
        const session = await initializeLandingEditorSession({ browser, baseURL, selectors });
        sharedContext.page = session.page;
        sharedContext.DOC_ID = session.DOC_ID;
        sharedContext.context = session.context;
        sharedContext.setupError = session.setupError;
        sharedContext.ready = session.isInitialized;
    });

    test.afterAll(async () => {
        const report = finalizeModuleStatusReport(tracker, { workspaceRoot: process.cwd() });
        updateTemplateExecutionStatus(templatePath, "query", tracker.cases);

        console.log("[query-module-status]", report.summary);

        await cleanupLandingEditorSession(sharedContext.page);
    });

    test("[TC_QUR_001] Landing flow opens editor and query module", async () => {
        assertReady();
        expect(sharedContext.ready).toBeTruthy();
        expect(sharedContext.DOC_ID).toBeTruthy();

        const health = await sharedContext.page.evaluate(() => ({
            queryModuleExists: !!window.queryModule,
            queryModuleInitialized: !!window.queryModule?.initialized,
            panelModuleExists: !!window.queryModule?.panelModule,
            queryMapSize: window.queryModule?._state?.queries?.size || 0
        }));

        expect(health.queryModuleExists).toBeTruthy();
        expect(health.queryModuleInitialized).toBeTruthy();
        expect(health.panelModuleExists).toBeTruthy();
        expect(health.queryMapSize).toBeGreaterThanOrEqual(0);
    });

    test("[TC_QUR_002] Query labels in editor and state are synchronized", async () => {
        assertReady();
        const result = await sharedContext.page.evaluate(() => {
            const mismatches = [];

            if (!window.queryModule?._state || !window.GlobalEditor?.document?.$) {
                return { error: "query module or editor not available" };
            }

            const editorDoc = GlobalEditor.document.$;
            const nodes = editorDoc.querySelectorAll('[data-class="ckcommentsfull"]:not([data-ignore-comment])');

            nodes.forEach((node) => {
                const id = node.getAttribute("id");
                const status = (node.getAttribute("data-status") || "").toLowerCase();
                if (status === "comment" || status === "note") return;

                const label = node.getAttribute("data-label");
                const stateNode = window.queryModule._state.queries.get(id);

                if (!stateNode || stateNode.label !== label) {
                    mismatches.push({
                        id,
                        editorLabel: label,
                        stateLabel: stateNode?.label || "MISSING"
                    });
                }
            });

            return {
                mismatches,
                totalChecked: nodes.length
            };
        });

        expect(result.error).toBeUndefined();
        expect(result.totalChecked).toBeGreaterThan(0);
        expect(result.mismatches).toEqual([]);
    });

    test("[TC_QUR_006] Query counts remain consistent between editor and state", async () => {
        assertReady();
        const result = await sharedContext.page.evaluate(() => {
            if (!window.queryModule?._state || !window.GlobalEditor?.document?.$) {
                return { error: "query module or editor not available" };
            }

            const editorDoc = GlobalEditor.document.$;
            const nodes = Array.from(editorDoc.querySelectorAll('[data-class="ckcommentsfull"]:not([data-ignore-comment])'));

            const openFromDom = nodes.filter((node) => (node.getAttribute("data-status") || "").toLowerCase() === "open").length;
            const closedFromDom = nodes.filter((node) => (node.getAttribute("data-status") || "").toLowerCase() === "closed").length;

            const stateQueries = Array.from(window.queryModule._state.queries.values()).filter((item) => !item.deleted);
            const openFromState = stateQueries.filter((item) => (item.status || "").toLowerCase() === "open").length;
            const closedFromState = stateQueries.filter((item) => (item.status || "").toLowerCase() === "closed").length;

            return {
                dom: { open: openFromDom, closed: closedFromDom },
                state: { open: openFromState, closed: closedFromState }
            };
        });

        expect(result.error).toBeUndefined();
        expect(result.dom.open).toBe(result.state.open);
        expect(result.dom.closed).toBe(result.state.closed);
    });

    test("[TC_QUR_016] Empty reply/comment content is blocked by validator", async () => {
        assertReady();
        const result = await sharedContext.page.evaluate(() => {
            if (!window.queryModule) {
                return { error: "query module missing" };
            }

            const blocked = window.queryModule.validateContentLength("", {
                MIN_CONTENT_LENGTH: 1
            });

            return {
                blocked
            };
        });

        expect(result.error).toBeUndefined();
        expect(result.blocked).toBe(false);
    });

    test("[TC_QUR_029] Single attachment >100MB is rejected", async () => {
        assertReady();
        const result = await sharedContext.page.evaluate(() => {
            if (!window.queryModule?.attachmentModule) {
                return { error: "attachment module missing" };
            }

            const oversized = {
                name: "oversized-proof.pdf",
                size: 101 * 1024 * 1024
            };

            return window.queryModule.attachmentModule.validateFile(oversized, 1);
        });

        expect(result.error).toBeUndefined();
        expect(result.valid).toBe(false);
        expect(result.error).toBe("Single_Upload_Size_Err");
    });

    test("[TC_QUR_030] Unsupported attachment extension is rejected", async () => {
        assertReady();
        const result = await sharedContext.page.evaluate(() => {
            if (!window.queryModule?.attachmentModule) {
                return { error: "attachment module missing" };
            }

            const invalid = {
                name: "malicious.exe",
                size: 10 * 1024
            };

            return window.queryModule.attachmentModule.validateFile(invalid, 1);
        });

        expect(result.error).toBeUndefined();
        expect(result.valid).toBe(false);
        expect(result.error).toBe("Upload_Invalid_Err");
    });

    test("[TC_QUR_031] Multi-attachment cumulative size limit is enforced", async () => {
        assertReady();
        const result = await sharedContext.page.evaluate(() => {
            if (!window.queryModule?.attachmentModule) {
                return { error: "attachment module missing" };
            }

            const mediumFile = {
                name: "large-image.tif",
                size: 110 * 1024 * 1024
            };

            return window.queryModule.attachmentModule.validateFile(mediumFile, 5);
        });

        expect(result.error).toBeUndefined();
        expect(result.valid).toBe(false);
        expect(result.error).toBe("Multi_Upload_Size_Err");
    });
});
