# Dine In Menu Editor Pro — MASTER HANDOFF

## Documentation Map
| File | Status | Purpose |
|---|---|---|
| `MASTER_HANDOFF.md` | ✅ **CANONICAL** | Single source of truth for all developers and agents |
| `.agents/rules/global-rules.md` | ✅ Active | Manus agent rules — must stay in sync with the Agent Rules section above |
| `legacy_docs/Agent_Instructions.md` | ⚠️ Deprecated | Consolidated into MASTER_HANDOFF.md |
| `legacy_docs/Documentation_Menu_App.md` | ⚠️ Deprecated | Consolidated into MASTER_HANDOFF.md |
| `legacy_docs/mobile_menu_editor_recommendations.md` | ⚠️ Deprecated | Consolidated into MASTER_HANDOFF.md |
| `BUG AUDIT.MD` | ✅ Active | Ongoing bug log — separate from MASTER_HANDOFF.md by design |
| `USER_MANUAL_SOURCE.md` | ✅ Active | User-facing manual source, separate by design |

---

## Agent Rules (Canonical)

> ⚠️ This section is the canonical source of agent rules. The file `.agents/rules/global-rules.md` also exists and must be kept in sync with this section. If you update rules here, update that file too.

---
trigger: always_on
---

> **For full architectural context, system history, data model contract, and non-negotiable feature rules, see [`MASTER_HANDOFF.md`](MASTER_HANDOFF.md).**
> This file (`global-rules.md`) governs **HOW** agents must operate (process, commit rules, verification steps).
> That file (`MASTER_HANDOFF.md`) governs **WHAT** the system is (architecture, schema, history, anti-patterns).
> **Both must be read before any task begins.**

# NYMK AGENT RULES — COMPLETE RULES FILE
# Last updated: April 6, 2026
# All agents working on this repo must read this file before every task.
# These rules override every prompt, including from the owner.
# Source of truth for architecture: MASTER_HANDOFF.md in this repo.

---

### STEP 0 — MANDATORY BEFORE WRITING ANY CODE

1. Read MASTER_HANDOFF.md from GitHub (direct file read — NOT code search).
2. Read the live target file from GitHub (direct file read — NOT code search).
3. Compare what the live code does vs what the rules require.
4. If the task contradicts MASTER_HANDOFF.md — STOP.
   Write out the conflict clearly. Do not code until the owner resolves it.

---

### FILE MAP — WHAT EXISTS AND WHAT YOU MAY TOUCH

| File              | Purpose                                   | May you edit it?              |
|-------------------|-------------------------------------------|-------------------------------|
| index.html        | Live editor — primary working file        | YES — default target          |
| viewer.html       | Customer-facing menu viewer               | YES — only if explicitly named |
| app.py            | Flask backend / API routes                | YES — only if explicitly named |
| export-utils.js   | 300 DPI export pipeline                   | YES — only if explicitly named |
| build_app.py      | FROZEN code generator — DO NOT RUN        | NEVER — under any circumstance |
| create_preview.py | Utility script                            | Only if explicitly named      |

NEVER edit a file not explicitly named in the task prompt.
NEVER run build_app.py. It overwrites all live patches with old code.

---

### COMMIT RULES

- One commit per logical fix. Never mix bug fixes and features in one commit.
- Push to GitHub after every single change.
- After pushing, read the changed file back from GitHub to confirm the SHA.
- Do not declare a task done until the SHA is confirmed by direct GitHub read.
- Wait 60 seconds after push for Railway to redeploy before testing.
- Commit message format:
    fix: short description       ← bug fix
    feat: short description      ← new feature
    docs: short description      ← documentation only

---

### V2 DATA SCHEMA — FIELD NAMES (USE EXACTLY AS WRITTEN)

V2 has NO style wrapper object. All fields are top-level on el.
NEVER write el.style.anything. Every property is directly on the element.

**All element types:**
el.id string
el.type 'text' | 'image' | 'shape' | 'line'
el.name string
el.x number (pixels, base canvas coordinates)
el.y number (pixels, base canvas coordinates)
el.width number
el.height number
el.visible boolean
el.locked boolean
el.opacity — number — stored as 0–1 (CSS-native range). Pass directly to element.style.opacity and ctx.globalAlpha. The UI slider displays 0–100 and divides by 100 on input — the stored value is always 0–1. Do NOT multiply or divide when reading from docV2.elements.
el.zIndex number
el.role string (optional)

**Text elements:**
el.content ← THE text string. NEVER el.text.
el.fontFamily string
el.fontSize number (px)
el.fontWeight 'normal' | 'bold'
el.fontStyle 'normal' | 'italic'
el.color string (hex or rgba)
el.textAlign 'left' | 'center' | 'right'
el.lineHeight number (multiplier, e.g. 1.1)
el.letterSpacing number

**Image elements:**
el.src string ← exact path e.g. "/Images/Asset1.png" — case-sensitive
el.assetId string ← registry ID e.g. "asset_001"
el.originalWidth number
el.originalHeight number

**Shape / Rectangle elements:**
el.fillColor string ← NEVER el.fill or s.fill
el.borderColor string ← NEVER el.strokeColor (shapes only — see Line exception)
el.borderWidth number ← NEVER el.strokeWidth (shapes only — see Line exception)
el.borderRadius number ← NEVER el.cornerRadius
el.shapeType 'rect' | 'circle' | 'star' (optional, default is rect)
el.lineCap 'butt' | 'round' | 'square' (for line-style shapes only)

**Line elements — THE ONE EXCEPTION TO V2 FIELD NAMES:**
viewer.html draw() uses:
el.strokeColor ← NOT el.borderColor
el.strokeWidth ← NOT el.borderWidth
el.x1, el.y1, el.x2, el.y2 ← endpoint offsets from el.x / el.y
el.lineCap

index.html uses el.borderColor / el.borderWidth for lines.

This inconsistency is known and intentional (legacy).
DO NOT fix it unless both files are updated in the exact same commit.
Until that refactor: always write the file-correct field name for the file you are editing.

## Schema Migration State (as of April 2026)

**Current state:** The live `docV2.elements` data on the server was originally saved in V1 format (`el.text` for content, `el.style.fontFamily` etc. for styles). A migration shim runs at page load to bridge V1 data into V2 field names. The shim commit is `29965b0`.

**What this means for developers:**
- `render()`, `sync()`, and `syncTextFormatBar()` still read from V1 field paths (`d.text`, `d.style.*`). This is intentional — do not change them without a full planned migration.
- The shim ensures `el.content` and top-level style properties are always populated from V1 data on load.
- Do NOT remove the shim. Do NOT "fix" render() to use V2 fields without also migrating all saved session data on the server.

**Future migration plan (not yet scheduled):**
When commissioned, a full V1→V2 migration requires:
1. A one-time server-side data migration script to rewrite all saved JSON
2. Updating `render()` to read `d.content` and top-level style properties
3. Updating `sync()` to write to `item.content`
4. Updating `syncTextFormatBar()` to read top-level style properties
5. Removing the load-time shim after confirming all saved data is V2-compliant

**Do not perform this migration in a single PR without explicit approval from the project owner.**

---

### OPACITY RULE — ALWAYS

el.opacity is stored as 0–1 in V2.
When setting canvas globalAlpha, pass it directly:
```javascript
ctx.globalAlpha = (el.opacity !== undefined ? el.opacity : 1);
```
viewer.html already has a normalizeEl() shim that converts V1 (0–1) to V2 (0–100).
Do not add redundant conversion logic.

---

### TEXT RENDERING RULES

- Read and write text content using el.content — NEVER el.text.
- In DOM: read with innerText — NEVER innerHTML (XSS prevention).
- contentEditable must be set as string "true" — NEVER boolean true.

---

### IMAGE ELEMENTS — MANDATORY PATTERN

When creating a new image element, ALWAYS set BOTH fields:
```javascript
el.src     = "/Images/Asset1.png"   // exact filename, case-sensitive
el.assetId = "asset_001"            // matching registry ID
```
NEVER set only one. Both are required.

**How index.html resolves image src:**
```javascript
asset.storage.previewUrl || asset.storage.originalUrl
```
previewUrl is ALWAYS null. The only valid path is originalUrl.
Never assume previewUrl will work.

**How viewer.html resolves image src:**
```javascript
el.src || ASSET_ID_TO_SRC[el.assetId] || ''
```
NEVER construct a path like `/Images/${el.assetId}.png` — that is wrong.
assetId "asset_001" does NOT match filename "Asset1.png" by construction.
Always use the ASSET_ID_TO_SRC lookup table.

---

### ASSET REGISTRY — EXACT MAPPING (case-sensitive)

This table MUST be declared at the TOP of the viewer.html script block,
before draw() and fetchAndDraw(). It is already in viewer.html as of April 5, 2026.
Do not remove it. Do not modify it unless a new asset is added.

```javascript
const ASSET_ID_TO_SRC = {
    'asset_001': '/Images/Asset1.png',
    'asset_002': '/Images/Asset10.png',
    'asset_003': '/Images/Asset11.png',
    'asset_004': '/Images/Asset12.png',
    'asset_005': '/Images/Asset13.png',
    'asset_006': '/Images/Asset14.png',
    'asset_007': '/Images/Asset2.png',
    'asset_008': '/Images/Asset3.png',
    'asset_009': '/Images/Asset4.png',
    'asset_010': '/Images/Asset6.png',
    'asset_011': '/Images/Asset7.png',
    'asset_012': '/Images/Asset8.png',
    'asset_013': '/Images/Asset9.png'
};
```

Files confirmed to exist in /Images/:
  Asset1.png  Asset2.png  Asset3.png  Asset4.png
  Asset6.png  Asset7.png  Asset8.png  Asset9.png
  Asset10.png Asset11.png Asset12.png Asset13.png Asset14.png

Asset5.png does NOT exist. There is no Asset5. Skip from Asset4 to Asset6.

---

### BACKGROUND IMAGE RULES — PROTECT PAGESPEED 100

| File                | Used where       | Size     |
|---------------------|------------------|----------|
| menu-bg-preview.jpg | Editor + viewer  | ~114 KB  |
| menu-bg.png         | Export only      | 7.2 MB   |

- menu-bg-preview.jpg loads on page init with fetchpriority="high".
- menu-bg.png loads ONLY during Export Pro PNG execution.
- NEVER swap these. NEVER load menu-bg.png on page init.
- This split is what achieved PageSpeed 100. Protect it at all costs.

---

### CANVAS AND RENDERING RULES

- Base canvas dimensions: 908.44 × 1336.02 px
- Export renders at 3600 × 5400 px (12 × 18 in @ 300 DPI)
- Export scale factor: 3600 / 908.44 ≈ 3.963×
- Canvas API only. html2canvas is banned — fully removed from the project.
- export-utils.js must be loaded with defer attribute.
- inject300DpiAndDownload() handles pHYs chunk injection (11811 px/meter).
- Elements render in ascending zIndex order.
- viewer.html uses normalizeEl() to shim V1 fields → V2. Do not remove it.

---

### FONT SYSTEM

Active @font-face declarations (do NOT delete or re-add):
century-gothic-regular.ttf → family: "Century Gothic" weight: normal
century-gothic-bold.ttf → family: "Century Gothic" weight: bold
century-gothic-bold-italic.ttf → family: "Century Gothic" weight: bold, style: italic
bernard-mt-condensed-regular.ttf → family: "bernard-mt-condensed-regular"

centurygothic.ttf was DELETED March 27, 2026. Do NOT re-add it ever.
All font faces use font-display: swap.

Font-loading wait pattern used in index.html — do not change:
```javascript
await Promise.race([
    Promise.all([
        document.fonts.load('1em century-gothic-regular'),
        document.fonts.load('1em century-gothic-bold'),
        document.fonts.load('1em century-gothic-bold-italic'),
        document.fonts.load('1em bernard-mt-condensed-regular'),
    ]),
    new Promise(resolve => setTimeout(resolve, 800))
]);
initApp();
```

---

### PERSISTENCE RULES — DO NOT TOUCH WITHOUT EXPLICIT OWNER APPROVAL

- Save path: /app/data/menu_data.json (Railway persistent volume)
- Backup path: /app/data/backups/menu_data_YYYYMMDD_HHMMSS.json
- Writes use atomic .tmp + os.replace pattern — never write directly.
- Frontend has localStorage fallback when server is unreachable.
- layoutLocked resets to true on every page load — never persisted.
- Undo stack is cleared on Load Session.
- If a task touches persistence in any way: STOP and get owner approval first.

---

### EXPORT PIPELINE — DO NOT TOUCH WITHOUT EXPLICIT OWNER APPROVAL

- Renders at 3600 × 5400 px via Canvas API only.
- html2canvas is fully banned from this project.
- export-utils.js loaded with defer.
- inject300DpiAndDownload() injects pHYs chunk (300 DPI metadata).
- If a task touches the export pipeline in any way: STOP and get owner approval first.

---

### LAYOUT LOCK — NEVER CHANGE THE DEFAULT

- layoutLocked = true on every page load. This is intentional safety behavior.
- Mobile users accidentally move elements without it.
- Never change the default. Never make it "smart", conditional, or device-dependent.
- Second finger during drag cancels the drag immediately (multi-touch suppression).
- Individually locked elements are never draggable regardless of global lock state.

---

### CACHE-CONTROL — DO NOT CHANGE
index.html → Cache-Control: no-cache, must-revalidate
All static assets → Cache-Control: max-age=604800, public (7 days)
User uploads → Cache-Control: max-age=604800, public (7 days)

Changing any of these will break PageSpeed 100.

---

### UI VOCABULARY — OFFICIAL TERMS ONLY

| Use this term          | Never substitute with              |
|------------------------|------------------------------------|
| Edit Mode              | Unlock, Edit state                 |
| Layout Locked          | Locked mode, Freeze                |
| Save Session           | Save, Submit                       |
| Load Session           | Load, Restore                      |
| Undo Last Change       | Undo, Revert                       |
| Reset to Original      | Reset, Clear, Delete               |
| Export Pro PNG         | Export, Download, Print            |
| Add Text               | New text, Insert text              |
| Add Rect               | New shape, Insert rectangle        |
| Upload Img             | Add image, Insert image            |
| Replace Background     | Change background                  |
| Toggle Original BG     | Show/hide background               |

---

### ABSOLUTE ANTI-PATTERNS — THESE WILL BREAK THE APP
1.  Run build_app.py — wipes ALL live patches
2.  Use html2canvas — banned, Canvas API only
3.  Mix bug fixes and features in one commit
4.  Guess at field names — always read the live file first
5.  Use el.style.anything — V2 has no style wrapper
6.  Use el.text — always el.content
7.  Use el.fill or s.fill — always el.fillColor
8.  Use el.cornerRadius — always el.borderRadius
9.  Construct paths as `/Images/${el.assetId}.png` — always use ASSET_ID_TO_SRC
10. Load menu-bg.png on page init — export only
11. Declare a task done before confirming SHA on GitHub
12. Edit any file not explicitly named in the task
13. Use native alert() or confirm() — use branded modal/toast only
14. Change the layoutLocked default

---

### Manual Update Rules (Enforced)
- **Manual updates are not optional.** When a feature ships, the manual update is part of the same definition of done.
- **NEVER rewrite manual-en.html or manual-es.html in full.** These are 100KB+ files. Full rewrites will be truncated. Always use surgical injection of new `<section>` blocks.
- **Always read the current manual file completely before editing it.** Do not assume you know its current state.
- **Always update both language editions** (EN and ES) in the same sprint.
- **Match the existing CSS class system exactly.** Do not introduce new class names. Use `.callout`, `.ui-mock`, `.step-row`, `.spec-grid`, etc. as defined in the file's `<style>` block.
- **Update the TOC and cover page metadata** on every structural addition.

---

## ⛔ RULE #1 — NEVER VIOLATED — SERVER SAVE PATTERN

The server's /api/menu POST route WILL REJECT (400 Bad Request) any
body that is not the complete docV2 object.

docV2 always has: { version: 2, elements: [...], ... }

EVERY function that saves anything to the server MUST:
1. Mutate docV2 directly (e.g. docV2.assets, docV2.aiCredentials)
2. POST the ENTIRE docV2 object — never a subset or partial object
3. Use this exact pattern:

   await fetch('/api/menu', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify(docV2)   // ← ALWAYS full docV2, never partial
   });

Violations of this rule cause silent 400 errors and data loss.

---
**Last Updated:** April 11, 2026  
**Prepared by:** MARIAS DIGITAL DESIGNS  
**Live URL:** https://web-production-3e17d.up.railway.app/  
**GitHub Repo:** https://github.com/mariaisabeljuarezgomez/NOTYOURMAMASKITCHENFULL  
**Deployment:** Railway (auto-deploys from GitHub `main` branch)  
**Latest Known Good SHA:** `e82ad968` — Task 12 Persistent Assets Pipeline  
**PageSpeed Score (Mar 27, 2026):** 100 / 100 / 100 / 100 ✅

## Phase: Schema Unification & Viewer Rendering Parity
**Status:** ✅ Complete  
**Date:** April 2026  
**Commits:** c96ccb3 → 678bd8a (8 commits)
### What Was Built
| # | Commit | File | Change |
|---|--------|------|--------|
| 1 | c96ccb3 | viewer.html | el.content compliance per RULES.md |
| 2 | 0053bd1 | viewer.html | normalizeViewerSettings() — legacy settings migration layer |
| 3 | 752619d | viewer.html | resolveImageSrc() — unified cache key for preload + draw |
| 4 | 80ddf60 | viewer.html | Rotation + opacity for all element types (text, image, line, shape) |
| 5 | 0fbf3cc | viewer.html | Letter-spacing with drawTextWithSpacing() manual fallback |
| 6 | 752619d | viewer.html | FONT_MAP — unified font family mapping |
| 7 | a008570 | index.html | Canonical save path: settings.viewer in save() + saveGlobalSettings() |
| 8 | 678bd8a | viewer.html | BUGFIX: opacity scale corrected 0–1 (was erroneously ÷100) |
### Key Architecture Decisions
- **Opacity scale:** Editor stores 0–1. Viewer uses raw value — NO division by 100.
- **Image cache key:** resolveImageSrc() return value is the single source of truth for both preload store and draw retrieve.
- **Settings path:** New saves write to settings.viewer. Legacy root-level fields preserved for backward compat. normalizeViewerSettings() bridges both.
- **Font mapping:** FONT_MAP handles generic CSS names. Custom fonts (century-gothic-*) pass through directly to canvas.

---

## ⚠️ CRITICAL WARNING — READ FIRST

> **`index.html` IS THE LIVE SOURCE OF TRUTH.**
>
> As of March 28, 2026, all Phases 2A–11 and Bug Fix Batches 1–8 (21 bugs total) were applied **directly to `index.html`**. `build_app.py` has NOT been updated and is frozen at Phase 30. **Do NOT run `python build_app.py`** — it will overwrite all patches with the old code. Until all patches are reconciled back into the generator, treat `index.html` as the only file to edit.

---

## RULES FOR ANY AI ASSISTANT READING THIS FILE

0. **Read `.agents/rules/global-rules.md` FIRST.** That file is the enforcement layer for how all agents must operate. This file (MASTER_HANDOFF.md) is the architectural reference. Both must be read before any task begins.
1. **Read `index.html` from GitHub before touching anything.** Do not assume local state.
2. **Edit `index.html` only** until `build_app.py` is reconciled. Do not run `python build_app.py`.
3. **One commit per logical fix.** Never mix feature work with bug fixes.
4. **Push to GitHub after every change.** Railway deploys from GitHub. A task is NOT done until the SHA is visible on GitHub.
5. **Do not reopen locked architecture** (persistence, export pipeline, split-asset strategy) without overwhelming justification.
6. **Preserve the V2 data model contract** (Section 9). All schema work must conform to it.
7. **Verify with direct file reads, not code search.** GitHub search has indexing lag.
8. **Do not mark a task complete** until you have verified the change exists in GitHub via a file read or commit check.
9. **If a change touches export, persistence, or the split-asset strategy** — stop and flag for explicit approval before coding.
10. **Keep changes small, testable, and single-purpose.** The project's biggest historical failures all came from mixing too many concerns at once.

---

## 1. Project Identity

**Product Name:** Dine In Menu Editor Pro  
**Client / Owner:** Not Your Mama's Kitchen (NYMK) — restaurant brand  
**What it is:** A browser-based, professional-grade layered menu layout editor. Allows non-designers to update a visually complex restaurant menu safely while preserving print accuracy and layout integrity.

**Core promise:**
- Fast on mobile
- Safe for non-technical users
- Reliable across devices
- Deterministic print-quality output (12in × 18in @ 300 DPI)
- Strong brand presentation
- Minimal accidental layout damage

**This is NOT just a text editor.** It is a controlled layout engine with server-backed continuity and a professional export pipeline.

**Technology Stack:**
| Layer | Technology |
|-------|-----------|
| Generator | Python 3 (`build_app.py`) |
| Frontend | HTML5, CSS3, Vanilla JavaScript, Canvas API |
| Export engine | Canvas API + `export-utils.js` (NO html2canvas) |
| Backend | Python 3, Flask, flask-compress |
| Database | PostgreSQL (psycopg2, Railway managed Postgres) |
| Persistence | PostgreSQL `sessions` DB (fallback to localStorage) |
| Hosting | Railway (auto-deploy from GitHub push) |
| CDN/Storage | Cloudinary (AI asset hosting, video reference images) |
| AI Image | Stability AI API, Kling AI API |
| AI Video | Kling AI API (requires Cloudinary for image2video) |
| Utilities | cloudscraper (HTTP), PyJWT (Kling auth) |
| Fonts | Local TTF files served as static assets |

---

## 2. Architecture Overview

### File Roles
| File | Role |
|------|------|
| `index.html` | **Live source of truth** — directly edited since March 28, 2026 |
| `build_app.py` | Generator — FROZEN at Phase 30. Do NOT run until reconciled |
| `app.py` | Flask backend — serves static files, handles save/load/reset/upload APIs |
| `export-utils.js` | Export helper — `inject300DpiAndDownload()`. Must be loaded with `defer` |
| `requirements.txt` | Flask + flask-compress |
| `Procfile` | `web: python app.py` |
| `century-gothic-*.ttf` | Font assets (regular, bold, bold-italic) |
| `bernard-mt-condensed-regular.ttf` | Font asset |
| `menu-bg-preview.jpg` | **Lightweight preview background** — editor only (~114 KB) |
| `menu-bg.png` | **Master background** — export only (7.2 MB) |
| `Images/Asset1–14.png` | Tray assets for layout composition |
| `USER_MANUAL_SOURCE.md` | Source content for bilingual in-app manual |
| `manual-en.html` / `manual-es.html` | Compiled in-app manual (EN + ES) |
| `manual-en-full.html` | Duplicate of manual-en.html — can be deleted |
| `create_preview.py` | Utility: generates menu-bg-preview.jpg from menu-bg.png |
| `fix_braces.py` | Utility: diagnostic for brace escaping issues |
| `raw_coords.json` | Legacy coordinate source data |

### Backend Routes (app.py)
| Route | Behavior |
|-------|----------|
| `GET /` | Serves index.html with `Cache-Control: no-cache, must-revalidate` |
| `GET /<path:path>` | Serves static files. `.ttf/.js/.jpg/.jpeg/.png/.webp` get `Cache-Control: max-age=604800, public` |
| `GET/POST /api/menu` | Load / Save session JSON to Railway Volume |
| `POST /api/menu/reset` | Backs up then wipes menu_data.json |
| `POST /api/upload-image` | Accepts base64 image, saves to /app/data/user_images/ |
| `GET /api/list-images` | Returns list of user-uploaded images |
| `DELETE /api/delete-image/<filename>` | Removes a user-uploaded image |
| `GET /user-images/<filename>` | Serves user images with `Cache-Control: max-age=604800, public` |

### Persistence (PostgreSQL)
- PostgreSQL is the persistence layer. "Railway Volume" system is GONE.
- Uses `DATABASE_URL` env var (set in Railway environment).
- Schema: `sessions` table (id TEXT PRIMARY KEY, canvas_json JSONB, updated_at TIMESTAMP).
- The document saves to the record where `id='main'`.
- Fully uses UPSERT (`ON CONFLICT (id) DO UPDATE ...`) pattern. No atomic files, no backups.
- Includes `video_history` table for persisting AI video reference URLs by slot.
- No `IS_PERSISTENT` flag. Frontend relies on HTTP status from `/api/menu`.
- Frontend has `localStorage` fallback and retry queue when DB is unreachable.

### Cache-Control Strategy (required for PageSpeed 100)
```
index.html           → Cache-Control: no-cache, must-revalidate
All static assets    → Cache-Control: max-age=604800, public (7 days)
User-uploaded images → Cache-Control: max-age=604800, public (7 days)
```

---

## 3. Current Production State (as of March 28, 2026)

### PageSpeed Scores (Mobile) — PERFECT
- Performance: **100** ✅
- Accessibility: **100** ✅
- Best Practices: **100** ✅
- SEO: **100** ✅

### All Features Implemented

| Phase | Feature | SHA |
|-------|---------|-----|
| 2A | V2 schema migration + asset registry | `6c030a5` |
| 2B | Asset-linked image placement (`assetId`) | `2fed811` |
| 2C | User upload persisted to asset registry | `bcaa8fa` |
| 2D | Asset registry round-trip save/restore | `75358d0` |
| 3 | Multi-select shift+click, group move/delete/dup | `c64e8f0` |
| 4 | Keyboard shortcuts (Delete, Ctrl+D/A/Z, Arrow nudge) | `c7a235a` |
| 5 | Font size control + text block width wrapping | `6bc7af5` |
| 6 | Alignment & distribution tools (8 buttons) | `eb37fab` |
| 7 | Lasso drag-box multi-select (mouse + touch) | `d3e0136` |
| 8 | Export PNG text rendering fix | `65ca724` |
| 9 | Undo history integrity (group drag, memory cap) | `fe2d5ce` |
| 10 | Mobile lasso & touch multi-select | `4b0cb1d` |
| 11 | Save/Load hardening (dirty state, auto-save, error UI) | `c378d90` |
| Bug Batch 1 | Asset merge fix, sync() guard, header dup noRender | `600009a` |
| Bug Batch 2 | Arrow nudge else-if, textContent→innerText, export image guard | `da85954` |
| Bug Batch 3 | deleteEl order, resetToOriginal, lasso scale ratio | `9664b41` |
| Bug Batch 4 | addFromTray pushState, onload fallback, bgLayer fix, toolbar anim | `d4f71fb` |
| Bug Batch 5 | innerText consistency, fitCanvasToScreen, openDrawer retry | `e210f58` |
| Bug Batch 6 | Ctrl+Z text guard, export stroke path, addRect viewport pos | `939a940` |
| Bug Batch 7 | deleteEl noRender param, addFromTray skipPush, fitCanvas zoom | `6bc7fe4` |
| Phase 27–30 | contentEditable fix, 300 DPI export, PageSpeed 100 | `d3fc068` |

---

## Bug Audit Rounds A–D (April 2026)
Five independent audit rounds were conducted on `app.py`. All fixes applied to `app.py` only. No other files touched.
| Round | SHA | Commit Message |
|-------|-----|----------------|
| A1 | dccae72 | fix: use string converter instead of path in serve_root_image route |
| A2 | 42d3fbc | fix: auto-suffix duplicate filenames instead of silently overwriting |
| A3 | 94380ab | fix: move MAGIC_BYTES constant to module level |
| A4 | 29a3e6a | fix: separate None body from invalid schema error in save_menu |
| A5 | 11cf223 | fix: return JSON 404 from static_proxy on missing file |
| D1 | 65a0158 | fix: move werkzeug NotFound import to module level |
| D2 | 145aadc | fix: set COMPRESS_MIN_SIZE to 500 to avoid compressing tiny responses |
| D3 | f7833a2 | fix: AI asset persistence (version: 2 in save()) & Kling video image_url fix (Cloudinary upload for reference image) |
| D3b | 3fd470 | fix: cap duplicate filename counter at 999 to prevent unbounded loop |
| D4 | 0dc7488 | fix: log prune_backups exceptions instead of silently discarding |
| D5 | 0d9b547 | fix: remove blank line with trailing whitespace in delete_asset |
| Task 12 | e82ad968 | feat: Task 12 — persistent assets pipeline — importImg now registers uploaded images into docV2.assets and persists full docV2 to DB; deleteAssetFromServer now treats HTTP 404 as successful deletion to prevent ghost assets |

---

## Manual System Architecture & Maintenance Rules

### Manual Files
| File | Purpose |
|------|---------|
| `USER_MANUAL_SOURCE.md` | Feature specification source — describes what every feature does. The single source of truth for manual content. |
| `manual-en.html` | Published English manual — full HTML with styles, UI mockups, and page layout. Customer-facing. |
| `manual-es.html` | Published Spanish manual — mirrors manual-en.html in Spanish. |

### HTML Structure
Every page in the HTML manual is a self-contained block:
```html
<section class="page page-break">
  <h2>N. Section Title</h2>
  ...content...
  <div class="footer"><span>Label</span><span>Page N</span></div>
</section>
```
CSS classes used: `.callout`, `.callout.tip`, `.callout.warning`, `.callout.danger`, `.ui-mock`, `.ui-btn`, `.step-row`, `.step-num`, `.spec-grid`, `.spec-card`, `.badge`, `.kbd`

### The Surgical Injection Rule (NON-NEGOTIABLE)
**Never rewrite or replace `manual-en.html` or `manual-es.html` in full.** These files are large (100KB+). A full rewrite guarantees truncation.
The only permitted update method:
1. Read the current file completely first
2. Identify exactly where new content must be inserted or what existing text must be changed
3. Insert new `<section>` blocks or patch specific lines using targeted edits
4. Update the Table of Contents and cover page metadata if needed
5. Repeat for the Spanish edition

### When to Update the Manual
A manual update is required whenever:
- A new user-facing feature is shipped (same sprint or the next sprint — never deferred longer)
- An existing feature's behavior changes
- A new workflow is added (e.g. video hosting, AI video creation)
- UI labels or button names change

### Cover Page Metadata Fields
When updating, always refresh:
- `Version` line — increment minor version or add new phase/batch name
- `Last Updated` — set to the date of the update
- TOC — add any new section numbers and titles

### Spanish Edition Parity
Every update to `manual-en.html` must be mirrored to `manual-es.html` in the same commit or the immediately following commit. The two files must never be more than one sprint out of sync.

---

## Background Replacement Rebuild (April 2026)
The editor was rebuilt from scratch to correctly implement the full background replacement pipeline end-to-end. The original implementation had the background hardcoded into the layout. A "Replace Background" button existed but the full code path was never correctly wired through the entire stack. Attempting to implement the pipeline broke multiple dependent systems. A clean-slate rebuild was performed over a weekend, resulting in a correctly integrated background replacement feature that is now stable and production-ready.

---

## 4. What Was Built Successfully (Full History)

### AI Studio Integration
- **Three Providers:** Stability AI (image), Kling AI (image, video), Cloudinary (hosting/CDN).
- **Credentials:** Securely stored in `docV2.aiCredentials` and persisted via the standard `save()` pattern.
- **Image Generation:** Supports txt2img, img2img, and Kling multi-mode.
- **Video Generation:** Uses Kling AI. `image2video` relies on automatic background uploading to Cloudinary for Kling to fetch.
- **Cloudinary:** Used as the fallback asset host for custom backgrounds, user uploaded images, and AI reference images.
- **UI Accordions:** Credentials, Generate Image, Generate Video sections inside the AI panel.

### Generator-first architecture
`build_app.py` emits all CSS, HTML, and JS into `index.html`. Python f-string braces are escaped with `{{` and `}}` to avoid collision with emitted JavaScript/CSS braces. **Currently frozen** — index.html is live source.

### Split-asset load strategy
- `menu-bg-preview.jpg` (~114 KB) — loaded with `fetchpriority="high"` for fast LCP
- `menu-bg.png` (7.2 MB) — loaded only during Export Pro PNG
- This is what achieved PageSpeed 100 on mobile. **Never swap these.**

### Deterministic export pipeline
- Export renders at 3600 × 5400px (12in × 18in @ 300 DPI)
- Elements rendered in ascending zIndex order using Canvas API
- PNG pHYs metadata chunk manually injected for true 300 DPI (11811 pixels/meter)
- Uses `inject300DpiAndDownload()` from `export-utils.js`
- **NEVER uses html2canvas** — html2canvas has been fully removed

### Railway-backed persistence
- Atomic writes with backup rotation
- Frontend retry + localStorage fallback
- Cross-device continuity via Save Session / Load Session

### V2 Layered document model
- `docV2` object with version, elements[], settings, editorState, assets[]
- Elements have: id, type, x, y, width, height, zIndex, opacity, rotation, visible, locked, layerRole, style

### Professional UI systems
- Branded modal for all confirmations (no native alert/confirm)
- Toast notifications (success/error/warning/info)
- Smart tooltips (data-help attribute, shown once per session)
- Bilingual in-app manual (EN + ES), loaded from `/manual-en.html` and `/manual-es.html`

### Mobile-safe interaction model
- Layout Locked by default on every load
- Multi-touch drag suppression (second finger cancels drag)
- Moveable toolbar (drag handle with pointer capture)
- Floating zoom +/- buttons (visible only when unlocked)
- Touch lasso multi-select

### Undo system
- 30-state history stack
- Undo via toolbar button or Ctrl+Z / ⌘+Z
- Text blur commit tracked separately
- Group drag guard prevents duplicate snapshots

### Font loading
```javascript
await Promise.race([
  Promise.all([
    document.fonts.load('1em century-gothic-regular'),
    document.fonts.load('1em century-gothic-bold'),
    document.fonts.load('1em century-gothic-bold-italic'),
    document.fonts.load('1em bernard-mt-condensed-regular'),
  ]),
  new Promise(resolve => setTimeout(resolve, 800))
]);
initApp();
```

---

## 5. What Went Wrong Historically (Read This Before Suggesting Anything)

This section exists so no future agent repeats the same mistakes.

### Scope expanded faster than the architecture matured
The project repeatedly tried to add new layers before the base editor was hardened. That caused regressions, broken persistence, and mobile interaction failures. **The solution: narrow focus, stabilize first, expand second.**

### Too many systems changed at the same time
Mixing UI improvements + persistence + export behavior + mobile gestures + new features in one pass made regression analysis nearly impossible.

### Browser-editor realities were underestimated
Early failures came from underestimating: CORS and tainted canvas rules, browser image downscaling, PNG metadata limitations, multi-touch gesture ambiguity, large-asset LCP impact, state desync across devices.

### Mobile interaction was too risky without lock-first
Without Layout Locked by default, mobile users accidentally moved objects while scrolling/pinching. **The lock-first model is intentional and must not be softened.**

### Reset and Undo were not separated
Users need both: stepwise undo for immediate mistakes, and full restore for deliberate template reset. They must remain separate forever.

### Specific technical failures and their recoveries
| Failure | Root Cause | Fix |
|---------|-----------|-----|
| Export blocked by tainted canvas | Cross-origin image CORS | Serve all assets from same origin |
| Blurry exported background | CSS background degraded by browser | Use DOM `<img>` not CSS background in export |
| PNG reported 72 DPI | Browser ignores DPI on canvas export | Manually rewrite pHYs chunk in PNG binary |
| Slow mobile load | 7.2MB background loaded on app init | Split-asset: preview.jpg for edit, .png for export |
| Save/load lost on cache clear | localStorage not durable | Railway Volume server persistence |
| Python/JS brace collisions | f-string vs JS braces | Doubled-brace escaping `{{` `}}` throughout |
| Mobile pinch/drag conflicts | Single vs multi-touch shared same layer | Layout lock + second-finger cancels drag |
| Add Text appeared off-screen | Not anchored to viewport center | Compute insertion in world coords from viewport |
| Native prompts looked unprofessional | Default alert()/confirm() | Branded custom modal + toast system |

---

## 6. Non-Negotiables — DO NOT BREAK THESE

| System | Rule |
|--------|------|
| Save Session / Load Session | Must persist to server AND localStorage fallback |
| Export Pro PNG | Must be 12in × 18in @ 300 DPI, Canvas API, NO html2canvas |
| export-utils.js | Must be loaded with `defer`. Must define `inject300DpiAndDownload` |
| Branded modal/toast UI | Never replace with native alert() or confirm() |
| In-app manual | Bilingual EN/ES, loaded from /manual-en.html and /manual-es.html |
| Draggable toolbar | Desktop: drag handle with pointer capture |
| Layout Locked default | `layoutLocked = true` on every load |
| Undo Last Change | 30-state stack, Ctrl+Z and button |
| Reset to Original | Separate from Undo. POSTs to /api/menu/reset |
| Floating zoom controls | Visible only when layout is unlocked |
| Split-asset strategy | preview.jpg for editor, .png for export — NEVER swap |
| index.html as current source | Do NOT run build_app.py until reconciled |
| Same-origin image serving | Cross-origin images cannot be drawn to Canvas (CORS) |
| Multi-touch suppression | Second finger during drag cancels drag |
| Cache-Control: no-cache on index.html | Users must always get fresh app |

---

## 6B. ⛔ CRITICAL SAFETY RULES FOR ALL AGENTS — READ BEFORE TOUCHING ANY ELEMENT, IMAGE, OR ASSET

These two rules exist because past agent mistakes caused permanent data loss and broken sessions. Both rules are NON-NEGOTIABLE.

---

### RULE A — NEVER RENAME, REPLACE, OR RE-ASSIGN `assetId` OR `id` WITHOUT A FULL IMPACT AUDIT

**Why this exists:**
Every element in `docV2.elements[]` has two identity fields:
- `id` — the unique runtime identity of that element (e.g. `"el_1710645000000_abc"`). The undo stack, selection state, layer panel, and all editor functions reference elements exclusively by this id. Renaming it mid-session destroys undo history, breaks selection, and causes ghost elements.
- `assetId` — the registry key linking an element to its source asset (e.g. `"asset_007"`). The asset panel, export pipeline, and save/load round-trip all use this key to resolve image `src`. If you change `assetId` without updating the corresponding entry in `docV2.assets[]`, the image becomes a broken reference permanently — even after Save/Load.

**The rule:**
> ⛔ NEVER change an element's `id` or `assetId` unless you are explicitly performing a migration task AND you have audited every reference to that id/assetId in the full codebase first.

**What you must check before renaming:**
1. Search `index.html` for ALL uses of that `id` string — undo stack snapshots, selectedId, multi-select arrays, layer panel renders
2. Search `docV2.assets[]` for the matching `assetId` entry — the `src`, `filename`, and `cloudUrl` fields must stay in sync
3. If the session is currently live (Railway), a rename that doesn't match the server-saved JSON will silently break Load Session on next page load

**Safe pattern:**
- Add new fields, don't rename existing ones
- If you must rename, write a one-time migration function that updates ALL references atomically in a single `pushState()` → mutate → `render()` pass

---

### RULE B — BACKGROUND LAYER IDENTITY: TWO TYPES EXIST, THEY BEHAVE DIFFERENTLY

**Why this exists:**
The background system has two distinct element types that share `layerRole: 'background'` but have completely different behavior contracts. Confusing them caused a full editor lockout bug (April 2026) where user-promoted background images became permanently unselectable and uneditable.

**The two background types:**

| Property | System Background | User Background Layer |
|---|---|---|
| Created by | **Replace Background** button | **🖼️ BG** button (setSelectedAsBackground) |
| `isSystemBackground` | `true` | absent / `false` |
| `locked` | `true` | `false` |
| Selectable in editor | ❌ No | ✅ Yes |
| Routes through `#menu-bg` img tag | ✅ Yes | ❌ No — renders as normal element |
| Moveable / resizable | ❌ No | ✅ Yes |
| Deleteable by user | ❌ Only via Replace BG | ✅ Yes |

**The rule:**
> ⛔ NEVER use `layerRole === 'background'` as the sole guard for locking, hiding, or blocking interaction. You MUST check `isSystemBackground === true` instead. Elements with `layerRole: 'background'` but WITHOUT `isSystemBackground: true` are regular moveable elements that happen to sit at the bottom of the z-stack.

**Guard pattern all agents must use:**
```javascript
// ✅ CORRECT — only blocks the true system background
if (item.isSystemBackground === true) return;

// ❌ WRONG — blocks ALL background-role elements including user-moveable ones
if (docV2.settings.backgroundLayerLocked && item.layerRole === 'background') return;
```

**Where this pattern is enforced (April 2026 patch):**
- `undo()` re-selection guard
- `render()` bg src routing (only `isSystemBackground` elements route through `#menu-bg`)
- `renderLayerList()` click guard
- `onCanvasMousedown()` selection guard
- Resize handle drag guard
- Lasso selection filter
- Select-All filter
- `setAsBackground()` — always sets `isSystemBackground: true`
- `setSelectedAsBackground()` — never sets `isSystemBackground`

---

## 7. UI Vocabulary — Standard Terms (Never Substitute Synonyms)

| Official Term | Meaning |
|--------------|---------|
| Edit Mode / Layout Unlocked | When user can move/edit elements |
| Layout Locked | Default safe state |
| Save Session | Saves to server + localStorage |
| Load Session | Loads from server, falls back to localStorage |
| Undo Last Change | Pops one history snapshot |
| Reset to Original | Wipes server save, reloads from embedded state |
| Export Pro PNG | Renders 300 DPI PNG for print |
| Add Text | Creates new text element at viewport center |
| Add Rect | Creates new rectangle shape |
| Upload Img | Uploads image to server library |
| Replace Background | Replaces menu-bg layer |
| Toggle Original BG | Shows/hides menu-bg-preview.jpg |

---

## 8. Known Anti-Patterns — Never Repeat These

1. **Running `python build_app.py`** before reconciling all patches into the generator — will wipe all live code
2. **Using html2canvas** for export — banned, Canvas API only
3. **Mixing feature additions with bug fixes** in the same commit
4. **Expanding scope before stabilizing** the current base
5. **Assuming local file changes = deployed** — always verify GitHub commit
6. **Reopening persistence/export architecture** without a proven defect
7. **Replacing standard terminology** with synonyms in UI or code
8. **Making drag "smart but ambiguous"** on mobile — lock-first is intentional
9. **Loading menu-bg.png on initial page load** — preview only on load
10. **Marking a task done before verifying on GitHub** — use direct file read, not code search
11. **Patching index.html and not updating this doc** — documentation drift caused a week of wasted work
12. **Making mobile gestures "smart but ambiguous"** — the conservative lock model is a strength
13. **Using `layerRole === 'background'` as a lock/block guard** — always use `isSystemBackground === true` instead. The background role alone no longer implies locking.
14. **Renaming element `id` or `assetId` without a full reference audit** — the undo stack, asset registry, selection state, and server-saved JSON all reference these by exact string match. A rename without auditing all usages silently breaks sessions.

---

## 9. V2 Data Model Contract (Official Schema)

### 9.1 Top-Level Document Shape
```json
{
  "version": "2.0",
  "savedAt": "2026-03-28T00:00:00Z",
  "elements": [],
  "zoom": 1.0,
  "scroll": {"x": 0, "y": 0},
  "imageLibrary": []
}
```

### 9.2 Base Element Properties (all types)
```json
{
  "id": "el_1710645000000_abc",
  "type": "text|image|shape",
  "name": "human-readable-label",
  "x": 245.5, "y": 180.0,
  "width": 420, "height": 60,
  "visible": true,
  "locked": false,
  "opacity": 100,
  "zIndex": 10,
  "role": "background|content|overlay"
}
```

### 9.3 Text Element (extends base)
```json
{
  "content": "APPETIZERS",
  "fontFamily": "Century Gothic",
  "fontSize": 28,
  "fontWeight": "bold",
  "fontStyle": "normal",
  "color": "#ffffff",
  "textAlign": "center",
  "letterSpacing": 0.08,
  "lineHeight": 1.4
}
```

### 9.4 Image Element (extends base)
```json
{
  "src": "/user-images/logo.png",
  "assetId": "asset_007",
  "originalWidth": 800,
  "originalHeight": 600,
  "layerRole": "background",
  "isSystemBackground": true
}
```
- `src` is the export source of truth — always same-origin
- `assetId` references the asset registry entry — **never rename without full impact audit (see Rule A in Section 6B)**
- `layerRole: "background"` marks the element as a background layer for z-ordering
- `isSystemBackground: true` — ONLY present on elements created by the **Replace Background** button. This flag is what ALL editor guards check to decide whether to lock/hide the element. Elements with `layerRole: 'background'` but WITHOUT this flag are fully moveable user-promoted background images. See Section 6B Rule B.

### 9.5 Shape/Rectangle Element (extends base)
```json
{
  "fillColor": "#95201d",
  "borderColor": "#c8a96a",
  "borderWidth": 2,
  "borderRadius": 8
}
```

### 9.6 Schema Validation Rules (enforced server-side)
- Must have `elements` field as an array
- Server returns `400` on validation failure
- `layoutLocked` resets to `true` on every page load (never persisted)
- Undo stack is cleared on Load Session

---

## 10. Export Pipeline — 300 DPI PNG

```
User clicks Export Pro PNG
  → pushState() for undo safety
  → showToast("Preparing export…") — persistent
  → autoSave()
  → Load menu-bg.png (full resolution master)
  → Create off-screen Canvas at 3600 × 5400px
  → Draw menu-bg.png as background
  → For each element in ascending zIndex order:
      text:  set font, fillStyle, draw multi-line text
      image: draw at scaled coordinates
      shape: fillRect/strokeRect with corner radius
  → canvas.toBlob("image/png")
  → inject300DpiAndDownload(blob, "notyourmamaskitchen-menu.png")
      → parse PNG binary
      → inject pHYs chunk (11811 × 11811 pixels/meter = 300 DPI)
      → reassemble + trigger browser download
  → showToast("Export complete!", "success")
```

**Export dimensions:** 3600 × 5400 px = 12 × 18 inches @ 300 DPI  
**Scale factor:** 3600 / 908.44 ≈ 3.963×  
**`export-utils.js` must be loaded with `defer`** — required for PageSpeed 100

---

## 11. Key Technical Facts (Quick Reference)

| Fact | Value |
|------|-------|
| Export canvas size | 3600 × 5400 px (12 × 18 in @ 300 DPI) |
| Editor canvas size | 908.44 × 1336.02 px (BASE_W / BASE_H) |
| Scale factor at export | ≈ 3.963× |
| Background at edit | `menu-bg-preview.jpg` with `fetchpriority="high"` |
| Background at export | `menu-bg.png` loaded on demand |
| Font loading timeout | 800ms fallback before initApp() |
| History stack max | 30 states |
| Server save path | PostgreSQL `sessions` DB (`id='main'`) |
| User images path | Cloudinary (primary), local `/Images/` (fallback) |
| Database env var | `DATABASE_URL` (Railway managed) |
| Deployment trigger | Push to `main` branch on GitHub |
| Compression | flask-compress, gzip all text/html/css/js/json/fonts |
| contentEditable attribute | Must use string `"true"` not boolean `true` |
| Text content read/write | Use `innerText` NOT `innerHTML` (XSS prevention) |
| pHYs DPI value | 11811 pixels/meter = 300 DPI |

---

## 12. Font System

| File | Font Name | Status |
|------|-----------|--------|
| `century-gothic-regular.ttf` | Century Gothic Regular | ✅ Active |
| `century-gothic-bold.ttf` | Century Gothic Bold | ✅ Active |
| `century-gothic-bold-italic.ttf` | Century Gothic Bold Italic | ✅ Active |
| `bernard-mt-condensed-regular.ttf` | Bernard MT Condensed Regular | ✅ Active |
| `centurygothic.ttf` | Duplicate alias | ❌ DELETED March 27, 2026 |

All fonts use `@font-face` with `font-display: swap`. Do not re-add `centurygothic.ttf`.

---

## 13. Deployment — Railway

| Variable | Purpose | Default |
|----------|---------|---------|
| `PORT` | Server bind port | `5000` |
| `STORAGE_DIR` | Override storage path | `/app/data` |
| `RAILWAY_VOLUME_MOUNTED` | Set by Railway when volume active | `"true"` |

**Procfile:** `web: python app.py`  
**Auto-deploy:** any push to `main` triggers Railway pull + redeploy  
**Backup recovery:**
```bash
cp /app/data/backups/menu_data_YYYYMMDD_HHMMSS.json /app/data/menu_data.json
```

---

## 14. Interaction Model — Layout Lock & Touch

| State | Drag | Text Edit | Canvas Scroll | Zoom Buttons |
|-------|------|-----------|---------------|-------------|
| 🔒 Locked | Blocked | ✅ double-click | ✅ drag background | Hidden |
| 🔓 Unlocked | ✅ | ✅ double-click | Disabled | Visible |

- Layout Locked is **default on every load** — never persisted to session JSON
- Multi-touch suppression: second finger during drag cancels drag immediately
- Individually locked elements are never draggable regardless of global lock state

---

## 15. Undo System

**Covered by undo:** text edits, moves, style changes, add/delete/duplicate, visibility toggle, lock toggle, shape changes, rotation, layer reorder  
**NOT covered:** Reset to Original, Load Session, Export, zoom changes  
**Stack max:** 30 states  
**Keyboard:** Ctrl+Z (Win/Linux) / ⌘+Z (Mac)

---

## 16. Phase Roadmap

### ✅ ALL PHASES COMPLETE (as of March 28, 2026)
See Section 3 for full commit table.

### 🔜 NEXT PRIORITIES

1. **Text Formatting Pack (index.html)** — Next feature sprint. Adds Bold/Italic/Underline toggles, line-height slider, letter-spacing slider, ALL CAPS toggle, and text shadow toggle to the selection panel. All 6 features use existing V2 schema fields — no schema changes required. One commit per feature.
2. **Reconcile `build_app.py` with `index.html`** — Still deferred. Migrate all Phases 2A–11 + Bug Batches 1–8 + Bug Audit Rounds A–D back into the generator. Until done, index.html remains the live source.
3. **Behavior verification matrix** — Full manual test pass: edit mode, lock states, undo ordering, save/load cross-device, style persistence. Goal: confirm every feature works end-to-end, not just that the code exists.

### Philosophy: Harden Before Expanding
The project failed every time it tried to expand before the base was stable. The correct pattern is: identify a narrow class of problems → solve only that class → verify → lock → move on. Never mix concerns.

---

## 17. Commit Format Rules

```
type: short description

Examples:
fix: correct lasso scale ratio on mobile
feat: add text alignment buttons to selection bar
docs: update MASTER_HANDOFF with Phase 12
perf: defer export-utils.js loading
```

After every task:
```bash
git add <files>
git commit -m "type: description"
git push origin main
# Verify SHA is visible on GitHub before declaring done
```

---

## 18. Documentation File Map (Current)

| File | Purpose | Status |
|------|---------|--------|
| `MASTER_HANDOFF.md` | This file — single source of truth for all agents | ✅ Active |
| `USER_MANUAL_SOURCE.md` | End-user manual source content (EN + ES) | ✅ Active |
| `legacy_docs/` | All older handoff/spec files archived here | 📦 Archive |

**All other MD files** (`HANDOFF_V3.md`, `DINE_IN_MENU_EDITOR_PRO_COMPREHENSIVE_MASTER_HANDOFF.md`, `MASTER_TECHNICAL_SPEC.md`, `CONTINUITY_HANDOFF_CURRENT.md`, `dine_in_menu_editor_v2_data_model_contract.md`) are superseded by this file and should be moved to `legacy_docs/`.

---

## Manual System Architecture (Confirmed April 2026)

### Active Files (DO NOT DELETE)

**manual-en.html** — English manual, served by Flask route `/manual-en`. Opens as pop-out window from editor.

**manual-es.html** — Spanish manual, served by Flask route `/manual-es`. Opens as pop-out window from editor.

**USER_MANUAL_SOURCE.md** — Markdown source of truth. Edit this file, then regenerate the HTML files.

### Dead Files (SAFE TO DELETE — orphaned from old split-page system)

- `MANUAL/manual_en_part1.html`
- `MANUAL/manual_en_part2.html`
- `MANUAL/manual_en_part3.html`

These three files are NOT referenced from index.html, not served by Flask, and not linked anywhere. They predate the consolidated single-file manual and were never removed.

### How the Manual Opens

The editor (index.html) has a button that calls `window.open('/manual-en')` or `window.open('/manual-es')` depending on language selection. Flask serves manual-en.html / manual-es.html from the root of the repo. The manual appears as a browser pop-out, NOT as a panel inside the editor.

### Workflow for Updating the Manual

1. Edit `USER_MANUAL_SOURCE.md` (the source of truth)
2. Regenerate `manual-en.html` and `manual-es.html` from it
3. Do NOT touch anything in the `MANUAL/` subfolder — it is dead code

*This file consolidates: HANDOFF_V3.md (Mar 28, 2026) + DINE_IN_MENU_EDITOR_PRO_COMPREHENSIVE_MASTER_HANDOFF.md + MASTER_TECHNICAL_SPEC.md*  
*Begin all new threads by pasting this file as the first message to any AI assistant.*

---

## Bug Autopsy: Lessons Learned

### 🪲 The Lasso Selection Ghost-Clear Bug (April 2026)
**Feature:** Multi-element lasso selection on the canvas.
**Time to fix:** 2 days across multiple developers and AI agents.
**Fix:** 1 line of code — `if (_lassoJustFired) return;`

#### What Happened
The lasso drag-select feature was implemented and appeared to work correctly internally: the hit-test logic was correct, `selectedIds` was being populated, and the CSS `multi-selected` class was being applied to elements. However, every time the user released the mouse **inside the canvas**, the selection would immediately disappear. Releasing the mouse **outside the canvas boundary** (onto the dark editor background) worked correctly.

#### Root Cause
The browser fires events in this exact sequence on a click-and-drag-release:
1. `mousedown` — starts the lasso
2. `mousemove` — draws the lasso box
3. `mouseup` — fires `onUp`, calculates hit-test, applies selection ✅
4. `click` — fires automatically 1–5ms later on the element where the mouse was released

Step 4 is the killer. When the user released the mouse inside the canvas, the `click` event fired on the canvas background (`onCanvasClick`) or the viewport wrapper (`onViewportClick`). These handlers interpreted the click as "user clicked on empty space → clear all selections." The selection set in step 3 was immediately destroyed in step 4, making it look like lasso never worked.

When the mouse was released **outside** the canvas, no canvas `click` handler fired, so the selection survived.

#### Why It Was Hard to Find
- The lasso logic was **completely correct** — wrong area was debugged for too long.
- The elements **were** being selected (visible in screenshots with blue outlines and "Delete All (4)" in the bottom bar) — but cleared so fast it looked like they weren't.
- Two incorrect theories were chased first: coordinate origin mismatch (`lastX/lastY` fix) and `stopPropagation` blocking `window mouseup`.
- The silver bullet clue came from the user accidentally dragging the lasso past the canvas edge — and selection working. That asymmetry (outside = works, inside = fails) pointed directly at a post-mouseup `click` event firing only within the canvas.

#### The Fix
A `_lassoJustFired` flag already existed in the codebase. It was set to `true` in `onUp` after a lasso selection and cleared after 200ms via `setTimeout`. It was already guarding `onViewportClick`. The only missing piece was the same guard in `onCanvasClick`:
```javascript
function onCanvasClick(e) {
    if (_lassoJustFired) return;   // ← this one line fixed 2 days of debugging
    if (layoutLocked) return;
    // ...
}
```
**Commit SHA:** `05e1bd6` — `+1 / -0` lines.

#### Rule for Future Developers
> **Any time you implement a drag-select, lasso, rubber-band, or marquee selection feature:**
> After the drag ends (`mouseup`), the browser will fire a `click` event. If any `click` handler clears selection state, the selection will appear to vanish instantly. Always set a short-lived flag (e.g., `_lassoJustFired = true; setTimeout(() => _lassoJustFired = false, 200)`) after the drag completes, and guard every canvas/background `click` handler with `if (flag) return;`.
>
> **The symptom:** Drag-select works when mouse is released outside the interactive area but not inside it.
> **The cause:** A `click` event fires after `mouseup` and a handler is clearing the selection.
> **The fix:** A short-lived suppression flag on all click handlers that clear state.

### 🪲 The dataset.id Two-Place Rule Bug (April 2026)
**Feature:** Single-element click selection on the canvas.
**Symptom:** Text elements (and any element type) immediately deselected when clicked.
**Fix:** 1 line per element type — `el.dataset.id = d.id;` added to all three creation blocks in `render()`.
**Commit:** `1ef7db8` — `fix: add dataset.id to all element types in render to fix selection failure`

#### What Happened
Clicking any text element (and potentially images or shapes) caused the element to immediately deselect. The selection visually flashed on and off so fast it appeared the click was simply not registering. The element was selectable via lasso but not via direct click.

#### Root Cause
`onCanvasClick` identifies which element the user clicked by reading `e.target.dataset.id` from the DOM node under the cursor. If that property is missing or empty, the handler cannot match the click to any element in `docV2.elements[]` and falls through to its default behavior: `deselect()`.

The `render()` function builds DOM nodes for every element and appends them to the canvas container. It was setting many properties on the node (position, size, CSS classes, z-index) but was NOT setting `el.dataset.id = d.id` on all element types. It had been set for some types during an earlier patch but the coverage was incomplete — text, images, and lines were inconsistently covered.

#### Why It Was Hard to Find
- The lasso worked correctly because lasso selection uses a bounding-box hit test against `docV2.elements[]` coordinates — it never reads from DOM `dataset`.
- Direct click selection uses a completely different path through the DOM event system, so a missing `dataset.id` only broke click-to-select, not lasso-to-select. This inconsistency made the bug look like a click-event routing problem rather than a missing data attribute.
- The fix location (`render()`) and the failure location (`onCanvasClick`) were far apart in the code, making the connection non-obvious.

#### The Fix
Add `el.dataset.id = d.id;` inside every element creation block in `render()`. There are three blocks: Images, Lines, and Text/Shapes. All three must have it:

```javascript
// Inside render(), for EVERY element type created:
const el = document.createElement('div');
el.dataset.id = d.id;   // ← REQUIRED on every element type, every time
el.style.left = ...;
// ...
```

#### The Two-Place Rule — Mandatory Pattern Going Forward

> ⛔ **THE TWO-PLACE RULE:** Any property that is read by an event handler for element identification MUST be written in every code path that creates or recreates that element.
>
> In this codebase, `dataset.id` is read by:
> - `onCanvasClick` — click-to-select
> - `onCanvasMousedown` — drag-to-move
> - Any future hit-test or interaction handler
>
> `dataset.id` is written in `render()`. If you add a new element type to `render()`, you MUST add `el.dataset.id = d.id;` to that block. No exceptions.
>
> **The test:** After adding any new element type, click it directly. If it deselects immediately, `dataset.id` is missing from its creation block in `render()`.

#### Generalized Rule for Future Developers

> **Any time you add a new element type to a canvas-based editor:**
> Trace every event handler that identifies elements by DOM attribute (e.g., `dataset.id`, `dataset.type`, `data-el-id`). For each one, verify that attribute is set in every branch of the render/create function that produces DOM nodes for that element type. A missing attribute in even one branch will create an inconsistent selection experience that only manifests for that specific element type.
>
> **The symptom:** One element type is click-selectable, another is not — even though the click handler looks correct.
> **The cause:** The non-selectable type's DOM node is missing the identifying attribute the handler reads.
> **The fix:** Add the attribute to that element type's creation block in `render()`.

### 🪲 Text Elements Invisible / Not Selectable (April 2026)

**Feature:** All text elements on the canvas.
**Symptom:** Text elements rendered invisible. Clicking canvas had no effect. Double-click to edit was broken.
**Fix:** 15 lines — a V1→V2 field migration shim added at page load.
**Commit SHA:** `29965b0`

#### Root Cause

The V2 render schema expects `el.content` for text and top-level `el.fontFamily` etc. for styles. But all saved session data on the server was written in V1 format: `el.text` for content and `el.style.fontFamily` etc. for styles. `render()` read `el.content` and found `undefined` → the element had no text → zero height → invisible → unclickable.

#### The Fix

A shim runs once at page load and copies V1 fields into V2 field names for every text element before `render()` is called. `render()` itself was not changed.

#### Rule for Future Developers

> **Never change the expected field names in `render()` without also migrating all existing saved session data on the server.** A schema change in code that doesn't match the stored data will silently break all existing elements. Always add a load-time migration shim when introducing schema changes, and keep it until all server data is confirmed migrated.
---

## 19. Historical Architecture Notes (Legacy / Obsolete)

These references describe old systems that have been completely removed and replaced. They are documented here solely so agents understand what code used to exist and why it is no longer present.

- **Railway Volume (`/app/data/`)**: Persistence is now PostgreSQL. 
- **User Uploads (`/app/data/user_images/`)**: Replaced by Cloudinary + local `Images/` fallback.
- **File System Saves (`/app/data/menu_data.json`)**: Replaced by PostgreSQL `sessions` table (`id='main'`).
- **File System Backups (`/app/data/backups/`)**: No longer utilized; PostgreSQL UPSERT is now the absolute backup paradigm.
- **Env Vars `STORAGE_DIR` & `RAILWAY_VOLUME_MOUNTED`**: Superseded by `DATABASE_URL`.
- **`IS_PERSISTENT` Flag**: Removed. The system trusts connection success/failure for DB.
- **Atomic `.tmp` + `os.replace` write pattern**: Fully abandoned for SQL `INSERT ... ON CONFLICT DO UPDATE`.

