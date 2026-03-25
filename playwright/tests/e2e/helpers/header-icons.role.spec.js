import { test, expect } from '@playwright/test';

/**
 * Query Panel Header Icon Validation (Manual-first, automation-ready)
 *
 * Default flow:
 * 1) Opens baseURL
 * 2) Pauses so tester can login with requested role and open Query Panel
 * 3) Validates Edit/Delete icon visibility for a target query header
 *
 * Future automation:
 * - Replace `manualPrepareRoleContext` with role login + navigation helpers.
 */

const SELECTORS = {
  queryItem: process.env.PW_QUERY_ITEM_SELECTOR || '.query-item[data-query-id]',
  header: '.panel-query-header',
  label: '.panel-query-header .data-label',
  editBtn: '.panel-query-header .edit-btn',
  deleteBtn: '.panel-query-header .delete-btn'
};

const ROLES = [
  { role: 'Author', env: 'AUTHOR', defaults: { edit: true, delete: true } },
  { role: 'Co-Author', env: 'CO_AUTHOR', defaults: { edit: true, delete: true } },
  { role: 'Editor', env: 'EDITOR', defaults: { edit: true, delete: true } },
  { role: 'Editor 2', env: 'EDITOR_2', defaults: { edit: true, delete: true } },
  // Based on your current rule discussion: Co-Editor should not delete Editor base comment.
  { role: 'Co-Editor', env: 'CO_EDITOR', defaults: { edit: false, delete: false } }
];

function envBool(name, fallback) {
  const raw = process.env[name];
  if (raw === undefined) return fallback;
  return /^1|true|yes$/i.test(raw);
}

function expectationFor(roleCfg) {
  return {
    edit: envBool(`PW_EXPECT_${roleCfg.env}_EDIT`, roleCfg.defaults.edit),
    delete: envBool(`PW_EXPECT_${roleCfg.env}_DELETE`, roleCfg.defaults.delete)
  };
}

async function manualPrepareRoleContext(page, roleName) {
  console.log(`\n[MANUAL STEP] Login as: ${roleName}`);
  console.log('[MANUAL STEP] Open article/proof and ensure Query Panel is visible.');
  console.log('[MANUAL STEP] Expand/select the target query row, then Resume test.\n');
  await page.pause();
}

async function getTargetQueryItem(page) {
  const queryId = process.env.PW_QUERY_ID;
  const queryLabel = process.env.PW_QUERY_LABEL;

  if (queryId) {
    return page.locator(`${SELECTORS.queryItem}[data-query-id="${queryId}"]`).first();
  }

  if (queryLabel) {
    return page
      .locator(SELECTORS.queryItem)
      .filter({ has: page.locator(`${SELECTORS.label}:has-text("${queryLabel}")`) })
      .first();
  }

  return page.locator(SELECTORS.queryItem).first();
}

async function validateHeaderIcons(page, expected) {
  const queryItem = await getTargetQueryItem(page);
  await expect(queryItem, 'Target query item not found. Set PW_QUERY_ID or PW_QUERY_LABEL.').toBeVisible();

  const header = queryItem.locator(SELECTORS.header).first();
  await expect(header).toBeVisible();

  const editBtn = header.locator(SELECTORS.editBtn);
  const deleteBtn = header.locator(SELECTORS.deleteBtn);

  if (expected.edit) {
    await expect(editBtn, 'Edit icon should be visible').toBeVisible();
  } else {
    await expect(editBtn, 'Edit icon should be hidden').toHaveCount(0);
  }

  if (expected.delete) {
    await expect(deleteBtn, 'Delete icon should be visible').toBeVisible();
  } else {
    await expect(deleteBtn, 'Delete icon should be hidden').toHaveCount(0);
  }
}

test.describe('Query Panel Header Icons by Role', () => {
  for (const roleCfg of ROLES) {
    test(`${roleCfg.role}: validate Edit/Delete icons`, async ({ page, baseURL }) => {
      const expected = expectationFor(roleCfg);

      if (baseURL) {
        await page.goto(baseURL, { waitUntil: 'domcontentloaded' });
      }

      await manualPrepareRoleContext(page, roleCfg.role);
      await validateHeaderIcons(page, expected);
    });
  }
});
