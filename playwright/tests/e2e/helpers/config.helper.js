import fs from "fs";
import path from "path";

const PROJECT_ROOT = process.cwd();

/**
 * Load selectors by section name (e.g. landing, editor)
 */
export function loadSelectors(section) {
    const filePath = path.join(
        PROJECT_ROOT,
        "tests",
        "selectors.json"
    );

    const selectors = JSON.parse(
        fs.readFileSync(filePath, "utf8")
    );
    const aliases = {
        editor6: "editor",
        landingPage: "landing",
        querypanel: "queryPanel",
        queryPanel: "queryPanel"
    };

    const resolvedSection = selectors[section]
        ? section
        : aliases[section];

    console.log(`Loaded selectors for section: ${section}${resolvedSection && resolvedSection !== section ? ` (alias: ${resolvedSection})` : ""}`);

    if (!resolvedSection || !selectors[resolvedSection]) {
        throw new Error(`Selectors not found for section: ${section}`);
    }

    return selectors[resolvedSection];
}

/**
 * Load environment configuration
 */
export function loadEnvConfig() {
    const envName = process.env.ENV || "local";

    const filePath = path.join(
        PROJECT_ROOT,
        "unit-test-env.config.json"
    );

    const envs = JSON.parse(
        fs.readFileSync(filePath, "utf8")
    );

    if (!envs[envName]) {
        throw new Error(`Environment config not found: ${envName}`);
    }

    return envs[envName];
}
