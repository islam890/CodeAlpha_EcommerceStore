from pathlib import Path

from django.core.exceptions import ValidationError


MAX_IMAGE_SIZE = 5 * 1024 * 1024
IMAGE_SIGNATURES = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".webp": (b"RIFF",),
}


def validate_image_upload(upload):
    if upload.size > MAX_IMAGE_SIZE:
        raise ValidationError("Images must be 5 MB or smaller.")
    extension = Path(upload.name).suffix.lower()
    signatures = IMAGE_SIGNATURES.get(extension)
    if not signatures:
        raise ValidationError("Use a JPG, JPEG, PNG, or WebP image.")
    current_position = upload.tell()
    try:
        header = upload.read(12)
    finally:
        upload.seek(current_position)
    valid_signature = any(header.startswith(signature) for signature in signatures)
    if extension == ".webp":
        valid_signature = valid_signature and header[8:12] == b"WEBP"
    if not valid_signature:
        raise ValidationError("The uploaded file is not a valid image.")
