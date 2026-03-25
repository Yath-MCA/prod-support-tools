import fs from "fs";
import xml2js from "xml2js";

let cachedConfig = null;

/**
 * Load and cache XML config
 */
export async function loadXmlConfig(filePath) {
    if (cachedConfig) return cachedConfig;

    const xmlData = fs.readFileSync(filePath, "utf8");

    const parser = new xml2js.Parser({
        explicitArray: true,
        attrkey: "$",
        trim: true
    });

    cachedConfig = await parser.parseStringPromise(xmlData);
    return cachedConfig;
}

/**
 * Extract menu functionalities
 */
export function getMenuFunctionalities(parsed) {
    const list =
        parsed?.impact?.project?.[0]
            ?.menuoption?.[0]
            ?.functionality || [];

    return normalizeFunctionalities(list);
}

/**
 * Extract dialog functionalities
 */
export function getDialogFunctionalities(parsed) {
    const list =
        parsed?.impact?.project?.[0]
            ?.dialogs?.[0]
            ?.functionality || [];

    return normalizeFunctionalities(list);
}

/* ---------------- helpers ---------------- */

function normalizeFunctionalities(list) {
    return list.map(f => ({
        name: f.$?.name,
        show: toBool(f.$?.show),
        showTrackView: toBool(f.$?.showTrackView),
        roles: extractRoles(f.$),
        children: extractChildren(f)
    }));
}

function extractRoles(attrs = {}) {
    return Object.fromEntries(
        Object.entries(attrs)
            .filter(([k]) => k.startsWith("showFor"))
            .map(([k, v]) => [k, v === "true"])
    );
}

function extractChildren(node) {
    const children = {};
    Object.keys(node).forEach(k => {
        if (k !== "$") {
            children[k] = node[k].map(n => ({ ...n.$ }));
        }
    });
    return children;
}

function toBool(val) {
    return val === "true";
}
    