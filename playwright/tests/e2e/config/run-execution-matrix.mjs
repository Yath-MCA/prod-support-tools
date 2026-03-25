import fs from "fs";
import path from "path";
import { spawnSync } from "child_process";

const root = process.cwd();
const matrixPath = path.join(root, "tests", "e2e", "config", "execution-matrix.config.json");

function parseArgs(argv) {
    const args = {
        workflow: null,
        role: null,
        testingType: null,
        browser: null,
        dryRun: false,
        useProject: false
    };

    for (let i = 0; i < argv.length; i++) {
        const cur = argv[i];
        const next = argv[i + 1];

        if (cur === "--workflow") args.workflow = next;
        if (cur === "--role") args.role = next;
        if (cur === "--testingType") args.testingType = next;
        if (cur === "--browser") args.browser = next;
        if (cur === "--dry-run") args.dryRun = true;
        if (cur === "--use-project") args.useProject = true;
    }

    return args;
}

function normalizeBrowserId(browserId) {
    if (!browserId) return "chrome";
    const id = browserId.toLowerCase();
    if (id === "firefox") return "firebox";
    return id;
}

function fail(msg) {
    console.error(`\n[execution-matrix] ${msg}`);
    process.exit(1);
}

if (!fs.existsSync(matrixPath)) {
    fail(`Config file not found: ${matrixPath}`);
}

const matrix = JSON.parse(fs.readFileSync(matrixPath, "utf8"));
const cli = parseArgs(process.argv.slice(2));

const workflows = matrix?.combinationAxes?.workflows || [];
const roles = matrix?.combinationAxes?.roles || [];
const testingTypes = matrix?.combinationAxes?.testingTypes || [];
const browsers = matrix?.combinationAxes?.browsers || [];
const defaults = matrix?.defaults || {};

const selected = {
    workflow: cli.workflow || defaults.workflow,
    role: cli.role || defaults.role,
    testingType: cli.testingType || defaults.testingType,
    browser: normalizeBrowserId(cli.browser || defaults.browser)
};

const workflow = workflows.find((w) => w.id === selected.workflow);
const roleOk = roles.includes(selected.role);
const testing = testingTypes.find((t) => t.id === selected.testingType);
const browser = browsers.find((b) => b.id === selected.browser);

if (!workflow) {
    fail(`Invalid workflow '${selected.workflow}'. Available: ${workflows.map((w) => w.id).join(", ")}`);
}
if (!roleOk) {
    fail(`Invalid role '${selected.role}'. Available: ${roles.join(", ")}`);
}
if (!testing) {
    fail(`Invalid testingType '${selected.testingType}'. Available: ${testingTypes.map((t) => t.id).join(", ")}`);
}
if (!browser) {
    fail(`Invalid browser '${selected.browser}'. Available: ${browsers.map((b) => b.id).join(", ")}`);
}

const profileName = `${selected.workflow}.${selected.role}.${selected.testingType}.${selected.browser}`;
const specs = testing.specs || [];

if (!specs.length) {
    fail(`No specs configured for testingType '${selected.testingType}'`);
}

const args = ["playwright", "test", ...specs];
const requestedProject = browser.playwrightProject || "chromium";

if (cli.useProject) {
    args.push("--project", requestedProject);
}

console.log("\n[execution-matrix] Selected profile");
console.log(`- profile: ${profileName}`);
console.log(`- workflow: ${workflow.label}`);
console.log(`- role: ${selected.role}`);
console.log(`- testingType: ${selected.testingType}`);
console.log(`- browser: ${selected.browser} -> ${requestedProject}`);
console.log(`- specs: ${specs.join(", ")}`);
console.log(`- useProject: ${cli.useProject ? "yes" : "no"}`);

const env = {
    ...process.env,
    TEST_WORKFLOW: selected.workflow,
    TEST_ROLE: selected.role,
    TESTING_TYPE: selected.testingType,
    TEST_BROWSER: selected.browser,
    TEST_PROFILE: profileName
};

if (cli.dryRun) {
    console.log("\n[execution-matrix] Dry run enabled. Command not executed.");
    console.log(`npx ${args.join(" ")}`);
    process.exit(0);
}

const run = spawnSync("npx", args, {
    stdio: "inherit",
    shell: true,
    env,
    cwd: root
});

if (run.error) {
    fail(`Execution failed: ${run.error.message}`);
}

process.exit(run.status ?? 0);
