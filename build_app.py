import json
import os
import glob
# Ensure we are in the script's directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("--- Menu Editor Pro Generator (V2 - UX Hardening) ---")
bg_url = "menu-bg-preview.jpg"
bg_master = "menu-bg.png"

# Assets: Fonts
font_files = glob.glob("*.ttf") + glob.glob("*.otf")
fonts = {os.path.splitext(f)[0]: f for f in font_files}
font_options = "".join([f"<option value=\"{n}\">{n.replace('-', ' ').title()}</option>\n" for n in sorted(fonts.keys())])

# Assets: Project Images (Referenced by file path for performance)
asset_html = []
image_files = sorted(glob.glob("Images/*.png") + glob.glob("Images/*.jpg"))
for fpath in image_files:
    fname = os.path.basename(fpath)
    asset_html.append(
        f'<img src="Images/{fname}" class="tray-item" '
        f'onclick="addFromTray(this.src)" title="{fname}" '
        f'loading="lazy" width="80" height="80">'
    )

asset_gallery_html = "".join(asset_html)

with open("raw_coords.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

width, height = raw_data["width"], raw_data["height"]
spans = raw_data["text_data"]

font_css = "".join([f"@font-face {{ font-family: '{n}'; src: url('{f}') format('truetype'); font-display: swap; }}\n" for n, f in fonts.items()])

html_start = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
<title>Menu Editor Pro V2 - UX Hardened</title>
<style>
{font_css}
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
:root {{ --primary: #95201d; --accent: #f1c40f; --bg: #1a1a1a; --surface: #2d2d2d; --selection: rgba(241, 196, 15, 0.5); }}
html {{ height: 100%; overflow: hidden; margin: 0; }}
body {{ margin: 0; padding:0; background: var(--bg); font-family: 'Inter', sans-serif; overflow:hidden; height:100%; color:#fff; user-select: none; -webkit-user-select: none; }}

/* Fix 4 - Bigger Main Viewport Scrollbars */
#editor-viewport::-webkit-scrollbar {{ width: 10px; height: 10px; }}
#editor-viewport::-webkit-scrollbar-track {{ background: #222; }}
#editor-viewport::-webkit-scrollbar-thumb {{ background: #666; border-radius: 5px; }}
#editor-viewport::-webkit-scrollbar-thumb:hover {{ background: #999; }}
#editor-viewport {{ scrollbar-width: thin; scrollbar-color: #666 #222; }}

#top-header {{ position:fixed; top:0; left:0; right:0; height:60px; background:rgba(0,0,0,0.9); backdrop-filter:blur(10px); display:flex; align-items:center; justify-content:space-between; padding:0 20px; z-index:1000; border-bottom:1px solid #333; }}
#header-title {{ font-weight:700; font-size:16px; letter-spacing:1px; color:var(--accent); }}
.header-actions {{ display:flex; gap:10px; align-items:center; }}

#editor-viewport {{ position:absolute; top:60px; left:0; right:0; bottom:0; overflow:auto; background:#111; display:flex; align-items:flex-start; justify-content:center; }}
#centering-wrapper {{ 
    padding: 100px; 
    display: flex; 
    justify-content: center; 
    width: auto;
}}
#scaler-wrapper {{ 
    position:relative; 
    background:#fff; 
    box-shadow:0 10px 50px rgba(0,0,0,0.8); 
    width: 908px !important; 
    height: 1336px !important; 
    transform: none !important; 
}}
#menu-container {{ position:absolute; top:0; left:0; width:100%; height:100%; overflow:hidden; cursor: default; }}
#menu-bg {{ width:100%; height:100%; display:block; pointer-events:none; transition: opacity 0.3s; }}
.legacy-bg-hidden {{ opacity: 0; }}

.editable-element {{ position:absolute; cursor:pointer; transition: outline 0.1s, opacity 0.2s, border-radius 0.2s; user-select:none; z-index:10; transform-origin: center; box-sizing: border-box; }}
.editable-element:hover {{ outline: 2px solid var(--accent); }}
.editable-element.selected {{ outline: 3px solid var(--accent); box-shadow: 0 0 15px var(--selection); z-index: 100 !important; }}
.editable-element.locked {{ cursor: default; }}
.editable-element.hidden-editor {{ opacity: 0.2 !important; outline: 1px dashed #666; }}

.editable-text {{ white-space: pre-wrap; padding: 2px; }}
.image-object {{ object-fit: contain; overflow: hidden; }}
.shape-object {{ border: none; }}

/* Snapping Guides */
.guide {{ position:absolute; pointer-events:none; border: 1px dashed var(--accent); z-index: 500; display:none; }}
.guide-h {{ left:0; width: 100%; height: 0; }}
.guide-v {{ top:0; height: 100%; width: 0; }}

/* Navigation UI */
#fab {{ position:fixed; bottom:30px; left:30px; width:60px; height:60px; border-radius:50%; background:var(--primary); color:#fff; border:none; font-size:24px; cursor:pointer; z-index:1100; box-shadow:0 4px 20px rgba(0,0,0,0.6); transition:0.3s; display:flex; align-items:center; justify-content:center; }}
#fab.open {{ transform: rotate(90deg); background: #444; }}

#bottom-drawer {{ position:fixed; bottom:0; left:0; right:0; background:var(--surface); border-top:1px solid #444; padding:20px; z-index:900; transform:translateY(0); transition:0.4s cubic-bezier(0.19,1,0.22,1); width: 100%; box-sizing: border-box; }}
#bottom-drawer.closed {{ transform:translateY(100%); }}

.asset-tray {{ display:flex; gap:12px; overflow-x:auto; padding-bottom:15px; margin-bottom:15px; border-bottom:1px solid #444; scrollbar-width: thin; }}
.tray-item {{ height:80px; width:auto; border-radius:6px; cursor:pointer; border:2px solid transparent; transition:0.2s; background:#222; }}
.tray-item:hover {{ border-color:var(--accent); transform:scale(1.05); }}

#layers-panel {{ background: #222; border-radius: 8px; border: 1px solid #333; max-height: 150px; overflow-y: auto; margin-top: 10px; }}
.layer-item {{ display: flex; align-items: center; gap: 10px; padding: 6px 12px; border-bottom: 1px solid #333; cursor: pointer; font-size: 11px; }}
.layer-item:hover {{ background: #2a2a2a; }}
.layer-item.active {{ background: #333; border-left: 3px solid var(--accent); }}
.layer-name {{ flex-grow: 1; color: #ccc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.layer-btn {{ background: transparent; border: none; color: #666; cursor: pointer; padding: 4px; border-radius: 4px; }}
.layer-btn:hover {{ color: #fff; background: #333; }}
.layer-btn.active {{ color: var(--accent); }}

.btn-row {{ display:flex; gap:10px; flex-wrap:wrap; }}
.btn-ui {{ background:#333; color:#fff; border:1px solid #444; padding:10px 18px; border-radius:8px; cursor:pointer; font-weight:600; font-size:12px; transition:0.2s; display:flex; align-items:center; gap:6px; }}
.btn-ui:hover {{ background:#444; }}
.btn-ui.primary {{ background:var(--primary); color:#fff; border-color:transparent; }}
.btn-ui.accent {{ background:var(--accent); color:#000; border-color:transparent; font-weight:700; }}

/* Selection Bar (Contextual) */
/* Fix 2 & 3 - Moveable Toolbar & Horizontal Scroll */
#selection-bar {{ 
    position:fixed; 
    bottom:120px; 
    left:50%; 
    transform:translateX(-50%); 
    background:rgba(0,0,0,0.95); 
    backdrop-filter:blur(10px); 
    padding:12px 20px; 
    border-radius:50px; 
    display:none; 
    align-items:center; 
    gap:12px; 
    z-index:2000; 
    box-shadow:0 15px 40px rgba(0,0,0,0.8); 
    border:1px solid #444; 
    flex-wrap:nowrap; 
    max-width: 90vw; 
    overflow-x: auto; 
    scrollbar-width: none; 
    -webkit-overflow-scrolling: touch;
}}
#bar-content {{
    display:flex; 
    align-items:center; 
    gap:10px; 
    flex-grow:1; 
    overflow-x:auto; 
    scrollbar-width:none;
    -webkit-overflow-scrolling: touch; 
    min-width: max-content;
}}
.ctrl-group {{ 
    display:flex; 
    align-items:center; 
    gap:8px; 
    border-left:1px solid #333; 
    padding-left:12px; 
    flex-shrink: 0; 
}}
#selection-bar.show {{ display:flex; animation: barPop 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275); }}
@keyframes barPop {{ from {{ opacity:0; transform:translateX(-50%) translateY(20px) scale(0.9); }} to {{ opacity:1; transform:translateX(-50%) translateY(0) scale(1); }} }}

.bar-tab {{ padding: 6px 14px; border-radius: 20px; font-size: 10px; font-weight: 800; color: #888; cursor: pointer; transition: 0.2s; background: #111; border: 1px solid #222; text-transform: uppercase; }}
.bar-tab.active {{ background: var(--primary); color: #fff; border-color: var(--accent); box-shadow: 0 0 10px rgba(149, 32, 29, 0.5); }}

#selection-bar::-webkit-scrollbar {{ display: none; }}
#bar-content::-webkit-scrollbar {{ display: none; }}

#toast-container {{ position:fixed; top:80px; left:50%; transform:translateX(-50%); z-index:3000; }}
.toast {{ background:rgba(0,0,0,0.9); color:#fff; padding:10px 20px; border-radius:30px; border:1px solid var(--accent); margin-bottom:10px; animation: slideDown 0.3s; display:flex; align-items:center; gap:8px; font-size:13px; }}
@keyframes slideDown {{ from {{ opacity:0; transform:translateY(-20px); }} to {{ opacity:1; transform:translateY(0); }} }}

/* Header High Visibility */
#btn-lock-global {{ font-size: 11px; padding: 8px 15px; border-radius: 20px; }}
.lock-unlocked {{ background: var(--accent) !important; color: #000 !important; border-color: #000 !important; }}

/* Smart Tooltip Premium Style */
#smart-tooltip {{
    position: fixed;
    display: none;
    background: rgba(20, 20, 20, 0.95);
    backdrop-filter: blur(8px);
    color: #fff;
    padding: 12px 18px;
    border-radius: 12px;
    font-size: 12px;
    line-height: 1.5;
    z-index: 100000;
    pointer-events: none;
    box-shadow: 0 10px 30px rgba(0,0,0,0.8), 0 0 0 1px rgba(255,255,255,0.1);
    border-left: 4px solid var(--accent);
    max-width: 280px;
    animation: tooltipFade 0.2s ease-out;
}}
@keyframes tooltipFade {{ from {{ opacity: 0; transform: translateY(5px); }} to {{ opacity: 1; transform: translateY(0); }} }}
</style>
</head>
<body>
<div id="toast-container"></div>
<div id="smart-tooltip"></div>
<div id="top-header">
    <div id="header-title">MENU EDITOR PRO V2</div>
    <div class="header-actions">
        <button id="btn-undo" class="btn-ui" onclick="undo()" title="Undo Last Change" data-help="Reverses your last action (move, edit, delete, etc.)">↺ UNDO</button>
        <button id="btn-lock-global" class="btn-ui primary" onclick="toggleGlobalLock()" data-help="When locked, elements cannot be moved or edited — click to unlock for editing">🔒 LAYOUT LOCKED</button>
        <button id="btn-reload" class="btn-ui" onclick="location.reload()" data-help="Reloads the page to reset the session if needed.">↺ RELOAD</button>
    </div>
</div>

<main id="editor-viewport" onclick="onViewportClick(event)">
    <div id="centering-wrapper">
        <div id="scaler-wrapper" style="width:{width}px; height:{height}px;">
            <div id="menu-container" onclick="onCanvasClick(event)">
                <img id="menu-bg" src="{bg_url}" alt="BG">
                <div id="elements-layer" style="position:absolute; top:0; left:0; width:100%; height:100%;"></div>
                <div id="guide-cx" class="guide guide-v" style="left:50%"></div>
                <div id="guide-cy" class="guide guide-h" style="top:50%"></div>
            </div>
"""

# Text Data to V2 Elements
elements_json = []
for i, s in enumerate(spans):
    f_fam = "century-gothic-regular"
    if "bold" in s["font"].lower(): f_fam = "century-gothic-bold"
    elements_json.append({
        "id": f"txt_{i}", "type": "text", "text": s["text"], "x": s["bbox"][0], "y": s["bbox"][1], "zIndex": 10, 
        "opacity": 1, "rotation": 0, "visible": True, "locked": False, "layerRole": "content",
        "style": { "fontFamily": f_fam, "fontSize": s["size"], "color": f"#{s['color']:06x}" if s['color']>0 else "#000000", "lineHeight": 1.1, "letterSpacing": 0 }
    })

html_footer = f"""</div></div></main>

<button id="fab" onclick="this.classList.toggle('open'); document.getElementById('bottom-drawer').classList.toggle('closed')" data-help="Opens the asset tray and main menu controls.">☰</button>

<div id="bottom-drawer" class="closed">
    <div class="asset-tray">{asset_gallery_html}</div>
    <div class="btn-row">
        <button id="btn-save" class="btn-ui primary" onclick="save()" data-help="Saves your current layout to the server AND to browser memory as a backup">💾 Save Project</button>
        <button id="btn-load" class="btn-ui" onclick="load()" data-help="Loads your last saved project from the server or browser backup">📂 Load Draft</button>
        <button id="btn-add-text" class="btn-ui" onclick="addText()" data-help="Creates a new editable text box in the center of the menu — double-click to type">＋ Add Text</button>
        <button id="btn-add-rect" class="btn-ui" onclick="addRect()" data-help="Adds a colored rectangle shape — useful for backgrounds, banners, or price tags">⬜ Add Rect</button>
        <button id="btn-upload-img" class="btn-ui" onclick="document.getElementById('in-img').click()" data-help="Upload a photo or logo from your device to place on the menu">🖼️ Upload Img</button>
        <button id="btn-toggle-bg" class="btn-ui" onclick="toggleBg()" data-help="Show or hide the original scanned menu background image">👁️ Toggle Original BG</button>
        <button id="btn-png" class="btn-ui accent" onclick="exportPng()" data-help="Renders the entire menu as a high-resolution PNG file ready to print or share">⬇️ Final PNG Export</button>
    </div>
    <div id="layers-panel"></div>
    <input type="file" id="in-img" style="display:none" accept="image/*" onchange="importImg(this)">
</div>

<div id="selection-bar">
    <div id="bar-handle" style="cursor:grab; padding:4px 8px; color:#666; font-size:18px; flex-shrink:0; touch-action:none;" title="Drag to move toolbar">⠿</div>
    <div style="display:flex; gap:6px; margin-right:10px; flex-shrink:0;">
        <div class="bar-tab active" id="tab-layer" onclick="setBarTab('layer')" data-help="Controls visibility, opacity, rotation, and layer role">LAYER</div>
        <div class="bar-tab" id="tab-design" onclick="setBarTab('design')" data-help="Controls font, color, line height, letter spacing (text) or corner radius and stroke (shapes)">DESIGN</div>
        <div class="bar-tab" id="tab-arrange" onclick="setBarTab('arrange')" data-help="Controls position in the layer stack and center alignment">ARRANGE</div>
    </div>

    <div id="bar-content" style="display:flex; align-items:center; gap:10px; flex-grow:1; overflow-x:auto; scrollbar-width:none;">
        <div id="bar-tab-layer" style="display:flex; align-items:center; gap:10px;">
            <button class="ctrl-btn" id="ctrl-lock" onclick="toggleItemLock()" title="Lock Layer" data-help="Prevents the element from being moved or edited">🔓</button>
            <button class="ctrl-btn" id="ctrl-visible" onclick="toggleVisibility()" title="Show/Hide" data-help="Hides or shows the element on the canvas">👁️</button>
            <div class="ctrl-group"><label>Role</label><select id="sel-role" onchange="updateProp('layerRole', this.value)"><option value="content">Content</option><option value="background">Background</option><option value="overlay">Overlay</option></select></div>
            <div class="ctrl-group"><label>Opac</label><input type="range" id="sel-opacity" min="0" max="100" style="width:40px" oninput="updateProp('opacity', this.value/100)"></div>
            <div class="ctrl-group"><label>Rot</label><input type="range" id="sel-rotate" min="0" max="359" style="width:40px" oninput="updateProp('rotation', parseInt(this.value))"></div>
        </div>

        <div id="bar-tab-design" style="display:none; align-items:center; gap:10px;">
            <div id="geo-style-ctrls" style="display:flex; align-items:center; gap:10px;">
                <div class="ctrl-group"><label>Rad</label><input type="range" id="sel-radius" min="0" max="200" style="width:40px" oninput="updateProp('cornerRadius', parseInt(this.value))"></div>
                <div class="ctrl-group"><label>Stroke</label><input type="number" id="sel-stroke-w" min="0" max="50" style="width:40px" onchange="updateProp('strokeWidth', parseInt(this.value))"><input type="color" id="sel-stroke-c" onchange="updateProp('strokeColor', this.value)"></div>
            </div>
            <div id="text-style-ctrls" style="display:none; align-items:center; gap:10px;">
                <select id="sel-font" style="max-width:100px" onchange="updateStyle('fontFamily', this.value)">{font_options}</select>
                <input type="color" id="sel-color" onchange="updateStyle('color', this.value)">
                <div class="ctrl-group"><label>L.H.</label><input type="number" id="sel-l-height" step="0.1" min="0.5" max="3" style="width:40px" onchange="updateStyle('lineHeight', parseFloat(this.value))"></div>
                <div class="ctrl-group"><label>L.S.</label><input type="number" id="sel-l-spacing" min="-10" max="50" style="width:40px" onchange="updateStyle('letterSpacing', parseInt(this.value))"></div>
            </div>
        </div>

        <div id="bar-tab-arrange" style="display:none; align-items:center; gap:10px;">
            <button id="btn-center-h" class="btn-ui" style="padding:6px 12px; font-size:10px;" onclick="centerElement('h')" data-help="Snaps the element to the exact horizontal center of the menu">Center H</button>
            <button id="btn-center-v" class="btn-ui" style="padding:6px 12px; font-size:10px;" onclick="centerElement('v')" data-help="Snaps the element to the exact vertical center of the menu">Center V</button>
            <div class="ctrl-group">
                <button id="btn-layer-up" class="ctrl-btn" style="width:30px; height:30px" onclick="updateZ(1)" title="Layer Up" data-help="Moves the element forward in the stacking order">⬆️</button>
                <button id="btn-layer-down" class="ctrl-btn" style="width:30px; height:30px" onclick="updateZ(-1)" title="Layer Down" data-help="Moves the element backward in the stacking order">⬇️</button>
                <button id="btn-layer-front" class="ctrl-btn" style="width:30px; height:30px; font-size:12px;" onclick="bringToFront()" title="To Front" data-help="Sends element all the way to the very top of the layer stack">⇈</button>
                <button id="btn-layer-back" class="ctrl-btn" style="width:30px; height:30px; font-size:12px;" onclick="sendToBack()" title="To Back" data-help="Sends element all the way to the very bottom of the layer stack">⇊</button>
            </div>
        </div>
    </div>
    <div style="display:flex; gap:10px; flex-shrink:0; margin-left:10px; border-left:1px solid #444; padding-left:10px;">
        <button id="btn-duplicate" class="ctrl-btn" style="background:#2980b9" onclick="duplicateEl()" title="Duplicate Layer" data-help="Makes an exact copy of the selected layer — text, image, or shape">📋</button>
        <button id="btn-delete" class="ctrl-btn" style="background:#c0392b; border-color:#e74c3c;" onclick="deleteEl()" title="Delete Layer" data-help="Permanently removes the selected element from the menu">🗑</button>
    </div>
</div>

<script>
let docV2 = {{ 
    version:"2.0.0", 
    elements: {json.dumps(elements_json)}, 
    settings:{{ legacyBgVisible:true, layoutLocked:true, backgroundLayerLocked:true }}, 
    editorState:{{ zoom:1 }} 
}};
const BASE_W = 908.4429931640625;
const BASE_H = 1336.02001953125;
const PAD = 100;

let layoutLocked = true, selectedId = null, zoomScale = 1;
let historyStack = [];

function pushState() {{
    // Keep max 30 states for memory hygiene
    if(historyStack.length > 30) historyStack.shift();
    historyStack.push(JSON.stringify(docV2.elements));
    console.log("State Pushed. Stack Size:", historyStack.length);
}}

function undo() {{
    console.log("Undo Request. Stack Size:", historyStack.length);
    console.trace("Undo Source:");
    if(historyStack.length === 0) {{ 
        showToast("Nothing to Undo"); 
        console.warn("Undo ignored: History empty");
        return; 
    }}
    const lastElements = JSON.parse(historyStack.pop());
    docV2.elements = lastElements;
    // If the selected element was removed in the undone state, deselect
    if(selectedId && !docV2.elements.find(e => e.id === selectedId)) {{
        selectedId = null;
    }}
    render();
    showToast("Action Undone");
    console.log("Undo Complete. New Stack Size:", historyStack.length);
}}

const elementsLayer = document.getElementById('elements-layer');
const viewport = document.getElementById('editor-viewport');
const scaler = document.getElementById('scaler-wrapper');
const selBar = document.getElementById('selection-bar');
const layersPanel = document.getElementById('layers-panel');

// Fix 2 - Moveable Toolbar JS Logic
let isBarDragged = false;
const barHandle = document.getElementById('bar-handle');
if(barHandle) {{
    barHandle.onpointerdown = (e) => {{
        e.preventDefault();
        barHandle.setPointerCapture(e.pointerId);
        barHandle.style.cursor = 'grabbing';
        let startX = e.clientX, startY = e.clientY;
        let rect = selBar.getBoundingClientRect();
        let offX = e.clientX - rect.left, offY = e.clientY - rect.top;

        document.onpointermove = (pe) => {{
            if(!isBarDragged) {{
                isBarDragged = true;
                selBar.style.transform = 'none';
                selBar.style.margin = '0';
            }}
            let nx = pe.clientX - offX;
            let ny = pe.clientY - offY;

            // Viewport Constraints
            nx = Math.max(0, Math.min(nx, window.innerWidth - selBar.offsetWidth));
            ny = Math.max(60, Math.min(ny, window.innerHeight - selBar.offsetHeight));

            selBar.style.left = nx + 'px';
            selBar.style.top = ny + 'px';
            selBar.style.bottom = 'auto'; // Break the fixed bottom rule
        }};

        document.onpointerup = () => {{
            document.onpointermove = null;
            document.onpointerup = null;
            barHandle.style.cursor = 'grab';
        }};
    }};
}}

function showToast(m) {{
    const t = document.createElement('div'); t.className = 'toast'; t.innerHTML = `<span>✔</span> ${{m}}`;
    const container = document.getElementById('toast-container');
    container.appendChild(t); setTimeout(() => t.remove(), 2500);
}}

function render() {{
    const bg = document.getElementById('menu-bg'); 
    if(bg) bg.classList.toggle('legacy-bg-hidden', !docV2.settings.legacyBgVisible);
    
    elementsLayer.innerHTML = ''; 
    const sorted = [...docV2.elements].sort((a,b)=> (a.zIndex||10)-(b.zIndex||10));
    
    sorted.forEach(d => {{
        const el = document.createElement(d.type==='image'?'img':'div'); el.id = d.id;
        el.className = 'editable-element ' + (d.type==='text'?'editable-text':(d.type==='image'?'image-object':'shape-object'));
        if(d.locked) el.classList.add('locked');
        if(!d.visible) el.classList.add('hidden-editor');
        if(selectedId === d.id) el.classList.add('selected');
        
        if(d.type==='text') {{ 
            el.innerText = d.text; 
            el.contentEditable = (!layoutLocked && !d.locked && d.visible); 
            el.onfocus = onTextFocus;
            el.onblur = onTextBlur;
            el.ondblclick = (e) => {{ if(!layoutLocked && !d.locked) el.focus(); e.stopPropagation(); }};
        }}
        if(d.type==='image') el.src = d.src;
        
        Object.assign(el.style, {{ 
            left:d.x+'px', top:d.y+'px', zIndex:d.zIndex||10, 
            opacity: d.opacity ?? 1,
            transform: `rotate(${{d.rotation||0}}deg)`,
            borderRadius: (d.cornerRadius||0)+'px',
            border: (d.strokeWidth||0) > 0 ? `${{d.strokeWidth}}px solid ${{d.strokeColor||'#000'}}` : 'none'
        }});
        
        if(d.style) {{
            if(d.style.fontFamily) el.style.fontFamily = d.style.fontFamily;
            if(d.style.fontSize) el.style.fontSize = d.style.fontSize+'px';
            if(d.style.color) el.style.color = d.style.color;
            if(d.style.lineHeight) el.style.lineHeight = d.style.lineHeight;
            if(d.style.letterSpacing) el.style.letterSpacing = d.style.letterSpacing + 'px';
            if(d.style.fill) el.style.backgroundColor = d.style.fill;
        }}
        if(d.width) el.style.width = d.width+'px'; if(d.height) el.style.height = d.height+'px';
        
        elementsLayer.appendChild(el); attach(el);
    }});
    renderLayerList();
    if(selectedId) updateSelectionBar();
}}

function renderLayerList() {{
    layersPanel.innerHTML = '';
    [...docV2.elements].sort((a,b)=> (b.zIndex||10)-(a.zIndex||10)).forEach(item => {{
        const div = document.createElement('div');
        div.className = 'layer-item' + (selectedId === item.id ? ' active' : '');
        div.onclick = (e) => {{ e.stopPropagation(); selectById(item.id); }};
        
        const icon = item.type==='text'?'T':(item.type==='image'?'🖼️':'⬜');
        const name = item.text || item.id;
        
        const roleTag = `<span style="font-size:8px; padding:2px 4px; border-radius:3px; background:#444; color:#aaa; text-transform:uppercase; margin-right:4px;">${{item.layerRole || 'content'}}</span>`;
        
        div.innerHTML = `
            <div style="font-size:12px">${{icon}}</div>
            <div class="layer-name">${{roleTag}}${{name}}</div>
            <button class="layer-btn ${{item.visible?'active':''}}" onclick="toggleVisById(event, '${{item.id}}')">👁️</button>
            <button class="layer-btn ${{item.locked?'active':''}}" onclick="toggleLockById(event, '${{item.id}}')">🔒</button>
        `;
        layersPanel.appendChild(div);
    }});
}}

function attach(el) {{
    el.onmousedown = (e) => {{
        console.log("Element Mousedown:", el.id);
        e.stopPropagation();
        const itemData = d(el);
        selectById(el.id);
        
        if(layoutLocked || itemData.locked || (docV2.settings.backgroundLayerLocked && itemData.layerRole==='background')) return;
        
        pushState(); // Store state BEFORE move
        
        let rect = elementsLayer.getBoundingClientRect();
        let ox = (e.clientX - rect.left)/zoomScale - parseFloat(el.style.left);
        let oy = (e.clientY - rect.top)/zoomScale - parseFloat(el.style.top);
        
        const gcx = document.getElementById('guide-cx'), gcy = document.getElementById('guide-cy');

        document.onmousemove = (me) => {{
            let nx = (me.clientX - rect.left)/zoomScale - ox;
            let ny = (me.clientY - rect.top)/zoomScale - oy;
            
            const cx = BASE_W/2 - el.offsetWidth/2, cy = BASE_H/2 - el.offsetHeight/2;
            if(Math.abs(nx-cx)<15) {{ nx=cx; gcx.style.display='block'; }} else gcx.style.display='none';
            if(Math.abs(ny-cy)<15) {{ ny=cy; gcy.style.display='block'; }} else gcy.style.display='none';

            el.style.left = nx + 'px'; el.style.top = ny + 'px';
        }};
        document.onmouseup = () => {{ document.onmousemove = null; gcx.style.display='none'; gcy.style.display='none'; sync(); }};
    }};

    el.ontouchstart = (e) => {{
        if(e.touches.length !== 1) return;
        const touch = e.touches[0];
        const fakeEvent = {{ clientX: touch.clientX, clientY: touch.clientY, stopPropagation: () => e.stopPropagation() }};
        el.onmousedown(fakeEvent);
        e.preventDefault();
    }};
    el.ontouchmove = (e) => {{
        if(e.touches.length !== 1) return;
        const touch = e.touches[0];
        if(document.onmousemove) document.onmousemove({{ clientX: touch.clientX, clientY: touch.clientY }});
        e.preventDefault();
    }};
    el.ontouchend = () => {{
        if(document.onmouseup) document.onmouseup();
    }};
}}

function selectById(id) {{
    // Remove selected class from old element without full re-render
    if(selectedId) {{
        const oldEl = document.getElementById(selectedId);
        if(oldEl) oldEl.classList.remove('selected');
    }}
    selectedId = id;
    const newEl = document.getElementById(id);
    if(newEl) newEl.classList.add('selected');
    updateSelectionBar();
    renderLayerList();
}}

function updateSelectionBar() {{
    console.log("UpdateSelectionBar. ID:", selectedId);
    if(!selectedId) return;
    
    // Robust find: handles both literal ID and numeric/txt_/text_ prefix mismatches
    const item = docV2.elements.find(e => {{
        const normE = String(e.id).replace(/^(txt_|text_)/, '');
        const normS = String(selectedId).replace(/^(txt_|text_)/, '');
        return e.id == selectedId || normE == normS;
    }});

    if(!item) {{ 
        console.warn("Item not found for selection:", selectedId);
        deselect(); 
        return; 
    }}
    
    console.log("Showing Selection Bar for type:", item.type);
    selBar.classList.add('show');
    
    document.getElementById('text-style-ctrls').style.display = (item.type==='text'?'flex':'none');
    document.getElementById('geo-style-ctrls').style.display = (item.type==='text'?'none':'flex');
    
    document.getElementById('sel-opacity').value = (item.opacity ?? 1) * 100;
    document.getElementById('sel-rotate').value = item.rotation || 0;
    if(item.type!=='text') {{
        document.getElementById('sel-radius').value = item.cornerRadius || 0;
        document.getElementById('sel-stroke-w').value = item.strokeWidth || 0;
        document.getElementById('sel-stroke-c').value = item.strokeColor || '#000000';
    }}
    document.getElementById('ctrl-lock').innerText = item.locked ? '🔒' : '🔓';
    document.getElementById('ctrl-lock').classList.toggle('active', item.locked);
    document.getElementById('ctrl-visible').innerText = item.visible ? '👁️' : '👁️‍🗨️';
    document.getElementById('ctrl-visible').classList.toggle('active', !item.visible);
    document.getElementById('sel-role').value = item.layerRole || 'content';
    
    if(item.type==='text') {{
        document.getElementById('sel-font').value = item.style.fontFamily.replace(/['"]/g, '');
        document.getElementById('sel-color').value = item.style.color;
        document.getElementById('sel-l-height').value = item.style.lineHeight || 1.1;
        document.getElementById('sel-l-spacing').value = item.style.letterSpacing || 0;
        // Default text elements to DESIGN tab if unlocked
        if(item.type === 'text') setBarTab('design');
    }}
    renderLayerList();
}}

function deselect() {{
    if(selectedId) {{
        const el = document.getElementById(selectedId);
        if(el) el.classList.remove('selected');
    }}
    selectedId = null;
    if(selBar) selBar.classList.remove('show');
    renderLayerList();
}}

function onCanvasClick(e) {{ if(e.target.id === 'menu-container' || e.target.id === 'elements-layer') deselect(); }}
function onViewportClick(e) {{ if(e.target.id === 'editor-viewport' || e.target.id === 'centering-wrapper') deselect(); }}

function toggleVisById(e, id) {{ e.stopPropagation(); const item = docV2.elements.find(i=>i.id===id); if(item) {{ pushState(); item.visible = !item.visible; render(); }} }}
function toggleLockById(e, id) {{ e.stopPropagation(); const item = docV2.elements.find(i=>i.id===id); if(item) {{ pushState(); item.locked = !item.locked; render(); }} }}

function setBarTab(tab) {{
    ['layer','design','arrange'].forEach(t => {{
        const target = document.getElementById('bar-tab-'+t);
        if(target) target.style.display = (t===tab?'flex':'none');
        const tabBtn = document.getElementById('tab-'+t);
        if(tabBtn) tabBtn.classList.toggle('active', t===tab);
    }});
}}

function d(el) {{ return docV2.elements.find(e => e.id === el.id); }}
function sync() {{
    document.querySelectorAll('.editable-element').forEach(el => {{
        let item = d(el); if(!item) return;
        item.x = parseFloat(el.style.left); item.y = parseFloat(el.style.top);
        if(item.type==='text') item.text = el.innerText;
    }});
}}

function updateProp(k, v) {{ if(!selectedId) return; pushState(); let item = docV2.elements.find(e=>e.id===selectedId); if(item) {{ item[k]=v; render(); }} }}
function updateStyle(k, v) {{ if(!selectedId) return; pushState(); let item = docV2.elements.find(e=>e.id===selectedId); if(item && item.style) {{ item.style[k]=v; render(); }} }}

function toggleGlobalLock() {{
    layoutLocked = !layoutLocked;
    const btn = document.getElementById('btn-lock-global');
    btn.innerText = layoutLocked ? '🔒 LAYOUT LOCKED' : '🔓 LAYOUT UNLOCKED';
    btn.classList.toggle('lock-unlocked', !layoutLocked);
    showToast(layoutLocked ? 'Layout Protected' : 'Edit Mode Active');
    
    // Fix 5b - Show zoom controls only when layout is UNLOCKED
    const zoomControls = document.getElementById('zoom-controls');
    if(zoomControls) {{
        zoomControls.style.display = layoutLocked ? 'none' : 'flex';
        console.log("Zoom controls visibility:", zoomControls.style.display);
    }}

    render();
}}

function toggleItemLock() {{ if(!selectedId) return; pushState(); let item = docV2.elements.find(e=>e.id===selectedId); item.locked = !item.locked; render(); }}
function toggleVisibility() {{ if(!selectedId) return; pushState(); let item = docV2.elements.find(e=>e.id===selectedId); item.visible = !item.visible; render(); }}
function toggleBg() {{ docV2.settings.legacyBgVisible = !docV2.settings.legacyBgVisible; render(); }}

function duplicateEl() {{
    if(!selectedId) return;
    pushState();
    let item = docV2.elements.find(e=>e.id===selectedId);
    if(!item) return;
    let clone = JSON.parse(JSON.stringify(item));
    clone.id = item.id + '_copy_' + Date.now();
    clone.x += 30; clone.y += 30;
    clone.zIndex = Math.max(...docV2.elements.map(e => e.zIndex || 10)) + 1;
    docV2.elements.push(clone);
    render();
    setTimeout(() => selectById(clone.id), 50);
    showToast('Layer Cloned');
}}

function bringToFront() {{ if(!selectedId) return; pushState(); let maxZ = Math.max(...docV2.elements.map(e => e.zIndex || 10)); let item=docV2.elements.find(e=>e.id===selectedId); if(item) item.zIndex = maxZ + 1; render(); }}
function sendToBack() {{ if(!selectedId) return; pushState(); let minZ = Math.min(...docV2.elements.map(e => e.zIndex || 10)); let item=docV2.elements.find(e=>e.id===selectedId); if(item) item.zIndex = minZ - 1; render(); }}
function centerElement(dir) {{ if(!selectedId) return; pushState(); let item = docV2.elements.find(e=>e.id===selectedId); let el = document.getElementById(selectedId); if(!item || !el) return; if(dir==='h') item.x = (BASE_W/2) - (el.offsetWidth/2); if(dir==='v') item.y = (BASE_H/2) - (el.offsetHeight/2); render(); sync(); }}
function deleteEl() {{ if(!selectedId) return; pushState(); docV2.elements = docV2.elements.filter(e => e.id !== selectedId); selectedId = null; render(); deselect(); }}

function addText() {{ pushState(); let id='txt_'+Date.now(); docV2.elements.push({{id, type:'text', text:'New Text', x:600, y:400, zIndex:51, opacity:1, rotation:0, visible:true, locked:false, layerRole:'content', style:{{fontFamily:'century-gothic-bold', fontSize:40, color:'#000', lineHeight:1.1, letterSpacing:0}} }}); render(); selectById(id); }}
function addRect() {{ pushState(); let id='rect_'+Date.now(); docV2.elements.push({{id, type:'shape', x:600, y:400, width:300, height:200, zIndex:5, opacity:1, rotation:0, visible:true, locked:false, layerRole:'content', style:{{fill:'#f1c40f'}} }}); render(); selectById(id); }}
function importImg(input) {{ let f = input.files[0]; if(!f) return; let r = new FileReader(); r.onload=(e)=>{{ addFromTray(e.target.result); }}; r.readAsDataURL(f); }}
function addFromTray(src) {{ let id='img_'+Date.now(); docV2.elements.push({{id, type:'image', src, x:500, y:500, width:400, height:400, zIndex:20, opacity:1, rotation:0, visible:true, locked:false, layerRole:'content' }}); render(); selectById(id); }}

// Fix 5c - Pinch-vs-drag suppression
document.addEventListener('touchstart', (e) => {{
    if(e.touches.length > 1 && document.onmousemove) {{
        document.onmousemove = null;
        document.onmouseup = null;
        const gcx = document.getElementById('guide-cx');
        const gcy = document.getElementById('guide-cy');
        if(gcx) gcx.style.display='none';
        if(gcy) gcy.style.display='none';
        sync();
    }}
}}, {{ passive: true }});

function applyZoom(f) {{
    zoomScale = Math.max(0.3, Math.min(4, zoomScale * f));
    const scalerWrapper = document.getElementById('scaler-wrapper');
    const centeringWrapper = document.getElementById('centering-wrapper');
    
    if(scalerWrapper) {{
        scalerWrapper.style.transform = `scale(${{zoomScale}})`;
        scalerWrapper.style.transformOrigin = 'top center';
    }}
    
    if(centeringWrapper) {{
        centeringWrapper.style.width = (BASE_W * zoomScale) + (PAD * 2) + 'px';
        centeringWrapper.style.height = (BASE_H * zoomScale) + (PAD * 2) + 'px';
    }}
}}

async function save() {{ sync(); localStorage.setItem('menu_pro_draft_v2', JSON.stringify(docV2)); await fetch('/api/menu', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(docV2)}}); showToast('Project Saved Locally'); }}
async function load() {{
    try {{ 
        let r = await fetch('/api/menu'); 
        let s = await r.json(); 
        if(s.elements && s.elements.length > 0) {{ 
            docV2 = s; 
            layoutLocked = docV2.settings.layoutLocked ?? true; 
            render(); 
            showToast('Project Loaded');
        }}
    }} catch(e) {{ 
        let l = localStorage.getItem('menu_pro_draft_v2'); 
        if(l) {{ 
            let parsed = JSON.parse(l); 
            if(parsed.elements && parsed.elements.length > 0) {{
                docV2 = parsed; 
                layoutLocked = docV2.settings.layoutLocked ?? true; 
                render(); 
            }}
        }} 
    }}
}}

async function exportPng() {{
    const S = 4.1687, canvas = document.createElement('canvas'); canvas.width = BASE_W*S; canvas.height = BASE_H*S; const ctx = canvas.getContext('2d');
    if(docV2.settings.legacyBgVisible) {{
        const img = new Image(); img.src = "{bg_master}"; await new Promise(r => img.onload = r);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    }} else {{ ctx.fillStyle='#fff'; ctx.fillRect(0,0,canvas.width,canvas.height); }}
    
    for(const el of [...docV2.elements].sort((a,b)=>(a.zIndex||10)-(b.zIndex||10))) {{
        if(!el.visible) continue;
        ctx.save();
        ctx.globalAlpha = el.opacity ?? 1;
        let L = el.x * S, T = el.y * S, W = (el.width||0) * S, H = (el.height||0) * S;
        if(el.type==='text') {{ ctx.font=`${{el.style.fontSize*S}}px "${{el.style.fontFamily}}"`; W=ctx.measureText(el.text).width; H=el.style.fontSize*S; }}
        
        if(el.rotation) {{
            let cx = L + W/2, cy = T + H/2;
            ctx.translate(cx, cy); ctx.rotate(el.rotation * Math.PI / 180); ctx.translate(-cx, -cy);
        }}

        if(el.cornerRadius && el.type!=='text') {{
            const R = el.cornerRadius * S;
            ctx.beginPath(); ctx.moveTo(L+R, T); ctx.lineTo(L+W-R, T); ctx.quadraticCurveTo(L+W, T, L+W, T+R); ctx.lineTo(L+W, T+H-R); ctx.quadraticCurveTo(L+W, T+H, L+W-R, T+H); ctx.lineTo(L+R, T+H); ctx.quadraticCurveTo(L, T+H, L, T+H-R); ctx.lineTo(L, T+R); ctx.quadraticCurveTo(L, T, L+R, T); ctx.closePath(); ctx.clip();
        }}

        if(el.type==='text') {{ 
            ctx.font=`${{el.style.fontSize*S}}px "${{el.style.fontFamily}}"`; 
            ctx.fillStyle=el.style.color; ctx.textBaseline='top'; 
            ctx.fillText(el.text, L, T); 
        }}
        else if(el.type==='image') {{ 
            let img=new Image(); img.src=el.src; await new Promise(r=>img.onload=r); 
            ctx.drawImage(img, L, T, W, H); 
        }}
        else if(el.type==='shape') {{ ctx.fillStyle=el.style.fill; ctx.fillRect(L, T, W, H); }}
        
        if(el.strokeWidth && el.type!=='text') {{
            ctx.strokeStyle = el.strokeColor || '#000'; ctx.lineWidth = el.strokeWidth * S;
            ctx.strokeRect(L, T, W, H);
        }}
        ctx.restore();
    }}
    canvas.toBlob(b => {{ let a=document.createElement('a'); a.download='menu_v2_hardened.png'; a.href=URL.createObjectURL(b); a.click(); }}, 'image/png');
}}

window.onload = () => {{
    render();
    initSmartTooltips();
    fitCanvasToScreen();
    window.addEventListener('resize', fitCanvasToScreen);

    // Fix 1 - Font Force-Load on Mobile
    const fontNames = ['bernard-mt-condensed-regular','century-gothic-bold-italic','century-gothic-bold','century-gothic-regular','centurygothic'];
    fontNames.forEach(name => {{ document.fonts.load(`16px "${{name}}"`); }});
    
    // Fix 5b - Initial Zoom Controls State
    const zoomControls = document.getElementById('zoom-controls');
    if(zoomControls) zoomControls.style.display = layoutLocked ? 'none' : 'flex';
}};

function fitCanvasToScreen() {{
    console.log("fitCanvasToScreen: Using fixed 908px layout with natural scroll.");
}}
viewport.onwheel = (e) => {{ if(e.ctrlKey) {{ e.preventDefault(); applyZoom(e.deltaY>0?0.9:1.1, e.clientX, e.clientY); }} }};

window.addEventListener('keydown', (e) => {{
    if ((e.ctrlKey || e.metaKey) && e.key === 'z') {{
        e.preventDefault();
        undo();
    }}
}});

// Text editing history tracking
let textEditingOriginal = null;
function onTextFocus(e) {{ textEditingOriginal = e.target.innerText; }}
function onTextBlur(e) {{
    if(textEditingOriginal !== e.target.innerText) {{
        // Push the original state BEFORE syncing the new text
        const snapshot = JSON.stringify(docV2.elements);
        // Robust find for history matching
        const item = docV2.elements.find(el => {{
            const normE = String(el.id).replace(/^(txt_|text_)/, '');
            const normS = String(e.target.id).replace(/^(txt_|text_)/, '');
            return el.id == e.target.id || normE == normS;
        }});
        if(item) item.text = textEditingOriginal; // temporarily restore
        historyStack.push(snapshot);
        if(historyStack.length > 30) historyStack.shift();
        item.text = e.target.innerText; // put back the new text
    }}
}}

// Smart Tooltip Logic
let tooltipTimer = null;
const tooltipEl = document.getElementById('smart-tooltip');

function showTooltip(el, e) {{
    const helpText = el.getAttribute('data-help');
    const tipKey = 'tip_seen_' + (el.id || el.innerText.trim().toLowerCase());
    
    if(!helpText || sessionStorage.getItem(tipKey)) return;

    clearTimeout(tooltipTimer);
    tooltipEl.innerText = helpText;
    tooltipEl.style.display = 'block';
    
    // Position logic
    const rect = el.getBoundingClientRect();
    let top = rect.top - tooltipEl.offsetHeight - 10;
    let left = rect.left + (rect.width / 2) - (tooltipEl.offsetWidth / 2);

    // Collision detection
    if(top < 10) top = rect.bottom + 10;
    if(left < 10) left = 10;
    if(left + tooltipEl.offsetWidth > window.innerWidth - 10) {{
        left = window.innerWidth - tooltipEl.offsetWidth - 10;
    }}

    tooltipEl.style.top = top + 'px';
    tooltipEl.style.left = left + 'px';
    
    sessionStorage.setItem(tipKey, 'true');
    tooltipTimer = setTimeout(hideTooltip, 3000);
}}

function hideTooltip() {{
    clearTimeout(tooltipTimer);
    tooltipEl.style.display = 'none';
}}

function initSmartTooltips() {{
    document.body.addEventListener('mouseenter', (e) => {{
        const target = e.target.closest('[data-help]');
        if(target) showTooltip(target, e);
    }}, true);

    document.body.addEventListener('mouseleave', (e) => {{
        const target = e.target.closest('[data-help]');
        if(target) hideTooltip();
    }}, true);
}}
</script>

<!-- Fix 5b - Floating Zoom Buttons (High Visibility Debug Mode) -->
<div id="zoom-controls" style="position:fixed; right:20px; bottom:200px; display:flex; flex-direction:column; gap:12px; z-index:9999; padding:8px; background:rgba(0,0,0,0.8); border:2px solid #ff0000; border-radius:12px;">
    <button onclick="applyZoom(1.2)" style="width:50px;height:50px;border-radius:50%;background:#000;color:#fff;border:2px solid #fff;font-size:24px;cursor:pointer;display:flex;align-items:center;justify-content:center;">＋</button>
    <button onclick="applyZoom(0.833)" style="width:50px;height:50px;border-radius:50%;background:#000;color:#fff;border:2px solid #fff;font-size:24px;cursor:pointer;display:flex;align-items:center;justify-content:center;">－</button>
</div>

</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_start + html_footer)
print("Generated index.html with UX Hardening (Phase 2E Support).")
