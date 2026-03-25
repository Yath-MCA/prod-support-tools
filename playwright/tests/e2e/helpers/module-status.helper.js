import fs from "fs";
import path from "path";

function toSafeFileDate(now = new Date()) {
    return now.toISOString().slice(0, 10).replace(/-/g, "_");
}

function csvEscape(value) {
    const normalized = value == null ? "" : String(value);
    if (/[",\n]/.test(normalized)) {
        return `"${normalized.replace(/"/g, '""')}"`;
    }
    return normalized;
}

function toCsv(rows) {
    if (!rows.length) return "";

    const headers = Object.keys(rows[0]);
    const lines = [headers.join(",")];

    for (const row of rows) {
        lines.push(headers.map((h) => csvEscape(row[h])).join(","));
    }

    return `${lines.join("\n")}\n`;
}

export function extractCaseIdFromTitle(title = "") {
    const first = title.match(/\[(TC_[A-Z]+_\d+)\]/i);
    if (first?.[1]) return first[1].toUpperCase();

    const second = title.match(/(TC_[A-Z]+_\d+)/i);
    if (second?.[1]) return second[1].toUpperCase();

    return null;
}

export function createModuleStatusTracker(moduleName, options = {}) {
    return {
        moduleName,
        workflow: options.workflow || "Author → Editor → Collator",
        source: options.source || "master-template.query-comment.json",
        startedAt: new Date().toISOString(),
        cases: []
    };
}

export function pushCaseResult(tracker, testInfo, extras = {}) {
    const caseId = extras.caseId || extractCaseIdFromTitle(testInfo.title);
    const result = {
        module: tracker.moduleName,
        caseId: caseId || "UNMAPPED",
        title: testInfo.title,
        status: testInfo.status,
        expectedStatus: testInfo.expectedStatus,
        role: extras.role || "All",
        workflow: extras.workflow || tracker.workflow,
        browser: testInfo.project.name,
        durationMs: testInfo.duration,
        executedAt: new Date().toISOString(),
        notes: extras.notes || ""
    };

    tracker.cases.push(result);
    return result;
}

export function finalizeModuleStatusReport(tracker, options = {}) {
    const workspaceRoot = options.workspaceRoot || process.cwd();
    const writeCsv = options.writeCsv !== false;
    const reportDate = toSafeFileDate();
    const reportDir = path.join(workspaceRoot, "tests", "reports", "module-status", reportDate);

    fs.mkdirSync(reportDir, { recursive: true });

    const summary = {
        module: tracker.moduleName,
        workflow: tracker.workflow,
        source: tracker.source,
        startedAt: tracker.startedAt,
        completedAt: new Date().toISOString(),
        total: tracker.cases.length,
        passed: tracker.cases.filter((c) => c.status === "passed").length,
        failed: tracker.cases.filter((c) => c.status === "failed").length,
        skipped: tracker.cases.filter((c) => c.status === "skipped").length,
        timedOut: tracker.cases.filter((c) => c.status === "timedOut").length,
        interrupted: tracker.cases.filter((c) => c.status === "interrupted").length
    };

    const payload = {
        summary,
        cases: tracker.cases
    };

    const jsonPath = path.join(reportDir, `${tracker.moduleName}-module-status.json`);
    const csvPath = path.join(reportDir, `${tracker.moduleName}-module-status.csv`);

    fs.writeFileSync(jsonPath, JSON.stringify(payload, null, 2), "utf8");
    if (writeCsv) {
        fs.writeFileSync(csvPath, toCsv(tracker.cases), "utf8");
    }

    return {
        jsonPath,
        csvPath: writeCsv ? csvPath : null,
        summary
    };
}

export function updateTemplateExecutionStatus(templatePath, moduleName, cases = []) {
    if (!fs.existsSync(templatePath)) {
        return {
            updated: false,
            reason: `Template not found: ${templatePath}`
        };
    }

    const template = JSON.parse(fs.readFileSync(templatePath, "utf8"));
    const moduleCases = template?.modules?.[moduleName];

    if (!Array.isArray(moduleCases)) {
        return {
            updated: false,
            reason: `Module ${moduleName} not found in template`
        };
    }

    const byCaseId = new Map();
    for (const result of cases) {
        if (!result.caseId || result.caseId === "UNMAPPED") continue;
        byCaseId.set(result.caseId, result);
    }

    moduleCases.forEach((testCase) => {
        const run = byCaseId.get(testCase.id);
        if (!run) return;

        if (!testCase.execution) {
            testCase.execution = {};
        }

        testCase.execution.lastStatus = run.status;
        testCase.execution.lastRunAt = run.executedAt;
        testCase.execution.lastDurationMs = run.durationMs;
        testCase.execution.browser = run.browser;
    });

    template.meta = template.meta || {};
    template.meta.lastUpdatedAt = new Date().toISOString();

    fs.writeFileSync(templatePath, JSON.stringify(template, null, 2), "utf8");

    return {
        updated: true,
        templatePath
    };
}
