# MASTER HANDOFF — Not Your Mama's Kitchen Menu Editor

**Last Updated: April 12, 2026**

## Changelog — Audit Patch April 12, 2026
Updated based on confirmed three-agent source code audit. 14 fixes applied. Includes PR #9 features (Clear Credentials, AI Gallery 3-slot apply).
**Manual Hardening — Apply 16 surgical fixes to manual-en.html to reconcile docs with live code.**
**Lasso Tool Enhancement — Replaced anonymous touch listeners with named functions for proper event cleanup and memory leak prevention.**
**Lasso Tool Fix — Simplified 7-line background-check condition to 1-line guard. Removed ontouchstart from menu-container inline handler (touch handled by JS named listeners). Function is now clean and correctly limits lasso initiation to empty canvas space only.**
**Lasso Tool Fix — Moved mousedown handler from inline HTML bubble-phase to capture-phase JS listener inside window.onload. onCanvasMousedown now fires before stopPropagation() in attach(), making lasso initiation robust against element click interception.**
**Lasso Tool Fix — Restored robust background collision detection to the lasso initiation guard, and expanded it to allow lasso initiation from any locked element. Since locked elements cannot be dragged and often serve as full-canvas background overlays, dragging over them now correctly initiates the lasso rather than blocking it.**

---

## Section 1 — Project Overview

**App Name:** Not Your Mama's Kitchen Menu Editor (Menu Editor Pro V2)

**Stack:**
- Backend: Flask (app.py) running on Railway
- Database: PostgreSQL on Railway (no local filesystem)
- Frontend: index.html (single-page canvas editor), viewer.html, export-utils.js
- Build: build_app.py (regenerates index.html from components)

**Deployment:** Railway — https://web-production-3e17d.up.railway.app/

**Persistence Model:** PostgreSQL only — never localStorage, never local filesystem. All document state stored in `sessions` table as JSONB.

**Asset Storage:** Cloudinary for all images and videos. URLs only — no base64 stored in database. Base64 blocked at upload to prevent database bloat and 5MB payload failures.

---

## Section 2 — File Inventory

| File | Purpose |
|------|---------|
| `app.py` | Flask backend — all API routes, database operations, AI integrations |
| `index.html` | Complete frontend — canvas editor, sidebar panels, AI Studio, all JavaScript |
| `viewer.html` | Public-facing menu viewer — reads from same PostgreSQL data |
| `export-utils.js` | PNG export with CRC32 checksum — used by exportPng() |
| `build_app.py` | Build script — concatenates components into index.html |
| `create_preview.py` | Thumbnail generator utility |
| `fix_braces.py` | JSON brace fixing utility |
| `fix_coords.py` | Coordinate normalization utility |
| `read_example.py` | Example data reader |
| `raw_coords.json` | Sample coordinate data |
| `requirements.txt` | Python dependencies |
| `Procfile` | Railway deployment config |
| `manual-en.html` | English user manual |
| `manual-es.html` | Spanish user manual |
| `USER_MANUAL_SOURCE.md` | User manual source for agents |
| `bernard-mt-condensed-regular.ttf` | Font file |
| `century-gothic-bold-italic.ttf` | Font file |
| `century-gothic-bold.ttf` | Font file |
| `century-gothic-regular.ttf` | Font file |
| `menu-bg.png` | Default background image |
| `menu-bg-preview.jpg` | Preview thumbnail |
| `Images/` | Static image directory (deprecated — use Cloudinary) |
| `MANUAL/` | Generated manual files |
| `.agents/` | Agent rules and workflows |

---

## Section 3 — Database Schema

### Table: sessions
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,       -- 'main' for live, 'backup' for auto-backup
    canvas_json JSONB,        -- Full docV2 document
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Records:**
- `id='main'` — Primary document, loaded on page start
- `id='backup'` — Rolling auto-backup, overwritten every 5 minutes if dirty

### Table: video_history
```sql
CREATE TABLE video_history (
    id SERIAL PRIMARY KEY,
    slot TEXT NOT NULL,       -- 'hero', 'left', or 'right'
    url TEXT NOT NULL,        -- Cloudinary URL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Table: image_history
```sql
CREATE TABLE image_history (
    id SERIAL PRIMARY KEY,
    name TEXT,
    url TEXT NOT NULL,        -- Cloudinary URL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### docV2 JSON Structure
```javascript
{
    version: 2,
    elements: [ ... ],       // Canvas elements (text, image, rect, circle, star, line)
    assets: [ ... ],         // Registered image assets
    aiCredentials: {         // Stored in DB, loaded on page start
        cloudName: "",
        cloudKey: "",
        cloudSecret: "",
        klingKey: "",
        klingSecret: "",
        stabilityKey: ""
    },
    settings: {
        layoutLocked: false,
        viewer: {
            heroVideoUrl: "",
            sidePanelLeft: {},
            sidePanelRight: {}
        }
    },
    editorState: { ... },
    heroVideoUrl: ""
}
```

**init_db() Behavior:** Fatal on failure — app crashes loudly if PostgreSQL unavailable. No silent fallback.

---

## Section 4 — Backend Routes (app.py)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Serves index.html |
| GET | `/viewer` | Serves viewer.html |
| GET | `/manual-en` | Serves manual-en.html |
| GET | `/manual-es` | Serves manual-es.html |
| GET | `/api/menu` | Loads canvas_json where id='main' |
| POST | `/api/menu` | Saves full docV2 to canvas_json where id='main', validates schema |
| GET | `/api/backup` | Loads canvas_json where id='backup' |
| POST | `/api/backup" | Saves rolling backup to canvas_json where id='backup', validates schema |
| POST | `/api/upload-image" | Uploads base64 image to Cloudinary, returns secure_url |
| POST | `/api/ai/cloudinary-upload" | Uploads AI-generated base64 to Cloudinary |
| POST | `/api/ai/generate-image" | Generates image via Stability AI or Google Imagen |
| POST | `/api/ai/generate-kling-image" | Generates image via Kling AI |
| POST | `/api/ai/generate-video" | Generates video via Kling AI |
| GET | `/api/ai/poll-kling-video/<task_id>" | Polls Kling for video completion |
| POST | `/api/ai/enhance-prompt" | Appends food photography modifiers to prompt |
| POST | `/api/ai/test-cloudinary" | Validates Cloudinary credentials |
| GET | `/api/video-history" | Returns all video_history records |
| POST | `/api/video-history" | Saves video URL to history (deduped) |
| GET | `/api/image-history" | Returns all image_history records |
| DELETE | `/api/image-history/<id>" | Deletes image from history |
| POST | `/api/save-video-history" | Legacy alias for video-history POST |
| GET | `/api/list-images" | Lists /Images/ directory files (deprecated) |

---

## Section 5 — Frontend Architecture (index.html)

### State Management
- **docV2** — Single source of truth for all canvas state. Loaded from PostgreSQL on page start, saved on user action or auto-backup.
- **save()** — POSTs entire docV2 to /api/menu. Validates payload < 5MB. Shows toast on success/failure. Blocks save if base64 present in background elements.
- **load()** — GETs from /api/menu, parses JSON, merges into docV2 via _mergeLoadedDoc(), calls render() and renderAssetPanel().

### Undo System
- **pushState()** — Pushes JSON.stringify(docV2.elements) to historyStack. Limit: 50 entries (slice(-49) + 1 new).
- **undo()** — Pops from historyStack, restores to docV2.elements, calls render().
- **redoStack** — Cleared on any new pushState().

### Dirty State
- **markDirty()** — Sets btn.dataset.dirty='true', changes button to red with "💾 Save*" text. Called after any element change.
- **markClean()** — Removes dirty flag, resets button to "Save". Called after successful save().

### Auto-Backup
- **startAutoBackup()** — setInterval every 5 minutes (300,000ms). Only fires if btn.dataset.dirty exists. POSTs to /api/backup. Shows 🔄 toast on success, silent fail on error.
- **restoreFromBackup()** — showConfirmModal -> GET /api/backup -> restores elements and assets -> render().

### Rendering Pipeline
- **render()** — Clears canvas, iterates docV2.elements, draws each by type (text/image/rect/circle/star/line), applies z-index order.
- **renderBackground()** — Renders background element if present. Injects img with pointer-events:none.
- **fitCanvasToScreen()** — Calculates zoom to fit canvas in viewport. Called on load and resize.
- **renderAssetPanel()** — Builds asset grid from docV2.assets, shows in ASSETS tab.
- **renderLayersPanel()** — Lists all elements by z-index in LAYERS tab.

### 30-Second Sync System
A setInterval fires every 30,000ms (30 seconds) and calls sync(). This is a UI/state synchronization call — it is NOT a save operation and does NOT write to the database. It is separate from the 5-minute auto-backup. The sync() function has approximately 32 call sites throughout the codebase. Do not confuse this interval with the auto-backup timer.

### Help Popout System
maybeShowHelpPopout() — Auto-triggers on new sessions for first-time guidance. Renders a bottom-center floating popout (.help-popout) with a title, description text, a primary CTA button, and a dismiss X. The popout animates in with a cubic-bezier spring transition. Once dismissed, it does not reappear for that session. Called at line 4912 during editor initialization.

### Pinch-vs-Drag Suppression (Mobile)
At line 4454, the editor implements logic to distinguish between a two-finger pinch gesture (zoom intent) and a single-finger drag (pan/move intent) on touch devices. This prevents accidental element drags during pinch-to-zoom. Part of the broader mobile UX hardening layer.

### Auto-Backup Fallback
On backup restore, the editor first attempts to read menuBackup from localStorage (line 4873) as a fallback before fetching from /api/backup. This provides an additional recovery layer if the server backup is unavailable.

---

## Section 6 — Left Sidebar Tabs

### ADD Tab
| Button | Action |
|--------|--------|
| Add Text | addText() → pushes text element to elements[] |
| Add Rect | addRect() → pushes rect element |
| Add Circle | addCircle() → pushes circle element |
| Add Star | addStar() → pushes star element |
| Add Line | addLine() → pushes line element |
| Upload Img | triggers file picker for in-img-assets (multi-file) |
| Replace Background | promptReplaceBackground() → showConfirmModal() → user confirms → clicks in-bg → importBackground() |
| Export Pro PNG | exportPng() → calls export-utils.js |
| Load Session | load() → reloads from /api/menu |
| Restore Backup | restoreFromBackup() → loads from /api/backup |

### ASSETS Tab
- Displays uploaded image assets from docV2.assets[]
- "Upload Images" button triggers file picker with `multiple` attribute
- importMultipleImgs() loops through files, uploads to Cloudinary, adds to assets[], calls save()
- Each asset has delete button calling deleteAssetFromServer()

### LAYERS Tab
- Lists all elements by z-index
- Each item shows: visibility toggle, lock toggle, element type icon, element name
- Click to select, drag to reorder (z-index)

### Ruler & Draggable Canvas Guide System
The editor renders a horizontal ruler (ruler-h) across the top and a vertical ruler (ruler-v) on the left. Users can click and drag from either ruler onto the canvas to place draggable guide lines. Guides are rendered as .canvas-guide-h (horizontal) and .canvas-guide-v (vertical) elements with a cyan glow (rgba(0,255,230,0.55)). Guides can be repositioned by dragging. Hovering a guide reveals a delete button (✕) that removes it. Rulers are hidden on mobile (max-width: 900px). This system is entirely CSS + JS — no external library.

### Right-Click Context Menu
A custom right-click context menu is implemented at line 6669. When a user right-clicks an image element on the canvas, the menu offers shortcuts including "Use as Kling Reference" and "Use as Video Reference." These populate the reference image inputs in the AI Studio panel directly from the canvas selection, without requiring a separate upload.

### Text Format Bar
A floating Text Format Bar (text-format-bar) appears above the canvas whenever a text element is selected. It contains: Bold, Italic, Underline, Strikethrough, text alignment (Left/Center/Right/Justify), text transform (Caps/Lowercase), font family selector, font size input with ± controls, line height, letter spacing, and a color picker with live preview swatch. The bar is fixed-position at top: 60px, spanning left: 220px to right: 260px. It is hidden (opacity: 0.35, pointer-events: none) when no text is selected and becomes fully active (opacity: 1) when a text element is active.


### AI GALLERY Tab (4th tab)
- **Generated Images Section:** Reads from docV2.assets filtering for asset_ai_ prefixed IDs or AI in name. Shows delete button (✕) on each. Click adds to canvas via addFromAsset().
- **Generated Videos Section:** Reads from video_history table. Shows video preview, "🎬 Hero", "⬅️ Left", and "➡️ Right" buttons to apply to respective slots.

---

## Section 7 — Right Panel

### Viewer Settings Tab
| Slot | Field | Purpose |
|------|-------|---------|
| Hero Video | hero-video-url-input | URL for main video display |
| Left Panel | side-panel-left-url | URL for left sidebar video |
| Right Panel | side-panel-right-url | URL for right sidebar video |

Each slot has a "Set as Hero" / "Set as Left" / "Set as Right" button when video is generated in AI Studio.

### AI Studio Tab
- **Image Generation:** Stability AI, Google Imagen, Kling AI options
- **Video Generation:** Kling video with quality/aspect controls
- **Enhance Prompt:** Appends food photography modifiers
- **Save to Assets:** Saves generated image to docV2.assets[] and persists to DB
- **Upload to Cloudinary:** For videos, makes URL permanent in video_history

### Kling Prompt Enhancement
- **Enhance Prompt:** The AI Studio includes an "Enhance Prompt" button for both image and video generation panels. It calls /api/ai/enhance-prompt and rewrites the user's raw prompt into a more detailed, cinematic AI-optimized version. The enhanced text is injected back into the prompt textarea. Confirmed at line 5420.


### Credentials Accordion
- Cloudinary: cloudName, cloudKey, cloudSecret
- Kling: klingKey, klingSecret
- Stability: stabilityKey
- All stored in docV2.aiCredentials, persisted to PostgreSQL

---

## Section 8 — AI Credentials System

**Storage Location:** docV2.aiCredentials (JSON object in database)

**On Page Load:**
- restoreAiCredentials(doc) reads from docV2 and populates input fields
- Conditionally enables/disables AI generate buttons based on which credentials exist

**On Save:**
- saveAiCredentials() reads input fields, applies .trim(), writes to docV2.aiCredentials, calls save()
- Enables buttons: ai-img-btn (if stabilityKey), kling-img-btn + ai-vid-btn (if klingKey AND klingSecret)

**Credential Field Names (exact, camelCase):**
- cloudName
- cloudKey
- cloudSecret
- klingKey
- klingSecret
- stabilityKey

**Reading in Generators:**
- generateAiVideo() reads from docV2.aiCredentials directly
- pollKlingStatus() reads from docV2.aiCredentials directly
- Does NOT read from DOM — ensures credentials persist across accordion close/open

**Auto-validation & Clearing:**
- Auto-validate on load: After restoreAiCredentials(), if Cloudinary creds are present, silently tests via /api/ai/test-cloudinary. Shows green toast on success, warning toast on failure.
- clearAiCredentials(): Wipes docV2.aiCredentials to empty strings, clears all input fields, calls save(), disables AI buttons. Requires confirmation modal before executing.

---

## Section 9 — Image & Asset Pipeline

### Standard Upload Flow
1. User selects file from file picker
2. FileReader reads as base64
3. POST to /api/upload-image with base64 and credentials
4. Cloudinary returns secure_url
5. URL stored in docV2.assets[] with originalUrl
6. save() called to persist to PostgreSQL
7. renderAssetPanel() called to update UI

### AI Image Flow
1. AI generates image (Stability/Kling/Imagen)
2. POST to /api/ai/cloudinary-upload with base64
3. Cloudinary returns secure_url
4. URL added to docV2.assets[] AND image_history table
5. save() called
6. Shows in AI Gallery via loadAiGallery()

### Asset Deduplication
- loadUserImages() builds Map by asset ID
- Filters duplicates before adding to docV2.assets
- Prevents runaway accumulation on page reload

### addFromTray()
- Places asset on canvas using stored URL (not base64)
- Sets assetId to link element to asset registry

### placeAiImageOnCanvas()
- Links canvas element to asset registry via assetId

---

## Section 10 — Background System

**Background Element:** Regular element in docV2.elements[] with:
- type: 'image'
- layerRole: 'background'
- zIndex: 0
- locked: true
- isSystemBackground: true

**Rendering:**
- #bg-layer container has pointer-events:none in CSS
- renderBackground() injects img with pointer-events:none (ensures clicks pass through to canvas)

**Replacement Flow:**
1. User clicks "Replace Background" in ADD tab
2. promptReplaceBackground() shows confirmation modal
3. User confirms → in-bg.click() triggers file picker
4. importBackground(input) reads file, uploads to Cloudinary
5. setAsBackground(url) updates element src and properties

**Remove Background:**
- removeBackground(e) calls pushState() first (undoable)
- Filters elements where layerRole !== 'background' AND !isSystemBackground
- removeBackground(e) — Confirmed separate function from Replace Background. Deletes all elements where layerRole === 'background' or isSystemBackground === true. Does not import a new background — it fully clears the background layer. Triggers save() and shows a toast confirmation. UI button is located in the Layers panel context.
- Clears #bg-layer.innerHTML, calls render() and save()

---

## Section 11 — Video System

### Three Slots
- Hero, Left, Right — stored in docV2.settings.viewer

### applyVideoToSlot(slot, url)
- Takes explicit URL parameter (not global state)
- Updates appropriate field: hero-video-url-input, side-panel-left-url, or side-panel-right-url
- Calls saveVideoHistory(slot, url) → POST to /api/video-history
- Shows toast confirming which slot was updated

### generateAiVideo()
- Calls Kling API with credentials from docV2.aiCredentials
- Polls via /api/poll-kling-video/<task_id> with interval
- On completion: saves to video_history table, shows in AI Gallery

### pollKlingStatus()
- Reads credentials from docV2.aiCredentials directly
- Intervals cleared on beforeunload to prevent memory leaks

### Video History Dedup
- save_video_history() checks only most recent record per slot
- Prevents duplicate consecutive saves of same URL

### Video Slot History System
Each slot (Hero, Left, Right) maintains a history of applied videos via saveVideoHistory(slot, url), which POSTs to /api/video-history. History is displayed in dedicated DOM containers: ai-vid-history-hero, ai-vid-history-left, ai-vid-history-right. Users can re-apply previously generated videos from these history panels without regenerating.

### Kling Generation Costs
Kling AI generation costs are variable by model. Newer models (Kling v2.5 Turbo, v2.6, v3, v3-Omni, Video-O1) carry different point costs than legacy models (v1, v1.5, v1.6). Cost estimate is displayed to the user in the kling-cost-estimate div before generation. Do not document a flat point value — it changes per model selection.

### enhance_prompt()
- Checks if "professional food photography" (image) or "cinematic food video" (video) already in prompt
- Only appends modifiers if not already present (no double-append)

---

## Section 12 — UI Theme

**Premium Glossy Black** — CSS block appended at end of <style> tag in index.html (line ~7000).

**Visual Elements:**
- Deep black gradients (#111 to #080808) on header and sidebars
- Gold accent borders (#c8a96a) on active tabs, buttons, inputs
- Gold resize handle dots (radial gradient #f0d090 to #c8a96a)
- Gold-tinted scrollbars (gradient #3a3020 to #2a2215)
- Frosted glass toast notifications with gold left border
- Modal overlays with backdrop-filter: blur(8px)

**Scope:** Purely visual. Does not modify layout, z-index, or JavaScript behavior.

---

## Section 13 — Known TODOs / Open Items

| Item | Status |
|------|--------|
| **Kling Video Slots** | applyVideoToSlot('left', url) and applyVideoToSlot('right', url) are fully functional. They write the Cloudinary URL directly to side-panel-left-url and side-panel-right-url inputs and call saveVideoHistory(slot, url) and saveGlobalSettings(). All three slots (Hero, Left, Right) are operational. |
| build_app.py sync | ⚠️ May need verification after index.html changes |

---

## Section 14 — Agent Rules

### Before Writing Any Code
1. Read MASTER_HANDOFF.md (this file) — direct file read, not code search
2. Read the live target file from GitHub — direct file read, not code search
3. Compare what live code does vs what MASTER_HANDOFF requires
4. If task contradicts MASTER_HANDOFF — STOP and write conflict clearly

### What You May NOT Do
- NEVER use localStorage for persistence — PostgreSQL only
- NEVER save base64 to database assets array — use Cloudinary URLs
- NEVER guess function names or variable names — always verify in source
- NEVER skip validate_schema() on /api/menu or /api/backup POST routes

### What You MUST Do
- Run build_app.py after any structural index.html change (if applicable)
- Close DB connections in finally blocks (connection leak prevention)
- Check if build_app.py needs same change when editing index.html

### After Any Rule Change
- Update .agents/rules/rules.md to match this section
- Keep both files in sync

---

## Section 15 — Keyboard Shortcuts

- **Arrow keys** — Nudge selected element 2px in any direction.
- **Shift + Arrow keys** — Nudge selected element 10px in any direction (confirmed at line 4936). Both nudge modes call nudge(dx, dy) and push undo state.
- **Ctrl+Y** — Redo. Calls redo(). Pops the top state from redoStack, pushes current state back to historyStack, re-renders canvas, and shows "Action Redone" toast. Note: There is no visible redo button in the UI — redo is keyboard-only via Ctrl+Y.

**END OF MASTER HANDOFF**
