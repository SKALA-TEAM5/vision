import io

from PIL import Image


def load_rgb_image(image_bytes: bytes) -> Image.Image:
    try:
        return Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise ValueError("invalid image file") from exc
