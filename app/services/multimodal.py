"""URL extraction and pretrained image OCR for multimodal claim analysis."""

from html.parser import HTMLParser
from io import BytesIO
import re
from urllib.parse import urlparse

import httpx
from PIL import Image


class _ArticleTextParser(HTMLParser):
    _ignored_tags = {"script", "style", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.meta_description = ""
        self.text_parts: list[str] = []
        self._ignored_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._ignored_tags:
            self._ignored_depth += 1
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            attributes = dict(attrs)
            if attributes.get("name", "").lower() == "description":
                self.meta_description = attributes.get("content", "").strip()

    def handle_endtag(self, tag: str) -> None:
        if tag in self._ignored_tags and self._ignored_depth:
            self._ignored_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        clean = " ".join(data.split())
        if not clean or self._ignored_depth:
            return
        if self._in_title:
            self.title_parts.append(clean)
        else:
            self.text_parts.append(clean)


def fetch_url_text(url: str, *, timeout: float = 20.0, max_chars: int = 50_000) -> str:
    """Fetch a public web page and return its title plus readable text."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("url must be an absolute http or https URL.")
    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            headers={"User-Agent": "SignalCheck/0.1"},
            timeout=timeout,
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise RuntimeError("The URL could not be fetched.") from error
    content_type = response.headers.get("content-type", "").lower()
    if "text/html" not in content_type:
        raise ValueError("The URL does not contain an HTML article.")
    parser = _ArticleTextParser()
    parser.feed(response.text)
    title = " ".join(parser.title_parts)
    body = " ".join(parser.text_parts)
    description = " ".join(parser.meta_description.split())
    extracted = " ".join(part for part in (title, description, body) if part).strip()
    if len(extracted) < 30:
        raise ValueError("The URL did not contain enough readable text.")
    return extracted[:max_chars]


def extract_image_text(image_bytes: bytes) -> str:
    """Extract printed text with the pretrained TrOCR model."""
    if not image_bytes:
        raise ValueError("image must not be empty.")
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception as error:
        raise ValueError("The uploaded file is not a valid image.") from error

    try:
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        processor = _get_trocr_processor(TrOCRProcessor, VisionEncoderDecoderModel)
        model = _get_trocr_model(VisionEncoderDecoderModel)
        pixel_values = processor(images=image, return_tensors="pt").pixel_values
        generated_ids = model.generate(pixel_values, max_new_tokens=128)
        text = _clean_ocr_text(
            processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        )
    except (ImportError, OSError, RuntimeError) as error:
        raise RuntimeError(
            "Image OCR is unavailable. The pretrained TrOCR model could not be loaded."
        ) from error
    if len(text) < 3:
        raise ValueError("No readable claim text was found in the image.")
    return text


def _clean_ocr_text(text: str) -> str:
    """Remove common TrOCR punctuation artifacts without rewriting the claim."""
    cleaned = " ".join(text.split()).strip()
    cleaned = re.sub(r"\s+([,.;!?])", r"\1", cleaned)
    return re.sub(r"\s+[@#]\s*\d+%?\s*$", "", cleaned).strip()


_trocr_processor = None
_trocr_model = None


def _get_trocr_processor(processor_type, model_type):
    global _trocr_processor
    if _trocr_processor is None:
        _trocr_processor = processor_type.from_pretrained(
            "microsoft/trocr-base-printed"
        )
    return _trocr_processor


def _get_trocr_model(model_type):
    global _trocr_model
    if _trocr_model is None:
        _trocr_model = model_type.from_pretrained("microsoft/trocr-base-printed")
        _trocr_model.eval()
    return _trocr_model
