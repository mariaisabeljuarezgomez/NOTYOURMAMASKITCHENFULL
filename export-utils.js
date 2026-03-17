// ============================================================
// export-utils.js — DO NOT EDIT OR DELETE THIS FILE
// This file is intentionally separate from index.html and
// build_app.py so it is NEVER overwritten by code generation.
// It contains the 300 DPI PNG metadata injection for exportPng().
// ============================================================

function crc32(data) {
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let j = 0; j < 8; j++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
    table[i] = c;
  }
  let crc = 0xFFFFFFFF;
  for (let i = 0; i < data.length; i++) crc = table[(crc ^ data[i]) & 0xFF] ^ (crc >>> 8);
  return (crc ^ 0xFFFFFFFF) >>> 0;
}

async function inject300DpiAndDownload(blob, filename) {
  const PPM = 11811; // 300 DPI in pixels per meter
  const arrayBuffer = await blob.arrayBuffer();
  const bytes = new Uint8Array(arrayBuffer);

  // Build pHYs chunk: length(4) + type(4) + data(9) + crc(4) = 21 bytes
  const phys = new Uint8Array(21);
  // Length = 9
  phys[0]=0; phys[1]=0; phys[2]=0; phys[3]=9;
  // Chunk type = "pHYs"
  phys[4]=112; phys[5]=72; phys[6]=89; phys[7]=115;
  // X pixels per unit (PPM big-endian)
  phys[8]=(PPM>>24)&0xFF; phys[9]=(PPM>>16)&0xFF; phys[10]=(PPM>>8)&0xFF; phys[11]=PPM&0xFF;
  // Y pixels per unit (PPM big-endian)
  phys[12]=(PPM>>24)&0xFF; phys[13]=(PPM>>16)&0xFF; phys[14]=(PPM>>8)&0xFF; phys[15]=PPM&0xFF;
  // Unit = meter (1)
  phys[16]=1;
  // CRC over type + data
  const crcVal = crc32(phys.slice(4, 17));
  phys[17]=(crcVal>>24)&0xFF; phys[18]=(crcVal>>16)&0xFF; phys[19]=(crcVal>>8)&0xFF; phys[20]=crcVal&0xFF;

  // Insert pHYs chunk after PNG signature (8 bytes) + IHDR chunk (25 bytes) = byte 33
  const before = bytes.slice(0, 33);
  const after  = bytes.slice(33);
  const merged = new Uint8Array(before.length + phys.length + after.length);
  merged.set(before, 0);
  merged.set(phys, before.length);
  merged.set(after, before.length + phys.length);

  const fixedBlob = new Blob([merged], { type: 'image/png' });
  const a = document.createElement('a');
  a.download = filename;
  a.href = URL.createObjectURL(fixedBlob);
  a.click();
}
