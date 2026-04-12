<<<<<<< SEARCH
async function loadAiGallery() {
    const grid = document.getElementById('ai-gallery-images');
    grid.innerHTML = '';
    const aiAssets = (docV2.assets || []).filter(a =>
        a.id && (a.id.startsWith('asset_ai') || (a.name || '').toUpperCase().includes('AI'))
    );
    if (aiAssets.length === 0) {
        grid.innerHTML = '<div data-placeholder="true" style="color:#555;font-size:10px;grid-column:1/-1;text-align:center;padding:12px;">Generated images appear here.<br>Use "Save to Assets" in AI Studio.</div>';
        return;
    }
    aiAssets.forEach(asset => {
        const url = (asset.storage || {}).originalUrl || (asset.storage || {}).previewUrl || '';
        const wrap = document.createElement('div');
        wrap.className = 'asset-container';
        wrap.style.position = 'relative';
        wrap.innerHTML = `
            <img src="${url}" class="ls-asset-item"
                onclick="addFromAsset('${asset.id}', '${url}')"
                title="${asset.name || 'AI Image'}"
                onerror="this.closest('.asset-container').style.opacity='0.3'">
            <button class="asset-del-btn" onclick="deleteAiGalleryItem('${asset.id}', event)">✕</button>
        `;
        grid.appendChild(wrap);
    });
}
=======
async function loadAiGallery() {
  // ── VIDEOS ──
  const videoContainer = document.getElementById('ai-gallery-videos');
  videoContainer.innerHTML = '<div style="color:#555;font-size:10px;text-align:center;padding:8px;">Loading...</div>';
  try {
    const vRes = await fetch('/api/video-history');
    const vData = await vRes.json();
    const allVideos = [
      ...(vData.hero || []).map(url => ({ slot: 'hero', url })),
      ...(vData.left || []).map(url =>  ({ slot: 'left',  url })),
      ...(vData.right || []).map(url => ({ slot: 'right', url }))
    ];
    if (allVideos.length === 0) {
      videoContainer.innerHTML = '<div style="color:#555;font-size:10px;text-align:center;padding:12px;">No videos yet.</div>';
    } else {
      videoContainer.innerHTML = '';
      allVideos.forEach(({ slot, url }) => {
        const card = document.createElement('div');
        card.style.cssText = 'background:#1a1a1a;border:1px solid #2a2a2a;border-radius:6px;padding:6px;';
        card.innerHTML = `
          <video src="${url}" style="width:100%;border-radius:4px;" muted playsinline preload="metadata"></video>
          <div style="font-size:9px;color:#888;margin:4px 0 4px;text-transform:uppercase;font-weight:700;">📌 ${slot} slot</div>
          <div style="display:flex;gap:4px;">
            <button onclick="applyVideoToSlot('hero','${url}')" class="btn-ui accent" style="flex:1;font-size:9px;padding:4px;">🎬 Hero</button>
            <button onclick="applyVideoToSlot('left','${url}')" class="btn-ui" style="flex:1;font-size:9px;padding:4px;">⬅️ Left</button>
            <button onclick="applyVideoToSlot('right','${url}')" class="btn-ui" style="flex:1;font-size:9px;padding:4px;">➡️ Right</button>
          </div>`;
        videoContainer.appendChild(card);
      });
    }
  } catch(e) {
    videoContainer.innerHTML = `<div style="color:#e74c3c;font-size:10px;text-align:center;padding:8px;">Error: ${e.message}</div>`;
  }

  // ── IMAGES ──
  const imgContainer = document.getElementById('ai-gallery-images');
  const placeholder = imgContainer.querySelector('[data-placeholder]');
  if (placeholder) placeholder.remove();
  try {
    const iRes = await fetch('/api/image-history');
    const iData = await iRes.json();
    if (!iData.images || iData.images.length === 0) {
      imgContainer.innerHTML = '<div data-placeholder="true" style="color:#555;font-size:10px;grid-column:1/-1;text-align:center;padding:12px;">No AI images yet.</div>';
    } else {
      imgContainer.innerHTML = '';
      iData.images.forEach(img => {
        const wrap = document.createElement('div');
        wrap.className = 'asset-container';
        wrap.innerHTML = `
          <img src="${img.url}" class="ls-asset-item" title="${img.name}"
               onclick="addFromAsset('${img.id}', '${img.url}')">
          <button class="asset-del-btn" onclick="deleteAiGalleryImage('${img.id}')">✕</button>`;
        imgContainer.appendChild(wrap);
      });
    }
  } catch(e) { /* silent fail for images */ }
}
>>>>>>> REPLACE
