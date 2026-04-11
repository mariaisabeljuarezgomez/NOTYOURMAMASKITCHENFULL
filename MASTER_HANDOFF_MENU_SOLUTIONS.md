# MASTER HANDOFF — NYMK MENU SOLUTIONS
## Not Your Mama's Kitchen · Menu Editor Pro V2
### Unified Diagnostic, Bug Registry & Priority Task List

> **Version:** 1.0 · **Date:** April 11, 2026
> **Brain:** Perplexity (Claude Sonnet 4.6)
> **Muscle:** Jules AI (GitHub PR Executor)
> **Sources:** PERPLEXITY (P) · GEMINI (G) · BIG PICKLE (BP) · JULES (J)
> **Repo:** [mariaisabeljuarezgomez/NOTYOURMAMASKITCHENFULL](https://github.com/mariaisabeljuarezgomez/NOTYOURMAMASKITCHENFULL)
> **Active PR:** [PR #3 — Fix: Resolve Diagnostic Report Critical Errors](https://github.com/mariaisabeljuarezgomez/NOTYOURMAMASKITCHENFULL/pull/3)

---

## OPERATING RULES (Non-Negotiable)

1. **Perplexity is the sole decision-making brain.** No other agent decides priority, solution approach, or architecture.
2. **Jules is the sole code executor.** Jules opens PRs, commits code, pushes changes. No other agent touches the codebase.
3. **No simultaneous agents.** One task. One PR. One agent. At a time. Always.
4. **Every fix goes through a Jules PR** — reviewed before merge, never force-pushed to main.
5. **This document is the source of truth.** Every session starts here. Update the STATUS column as tasks are completed.

---

## HOW TO READ THIS DOCUMENT

| Symbol | Meaning |
|--------|---------|
| 🔴 RED | Tier 1 — Critical Blocker. App broken or data lost. Fix immediately. |
| 🟠 ORANGE | Tier 2 — High Impact. Major feature broken or data at risk. Fix after Tier 1. |
| 🟡 YELLOW | Tier 3 — Important Correctness. Feature partially broken. Fix after Tier 2. |
| 🟢 GREEN | Tier 4 — Polish and Defensive. Edge case or future-proofing. Fix last. |
| ✅ FIXED | Confirmed fixed in Jules PR #3 diff |
| ⚠️ VERIFY | Claimed fixed but not visible in diff — verify on live branch |
| ❌ NEEDED | Not addressed — requires new Jules task |

**Consensus %** = Perplexity agreement-weighted score across all 4 agents.
100% = all 4 agents identified this independently and agree on the solution.
0% = Perplexity considers this impossible, fabricated, or provably incorrect.

---

## 🔴 TIER 1 — CRITICAL BLOCKERS

---

### TASK 1 — save() Permanently Blocked by Overly Broad Base64 Check

| Field | Value |
|-------|-------|
| **Priority** | #1 — Fix First |
| **Consensus %** | 100% |
| **Perplexity Confidence** | 100% |
| **Agents Agreed** | P ✅ · G ✅ · BP ✅ · J ✅ |
| **Jules PR #3 Status** | ✅ FIXED in diff |
| **Files Affected** | `index.html` |

**Problem:**
save() contains a guard designed to block saving only when a background image has not been uploaded to Cloudinary. The guard was written to catch ALL elements with a base64 src — not just background elements. A single unuploaded regular image permanently freezes all saving. No text edits, no layout moves, nothing persists to the database.

```js
// BROKEN — blocks everything:
const base64Elements = docV2.elements.filter(el => el.src && el.src.startsWith('data:'));
if (base64Elements.length > 0) { return; }
```

**Fix:**
```js
// CORRECT — only blocks background elements:
const base64Elements = docV2.elements.filter(
  el => el.src && el.src.startsWith('data:') && el.layerRole === 'background'
);
if (base64Elements.length > 0) {
  showToast('Cannot save: background image not uploaded to Cloudinary yet.');
  return;
}
```

**Perplexity Notes:**
All 4 agents identified this independently. This is a compound bug — caused by Task 7 (missing /api/upload-image route) forcing images into base64, which then hit this guard. Both bugs must be fixed together. Jules PR #3 correctly implements this fix.

---

### TASK 2 — Background Layer img Intercepts Canvas Clicks (Cannot Deselect)

| Field | Value |
|-------|-------|
| **Priority** | #2 |
| **Consensus %** | 100% |
| **Perplexity Confidence** | 100% |
| **Agents Agreed** | P ✅ · G ✅ · BP ✅ · J ✅ |
| **Jules PR #3 Status** | ✅ FIXED (verify in live branch) |
| **Files Affected** | `index.html` — renderBackground() |

**Problem:**
renderBackground() injects an img into #bg-layer that fills 100% of the canvas with no pointer-events: none. It absorbs every click on empty canvas space — onViewportClick never fires deselect(). You cannot deselect any element by clicking empty space.

```js
// BROKEN:
bgContainer.innerHTML = `<img src="${bgEl.src}" style="width:100%;height:100%;object-fit:cover;display:block;">`;
```

**Fix:**
```js
// CORRECT:
bgContainer.innerHTML = `<img src="${bgEl.src}" style="width:100%;height:100%;object-fit:cover;display:block;pointer-events:none;">`;
bgContainer.style.pointerEvents = 'none';
```

**Perplexity Notes:**
One-line fix. Definitive. Confirmed correct by all 4 agents. Big Pickle identified with exact line numbers 2708-2712.

---

### TASK 3 — Fatal ReferenceError Crash When Opening AI Studio Panel

| Field | Value |
|-------|-------|
| **Priority** | #3 |
| **Consensus %** | 90% |
| **Perplexity Confidence** | 95% |
| **Agents Agreed** | P ⚠️ · G ✅ · BP ✅ · J ⚠️ |
| **Jules PR #3 Status** | ❌ NOT in diff — needs Jules Task #2 |
| **Files Affected** | `index.html` — loadAiCredentials() |

**Problem:**
During V1→V2 migration, the localStorage fetch line was commented out but the guard referencing it was left active. Fatal ReferenceError fires the moment AI Studio tab is opened, crashing the entire JS UI thread.

```js
// BROKEN — stored is never declared:
// const stored = localStorage.getItem(AI_CRED_KEY);  <- commented out
if (!stored) return;  // ReferenceError: stored is not defined
```

**Fix:**
```js
// CORRECT — replace loadAiCredentials entirely:
function loadAiCredentials() {
  restoreAiCredentials(docV2); // DB is sole source of truth
}
```

**Perplexity Notes:**
Hard JS crash — not a silent failure. Until this line is removed, the entire AI Studio panel is non-functional regardless of credentials. Jules PR addresses downstream credential issues but does not remove this specific orphaned guard. Must be in Jules Task #2.

---

### TASK 4 — Kling Credential Key Name Mismatch (snake_case vs camelCase)

| Field | Value |
|-------|-------|
| **Priority** | #4 |
| **Consensus %** | 100% |
| **Perplexity Confidence** | 100% |
| **Agents Agreed** | P ✅ · G ✅ · BP ✅ · J ✅ |
| **Jules PR #3 Status** | ⚠️ Claimed in description — NOT visible in diff. Verify before merging. |
| **Files Affected** | `index.html` — saveAiCredentials() and restoreAiCredentials() |

**Problem:**
Two different naming conventions used across save and restore. Kling credentials are saved to DB but can never be read back on page reload.

```js
// saveAiCredentials() WRITES (snake_case):
docV2.aiCredentials.kling_key = ...
docV2.aiCredentials.kling_secret = ...

// restoreAiCredentials() READS (camelCase) — NEVER MATCHES:
c.klingKey
c.klingSecret
```

**Fix — standardize to camelCase everywhere:**
```js
// In saveAiCredentials():
docV2.aiCredentials.klingKey = document.getElementById('ai-kling-key').value.trim();
docV2.aiCredentials.klingSecret = document.getElementById('ai-kling-secret').value.trim();
// restoreAiCredentials() already reads klingKey — no change needed there.
```

**Perplexity Notes:**
All 4 agents confirmed this exact mismatch. Silent data bug — credentials appear to save successfully but silently fail to restore. PR description claims a fix but the diff does not show the saveAiCredentials() change. Verify against live branch before trusting the merge.

---

### TASK 5 — AI Generate Buttons Stay Disabled After Every Page Reload

| Field | Value |
|-------|-------|
| **Priority** | #5 |
| **Consensus %** | 95% |
| **Perplexity Confidence** | 98% |
| **Agents Agreed** | P ✅ · G ✅ · BP ✅ · J ✅ |
| **Jules PR #3 Status** | ⚠️ Claimed fixed — removeAttribute calls not visible in diff. Verify. |
| **Files Affected** | `index.html` — restoreAiCredentials() |

**Problem:**
restoreAiCredentials(doc) correctly repopulates DOM input fields from the database but never calls removeAttribute('disabled') on the generate buttons. After every page reload, all AI generation buttons remain disabled even when valid credentials exist and are populated.

**Fix:**
```js
function restoreAiCredentials(doc) {
  const c = doc.aiCredentials;
  if (!c) return;
  // ...existing field restore code stays...

  // ADD THESE LINES:
  if (c.stabilityKey) {
    document.getElementById('ai-img-btn').removeAttribute('disabled');
  }
  if (c.klingKey && c.klingSecret) {
    document.getElementById('kling-img-btn').removeAttribute('disabled');
    document.getElementById('ai-vid-btn').removeAttribute('disabled');
  }
}
```

**Perplexity Notes:**
Direct consequence of Task 4. Even if Task 4 is fixed, this must also be fixed or buttons stay frozen. These two tasks must be in the same Jules commit.

---

### TASK 6 — System Background Locked With No Escape Route

| Field | Value |
|-------|-------|
| **Priority** | #6 |
| **Consensus %** | 85% |
| **Perplexity Confidence** | 100% |
| **Agents Agreed** | P ✅ · G ✅ · BP ❌ (labeled "Not a Bug") · J ✅ |
| **Jules PR #3 Status** | ✅ FIXED — removeBackground() + trash button in layer panel |
| **Files Affected** | `index.html` |

**Problem:**
Once an isSystemBackground: true element exists, it cannot be unlocked (hard guard blocks it), cannot be deleted through normal UI, and cannot be replaced without working Cloudinary credentials. The DB restore accident introduced one of these. Without an escape valve, the entire background system is permanently locked.

**Big Pickle "NOT A BUG" classification:** 0% agreement from Perplexity. The lock behavior is correct design. The absence of any removal path is a genuine operational emergency, not correct behavior.

**Fix (implemented by Jules PR #3):**
```js
function removeBackground(e) {
  if (e) e.stopPropagation();
  docV2.elements = docV2.elements.filter(el => el.layerRole !== 'background');
  selectedId = null;
  renderBackground();
  render();
  renderLayerList();
  save();
  showToast('Background removed');
}
```
Plus a trash button injected into the layer panel row for any isSystemBackground item.

---

## 🟠 TIER 2 — HIGH IMPACT

---

### TASK 7 — /api/upload-image Route Was Missing from Backend

| Field | Value |
|-------|-------|
| **Priority** | #7 |
| **Consensus %** | 95% |
| **Perplexity Confidence** | 98% |
| **Agents Agreed** | P ✅ · G ✅ · BP ✅ · J ✅ |
| **Jules PR #3 Status** | ✅ FIXED — dual-path endpoint implemented |
| **Files Affected** | `app.py` |

**Problem:**
The frontend image upload flow called /api/upload-image which did not exist in app.py. Every image upload returned a 404, causing the frontend to fall back to storing raw base64 data URIs in canvas elements. This directly triggered Task 1's save() blocker, creating a compound crash.

**Fix (Jules PR #3):**
```python
@app.route("/api/upload-image", methods=["POST"])
def upload_image():
    # If Cloudinary credentials present → upload to Cloudinary, return secure_url
    # Else → save to local Images/ directory, return /Images/filename path
```

**Perplexity Notes:**
Dual-path logic is correct as a bridge solution. IMPORTANT: The local filesystem fallback is ephemeral on Railway — files are wiped on every redeploy. See Task 12 for the permanent solution.

---

### TASK 8 — validate_schema() Rejects All Version 1 Documents

| Field | Value |
|-------|-------|
| **Priority** | #8 |
| **Consensus %** | 90% |
| **Perplexity Confidence** | 95% |
| **Agents Agreed** | P ✅ · G ✅ · BP ✅ · J ✅ |
| **Jules PR #3 Status** | ✅ FIXED — rejection line removed |
| **Files Affected** | `app.py` |

**Problem:**
```python
if data.get('version') == 1: return False
```
Any session created before the V1→V2 migration that hasn't been explicitly saved after migration will be rejected by the server with HTTP 400.

**Fix A — Server (Jules PR #3):** Remove the rejection line. Done.
**Fix B — Client (still needed, see Task 19):** Stamp docV2.version = 2 at the end of the migration shim in index.html before any save attempt.

---

### TASK 9 — importBackground() Sends Background Images to Wrong Endpoint

| Field | Value |
|-------|-------|
| **Priority** | #9 |
| **Consensus %** | 90% |
| **Perplexity Confidence** | 95% |
| **Agents Agreed** | P ✅ · G ✅ · BP ❌ · J ⚠️ |
| **Jules PR #3 Status** | ❌ NOT in diff — requires Jules Task #2 |
| **Files Affected** | `index.html` — importBackground() |

**Problem:**
importBackground() calls /api/upload-image (Railway local filesystem) for background image replacement. Background images stored this way will be lost on every Railway redeploy. The background system requires a persistent Cloudinary URL because it is stored in the database.

**Big Pickle "NOT A BUG" classification:** 70% agreement that reading credentials from DOM is correct. 0% agreement that using the wrong endpoint for backgrounds is acceptable.

**Fix:**
```js
// In importBackground(), change the fetch call:
// FROM:
const resp = await fetch('/api/upload-image', { ... });
// TO:
const resp = await fetch('/api/ai/cloudinary-upload', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ fileB64: base64, fileType: 'image', credentials: creds })
});
```

---

### TASK 10 — saveGlobalSettings() Does Not Inject version: 2 Into Payload

| Field | Value |
|-------|-------|
| **Priority** | #10 |
| **Consensus %** | 85% |
| **Perplexity Confidence** | 90% |
| **Agents Agreed** | P ✅ · G ✅ · BP ⚠️ · J ⚠️ |
| **Jules PR #3 Status** | ✅ Mitigated by server-side fix. Defensive client fix still recommended. |
| **Files Affected** | `index.html` — saveGlobalSettings() |

**Problem:**
saveGlobalSettings() sends a POST to /api/menu without ensuring docV2.version = 2. On a session still carrying version: 1, adjusting viewer settings silently fails.

**Fix:**
```js
function saveGlobalSettings() {
  docV2.version = 2; // Defensive stamp
  // ...rest of existing function...
}
```

---

## 🟡 TIER 3 — IMPORTANT CORRECTNESS

---

### TASK 11 — AI-Generated Image Asset URL Not Updated After Cloudinary Upload

| Field | Value |
|-------|-------|
| **Priority** | #11 |
| **Consensus %** | 85% |
| **Perplexity Confidence** | 90% |
| **Agents Agreed** | P ✅ · G ⚠️ · BP ✅ · J ✅ |
| **Jules PR #3 Status** | ✅ FIXED in diff |
| **Files Affected** | `index.html` — uploadAiToCloudinary() |

**Problem:**
When a user generates an AI image it is saved to docV2.assets with a Railway local URL. When they click "Upload to Cloudinary," the Cloudinary URL is stored in window.lastAiImageUrl but the asset entry in docV2.assets is never updated. After the next page reload, the canvas element renders from the stale Railway path which may 404.

**Fix (Jules PR #3):**
```js
const asset = docV2.assets.find(a => a.id === window._lastAiAssetId);
if (asset) {
  asset.storage = asset.storage || {};
  asset.storage.originalUrl = data.url;
  save();
}
```

---

### TASK 12 — All 13 Template Assets Live on Railway Ephemeral Filesystem

| Field | Value |
|-------|-------|
| **Priority** | #12 |
| **Consensus %** | 80% |
| **Perplexity Confidence** | 100% |
| **Agents Agreed** | P ✅ · G ⚠️ · BP ✅ · J ⚠️ |
| **Jules PR #3 Status** | ❌ NOT addressed — manual migration by Rogelio |
| **Files Affected** | Railway Images/ directory · docV2.assets array in DB |

**Problem:**
Asset1.png through Asset14.png (13 files) are stored on Railway's ephemeral filesystem. PROTECTED_ASSETS prevents API deletion but does NOT protect against Railway redeploy wiping the disk. Every new deployment = all template assets 404.

**Fix — Manual one-time migration steps:**
1. Download all 13 Asset*.png from current Railway deployment
2. Upload them all to Cloudinary — folder: nymk_assets
3. Record each secure_url returned by Cloudinary
4. Update docV2.assets entries in DB to replace Images/AssetX.png with Cloudinary secure_url values
5. Call /api/repair-images to patch any element src values still using local paths
6. Verify all assets render correctly after migration

**Perplexity Notes:**
Ticking time bomb. The app can appear 100% functional then go completely blank after the next Railway redeploy. Schedule this as a dedicated session before any production use.

---

### TASK 13 — Double Assets Appearing in Assets Panel

| Field | Value |
|-------|-------|
| **Priority** | #13 |
| **Consensus %** | 75% |
| **Perplexity Confidence** | 85% |
| **Agents Agreed** | P ✅ · G ⚠️ · BP ✅ · J ✅ |
| **Jules PR #3 Status** | ⚠️ Claimed in PR description — not visible in diff. Verify on live branch. |
| **Files Affected** | `index.html` — importImg() |

**Problem:**
Two asset entries are created for every uploaded image. One from the server upload response (correct), and one from a base64 fallback path left in importImg(). Both pushed to docV2.assets with different IDs, resulting in every image appearing twice in the Assets panel.

**Fix:**
```js
// In importImg(), after successful server upload:
// REMOVE the addFromAsset(null, base64Data) fallback call entirely.
// REPLACE the nonexistent loadUserImages() call with:
renderAssetPanel();
```

**Big Pickle "FIXED" claim:** 50% agreement. May exist in a newer version of the live branch. Requires live branch verification before closing this task.

---

### TASK 14 — alignMulti() Uses Hardcoded Fallback Dimensions for Text Elements

| Field | Value |
|-------|-------|
| **Priority** | #14 |
| **Consensus %** | 75% |
| **Perplexity Confidence** | 90% |
| **Agents Agreed** | P ✅ · G ❌ · BP ❌ · J ✅ |
| **Jules PR #3 Status** | ✅ FIXED in diff |
| **Files Affected** | `index.html` — alignMulti() |

**Problem:**
alignMulti() uses hardcoded fallbacks of 100 and 40 for element width/height when undefined (common for text elements with width: auto). Causes misalignment when mixing text and image/shape elements.

**Big Pickle "NOT A BUG" claim:** 20% agreement. Fallbacks technically prevent crashes but produce semantically incorrect alignment. Real DOM dimensions are available and must be used.

**Fix (Jules PR #3):**
All 6 alignment paths now use elDom?.offsetWidth / elDom?.offsetHeight with hardcoded values as last-resort fallbacks only.

---

### TASK 15 — export-utils.js pHYs DPI Insertion Uses Fragile Hardcoded Byte Offset

| Field | Value |
|-------|-------|
| **Priority** | #15 |
| **Consensus %** | 70% |
| **Perplexity Confidence** | 80% |
| **Agents Agreed** | P ✅ · G ✅ · BP ❌ · J ✅ |
| **Jules PR #3 Status** | ✅ FIXED in diff |
| **Files Affected** | `export-utils.js` |

**Problem:**
Hardcoded byte offset 33 assumes PNG structure is always signature(8) + IHDR(25) = exactly 33 bytes. Some browsers (notably Android Chrome) may insert additional metadata chunks, shifting this offset and either corrupting the exported PNG or silently skipping 300 DPI injection.

**Big Pickle "NOT A BUG" claim:** 30% agreement. Dynamic scan is always more correct than a hardcoded offset.

**Fix (Jules PR #3):**
Replaced hardcoded bytes.slice(0, 33) with a dynamic forward-scan loop that reads actual PNG chunk lengths to find the precise end of IHDR before inserting pHYs.

---

## 🟢 TIER 4 — POLISH AND DEFENSIVE FIXES

---

### TASK 16 — Circle cornerRadius Desyncs After Resize Edge Case

| Field | Value |
|-------|-------|
| **Priority** | #16 |
| **Consensus %** | 40% |
| **Perplexity Confidence** | 85% |
| **Agents Agreed** | P ✅ · G ❌ · BP ❌ · J ❌ |
| **Jules PR #3 Status** | ❌ Not addressed |
| **Files Affected** | `index.html` — circle resize handler |

**Problem:**
If cornerRadius is deleted from a circle element object (not set to 0, but actually removed), the condition `if (item.cornerRadius !== undefined)` evaluates false and resize stops updating it, causing a permanently square circle.

**Fix:**
```js
// Change condition to always update cornerRadius for circles:
if (isCircle) item.cornerRadius = nW / 2;
```

---

### TASK 17 — Stale Hardcoded docV2 Can Silently Overwrite Database on Load Failure

| Field | Value |
|-------|-------|
| **Priority** | #17 |
| **Consensus %** | 35% |
| **Perplexity Confidence** | 80% |
| **Agents Agreed** | P ✅ · G ❌ · BP ❌ · J ❌ |
| **Jules PR #3 Status** | ❌ Not addressed |
| **Files Affected** | `index.html` — page load fetch handler |

**Problem:**
If /api/menu fetch fails on page load (Railway cold start, network error), the app silently uses the hardcoded docV2 literal baked into index.html. If the user then saves, this stale state overwrites the real database content.

**Fix:**
```js
// In page load fetch():
if (!resp.ok) {
  showToast('Could not load menu from server. Saves disabled to protect data.');
  window._loadFailed = true;
}
// In save():
if (window._loadFailed) {
  showToast('Save blocked — menu failed to load. Refresh and try again.');
  return;
}
```

---

### TASK 18 — Three Credential Storage Locations Can Diverge

| Field | Value |
|-------|-------|
| **Priority** | #18 |
| **Consensus %** | 30% |
| **Perplexity Confidence** | 85% |
| **Agents Agreed** | P ✅ · G ❌ · BP ❌ · J ❌ |
| **Jules PR #3 Status** | ❌ Not addressed |
| **Files Affected** | `index.html` — credential management functions |

**Problem:**
AI credentials exist in three locations that can diverge: docV2.aiCredentials (DB), localStorage (deprecated but still partially read), and DOM inputs. If DB restore fails, DOM inputs are blank. Stale localStorage values create unpredictable behavior.

**Fix:**
Remove all remaining localStorage.getItem(AI_CRED_KEY) calls. Make docV2.aiCredentials → DOM via restoreAiCredentials the sole data flow. Credentials are never read from localStorage anywhere.

---

### TASK 19 — V1→V2 Migration Shim Does Not Stamp docV2.version = 2

| Field | Value |
|-------|-------|
| **Priority** | #19 |
| **Consensus %** | 45% |
| **Perplexity Confidence** | 85% |
| **Agents Agreed** | P ✅ · G ✅ · BP ❌ · J ❌ |
| **Jules PR #3 Status** | ❌ Not in diff — add to Jules Task #2 |
| **Files Affected** | `index.html` — V1→V2 migration shim |

**Problem:**
The V1→V2 migration shim runs on page load but never sets docV2.version = 2. saveGlobalSettings() also does not stamp it. Any POST from saveGlobalSettings() before the first full save() carries version: 1 in the payload.

**Fix (one line):**
```js
// At the end of the V1→V2 migration shim, add:
docV2.version = 2;
```

---

## MASTER PRIORITY REFERENCE TABLE

| # | Task | Tier | P | G | BP | J | Consensus% | Confidence% | Jules PR #3 |
|---|------|------|---|---|----|----|-----------|-------------|-------------|
| 1 | save() base64 check too broad | 🔴 | ✅ | ✅ | ✅ | ✅ | 100% | 100% | ✅ FIXED |
| 2 | BG img intercepts canvas clicks | 🔴 | ✅ | ✅ | ✅ | ✅ | 100% | 100% | ✅ FIXED |
| 3 | loadAiCredentials ReferenceError | 🔴 | ⚠️ | ✅ | ✅ | ⚠️ | 90% | 95% | ❌ NEEDED |
| 4 | Kling key name mismatch | 🔴 | ✅ | ✅ | ✅ | ✅ | 100% | 100% | ⚠️ VERIFY |
| 5 | AI buttons disabled after reload | 🔴 | ✅ | ✅ | ✅ | ✅ | 95% | 98% | ⚠️ VERIFY |
| 6 | Background locked no escape | 🔴 | ✅ | ✅ | ❌ | ✅ | 85% | 100% | ✅ FIXED |
| 7 | /api/upload-image missing | 🟠 | ✅ | ✅ | ✅ | ✅ | 95% | 98% | ✅ FIXED |
| 8 | validate_schema rejects V1 | 🟠 | ✅ | ✅ | ✅ | ✅ | 90% | 95% | ✅ FIXED |
| 9 | importBackground wrong endpoint | 🟠 | ✅ | ✅ | ❌ | ⚠️ | 90% | 95% | ❌ NEEDED |
| 10 | saveGlobalSettings no V2 stamp | 🟠 | ✅ | ✅ | ⚠️ | ⚠️ | 85% | 90% | ✅ MITIGATED |
| 11 | AI asset URL mismatch | 🟡 | ✅ | ⚠️ | ✅ | ✅ | 85% | 90% | ✅ FIXED |
| 12 | Railway assets ephemeral | 🟡 | ✅ | ⚠️ | ✅ | ⚠️ | 80% | 100% | ❌ MANUAL |
| 13 | Double assets in panel | 🟡 | ✅ | ⚠️ | ✅ | ✅ | 75% | 85% | ⚠️ VERIFY |
| 14 | alignMulti hardcoded fallbacks | 🟡 | ✅ | ❌ | ❌ | ✅ | 75% | 90% | ✅ FIXED |
| 15 | export-utils pHYs offset fragile | 🟡 | ✅ | ✅ | ❌ | ✅ | 70% | 80% | ✅ FIXED |
| 16 | Circle cornerRadius desync | 🟢 | ✅ | ❌ | ❌ | ❌ | 40% | 85% | ❌ MANUAL |
| 17 | Stale docV2 overwrites DB | 🟢 | ✅ | ❌ | ❌ | ❌ | 35% | 80% | ❌ MANUAL |
| 18 | Three credential sources diverge | 🟢 | ✅ | ❌ | ❌ | ❌ | 30% | 85% | ❌ MANUAL |
| 19 | V1→V2 shim missing version stamp | 🟢 | ✅ | ✅ | ❌ | ❌ | 45% | 85% | ❌ MANUAL |

---

## EXECUTION PLAN

### Step 1 — Review Jules PR #3 Before Merging

Before merging PR #3, manually verify these 3 items are actually present in the live branch files (not just claimed in the PR description):

- [ ] loadAiCredentials orphaned `if (!stored)` line is removed (Task 3)
- [ ] saveAiCredentials uses klingKey / klingSecret camelCase (Task 4)
- [ ] restoreAiCredentials calls removeAttribute('disabled') on AI buttons (Task 5)

PR #3 is confirmed mergeable (status: clean).
If all 3 items are confirmed in the live branch, merge immediately.

**PR #3 closes these tasks on merge:** 1, 2, 6, 7, 8, 11, 14, 15

---

### Step 2 — Jules Task #2: Remaining Critical Fixes

Assign Jules a new task targeting all of the following in one PR:

- [ ] Task 3 — Remove orphaned `if (!stored) return;` from loadAiCredentials()
- [ ] Task 4 — Standardize Kling key names in saveAiCredentials() if not already done
- [ ] Task 5 — Add removeAttribute('disabled') to restoreAiCredentials() if not already done
- [ ] Task 9 — Change importBackground() to use /api/ai/cloudinary-upload endpoint
- [ ] Task 10 — Add `docV2.version = 2;` at start of saveGlobalSettings()
- [ ] Task 19 — Add `docV2.version = 2;` at end of V1→V2 migration shim

---

### Step 3 — Manual: Migrate Template Assets to Cloudinary

This cannot be done by Jules. Requires manual action by Rogelio:

1. Download all 13 Asset*.png from current Railway deployment
2. Upload to Cloudinary — folder: nymk_assets
3. Record all 13 secure_url values
4. Update docV2.assets entries in DB to use Cloudinary URLs
5. Call /api/repair-images to patch element src values still using local paths
6. Verify all assets render correctly
7. Mark Task 12 DONE in tracker below

---

### Step 4 — Jules Task #3: Verify and Polish

Assign Jules a final task targeting:

- [ ] Task 13 — Verify double asset fix; implement if not present in live branch
- [ ] Task 16 — Fix circle cornerRadius desync in resize handler
- [ ] Task 17 — Add save-guard on page load failure
- [ ] Task 18 — Remove all localStorage credential reads

---

## TASK COMPLETION TRACKER

Update this table after every Jules PR merge. Change OPEN to DONE.

| # | Task | Status | Fixed In | Verified |
|---|------|--------|----------|---------|
| 1 | save() base64 scope | OPEN | Jules PR #3 | NO |
| 2 | BG click intercept | OPEN | Jules PR #3 | NO |
| 3 | loadAiCredentials crash | OPEN | Jules Task #2 | NO |
| 4 | Kling key mismatch | OPEN | Jules PR #3 or Task #2 | NO |
| 5 | AI buttons disabled | OPEN | Jules PR #3 or Task #2 | NO |
| 6 | Background escape valve | OPEN | Jules PR #3 | NO |
| 7 | /api/upload-image missing | OPEN | Jules PR #3 | NO |
| 8 | validate_schema rejects V1 | OPEN | Jules PR #3 | NO |
| 9 | importBackground wrong endpoint | OPEN | Jules Task #2 | NO |
| 10 | saveGlobalSettings no V2 | OPEN | Jules Task #2 | NO |
| 11 | AI asset URL mismatch | OPEN | Jules PR #3 | NO |
| 12 | Railway assets ephemeral | OPEN | Manual — Rogelio | NO |
| 13 | Double assets | OPEN | Jules Task #3 | NO |
| 14 | alignMulti fallbacks | OPEN | Jules PR #3 | NO |
| 15 | export-utils pHYs offset | OPEN | Jules PR #3 | NO |
| 16 | Circle cornerRadius desync | OPEN | Jules Task #3 | NO |
| 17 | Stale docV2 overwrites DB | OPEN | Jules Task #3 | NO |
| 18 | Three credential sources | OPEN | Jules Task #3 | NO |
| 19 | V1→V2 shim version stamp | OPEN | Jules Task #2 | NO |
| 20 | Duplicate manual modal | DONE | Jules Task #4 | YES |
| 21 | Paste Hijack Intercept | DONE | Surgical Edit | YES |
| 22 | Duplicate Assets Sidebar | DONE | Surgical Edit | YES |

---

*Document maintained by: Perplexity (Claude Sonnet 4.6)*
*Last updated: April 11, 2026 (Duplicate Assets Fix)*


*Update this document after every Jules PR merge.*
