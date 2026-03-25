import { test, expect } from "@playwright/test";
import { loadSelectors } from "../helpers/config.helper.js";
import { workflowConfig } from "../config/workflow.config";
import {
    initializeLandingEditorSession,
    cleanupLandingEditorSession
} from "../helpers/session-baseline.helper.js";
import {
    createWorkflowReporter,
    writeWorkflowReport
} from "../helpers/workflow-report.helper.js";

const selectors = loadSelectors("landing");
const reporter = createWorkflowReporter("basic-workflow");

const shared = {
    page: null,
    DOC_ID: null,
    context: null,
    setupError: null,
    ready: false,
    editorReady: false,
    checkpoints: {}
};

function ensureReady() {
    if (shared.setupError) {
        throw new Error(shared.setupError);
    }
    if (!shared.ready || !shared.page) {
        throw new Error("Basic workflow setup did not complete");
    }
}

test.describe.serial("Basic Workflow: Landing -> Editor -> Module Testing", () => {
    test.beforeAll(async ({ browser, baseURL }) => {
        const session = await initializeLandingEditorSession({ browser, baseURL, selectors });
        shared.page = session.page;
        shared.DOC_ID = session.DOC_ID;
        shared.context = session.context;
        shared.setupError = session.setupError;
        shared.ready = session.isInitialized;
        shared.editorReady = session.isInitialized;
        shared.checkpoints = session.checkpoints || {};
    });

    test.afterAll(async () => {
        const result = writeWorkflowReport(reporter, { workspaceRoot: process.cwd() });
        console.log("[basic-workflow-report]", result.summary);
        await cleanupLandingEditorSession(shared.page);
    });

    test("Landing page loads and Accept button is visible", async () => {
        ensureReady();
        expect(shared.checkpoints.landingLoaded).toBeTruthy();
        expect(shared.checkpoints.landingValidated).toBeTruthy();
    });

    test("Accept redirects to editor6 and editor frame is ready", async () => {
        ensureReady();
        expect(shared.checkpoints.redirectedToEditor).toBeTruthy();
        await expect(shared.page.locator("iframe.cke_wysiwyg_frame")).toBeVisible();
    });

    test("Module registry is available with expected modules", async () => {
        ensureReady();
        test.skip(!shared.editorReady, "Skipped because editor was not reached from landing page");

        await shared.page.waitForFunction(() => {
            return typeof window.queryModule !== "undefined";
        }, { timeout: 20000 }).catch(() => null);

        const required = workflowConfig.basicWorkflow.requiredModules || [];
        const result = await shared.page.evaluate((requiredModules) => {
            const moduleRegistryExists = typeof moduleRegistry !== "undefined";
            const moduleSystemExists = typeof moduleSystem !== "undefined";

            const inspectEntries = (source) => {
                if (!source) {
                    return {
                        total: 0,
                        names: []
                    };
                }

                if (source instanceof Map) {
                    const names = Array.from(source.keys());
                    return { total: names.length, names };
                }

                if (typeof source === "object") {
                    const names = Object.keys(source);
                    return { total: names.length, names };
                }

                return { total: 0, names: [] };
            };

            const inspectRegistry = () => {
                if (!moduleRegistryExists || !moduleRegistry) {
                    return {
                        total: 0,
                        names: []
                    };
                }

                const candidates = [
                    moduleRegistry.modules,
                    moduleRegistry._modules,
                    moduleRegistry.registry,
                    moduleRegistry._registry
                ].filter(Boolean);

                for (const raw of candidates) {
                    const data = inspectEntries(raw);
                    if (data.total > 0) return data;
                }

                return { total: 0, names: [] };
            };

            const inspectModuleSystem = () => {
                if (!moduleSystemExists || !moduleSystem) {
                    return {
                        total: 0,
                        names: []
                    };
                }

                const candidates = [
                    moduleSystem.modules,
                    moduleSystem._modules,
                    moduleSystem.registry,
                    moduleSystem._registry
                ].filter(Boolean);

                for (const raw of candidates) {
                    const data = inspectEntries(raw);
                    if (data.total > 0) return data;
                }

                return { total: 0, names: [] };
            };

            const registryData = inspectRegistry();
            const systemData = inspectModuleSystem();
            const mergedNames = Array.from(new Set([...registryData.names, ...systemData.names]));
            const requiredStatus = requiredModules.map((name) => ({
                name,
                found: mergedNames.includes(name) ||
                    (name === "querySystem" && !!window.queryModule) ||
                    (name === "queryDialog" && !!window.queryModule?.dialogModule)
            }));

            return {
                moduleRegistryExists,
                moduleSystemExists,
                registryCount: registryData.total,
                registryNames: mergedNames,
                requiredStatus,
                queryModuleReady: !!window.queryModule?.initialized
            };
        }, required);

        expect(result.moduleRegistryExists || result.moduleSystemExists).toBeTruthy();
        expect(result.queryModuleReady).toBeTruthy();

        for (const item of result.requiredStatus) {
            expect(item.found).toBeTruthy();
        }
    });
});
