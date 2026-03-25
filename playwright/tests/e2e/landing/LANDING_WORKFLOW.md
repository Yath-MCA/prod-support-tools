# Landing Page Workflow — Test Discussion

## Overview

The landing page is a **URL-key-validated access gate** — not a standard web page.
A unique encrypted `key` in the URL is sent to the server, which returns the document
context (`status`, `client`, `author_count`, `role`, `emailList`, etc.).
The page then routes the user based on that response.

---

## URL Pattern

```
validateurl{client}.html?key=<encrypted-access-key>
```

Examples:
```
validateurllww.html?key=HgnqXDUGGRmt...
validateurlmedknow.html?key=HgnqXDUGGRmt...
validateurloup.html?key=HgnqXDUGGRmt...
```

The `key` encodes: document ID + user session + expiry.
Real test URLs live in: `tests/e2e/data/links.json` (role → status → urls).

---

## Workflow Decision Tree

```
URL key received
      │
      ▼
Server validates key
      │
      ├── status = "active"
      │         │
      │         ├── author_count = 1
      │         │         │
      │         │         ├── client = "PLOS"
      │         │         │       └── Show Access Code Dialog
      │         │         │               ├── Valid code   → Editor Page
      │         │         │               └── Invalid code → Error msg
      │         │         │
      │         │         └── client = LWW | OUP | MEDKNOW | BRILL
      │         │                     └── Show Confirm Dialog (Accept / Cancel)
      │         │                             ├── Accept → Editor Page
      │         │                             └── Cancel → Stay / Close
      │         │
      │         └── author_count > 1
      │                   └── Show Email Picker ("Which author are you?")
      │                           ├── Email in emailList → Editor Page
      │                           └── Email not found   → Access Denied
      │
      ├── status = "signoff"
      │         ├── Show blocking alert: "This article has been signed off"
      │         ├── Click OK → Read-Only Page
      │         └── IF client = "LWW" AND role = "author"
      │                   └── Show "Author Signed At: <timestamp>" in header
      │
      ├── status = "deactive"
      │         ├── Show blocking alert: "File is no longer active"
      │         └── Click OK → Archive Page
      │
      └── status = "file_deleted"
                ├── Show blocking alert: "Article moved to archive mode"
                └── Click OK → Archive Page
```

---

## Supported Clients

| Client   | Priority | Special Rules |
|----------|----------|---------------|
| LWW      | High     | AHA / NON-AHA journals. Author signoff shows sign time |
| OUP      | High     | Standard confirm dialog |
| MEDKNOW  | High     | Standard confirm dialog |
| BRILL    | Medium   | Standard confirm dialog |
| PLOS     | Low      | Access code dialog (author only) |

---

## API Response Shape

When the server validates the key, the page receives (via JS globals or XHR response):

```json
{
  "status":       "active | signoff | deactive | file_deleted",
  "client":       "lww | oup | medknow | plos | brill",
  "author_count": 1,
  "role":         "author | editor | collator",
  "emailList":    ["author1@pub.com", "author2@pub.com"],
  "title":        "Article title",
  "authorname":   "John Doe",
  "article_id":   "5b53536b4c4a803e9a5abf70",
  "signedAt":     "2026-03-25T10:30:00Z"
}
```

Available in browser as `window.SHARED_KEY` after page load.

---

## Page Content to Validate (active flow)

| Element           | Selector              | Verify |
|-------------------|-----------------------|--------|
| Article title 1   | `#title1`             | Visible + not empty |
| Article title 2   | `#title2`             | Visible + not empty |
| Author name       | `#authorname`         | Visible + not empty, matches API |
| Client icon       | `.navbar-brand img`   | Visible + not broken (naturalWidth > 0) |
| Support email     | `#support_mail_id`    | Valid `mailto:` link |
| FAQ PDF link      | `a[title='Frequently Asked Questions']` | Downloads .pdf |
| User Guide PDF    | `a[title='User Guide']` | Downloads .pdf |
| Accept button     | `#ValidateBtnOpt`     | Visible only after FullyLoaded = true |

---

## Loading Sequence to Verify

```
window.InitialLoadDialog.FullyLoaded = false
        ↓
Status: "Loading ..."
        ↓
Status: "Fetching Info ..."
        ↓
Status: "Setting Profile ..."
        ↓
Status: "Get document ..."
        ↓
Status: "Initiated IMPACT"
        ↓
Status: "Completed"
        ↓
window.InitialLoadDialog.FullyLoaded = true
#blurOverlay hidden
Accept button visible
```

---

## Access Tracking (after accept click)

The following must be recorded server-side:

| Field        | Source |
|--------------|--------|
| `email`      | User input (multi-author flow) or SHARED_KEY |
| `access_time`| Timestamp of accept click |
| `ip_address` | Server-captured |
| `client`     | From SHARED_KEY |
| `article_id` | From SHARED_KEY |
| `role`       | From SHARED_KEY |

---

## Test Files in This Folder

| File | What it tests |
|------|---------------|
| `landing-workflow.spec.js` | Status routing logic — all branches (mocked API + real URLs from `links.json`) |
| `landing-content.spec.js`  | UI content validation — title, author, images, mailto, PDFs |
| `landing-to-editor.spec.js`| Full flow: landing → accept → editor initialised |
| `landing-to-editor-query.spec.js` | Full flow: landing → editor → query module |
| `landing-to-editor-comment.spec.js` | Full flow: landing → editor → comment module |
| `landing-editor-module.spec.js` | Landing + all editor modules basic check |

---

## How to Run

```bash
# All landing tests
npx playwright test tests/e2e/landing/

# Workflow routing only (mocked + real URLs)
npx playwright test tests/e2e/landing/landing-workflow.spec.js

# Smoke only
npx playwright test tests/e2e/landing/ --grep @smoke

# Specific client via env
TEST_CLIENT=lww npx playwright test tests/e2e/landing/landing-workflow.spec.js
```

---

## Where Links Come From

```
assets/roles_details.js          assets/links.json  (FULLY POPULATED — real keys)
  roleId → pubkit_name             urls.{client}.{roleId}.{status} → [urls]
  "5b53536b..." → "author"  ◄───  "5b53536b...": { active:[...], signoff:[...] }
  "5b534e33..." → "editor"  ◄───  "5b534e33...": { active:[...] }
  "5bcf15b1..." → "collator" ◄──  "5bcf15b1...": { active:[...] }
          │
          ▼ resolved automatically by landing-signal.helper.js
          │
tests/e2e/data/links.json  (override / supplement — role-name format)
  {client}.{role}.{status} → [urls]
          │
          ▼
  pickLink(client, role, status)  ← used by landing-workflow.spec.js
```

**Resolution order in `pickLink()`:**
1. `tests/e2e/data/links.json` — checked first (role-name format, easy to read/edit)
2. `assets/links.json` — fallback (roleId format, resolved via `roles_details.js`)

Both sources are merged in `getAllLinks()` for full pool runs.

---

## links.json — How to Populate

Real test URLs live in `tests/e2e/data/links.json`, structured by **client → role → status**.
The URL pool (all clients, all statuses) is in `assets/links.json` (legacy format).

To identify which role a URL belongs to:
1. Open the URL in the browser
2. Open DevTools console
3. Run: `window.SHARED_KEY?.rolename`
4. Add the URL to the matching `role` bucket in `links.json`

```json
{
  "lww": {
    "author": {
      "active":  ["http://localhost/.../validateurllww.html?key=..."],
      "signoff": ["http://localhost/.../validateurllww.html?key=..."]
    },
    "editor": {
      "active":  []
    }
  }
}
```

---

## Open Questions / Decisions Needed

- [ ] What is the exact API endpoint the page calls to validate the key? (needed for `page.route()` mocking)
- [ ] Does BRILL use the same confirm dialog as LWW/OUP/MEDKNOW, or custom flow?
- [ ] Is there a cancel flow test needed — what happens when user clicks Cancel on the confirm dialog?
- [ ] Multi-author flow: what happens when an unrecognised email is entered — error message text?
- [ ] PLOS access code: what is an example valid code format for test data?
- [ ] LWW AHA vs NON-AHA journals — is there any UI difference on the landing page?
- [ ] Is `deactive` handled identically to `file_deleted` or are alert messages different?
