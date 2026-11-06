"""Contrôle et préparation des documents envoyés (images, PDF) avant l'appel LLM."""

import io

import pypdfium2 as pdfium
from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError

from llm.clients import ImageInput

from .models import Upload

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
# Côté le plus long envoyé au LLM : lisible pour l'écriture manuscrite, coût en tokens maîtrisé.
LLM_IMAGE_MAX_SIDE = 2048
MAX_IMAGE_PIXELS = 40_000_000


class DocumentError(Exception):
    """Document refusé ; le message s'adresse à l'élève."""


def detect_file_type(data):
    """Type déduit du contenu (jamais de l'extension ni du Content-Type fournis par le client)."""
    if data.startswith(b"%PDF-"):
        _open_pdf(data).close()
        return Upload.FileType.PDF
    _open_image(data)
    return Upload.FileType.IMAGE


def to_llm_images(data, file_type):
    """Pages du document en JPEG redimensionnés, orientés, sans métadonnées EXIF (GPS, appareil)."""
    if file_type == Upload.FileType.PDF:
        pdf = _open_pdf(data)
        try:
            return [_render_pdf_page(pdf[index]) for index in range(len(pdf))]
        finally:
            pdf.close()
    return [_normalize(_open_image(data))]


def _open_image(data):
    try:
        with Image.open(io.BytesIO(data)) as probe:
            image_format = probe.format
            width, height = probe.size
            probe.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError):
        raise DocumentError("Fichier illisible : envoie une photo (JPEG, PNG, WebP) ou un PDF.")
    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise DocumentError("Format non pris en charge : envoie une photo (JPEG, PNG, WebP) ou un PDF.")
    if width * height > MAX_IMAGE_PIXELS:
        raise DocumentError("Image trop grande.")
    # verify() rend l'image inutilisable : on la rouvre.
    return Image.open(io.BytesIO(data))


def _open_pdf(data):
    try:
        pdf = pdfium.PdfDocument(data)
    except pdfium.PdfiumError:
        raise DocumentError("PDF illisible ou protégé par un mot de passe.")
    if len(pdf) == 0:
        pdf.close()
        raise DocumentError("Le PDF est vide.")
    if len(pdf) > settings.UPLOAD_MAX_PDF_PAGES:
        pdf.close()
        raise DocumentError(f"PDF trop long : {settings.UPLOAD_MAX_PDF_PAGES} pages maximum.")
    return pdf


def _render_pdf_page(page):
    width, height = page.get_size()
    scale = min(LLM_IMAGE_MAX_SIDE / max(width, height), 4)
    return _normalize(page.render(scale=scale).to_pil())


def _normalize(image):
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((LLM_IMAGE_MAX_SIDE, LLM_IMAGE_MAX_SIDE))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return ImageInput(data=buffer.getvalue(), mime_type="image/jpeg")
