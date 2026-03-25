import { expect } from "@playwright/test";

function toCaseInsensitiveRegex(value) {
    if (value instanceof RegExp) return value;
    if (typeof value !== "string") return null;
    const escaped = value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp(escaped, "i");
}

function locate(page, selector, label, logSelector) {
    if (logSelector) logSelector(label, selector);
    return page.locator(selector).first();
}

function getNotificationLocators(page, selectors, logSelector) {
    return {
        alertRoot: locate(page, selectors.alertRoot, "custom alert root", logSelector),
        toast: locate(page, selectors.toast, "toast", logSelector),
        alertMessage: locate(page, selectors.alertMessage, "custom alert message", logSelector),
        toastMessage: locate(page, selectors.toastMessage, "toast message", logSelector)
    };
}

async function getVisibleNotificationSource(locators) {
    if (await locators.alertRoot.isVisible().catch(() => false)) return "alert";
    if (await locators.toast.isVisible().catch(() => false)) return "toast";
    return "";
}

async function getNotificationMessage(locators, source) {
    if (source === "alert") {
        return ((await locators.alertMessage.textContent()) || "").toLowerCase();
    }
    return ((await locators.toastMessage.textContent()) || "").toLowerCase();
}

export async function handleCustomAlertConfirmation(page, selectors, options = {}, logSelector) {
    const locators = getNotificationLocators(page, selectors, logSelector);
    await expect(locators.alertRoot).toBeVisible({ timeout: 10000 });

    const outlineDangerBtn = locate(page, selectors.alertOutlineDangerBtn, "custom alert outline-danger button", logSelector);
    const dangerBtn = locate(page, selectors.alertDangerBtn, "custom alert danger button", logSelector);
    const successBtn = locate(page, selectors.alertSuccessBtn, "custom alert success button", logSelector);

    const buttonMap = {
        "outline-danger": outlineDangerBtn,
        danger: dangerBtn,
        sucess: successBtn,
        success: successBtn
    };

    const expectedType = options?.type;
    const expectedText = options?.text;
    const expectedTextRegex = toCaseInsensitiveRegex(expectedText);

    if (expectedType) {
        const targetButton = buttonMap[expectedType];
        if (!targetButton) {
            throw new Error(`Unknown custom alert button type: ${expectedType}`);
        }

        await expect(targetButton).toBeVisible({ timeout: 5000 });
        if (expectedTextRegex) {
            await expect(targetButton).toHaveText(expectedTextRegex);
        }
        await targetButton.click().catch(() => { });
        return;
    }

    const visibleButtons = [];
    if (await outlineDangerBtn.isVisible().catch(() => false)) visibleButtons.push("outline-danger");
    if (await dangerBtn.isVisible().catch(() => false)) visibleButtons.push("danger");
    if (await successBtn.isVisible().catch(() => false)) visibleButtons.push("sucess");

    if (visibleButtons.length === 0) {
        const fallbackBtn = locate(page, selectors.alertOk, "custom alert fallback button", logSelector);
        await expect(fallbackBtn).toBeVisible({ timeout: 5000 });
        await fallbackBtn.click().catch(() => { });
        return;
    }

    if (visibleButtons.includes("danger")) {
        await expect(dangerBtn).toHaveText(/ok/i);
        await dangerBtn.click().catch(() => { });
        return;
    }

    if (visibleButtons.includes("sucess")) {
        await successBtn.click().catch(() => { });
        return;
    }

    await outlineDangerBtn.click().catch(() => { });
}

export async function expectToastMessage(page, selectors, pattern, customAlertConfirmationOptions = {}, logSelector) {
    const locators = getNotificationLocators(page, selectors, logSelector);

    await expect.poll(async () => await getVisibleNotificationSource(locators), { timeout: 15000 }).not.toBe("");
    const source = await getVisibleNotificationSource(locators);
    const message = await getNotificationMessage(locators, source);
    expect(message).toMatch(pattern);

    if (source === "alert") {
        await handleCustomAlertConfirmation(page, selectors, customAlertConfirmationOptions, logSelector);
    }
}
