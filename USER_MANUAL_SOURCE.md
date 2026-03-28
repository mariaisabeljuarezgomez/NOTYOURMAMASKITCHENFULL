# USER_MANUAL_SOURCE.md
# Dine In Menu Editor Pro V2 — Complete Technical & User Manual Source
**Version**: V2 Phase 30 + Phases 2A–11 + Bug Fix Batches 1–8 (Fully Hardened)
**Last Updated**: March 28, 2026
**Repository**: mariaisabeljuarezgomez/NOTYOURMAMASKITCHENFULL
**Prepared by**: MARIAS DIGITAL DESIGNS

> ⚠️ **GENERATOR FROZEN**: All Phases 2A–11 and Bug Fix Batches 1–8 (18 bugs) were applied **directly to `index.html`**. `build_app.py` is frozen at Phase 30. Treat `index.html` as the live source of truth. Do NOT run `python build_app.py` until all patches are reconciled into the generator.

---

## Document Purpose

This file is the single authoritative source of truth for the Dine In Menu Editor Pro V2. It covers:

1. What the product is and what it does
2. Architecture decisions and locked systems
3. Full feature inventory (current as of Phase 30 + Phases 2A–11)
4. User-facing control reference
5. Save/Load/Export/Undo behavior
6. Mobile usage guide
7. Troubleshooting
8. Build and deployment workflow
9. Phase history summary

This document should be updated whenever a Phase commit changes user-facing behavior, architecture, or the feature set.

---

## 1. Product Identity

**Product Name**: Dine In Menu Editor Pro V2
**Type**: Browser-based, professional-grade restaurant menu layout editor
**Deployed on**: Railway cloud platform
**Live URL**: https://web-production-3e17d.up.railway.app/
**Generator file**: `build_app.py` (frozen at Phase 30 — see warning above)
**Live source**: `index.html` (manually patched through Phase 11 + Bug Batches 1–8)
**Backend**: `app.py` (Python/Flask server, Railway Volume persistence at `/app/data`)
**Latest SHA**: `6bc7fe4`

### Core Promise
- Fast on mobile — PageSpeed 100/100/100/100 (achieved March 27, 2026)
- Safe for non-technical users — Layout Locked by default
- Reliable across devices — server-side session persistence
- Deterministic print-quality output — 300 DPI Canvas API PNG export with pHYs metadata injection
- Professional UI/UX — branded modal/toast system, no native browser prompts

### What This Product Is NOT
- Not a simple text editor
- Not a hand-edited HTML file (it is a compiled, generator-based application)
- Not a multi-restaurant SaaS platform (single client, single menu design)

---

## 2. Architecture — Locked Systems

These systems are stable and hardened. Do not casually reopen them.

### 2.1 Generator Model
- **Source**: `build_app.py` — the only file that should be edited to change the app
- **Output**: `index.html` — compiled artifact, never edited directly
- **Escaping rule**: All literal JavaScript/CSS braces inside the Python generator use doubled-brace escaping (`{{` and `}}`) to prevent Python f-string collisions
- **Current exception**: `index.html` has been manually patched (Phases 2A–11, Bug Batches 1–8). Do NOT regenerate until patches are reconciled into `build_app.py`.

### 2.2 Split-Asset Performance Strategy
- **Editing background**: `menu-bg-preview.jpg` — lightweight compressed version (~114 KB) loaded with `fetchpriority="high"`
- **Export background**: `menu-bg.png` — full-resolution master (~7.2 MB), loaded on demand only during export
- This split is critical — it solved the LCP problem and is required for PageSpeed 100

### 2.3 Export Pipeline
- Export uses the **Canvas API exclusively** — `html2canvas` has been fully removed
- Export dimensions: 3600 × 5400 pixels (12×18 inches at 300 DPI)
- Elements rendered in ascending `zIndex` order onto an off-screen Canvas
- PNG binary is manually rewritten by `inject300DpiAndDownload()` in `export-utils.js` to inject the `pHYs` chunk (11811 pixels/meter = 300 DPI)
- Rounded shapes (cornerRadius) use a re-traced bezier path for stroke — full stroke thickness at correct corners
- Export auto-saves session before rendering
- `export-utils.js` is loaded with `defer` attribute (required for PageSpeed 100)

### 2.4 Server-Side Persistence
- Session data stored as JSON at `/app/data` on Railway Volume
- Atomic writes: `.tmp` file + `os.replace()` to prevent corruption
- Frontend retry logic with auto-save every 30 seconds
- Local `localStorage` browser backup maintained as secondary safety net
- Cross-device continuity: save on one device → load on another

### 2.5 UI System
- Branded color palette: deep red `#95201d`, warm yellow `#f8f4ad`, gold `#c8a96a`
- Custom modal and toast notification system (no native `alert()` or `confirm()`)
- Focus-managed modal behavior with keyboard handling
- Bilingual in-app manual (English/Spanish via `manual-en.html` / `manual-es.html`)
- Full standalone English manual: `manual-en-full.html` (added March 27, 2026)

### 2.6 Interaction Model
- Layout Locked by default on every load (intentional safety feature)
- Undo stack: 30 steps
- Multi-touch drag suppression (second finger cancels active drag)
- Floating zoom buttons (＋/－) visible in top-right when Layout is Unlocked
- New elements (text, rect) placed at viewport center in world coordinates — never at hardcoded positions
- Ctrl+Z during active text editing passes through to the browser (native character undo) — only fires editor undo when idle

---

## 3. Full Feature Inventory (Phase 30 + Phases 2A–11 Current)

### 3.1 Top Header Bar
Always visible. Fixed at top of screen.

| Control | Action |
|---------|--------|
| ↺ RELOAD | Reloads the app (prompts save warning). Resets toolbar position. |
| 🔒 Layout Locked / 🔓 Layout Unlocked | Toggles global positioning lock. Default is Locked. |
| ↺ Undo Last Change | Steps back one action in the undo history (up to 30 steps). Keyboard: Ctrl+Z / ⌘+Z |
| 💾 Save | Saves current session to server. Shows success/failure toast. |

### 3.2 FAB (Floating Action Button)
The `🛠️` button at bottom-right opens the slide-up Tools Drawer.

### 3.3 Tools Drawer
Slide-up panel with all primary tools.

| Control | Action |
|---------|--------|
| ＋ Add Text | Spawns new blank text element at viewport center |
| 🖼️ Upload Image | Opens image upload dialog. Adds image to Asset Tray and places it on canvas |
| ⬜ Add Rectangle | Adds a new shape element at viewport center |
| 💾 Save Session | Server-side session save |
| 📂 Load Session | Loads latest server-saved session (replaces current state). Prompts if dirty. |
| 🔄 Reset to Original | Restores original template. CANNOT be undone. Shows confirmation modal. Clears localStorage on success. |
| ⬇️ Export Pro PNG | Triggers full Canvas API export pipeline. Auto-saves first. Downloads PNG file. |
| 📖 Manual (EN) | Opens in-app English user manual |
| 📖 Manual (ES) | Opens in-app Spanish user manual |

### 3.4 Asset Tray
Appears inside the Drawer after images have been uploaded.

- Displays thumbnail grid of all previously uploaded images
- Images are stored server-side (Railway Volume) — persists across sessions
- Tap/click any thumbnail to place that image on the canvas
- Each thumbnail has a ✕ delete button to remove from library
- Failed thumbnails retry load automatically (no stale guard lockout)
- Images are not re-uploaded; they are re-placed from the library

### 3.5 Selection Bar (Floating Toolbar)
Appears when any element is selected. Floats above/below the selected element. Draggable via `⠿` handle (pointer capture). Horizontally scrollable on mobile.

**Three tabs:**

#### LAYER Tab
| Control | Action |
|---------|--------|
| Name field | Editable label for this element (shown in Layers Panel) |
| 👁️ Visibility toggle | Show/hide element. Hidden elements are excluded from export. |
| 🔒 Lock toggle | Locks this specific element (cannot be selected or moved) |
| Opacity slider | 0–100% opacity |
| Role selector | Background / Content / Overlay — affects z-order grouping |

#### DESIGN Tab (Text Elements)
| Control | Action |
|---------|--------|
| Font selector | Dropdown of available brand fonts |
| Size +/− buttons | Increase/decrease font size by 1px |
| Color picker | Text color |
| Letter Spacing | Numeric input (em units) |
| Line Height | Numeric input |
| Bold / Italic / Underline toggles | Text style |
| Alignment buttons | Left / Center / Right |
| Text Shadow toggle | On/off |

#### DESIGN Tab (Image Elements)
| Control | Action |
|---------|--------|
| Opacity | Image opacity |
| Proportional resize | Shift+drag corner handle to resize proportionally |
| Auto-trim | Transparent pixel auto-trimming on PNG upload |

#### DESIGN Tab (Shape/Rectangle Elements)
| Control | Action |
|---------|--------|
| Fill Color | Shape background color |
| Border Color | Shape border/stroke color |
| Border Width | Stroke thickness (renders correctly with corner radius) |
| Border Radius | Corner rounding (0 = sharp, higher = rounded) |
| Opacity | Shape opacity |

#### ARRANGE Tab
| Control | Action |
|---------|--------|
| Bring to Front | Moves element to highest z-index |
| Bring Forward | Moves element up one z-level |
| Send Backward | Moves element down one z-level |
| Send to Back | Moves element to lowest z-index |
| Duplicate | Creates an identical copy of the selected element |
| Delete | Removes the element (covered by Undo) |

### 3.6 Multi-Select (Phase 3 + Phase 7 + Phase 10)
Select multiple elements at once for group operations.

| Method | How |
|--------|-----|
| Shift+click | Click additional elements while holding Shift |
| Lasso drag | Drag on empty canvas area to draw a selection box (mouse) |
| Touch lasso | One-finger drag on empty canvas area (mobile, Layout Unlocked) |
| Ctrl+A | Select all elements |

**Group operations available on multi-select:**
- Move all selected elements together
- Delete all selected (single history entry, single render)
- Duplicate all selected
- Count shown in selection bar header

### 3.7 Alignment & Distribution Tools (Phase 6)
Available in the ARRANGE tab when multiple elements are selected.

| Tool | Action |
|------|--------|
| Align Left | Align all selected elements to leftmost edge |
| Align Center (H) | Center horizontally across selection |
| Align Right | Align to rightmost edge |
| Align Top | Align to topmost edge |
| Align Middle (V) | Center vertically across selection |
| Align Bottom | Align to bottommost edge |
| Distribute Horizontally | Equal spacing between elements left-to-right |
| Distribute Vertically | Equal spacing between elements top-to-bottom |

### 3.8 Layers Panel
Accessible from the Tools Drawer. Lists all current elements.

- Each row shows: element name, type icon, visibility toggle (👁️), lock toggle (🔒)
- Click any row to select that element on canvas
- Useful for selecting hidden or stacked elements that are hard to click directly
- Locked elements show 🔒 and cannot be selected via canvas click

### 3.9 Undo System
- Stack depth: 30 steps
- Covers: text edits (committed on blur), element moves (including group drag), style changes (color/font/size/opacity/letter-spacing/line-height), add element (text, image, rect), delete element, visibility changes, lock toggles, shape property changes, duplicate, addFromTray placement
- Does NOT cover: Reset to Original, Load Session, Export, zoom changes
- Keyboard: Ctrl+Z (Windows) / ⌘+Z (Mac)
- **Smart guard**: Ctrl+Z during active text editing passes through to browser native undo — does NOT pop editor history while typing

### 3.10 Export Pro PNG
- Triggers full Canvas API render pipeline (NOT html2canvas)
- Auto-saves session before rendering
- Swaps preview background for full-resolution master (`menu-bg.png`)
- Renders all visible elements in zIndex order
- Rounded shapes with strokes: re-traces the same bezier path — full stroke thickness at correct rounded corners
- Injects 300 DPI pHYs metadata into PNG binary via `inject300DpiAndDownload()`
- Output: 3600×5400px (12×18 in @ 300 DPI)
- Downloads to device automatically as `notyourmamaskitchen-menu.png`

### 3.11 Save / Load Hardening (Phase 11)
- **Dirty state indicator**: Save button shows unsaved state visually
- **Auto-save**: Runs every 30 seconds automatically
- **Error toasts**: Visible feedback on save/load failure
- **localStorage fallback**: Always written on successful server save; used as fallback if server unreachable on load

---

## 4. Element Types

### 4.1 Text Elements
- Editable content via double-click (enter text editing mode)
- Style controls: font, size, color, bold, italic, underline, alignment, letter spacing, line height, text shadow
- Multi-line support (Enter key creates new line; multi-line text renders correctly in PNG export)
- Blur-commit behavior: clicking outside confirms the edit; `innerText` used consistently (not `innerHTML`) for correct newline capture
- Can be moved (Layout Unlocked), resized, duplicated, deleted, hidden, locked
- Arrow keys nudge selected text element by 1px when not in text edit mode

### 4.2 Image Elements
- Uploaded via the Drawer image upload control
- Stored in Asset Tray (server-side Railway Volume, persistent)
- Auto-trims transparent PNG borders on upload
- Resize handles at corners (Shift+drag for proportional)
- Can be moved, resized, duplicated, deleted, hidden, locked
- Excluded from export if hidden
- Placing from tray: single `pushState` entry (no duplicate history from upload path)

### 4.3 Shape / Rectangle Elements
- Added via Drawer `⬜ Add Rectangle`
- Always placed at visible viewport center — never at a hardcoded off-screen position
- Fill color, border color, border width, border radius controls
- Opacity control
- Border strokes with `cornerRadius` render correctly in PNG export (full thickness, rounded corners)
- Can be moved, resized, duplicated, deleted, hidden, locked
- Useful as overlays, highlight boxes, or decorative frames

---

## 5. Layout Lock System

| State | Behavior | Best For |
|-------|----------|----------|
| 🔒 Layout Locked (Default) | Elements cannot be dragged. Canvas can be scrolled by dragging background. Text can still be double-click edited. | Daily content updates — prices, text, descriptions |
| 🔓 Layout Unlocked | Elements can be dragged to new positions. Floating zoom buttons (＋/－) appear. Lasso multi-select available. | Repositioning elements, structural changes |

**Critical rules:**
- The editor loads in Layout Locked state every single time — this is intentional
- Text editing (double-click) works in BOTH lock states — you never need to unlock just to edit text
- Re-lock immediately after finishing any drag operation
- On mobile: stay Locked unless actively dragging

---

## 6. Save / Load / Reset

### Save Session
- Uploads current state (all elements, positions, styles, content) to Railway Volume
- Uses atomic write (`.tmp` + `os.replace`) to prevent data corruption
- Auto-save runs every 30 seconds
- Local browser backup (`localStorage`) is also updated simultaneously
- Dirty state indicator on Save button shows when unsaved changes exist

### Load Session
- Downloads the latest server-saved state and replaces the current view
- Used to restore after a browser crash, or to sync across devices
- Prompts user if there are unsaved changes (dirty state)
- Does not trigger undo (it is a full state replacement)

### Reset to Original
- Restores the original template exactly as delivered
- Shows a branded confirmation dialog before executing
- **CANNOT be undone** — not in the undo stack
- Clears all custom edits, positions, added elements
- On success: clears localStorage to prevent stale data reload
- On failure: shows error toast without reloading page

---

## 7. Cross-Device Workflow

1. On Device A: finish edits → click 💾 Save Session
2. On Device B: open editor link → open Drawer → click 📂 Load Session
3. All content, positions, styles, and uploaded image library are synced

---

## 8. Mobile Guide

### Recommended Browser
- iPhone/iPad: Safari
- Android: Chrome
- Add to home screen for app-like access

### Touch Gestures (Layout Locked)
| Gesture | Action |
|---------|--------|
| One-finger drag on background | Pans/scrolls the canvas |
| Single tap on element | Selects element |
| Double-tap on text element | Enters text editing mode, opens keyboard |
| Tap outside elements | Deselects |

### Touch Gestures (Layout Unlocked)
| Gesture | Action |
|---------|--------|
| One-finger drag on element | Moves the element |
| One-finger drag on empty area | Lasso multi-select |
| Two-finger touch while dragging | Cancels the drag (multi-touch suppression) |
| ＋/－ floating buttons | Zoom in/out |

### Mobile Selection Bar
- Appears at bottom when element selected
- Swipe horizontally to reveal all tabs and buttons
- Drag `⠿` handle to reposition if it overlaps content

### Mobile Best Practices
- Use Wi-Fi for Save/Load operations
- Save before closing the browser
- Keep Layout Locked except when dragging
- Landscape orientation recommended for more canvas space
- Canvas auto-fits to screen width on load (`fitCanvasToScreen`)
- Previously set manual zoom is restored on reload

---

## 9. Keyboard Shortcuts (Desktop)

| Shortcut | Action |
|----------|--------|
| Ctrl+Z / ⌘+Z | Undo Last Change (passes through to browser during active text edit) |
| Ctrl+D / ⌘+D | Duplicate selected element |
| Ctrl+A / ⌘+A | Select all elements |
| Delete / Backspace | Delete selected element(s) |
| Arrow keys | Nudge selected element 1px in any direction |
| Ctrl+E / ⌘+E | Export Pro PNG |
| Enter (in text edit mode) | New line |
| Escape (in text edit mode) | Exit text editing, confirm changes |
| Shift+click | Add to / remove from multi-select |
| Shift+drag corner (image) | Proportional resize |

---

## 10. Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Cannot click/drag an element | Layout is Locked | Click 🔒 to switch to 🔓 Layout Unlocked |
| Element won't move even when Unlocked | Element has individual Lock toggle enabled | Open LAYER tab → turn off 🔒 for that element |
| Text edits not showing | Didn't double-click to enter edit mode | Double-click the text element; look for cursor before typing |
| Ctrl+Z reverted whole element instead of one character | Expected — Ctrl+Z during text editing is now browser-native | Press Ctrl+Z again while still in text edit mode to undo individual characters |
| Export looks blurry on screen | Normal — screen is lower DPI than export | Open PNG at 100% zoom or send directly to printer |
| Rounded shape border looks thin/clipped | Old bug — fixed in Bug Batch 7 | Update to latest SHA (`6bc7fe4`) |
| Changes not on second device | Forgot to Save on first device | Click 💾 Save before switching devices |
| Save failing | Temporary network issue | Wait and retry; auto-save will retry; local backup is protecting your work |
| Editor slow or frozen | Memory/browser issue | Save first, then click ↺ RELOAD |
| Lost changes after browser close | Didn't save to server | Always click 💾 Save before closing; rely on server, not browser |
| Hidden element appears in export | Visibility is still ON | Check LAYER tab 👁️ toggle — must be set to hidden to exclude |
| Selection Bar disappeared | Nothing is selected | Click any element to bring it back |
| Added rect not visible | Canvas was scrolled far down (old bug — fixed) | Update to latest SHA — rect now places at viewport center |
| Canvas not fitting screen on load | Old bug — fixed in Bug Batch 5 | `fitCanvasToScreen()` now correctly scales to viewport width |

---

## 11. Build & Deployment Workflow

### Current State (March 28, 2026)
`index.html` is the live source. `build_app.py` is frozen at Phase 30. **Do not run `python build_app.py`** until all manual patches (Phases 2A–11, Bug Batches 1–8) have been reconciled into the generator.

### Normal workflow (when generator is reconciled):
1. Edit `build_app.py` (the generator)
2. Run: `python build_app.py` — this regenerates `index.html`
3. Test locally
4. Commit both `build_app.py` and `index.html` to GitHub
5. Railway auto-deploys from the GitHub push

### Current workflow (generator frozen):
1. Edit `index.html` directly with care
2. Commit `index.html` to GitHub
3. Railway auto-deploys from the GitHub push

### Key build rules:
- Never run `python build_app.py` in the current frozen state
- All JavaScript/CSS literal braces inside Python f-strings must use `{{` and `}}`
- The doubled-brace escaping strategy is mandatory and must not be removed

### Server files:
- `app.py` — Flask server, handles save/load API endpoints and static file serving
- `requirements.txt` — Python dependencies (Flask, flask-compress)
- `Procfile` — Railway process definition
- `/app/data/` — Railway Volume mount point for session JSON storage

### Utility scripts:
- `create_preview.py` — generates `menu-bg-preview.jpg` from `menu-bg.png`
- `fix_braces.py` — diagnostic tool for brace escaping issues
- `fix_coords.py` — coordinate migration utility
- `read_example.py` — example session data reader

---

## 12. Phase History Summary

| Phase | Date | Key Change |
|-------|------|------------|
| 1–10 | 2026-03-15 to 03-16 | Initial V2 build: image elements, shape elements, Asset Tray, Selection Bar with LAYER/DESIGN/ARRANGE tabs, Layers Panel |
| 11–26 | 2026-03-17 | Font loading, resize handles, server image persistence, drawer fixes, stacking order, locked layer hardening, export resolution (12×18 @ 300 DPI), export UI, multi-line export, font await, zoom persistence |
| 27 | 2026-03-17 | Fix contentEditable boolean; fix onTextFocus data reads; remove rogue sync() from onTextBlur; fix zoom restore; fix raw newline SyntaxError |
| 28 | 2026-03-17 | 300 DPI pHYs metadata injection; PNG binary helper functions |
| 29 | 2026-03-17 | Final Polish & UX Hardening (9 fixes): tooltip audit, interaction polish, production stability |
| 30 | 2026-03-27 | **PageSpeed 100**: defer export-utils.js, remove duplicate font (centurygothic.ttf), 7-day cache headers on static assets, Save button contrast fix |
| Phase 2A | 2026-03-27 | V2 schema migration + asset registry |
| Phase 2B | 2026-03-27 | Asset-linked image placement via `assetId` |
| Phase 2C | 2026-03-27 | User upload persisted to asset registry |
| Phase 2D | 2026-03-27 | Asset registry round-trip save/restore |
| Phase 3 | 2026-03-27 | Multi-select: Shift+click, group move/delete/duplicate |
| Phase 4 | 2026-03-27 | Keyboard shortcuts: Delete, Ctrl+D/A/Z, Arrow nudge |
| Phase 5 | 2026-03-27 | Font size control + text block width wrapping |
| Phase 6 | 2026-03-27 | 8-way alignment and distribution tools |
| Phase 7 | 2026-03-27 | Lasso drag-box multi-select (mouse + touch) |
| Phase 8 | 2026-03-27 | Export PNG text rendering fix |
| Phase 9 | 2026-03-27 | Undo history integrity (group drag guard, memory cap) |
| Phase 10 | 2026-03-27 | Mobile lasso & touch multi-select |
| Phase 11 | 2026-03-27 | Save/Load hardening: dirty state, 30s auto-save, error UI, localStorage fallback |
| Bug Batch 1 | 2026-03-27 | Asset merge fix, sync() guard, header dup noRender — SHA `600009a` |
| Bug Batch 2 | 2026-03-27 | Arrow nudge else-if, textContent→innerText, export image guard — SHA `da85954` |
| Bug Batch 3 | 2026-03-27 | deleteEl order, resetToOriginal localStorage clear, lasso scale ratio — SHA `9664b41` |
| Bug Batch 4 | 2026-03-27 | addFromTray pushState, onload fallback, bgLayer fix, toolbar anim — SHA `d4f71fb` |
| Bug Batch 5 | 2026-03-28 | innerText consistency, fitCanvasToScreen functional, openDrawer retry — SHA `e210f58` |
| Bug Batch 6 | 2026-03-28 | Ctrl+Z text guard, export rounded stroke path, addRect viewport pos — SHA `939a940` |
| Bug Batch 7 | 2026-03-28 | deleteEl noRender param, addFromTray skipPush, fitCanvas zoom persistence — SHA `6bc7fe4` |

---

## 13. Locked Architecture Decisions (Do Not Change Without Strong Reason)

1. **Generator model** — `build_app.py` is the source of truth (currently frozen; `index.html` is live)
2. **Split-asset strategy** — preview for editing, master for export; never swap
3. **Canvas API export** — deterministic, no DOM capture artifacts, no CORS issues; html2canvas permanently removed
4. **300 DPI pHYs injection** — manual binary rewrite of PNG metadata; only reliable browser method
5. **Railway Volume persistence** — atomic JSON writes at `/app/data`; backbone of cross-device sync
6. **Layout Locked as default** — intentional; do not change to unlocked default
7. **Undo stack depth: 30** — sufficient for real usage, bounded for memory
8. **`defer` on export-utils.js** — required for PageSpeed 100; do not remove
9. **User images served from same origin** — cross-origin images cannot be drawn to Canvas
10. **`document.fonts.load()` awaited before export** — prevents garbled text in exported PNG
11. **Branded UI system** — no native browser alerts/confirms; always use custom modals/toasts
12. **Multi-touch second-finger cancels drag** — prevents layout damage when pinch-zoom is attempted
13. **`Cache-Control: no-cache` on index.html** — users must always get fresh app; static assets get 7-day cache
14. **`innerText` (not `innerHTML`) for text capture** — correct newline handling, XSS prevention
15. **`addText()` / `addRect()` place at viewport center** — never hardcoded coordinates; always visible to user

---

## 14. UI Vocabulary (Fixed Terms — Use Exactly As Listed)

These terms appear in the UI and documentation and must remain consistent:

- Edit Mode (ON/OFF)
- Layout Locked / Layout Unlocked
- Save Session / Load Session
- Undo Last Change
- Reset to Original
- Export Pro PNG
- Asset Tray
- Selection Bar
- Layers Panel
- LAYER tab / DESIGN tab / ARRANGE tab
- Background / Content / Overlay (element roles)
- Add Text / Add Rect / Upload Img
- Bring to Front / Bring Forward / Send Backward / Send to Back

---

## 15. What Is Still Outside Current Scope

The following are not part of the current production system and should not be confused with existing features:

- Customer-facing read-only viewer (not built)
- Multi-template or multi-restaurant platform (not built)
- Video/animation/promo output (not built)
- Broad self-serve onboarding (not built)
- Cloudinary CDN delivery for user uploads (partially referenced in data model, not fully wired)
- Reconciliation of `build_app.py` with `index.html` manual patches (pending)

---

*End of USER_MANUAL_SOURCE.md — Updated March 28, 2026 (Phase 30 + Phases 2A–11 + Bug Fix Batches 1–8)*
