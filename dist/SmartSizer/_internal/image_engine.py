import os
import io
from PIL import Image, UnidentifiedImageError

# --- Application Configuration ---
SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff')

# --- Image Processing Logic ---
def process_image(input_path, output_path, max_size_kb, scale_percent, force_format="Auto"):
    try:
        img = Image.open(input_path)
        img_format = img.format if img.format else "JPEG"
        
        if force_format != "Auto":
            img_format = force_format
            output_path = os.path.splitext(output_path)[0] + f".{force_format.lower()}"
            if img_format in ["JPEG", "WEBP"]:
                img = img.convert("RGB")

        elif img_format == "PNG" and max_size_kb > 0:
            img_format = "JPEG"
            img = img.convert("RGB")
            output_path = os.path.splitext(output_path)[0] + ".jpg"

        if scale_percent < 100:
            new_width = int(img.width * (scale_percent / 100))
            new_height = int(img.height * (scale_percent / 100))
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        if max_size_kb > 0:
            quality = 95
            while quality >= 10:
                buffer = io.BytesIO()
                img.save(buffer, format=img_format, quality=quality)
                size_kb = len(buffer.getvalue()) / 1024

                if size_kb <= max_size_kb:
                    with open(output_path, "wb") as f:
                        f.write(buffer.getvalue())
                    return True, f"Optimized to {size_kb:.1f}KB", output_path
                quality -= 5
            return False, "Could not compress below target size", None
            
        else:
            img.save(output_path, format=img_format, quality=95)
            return True, "Dimensions resized successfully", output_path

    except UnidentifiedImageError:
        return False, "Invalid or corrupted image file", None
    except Exception as e:
        return False, str(e), None