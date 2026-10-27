"""Lightweight image signals used before advanced visual models are added."""

from dataclasses import dataclass
from io import BytesIO

from PIL import Image


@dataclass(frozen=True)
class ImageAssessment:
    width: int
    height: int
    format: str
    has_metadata: bool
    perceptual_hash: str


def assess_image(content: bytes) -> ImageAssessment:
    if not content:
        raise ValueError("image must not be empty.")
    try:
        with Image.open(BytesIO(content)) as image:
            pixels = image.convert("L").resize((8, 8))
            values = list(pixels.getdata())
            average = sum(values) / len(values)
            image_hash = "".join("1" if value >= average else "0" for value in values)
            return ImageAssessment(
                width=image.width,
                height=image.height,
                format=image.format or "unknown",
                has_metadata=bool(image.getexif()),
                perceptual_hash=f"{int(image_hash, 2):016x}",
            )
    except (OSError, ValueError) as error:
        raise ValueError("uploaded content is not a valid image.") from error
