import path from "path";
import { test, expect } from "@playwright/test";
import { loadSelectors } from "./helpers/config.helper.js";
import {
    initializeLandingEditorSession,
    cleanupLandingEditorSession
} from "./helpers/session-baseline.helper.js";
import {
    createModuleStatusTracker,
    finalizeModuleStatusReport,
    updateTemplateExecutionStatus
} from "./helpers/module-status.helper.js";

const selectors = loadSelectors("landing");
const templatePath = path.resolve(process.cwd(), "tests/e2e/config/master-template.query-comment.json");

const tracker = createModuleStatusTracker("comment", {
    workflow: "Author → Editor → Collator",
    source: "Testcase_2026 - S640.csv"
});

const sharedContext = {
    page: null,
    ready: false,
    setupError: null
};

function assertReady() {
    if (sharedContext.setupError) {
        throw new Error(sharedContext.setupError);
    }
    if (!sharedContext.ready || !sharedContext.page) {
        throw new Error("Comment module setup did not complete");
    }
}

test.describe.serial("Landing → Editor → Comment Module", () => {
    test.beforeAll(async ({ browser, baseURL }) => {
        const session = await initializeLandingEditorSession({ browser, baseURL, selectors });
        sharedContext.page = session.page;
        sharedContext.setupError = session.setupError;
        sharedContext.ready = session.isInitialized;
    });

    test.afterAll(async () => {
        const report = finalizeModuleStatusReport(tracker, { workspaceRoot: process.cwd() });
        updateTemplateExecutionStatus(templatePath, "comment", tracker.cases);

        console.log("[comment-module-status]", report.summary);

        await cleanupLandingEditorSession(sharedContext.page);
    });

    test("[TC_QUR_007] Add comment creates comment item in comment map", async () => {
        assertReady();
        expect(sharedContext.ready).toBeTruthy();

        const result = await sharedContext.page.evaluate(async () => {
            if (!window.queryModule?._state) {
                return { error: "query module not initialized" };
            }

            const before = window.queryModule._state.comments.size;
            window.queryModule._state._current_process = "comment";

            const comment = await window.queryModule.createQuery({
                content: "Automation comment: initial add comment flow",
                status: "comment"
            });

            const after = window.queryModule._state.comments.size;

            return {
                commentId: comment?.id,
                status: comment?.status,
                before,
                after
            };
        });

        expect(result.error).toBeUndefined();
        expect(result.commentId).toBeTruthy();
        expect(result.status).toBe("comment");
        expect(result.after).toBe(result.before + 1);
    });

    test("[TC_QUR_012] Comment text with links/formatting content is preserved", async () => {
        assertReady();
        const result = await sharedContext.page.evaluate(async () => {
            if (!window.queryModule?._state) {
                return { error: "query module not initialized" };
            }

            window.queryModule._state._current_process = "comment";

            const rawContent = "<b>Formatted</b> and <i>linked</i> text https://www.w3schools.com/xml/";
            const comment = await window.queryModule.createQuery({
                content: rawContent,
                status: "comment"
            });

            const stateComment = window.queryModule._state.comments.get(comment.id);

            return {
                commentId: comment.id,
                storedContent: stateComment?.content || "",
                hasUrl: (stateComment?.content || "").includes("https://www.w3schools.com/xml/")
            };
        });

        expect(result.error).toBeUndefined();
        expect(result.commentId).toBeTruthy();
        expect(result.hasUrl).toBeTruthy();
        expect(result.storedContent.length).toBeGreaterThan(10);
    });

    test("[TC_QUR_017] Existing comment can be updated", async () => {
        assertReady();
        const result = await sharedContext.page.evaluate(async () => {
            if (!window.queryModule?._state) {
                return { error: "query module not initialized" };
            }

            window.queryModule._state._current_process = "comment";

            const comment = await window.queryModule.createQuery({
                content: "Initial editable comment",
                status: "comment"
            });

            const updatedText = "Updated editable comment content";
            const updateResult = await window.queryModule.updateQueryOrCommentItem(comment.id, {
                content: updatedText
            });

            const stateItem = window.queryModule._state.comments.get(comment.id);

            return {
                success: updateResult?.success,
                commentId: comment.id,
                content: stateItem?.content
            };
        });

        expect(result.error).toBeUndefined();
        expect(result.success).toBeTruthy();
        expect(result.commentId).toBeTruthy();
        expect(result.content).toContain("Updated editable comment content");
    });

    test("[TC_QUR_018] Comment can be deleted by same user", async () => {
        assertReady();
        const result = await sharedContext.page.evaluate(async () => {
            if (!window.queryModule?._state) {
                return { error: "query module not initialized" };
            }

            window.queryModule._state._current_process = "comment";

            const comment = await window.queryModule.createQuery({
                content: "To be deleted",
                status: "comment"
            });

            const before = window.queryModule._state.comments.size;
            await window.queryModule.deleteQueryOrComment(comment.id, { sameUser: true });
            const after = window.queryModule._state.comments.size;

            return {
                before,
                after,
                removed: !window.queryModule._state.comments.has(comment.id)
            };
        });

        expect(result.error).toBeUndefined();
        expect(result.removed).toBeTruthy();
        expect(result.after).toBe(result.before - 1);
    });

    test("[TC_QUR_016] Empty comment content is blocked", async () => {
        assertReady();
        const result = await sharedContext.page.evaluate(() => {
            if (!window.queryModule) {
                return { error: "query module missing" };
            }

            const valid = window.queryModule.validateContentLength("", {
                MIN_CONTENT_LENGTH: 1
            });

            return { valid };
        });

        expect(result.error).toBeUndefined();
        expect(result.valid).toBe(false);
    });

    test("[TC_QUR_043] Comment attachment metadata validation accepts supported files", async () => {
        assertReady();
        const result = await sharedContext.page.evaluate(() => {
            if (!window.queryModule?.attachmentModule) {
                return { error: "attachment module missing" };
            }

            const supported = {
                name: "query-comment-image.png",
                size: 5 * 1024 * 1024
            };

            return window.queryModule.attachmentModule.validateFile(supported, 1);
        });

        expect(result.error).toBeUndefined();
        expect(result.valid).toBe(true);
    });
});
