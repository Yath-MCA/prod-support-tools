# DOI Path Hide + project-shortcode Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify and land the approved DOI progressive-report polish (no visible file-path; project-shortcode in metadata + filter); defer CSV `project_shortcode` to progressive-reports Phase 2.

**Architecture:** Polish already lives in `ee_report_store.py` (shell) and `element_extractor_tab.py` (run_meta → `project_shortcode` on file records). This plan is verify → commit. CSV column is explicitly out of scope here.

**Tech Stack:** Existing progressive DOI report stack; pytest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-20-doi-report-path-shortcode-polish-design.md`
- No `class="file-path"` in shell; path remains in `report-data.js`
- `project_shortcode` from run_meta `project-shortcode`; filter `#filterProjectShortcode`
- CSV shortcode → Phase 2 only
- Commit only when user asks; exclude `config/build_metadata.json`

## File Map

| File | Role |
|------|------|
| `core/ee_report_store.py` | Shell: no file-path; shortcode filter + metadata |
| `tabs/element_extractor_tab.py` | Populate `project_shortcode` from run_meta |
| `tests/test_ee_report_store.py` | Assert no file-path; has filterProjectShortcode |
| `tests/test_doi_pubid_by_ref.py` | Same shell asserts |
| `docs/superpowers/plans/2026-09-20-ee-progressive-json-reports-phase1.md` (optional note) | Or Phase 2 plan: CSV column |

---

### Task 1: Verify polish + note Phase 2 CSV

**Files:**
- Verify (already modified): `core/ee_report_store.py`, `tabs/element_extractor_tab.py`, tests above
- Optional modify: append one bullet under Phase 2 deferred in `docs/superpowers/plans/2026-09-20-ee-progressive-json-reports-phase1.md` Deferred section: “DOI CSV: add `project_shortcode` column”

- [ ] **Step 1: Run tests**

```bash
cd C:\_IMPACT\prod-support-tools\py\impact_config_suite
python -m pytest tests/test_ee_report_store.py tests/test_doi_pubid_by_ref.py -v
```

Expected: all PASS; shell tests assert `class="file-path"` absent and `filterProjectShortcode` present.

- [ ] **Step 2: Spot-check shell source**

Confirm in `doi_shell_html`:
- No `class="file-path"` string in card HTML
- `filterProjectShortcode` + `data-project-shortcode` + metaLine includes `project_shortcode`
- Tab writer sets `project_shortcode` from `run_meta_map[docid]["project-shortcode"]`

- [ ] **Step 3 (optional): Document CSV for Phase 2**

In `docs/superpowers/plans/2026-09-20-ee-progressive-json-reports-phase1.md` under `## Deferred (not this plan)`, add:

```markdown
- DOI CSV: add `project_shortcode` column (see polish design addendum)
```

- [ ] **Step 4: Commit (only if user requested)**

```bash
git add py/impact_config_suite/core/ee_report_store.py \
  py/impact_config_suite/tabs/element_extractor_tab.py \
  py/impact_config_suite/tests/test_ee_report_store.py \
  py/impact_config_suite/tests/test_doi_pubid_by_ref.py \
  py/impact_config_suite/docs/superpowers/plans/2026-09-20-ee-progressive-json-reports-phase1.md
git commit -m "Polish DOI report: hide path line; add project-shortcode filter."
```

Do not include CSV changes in this commit.

---

## Spec coverage

| Spec item | Task |
|-----------|------|
| Hide file-path | Already in store; Task 1 verify |
| project_shortcode metadata + filter | Already; Task 1 verify |
| run_meta population | Already in tab; Task 1 verify |
| CSV deferred Phase 2 | Task 1 Step 3 |

## Out of scope

- Optional suggestions (hide empty metadata, open on first hit, prefer run_meta always)
- Implementing CSV column now
