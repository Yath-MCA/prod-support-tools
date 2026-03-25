export async function getToolbarButtonState(editorFrame, buttonName) {
    // buttonName example: "save", "undo", "bold"
    const button = editorFrame.locator(
        `.cke_button__${buttonName}`
    );

    if (await button.count() === 0) {
        return "missing";
    }

    const classAttr = await button.getAttribute("class");

    if (classAttr.includes("cke_button_disabled")) {
        return "disabled";
    }

    if (classAttr.includes("cke_button_on")) {
        return "on";
    }

    if (classAttr.includes("cke_button_off")) {
        return "off";
    }

    return "unknown";
}

// -------------------------------------------------
// Helper: Execute editor operation
// -------------------------------------------------
async function executeEditorOperation(page, editorFrame, operation, content, section, selectedText) {
    const operations = {
        insert: async () => {
            // Simple text insertion
            await page.keyboard.type(content);
            return { success: true, message: "Text inserted" };
        },

        bold: async () => {
            if (!selectedText) {
                // Insert text first, then select and bold
                await page.keyboard.type(content);
                await page.keyboard.press("Control+A"); // Select all in section
            }
            await page.keyboard.press("Control+B");
            return { success: true, message: "Bold applied" };
        },

        italic: async () => {
            if (!selectedText) {
                await page.keyboard.type(content);
                await page.keyboard.press("Control+A");
            }
            await page.keyboard.press("Control+I");
            return { success: true, message: "Italic applied" };
        },

        bold_italic: async () => {
            if (!selectedText) {
                await page.keyboard.type(content);
                await page.keyboard.press("Control+A");
            }
            await page.keyboard.press("Control+B");
            await page.keyboard.press("Control+I");
            return { success: true, message: "Bold and Italic applied" };
        },

        comment: async () => {
            if (!selectedText) {
                await page.keyboard.type(content);
                await page.keyboard.press("Control+A");
            }
            
            // Trigger comment via toolbar or keyboard shortcut
            // Adjust based on your CKEditor plugin
            try {
                await page.keyboard.press("Control+Alt+C"); // Common comment shortcut
                return { success: true, message: "Comment inserted" };
            } catch {
                return { success: false, message: "Comment insertion not available" };
            }
        },

        insert_then_bold: async () => {
            await page.keyboard.type(content);
            await page.keyboard.press("Control+A");
            await page.keyboard.press("Control+B");
            return { success: true, message: "Text inserted and bolded" };
        }
    };

    const opFunc = operations[operation];
    if (!opFunc) {
        return { success: false, message: `Unknown operation: ${operation}` };
    }

    return await opFunc();
}