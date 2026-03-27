# MASTER_TECHNICAL_SPEC.md
# Dine In Menu Editor Pro V2 — Master Technical Specification
**Version**: V2 Phase 29 (Final Polish & UX Hardening)  
**Last Updated**: March 17, 2026  
**Repository**: [mariaisabeljuarezgomez/NOTYOURMAMASKITCHENFULL](https://github.com/mariaisabeljuarezgomez/NOTYOURMAMASKITCHENFULL)  
**Deployed on**: Railway  
**Prepared by**: MARIAS DIGITAL DESIGNS

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
- Must load fast on mobile (< 2 second LCP target)
- Must be safe for non-technical users (Layout Locked by default)
- Must produce print-quality output regardless of device used for editing
- Must survive browser cache clears via server-side persistence
- Must run entirely in-browser with zero client installation

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Generator | Python 3 (`build_app.py`) |
| Frontend | HTML5, CSS3, Vanilla JavaScript, Canvas API |
| Export engine | `html2canvas` (lazy-loaded) |
| Backend | Python 3, Flask, flask-compress |
| Persistence | Railway Volume (`/app/data/`) — JSON files |
| Image storage | Railway Volume (`/app/data/user_images/`) |
| CDN/Compression | flask-compress (gzip all assets) |
| Hosting | Railway (auto-deploy from GitHub push) |
| Fonts | Local TTF files served as static assets |

---

## 2. Repository File Map

```
NOTYOURMAMASKITCHENFULL/
│
├── build_app.py              ← AUTHORITATIVE SOURCE. Generates index.html.
├── index.html                ← COMPILED OUTPUT. Never edit directly.
├── app.py                    ← Flask server (routes, save/load/image APIs)
├── requirements.txt          ← Flask, flask-compress, gunicorn
├── Procfile                  ← Railway process: gunicorn app:app
│
├── menu-bg.png               ← Master background (7.2 MB, full res, export only)
├── menu-bg-preview.jpg       ← Preview background (compressed, editing only)
│
├── bernard-mt-condensed-regular.ttf
├── century-gothic-regular.ttf
├── century-gothic-bold.ttf
├── century-gothic-bold-italic.ttf
├── centurygothic.ttf         ← Alias copy of century-gothic-regular.ttf
│
├── manual-en.html            ← In-app English user manual (standalone HTML)
├── manual-es.html            ← In-app Spanish user manual (standalone HTML)
│
├── create_preview.py         ← Utility: generates menu-bg-preview.jpg from menu-bg.png
├── fix_braces.py             ← Utility: diagnostic for brace escaping issues in build_app.py
├── fix_coords.py             ← Utility: coordinate migration tool
├── read_example.py           ← Utility: session JSON reader example
├── raw_coords.json           ← Source coordinate data for element positioning
│
├── .gitignore
├── Images/                   ← Static image assets directory
│
├── USER_MANUAL_SOURCE.md     ← User-facing manual source (this project's docs)
├── MASTER_TECHNICAL_SPEC.md  ← This file
└── CONTINUITY_HANDOFF_CURRENT.md  ← AI assistant handoff and project context doc
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

1. Serve `index.html` at the root route `/`
2. Serve all static files (fonts, images, manuals) from the working directory
3. Expose REST API for session save/load
4. Expose REST API for image upload/list/delete/serve
5. Handle the reset endpoint (wipes saved data)
6. Apply gzip compression via `flask-compress` to all responses

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
Returns `index.html`. Entry point for the application.

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
{"status": "success", "backup": "menu_data_20260317_074500.json"}
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

**Response:**
```json
{
  "images": [
    {"filename": "logo.png", "url": "/user-images/logo.png"},
    ...
  ]
}
```

### DELETE /api/delete-image/\<filename\>
Removes a specific image from user_images.

### GET /user-images/\<filename\>
Serves a user-uploaded image file directly from disk.

### GET /\<path:path\>
Catch-all static file server — serves fonts, manuals, and any other static asset.

---

## 6. Storage Architecture

```
/app/data/                         ← Railway Volume mount
├── menu_data.json                 ← Current session state (atomic writes)
├── backups/
│   ├── menu_data_20260317_074500.json   ← Timestamped auto-backup before each save
│   ├── menu_data_RESET_20260317_080000.json  ← Backup taken before reset
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
- The app uses a DOM-based render model (not Canvas for editing)
- `render()` function rebuilds all element DOM nodes from state on each update
- Elements are positioned using absolute CSS (`left`, `top`, `width`, `height`) inside a scaled canvas container
- Canvas zoom is applied via CSS `transform: scale(zoom)` on the container
- Export uses a separate rendering path (`html2canvas`) that reads the same DOM

### Key JavaScript Functions

| Function | Purpose |
|----------|---------|
| `render()` | Rebuilds all element DOM nodes from current state |
| `pushState()` | Takes an undo snapshot before any mutating operation |
| `undo()` | Pops last undo snapshot and restores state |
| `saveSession()` | POSTs state to `/api/menu` |
| `loadSession()` | GETs from `/api/menu` and replaces state |
| `exportPng()` | Triggers full export pipeline |
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

### contentEditable Text Editing
- Text elements use `contentEditable="true"` on the DOM element
- `onTextFocus`: reads from `state.elements[id].content` into the DOM element
- `onTextBlur`: commits DOM element `innerText` back to `state.elements[id].content`
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

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier: `el_` + timestamp + random suffix |
| `type` | string | `"text"` / `"image"` / `"rect"` |
| `x` | number | Left position in canvas world coordinates (pixels) |
| `y` | number | Top position in canvas world coordinates (pixels) |
| `width` | number | Element width in canvas pixels |
| `height` | number | Element height in canvas pixels |
| `visible` | boolean | If false, hidden in editor and excluded from export |
| `locked` | boolean | If true, element cannot be selected or moved |
| `opacity` | number | 0–100 (percent). Applied as CSS opacity. |
| `role` | string | `"background"` / `"content"` / `"overlay"` |
| `name` | string | User-assigned label shown in Layers Panel |
| `zIndex` | number | Stacking order |

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
  "savedAt": "2026-03-17T07:24:01Z",
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
| `menu-bg-preview.jpg` | Editing preview | ~114 KB | On app load (immediate) |
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
| `centurygothic.ttf` | Century Gothic | Regular | Normal (alias) |

Fonts are declared with `@font-face` in the compiled CSS and are loaded as high-priority resources. A font-load fallback was added in Phase 26 to prevent `window.onload` from hanging if a font fails to load.

### User Images
- Uploaded via frontend → POSTed as base64 to `/api/upload-image`
- Stored at `/app/data/user_images/`
- Served from `/user-images/<filename>`
- Listed via `/api/list-images` and displayed in the Asset Tray
- Auto-trim: transparent PNG borders are cropped client-side on upload before placing on canvas

---

## 11. Export Pipeline — 300 DPI PNG

### Step-by-Step Export Flow

```
User clicks Export
  → pushState() for undo safety
  → showToast("Preparing export…", "info") — persistent toast
  → autoSave() — saves session to server
  → swap background: preview JPG → master PNG
  → await document.fonts.ready — ensures all fonts are rendered
  → html2canvas(canvas_container, options)
  → canvas.toBlob("image/png")
  → inject300DpiMetadata(pngBlob)
    → parse PNG binary
    → inject pHYs chunk (11811 × 11811 pixels/meter = 300 DPI)
    → reassemble PNG binary
  → trigger browser download: notyourmamaskitchen-menu.png
  → restore preview background
  → dismiss export toast
  → showToast("Export complete!", "success")
```

### Export Dimensions
- **Pixel dimensions**: 3600 × 5400 px (12 × 18 inches at 300 DPI)
- **Physical output**: 12 × 18 inch menu at print quality
- **DPI metadata**: 300 DPI (pHYs chunk: 11811 pixels/meter)
- **Color mode**: RGB
- **Format**: PNG (lossless)

### pHYs Chunk Injection (Phase 28)
Browser-exported PNGs carry no DPI metadata by default. The fix:

```javascript
function inject300DpiMetadata(pngBlob) {
  // Parse binary PNG
  // Locate IDAT chunk position
  // Insert pHYs chunk before IDAT:
  //   - Chunk length: 9 bytes
  //   - Chunk type: "pHYs"
  //   - X pixels/unit: 11811 (big-endian uint32)
  //   - Y pixels/unit: 11811 (big-endian uint32)
  //   - Unit: 1 (meter)
  //   - CRC32 of chunk type + data
  // Reassemble and return corrected Blob
}
```

This was the fix for the long-standing issue of visually-correct exports still reporting 72 DPI to printers and design software.

### html2canvas Options
```javascript
{
  scale: EXPORT_SCALE,          // computed to produce 3600px width
  useCORS: true,
  allowTaint: false,
  backgroundColor: null,
  logging: false,
  width: CANVAS_NATURAL_WIDTH,
  height: CANVAS_NATURAL_HEIGHT  // dynamic — calculated from actual element bounds
}
```

### Multi-Line Text in Export (Phase 23–24)
Multi-line text elements required special handling during export:
- Element height is calculated from actual line count × line height × font size
- `document.fonts.ready` is awaited before rendering to ensure correct font metrics
- Letter-spacing detection was standardized across edit and export paths

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
- Visibility toggle (👁️)
- Element lock toggle (🔒)
- Shape property changes (fill, border, radius)
- Duplicate element

### What Is NOT Covered by Undo
- Reset to Original (full state wipe)
- Load Session (full state replacement from server)
- Export (read-only operation)
- Zoom level changes

### Undo Snapshot Timing Fix (Phase 22)
A timing bug caused undo snapshots to be taken after text was committed rather than before. This was fixed by moving `pushState()` to be called in `onTextFocus` (when editing begins) rather than in `onTextBlur` (when editing ends).

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

**Multi-touch suppression rule**: If a second finger touches the screen while a drag is in progress, the drag is immediately cancelled and the element returns to its last committed position. This prevents accidental element displacement during pinch-zoom.

### Zoom Controls (Unlocked Mode Only)
- Floating `＋` / `－` buttons appear in top-right when Layout is Unlocked
- Zoom is stored in `state.zoom`
- Zoom is restored on Load Session (Phase 27-D fix — zoom was not being restored correctly)
- User-zoom persistence guard added in Phase 25 to prevent zoom state from being clobbered by async operations

### contentEditable Isolation (Phase 27)
A bug caused `contentEditable` to be set incorrectly (boolean `true` instead of string `"true"`) in the `render()` function. This broke text editing in certain browser contexts. Fixed in Phase 27.

### onTextFocus / onTextBlur (Phase 27-B, 27-C)
- `onTextFocus`: reads `state.elements[id].content` into the DOM node's `innerText` — ensures DOM matches data model at edit start
- `onTextBlur`: writes `innerText` back to `state.elements[id].content` — commits edit
- Rogue `sync()` call removed from `onTextBlur` in Phase 27-C — it was triggering unwanted auto-saves mid-edit

---

## 14. UI Component Inventory

### Top Header Bar
Fixed. Always visible. Z-index above canvas.

| Element | ID/Class | Behavior |
|---------|----------|---------|
| ↺ RELOAD button | `#btn-reload` | Confirms via modal, reloads page |
| 🔒/🔓 Lock button | `#btn-lock` | Toggles `layoutLocked`. Updates button label and zoom button visibility. |
| ↺ Undo button | `#btn-undo` | Calls `undo()`. Disabled state when stack empty. |
| 💾 Save button | `#btn-save` | Calls `saveSession()`. Shows success/failure toast. |

### FAB (Floating Action Button)
- `🛠️` button, fixed bottom-right
- Opens/closes Tools Drawer (slide-up panel)

### Tools Drawer
Slide-up panel, Z-index above canvas.

| Control | Behavior |
|---------|---------|
| ＋ Add Text | `addText()` — places text element at viewport center |
| 🖼️ Upload Image | Opens `<input type=file>` — accepts PNG/JPG/WEBP/GIF/SVG |
| ⬜ Add Rectangle | `addRect()` — places rect element |
| 💾 Save Session | `saveSession()` |
| 📂 Load Session | `loadSession()` — confirms via modal if dirty |
| 🔄 Reset | `resetToOriginal()` — confirms via modal (destructive) |
| ⬇️ Export Pro PNG | `exportPng()` |
| 📖 Manual EN | Opens `manual-en.html` in new tab |
| 📖 Manual ES | Opens `manual-es.html` in new tab |
| Asset Tray | Grid of uploaded image thumbnails. Click to place. |
| Layers Panel | List of all elements. Click to select. Toggle visibility/lock. |

### Selection Bar (Floating Toolbar)
- Appears on element selection
- Floats near selected element
- Draggable via `⠿` handle
- Horizontally scrollable on mobile (overflow-x: auto)
- Three tabs: LAYER / DESIGN / ARRANGE
- Disappears on deselect

### Modal System
- Branded dark overlay
- Branded dialog box
- Buttons: Confirm (red), Cancel (neutral)
- Focus trapped inside modal while open
- Keyboard: Escape = Cancel

### Toast System
- Slide-in notifications (bottom or top)
- Types: success (green), error (red), warning (orange), info (blue)
- Auto-dismiss after configurable timeout
- Export pre-toast is persistent (does not auto-dismiss) until export completes

---

## 15. Font System

### Font Loading
Fonts are declared via `@font-face` in compiled CSS with `font-display: swap`.

### Font Load Fallback (Phase 26)
A font-load fallback was added to `window.onload` to prevent the app from hanging if a font file fails to load:

```javascript
window.onload = async () => {
  try {
    await Promise.race([
      document.fonts.ready,
      new Promise(resolve => setTimeout(resolve, 3000)) // 3s timeout
    ]);
  } catch(e) {
    // continue anyway
  }
  initApp();
};
```

### Available Fonts in Font Selector
- Century Gothic (Regular, Bold, Bold Italic)
- Bernard MT Condensed

### Export Font Handling (Phase 24)
`document.fonts.ready` is awaited before `html2canvas` renders during export to ensure custom fonts are loaded and metrics are correct for all text elements.

---

## 16. Performance Architecture

### Load Time Strategy
| Asset | Strategy | Rationale |
|-------|----------|-----------|
| `index.html` | Served with gzip | Reduces ~100KB HTML to ~25KB transfer |
| `menu-bg-preview.jpg` | Served immediately, high-priority | Fast editing background; avoids large PNG on load |
| `menu-bg.png` | Deferred — loaded only on export | 7.2MB file must never block initial load |
| `html2canvas` | Lazy-loaded only on export trigger | Large library; no impact on editing performance |
| Fonts | `@font-face` with `font-display: swap` | Non-blocking; text renders immediately with fallback |
| JSON API responses | flask-compress gzip | Minimizes session data transfer size |

### Measured Performance Targets
- LCP (Largest Contentful Paint): < 2 seconds on mobile (4G)
- Time to interactive: < 3 seconds
- Export trigger to download: < 8 seconds (depends on element count)

---

## 17. Deployment — Railway

### Process
```
Procfile: web: gunicorn app:app
```

### Environment Variables
| Variable | Purpose | Default |
|----------|---------|---------|
| `PORT` | Port for gunicorn to bind | `5000` |
| `STORAGE_DIR` | Override storage path | `/app/data` |
| `RAILWAY_VOLUME_MOUNTED` | Set by Railway when volume is active | `"true"` |

### Auto-Deploy Trigger
Any push to the `main` branch triggers Railway to pull and redeploy. No manual deployment step required.

### Volume Mount
Railway Volume is mounted at `/app/data` automatically when configured in the Railway project settings. The volume persists across all deployments and restarts — this is the foundation of the cross-device sync feature.

### Backup Recovery
If `menu_data.json` becomes corrupted or needs rollback, timestamped backups are available in `/app/data/backups/`. To restore manually:
```bash
# SSH into Railway container or use Railway CLI
cp /app/data/backups/menu_data_20260317_074500.json /app/data/menu_data.json
```

---

## 18. Known Constraints & Edge Cases

### Browser Canvas Security (CORS / Tainted Canvas)
- All assets must be served from the same origin for `html2canvas` to capture them
- Cross-origin images will cause the canvas to be "tainted" and block export
- User-uploaded images are served from `/user-images/` on the same domain — this is intentional
- The master background `menu-bg.png` is served locally — this is intentional

### PNG DPI Metadata
- Browsers export PNGs with no DPI metadata by default (effectively 72 DPI to external software)
- The `inject300DpiMetadata()` function manually rewrites the PNG binary to insert the `pHYs` chunk
- Without this, the exported file would look correct visually but printers and InDesign would treat it as 72 DPI

### Mobile Multi-Touch
- A single-touch drag and a pinch-zoom use the same `touchstart`/`touchmove` events
- If not carefully guarded, a pinch attempt can accidentally move an element
- Fix: second finger detected → cancel drag immediately → return element to pre-drag position

### contentEditable and Browser Quirks
- `contentEditable="true"` behavior varies slightly across browsers
- Setting contentEditable as a boolean `true` (not string `"true"`) causes issues in some contexts — Phase 27 fixed this
- `innerText` is used (not `innerHTML`) to avoid XSS and formatting injection

### Undo After Load Session
- Load Session is a full state replacement and cannot be undone
- This is intentional — the undo stack is cleared after a Load Session

### Locked Layer Click-Through (Phase 16–17)
- Locked elements had a z-index "popping" bug where clicking near them would temporarily elevate them above unlocked elements
- Fixed by enforcing z-index discipline in the render function — locked/background elements never receive `z-index` elevation on hover or selection attempt

---

## 19. Phase Commit Log

| Phase | Commit SHA | Key Change |
|-------|-----------|------------|
| Initial V2 | (multiple) | Image elements, shape elements, Selection Bar with 3 tabs, Asset Tray, Layers Panel, Cloudinary integration |
| Hotfix | 7ab4bf1 | Font loading regressions, ReferenceError, initialization order |
| Fix | 0125549 | Resize scaling, layout lock decoupling, font cleanup |
| Fix | 30de113 | Final resize handle visibility (CSS restructuring, JS cleanup) |
| Fix | 01e2259 | Image wrapper refactor for resize handles |
| Fix | 15a5d31 | Image wrapper stability (naturalWidth, CSS styles, initial render hook) |
| Fix | b7c0a34 | startX/startY undefined; missing toggle handlers |
| Fix | 36d9984 | Image export distortion; initial zoom visibility; tray placement |
| Fix | be7d78d | Layer depth swapping; zoom repositioning; auto-trim transparent pixels |
| Phase 13 | 98771d2 | Server-side image persistence and library tray management |
| Phase 14 | 961a60 | Fix drawer clipping (removed hardcoded height) |
| Phase 15 | 1b9e161 | Fix stacking order and centering logic |
| Phase 16 | 458b05a | Prevent selection and z-index popping for locked/background layers |
| Phase 17 | 9e365d3 | Hardened locked layer interactions in list selection and CSS hover |
| Phase 18 | cb2f216 | Hardened resize, undo, duplication guards for locked/background layers |
| Phase 19 | a5995417 | Export resolution: 12×18in @ 300 DPI (3600×5400) |
| Phase 20 | ed023b7 | exportPng() with dynamic height, pre-export toast, background error handling |
| Phase 21 | 6774c9c | Persistent export toasts; double-click guard; text editing undo order fix |
| Phase 22 | 518c855 | Export try/catch hardening; undo snapshot timing fix; session load UI refresh |
| Phase 23 | fb41537 | Multi-line export support; pushState snapshot refactor; export try/catch |
| Phase 24 | d27a049 | Await fonts on export; multi-line dimensions; letter-spacing detection |
| Phase 25 | 65fa400 | Toast icon fix; user-zoom persistence guard |
| Phase 26 | 29efbdc | Font-load fallback; robust render error handling on window.onload |
| Phase 27 | 0351b38 | Fix contentEditable boolean bug in render() |
| Phase 27-B | 03b1729 | Fix onTextFocus reads from data model |
| Phase 27-C | 92104ea | Remove rogue sync() from onTextBlur |
| Phase 27-D | f57db49 | Fix zoom restore on Load Session |
| Phase 27-E | 02dfe80 | Fix SyntaxError (raw newline in strings) |
| Phase 28 | b8d611a | Implement 300 DPI pHYs metadata injection for PNG export |
| Phase 28-B | 456a770 | Add PNG helper functions for 300 DPI support |
| Phase 29 | e4102ee | Final Polish & UX Hardening (9 fixes) |

---

## 20. Locked Decisions — Do Not Change

The following architectural decisions are stable and hardened. Reopening any of them without overwhelming cause risks regression.

| # | Decision | Why Locked |
|---|----------|-----------|
| 1 | `build_app.py` is authoritative source | Direct edits to `index.html` are lost on next build |
| 2 | Doubled-brace escaping in f-strings | Python/JS brace conflict — removing this breaks the build |
| 3 | Preview/master split-asset strategy | Preview load is 60× faster than master; critical for mobile |
| 4 | `html2canvas` lazy-loaded on export only | Prevents large library from blocking edit-time performance |
| 5 | 300 DPI pHYs binary injection | Only reliable way to set PNG DPI metadata in browser exports |
| 6 | Railway Volume at `/app/data` | Persistent across deploys; backbone of cross-device sync |
| 7 | Atomic write (`.tmp` + `os.replace()`) | Prevents partial writes / data corruption |
| 8 | Layout Locked as default on load | Prevents mobile users from accidentally moving elements |
| 9 | Undo stack max 30 steps | Bounded memory; sufficient for real-world usage |
| 10 | Background as DOM `<img>` (not CSS) | CSS backgrounds cannot be captured reliably by html2canvas |
| 11 | User images served from same origin | Cross-origin images taint the canvas and block export |
| 12 | `document.fonts.ready` awaited on export | Prevents garbled text in exported PNG if fonts not yet loaded |
| 13 | Modal/toast system (no native alerts) | Native prompts break mobile UX and look unprofessional |
| 14 | Multi-touch second-finger cancels drag | Prevents layout damage when pinch-zoom is attempted on element |

---

*End of MASTER_TECHNICAL_SPEC.md — Phase 29*
