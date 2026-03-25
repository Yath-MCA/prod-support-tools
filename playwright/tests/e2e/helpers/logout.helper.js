import { expect } from "@playwright/test";

/**
 * Strict logout flow
 * - Handles profile → dropdown → confirm dialog
 * - Waits for DB save + redirect
 * - Safe to call before page.close()
 */
export async function logoutSafely(page) {
    if (!page || page.isClosed()) return;

    try {
        /* ------------------------------------
           STEP 1: Ensure page is ready
        ------------------------------------ */
        await page.waitForLoadState("domcontentloaded", { timeout: 15000 });

        /* ------------------------------------
           STEP 2: Profile icon visible
        ------------------------------------ */
        console.log("[logoutSafely] Checking for profile icon...");
        const profileIcon = page.locator("#profileGroup");
        await expect(
            profileIcon,
            "Profile icon should be visible"
        ).toBeVisible({ timeout: 10000 });

        /* ------------------------------------
           STEP 3: Click profile → show dropdown
        ------------------------------------ */
        await profileIcon.click();

        const profileDropdown = page.locator("#profileDiv.dropdown-menu");
        await expect(
            profileDropdown,
            "Profile dropdown should be visible"
        ).toBeVisible({ timeout: 10000 });

        /* ------------------------------------
           STEP 4: Logout button visible
        ------------------------------------ */
        const logoutBtn = page.locator("#log_out_btn");
        await expect(
            logoutBtn,
            "Logout button should be visible"
        ).toBeVisible({ timeout: 10000 });

        /* ------------------------------------
           STEP 5: Click logout
        ------------------------------------ */
        await logoutBtn.click();

        /* ------------------------------------
           STEP 6: Confirm dialog appears
        ------------------------------------ */
        const confirmDialog = page.locator("#AlertNewDialogModule");
        await expect(
            confirmDialog,
            "Logout confirmation dialog should appear"
        ).toBeVisible({ timeout: 10000 });

        /* ------------------------------------
           STEP 7: Confirm logout
        ------------------------------------ */
        const confirmBtn = confirmDialog.locator("#danger");
        await expect(
            confirmBtn,
            "Confirm logout button should be visible"
        ).toBeVisible();

        await confirmBtn.click();

        /* ------------------------------------
           STEP 8: Wait for DB save / backend response
           (loading / saving indicator)
        ------------------------------------ */
        const savingIndicator = page.locator("#filesaving");
        if (await savingIndicator.isVisible().catch(() => false)) {
            await expect(
                savingIndicator,
                "File saving indicator should disappear"
            ).toBeHidden({ timeout: 30000 });
        }

        /* ------------------------------------
           STEP 9: Redirect after logout
        ------------------------------------ */
        await page.waitForURL(
            /validateurl|login|landing/i,
            { timeout: 30000 }
        );

    } catch (error) {
        console.warn("[logoutSafely] Logout flow incomplete:", error.message);
    }
}
