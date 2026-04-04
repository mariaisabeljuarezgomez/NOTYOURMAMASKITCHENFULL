/**
 * editor-patches.js  —  All-in-one bug-fix patch
 * Loaded after index.html inline scripts.
 * Fixes: viewer tab, saveGlobalSettings, loadGlobalSettings,
 *        updateShapeFill, toggleOutlineOnly, addRect draw-to-create,
 *        addLine, injectResizeHandles (shape free-resize vs image AR),
 *        render() shape SVG (fill/stroke/radius), updateSelectionBar
 *        shape controls visibility, setLineWidth, setLineCap.
 */

// ─────────────────────────────────────────────────────────────────────────────
// UTILITY — safe item getter
// ─────────────────────────────────────────────────────────────────────────────
function _getItem(id) {
    const itemId = id !== undefined ? id : (typeof selectedId !== 'undefined' ? selectedId : null);
    if (!itemId) return null;
    return (docV2.elements || []).find(e => e.id === itemId) || null;
}

// ─────────────────────────────────────────────────────────────────────────────
// FIX: setRpTab — keeps viewer tab highlighted correctly
// ─────────────────────────────────────────────────────────────────────────────
function setRpTab(tab) {
    ['viewer'].forEach(t => {
        const btn   = document.getElementById(`rp-tab-${t}`);
        const panel = document.getElementById(`rp-panel-${t}`);
        const active = t === tab;
        if (btn)   btn.classList.toggle('active', active);
        if (panel) panel.style.display = active ? 'block' : 'none';
    });
    const vBtn = document.getElementById('rp-tab-viewer');
    if (vBtn) vBtn.classList.toggle('active', tab === 'viewer');
}

// ─────────────────────────────────────────────────────────────────────────────
// FIX: saveGlobalSettings / loadGlobalSettings
// ─────────────────────────────────────────────────────────────────────────────
function saveGlobalSettings() {
    const heroUrl = (document.getElementById('hero-video-url-input')   || {}).value || '';
    const lUrl    = (document.getElementById('side-panel-left-url')    || {}).value || '';
    const lLabel  = (document.getElementById('side-panel-left-label')  || {}).value || '';
    const rUrl    = (document.getElementById('side-panel-right-url')   || {}).value || '';
    const rLabel  = (document.getElementById('side-panel-right-label') || {}).value || '';
    if (!docV2.settings) docV2.settings = {};
    docV2.settings.viewer = {
        heroVideoUrl:   heroUrl,
        sidePanelLeft:  { videoUrl: lUrl,  label: lLabel },
        sidePanelRight: { videoUrl: rUrl,  label: rLabel }
    };
    if (typeof save === 'function') {
        save();
        if (typeof showToast === 'function') showToast('✅ Viewer settings saved');
    }
}

function loadGlobalSettings() {
    const viewer = (docV2.settings && docV2.settings.viewer) || {};
    const heroUrl   = viewer.heroVideoUrl || docV2.heroVideoUrl || '';
    const lSettings = viewer.sidePanelLeft  || docV2.sidePanelLeft  || {};
    const rSettings = viewer.sidePanelRight || docV2.sidePanelRight || {};
    const _set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val || ''; };
    _set('hero-video-url-input',   heroUrl);
    _set('side-panel-left-url',    lSettings.videoUrl || '');
    _set('side-panel-left-label',  lSettings.label    || '');
    _set('side-panel-right-url',   rSettings.videoUrl || '');
    _set('side-panel-right-label', rSettings.label    || '');
}

// ─────────────────────────────────────────────────────────────────────────────
// FIX: updateShapeFill — writes to item.style.fill (correct property)
// ─────────────────────────────────────────────────────────────────────────────
function updateShapeFill(val) {
    const item = _getItem();
    if (!item || item.type !== 'shape') return;
    if (!item.style) item.style = {};
    item.style.fill = val;
    if (typeof pushState === 'function') pushState();
    if (typeof render    === 'function') render();
}

// ─────────────────────────────────────────────────────────────────────────────
// FIX: toggleOutlineOnly — fill = 'transparent', strokeWidth ≥ 2,
//       strokeColor = gold; second press restores fill = '#333333'
// ─────────────────────────────────────────────────────────────────────────────
function toggleOutlineOnly() {
    const item = _getItem();
    if (!item || item.type !== 'shape') return;
    if (!item.style) item.style = {};

    const isOutline = item.style.fill === 'transparent';
    if (isOutline) {
        // Restore solid fill
        item.style.fill        = item._savedFill || '#333333';
        item._savedFill        = undefined;
        const btn = document.getElementById('btn-outline-toggle');
        if (btn) btn.style.background = '';
    } else {
        // Switch to outline-only
        item._savedFill        = item.style.fill || '#333333';
        item.style.fill        = 'transparent';
        item.strokeWidth       = Math.max(item.strokeWidth || 0, 2);
        item.strokeColor       = item.strokeColor || '#c8a96a';
        const btn = document.getElementById('btn-outline-toggle');
        if (btn) btn.style.background = '#c8a96a';
    }
    if (typeof pushState === 'function') pushState();
    if (typeof render    === 'function') render();
    if (typeof updateSelectionBar === 'function') updateSelectionBar();
}

// ─────────────────────────────────────────────────────────────────────────────
// FIX: addLine — 200×4 shape, gold fill, layer icon "—"
// ─────────────────────────────────────────────────────────────────────────────
function addLine() {
    if (typeof pushState === 'function') pushState();
    const canvas = docV2.canvas;
    const cx = (canvas ? canvas.width  : 908) / 2;
    const cy = (canvas ? canvas.height : 1336) / 2;
    const id = 'shape_line_' + Date.now();
    const el = {
        id,
        type:         'shape',
        shapeType:    'rect',
        x:            cx - 100,
        y:            cy - 2,
        width:        200,
        height:       4,
        zIndex:       10,
        opacity:      1,
        rotation:     0,
        visible:      true,
        locked:       false,
        layerRole:    'content',
        cornerRadius: 0,
        strokeWidth:  0,
        strokeColor:  '#c8a96a',
        style:        { fill: '#c8a96a' }
    };
    docV2.elements.push(el);
    if (typeof selectedId !== 'undefined') window.selectedId = id;
    if (typeof render    === 'function') render();
    if (typeof updateSelectionBar === 'function') updateSelectionBar();
    if (typeof showToast === 'function') showToast('Line added');
}

// ─────────────────────────────────────────────────────────────────────────────
// FIX: addRect — draw-to-create mode with crosshair cursor
//      Named pointer handlers so they self-remove cleanly.
//      Cancels if gesture < 10 px.
// ─────────────────────────────────────────────────────────────────────────────
function addRect() {
    const mc = document.getElementById('menu-container');
    if (!mc) return;

    window._drawMode = 'rect';
    mc.style.cursor = 'crosshair';
    if (typeof showToast === 'function') showToast('🖊 Draw a rectangle — drag on the canvas');

    let startX, startY, drawing = false;
    const preview = document.createElement('div');
    preview.style.cssText = 'position:absolute;border:2px dashed #c8a96a;background:rgba(200,169,106,0.15);pointer-events:none;z-index:9998;box-sizing:border-box;';

    function _drawPointerDown(e) {
        if (e.button !== 0) return;
        const rect = mc.getBoundingClientRect();
        const scale = mc.offsetWidth / (docV2.canvas ? docV2.canvas.width : 908);
        startX = (e.clientX - rect.left) / scale;
        startY = (e.clientY - rect.top)  / scale;
        drawing = true;
        preview.style.left   = startX + 'px';
        preview.style.top    = startY + 'px';
        preview.style.width  = '0px';
        preview.style.height = '0px';
        mc.appendChild(preview);
        e.stopPropagation();
    }

    function _drawPointerMove(e) {
        if (!drawing) return;
        const rect  = mc.getBoundingClientRect();
        const scale = mc.offsetWidth / (docV2.canvas ? docV2.canvas.width : 908);
        const cx = (e.clientX - rect.left) / scale;
        const cy = (e.clientY - rect.top)  / scale;
        const x  = Math.min(cx, startX), y = Math.min(cy, startY);
        const w  = Math.abs(cx - startX),  h = Math.abs(cy - startY);
        preview.style.left   = x + 'px';
        preview.style.top    = y + 'px';
        preview.style.width  = w + 'px';
        preview.style.height = h + 'px';
        e.stopPropagation();
    }

    function _drawPointerUp(e) {
        if (!drawing) return;
        drawing = false;
        if (preview.parentNode) preview.parentNode.removeChild(preview);

        const rect  = mc.getBoundingClientRect();
        const scale = mc.offsetWidth / (docV2.canvas ? docV2.canvas.width : 908);
        const cx = (e.clientX - rect.left) / scale;
        const cy = (e.clientY - rect.top)  / scale;
        const x  = Math.min(cx, startX), y = Math.min(cy, startY);
        const w  = Math.abs(cx - startX),  h = Math.abs(cy - startY);

        // Clean up listeners and cursor
        mc.removeEventListener('pointerdown', _drawPointerDown, true);
        mc.removeEventListener('pointermove', _drawPointerMove, true);
        mc.removeEventListener('pointerup',   _drawPointerUp,   true);
        mc.style.cursor = '';
        window._drawMode = null;

        if (w < 10 || h < 10) {
            if (typeof showToast === 'function') showToast('Too small — draw bigger');
            return;
        }

        if (typeof pushState === 'function') pushState();
        const id = 'shape_rect_' + Date.now();
        const el = {
            id,
            type:         'shape',
            shapeType:    'rect',
            x, y, width: w, height: h,
            zIndex:       10,
            opacity:      1,
            rotation:     0,
            visible:      true,
            locked:       false,
            layerRole:    'content',
            cornerRadius: 0,
            strokeWidth:  0,
            strokeColor:  '#c8a96a',
            style:        { fill: '#c8a96a' }
        };
        docV2.elements.push(el);
        window.selectedId = id;
        if (typeof render    === 'function') render();
        if (typeof updateSelectionBar === 'function') updateSelectionBar();
        if (typeof showToast === 'function') showToast('✅ Rectangle created');

        e.stopPropagation();
    }

    mc.addEventListener('pointerdown', _drawPointerDown, true);
    mc.addEventListener('pointermove', _drawPointerMove, true);
    mc.addEventListener('pointerup',   _drawPointerUp,   true);
}

// ─────────────────────────────────────────────────────────────────────────────
// FIX: injectResizeHandles — shapes get independent dx/dy per corner (free),
//      images keep AR-locked resize.  Min size 10 px for both axes.
// ─────────────────────────────────────────────────────────────────────────────
function injectResizeHandles(el, item) {
    if (!el || !item) return;
    // Remove stale handles
    el.querySelectorAll('.resize-handle').forEach(h => h.remove());

    const isShape = item.type === 'shape';
    const handles = [
        { cls: 'nw', style: 'top:-10px;left:-10px;cursor:nw-resize;'  },
        { cls: 'ne', style: 'top:-10px;right:-10px;cursor:ne-resize;' },
        { cls: 'se', style: 'bottom:-10px;right:-10px;cursor:se-resize;' },
        { cls: 'sw', style: 'bottom:-10px;left:-10px;cursor:sw-resize;'  },
    ];

    const mc    = document.getElementById('menu-container');
    const cw    = docV2.canvas ? docV2.canvas.width  : 908;
    const ch    = docV2.canvas ? docV2.canvas.height : 1336;

    handles.forEach(({ cls, style }) => {
        const h = document.createElement('div');
        h.className = 'resize-handle ' + cls;
        h.setAttribute('style', 'display:block;position:absolute;width:20px;height:20px;background:#f1c40f;border:2px solid #000;border-radius:50%;z-index:9999;box-sizing:border-box;' + style);

        let startPx, startPy, startW, startH, startX, startY, AR;

        h.addEventListener('pointerdown', ev => {
            ev.stopPropagation(); ev.preventDefault();
            h.setPointerCapture(ev.pointerId);
            const rect  = mc.getBoundingClientRect();
            const scale = mc.offsetWidth / cw;
            startPx = ev.clientX; startPy = ev.clientY;
            startW  = item.width;  startH  = item.height;
            startX  = item.x;      startY  = item.y;
            AR      = startW / startH;
        });

        h.addEventListener('pointermove', ev => {
            if (!h.hasPointerCapture(ev.pointerId)) return;
            ev.stopPropagation();
            const rect  = mc.getBoundingClientRect();
            const scale = mc.offsetWidth / cw;
            const dx = (ev.clientX - startPx) / scale;
            const dy = (ev.clientY - startPy) / scale;

            if (isShape) {
                // Free resize — each corner moves independently
                if (cls === 'se') {
                    item.width  = Math.max(10, startW + dx);
                    item.height = Math.max(10, startH + dy);
                } else if (cls === 'sw') {
                    const nw = Math.max(10, startW - dx);
                    item.x     = startX + (startW - nw);
                    item.width = nw;
                    item.height = Math.max(10, startH + dy);
                } else if (cls === 'ne') {
                    item.width  = Math.max(10, startW + dx);
                    const nh    = Math.max(10, startH - dy);
                    item.y      = startY + (startH - nh);
                    item.height = nh;
                } else { // nw
                    const nw = Math.max(10, startW - dx);
                    const nh = Math.max(10, startH - dy);
                    item.x  = startX + (startW - nw);
                    item.y  = startY + (startH - nh);
                    item.width  = nw;
                    item.height = nh;
                }
            } else {
                // AR-locked for images
                let delta = (Math.abs(dx) > Math.abs(dy)) ? dx : dy;
                if (cls === 'nw' || cls === 'sw') delta = -delta;
                const nw = Math.max(10, startW + delta);
                const nh = nw / AR;
                if (cls === 'se') {
                    item.width = nw; item.height = nh;
                } else if (cls === 'sw') {
                    item.x = startX + startW - nw;
                    item.width = nw; item.height = nh;
                } else if (cls === 'ne') {
                    item.width = nw;
                    item.y = startY + startH - nh; item.height = nh;
                } else {
                    item.x = startX + startW - nw;
                    item.y = startY + startH - nh;
                    item.width = nw; item.height = nh;
                }
            }
            if (typeof render === 'function') render();
        });

        h.addEventListener('pointerup', ev => {
            h.releasePointerCapture(ev.pointerId);
            if (typeof pushState === 'function') pushState();
        });

        el.appendChild(h);
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// FIX: setLineWidth / setLineCap — update the selected shape item
// ─────────────────────────────────────────────────────────────────────────────
function setLineWidth(w) {
    const item = _getItem();
    if (!item || item.type !== 'shape') return;
    item.height = w;                       // for line shapes height = visual thickness
    item.strokeWidth = 0;                  // thickness is carried by height, not stroke
    const inp = document.getElementById('sel-line-width-custom');
    if (inp) inp.value = w;
    // Update active button highlights
    document.querySelectorAll('#line-width-presets .ctrl-btn').forEach(btn => {
        btn.classList.toggle('active', parseFloat(btn.textContent) === w);
    });
    if (typeof pushState === 'function') pushState();
    if (typeof render    === 'function') render();
}

function setLineCap(cap) {
    const item = _getItem();
    if (!item || item.type !== 'shape') return;
    item.lineCap = cap;
    ['butt','round','square'].forEach(c => {
        const btn = document.getElementById('btn-cap-' + c);
        if (btn) btn.classList.toggle('active', c === cap);
    });
    if (typeof pushState === 'function') pushState();
    if (typeof render    === 'function') render();
}

// ─────────────────────────────────────────────────────────────────────────────
// FIX: updateSelectionBar — correctly shows/hides geo vs text controls and
//      seeds all shape inputs (fill, stroke, radius, outline button) from
//      the correct item properties.
// ─────────────────────────────────────────────────────────────────────────────
(function patchUpdateSelectionBar() {
    const _orig = typeof updateSelectionBar === 'function' ? updateSelectionBar : null;

    window.updateSelectionBar = function() {
        // Run original first if it exists (populates text/image controls)
        if (_orig) _orig();

        const item = _getItem();
        if (!item) return;

        const isShape = item.type === 'shape';
        const isText  = item.type === 'text';
        const isLine  = isShape && (item.height <= 8);

        // Show/hide the two control groups in the Design tab
        const geoCtrl  = document.getElementById('geo-style-ctrls');
        const txtCtrl  = document.getElementById('text-style-ctrls');
        const linePresets = document.getElementById('line-width-presets');
        if (geoCtrl)    geoCtrl.style.display     = isShape ? 'flex' : 'none';
        if (txtCtrl)    txtCtrl.style.display      = isText  ? 'flex' : 'none';
        if (linePresets) linePresets.style.display = isLine  ? 'flex' : 'none';

        if (!isShape) return;

        // Seed fill color picker — item.style.fill is canonical
        const fillEl = document.getElementById('sel-fill-color');
        if (fillEl) {
            const fill = (item.style && item.style.fill) || '#333333';
            fillEl.value = fill === 'transparent' ? '#333333' : fill;
        }

        // Stroke
        const swEl = document.getElementById('sel-stroke-w');
        const scEl = document.getElementById('sel-stroke-c');
        if (swEl) swEl.value = item.strokeWidth || 0;
        if (scEl) scEl.value = item.strokeColor || '#c8a96a';

        // Corner radius
        const radEl = document.getElementById('sel-radius');
        if (radEl) radEl.value = item.cornerRadius || 0;

        // Outline toggle button highlight
        const outlineBtn = document.getElementById('btn-outline-toggle');
        if (outlineBtn) {
            const isOutline = (item.style && item.style.fill) === 'transparent';
            outlineBtn.style.background = isOutline ? '#c8a96a' : '';
        }

        // Line-cap button highlights
        if (isLine && item.lineCap) {
            ['butt','round','square'].forEach(c => {
                const b = document.getElementById('btn-cap-' + c);
                if (b) b.classList.toggle('active', item.lineCap === c);
            });
        }
    };
})();

// ─────────────────────────────────────────────────────────────────────────────
// FIX: render() shape SVG — patch renderElement to use correct property names:
//      fill  = item.style.fill
//      stroke = item.strokeWidth / item.strokeColor
//      radius = item.cornerRadius
//      Also triggers injectResizeHandles for type==='shape'
// ─────────────────────────────────────────────────────────────────────────────
(function patchRenderShape() {
    const _origRender = typeof render === 'function' ? render : null;

    window.render = function() {
        if (_origRender) _origRender();

        // After base render runs, patch any shape elements whose SVG
        // may have used wrong property names.
        (docV2.elements || []).forEach(item => {
            if (item.type !== 'shape') return;
            const domEl = document.querySelector(`[data-id="${item.id}"]`);
            if (!domEl) return;

            const fill   = (item.style && item.style.fill != null) ? item.style.fill : '#c8a96a';
            const sw     = item.strokeWidth  || 0;
            const sc     = item.strokeColor  || '#c8a96a';
            const radius = item.cornerRadius || 0;
            const w      = item.width  || 100;
            const h      = item.height || 100;

            // Rebuild the inner shape SVG with correct values
            const shapeEl = domEl.querySelector('.shape-object') || domEl;
            const isLine  = h <= 8;

            const svgNS = 'http://www.w3.org/2000/svg';
            let svg = domEl.querySelector('svg.shape-svg');
            if (!svg) {
                svg = document.createElementNS(svgNS, 'svg');
                svg.classList.add('shape-svg');
                svg.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;overflow:visible;pointer-events:none;';
                domEl.appendChild(svg);
            }
            svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
            svg.innerHTML = '';

            const shapeType = item.shapeType || 'rect';
            let shapeNode;

            if (shapeType === 'rect' || shapeType === 'line') {
                shapeNode = document.createElementNS(svgNS, 'rect');
                shapeNode.setAttribute('x',      sw / 2);
                shapeNode.setAttribute('y',      sw / 2);
                shapeNode.setAttribute('width',  Math.max(0, w - sw));
                shapeNode.setAttribute('height', Math.max(0, h - sw));
                shapeNode.setAttribute('rx',     radius);
                shapeNode.setAttribute('ry',     radius);
            } else if (shapeType === 'circle' || shapeType === 'ellipse') {
                shapeNode = document.createElementNS(svgNS, 'ellipse');
                shapeNode.setAttribute('cx', w / 2);
                shapeNode.setAttribute('cy', h / 2);
                shapeNode.setAttribute('rx', Math.max(0, w / 2 - sw / 2));
                shapeNode.setAttribute('ry', Math.max(0, h / 2 - sw / 2));
            } else if (shapeType === 'star') {
                shapeNode = document.createElementNS(svgNS, 'polygon');
                const points = _starPoints(w / 2, h / 2, 5, Math.min(w, h) / 2 - sw, Math.min(w, h) / 4);
                shapeNode.setAttribute('points', points);
            } else {
                shapeNode = document.createElementNS(svgNS, 'rect');
                shapeNode.setAttribute('x',      sw / 2);
                shapeNode.setAttribute('y',      sw / 2);
                shapeNode.setAttribute('width',  Math.max(0, w - sw));
                shapeNode.setAttribute('height', Math.max(0, h - sw));
                shapeNode.setAttribute('rx',     radius);
            }

            shapeNode.setAttribute('fill',            fill);
            shapeNode.setAttribute('stroke',          sw > 0 ? sc : 'none');
            shapeNode.setAttribute('stroke-width',    sw);
            svg.appendChild(shapeNode);

            // Re-inject resize handles for selected shape
            if (item.id === (typeof selectedId !== 'undefined' ? selectedId : null)) {
                injectResizeHandles(domEl, item);
            }
        });
    };

    function _starPoints(cx, cy, points, outerR, innerR) {
        let pts = [];
        for (let i = 0; i < points * 2; i++) {
            const r   = (i % 2 === 0) ? outerR : innerR;
            const ang = (Math.PI / points) * i - Math.PI / 2;
            pts.push(`${cx + r * Math.cos(ang)},${cy + r * Math.sin(ang)}`);
        }
        return pts.join(' ');
    }
})();

// ─────────────────────────────────────────────────────────────────────────────
// INIT — auto-load viewer settings after page ready
// ─────────────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(loadGlobalSettings, 1200);
});
