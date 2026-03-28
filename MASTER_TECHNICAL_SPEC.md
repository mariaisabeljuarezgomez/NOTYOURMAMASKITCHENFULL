# MASTER_TECHNICAL_SPEC.md
# Dine In Menu Editor Pro V2 — Master Technical Specification
**Version**: V2 Phase 30+ Fully Hardened  
**Last Updated**: March 28, 2026  
**Repository**: [mariaisabeljuarezgomez/NOTYOURMAMASKITCHENFULL](https://github.com/mariaisabeljuarezgomez/NOTYOURMAMASKITCHENFULL)  
**Deployed on**: Railway  
**Prepared by**: MARIAS DIGITAL DESIGNS

> ⚠️ **GENERATOR FROZEN**: As of March 28, 2026, all Phases 2A–11 and Bug Fix Batches 1–8 (21 bugs) were applied **directly to `index.html`**. `build_app.py` has NOT been updated and is frozen at Phase 30. Treat `index.html` as the live source of truth. Do NOT run `python build_app.py` until all patches have been reconciled into the generator. See `HANDOFF_V3.md` for the complete patch history.

---

## Table of Contents

1. [Product Summary](#1-product-summary)
2. [Repository File Map](#2-repository-file-map)
3. [Build System](#3-build-system)
4. [Backend Server — app.py](#4-backend-server--apppy)
5. [API Endpoints](#5-api-endpoints)
6. [Storage Architecture](#6-storage-architecture)
7. [Frontend Architecture](#7-frontend-architecture)
8. [Element Data Model](#8-element-data-model)
9. [Session Data Schema](#9-session-data-schema)
10. [Asset Pipeline](#10-asset-pipeline)
11. [Export Pipeline — 300 DPI PNG](#11-export-pipeline--300-dpi-png)
12. [Undo System](#12-undo-system)
13. [Interaction Model — Layout Lock & Touch](#13-interaction-model--layout-lock--touch)
14. [UI Component Inventory](#14-ui-component-inventory)
15. [Font System](#15-font-system)
16. [Performance Architecture](#16-performance-architecture)
17. [Deployment — Railway](#17-deployment--railway)
18. [Known Constraints & Edge Cases](#18-known-constraints--edge-cases)
19. [Phase Commit Log](#19-phase-commit-log)
20. [Locked Decisions — Do Not Change](#20-locked-decisions--do-not-change)

---

## 1. Product Summary

**Dine In Menu Editor Pro V2** is a browser-based, professional-grade menu layout editor for restaurant use. It is a generator-compiled single-page application served by a Python/Flask backend, deployed on Railway with persistent Volume storage.

### Key Design Constraints
- Must load fast on mobile (PageSpeed 100 achieved March 27, 2026)
- Must be safe for non-technical users (Layout Locked by default)
- Must produce print-quality output regardless of device used for editing
- Must survive browser cache clears via server-side persistence
- Must run entirely in-browser with zero client installation

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Generator | Python 3 (`build_app.py`) |
| Frontend | HTML5, CSS3, Vanilla JavaScript, Canvas API |
| Export engine | **Canvas API + `export-utils.js`** (deterministic, NO html2canvas) |
| Backend | Python 3, Flask, flask-compress |
| Persistence | Railway Volume (`/app/data/`) — JSON files |
| Image storage | Railway Volume (`/app/data/user_images/`) |
| CDN/Compression | flask-compress (gzip all assets) |
| Hosting | Railway (auto-deploy from GitHub push) |
| Fonts | Local TTF files served as static assets |

> ⚠️ **html2canvas has been removed from this project.** The export pipeline was migrated to a deterministic Canvas API renderer. `export-utils.js` provides `inject300DpiAndDownload()`. Any reference to html2canvas in older docs is outdated.

---

## 2. Repository File Map

```
NOTYOURMAMASKITCHENFULL/
│
├── build_app.py              ← AUTHORITATIVE SOURCE. Generates index.html.
├── index.html                ← COMPILED OUTPUT. Never edit directly.
├── app.py                    ← Flask server (routes, save/load/image APIs)
├── export-utils.js           ← Export utility: inject300DpiAndDownload(). Loaded with defer.
├── requirements.txt          ← Flask, flask-compress
├── Procfile                  ← Railway process: python app.py
│
├── menu-bg.png               ← Master background (7.2 MB, full res, export only)
├── menu-bg-preview.jpg       ← Preview background (~114 KB, editing only)
│
├── bernard-mt-condensed-regular.ttf
├── century-gothic-regular.ttf
├── century-gothic-bold.ttf
├── century-gothic-bold-italic.ttf
│   NOTE: centurygothic.ttf was a duplicate alias and was DELETED on March 27, 2026.
│
├── manual-en.html            ← In-app English user manual (standalone HTML)
├── manual-en-full.html       ← Full standalone English manual (added March 27, 2026)
├── manual-es.html            ← In-app Spanish user manual (standalone HTML)
│
├── HANDOFF_V3.md             ← MASTER CONTINUITY DOC (supersedes older handoff files)
├── MASTER_TECHNICAL_SPEC.md  ← This file
├── CONTINUITY_HANDOFF_CURRENT.md  ← Older handoff — superseded by HANDOFF_V3.md
├── USER_MANUAL_SOURCE.md     ← User-facing manual source
├── dine_in_menu_editor_v2_data_model_contract.md  ← V2 schema contract
│
├── create_preview.py         ← Utility: generates menu-bg-preview.jpg from menu-bg.png
├── fix_braces.py             ← Utility: diagnostic for brace escaping issues in build_app.py
├── fix_coords.py             ← Utility: coordinate migration tool
├── read_example.py           ← Utility: session JSON reader example
├── raw_coords.json           ← Source coordinate data for element positioning
│
├── .gitignore
├── Images/                   ← Static tray image assets (Asset1–14.png)
├── MANUAL/                   ← Manual source folder
└── legacy_docs/              ← Archived older documentation
```

---

## 3. Build System

### Generator Model
The application uses a strict generator-first model:

```
build_app.py  →  python build_app.py  →  index.html
```

- `build_app.py` is the **only** file that should be edited to change the app behavior
- `index.html` is a **compiled artifact** — it will be overwritten by the next build run
- Any direct edits to `index.html` will be permanently lost on the next build

### Brace Escaping Rule
`build_app.py` uses Python f-strings to emit JavaScript and CSS. All literal braces in emitted JS/CSS must be doubled:

```python
# CORRECT — literal JS brace in Python f-string
js_code = f"""
  const obj = {{key: value}};
"""

# WRONG — Python f-string interprets this as a variable reference
js_code = f"""
  const obj = {key: value};   # SyntaxError or variable injection
"""
```

This rule is **mandatory** and must be preserved in all future edits to `build_app.py`.

### Build Command
```bash
python build_app.py
```
Run from the repo root. Produces `index.html` in the same directory.

### After Building
```bash
git add build_app.py index.html
git commit -m "Phase N: description of change"
git push
# Railway auto-deploys on push
```

---

## 4. Backend Server — app.py

The server is a minimal Flask application. Its responsibilities are:

1. Serve `index.html` at the root route `/` with `Cache-Control: no-cache, must-revalidate`
2. Serve all static files (fonts, images, manuals) from the working directory with appropriate cache headers
3. Expose REST API for session save/load
4. Expose REST API for image upload/list/delete/serve
5. Handle the reset endpoint (wipes saved data)
6. Apply gzip compression via `flask-compress` to all responses

### Cache-Control Headers (added Phase 30 — March 27, 2026)
```python
# index.html — never cache
Cache-Control: no-cache, must-revalidate

# Static assets (.ttf, .js, .jpg, .jpeg, .png, .webp) — 7-day cache
Cache-Control: max-age=604800, public

# User-uploaded images — 7-day cache
Cache-Control: max-age=604800, public
```

This cache strategy was required to achieve PageSpeed 100 on mobile.

### Key Configuration
```python
STORAGE_BASE = os.environ.get("STORAGE_DIR", "/app/data")
DATA_FILE    = os.path.join(STORAGE_BASE, "menu_data.json")
BACKUP_DIR   = os.path.join(STORAGE_BASE, "backups")
IMAGES_DIR   = os.path.join(STORAGE_BASE, "user_images")
IS_PERSISTENT = STORAGE_BASE.startswith("/app/data") or 
                os.environ.get("RAILWAY_VOLUME_MOUNTED") == "true"
```

- If `/app/data` is not available (local dev), falls back to `./data`
- `IS_PERSISTENT` is a truthiness flag exposed in API responses so the frontend can warn users if running without persistent storage

### Schema Validation
```python
def validate_schema(data):
    if "version" in data and "elements" in data:
        return isinstance(data["elements"], list)
    required_keys = ["zoom", "scroll", "elements"]
    if all(k in data for k in required_keys):
        return isinstance(data["elements"], list)
    return False
```

The server rejects any POST that does not pass schema validation with a `400` error.

### Compression
```python
app.config["COMPRESS_MIN_SIZE"] = 0   # compress everything
app.config["COMPRESS_MIMETYPES"] = [
    "text/html", "text/css", "text/xml",
    "application/json", "application/javascript", "application/octet-stream",
    "font/ttf", "font/otf", "font/woff", "font/woff2",
    "image/svg+xml"
]
```

Gzip compression is applied to all asset types including fonts and JSON for maximum transfer performance.

---

## 5. API Endpoints

### GET /
Returns `index.html` with `Cache-Control: no-cache, must-revalidate`. Entry point for the application.

### GET /api/menu
Returns the current saved session JSON.

**Response (success):**
```json
{
  "version": "2.0",
  "elements": [...],
  "zoom": 1.0,
  "scroll": {"x": 0, "y": 0},
  "imageLibrary": [...],
  "status": {
    "is_persistent": true,
    "storage_base": "/app/data"
  }
}
```

**Response (no saved data):**
```json
{
  "elements": [],
  "zoom": 1,
  "scroll": {"x": 0, "y": 0},
  "info": "initial",
  "status": {...}
}
```

### POST /api/menu
Saves the current session to disk.

**Request body:** Full session JSON (must pass `validate_schema`)  
**Side effect:** Creates timestamped backup in `/app/data/backups/` before overwriting  
**Write method:** Atomic — writes to `.tmp` file then `os.replace()` to final path  

**Response (success):**
```json
{"status": "success", "backup": "menu_data_20260327_074500.json"}
```

### POST /api/menu/reset
Wipes `menu_data.json` (backs it up first to `backups/` with `_RESET_` prefix). Forces the app to load from embedded initial state on next page load.

### POST /api/upload-image
Accepts base64-encoded image data. Saves to `/app/data/user_images/`.

**Request body:**
```json
{
  "filename": "logo_upload.png",
  "data": "data:image/png;base64,iVBORw..."
}
```

**Response:**
```json
{"status": "ok", "filename": "logo_upload.png", "url": "/user-images/logo_upload.png"}
```

### GET /api/list-images
Returns list of all images in the user_images directory.

### DELETE /api/delete-image/\<filename\>
Removes a specific image from user_images.

### GET /user-images/\<filename\>
Serves a user-uploaded image file with `Cache-Control: max-age=604800, public`.

### GET /\<path:path\>
Catch-all static file server — serves fonts, manuals, and any other static asset. Font and image extensions receive `Cache-Control: max-age=604800, public`.

---

## 6. Storage Architecture

```
/app/data/                         ← Railway Volume mount
├── menu_data.json                 ← Current session state (atomic writes)
├── backups/
│   ├── menu_data_20260327_074500.json   ← Timestamped auto-backup before each save
│   ├── menu_data_RESET_20260327_080000.json  ← Backup taken before reset
│   └── ...
└── user_images/
    ├── logo_upload.png            ← User-uploaded images
    ├── header_art.jpg
    └── ...
```

### Durability Properties
- **Atomic writes**: `.tmp` file written fully, then `os.replace()` — no partial writes possible
- **Auto-backups**: Every successful save creates a timestamped backup copy
- **Reset safety**: Reset endpoint backs up data before deleting it
- **Fallback**: If Railway Volume unavailable, falls back to `./data` local directory (non-persistent across restarts)

### Frontend Backup
- `localStorage` key `menuEditorSession` is updated on every server save
- Acts as a last-resort recovery during temporary network outages
- Not suitable as primary persistence (cleared by browser on cache clear)

---

## 7. Frontend Architecture

### Application State Model
The app maintains a single global state object in JavaScript:

```javascript
state = {
  version: "2.0",
  elements: [],          // array of element objects
  zoom: 1.0,             // current canvas zoom level
  scroll: {x: 0, y: 0}, // canvas scroll offset
  imageLibrary: [],      // array of uploaded image metadata
  layoutLocked: true,    // global layout lock state
  selectedId: null,      // currently selected element id
  undoStack: [],         // array of state snapshots (max 30)
  isDirty: false         // unsaved changes flag
}
```

### Render Loop
- The app uses a DOM-based render model for editing
- `render()` function rebuilds all element DOM nodes from state on each update
- Elements are positioned using absolute CSS (`left`, `top`, `width`, `height`) inside a scaled canvas container
- Canvas zoom is applied via CSS `transform: scale(zoom)` on the container
- **Export uses a separate Canvas API rendering path** (NOT DOM capture) — see Section 11

### Key JavaScript Functions

| Function | Purpose |
|----------|---------|
| `render()` | Rebuilds all element DOM nodes from current state |
| `pushState()` | Takes an undo snapshot before any mutating operation |
| `undo()` | Pops last undo snapshot and restores state |
| `saveSession()` | POSTs state to `/api/menu` |
| `loadSession()` | GETs from `/api/menu` and replaces state |
| `exportPng()` | Triggers full Canvas API export pipeline |
| `addText()` | Creates new text element at viewport center |
| `addRect()` | Creates new rectangle element |
| `uploadImage()` | Reads file, POSTs to `/api/upload-image`, places on canvas |
| `selectElement(id)` | Sets `selectedId`, updates Selection Bar |
| `deleteElement(id)` | Removes element, pushes undo snapshot first |
| `duplicateElement(id)` | Deep-copies element with offset position |
| `toggleLayoutLock()` | Flips `layoutLocked`, updates UI |
| `showToast(msg, type)` | Displays branded notification (success/error/warning/info) |
| `showModal(opts)` | Displays branded confirmation dialog |
| `onTextFocus(id)` | Reads content from data model into contentEditable |
| `onTextBlur(id)` | Commits contentEditable content back to data model |
| `inject300DpiAndDownload()` | Injects pHYs DPI chunk and triggers PNG download (in export-utils.js) |

### contentEditable Text Editing
- Text elements use `contentEditable="true"` (string, not boolean) on the DOM element
- `onTextFocus`: reads from `state.elements[id].content` into the DOM element
- `onTextBlur`: writes `innerText` back to `state.elements[id].content` — commits edit
- A rogue `sync()` call was removed from `onTextBlur` in Phase 27-C to prevent unintended auto-saves during typing

---

## 8. Element Data Model

Every element on the canvas (text, image, shape) is stored as an object in `state.elements`. All elements share a base set of properties, with type-specific additions.

### Base Properties (All Element Types)
```json
{
  "id": "el_1710645000000_abc",
  "type": "text",
  "x": 245.5,
  "y": 180.0,
  "width": 420,
  "height": 60,
  "visible": true,
  "locked": false,
  "opacity": 100,
  "role": "content",
  "name": "main-title",
  "zIndex": 10
}
```

### Text Element Additional Properties
```json
{
  "content": "APPETIZERS",
  "fontFamily": "Century Gothic",
  "fontSize": 28,
  "fontWeight": "bold",
  "fontStyle": "normal",
  "textDecoration": "none",
  "color": "#ffffff",
  "textAlign": "center",
  "letterSpacing": 0.08,
  "lineHeight": 1.4,
  "textShadow": false
}
```

### Image Element Additional Properties
```json
{
  "src": "/user-images/logo_upload.png",
  "originalWidth": 800,
  "originalHeight": 600,
  "aspectRatio": 1.333
}
```

### Rectangle Element Additional Properties
```json
{
  "fillColor": "#95201d",
  "borderColor": "#c8a96a",
  "borderWidth": 2,
  "borderRadius": 8
}
```

---

## 9. Session Data Schema

The full session JSON saved to and loaded from the server:

```json
{
  "version": "2.0",
  "savedAt": "2026-03-27T07:24:01Z",
  "elements": [
    { ...element object... },
    { ...element object... }
  ],
  "zoom": 1.2,
  "scroll": {
    "x": 0,
    "y": 120
  },
  "imageLibrary": [
    {
      "filename": "logo.png",
      "url": "/user-images/logo.png",
      "thumbnail": "data:image/png;base64,..."
    }
  ]
}
```

### Schema Validation Rules (enforced by server)
- Must have `elements` field that is an array
- If `version` is present, `elements` must be present
- If `version` is absent, `zoom`, `scroll`, and `elements` must all be present
- Server returns `400` on validation failure

---

## 10. Asset Pipeline

### Background Images
| File | Purpose | Size | When Loaded |
|------|---------|------|------------|
| `menu-bg-preview.jpg` | Editing preview | ~114 KB | On app load (`fetchpriority="high"`) |
| `menu-bg.png` | Export master | ~7.2 MB | On export trigger only |

The preview JPG is generated from the master PNG using `create_preview.py`:
```bash
python create_preview.py
# Resizes menu-bg.png to ~1200px wide, saves as menu-bg-preview.jpg
```

### Fonts
All fonts are served as local TTF files from the repo root.

| File | Font Name | Weight | Style |
|------|-----------|--------|-------|
| `bernard-mt-condensed-regular.ttf` | Bernard MT Condensed | Regular | Normal |
| `century-gothic-regular.ttf` | Century Gothic | Regular | Normal |
| `century-gothic-bold.ttf` | Century Gothic | Bold | Normal |
| `century-gothic-bold-italic.ttf` | Century Gothic | Bold | Italic |

> ⚠️ `centurygothic.ttf` was a duplicate alias of `century-gothic-regular.ttf` and was **deleted on March 27, 2026** as part of PageSpeed optimization. Do not re-add it.

Fonts are declared with `@font-face` in the compiled CSS with `font-display: swap`. A font-load promise with 800ms fallback timeout runs before `initApp()` to prevent rendering hangs.

### User Images
- Uploaded via frontend → POSTed as base64 to `/api/upload-image`
- Stored at `/app/data/user_images/`
- Served from `/user-images/<filename>` with 7-day cache headers
- Listed via `/api/list-images` and displayed in the Asset Tray
- Auto-trim: transparent PNG borders are cropped client-side on upload before placing on canvas

---

## 11. Export Pipeline — 300 DPI PNG

> ⚠️ **IMPORTANT**: The export engine uses the **Canvas API exclusively**. `html2canvas` has been fully removed. The export pipeline renders elements programmatically onto an off-screen HTML5 Canvas at 3600×5400px, then calls `inject300DpiAndDownload()` from `export-utils.js`.

### Step-by-Step Export Flow

```
User clicks Export Pro PNG
  → pushState() for undo safety
  → showToast("Preparing export…", "info") — persistent toast
  → autoSave() — saves session to server
  → Load menu-bg.png (full resolution master) into Image object
  → Create off-screen Canvas at 3600 × 5400px
  → Draw menu-bg.png as background layer
  → For each element in ascending zIndex order:
      if image: draw at scaled coordinates
      if text:  set font, fillStyle, draw text (multi-line aware)
      if rect:  fillRect / strokeRect with corner radius
  → canvas.toBlob("image/png")
  → inject300DpiAndDownload(blob, "notyourmamaskitchen-menu.png")
    → parse PNG binary
    → inject pHYs chunk before IDAT (11811 × 11811 pixels/meter = 300 DPI)
    → reassemble PNG binary
    → trigger browser download
  → dismiss export toast
  → showToast("Export complete!", "success")
```

### Export Dimensions
- **Pixel dimensions**: 3600 × 5400 px (12 × 18 inches at 300 DPI)
- **Physical output**: 12 × 18 inch menu at print quality
- **DPI metadata**: 300 DPI (pHYs chunk: 11811 pixels/meter)
- **Color mode**: RGB
- **Format**: PNG (lossless)
- **Scale factor**: TARGET_W / BASE_W = 3600 / 908.44 ≈ 3.963×

### pHYs Chunk Injection
Browser-exported PNGs carry no DPI metadata by default. `inject300DpiAndDownload()` in `export-utils.js`:

```javascript
// Locates IDAT chunk position in PNG binary
// Inserts pHYs chunk before IDAT:
//   - Chunk length: 9 bytes
//   - Chunk type: "pHYs"
//   - X pixels/unit: 11811 (big-endian uint32)
//   - Y pixels/unit: 11811 (big-endian uint32)
//   - Unit: 1 (meter)
//   - CRC32 of chunk type + data
// Reassembles and triggers browser download
```

### export-utils.js Loading
`export-utils.js` is loaded in `index.html` with the `defer` attribute:
```html
<script src="export-utils.js" defer></script>
```
This is required for PageSpeed 100 — do not remove `defer`.

---

## 12. Undo System

### Stack Behavior
- `pushState()` is called before every mutating operation
- Each snapshot is a deep clone of the full `state.elements` array
- Stack maximum depth: **30 steps**
- When stack exceeds 30, oldest snapshot is discarded (FIFO)
- Keyboard: `Ctrl+Z` (Windows) / `⌘+Z` (Mac)
- Button: ↺ Undo Last Change in top header bar

### What Is Covered by Undo
- Text content edits (committed on blur)
- Element position changes (drag)
- Style changes (font, size, color, opacity, letter spacing, line height, bold/italic/underline)
- Add element (Text, Image, Rect)
- Delete element
- Visibility toggle
- Element lock toggle
- Shape property changes (fill, border, radius)
- Duplicate element

### What Is NOT Covered by Undo
- Reset to Original (full state wipe)
- Load Session (full state replacement from server)
- Export (read-only operation)
- Zoom level changes

---

## 13. Interaction Model — Layout Lock & Touch

### Layout Lock States

| State | Drag | Text Edit | Canvas Scroll | Zoom Buttons |
|-------|------|-----------|---------------|-------------|
| 🔒 Locked | Blocked | ✅ (double-click) | ✅ (drag background) | Hidden |
| 🔓 Unlocked | ✅ | ✅ (double-click) | Disabled | Visible (＋/－) |

- Layout Locked is the **default on every load** — intentional safety feature
- The lock state is stored in UI state but **not** persisted to session JSON (resets to Locked on reload)
- Locked elements (individual lock, LAYER tab) are never draggable regardless of global lock state

### Touch Event Handling
```
touchstart →
  if (touches.length > 1): suppress, cancel any active drag
  if (touches.length === 1 && layoutUnlocked && element hit):
    begin drag sequence

touchmove →
  if (touches.length > 1): cancel drag immediately
  if (drag active): update element position

touchend →
  commit drag position to state
  pushState() snapshot
```

**Multi-touch suppression rule**: If a second finger touches the screen while a drag is in progress, the drag is immediately cancelled and the element returns to its last committed position.

### Zoom Controls (Unlocked Mode Only)
- Floating `＋` / `－` buttons appear in top-right when Layout is Unlocked
- Zoom is stored in `state.zoom` and restored on Load Session

---

## 14. UI Component Inventory

### Top Header Bar
| Element | Behavior |
|---------|----------|
| ↺ RELOAD button | Confirms via modal, reloads page |
| 🔒/🔓 Lock button | Toggles `layoutLocked`. Updates button label and zoom button visibility. |
| ↺ Undo button | Calls `undo()`. Disabled state when stack empty. |
| 💾 Save button | Calls `saveSession()`. Shows success/failure toast. Color: `#1e8449` (contrast-safe). |

### FAB (Floating Action Button)
- `🛠️` button, fixed bottom-right. Opens/closes Tools Drawer.

### Tools Drawer
| Control | Behavior |
|---------|---------|
| ＋ Add Text | `addText()` — places text element at viewport center |
| 🖼️ Upload Image | Opens file input — accepts PNG/JPG/WEBP/GIF/SVG |
| ⬜ Add Rectangle | `addRect()` — places rect element |
| 💾 Save Session | `saveSession()` |
| 📂 Load Session | `loadSession()` — confirms via modal if dirty |
| 🔄 Reset | `resetToOriginal()` — confirms via modal (destructive) |
| ⬇️ Export Pro PNG | `exportPng()` — Canvas API, 300 DPI |
| 📖 Manual EN | Opens `manual-en.html` in new tab |
| 📖 Manual ES | Opens `manual-es.html` in new tab |
| Asset Tray | Grid of uploaded image thumbnails. Click to place. |
| Layers Panel | List of all elements. Click to select. Toggle visibility/lock. |

### Selection Bar (Floating Toolbar)
- Appears on element selection, floats near selected element
- Draggable via `⠿` handle (pointer capture)
- Horizontally scrollable on mobile
- Three tabs: LAYER / DESIGN / ARRANGE

### Modal & Toast Systems
- **Modal**: Branded dark overlay, Confirm (red) + Cancel buttons, Escape = Cancel
- **Toast**: Slide-in, types: success/error/warning/info. Export toast is persistent until export completes.

---

## 15. Font System

### Active Fonts (4 files)
| File | Font Name | Used for |
|------|-----------|----------|
| `century-gothic-regular.ttf` | Century Gothic Regular | Body text |
| `century-gothic-bold.ttf` | Century Gothic Bold | Headings |
| `century-gothic-bold-italic.ttf` | Century Gothic Bold Italic | Accents |
| `bernard-mt-condensed-regular.ttf` | Bernard MT Condensed | Display titles |

`centurygothic.ttf` was a duplicate and was **deleted March 27, 2026**. Do not re-add.

### Font Loading
```javascript
await Promise.race([
  Promise.all([
    document.fonts.load('1em century-gothic-regular'),
    document.fonts.load('1em century-gothic-bold'),
    document.fonts.load('1em century-gothic-bold-italic'),
    document.fonts.load('1em bernard-mt-condensed-regular'),
  ]),
  new Promise(resolve => setTimeout(resolve, 800)) // 800ms fallback
]);
initApp();
```

All fonts use `@font-face` with `font-display: swap` for non-blocking render.

---

## 16. Performance Architecture

### PageSpeed Score (March 27, 2026): 100 / 100 / 100 / 100 ✅

### Load Time Strategy
| Asset | Strategy | Rationale |
|-------|----------|-----------|
| `index.html` | `no-cache` + gzip | Always fresh; ~100KB → ~25KB transfer |
| `menu-bg-preview.jpg` | `fetchpriority="high"`, 7-day cache | Fast LCP; 114KB vs 7.2MB |
| `menu-bg.png` | Deferred — loaded only on export | 7.2MB must never block initial load |
| `export-utils.js` | `defer` attribute | Non-blocking; loaded after HTML parsed |
| Fonts | `@font-face` with `font-display: swap`, 7-day cache | Non-blocking render + browser caching |
| JSON API responses | flask-compress gzip | Minimizes session data transfer size |

### Key Optimizations Applied
- `defer` on `export-utils.js` script tag (Phase 30)
- `Cache-Control: max-age=604800` on all static assets (Phase 30)
- Duplicate font `centurygothic.ttf` deleted (Phase 30)
- Save button contrast raised to `#1e8449` for accessibility (Phase 30)
- No render-blocking scripts or stylesheets on critical path

---

## 17. Deployment — Railway

### Process
```
Procfile: web: python app.py
```

### Environment Variables
| Variable | Purpose | Default |
|----------|---------|---------|
| `PORT` | Port for server to bind | `5000` |
| `STORAGE_DIR` | Override storage path | `/app/data` |
| `RAILWAY_VOLUME_MOUNTED` | Set by Railway when volume is active | `"true"` |

### Auto-Deploy Trigger
Any push to the `main` branch triggers Railway to pull and redeploy.

### Volume Mount
Railway Volume is mounted at `/app/data`. Persists across all deployments and restarts.

### Backup Recovery
```bash
# SSH into Railway container or use Railway CLI
cp /app/data/backups/menu_data_20260327_074500.json /app/data/menu_data.json
```

---

## 18. Known Constraints & Edge Cases

### Browser Canvas Security (CORS)
- All assets must be served from the same origin for Canvas export to work
- User-uploaded images are served from `/user-images/` on same domain — intentional

### PNG DPI Metadata
- Browsers export PNGs with no DPI metadata (effectively 72 DPI)
- `inject300DpiAndDownload()` rewrites the PNG binary to insert the pHYs chunk

### Mobile Multi-Touch
- Second finger during drag cancels drag and returns element to last committed position

### contentEditable Browser Quirks
- Must use `contentEditable="true"` (string) — boolean `true` causes issues in some browsers
- `innerText` used (not `innerHTML`) to avoid XSS

### Undo After Load Session
- Load Session is a full state replacement and cannot be undone (undo stack is cleared)

---

## 19. Phase Commit Log

| Phase | Commit SHA | Key Change |
|-------|-----------|------------|
| Phase 27 | 0351b38 | Fix contentEditable boolean bug in render() |
| Phase 27-B | 03b1729 | Fix onTextFocus reads from data model |
| Phase 27-C | 92104ea | Remove rogue sync() from onTextBlur |
| Phase 27-D | f57db49 | Fix zoom restore on Load Session |
| Phase 27-E | 02dfe80 | Fix SyntaxError (raw newline in strings) |
| Phase 28 | b8d611a | Implement 300 DPI pHYs metadata injection for PNG export |
| Phase 28-B | 456a770 | Add PNG helper functions for 300 DPI support |
| Phase 29 | e4102ee | Final Polish & UX Hardening (9 fixes) |
| Phase 30 | d3fc068 | PageSpeed 100: defer JS, remove dup font, cache headers, contrast fix |
| Phase 2A | 6c030a5 | V2 schema migration + asset registry (direct index.html) |
| Phase 2B | 2fed811 | Asset-linked image placement via assetId |
| Phase 2C | bcaa8fa | User upload persisted to asset registry |
| Phase 2D | 75358d0 | Asset registry round-trip save/restore |
| Phase 3 | c64e8f0 | Multi-select shift+click, group move/delete/dup |
| Phase 4 | c7a235a | Keyboard shortcuts (Delete, Ctrl+D/A/Z, Arrow nudge) |
| Phase 5 | 6bc7af5 | Font size control + text block width wrapping |
| Phase 6 | eb37fab | 8-way alignment and distribution tools |
| Phase 7 | d3e0136 | Lasso drag-box multi-select (mouse + touch) |
| Phase 8 | 65ca724 | Export PNG text rendering fix |
| Phase 9 | fe2d5ce | Undo history integrity (group drag, memory cap) |
| Phase 10 | 4b0cb1d | Mobile lasso & touch multi-select |
| Phase 11 | c378d90 | Save/Load hardening (dirty state, auto-save, error UI) |
| Bug Batch 1 | 600009a | Asset merge fix, sync() guard, header dup noRender |
| Bug Batch 2 | da85954 | Arrow nudge else-if, textContent→innerText, export img guard |
| Bug Batch 3 | 9664b41 | deleteEl order, resetToOriginal localStorage, lasso scale |
| Bug Batch 4 | d4f71fb | addFromTray pushState, onload fallback, bgLayer fix, toolbar anim |
| Bug Batch 5 | e210f58 | innerText consistency, fitCanvasToScreen, openDrawer retry |
| Bug Batch 6 | 939a940 | Ctrl+Z text guard, export rounded stroke, addRect viewport pos |
| Bug Batch 7 | 6bc7fe4 | deleteEl noRender, addFromTray skipPush, fitCanvas zoom persistence |

---

## 20. Locked Decisions — Do Not Change

| # | Decision | Why Locked |
|---|----------|-----------|
| 1 | `build_app.py` is authoritative source | Direct edits to `index.html` are lost on next build |
| 2 | Doubled-brace escaping in f-strings | Python/JS brace conflict — removing this breaks the build |
| 3 | Preview/master split-asset strategy | Preview load is 60× faster than master; critical for mobile |
| 4 | Canvas API export (NOT html2canvas) | Deterministic, no DOM capture artifacts, no CORS issues |
| 5 | 300 DPI pHYs binary injection | Only reliable way to set PNG DPI metadata in browser exports |
| 6 | Railway Volume at `/app/data` | Persistent across deploys; backbone of cross-device sync |
| 7 | Atomic write (`.tmp` + `os.replace()`) | Prevents partial writes / data corruption |
| 8 | Layout Locked as default on load | Prevents mobile users from accidentally moving elements |
| 9 | Undo stack max 30 steps | Bounded memory; sufficient for real-world usage |
| 10 | `defer` on export-utils.js | Required for PageSpeed 100; do not remove |
| 11 | User images served from same origin | Cross-origin images cannot be drawn to Canvas without CORS error |
| 12 | `document.fonts.load()` awaited before export | Prevents garbled text in exported PNG |
| 13 | Modal/toast system (no native alerts) | Native prompts break mobile UX and look unprofessional |
| 14 | Multi-touch second-finger cancels drag | Prevents layout damage when pinch-zoom is attempted on element |
| 15 | `Cache-Control: no-cache` on index.html | Users must always get fresh app; static assets get 7-day cache |

---

*End of MASTER_TECHNICAL_SPEC.md — Updated March 28, 2026 (Phase 30 + Phases 2A–11 + Bug Fix Batches 1–8)*
