import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";
import os from "os";
import { loadSelectors } from "./helpers/config.helper.js";
import { resolveDocId, getEditorContext } from "./helpers/common.helper.js";
import {
    expectToastMessage
} from "./helpers/notification.helper.js";
import {
    initializeLandingEditorSession,
    cleanupLandingEditorSession
} from "./helpers/session-baseline.helper.js";
// import { registerAttachmentValidationCases } from "./comment-dialog-attachment-validation.cases";
import {
    waitForPageFullyLoaded,
    waitForEditorReady,
    waitForQueryPanelReady,
    getEditorStats,
    getQueryCounts,
    getQueryPanelStatus,
    clickAcceptButton,
    takeScreenshot,
    logStep,
    config
} from './helpers/test-helpers.js';

const landFinders = loadSelectors("landing");
const editorFinders = loadSelectors("editor6");
const commentPanelFinders = loadSelectors("commentPanel");
const queryDialogFinders = loadSelectors("query_comment_dialog");
const sweetToasterFinders = loadSelectors("sweetToaster");
const alertDialogFinders = loadSelectors("alert_dialog");

const SELECTORS = {
    root: queryDialogFinders.root,
    header: queryDialogFinders.header,
    label: queryDialogFinders.label,
    commentInput: queryDialogFinders.commentInput,
    attachBtn: queryDialogFinders.attachBtn,
    clearBtn: queryDialogFinders.clearBtn,
    insertBtn: queryDialogFinders.insertBtn,
    closeIcon: queryDialogFinders.closeIcon,
    fileInput: queryDialogFinders.fileInput,
    attachmentPreview: queryDialogFinders.attachmentPreview,
    attachmentCount: queryDialogFinders.attachmentCount,
    attachmentItem: queryDialogFinders.attachmentItem,
    attachmentItemName: queryDialogFinders.attachmentItemName,
    attachmentItemSize: queryDialogFinders.attachmentItemSize,
    attachmentRemoveBtn: queryDialogFinders.attachmentRemoveBtn,
    attachmentIcon: queryDialogFinders.attachmentIcon,
    toast: sweetToasterFinders.root,
    toastMessage: sweetToasterFinders.message,
    alertRoot: alertDialogFinders.root,
    alertMessage: alertDialogFinders.message,
    alertOk: alertDialogFinders.okButton,
    alertOutlineDangerBtn: alertDialogFinders.outlineDangerBtn,
    alertDangerBtn: alertDialogFinders.dangerBtn,
    alertSuccessBtn: alertDialogFinders.successBtn,
    swalDialog: alertDialogFinders.root,
    swalContent: alertDialogFinders.message,
    swalConfirmBtn: sweetToasterFinders.confirmButton,
    swalCancelBtn: alertDialogFinders.outlineDangerBtn,
    swalDangerBtn: `${alertDialogFinders.dangerBtn}, ${alertDialogFinders.outlineDangerBtn}`,

    comment_tab: commentPanelFinders.comment_tab,
    add_comment_btn: commentPanelFinders.add_comment,
};

const TEST_DATA = {
    randomText: `Test comment ${Date.now()}`,
    randomTextSecond: `Another comment ${Math.random().toString(36).slice(2, 10)}`,
    insertHeaderText: "Insert New Comment",
    editHeaderPrefix: "Edit Comment",
    downloadFolder: path.join(os.homedir(), "Downloads"),
    allowedImageExts: [".png", ".jpeg", ".jpg"],
    maxSingleFileSizeMb: 100,
    maxMultiFileSizeMb: 500
};

const shared = {
    page: null,
    DOC_ID: null,
    context: null,
    setupError: null,
    editorReady: false
};

function logSelector(name, selector) {
    console.log(`[selector] ${name}: ${selector}`);
}

function find(page, name, selector) {
    logSelector(name, selector);
    return page.locator(selector);
}

function ensureReady() {
    test.skip(!!shared.setupError, shared.setupError || "Baseline setup failed");
    test.skip(!shared.page || !shared.editorReady, "Editor is not ready for comment dialog tests");
}

function mbToBytes(mb) {
    return mb * 1024 * 1024;
}

function getFileSizeMb(filePath) {
    const stat = fs.statSync(filePath);
    return stat.size / (1024 * 1024);
}

function getRandomImagesFromDownloads(limit = 3, maxSingleMb = TEST_DATA.maxSingleFileSizeMb, maxTotalMb = TEST_DATA.maxMultiFileSizeMb) {
    if (!fs.existsSync(TEST_DATA.downloadFolder)) return [];
    const files = fs.readdirSync(TEST_DATA.downloadFolder);
    const images = files
        .filter((f) => TEST_DATA.allowedImageExts.includes(path.extname(f).toLowerCase()))
        .map((f) => path.join(TEST_DATA.downloadFolder, f))
        .filter((filePath) => getFileSizeMb(filePath) <= maxSingleMb);

    const randomized = images.sort(() => Math.random() - 0.5);
    const selected = [];
    let totalMb = 0;

    for (const imagePath of randomized) {
        const sizeMb = getFileSizeMb(imagePath);
        if (totalMb + sizeMb > maxTotalMb) continue;
        selected.push(imagePath);
        totalMb += sizeMb;
        if (selected.length >= limit) break;
    }

    return selected;
}

function createTempFile({ ext, sizeMb, fileNamePrefix }) {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "impact-e2e-"));
    const filePath = path.join(dir, `${fileNamePrefix}-${Date.now()}${ext}`);
    fs.writeFileSync(filePath, Buffer.from([0xff, 0xd8, 0xff, 0xd9]));
    if (sizeMb > 0) {
        fs.truncateSync(filePath, mbToBytes(sizeMb));
    }
    return filePath;
}

function cleanupTempFile(filePath) {
    try {
        if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
        const dir = path.dirname(filePath);
        if (fs.existsSync(dir)) fs.rmdirSync(dir);
    } catch (_e) {
    }
}

async function attachFilesToDialog(page, filePaths) {
    const chooserPromise = page.waitForEvent("filechooser", { timeout: 5000 }).catch(() => null);
    await find(page, "attach button", SELECTORS.attachBtn).first().click();
    const chooser = await chooserPromise;
    if (chooser) {
        await chooser.setFiles(filePaths);
        return;
    }

    const fileInput = find(page, "file input", SELECTORS.fileInput).first();
    // await expect(fileInput).toBeVisible({ timeout: 5000 });
    await fileInput.setInputFiles(filePaths);
}

async function ensureEditorSelection(page) {
    const iframeSelector = editorFinders.editorIframe;
    const iframe = find(page, "editor iframe", iframeSelector).first();
    await expect(iframe).toBeVisible({ timeout: 15000 });

    const handle = await iframe.elementHandle();
    const frame = await handle?.contentFrame();
    if (!frame) {
        throw new Error("Unable to resolve CKEditor iframe content frame");
    }

    await frame.waitForLoadState("domcontentloaded");
    console.log("[selector] editor frame body: body");
    await frame.locator("body").click({ timeout: 10000 });

    await frame.evaluate(() => {
        const root = document.body;
        if (!root) return;

        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        const firstText = walker.nextNode();

        const range = document.createRange();
        if (firstText && firstText.textContent) {
            range.setStart(firstText, 0);
            range.setEnd(firstText, 0);
        } else {
            range.selectNodeContents(root);
            range.collapse(true);
        }

        const selection = window.getSelection();
        selection?.removeAllRanges();
        selection?.addRange(range);
    });

    await page.waitForTimeout(200);
}

async function openNewCommentDialog(page) {
    const commentsTabBtn = find(page, "comments tab switch button", SELECTORS.comment_tab).first();
    if (await commentsTabBtn.isVisible().catch(() => false)) {
        await commentsTabBtn.click().catch(() => { });
    }

    const dialog = find(page, "comment dialog root", SELECTORS.root);
    const visible = await dialog.isVisible().catch(() => false);
    if (!visible) {
        const addCommentBtn = find(page, "add comment button", SELECTORS.add_comment_btn).first();
        await addCommentBtn.waitFor({ state: "visible", timeout: 15000 });
        await expect.poll(
            async () => (await addCommentBtn.getAttribute("data-click-evt")) || "",
            { timeout: 15000 }
        ).not.toBe("");
        await addCommentBtn.click();
    }

    await expect(dialog).toBeVisible({ timeout: 5000 });
}



async function typeIntoInput(page, text) {
    const input = find(page, "comment input", SELECTORS.commentInput);
    await expect(input).toBeVisible({ timeout: 2000 });
    console.log(`[test] typing into input: ${text}`);
    await input.click();
    await input.fill("");
    await input.type(text);
    return input;
}

async function closeDialog(page) {
    const closeBtn = find(page, "dialog close icon", SELECTORS.closeIcon).first();
    await expect(closeBtn).toBeVisible();
    console.log("[test] closing comment dialog");
    await closeBtn.click();
    await expect(find(page, "comment dialog root", SELECTORS.root)).toBeHidden({ timeout: 10000 });
}

test.describe.serial("Comment Module - Basic Testing Points ", () => {
    /*    const attachmentCases = registerAttachmentValidationCases({
           shared,
           ensureReady,
           ensureEditorSelection,
           openNewCommentDialog,
           find,
           selectors: SELECTORS,
           attachFilesToDialog
       }); */

    test.beforeAll(async ({ browser, baseURL }) => {
        let session = await initializeLandingEditorSession({ browser, baseURL, selectors: landFinders });

        if (!session.isInitialized && session.page) {
            const page = session.page;
            const continueBtn = find(page, "landing submit", landFinders.submit).first();
            const canContinue = await continueBtn.isVisible().catch(() => false);

            if (canContinue) {
                await continueBtn.click();
                await page.waitForLoadState("domcontentloaded");
                await find(page, "editor iframe", editorFinders.editorIframe).first().waitFor({ state: "visible", timeout: 45000 });

                const DOC_ID = await resolveDocId(page);
                const context = await getEditorContext(page, DOC_ID);

                session = {
                    ...session,
                    DOC_ID,
                    context,
                    isInitialized: true,
                    setupError: null
                };
            }
        }

        shared.page = session.page;
        shared.DOC_ID = session.DOC_ID;
        shared.context = session.context;
        shared.setupError = session.setupError;
        shared.editorReady = session.isInitialized;
    });

    /*     test.beforeEach(async () => {
            ensureReady();
        }); */


    test("IC000 wait for page fully loaded", async () => {
        await waitForPageFullyLoaded(shared.page);
    });

    test("IC000a click comments switch tab button and verify title", async () => {
        ensureReady();
        const commentsTabBtn = find(shared.page, "comments tab switch button", SELECTORS.comment_tab).first();
        await expect(commentsTabBtn).toBeVisible({ timeout: 10000 });
        await expect(commentsTabBtn).toHaveAttribute("title", "Use comments to share instructions and document attachments");
        await commentsTabBtn.click();
    });

    test("IC000b click add comment button and verify title", async () => {

        const addCommentBtn = find(shared.page, "add comment button", SELECTORS.add_comment_btn).first();
        await addCommentBtn.waitFor({ state: "visible", timeout: 15000 });
        await expect(addCommentBtn).toBeVisible({ timeout: 15000 });
        await expect(addCommentBtn).toHaveAttribute("title", "Add Comment");
        await expect.poll(
            async () => (await addCommentBtn.getAttribute("data-click-evt")) || "",
            { timeout: 15000 }
        ).not.toBe("");

        await addCommentBtn.click();
        console.log("[test] add comment button clicked, waiting for dialog...");
        await expect(find(shared.page, "comment dialog root", SELECTORS.root)).toBeVisible({ timeout: 5000 });
    });

    test("IC0001 - query dialog open and verify basic info", async () => {

        const dialog = find(shared.page, "comment dialog root", SELECTORS.root);
        await expect(dialog).toBeVisible({ timeout: 2000 });

        await expect(find(shared.page, "dialog header", SELECTORS.header)).toContainText(/new comment/i);
    });

    test("IC0002 - dialog label should match current role", async () => {
        const author = find(shared.page, "User label Checking at dialog", SELECTORS.label).first();
        if ((await author.count()) === 0) {
            test.skip();
            return;
        }
        const expectedRole = shared.context?.USER_INFO?.ROLE_NAME || "Author";
        console.log(`[test] expecting label to contain role: ${expectedRole}`);
        await expect(author).toContainText(new RegExp(expectedRole, "i"));
    });

    test("IC0003 Action buttons should be enabled [Attach,Clear,Insert]", async () => {

        await expect(find(shared.page, "attach button", SELECTORS.attachBtn).first()).toBeEnabled();
        await expect(find(shared.page, "clear button", SELECTORS.clearBtn).first()).toBeEnabled();
        await expect(find(shared.page, "insert button", SELECTORS.insertBtn).first()).toBeEnabled();
    });


    test("IC0005 type then clear should empty input", async () => {

        console.log("[test] typing into comment input and then clearing it");
        const input = await typeIntoInput(shared.page, TEST_DATA.randomText);

        await expect(input).toContainText(TEST_DATA.randomText);
        await find(shared.page, "clear button", SELECTORS.clearBtn).first().click();
        await expect(input).toHaveText("");
        await closeDialog(shared.page);
    });

    test("IC0008 insert with empty input shows warning", async () => {

        console.log("[test] inserting with empty input should show warning");

        const addCommentBtn = find(shared.page, "add comment button", SELECTORS.add_comment_btn).first();
        await addCommentBtn.click();
        const input = find(shared.page, "comment input", SELECTORS.commentInput);
        await input.fill("");
        await find(shared.page, "insert button", SELECTORS.insertBtn).first().click();

        const toast = find(shared.page, "toast", SELECTORS.toast).first();
        await expect(toast).toBeVisible({ timeout: 5000 });
        const msg = ((await find(shared.page, "toast message", SELECTORS.toastMessage).first().textContent()) || "").toLowerCase();
        expect(msg).toMatch(/comment|empty|required|cannot|insert/);
        // ── Wait for SweetAlert2 toast to auto-dismiss after 4000ms ──────────────
        await expect(toast).toBeHidden({ timeout: 6000 });
    });

    test.afterAll(async () => {
        // await attachmentCases.cleanupTempFiles();
        await cleanupLandingEditorSession(shared.page);
    });
});

/*
   test("IC0006 type attach random images then clear", async () => {

       // await openNewCommentDialog(shared.page);
       const input = await typeIntoInput(shared.page, TEST_DATA.randomTextSecond);
       await expect(input).not.toHaveText("");

       let images = getRandomImagesFromDownloads(3, TEST_DATA.maxSingleFileSizeMb, TEST_DATA.maxMultiFileSizeMb);
       let fallbackTempImage = null;

       if (images.length === 0) {
           fallbackTempImage = createTempFile({ ext: ".jpg", sizeMb: 1, fileNamePrefix: "ic0006-valid" });
           images = [fallbackTempImage];
       }

       const totalMb = images.reduce((sum, filePath) => sum + getFileSizeMb(filePath), 0);
       for (const imagePath of images) {
           expect(getFileSizeMb(imagePath)).toBeLessThanOrEqual(TEST_DATA.maxSingleFileSizeMb);
       }
       expect(totalMb).toBeLessThanOrEqual(TEST_DATA.maxMultiFileSizeMb);

       await attachFilesToDialog(shared.page, images);

       if (fallbackTempImage) {
           cleanupTempFile(fallbackTempImage);
       }

       // ─────────────────────────────────────────
       // VERIFY BEFORE CLEAR
       // ─────────────────────────────────────────

       const attachmentPreview = find(shared.page, "attachment preview", SELECTORS.attachmentPreview).first();
       const attachmentItems = find(shared.page, "attachment items", SELECTORS.attachmentItem);
       const fileInput = find(shared.page, "file input", SELECTORS.fileInput).first();

       // Preview container visible
       await expect(attachmentPreview).toBeVisible({ timeout: 1500 });
       // await expect(find(shared.page, "attachment preview visible", SELECTORS.attachmentPreview).first()).toBeVisible({ timeout: 500 });

       // Items rendered
       // await expect(attachmentItems).toHaveCount(images.length);

       // Attachment count text updated (defensive polling)
       await expect.poll(async () => {
           return await attachmentItems.count();
       }).toBe(images.length);

       // Optional: verify file input internal state
       await expect.poll(async () => {
           return await fileInput.evaluate((el) => el.files?.length || 0);
       }).toBe(images.length);

       await find(shared.page, "clear button", SELECTORS.clearBtn).first().click();
       await expect(input).toHaveText("");


   });

   
   
   test("IC0006a choose single image more than 100MB shows toaster", async () => {
       // ensureReady();
       // await ensureEditorSelection(shared.page);
       await openNewCommentDialog(shared.page);
       const input = await typeIntoInput(shared.page, `Oversize file check ${Date.now()}`);
       await expect(input).not.toHaveText("");

       const oversizedImage = createTempFile({ ext: ".jpg", sizeMb: 101, fileNamePrefix: "ic0006a-oversize" });
       try {
           expect(getFileSizeMb(oversizedImage)).toBeGreaterThan(TEST_DATA.maxSingleFileSizeMb);
           await attachFilesToDialog(shared.page, [oversizedImage]);
           await typeIntoInput(shared.page, `Oversize validation ${Date.now()}`);
           await find(shared.page, "insert button", SELECTORS.insertBtn).first().click();
           await expectToastMessage(
               shared.page,
               SELECTORS,
               /make sure the file size doesn't exceed 100 mb|100\s*mb|file size|exceed/,
               { type: "danger", text: /ok/i },
               logSelector
           );
       } finally {
           cleanupTempFile(oversizedImage);
       }

       await find(shared.page, "clear button", SELECTORS.clearBtn).first().click();
       await expect(input).toHaveText("");
   });

   test("IC0006c invalid extension is not allowed", async () => {
       ensureReady();
       // await ensureEditorSelection(shared.page);
       await openNewCommentDialog(shared.page);
       const input = await typeIntoInput(shared.page, `Invalid extension check ${Date.now()}`);
       await expect(input).not.toHaveText("");

       const invalidFile = createTempFile({ ext: ".exe", sizeMb: 1, fileNamePrefix: "ic0006c-invalid" });
       try {
           await attachFilesToDialog(shared.page, [invalidFile]);
           await typeIntoInput(shared.page, `Invalid extension validation ${Date.now()}`);
           await find(shared.page, "insert button", SELECTORS.insertBtn).first().click();
           await expectToastMessage(
               shared.page,
               SELECTORS,
               /invalid|extension|not allowed|unsupported|file type|exe|cannot/,
               { type: "danger", text: /ok/i },
               logSelector
           );
       } finally {
           cleanupTempFile(invalidFile);
       }

       await find(shared.page, "clear button", SELECTORS.clearBtn).first().click();
       await expect(input).toHaveText("");
   });

   test("IC0007 close icon should hide dialog", async () => {

       await closeDialog(shared.page);
   });

   

   test("IC0009  - insert with random text", async () => {


       const totalLocator = find(shared.page, "comments total", commentPanelFinders.total).first();

       const getTotalCount = async () => {
           const raw = (await totalLocator.textContent()) || "0";
           const parsed = Number.parseInt(raw.replace(/[^0-9]/g, ""), 10);
           return Number.isNaN(parsed) ? 0 : parsed;
       };

       await expect(totalLocator).toBeVisible({ timeout: 10000 });
       const beforeTotal = await getTotalCount();
       console.log(`[test] current total comments: ${beforeTotal}`);

       const addCommentBtn = find(shared.page, "add comment button", SELECTORS.add_comment_btn).first();
       await expect.poll(
           async () => (await addCommentBtn.getAttribute("data-click-evt")) || "",
           { timeout: 1000 }
       ).not.toBe("");
       await addCommentBtn.click();

       const input = find(shared.page, "comment input", SELECTORS.commentInput);
       const randomText = `IC0009-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
       await input.fill(randomText);
       await find(shared.page, "insert button", SELECTORS.insertBtn).first().click();

       await expect.poll(async () => await getTotalCount(), { timeout: 5000 }).toBe(beforeTotal + 1);

       const commentList = find(
           shared.page,
           "comment list",
           commentPanelFinders.comment_list
       ).first();
       await expect(commentList).toBeVisible({ timeout: 5000 });

       const commentItemsInList = commentList.locator(commentPanelFinders.comment_item);
       await expect(commentItemsInList.first()).toBeVisible({ timeout: 5000 });
       await expect.poll(async () => await commentItemsInList.count(), { timeout: 5000 }).toBeGreaterThan(0);

   });
 
       test("EDIT-01 header should show edit mode", async () => {
           ensureReady();
           const opened = await openEditCommentDialog(shared.page, 1);
           const header = shared.page.locator(SELECTORS.header);
           await expect(header).toContainText(/edit comment/i);
           const text = ((await header.textContent()) || "").toLowerCase();
           expect(text.includes((opened.label || "").toLowerCase()) || text.includes(TEST_DATA.editHeaderPrefix.toLowerCase())).toBeTruthy();
       });
   
       test("EDIT-02 author label should match current role", async () => {
           ensureReady();
           await openEditCommentDialog(shared.page, 1);
   
           const author = shared.page.locator(SELECTORS.authorLabel).first();
           if ((await author.count()) === 0) {
               test.skip();
               return;
           }
   
           const expectedRole = shared.context?.USER_INFO?.ROLE_NAME || "Author";
           await expect(author).toContainText(new RegExp(expectedRole, "i"));
       });
   
       test("EDIT-03 Attach Clear Insert buttons enabled", async () => {
           ensureReady();
           await openEditCommentDialog(shared.page, 1);
   
           await expect(shared.page.locator(SELECTORS.attachBtn).first()).toBeEnabled();
           await expect(shared.page.locator(SELECTORS.clearBtn).first()).toBeEnabled();
           await expect(shared.page.locator(SELECTORS.insertBtn).first()).toBeEnabled();
       });
   
       test("EDIT-04 insert with empty input shows warning", async () => {
           ensureReady();
           await openEditCommentDialog(shared.page, 1);
   
           const input = shared.page.locator(SELECTORS.commentInput);
           await input.fill("");
           await shared.page.locator(SELECTORS.insertBtn).first().click();
   
           const toast = shared.page.locator(SELECTORS.toast).first();
           await expect(toast).toBeVisible({ timeout: 5000 });
           const msg = ((await shared.page.locator(SELECTORS.toastMessage).first().textContent()) || "").toLowerCase();
           expect(msg).toMatch(/comment|empty|required|cannot|insert/);
       });
   
       test("EDIT-05 type then clear should empty input", async () => {
           ensureReady();
           await openEditCommentDialog(shared.page, 1);
   
           const input = await typeIntoInput(shared.page, TEST_DATA.randomText);
           await expect(input).toContainText(TEST_DATA.randomText);
           await shared.page.locator(SELECTORS.clearBtn).first().click();
           await expect(input).toHaveText("");
       });
   
       test("EDIT-06 type attach random images then clear", async () => {
           ensureReady();
           await openEditCommentDialog(shared.page, 1);
   
           const input = await typeIntoInput(shared.page, TEST_DATA.randomTextSecond);
           await expect(input).not.toHaveText("");
   
           const images = getRandomImagesFromDownloads(3);
           if (images.length > 0) {
               const chooserPromise = shared.page.waitForEvent("filechooser", { timeout: 5000 }).catch(() => null);
               await shared.page.locator(SELECTORS.attachBtn).first().click();
               const chooser = await chooserPromise;
               if (chooser) {
                   await chooser.setFiles(images);
               } else {
                   await expect(shared.page.locator(SELECTORS.fileInput)).toHaveCount(1);
               }
           }
   
           await shared.page.locator(SELECTORS.clearBtn).first().click();
           await expect(input).toHaveText("");
       });
   
       test("EDIT-07 close icon should hide dialog", async () => {
           ensureReady();
           await openEditCommentDialog(shared.page, 1);
           await closeDialog(shared.page);
       });
    */