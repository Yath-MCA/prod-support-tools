import { defineConfig, devices } from "@playwright/test";
import fs from "fs";


// ---------------- Environment ----------------
const envName   = process.env.ENV || "local";
const envConfig = JSON.parse(
    fs.readFileSync("./unit-test-env.config.json", "utf8")
)[envName];
const browserFromConfig = envConfig.browser || "chromium";
// CI injects BASE_URL via secrets; local reads from envConfig
const baseURL = process.env.BASE_URL || envConfig.baseURL;
// const isCI = !!process.env.CI;
// const isHeaded = process.env.HEADED === "true";
// ---------------- Date-Time Folder Structure ----------------
const now = new Date();
const dayFolder = now.toISOString().slice(0, 10).replace(/-/g, "_"); // YYYY_MM_DD
const timeStamp = now.toTimeString().slice(0, 8).replace(/:/g, ""); // HHMMSS

// reports/YYYY_MM_DD/env_HHMMSS
const outputFolder = `tests/reports/${dayFolder}/${envName}_${timeStamp}`;

// ---------------- Browser Resolver ----------------
function resolveBrowserProject(name) {
    switch (name) {
        case "chromium":
            return { name: "chromium", use: { ...devices["Desktop Chrome"] } };
        case "firefox":
            return { name: "firefox", use: { ...devices["Desktop Firefox"] } };
        case "webkit":
            return { name: "webkit", use: { ...devices["Desktop Safari"] } };
        default:
            throw new Error(`Unknown browser: ${name}`);
    }
}

// ---------------- Playwright Config ----------------
export default defineConfig({
    testDir: "./tests",
    timeout: 30 * 2500,
    // globalSetup: './tests/global.setup.js',
    retries: envConfig.retries ?? 0,
    workers: envConfig.workers ?? 2,

    // Store screenshots, traces, videos per run
    outputDir: `${outputFolder}/artifacts`,

    reporter: [
        [
            "html",
            {
                outputFolder: `${outputFolder}/html`,
                open: "always"
            }
        ],
        [
            "json",
            {
                outputFile: `${outputFolder}/test-results.json`
            }
        ],
        ["list"]
    ],

    use: {
        baseURL,
        headless: false,
        trace: "on-first-retry",
        screenshot: "only-on-failure",
        video: "retain-on-failure"
    },
    fullyParallel: false,   // ⛔ disable file-level parallelism
    workers: 1,             // ⛔ only ONE worker globally

    projects: [
        resolveBrowserProject(browserFromConfig),
        // resolveBrowserProject("chromium"),
        // resolveBrowserProject("firefox"),
        // resolveBrowserProject("webkit")
    ]
});
