# USER_MANUAL_SOURCE.md
# Dine In Menu Editor Pro V2 — Complete Technical & User Manual Source
**Version**: V2 Phase 29 (Final Polish & UX Hardening)
**Last Updated**: March 17, 2026
**Repository**: mariaisabeljuarezgomez/NOTYOURMAMASKITCHENFULL
**Prepared by**: MARIAS DIGITAL DESIGNS

---

## Document Purpose

This file is the single authoritative source of truth for the Dine In Menu Editor Pro V2. It covers:

1. What the product is and what it does
2. Architecture decisions and locked systems
3. Full feature inventory (current as of Phase 29)
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
**Generator file**: `build_app.py` (authoritative source — never edit `index.html` directly)  
**Compiled output**: `index.html`  
**Backend**: `app.py` (Python/Flask server, Railway Volume persistence at `/app/data`)

### Core Promise
- Fast on mobile — lightweight preview background for editing speed
- Safe for non-technical users — Layout Locked by default
- Reliable across devices — server-side session persistence
- Deterministic print-quality output — 300 DPI PNG export with pHYs metadata injection
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

### 2.2 Split-Asset Performance Strategy
- **Editing background**: `menu-bg-preview.jpg` — lightweight compressed version for fast load
- **Export background**: `menu-bg.png` — full-resolution master, loaded on demand only during export
- This split solved the critical mobile performance problem of loading a 7MB PNG on initial page load

### 2.3 Export Pipeline
- `html2canvas` is lazy-loaded only when Export is triggered
- Export dimensions: 3600 × 5400 pixels (12×18 inches at 300 DPI)
- PNG binary is manually rewritten to inject `pHYs` chunk: 11811 pixels/meter ≈ 300 DPI
- Background rendered as DOM `<img>` element (not CSS background) for correct canvas capture
- Hidden elements are excluded from export render
- Export auto-saves session before rendering

### 2.4 Server-Side Persistence
- Session data stored as JSON at `/app/data` on Railway Volume
- Atomic writes: `.tmp` file + `os.replace()` to prevent corruption
- Frontend retry logic with exponential backoff on save failure
- Local `localStorage` browser backup maintained as secondary safety net
- Cross-device continuity: save on one device → load on another

### 2.5 UI System
- Branded color palette: deep red `#95201d`, warm yellow `#f8f4ad`, gold `#c8a96a`
- Custom modal and toast notification system (no native `alert()` or `confirm()`)
- Focus-managed modal behavior with keyboard handling
- Bilingual in-app manual (English/Spanish via `manual-en.html` / `manual-es.html`)

### 2.6 Interaction Model
- Layout Locked by default on every load (intentional safety feature)
- Undo stack: 30 steps
- Multi-touch drag suppression (second finger cancels active drag)
- Floating zoom buttons (＋/－) visible in top-right when Layout is Unlocked
- New text elements placed at viewport center in world coordinates

---

## 3. Full Feature Inventory (Phase 29 Current)

### 3.1 Top Header Bar
Always visible. Fixed at top of screen.

| Control | Action |
|---------|--------|
| ↺ RELOAD | Reloads the app (prompts save warning). Resets toolbar position. |
| 🔒 Layout Locked / 🔓 Layout Unlocked | Toggles global positioning lock. Default is Locked. |
| ↺ Undo Last Change | Steps back one action in the undo history (up to 30 steps). Keyboard: Ctrl+Z / ⌘+Z |
| 💾 Save | Saves current session to server. |

### 3.2 FAB (Floating Action Button)
The `🛠️` button at bottom-right opens the slide-up Tools Drawer.

### 3.3 Tools Drawer
Slide-up panel with all primary tools.

| Control | Action |
|---------|--------|
| ＋ Add Text | Spawns new blank text element at viewport center |
| 🖼️ Upload Image | Opens image upload dialog. Adds image to Asset Tray and places it on canvas |
| ⬜ Add Rectangle | Adds a new shape element to canvas |
| 💾 Save Session | Server-side session save |
| 📂 Load Session | Loads latest server-saved session (replaces current state) |
| 🔄 Reset to Original | Restores original template. CANNOT be undone. Shows confirmation modal. |
| ⬇️ Export Pro PNG | Triggers full export pipeline. Auto-saves first. Downloads PNG file. Keyboard: Ctrl+E / ⌘+E |
| 📖 Manual (EN) | Opens in-app English user manual |
| 📖 Manual (ES) | Opens in-app Spanish user manual |

### 3.4 Asset Tray
Appears inside the Drawer after images have been uploaded.

- Displays thumbnail grid of all previously uploaded images
- Images are stored server-side (Cloudinary CDN) — persists across sessions
- Tap/click any thumbnail to place that image on the canvas
- Images are not re-uploaded; they are re-placed from the library

### 3.5 Selection Bar (Floating Toolbar)
Appears when any element is selected. Floats above/below the selected element. Draggable via `⠿` handle. Horizontally scrollable on mobile.

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
| Border Width | Stroke thickness |
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

### 3.6 Layers Panel
Accessible from the Tools Drawer. Lists all current elements.

- Each row shows: element name, type icon, visibility toggle (👁️), lock toggle (🔒)
- Click any row to select that element on canvas
- Useful for selecting hidden or stacked elements that are hard to click directly
- Locked elements show 🔒 and cannot be selected via canvas click

### 3.7 Undo System
- Stack depth: 30 steps
- Covers: text edits, moves, style changes (color/font/size/opacity/letter-spacing/line-height), add element, delete element, visibility changes, lock toggles, shape property changes
- Does NOT cover: Reset to Original, Load Session, Export
- Keyboard shortcut: Ctrl+Z (Windows) / ⌘+Z (Mac)

### 3.8 Export Pro PNG
- Keyboard shortcut: Ctrl+E (Windows) / ⌘+E (Mac)
- Auto-saves session before rendering
- Swaps preview background for full-resolution master
- Renders all visible elements to canvas
- Injects 300 DPI pHYs metadata into PNG binary
- Output: 3600×5400px (12×18 in @ 300 DPI)
- Downloads to device automatically as `notyourmamaskitchen-menu.png`

---

## 4. Element Types

### 4.1 Text Elements
- Editable content via double-click (enter text editing mode)
- Style controls: font, size, color, bold, italic, underline, alignment, letter spacing, line height, text shadow
- Multi-line support (Enter key creates new line)
- Blur-commit behavior: clicking outside confirms the edit
- Can be moved (Layout Unlocked), resized, duplicated, deleted, hidden, locked

### 4.2 Image Elements
- Uploaded via the Drawer image upload control
- Stored in Asset Tray (server-side, persistent)
- Auto-trims transparent PNG borders on upload
- Resize handles at corners (Shift+drag for proportional)
- Can be moved, resized, duplicated, deleted, hidden, locked
- Excluded from export if hidden

### 4.3 Shape / Rectangle Elements
- Added via Drawer `⬜ Add Rectangle`
- Fill color, border color, border width, border radius controls
- Opacity control
- Can be moved, resized, duplicated, deleted, hidden, locked
- Useful as overlays, highlight boxes, or decorative frames

---

## 5. Layout Lock System

| State | Behavior | Best For |
|-------|----------|----------|
| 🔒 Layout Locked (Default) | Elements cannot be dragged. Canvas can be scrolled by dragging background. Text can still be double-click edited. | Daily content updates — prices, text, descriptions |
| 🔓 Layout Unlocked | Elements can be dragged to new positions. Floating zoom buttons (＋/－) appear. | Repositioning elements, structural changes |

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
- Frontend retries automatically with exponential backoff if connection fails
- Local browser backup (`localStorage`) is also updated simultaneously

### Load Session
- Downloads the latest server-saved state and replaces the current view
- Used to restore after a browser crash, or to sync across devices
- Does not trigger undo (it is a full state replacement)

### Reset to Original
- Restores the original template exactly as delivered
- Shows a branded confirmation dialog before executing
- **CANNOT be undone** — not in the undo stack
- Clears all custom edits, positions, added elements

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
| Two-finger pinch on canvas | Does not zoom (locked mode) — use zoom buttons instead |
| Single tap on element | Selects element |
| Double-tap on text element | Enters text editing mode, opens keyboard |
| Tap outside elements | Deselects |

### Touch Gestures (Layout Unlocked)
| Gesture | Action |
|---------|--------|
| One-finger drag on element | Moves the element |
| Two-finger touch while dragging | Cancels the drag (multi-touch suppression) |
| Two-finger pinch | Zooms canvas |
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
- Close other apps if editor feels slow

---

## 9. Keyboard Shortcuts (Desktop)

| Shortcut | Action |
|----------|--------|
| Ctrl+Z / ⌘+Z | Undo Last Change |
| Ctrl+E / ⌘+E | Export Pro PNG |
| Enter (in text edit mode) | New line |
| Escape (in text edit mode) | Exit text editing, confirm changes |
| Shift + drag corner (image) | Proportional resize |

---

## 10. Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Cannot click/drag an element | Layout is Locked | Click 🔒 to switch to 🔓 Layout Unlocked |
| Element won't move even when Unlocked | Element has individual Lock toggle enabled | Open LAYER tab → turn off 🔒 for that element |
| Text edits not showing | Didn't double-click to enter edit mode | Double-click the text element; look for cursor before typing |
| Export looks blurry on screen | Normal — screen is lower DPI than export | Open PNG at 100% zoom or send directly to printer |
| Changes not on second device | Forgot to Save on first device | Click 💾 Save before switching devices |
| Save failing | Temporary network issue | Wait and retry; local backup is protecting your work |
| Editor slow or frozen | Memory/browser issue | Save first, then click ↺ RELOAD |
| Lost changes after browser close | Didn't save to server | Always click 💾 Save before closing; rely on server, not browser |
| Hidden element appears in export | Visibility is still ON | Check LAYER tab 👁️ toggle — must be set to 🙈 (hidden) to exclude |
| Selection Bar disappeared | Nothing is selected | Click any element to bring it back |

---

## 11. Build & Deployment Workflow

### To make any change to the app:
1. Edit `build_app.py` (the generator)
2. Run: `python build_app.py` — this regenerates `index.html`
3. Test locally
4. Commit both `build_app.py` and `index.html` to GitHub
5. Railway auto-deploys from the GitHub push

### Key build rules:
- Never edit `index.html` directly — changes will be overwritten on next build
- All JavaScript/CSS literal braces inside Python strings must use `{{` and `}}`
- The doubled-brace escaping strategy is mandatory and must not be removed

### Server files:
- `app.py` — Flask server, handles save/load API endpoints and static file serving
- `requirements.txt` — Python dependencies (Flask, gunicorn)
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
| 1–10 | 2026-03-15 to 03-16 | Initial V2 build: image elements, shape elements, Asset Tray, Selection Bar with LAYER/DESIGN/ARRANGE tabs, Layers Panel, Cloudinary integration |
| 11–12 | 2026-03-17 | Font loading fixes, initialization order, resize handle visibility |
| 13 | 2026-03-17 | Server-side image persistence and Asset Tray library management |
| 14 | 2026-03-17 | Fix drawer clipping (removed hardcoded height) |
| 15 | 2026-03-17 | Fix stacking order and centering logic |
| 16 | 2026-03-17 | Prevent selection and z-index popping for locked/background layers |
| 17 | 2026-03-17 | Hardened locked layer interactions in list selection and CSS hover |
| 18 | 2026-03-17 | Hardened resize, undo, and duplication guards for locked/background layers |
| 19 | 2026-03-17 | Export resolution updated to 12×18 in @ 300 DPI (3600×5400px) |
| 20 | 2026-03-17 | Hardened exportPng() with dynamic height, pre-export toast, background error handling |
| 21 | 2026-03-17 | Hardened export UI with persistent toasts and double-click guard; fixed text editing undo order |
| 22 | 2026-03-17 | Hardened export with try/catch; fixed text undo snapshot timing; optimized session load UI refresh |
| 23 | 2026-03-17 | Multi-line export support, pushState snapshot refactor, export try/catch tightening |
| 24 | 2026-03-17 | Await fonts on export; fix multi-line element dimensions; standardize letter-spacing detection |
| 25 | 2026-03-17 | Fixed toast icon hardcoding; implemented user-zoom persistence guard |
| 26 | 2026-03-17 | Emergency hotfix — font-load fallback and robust render error handling on window.onload |
| 27 | 2026-03-17 | Fix contentEditable boolean bug in render(); fix onTextFocus data model reads; remove rogue sync() from onTextBlur; fix zoom restore on load; fix raw newline SyntaxError |
| 28 | 2026-03-17 | Implement 300 DPI metadata injection (pHYs chunk); add PNG helper functions |
| 29 | 2026-03-17 | Final Polish & UX Hardening (9 fixes): tooltip audit, interaction polish, production stability |

---

## 13. Locked Architecture Decisions (Do Not Change Without Strong Reason)

1. **Generator model** — `build_app.py` is the source of truth
2. **Split-asset strategy** — preview for editing, master for export
3. **300 DPI pHYs injection** — manual binary rewrite of PNG metadata
4. **Railway Volume persistence** — atomic JSON writes at `/app/data`
5. **Layout Locked as default** — intentional; do not change to unlocked default
6. **Undo stack depth: 30** — sufficient for real usage, bounded for memory
7. **html2canvas lazy-load** — only loaded on export trigger, not on page load
8. **Cloudinary for image CDN** — uploaded images served from Cloudinary, not local storage
9. **Branded UI system** — no native browser alerts/confirms; always use custom modals/toasts
10. **Doubled-brace escaping** — mandatory in all Python generator string blocks

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

---

## 15. What Is Still Outside Current Scope

The following are not part of the current production system and should not be confused with existing features:

- Customer-facing read-only viewer (not built)
- Multi-template or multi-restaurant platform (not built)
- Video/animation/promo output (not built)
- Broad self-serve onboarding (not built)

These remain future possibilities only.

---

*End of USER_MANUAL_SOURCE.md — Phase 29 Final*
