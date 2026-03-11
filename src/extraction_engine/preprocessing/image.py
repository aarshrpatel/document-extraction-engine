import io
import base64

from PIL import Image, ImageEnhance, ImageFilter


def preprocess_image(img: Image.Image) -> Image.Image:
    """Apply preprocessing to improve OCR and extraction quality.

    Steps: convert to RGB, auto-contrast, slight sharpen.
    """
    # Ensure RGB
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Auto-contrast enhancement
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.3)

    # Slight sharpen to improve text clarity
    img = img.filter(ImageFilter.SHARPEN)

    return img


def image_to_base64(img: Image.Image, format: str = "PNG") -> str:
    """Convert PIL Image to base64 string for API consumption."""
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def image_to_bytes(img: Image.Image, format: str = "PNG") -> bytes:
    """Convert PIL Image to bytes."""
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    return buffer.getvalue()


def get_media_type(format: str = "PNG") -> str:
    """Get MIME type for image format."""
    return {
        "PNG": "image/png",
        "JPEG": "image/jpeg",
        "JPG": "image/jpeg",
        "TIFF": "image/tiff",
    }.get(format.upper(), "image/png")
