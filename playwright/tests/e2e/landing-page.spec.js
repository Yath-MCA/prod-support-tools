import { test, expect } from "@playwright/test";
import fs from "fs";
import {
    shouldBeVisibleAndNotEmpty,
    checkImageHealthy,
    verifyMailLink,
    verifyPdfDownload
} from "./helpers/ui-validators.js";

const selectors = JSON.parse(
    fs.readFileSync("./tests/selectors.json", "utf8")
).landing;

let page;

test.describe.serial("Landing Page Suite", () => {

    test.beforeAll(async ({ browser, baseURL }) => {
        page = await browser.newPage();
        await page.goto(baseURL);
        await page.waitForLoadState("domcontentloaded");
        await page.waitForTimeout(6000);
    });

    /* ------------------------------
       Visibility Rules
    ------------------------------ */
    test("Client icon and submit visibility rule", async () => {
        const clientVisible = await page.locator(selectors.clientIcon)
            .isVisible()
            .catch(() => false);

        const submitVisible = await page.locator(selectors.submit)
            .isVisible()
            .catch(() => false);

        if (
            (clientVisible && submitVisible) ||
            (!clientVisible && !submitVisible)
        ) {
            expect(true).toBeTruthy();
        } else {
            test.fail(true, "Client icon and Submit visibility mismatch");
        }
    });

    /* ------------------------------
       Text Content Validations
    ------------------------------ */
    test("Title 1 should be visible and not empty", async () => {
        await shouldBeVisibleAndNotEmpty(page, selectors.title1, "Title 1");
    });

    test("Title 2 should be visible and not empty", async () => {
        await shouldBeVisibleAndNotEmpty(page, selectors.title2, "Title 2");
    });

    test("Author name should be visible and not empty", async () => {
        await shouldBeVisibleAndNotEmpty(page, selectors.authorname, "Author Name");
    });

    /* ------------------------------
       Media & Links
    ------------------------------ */
    test("Client icon image should not be broken", async () => {
        await checkImageHealthy(page, selectors.clientIcon, "Client Icon");
    });

    test("Support email should be a valid mailto link", async () => {
        await verifyMailLink(page, selectors.supportEmail, "Support Email");
    });

    /* ------------------------------
       Downloads (Optional)
    ------------------------------ */
    test("FAQ PDF should download successfully", async () => {
        await verifyPdfDownload(page, selectors.faqPdf, "FAQ PDF");
    });

    test("User Guide PDF should download successfully", async () => {
        await verifyPdfDownload(page, selectors.userGuidePdf, "User Guide PDF");
    });

    test.afterAll(async () => {
        await page.close();
    });
});
