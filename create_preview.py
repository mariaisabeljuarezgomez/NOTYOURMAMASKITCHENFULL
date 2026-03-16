from PIL import Image
import os

img_path = "menu-bg.png"
out_path = "menu-bg-preview.jpg"

if os.path.exists(img_path):
    with Image.open(img_path) as img:
        width, height = img.size
        print(f"Original: {width}x{height}")
        target_width = 908
        target_height = 1336
        print(f"Resizing to: {target_width}x{target_height}")
        preview = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        preview = preview.convert("RGB")
        preview.save(out_path, "JPEG", quality=82, optimize=True)
        print(f"Saved preview to {out_path}")
        print(f"Preview size: {os.path.getsize(out_path) / 1024:.2f} KB")
else:
    print(f"Error: {img_path} not found")
