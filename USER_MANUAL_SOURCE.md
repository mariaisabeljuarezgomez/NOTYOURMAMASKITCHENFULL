# USER MANUAL — Not Your Mama's Kitchen Menu Editor

**Last Updated: April 12, 2026**

---

## 1. Product Overview

**Product Name:** Not Your Mama's Kitchen Menu Editor (Menu Editor Pro V2)

**Type:** Browser-based professional restaurant menu layout editor

**Live URL:** https://web-production-3e17d.up.railway.app/

**Deployment Platform:** Railway (Python/Flask backend, PostgreSQL database)

---

## 2. Getting Started

### Accessing the Editor
Navigate to the live URL. The menu canvas loads automatically from the server.

### Layout Overview
- **Top Header:** Title, save button, layout lock toggle
- **Left Sidebar:** ADD, ASSETS, LAYERS, AI GALLERY tabs
- **Center Canvas:** Editable menu workspace
- **Right Panel:** Viewer settings (video slots), AI Studio

---

## 3. Left Sidebar — Tab Reference

### ADD Tab
Create elements on the canvas:

| Button | Action |
|--------|--------|
| T (Add Text) | Adds editable text element |
| ⬜ (Add Rect) | Adds rectangle shape |
| ⭕ (Add Circle) | Adds circle shape |
| ⭐ (Add Star) | Adds star shape |
| ╱ (Add Line) | Adds line/shape |
| 📷 (Upload Img) | Opens file picker for images (select multiple files) |
| 🖼️ (Replace Background) | ⚠️ Shows confirmation modal first, then opens file picker |

**File Section:**
- ⬇️ Export Pro PNG — Exports high-resolution PNG with print metadata
- 📂 Load Session — Reloads from server
- 🔄 Restore Backup — Loads from auto-backup (see Auto-Backup section)

### ASSETS Tab
- Displays all uploaded image assets
- "Upload Images" button — select multiple files at once
- Click any asset to place it on canvas
- ✕ button on each asset to delete

### LAYERS Tab
- Lists all canvas elements by z-order
- Click to select
- Toggle visibility (eye icon)
- Toggle lock (lock icon)
- Drag to reorder

### AI GALLERY Tab (4th Tab)
- **Generated Images:** Shows AI-created images from AI Studio. Click to add to canvas. ✕ to delete.
- **Generated Videos:** Shows AI-created videos. 🎬 Hero button applies to Hero slot. 📋 copies URL.

---

## 4. Right Panel — Viewer Settings

### Video Slots
Three video slots: Hero, Left, Right

Each slot has:
- Text input for video URL (.mp4 or .webm)
- Clear button (✕)
- Set as slot button (in AI Studio)

### AI Studio
Access AI generation tools:

**Image Generation:**
- Select model: Stability AI, Google Imagen, or Kling AI
- Enter prompt
- Click Generate Image
- Click "Save to Assets" to save to gallery

**Video Generation:**
- Select Kling model and quality
- Enter prompt
- Click Generate Video
- After generation, click "Upload to Cloudinary" for permanent URL

**Enhance Prompt:**
- Click to add professional food photography modifiers to your prompt

---

## 5. AI Credentials

To use AI features, enter your API credentials in the AI Studio Credentials accordion:

| Service | Fields |
|---------|--------|
| Cloudinary | Cloud Name, API Key, API Secret |
| Kling AI | API Key, API Secret |
| Stability AI | API Key |

**How to Save:**
1. Enter credentials in the fields
2. Click "Save Credentials" button
3. Credentials persist in the database across sessions

**Important:** Cloudinary credentials are required to save images and videos permanently. Without them, uploads will fail with an error message.

---

## 6. Canvas Interactions

### Selecting Elements
- Click element to select
- Selection bar appears with tools
- Click empty canvas area to deselect

### Editing Text
- Double-click text element to edit
- Use text format bar for font, size, color, alignment

### Moving & Resizing
- Drag element to move
- Drag corner handles to resize
- Hold Shift for proportional resize

### Alignment Tools
- Use align bar to align to left/center/right/top/middle/bottom
- Use distribute bar to space elements evenly

### Undo / Redo
- Ctrl+Z for undo
- Ctrl+Y for redo
- 50 undo steps available

---

## 7. Save & Load

### Manual Save
- Click "💾 Save" button in header
- Button turns red with asterisk (💾 Save*) when there are unsaved changes
- Click saves to server (PostgreSQL database)

### Auto-Backup
- System automatically saves a backup every 5 minutes if you have made changes
- Shows "🔄 Auto-backup saved" toast when triggered
- Backup is stored separately from main document

### Restore Backup
- Click "🔄 Restore Backup" button in ADD tab
- Confirmation modal appears
- Confirm to replace current canvas with backup

### Load Session
- Click "📂 Load Session" to reload from server
- Useful if you want to discard changes and start fresh

---

## 8. Background Management

### Replace Background
1. Click "🖼️ Replace Background" button in ADD tab
2. ⚠️ Confirmation modal appears: "Replace Background? This will permanently replace your current background. Make sure you have saved a backup first."
3. Click "Yes, Replace It" to proceed, or "Cancel" to abort
4. File picker opens — select new background image
5. Image uploads to Cloudinary and becomes new background

### Remove Background
- Click 🗑️ button on background layer in LAYERS tab
- Background is removed (undoable)

---

## 9. Export

### Export Pro PNG
- Click "⬇️ Export Pro PNG" in ADD tab
- Generates 300 DPI print-ready PNG with pHYs metadata
- Downloads automatically

---

## 10. Premium UI Theme

The editor features a premium glossy black theme with gold accents:

- Deep black gradients on header and sidebars
- Gold accent borders on active elements
- Gold resize handle dots
- Gold-tinted scrollbars
- Frosted glass toast notifications

This is purely visual — all functionality works the same regardless of theme.

---

## 11. Troubleshooting

### Images Not Loading
- Ensure Cloudinary credentials are saved in AI Studio → Credentials
- Images without credentials are stored locally and may be lost on redeployment

### Can't Upload Multiple Images
- Use the "Upload Images" button in ASSETS tab
- The file picker supports selecting multiple files (click and hold to select more than one)

### Background Replacement Blocked
- Make sure to click "Yes, Replace It" in the confirmation modal first

### Video Apply Buttons Limited
- Currently only "🎬 Hero" button works in AI Gallery
- Left and Right video apply buttons are coming soon

### Save Fails
- If you see "Payload too large" error, you may have base64 images in background
- Upload background images to Cloudinary first before using as background

---

## 12. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+S | Manual save |
| Delete | Delete selected element |
| Ctrl+A | Select all (when no element focused) |

---

**END OF USER MANUAL**