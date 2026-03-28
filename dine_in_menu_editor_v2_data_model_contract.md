# Dine In Menu Editor Pro — V2 Data Model Contract

## Purpose
This document defines the official Version 2 data model contract for the layered editor upgrade.

It exists to prevent ad hoc implementation and to ensure the editor evolves from a text-over-background system into a scalable layered document editor with stable save/load, export, undo, and future upload support.

Antigravity should treat this file as the authoritative schema/design baseline for Phase 2A and future layered-editor work unless explicitly revised.

> **Implementation Status (March 28, 2026):** Phase 2A through Phase 11 are **fully implemented** in `index.html`. All schemas below reflect the live implementation. `build_app.py` is frozen at Phase 30 and does NOT reflect these changes yet.

## Goals
- Preserve accepted production-safe behavior.
- Support a true layered document model.
- Separate reusable assets from placed elements.
- Preserve deterministic high-resolution export.
- Support future Cloudinary preview delivery without changing export source of truth.
- Keep migration from the current text-only system manageable.

## Non-Negotiables
Do NOT break:
- Save Session / Load Session
- Export Pro PNG
- 12-inch 300 DPI export baseline
- branded modal/toast UI
- manual system
- draggable desktop toolbar
- lock-first mobile behavior
- floating + / - zoom controls while unlocked
- Undo Last Change
- Reset to Original as separate action

Export rules:
- Export must remain deterministic and production-safe.
- Export must continue to render at 12 inches, 300 DPI.
- Export must use original-resolution image assets, never preview assets.
- Do NOT revert to screenshot/html2canvas export.

## High-Level Model
Version 2 uses:
- one document
- one asset registry
- one elements array
- versioned schema
- explicit separation between editor preview sources and export/original sources

## Top-Level Document Shape
```json
{
  "version": "2.0.0",
  "documentId": "doc_001",
  "name": "Not Your Mama's Kitchen Menu",
  "createdAt": "2026-03-15T12:00:00Z",
  "updatedAt": "2026-03-15T12:00:00Z",
  "canvas": {
    "width": 3600,
    "height": 5400,
    "dpi": 300,
    "unit": "px",
    "backgroundColor": "#f3f3f3"
  },
  "settings": {
    "layoutLocked": true,
    "backgroundLayerLocked": true,
    "snapEnabled": false,
    "gridEnabled": false
  },
  "editorState": {
    "activeElementId": null,
    "selectedElementIds": [],
    "zoom": 1,
    "panX": 0,
    "panY": 0
  },
  "assets": [],
  "elements": [],
  "meta": {
    "sourceTemplate": "nymk-menu-v1",
    "migrationFrom": "1.x"
  }
}
```

## Top-Level Field Definitions
### Required
- `version`: schema version string, required for migration.
- `documentId`: unique document identifier.
- `name`: human-readable document/project name.
- `canvas`: fixed export-space definition.
- `settings`: document-level editing behavior.
- `assets`: reusable source asset registry.
- `elements`: placed objects on canvas.

### Optional but recommended
- `createdAt`
- `updatedAt`
- `editorState`
- `meta`

## Canvas Object
```json
{
  "width": 3600,
  "height": 5400,
  "dpi": 300,
  "unit": "px",
  "backgroundColor": "#f3f3f3"
}
```

### Rules
- `width` and `height` represent export-space dimensions.
- Version 2 default is 3600 x 5400 at 300 DPI.
- `unit` should remain `px` internally.
- Background color is allowed, but background composition is expected to come from image/shape elements.

## Settings Object
```json
{
  "layoutLocked": true,
  "backgroundLayerLocked": true,
  "snapEnabled": false,
  "gridEnabled": false
}
```

### Required meanings
- `layoutLocked`: global edit lock.
- `backgroundLayerLocked`: blocks editing for elements assigned to the background layer role.
- `snapEnabled`: optional alignment feature flag.
- `gridEnabled`: optional future editor aid.

### Rules
- On load, `layoutLocked` should default to `true` to preserve current mobile-safe behavior.
- `backgroundLayerLocked` should default to `true`.
- Global locking must remain visually clear in UI.

## Editor State Object
```json
{
  "activeElementId": null,
  "selectedElementIds": [],
  "zoom": 1,
  "_userZoom": null,
  "panX": 0,
  "panY": 0
}
```

### Notes
- This stores transient workspace state.
- It may be persisted if useful, but core document fidelity must not depend on it.
- Selection state should never be required for export.
- `_userZoom`: stores the last manually-set zoom level. If present and non-1, it is restored on load instead of auto-fitting the canvas to the viewport. Set to `null` to allow auto-fit behavior.

## Asset Registry
Assets are reusable source definitions.

An asset is NOT the same as a placed object.
A single asset may be used by multiple image elements.

### Asset Shape
```json
{
  "id": "asset_001",
  "kind": "image",
  "name": "Chicken and Waffles Hero",
  "storage": {
    "originalUrl": "/Images/asset7.png",
    "previewUrl": "https://res.cloudinary.com/demo/image/upload/v1/asset7.webp",
    "thumbnailUrl": "https://res.cloudinary.com/demo/image/upload/w_300/v1/asset7.webp"
  },
  "original": {
    "width": 1800,
    "height": 1200,
    "mimeType": "image/png"
  },
  "tags": ["food", "hero", "waffles"],
  "createdAt": "2026-03-15T12:00:00Z",
  "updatedAt": "2026-03-15T12:00:00Z"
}
```

### Required asset fields
- `id`
- `kind`
- `name`
- `storage.originalUrl`
- `original.width`
- `original.height`
- `original.mimeType`

### Optional asset fields
- `storage.previewUrl`
- `storage.thumbnailUrl`
- `tags`
- timestamps

### Asset rules
- `originalUrl` is the source of truth for export.
- `previewUrl` is for editor display/performance only.
- `thumbnailUrl` is optional and useful for media pickers/layer panels later.
- Phase 2A only requires `kind: "image"`.
- Future asset kinds may be added later if needed.

## Base Element Contract
Every placed object on the canvas must share a common base structure.

### Base Element Shape
```json
{
  "id": "el_001",
  "type": "image",
  "name": "Hero Food Image",
  "x": 300,
  "y": 2100,
  "width": 800,
  "height": 600,
  "rotation": 0,
  "zIndex": 10,
  "locked": true,
  "visible": true,
  "opacity": 1,
  "layerRole": "background",
  "createdAt": "2026-03-15T12:00:00Z",
  "updatedAt": "2026-03-15T12:00:00Z"
}
```

### Required base fields
- `id`
- `type`
- `name`
- `x`
- `y`
- `width`
- `height`
- `rotation`
- `zIndex`
- `locked`
- `visible`
- `opacity`
- `layerRole`

### Base element rules
- `x` and `y` are top-left coordinates in document space.
- `rotation` is degrees.
- `zIndex` defines stack ordering.
- `locked` blocks selection, movement, resize, rotation, and edits.
- `visible` allows future hide/show support.
- `opacity` should be from 0 to 1.
- `layerRole` supports grouped behavior.

### Allowed layerRole values in V2
- `background`
- `content`
- `overlay`

## Text Element
```json
{
  "id": "el_text_001",
  "type": "text",
  "name": "Main Entrees Title",
  "x": 1430,
  "y": 500,
  "width": 900,
  "height": 110,
  "rotation": 0,
  "zIndex": 40,
  "locked": false,
  "visible": true,
  "opacity": 1,
  "layerRole": "content",
  "text": "MAIN ENTREES",
  "style": {
    "fontFamily": "Bernard MT Condensed",
    "fontSize": 84,
    "fontWeight": 700,
    "fontStyle": "normal",
    "color": "#ffffff",
    "textAlign": "center",
    "lineHeight": 1.1,
    "letterSpacing": 0,
    "textTransform": "uppercase"
  },
  "createdAt": "2026-03-15T12:00:00Z",
  "updatedAt": "2026-03-15T12:00:00Z"
}
```

### Required text fields
- all base fields
- `text`
- `style.fontFamily`
- `style.fontSize`
- `style.color`

### Recommended text style fields
- `fontWeight`
- `fontStyle`
- `textAlign`
- `lineHeight`
- `letterSpacing`
- `textTransform`

## Image Element
```json
{
  "id": "el_img_001",
  "type": "image",
  "name": "Chicken and Waffles Image",
  "x": 300,
  "y": 2250,
  "width": 780,
  "height": 560,
  "rotation": -4,
  "zIndex": 18,
  "locked": true,
  "visible": true,
  "opacity": 1,
  "layerRole": "background",
  "assetId": "asset_007",
  "fitMode": "contain",
  "crop": null,
  "createdAt": "2026-03-15T12:00:00Z",
  "updatedAt": "2026-03-15T12:00:00Z"
}
```

### Required image fields
- all base fields
- `assetId`

### Optional image fields
- `fitMode`
- `crop`

### Image rules
- `assetId` must reference a valid asset.
- Export must use the referenced asset's `storage.originalUrl`.
- Editor preview may use `storage.previewUrl`.
- If `previewUrl` is absent, editor may fall back to `originalUrl`.
- Phase 2A should support move, resize, reorder, duplicate, delete, lock/unlock.

## Shape Element
Version 2 Phase 2A supports rectangles only.

```json
{
  "id": "el_shape_001",
  "type": "shape",
  "name": "Main Entrees Bar",
  "x": 1360,
  "y": 470,
  "width": 1080,
  "height": 100,
  "rotation": 0,
  "zIndex": 30,
  "locked": false,
  "visible": true,
  "opacity": 1,
  "layerRole": "background",
  "shapeType": "rectangle",
  "style": {
    "fill": "#000000",
    "stroke": null,
    "strokeWidth": 0,
    "cornerRadius": 0
  },
  "createdAt": "2026-03-15T12:00:00Z",
  "updatedAt": "2026-03-15T12:00:00Z"
}
```

### Required shape fields
- all base fields
- `shapeType`
- `style.fill`

### Shape rules
- Phase 2A supports only `shapeType: "rectangle"`.
- Shapes must support move, resize, recolor, reorder, duplicate, delete, lock/unlock.
- Fill color must support hex input.

## Selection and Locking Rules
### Global rules
- `settings.layoutLocked = true` blocks editing interactions globally.
- `settings.backgroundLayerLocked = true` blocks editing on elements where `layerRole = "background"`.

### Per-object rules
- `element.locked = true` blocks selection and manipulation of that object.
- Locked objects must not move, resize, rotate, or be accidentally selected.
- Unlocking should be deliberate and visually obvious.

## Save / Load Rules
Persist the full document object, including:
- `canvas`
- `settings`
- `assets`
- `elements`
- `meta`

Do NOT rely on transient UI state for document fidelity.

Expected persisted element state includes:
- positions
- sizes
- rotations
- z-order
- lock state
- visibility
- styles
- asset references

## Undo / Redo Rules
For Phase 2A, use full-document snapshots.

### Recommendation
- maximum 50 history states initially
- snapshot after each discrete committed change

### Must cover
- text edits
- image move/resize/reorder/lock/delete/duplicate
- shape create/move/resize/recolor/reorder/lock/delete/duplicate
- global/document lock changes if they affect user-facing state

## Export Rules
### Required
- Export must render from `elements` in z-order.
- Text renders from text properties.
- Shapes render from shape properties.
- Images render from referenced asset `storage.originalUrl`.
- Preview URLs must NEVER be used for final export.
- Output remains deterministic 12-inch 300 DPI PNG.

### Z-order rule
- Render in ascending `zIndex`.

## Migration Rules from V1
The old system is text-over-background.
Version 2 is a full layered document model.

### Required migration behavior
- old text items become `type: "text"` elements
- migrated document version becomes `2.0.0`
- `layoutLocked` defaults to `true`
- `backgroundLayerLocked` defaults to `true`

### Compatibility principle
The existing conceptual `menu-bg.jpg` result must remain compatible with the workflow, even if internally the document is now composed from many editable elements.

## Phase 2A Scope Guidance
This data model supports future features, but Phase 2A should implement only the smallest safe layered slice.

### Phase 2A should include
- V2 schema adoption
- migration support
- text elements
- image elements from the existing Images folder
- rectangle shape elements
- per-object locking
- background layer lock behavior
- expanded save/load
- expanded export

### Phase 2A should NOT yet include
- full Cloudinary upload flow
- advanced asset management UI
- complex layer panel
- visibility panel UI unless trivial
- advanced vector editing
- non-rectangle shapes
- heavy mobile editing expansion

## Required initialization behavior for current project
For the current menu project:
- initialize the 14 existing image assets from the Images folder into the asset registry
- place them as image elements in the document
- assign them `layerRole: "background"`
- set them locked by default
- preserve the existing visual composition as closely as possible

## Future Extension Notes
This model is intentionally designed to support later additions such as:
- uploaded image assets
- Cloudinary-generated preview URLs
- thumbnail generation
- visibility toggles
- alignment/snap tools
- richer layer panel
- additional shapes
- cropping
- template libraries
- multi-page documents

## Final Implementation Directive
Antigravity should use this file as the official V2 data model contract.
If implementation requires deviation, the deviation must be documented and approved before coding proceeds.

## Implemented Behaviors (March 28, 2026)
All Phase 2A items listed in the scope section are implemented. Additionally:
- `addFromTray(src, skipPush)` — second param prevents double pushState from upload path
- `deleteEl(skipPush, noRender)` — second param prevents N renderings in bulk-delete loops
- `_mergeLoadedDoc(s)` — asset registry merge is safe against server overwriting user-uploaded assets
- `onTextBlur` / `onTextFocus` — use `innerText` consistently for text capture and commit
- `sync()` — guarded with `contentEditable !== 'true'` to prevent text-in-edit overwrite
- `finalizeLasso()` — unified X/Y scale ratio, touch + mouse events both handled
- Export PNG — rounded stroke re-traces bezier path; image load guard skips broken images; multi-line `\n` split
- `fitCanvasToScreen()` — functional viewport-width scaling, `_userZoom` checked before auto-fit
- `resetToOriginal()` — clears localStorage on success, shows toast on failure without reloading
- `addRect()` — places at viewport center (not hardcoded coordinates)
