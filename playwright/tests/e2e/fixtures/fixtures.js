import { test as base } from "@playwright/test";

export const test = base.extend({
    page: async ({ page, baseURL }, use) => {
        await page.goto(baseURL);      // auto navigate
        await use(page);
    }
});
