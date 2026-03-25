import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const PROJECT_ROOT = path.resolve(__dirname, "..");

/**
 * Resolve DOC_ID from URL or localStorage
 */
export async function resolveDocId(page) {
    const url = page.url();
    const params = new URL(url).searchParams;

    let docId = params.get("docid") || params.get("DOC_ID");
    if (docId) return docId;

    return await page.evaluate(() => {
        const key = Object.keys(localStorage)
            .find(k => k.startsWith("xmleditor:username:"));
        return key ? key.split(":").pop() : null;
    });
}

/**
 * Read editor context from browser
 */
export async function getEditorContext(page, DOC_ID) {
    return page.evaluate(docId => ({
        DOC_ID: docId,
        USER_INFO: window.USER_INFO || null,
        SHARED_KEY: (() => {
            const data = localStorage.getItem(`xmleditor:shared:${docId}`);
            return data ? JSON.parse(data) : null;
        })()
    }), DOC_ID);
}

/**
 * Derive XML role key from USER_INFO
 */
export function deriveUserRoleKey(userInfo) {
    const roleMap = {
        Author: "AU",
        Collator: "CO",
        Copyeditor: "CE",
        "Production Manager": "PM",
        Editor: "ED",
        "Production Editor": "PE",
        "Journal Manager": "JM",
        Proofreader: "PR"
    };

    const roleKey = userInfo.SELECTOR_SHOW_HIDE || roleMap[userInfo.ROLE_NAME];

    if (!roleKey) {
        throw new Error(`Unknown role: ${userInfo.ROLE_NAME}`);
    }

    return roleKey;
}

/**
 * Resolve config.xml path from sharedKey
 */
export function resolveConfigPath(sharedKey) {
    return path.join(
        PROJECT_ROOT,
        "config",
        "journals",
        sharedKey.client.toLowerCase(),
        "config.xml"
    );
}
