> ⛔ **THIS DOCUMENT IS SUPERSEDED**
> 
> **This is an older Phase 29 handoff (March 17, 2026).**  
> The current master continuity document is **[HANDOFF_V3.md](./HANDOFF_V3.md)** (March 28, 2026).  
> HANDOFF_V3.md includes all changes through Phase 30 (PageSpeed 100), Phases 2A–11 (multi-select, lasso, alignment tools, keyboard shortcuts, font size control, save/load hardening, asset registry), and Bug Fix Batches 1–8 (18 bugs fixed).  
> **Start all new threads from HANDOFF_V3.md, not this file.**

---

# CONTINUITY_HANDOFF_CURRENT.md
# Dine In Menu Editor Pro V2 — AI Assistant Continuity & Handoff Document
**Version**: Phase 29 Handoff (SUPERSEDED — see HANDOFF_V3.md)
**Last Updated**: March 17, 2026 (header updated March 28, 2026)
**Repository**: mariaisabeljuarezgomez/NOTYOURMAMASKITCHENFULL
**Deployed at**: Railway (auto-deploy from GitHub main branch)
**Prepared by**: MARIAS DIGITAL DESIGNS / Rogelio Corral

---

## Purpose of This Document

This document exists to give any AI coding assistant (Claude, GPT-4, Copilot, Antigravity, etc.) complete context to resume work on this project without re-explaining the entire history. Read this document fully before touching any code. It answers:

- What this project is
- What state it is currently in
- What files do what and which are sacred
- What has been built, tested, and locked
- What the current working rules are
- What to do and what NOT to do

**⛔ This file covers Phase 29 only. For the full current state including Phase 30, Phases 2A–11, and Bug Fix Batches 1–8, use HANDOFF_V3.md.**

---

## 1. Project Identity

**Product**: Dine In Menu Editor Pro V2  
**Client**: MARIAS DIGITAL DESIGNS — restaurant brand menu editor  
**Type**: Single-page browser app, generator-compiled, Flask-served, Railway-deployed  
**Current phase**: **Phase 29 — Final Polish & UX Hardening** ✅ COMPLETE (as of this document)  
**Current actual state**: Phase 30 + Phases 2A–11 + Bug Batches 1–8 complete — see HANDOFF_V3.md  
**Status**: Production-deployed, stable, all known bugs resolved

This is NOT a simple text editor anymore. It is a full multi-layer canvas editor with:
- Text elements (editable, styled)
- Image elements (uploadable, resizable)
- Shape/rectangle elements
- Multi-select (Shift+click, lasso, touch lasso)
- 8-way alignment and distribution tools
- Keyboard shortcuts (Delete, Ctrl+Z/D/A, Arrow nudge)
- Layers panel, selection bar with 3 tabs, asset tray
- Server-side session persistence with cross-device sync
- 300 DPI professional PNG export (Canvas API, NOT html2canvas)
- Undo system (30 steps, with Ctrl+Z text-editing guard)
- Full mobile touch support with Layout Lock safety model
- Bilingual in-app manual (EN/ES)
- PageSpeed 100/100/100/100

---

## 2. The Golden Rules — Read Before Writing Any Code

These are non-negotiable. Violating any of them will break the project.

### Rule 1: index.html is currently the live source
As of March 28, 2026, `index.html` has been manually patched with Phases 2A–11 and Bug Fix Batches 1–8. `build_app.py` is frozen at Phase 30. **Do NOT run `python build_app.py`** until all patches are reconciled into the generator. Edit `index.html` directly for now.

### Rule 2: Double all literal braces in Python f-strings
`build_app.py` uses Python f-strings to emit JavaScript and CSS. Any literal `{` or `}` in the JavaScript or CSS output must be written as `{{` or `}}` in the Python source.

### Rule 3: Never load menu-bg.png on page load
`menu-bg.png` is 7.2 MB. It is only loaded during the export pipeline. The editing preview uses `menu-bg-preview.jpg` (~114 KB).

### Rule 4: Layout Locked is always the default on load
The app must always initialize with Layout Locked = true.

### Rule 5: User images must be served from the same origin
Cross-origin images cannot be drawn to Canvas. All uploaded images must be stored on the Railway Volume and served from `/user-images/<filename>`.

### Rule 6: The pHYs DPI injection must not be removed
`inject300DpiAndDownload()` in `export-utils.js` manually rewrites the exported PNG binary to insert the pHYs chunk (300 DPI). Do not remove.

### Rule 7: export-utils.js must be loaded with defer
Required for PageSpeed 100. Do not remove the `defer` attribute.

### Rule 8: Never use native browser alert(), confirm(), or prompt()
Use `showModal()` and `showToast()` instead.

### Rule 9: Atomic writes only for server persistence
All writes to `menu_data.json` must use the `.tmp` + `os.replace()` pattern.

### Rule 10: Do not reopen locked architecture decisions
See Section 9 of this document and HANDOFF_V3.md Section 5.

---

## 3. File Responsibility Map

| File | Who owns it | What it does | Edit? |
|------|------------|--------------|-------|
| `build_app.py` | Developer | Generates the entire frontend app (FROZEN — do not run) | ⚠️ Only after reconciliation |
| `index.html` | Live source | Manually patched frontend app (Phases 2A–11 + Batches 1–8) | ✅ YES — current edit target |
| `app.py` | Developer | Flask server — all API routes | ✅ YES when backend changes needed |
| `export-utils.js` | Developer | inject300DpiAndDownload() export utility | ✅ YES if export logic changes |
| `requirements.txt` | Developer | Python deps (Flask, flask-compress) | ✅ When adding new deps |
| `Procfile` | Developer | Railway process definition | ✅ Rarely |
| `menu-bg.png` | Design | Master background (export use only) | ✅ Replace when design changes |
| `menu-bg-preview.jpg` | Build | Compressed preview (run create_preview.py) | ✅ Regenerate after bg change |
| `*.ttf` fonts | Design | Brand font files (4 active, centurygothic.ttf DELETED) | ✅ Add/replace as needed |
| `manual-en.html` | Developer | In-app EN user manual | ✅ Update when features change |
| `manual-en-full.html` | Developer | Full standalone EN manual (added Mar 27, 2026) | ✅ Update when features change |
| `manual-es.html` | Developer | In-app ES user manual | ✅ Update when features change |
| `HANDOFF_V3.md` | Docs | **MASTER CONTINUITY DOC — use this** | ✅ Update at each milestone |
| `MASTER_TECHNICAL_SPEC.md` | Docs | Full technical spec | ✅ Update with architecture changes |
| `USER_MANUAL_SOURCE.md` | Docs | User-facing manual source | ✅ Update with features |

---

## 4. Resuming After This Handoff

**⛔ Use HANDOFF_V3.md as the starting document for any new thread.**

Current state as of **March 28, 2026**:
- Phase 30 complete (PageSpeed 100/100/100/100)
- Phases 2A–11 complete (all applied directly to `index.html`)
- Bug Fix Batches 1–8 complete (18 bugs fixed in `index.html`)
- Latest SHA: `6bc7fe4` on `main`
- **`build_app.py` is frozen at Phase 30** — do NOT regenerate `index.html` until generator patches are reconciled

**What was fixed in Bug Batches 1–8 (not in original Phase 29 docs):**
- Asset registry corruption on load (`_mergeLoadedDoc`)
- Text newlines preserved through sync, blur, and undo (`innerText` consistency)
- Undo history: group drag, arrow nudge, Ctrl+Z during text editing, addFromTray, double pushState on upload
- Export PNG: rounded stroke rendering (bezier re-trace), image load guard, multi-line text split
- Bulk delete: N→1 render via `noRender` param on `deleteEl`
- Mobile: lasso touch events, real `fitCanvasToScreen`, zoom persistence (`_userZoom`)
- `resetToOriginal`: no reload on failure, clears localStorage on success
- `addRect`: places at viewport center instead of hardcoded position
- `setSelectedAsBackground`: full object constructed before `push()`
- `openDrawer`: failed images retry correctly without stale guard

---

*End of CONTINUITY_HANDOFF_CURRENT.md — Phase 29 Handoff (superseded by HANDOFF_V3.md)*
*Header updated March 28, 2026 to reflect current project state*
