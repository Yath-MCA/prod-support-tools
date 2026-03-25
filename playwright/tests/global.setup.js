import { FullConfig } from "@playwright/test";
import { killChromium } from "./kill-chromium.js";

async function globalSetup(config) {
    // close any open chromium windows
    killChromium();
    const { baseURL } = config.projects[0].use;

    // const { chromium } = require("playwright");
    // const browser = await chromium.launch({ headless: false });
    // const page = await browser.newPage();

    // await page.goto(baseURL);

    // // Keep page open for test runner to attach
    // global.__BROWSER__ = browser;
    // global.__PAGE__ = page;
}

export default globalSetup;
