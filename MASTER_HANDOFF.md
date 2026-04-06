# Dine In Menu Editor Pro — MASTER HANDOFF
**Last Updated:** March 29, 2026  
**Prepared by:** MARIAS DIGITAL DESIGNS  
**Live URL:** https://web-production-3e17d.up.railway.app/  
**GitHub Repo:** https://github.com/mariaisabeljuarezgomez/NOTYOURMAMASKITCHENFULL  
**Deployment:** Railway (auto-deploys from GitHub `main` branch)  
**Latest Known Good SHA:** `6bc7fe4` — Bug Fix Batch 8  
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
| Persistence | Railway Volume (`/app/data/`) — JSON files |
| Hosting | Railway (auto-deploy from GitHub push) |
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

### Persistence
- Railway Volume mounted at `/app/data`
- Save file: `/app/data/menu_data.json`
- Backups: `/app/data/backups/menu_data_YYYYMMDD_HHMMSS.json`
- Writes use atomic `.tmp` + `os.replace` pattern
- Frontend has localStorage fallback if server unreachable
- `IS_PERSISTENT` flag in API response warns if volume is unavailable

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

## 4. What Was Built Successfully (Full History)

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
  "originalHeight": 600
}
```
- `src` is the export source of truth — always same-origin
- `assetId` references the asset registry entry

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
| Server save path | `/app/data/menu_data.json` |
| User images path | `/app/data/user_images/` |
| Railway volume env var | `STORAGE_DIR` (defaults to `/app/data`) |
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

1. **Reconcile `build_app.py` with `index.html`** — migrate all Phases 2A–11 + Bug Batches 1–8 back into the generator. Until done, index.html remains the live source.

2. **Behavior verification matrix** — full manual test pass: edit mode, lock states, undo ordering, save/load cross-device, style persistence. Goal: confirm every feature works end-to-end, not just that the code exists.

3. **Read-Only Viewer** — separate route, read-only, no editor controls, no persistence mutation. Reuses the same rendering model. **Only build this after the editor is fully verified.**

4. **Future extensions** — Cloudinary delivery, multi-page, template library. These are Stage 3 and beyond.

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

*This file consolidates: HANDOFF_V3.md (Mar 28, 2026) + DINE_IN_MENU_EDITOR_PRO_COMPREHENSIVE_MASTER_HANDOFF.md + MASTER_TECHNICAL_SPEC.md*  
*Begin all new threads by pasting this file as the first message to any AI assistant.*
