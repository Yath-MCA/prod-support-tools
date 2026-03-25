import fs from "fs";
import path from "path";

function toSafeFileDate(now = new Date()) {
    return now.toISOString().slice(0, 10).replace(/-/g, "_");
}

export function createWorkflowReporter(workflowName) {
    return {
        workflowName,
        startedAt: new Date().toISOString(),
        items: []
    };
}

export function addWorkflowItem(reporter, item) {
    reporter.items.push({
        ...item,
        createdAt: new Date().toISOString()
    });
}

export function writeWorkflowReport(reporter, options = {}) {
    const workspaceRoot = options.workspaceRoot || process.cwd();
    const reportDate = toSafeFileDate();
    const reportDir = path.join(workspaceRoot, "tests", "reports", "workflow-status", reportDate);

    fs.mkdirSync(reportDir, { recursive: true });

    const summary = {
        workflow: reporter.workflowName,
        startedAt: reporter.startedAt,
        completedAt: new Date().toISOString(),
        totalItems: reporter.items.length,
        passed: reporter.items.filter((i) => i.status === "passed").length,
        failed: reporter.items.filter((i) => i.status === "failed").length,
        skipped: reporter.items.filter((i) => i.status === "skipped").length
    };

    const payload = {
        summary,
        items: reporter.items
    };

    const filePath = path.join(reportDir, `${reporter.workflowName}.json`);
    fs.writeFileSync(filePath, JSON.stringify(payload, null, 2), "utf8");

    return {
        filePath,
        summary
    };
}
