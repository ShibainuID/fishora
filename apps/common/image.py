from io import BytesIO

from PIL import Image

from apps.contracts import ImageValidationError

ALLOWED_CONTENT_TYPES = ("image/jpeg", "image/png")


def validate_image_bytes(data: bytes, content_type: str | None, max_bytes: int) -> Image.Image:
    """Trust-boundary gate: content type, size, then decodability, before any inference.

    Preprocessing (exif transpose, RGB, resize/pad, normalize) belongs to the
    generated wrapper only; nothing here touches pixel values.
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ImageValidationError(415, f"unsupported content type {content_type!r}; only image/jpeg and image/png are accepted")
    if len(data) > max_bytes:
        raise ImageValidationError(413, f"image exceeds the {max_bytes} byte limit")
    try:
        with Image.open(BytesIO(data)) as probe:
            probe.verify()
    except Exception:
        raise ImageValidationError(400, "image data is unreadable") from None
    # verify() invalidates the handle; reopen for actual reading.
    return Image.open(BytesIO(data))