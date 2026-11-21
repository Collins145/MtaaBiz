"""Validators for uploaded business images (size and dimensions)."""

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from PIL import Image

MAX_FILE_MB = 5
MIN_DIMENSION = 200   # px, avoids tiny/blurry uploads
MAX_DIMENSION = 6000  # px, guards against decompression-bomb style uploads


@deconstructible
class ImageUploadValidator:
    """Validate uploaded images: type, file size and pixel dimensions."""

    def __init__(self, max_mb=MAX_FILE_MB, min_dimension=MIN_DIMENSION, max_dimension=MAX_DIMENSION):
        self.max_mb = max_mb
        self.min_dimension = min_dimension
        self.max_dimension = max_dimension

    def __call__(self, value):
        if not value:
            return

        max_bytes = self.max_mb * 1024 * 1024
        if value.size > max_bytes:
            raise ValidationError(
                f"Image is too large ({value.size / (1024 * 1024):.1f} MB). "
                f"Maximum allowed size is {self.max_mb} MB."
            )

        try:
            with Image.open(value) as img:
                width, height = img.size
                fmt = (img.format or "").upper()
        except Exception as exc:
            raise ValidationError("Upload a valid image file (PNG, JPEG, WebP or GIF).") from exc

        if fmt not in ("PNG", "JPEG", "WEBP", "GIF"):
            raise ValidationError("Unsupported image format. Use PNG, JPEG, WebP or GIF.")

        if width < self.min_dimension or height < self.min_dimension:
            raise ValidationError(
                f"Image is too small ({width}x{height}px). "
                f"Minimum dimension is {self.min_dimension}px."
            )

        if width > self.max_dimension or height > self.max_dimension:
            raise ValidationError(
                f"Image is too large ({width}x{height}px). "
                f"Maximum dimension is {self.max_dimension}px."
            )

        value.seek(0)  # rewind after reading, so the file can still be saved

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.max_mb == other.max_mb
            and self.min_dimension == other.min_dimension
            and self.max_dimension == other.max_dimension
        )
