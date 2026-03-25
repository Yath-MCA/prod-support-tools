import { expect, Page } from "@playwright/test";
import { HELP_GROUP_CHILDREN } from "./constants.helper.js";


export function createSoftAssert() {
    const errors = [];

    function softAssert(condition, message) {
        if (!condition) {
            errors.push(message);
            console.error("✗ FAIL:", message);
        } else {
            console.log("✓ PASS:", message);
        }
    }

    return {
        softAssert,
        getErrors: () => errors
    };
}


export async function expandDropdownIfNeeded(page, parentId) {
    const parent = page.locator(`#${parentId}`);

    await parent.waitFor({ state: "visible", timeout: 10000 });

    const expanded = await parent.getAttribute("aria-expanded");
    if (expanded !== "true") {
        await parent.click();
    }
}

export async function validateMenuOptions(
    page,
    menuOptions,
    roleKey,
    softAssert
) {
    const excluded = new Set(HELP_GROUP_CHILDREN);

    for (const option of menuOptions) {
        if (excluded.has(option.name)) continue;
        if (option.name === "helpGroup") continue;

        const expected =
            option.roles[`showFor${roleKey}`] ?? false;

        const el = page.locator(`#${option.name}`);
        const visible =
            await el.count() > 0 &&
            await el.isVisible().catch(() => false);

        softAssert(
            visible === expected,
            `Menu ${option.name} expected=${expected}, actual=${visible}`
        );
    }
}
export async function validateHelpGroup(
    page,
    menuOptions,
    roleKey,
    softAssert
) {
    const parentConfig = menuOptions.find(m => m.name === "helpGroup");

    if (!parentConfig) {
        softAssert(false, "helpGroup missing in XML");
        return;
    }

    const expectedParent =
        parentConfig.roles[`showFor${roleKey}`] ?? false;

    const parent = page.locator("#helpGroup");
    const parentVisible = await parent.isVisible().catch(() => false);

    softAssert(
        parentVisible === expectedParent,
        `helpGroup expected=${expectedParent}, actual=${parentVisible}`
    );

    if (!parentVisible) return;

    await expandDropdownIfNeeded(page, "helpGroup");

    for (const childId of HELP_GROUP_CHILDREN) {
        const childConfig = menuOptions.find(m => m.name === childId);
        if (!childConfig) continue;

        const expected =
            childConfig.roles[`showFor${roleKey}`] ?? false;

        const el = page.locator(`#${childId}`);
        const visible =
            await el.count() > 0 &&
            await el.isVisible().catch(() => false);

        softAssert(
            visible === expected,
            `helpGroup → ${childId} expected=${expected}, actual=${visible}`
        );
    }
}
// Visible + Not empty
export async function shouldBeVisibleAndNotEmpty(page, selector, label) {
    const element = page.locator(selector);

    await expect(element, `${label} should be visible`).toBeVisible();

    let value = "";

    if (await element.evaluate(el => "value" in el)) {
        value = await element.inputValue();
    } else {
        value = await element.evaluate(
            el => el.innerText || el.textContent || ""
        );
    }

    value = value.trim();

    expect(
        value.length,
        `${label} is not empty.\nActual value: "${value}"`
    ).toBeGreaterThan(0);
}



// Image visible + not broken
export async function checkImageHealthy(page, selector, label) {
    const img = page.locator(selector);

    await expect(img, `${label} should be visible`).toBeVisible();

    const info = await img.evaluate((node) => ({
        complete: node.complete,
        naturalWidth: node.naturalWidth,
        src: node.currentSrc || node.src
    }));

    expect(
        info.complete && info.naturalWidth > 0,
        `${label} is not broken.\n` +
        `src: ${info.src}\n` +
        `naturalWidth: ${info.naturalWidth}`
    ).toBeTruthy();
}



// Validate mailto link
export async function verifyMailLink(page, selector, label) {
    const elem = page.locator(selector);

    await expect(elem, `${label} should be visible`).toBeVisible();

    const href = await elem.getAttribute("href");

    expect(
        href,
        `${label} should have href attribute`
    ).toBeTruthy();

    expect(
        href.toLowerCase(),
        `${label} should be a mailto link`
    ).toContain("mailto:");

    const email = href
        .split("?")[0]
        .replace(/^mailto:/i, "")
        .trim();

    expect(
        email.length,
        `${label} email address is not empty.\nActual value: "${email}"`
    ).toBeGreaterThan(0);

    if (href.includes("?")) {
        expect(
            href,
            `${label} mailto params should include subject or body`
        ).toMatch(/subject=|body=/i);
    }
}

// PDF download
export async function verifyPdfDownload(page, selector, label) {
    const elem = page.locator(selector);

    await expect(elem, `${label} should be visible`).toBeVisible();

    await elem.scrollIntoViewIfNeeded();

    const [download] = await Promise.all([
        page.waitForEvent("download"),
        elem.click()
    ]);

    const fileName = download.suggestedFilename();

    expect(
        fileName.toLowerCase(),
        `${label} downloaded file should be a PDF.\nActual filename: "${fileName}"`
    ).toMatch(/\.pdf$/);
}


// ============================================
// CJK Validation Helpers
// ============================================

/**
 * Wait for CJKValidator class to be available
 * @param {Page} page - Playwright page
 * @param {number} timeout - Timeout in ms
 */
export async function waitForCJKValidator(page, timeout = 30000) {
    await page.waitForFunction(() => {
        return typeof CJKValidator !== "undefined" && CJKValidator !== null;
    }, { timeout });
}

/**
 * Run CJK validation on editor content
 * @param {Page} page - Playwright page
 * @param {Object} options - Validation options
 * @returns {Promise<Object>} Validation result
 */
export async function runCJKValidation(page, options = {}) {
    return await page.evaluate((opts) => {
        if (typeof CJKValidator === "undefined") {
            return { error: "CJKValidator not available" };
        }

        if (typeof GlobalEditor === "undefined" || !GlobalEditor?.document?.$) {
            return { error: "Editor not available" };
        }

        try {
            const validator = new CJKValidator();
            const editorContent = GlobalEditor.document.$.body;

            // Get original content
            let originalContent;
            if (opts.originalHTML) {
                const tempDiv = document.createElement("div");
                tempDiv.innerHTML = opts.originalHTML;
                originalContent = tempDiv;
            } else if (window._originalEditorContent) {
                originalContent = window._originalEditorContent;
            } else {
                originalContent = editorContent.cloneNode(true);
            }

            const validationResult = validator.validateDocument(originalContent, editorContent);
            const debugResult = validator.debugCJK(editorContent.textContent);

            return {
                success: true,
                validation: {
                    isValid: validationResult.document?.isValid,
                    status: validationResult.document?.status,
                    untracked: validationResult.document?.untracked,
                    formula: validationResult.document?.formula,
                    nestedTagInfo: validationResult.document?.nestedTagInfo
                },
                debug: {
                    totalCJK: debugResult.willCount,
                    ideographs: debugResult.countedIdeographs,
                    punctuation: debugResult.excludedPunctuation
                }
            };
        } catch (error) {
            return { error: error.message };
        }
    }, options);
}

/**
 * Get CJK statistics from editor content
 * @param {Page} page - Playwright page
 * @returns {Promise<Object>} CJK statistics
 */
export async function getCJKStats(page) {
    return await page.evaluate(() => {
        if (typeof CJKValidator === "undefined") {
            return { error: "CJKValidator not available" };
        }

        if (typeof GlobalEditor === "undefined" || !GlobalEditor?.document?.$) {
            return { error: "Editor not available" };
        }

        const validator = new CJKValidator();
        const editorContent = GlobalEditor.document.$.body;
        const textContent = editorContent.textContent || "";

        const debug = validator.debugCJK(textContent);

        return {
            success: true,
            textLength: textContent.length,
            cjkStats: {
                total: debug.totalFound,
                ideographs: debug.countedIdeographs,
                punctuation: debug.excludedPunctuation,
                willCount: debug.willCount
            },
            trackingElements: {
                insertCount: editorContent.querySelectorAll("insert").length,
                delCount: editorContent.querySelectorAll("del").length,
                nestedInsertInDel: editorContent.querySelectorAll("del insert").length,
                nestedDelInInsert: editorContent.querySelectorAll("insert del").length
            }
        };
    });
}

/**
 * Store original editor content for later comparison
 * @param {Page} page - Playwright page
 */
export async function storeOriginalContent(page) {
    await page.evaluate(() => {
        if (typeof GlobalEditor !== "undefined" && GlobalEditor?.document?.$) {
            window._originalEditorContent = GlobalEditor.document.$.body.cloneNode(true);
        }
    });
}

/**
 * Verify CJK character count
 * @param {Page} page - Playwright page
 * @param {string} text - Text to check
 * @param {number} expectedCount - Expected CJK count
 */
export async function verifyCJKCount(page, text, expectedCount) {
    const count = await page.evaluate((t) => {
        const validator = new CJKValidator();
        return validator.countCJK(t);
    }, text);

    expect(count).toBe(expectedCount);
    return count;
}

/**
 * Verify character type using Unicode info
 * @param {Page} page - Playwright page
 * @param {string} char - Character to check
 * @param {string} expectedType - Expected type
 */
export async function verifyCharType(page, char, expectedType) {
    const info = await page.evaluate((c) => {
        const validator = new CJKValidator();
        return validator.getCharUnicodeInfo(c);
    }, char);

    expect(info.type).toBe(expectedType);
    return info;
}
