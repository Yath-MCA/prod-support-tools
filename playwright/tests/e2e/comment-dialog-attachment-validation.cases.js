import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";
import os from "os";

const FILE_RULES = {
    MAX_SINGLE_FILE_SIZE_MB: 100,
    MAX_MULTI_FILE_SIZE_MB: 500,
    invalidExtensions: /\.(exe|bat|cmd|sh|dll)$/i,
    validExtensions: [".jpeg", ".jpg", ".docx", ".pdf"],
};

export function registerAttachmentValidationCases({
    shared,
    ensureReady,
    ensureEditorSelection,
    openNewCommentDialog,
    find,
    selectors,
    attachFilesToDialog
}) {
    const SEL = selectors;

    const tempFiles = [];
    let dialogIsOpen = false;

    function makeSyntheticFile(name, sizeMB) {
        const filePath = path.join(os.tmpdir(), `${Date.now()}-${name}`);
        fs.writeFileSync(filePath, Buffer.alloc(sizeMB * 1024 * 1024));
        tempFiles.push(filePath);
        return filePath;
    }

    async function cleanupTempFiles() {
        for (const filePath of tempFiles) {
            try {
                fs.unlinkSync(filePath);
            } catch (_e) {
            }
        }
    }

    async function ensureDialogOpen() {
        if (!dialogIsOpen) {
            await openNewCommentDialog(shared.page);
            dialogIsOpen = true;
            return;
        }

        const dialog = find(shared.page, "comment dialog root", SEL.root).first();
        if (!(await dialog.isVisible().catch(() => false))) {
            await openNewCommentDialog(shared.page);
            dialogIsOpen = true;
        }
    }

    async function expectNoValidationAlert() {
        const swal = find(shared.page, "swal dialog", SEL.swalDialog).first();
        await expect(swal).toBeHidden({ timeout: 1500 });
    }

    async function hasDangerVisual(locator) {
        return await locator.evaluate((element) => {
            const cls = (element.className || "").toString().toLowerCase();
            if (/danger|deny|btn-danger/.test(cls)) return true;

            const style = window.getComputedStyle(element);
            const bg = style.backgroundColor || "";
            const values = bg.match(/\d+/g)?.map(Number) || [];
            if (values.length < 3) return false;
            const [r, g, b] = values;
            return r >= 140 && r > g + 20 && r > b + 20;
        }).catch(() => false);
    }

    async function expectValidationAlertAndDismiss(messagePattern, dismissWith) {
        const swalDialog = find(shared.page, "swal dialog", SEL.swalDialog).first();
        const swalContent = find(shared.page, "swal content", SEL.swalContent).first();
        const confirmBtn = find(shared.page, "swal confirm button", SEL.swalConfirmBtn).first();
        const cancelBtn = find(shared.page, "swal cancel button", SEL.swalCancelBtn).first();
        const dangerBtns = find(shared.page, "swal danger buttons", SEL.swalDangerBtn);

        await expect(swalDialog).toBeVisible({ timeout: 10000 });
        await expect(swalContent).toBeVisible({ timeout: 10000 });

        const message = ((await swalContent.textContent()) || "").toLowerCase();
        expect(message).toMatch(messagePattern);

        const dangerCount = await dangerBtns.count();
        expect(dangerCount).toBeGreaterThan(0);

        let dangerFound = false;
        for (let index = 0; index < dangerCount; index++) {
            const btn = dangerBtns.nth(index);
            if (await btn.isVisible().catch(() => false)) {
                const looksDanger = await hasDangerVisual(btn);
                if (looksDanger) {
                    dangerFound = true;
                    break;
                }
            }
        }
        expect(dangerFound).toBeTruthy();

        if (dismissWith === "confirm") {
            await expect(confirmBtn).toBeVisible({ timeout: 5000 });
            await confirmBtn.click();
        } else if (dismissWith === "cancel") {
            await expect(cancelBtn).toBeVisible({ timeout: 5000 });
            await cancelBtn.click();
        } else {
            if (await confirmBtn.isVisible().catch(() => false)) {
                await confirmBtn.click();
            } else if (await cancelBtn.isVisible().catch(() => false)) {
                await cancelBtn.click();
            } else {
                await dangerBtns.first().click();
            }
        }

        await expect(swalDialog).toBeHidden({ timeout: 10000 });
    }

    async function verifyAttachmentPreview(expectedCount, expectedFilenames) {
        const preview = find(shared.page, "attachment preview", SEL.attachmentPreview).first();
        const count = find(shared.page, "attachment count", SEL.attachmentCount).first();

        await expect(preview).toBeVisible({ timeout: 10000 });
        await expect(count).toContainText(String(expectedCount));

        const itemLocators = [];
        for (const filename of expectedFilenames) {
            const items = find(shared.page, `attachment items for ${filename}`, SEL.attachmentItem);
            const itemByName = items.filter({ hasText: filename }).first();
            const itemByAttribute = shared.page.locator(`${SEL.attachmentItem}[data-filename="${filename}"]`).first();
            const item = (await itemByName.isVisible().catch(() => false)) ? itemByName : itemByAttribute;

            await expect(item).toBeVisible({ timeout: 10000 });
            await expect(item.locator(SEL.attachmentIcon).first()).toBeVisible({ timeout: 10000 });
            await expect(item.locator(SEL.attachmentRemoveBtn).first()).toBeVisible({ timeout: 10000 });
            itemLocators.push(item);
        }

        return itemLocators;
    }

    async function expectAttachmentPreviewRejected() {
        const preview = find(shared.page, "attachment preview", SEL.attachmentPreview).first();
        const count = find(shared.page, "attachment count", SEL.attachmentCount).first();

        const previewVisible = await preview.isVisible().catch(() => false);
        if (!previewVisible) {
            await expect(preview).toBeHidden({ timeout: 5000 });
            return;
        }

        const countText = ((await count.textContent()) || "").replace(/\s+/g, "").trim();
        expect(["0", "", "(0)"]).toContain(countText);
    }

    async function clearAllAttachmentsIfAny() {
        const preview = find(shared.page, "attachment preview", SEL.attachmentPreview).first();
        if (!(await preview.isVisible().catch(() => false))) return;

        const removeButtons = find(shared.page, "attachment remove buttons", `${SEL.attachmentItem} ${SEL.attachmentRemoveBtn}`);
        let loops = 0;
        while ((await removeButtons.count()) > 0 && loops < 15) {
            await removeButtons.first().click().catch(() => { });
            await shared.page.waitForTimeout(150);
            loops += 1;
        }
    }

    test("IA0001 — upload single valid JPEG (1 MB)", async () => {
        ensureReady();
        await ensureEditorSelection(shared.page);
        await ensureDialogOpen();

        await clearAllAttachmentsIfAny();
        const jpegPath = makeSyntheticFile("valid-ia0001.jpeg", 1);
        await attachFilesToDialog(shared.page, [jpegPath]);
        await expectNoValidationAlert();

        const items = await verifyAttachmentPreview(1, [path.basename(jpegPath)]);
        await items[0].locator(SEL.attachmentRemoveBtn).first().click();

        const preview = find(shared.page, "attachment preview", SEL.attachmentPreview).first();
        const count = find(shared.page, "attachment count", SEL.attachmentCount).first();
        if (await preview.isVisible().catch(() => false)) {
            await expect(count).toContainText(/0/);
        } else {
            await expect(preview).toBeHidden();
        }
    });

    test("IA0002 — upload single valid PDF (1 MB)", async () => {
        ensureReady();
        await ensureEditorSelection(shared.page);
        await ensureDialogOpen();

        await clearAllAttachmentsIfAny();
        const pdfPath = makeSyntheticFile("valid-ia0002.pdf", 1);
        await attachFilesToDialog(shared.page, [pdfPath]);
        await expectNoValidationAlert();

        const items = await verifyAttachmentPreview(1, [path.basename(pdfPath)]);
        await items[0].locator(SEL.attachmentRemoveBtn).first().click();
        await expectAttachmentPreviewRejected();
    });

    test("IA0003 — upload single valid DOCX (1 MB)", async () => {
        ensureReady();
        await ensureEditorSelection(shared.page);
        await ensureDialogOpen();

        await clearAllAttachmentsIfAny();
        const docxPath = makeSyntheticFile("valid-ia0003.docx", 1);
        await attachFilesToDialog(shared.page, [docxPath]);
        await expectNoValidationAlert();

        const items = await verifyAttachmentPreview(1, [path.basename(docxPath)]);
        await items[0].locator(SEL.attachmentRemoveBtn).first().click();
        await expectAttachmentPreviewRejected();
    });

    test("IA0004 — upload multiple valid files (1× JPEG + 1× PDF = 2 files)", async () => {
        ensureReady();
        await ensureEditorSelection(shared.page);
        await ensureDialogOpen();

        await clearAllAttachmentsIfAny();
        const jpgPath = makeSyntheticFile("valid-ia0004-a.jpg", 1);
        const pdfPath = makeSyntheticFile("valid-ia0004-b.pdf", 1);

        await attachFilesToDialog(shared.page, [jpgPath, pdfPath]);
        await expectNoValidationAlert();
        await verifyAttachmentPreview(2, [path.basename(jpgPath), path.basename(pdfPath)]);
    });

    test("IA0005 — upload single file EXACTLY at 100 MB boundary", async () => {
        ensureReady();
        await ensureEditorSelection(shared.page);
        await ensureDialogOpen();

        await clearAllAttachmentsIfAny();
        const boundaryPath = makeSyntheticFile("boundary-ia0005.jpg", FILE_RULES.MAX_SINGLE_FILE_SIZE_MB);

        await attachFilesToDialog(shared.page, [boundaryPath]);
        await expectValidationAlertAndDismiss(/file size|doesn't exceed|100 mb/i, "any");
        await expectAttachmentPreviewRejected();
    });

    test("IA0006 — upload single oversized file (101 MB JPEG)", async () => {
        ensureReady();
        await ensureEditorSelection(shared.page);
        await ensureDialogOpen();

        await clearAllAttachmentsIfAny();
        const oversizedPath = makeSyntheticFile("oversized-ia0006.jpeg", 101);

        await attachFilesToDialog(shared.page, [oversizedPath]);
        const confirmBtn = find(shared.page, "swal confirm button", SEL.swalConfirmBtn).first();
        const cancelBtn = find(shared.page, "swal cancel button", SEL.swalCancelBtn).first();
        await expect(confirmBtn).toBeVisible({ timeout: 10000 });
        await expect(cancelBtn).toBeVisible({ timeout: 10000 });

        await expectValidationAlertAndDismiss(/file size|doesn't exceed|100 mb/i, "confirm");
        await expectAttachmentPreviewRejected();
    });

    test("IA0007 — upload single oversized file, dismiss via cancel button", async () => {
        ensureReady();
        await ensureEditorSelection(shared.page);
        await ensureDialogOpen();

        await clearAllAttachmentsIfAny();
        const oversizedPath = makeSyntheticFile("oversized-ia0007.jpeg", 101);

        await attachFilesToDialog(shared.page, [oversizedPath]);
        await expectValidationAlertAndDismiss(/file size|doesn't exceed|100 mb/i, "cancel");
        await expectAttachmentPreviewRejected();
    });

    test("IA0008 — upload multiple files whose combined size exceeds 500 MB", async () => {
        ensureReady();
        await ensureEditorSelection(shared.page);
        await ensureDialogOpen();

        await clearAllAttachmentsIfAny();
        const files = [
            makeSyntheticFile("oversized-ia0008-1.jpg", 170),
            makeSyntheticFile("oversized-ia0008-2.jpg", 170),
            makeSyntheticFile("oversized-ia0008-3.jpg", 170)
        ];

        await attachFilesToDialog(shared.page, files);
        await expectValidationAlertAndDismiss(/500 mb|total|combined|exceeds|100 mb|file size/i, "any");
        await expectAttachmentPreviewRejected();
    });

    test("IA0009 — upload invalid extension (.exe renamed to test.exe)", async () => {
        ensureReady();
        await ensureEditorSelection(shared.page);
        await ensureDialogOpen();

        await clearAllAttachmentsIfAny();
        const invalidPath = makeSyntheticFile("test.exe", 1);

        await attachFilesToDialog(shared.page, [invalidPath]);
        await expectValidationAlertAndDismiss(/incorrect file format|check and upload/i, "any");
        await expectAttachmentPreviewRejected();
    });

    test("IA0010 — upload mix of valid + invalid extension in one batch", async () => {
        ensureReady();
        await ensureEditorSelection(shared.page);
        await ensureDialogOpen();

        await clearAllAttachmentsIfAny();
        const validPath = makeSyntheticFile("valid-ia0010.jpg", 1);
        const invalidPath = makeSyntheticFile("bad.bat", 1);

        await attachFilesToDialog(shared.page, [validPath, invalidPath]);
        await expectValidationAlertAndDismiss(/incorrect file format|check and upload/i, "any");
        await expectAttachmentPreviewRejected();
    });

    test("IA0011 — remove attachment after successful upload", async () => {
        ensureReady();
        await ensureEditorSelection(shared.page);
        await ensureDialogOpen();

        await clearAllAttachmentsIfAny();
        const jpgPath = makeSyntheticFile("valid-ia0011-a.jpg", 1);
        const pdfPath = makeSyntheticFile("valid-ia0011-b.pdf", 1);

        await attachFilesToDialog(shared.page, [jpgPath, pdfPath]);
        const [firstItem, secondItem] = await verifyAttachmentPreview(2, [path.basename(jpgPath), path.basename(pdfPath)]);

        await firstItem.locator(SEL.attachmentRemoveBtn).first().click();
        await expect(find(shared.page, "attachment count", SEL.attachmentCount).first()).toContainText("1");

        await secondItem.locator(SEL.attachmentRemoveBtn).first().click();
        await expectAttachmentPreviewRejected();
    });

    return {
        cleanupTempFiles
    };
}
