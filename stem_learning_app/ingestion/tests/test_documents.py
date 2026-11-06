import io

import pytest
from PIL import Image

from ingestion.documents import LLM_IMAGE_MAX_SIDE, DocumentError, detect_file_type, to_llm_images
from ingestion.models import Upload

from .factories import image_bytes, pdf_bytes

ORIENTATION_TAG = 0x0112
GPS_TAG = 0x8825


@pytest.mark.parametrize("fmt", ["JPEG", "PNG", "WEBP"])
def test_detects_supported_images(fmt):
    assert detect_file_type(image_bytes(fmt)) == Upload.FileType.IMAGE


def test_detects_pdf():
    assert detect_file_type(pdf_bytes()) == Upload.FileType.PDF


@pytest.mark.parametrize(
    "data",
    [b"pas une image", image_bytes("GIF"), image_bytes("JPEG")[:100], b"%PDF-1.4 tronque"],
    ids=["texte", "gif", "image-tronquee", "pdf-invalide"],
)
def test_rejects_invalid_documents(data):
    with pytest.raises(DocumentError):
        detect_file_type(data)


def test_rejects_too_many_pdf_pages(settings):
    settings.UPLOAD_MAX_PDF_PAGES = 2

    with pytest.raises(DocumentError, match="2 pages maximum"):
        detect_file_type(pdf_bytes(pages=3))


def test_image_is_resized_and_reencoded_as_jpeg():
    [result] = to_llm_images(image_bytes("PNG", size=(4000, 1000)), Upload.FileType.IMAGE)

    image = Image.open(io.BytesIO(result.data))
    assert result.mime_type == "image/jpeg"
    assert image.format == "JPEG"
    assert image.size == (LLM_IMAGE_MAX_SIDE, LLM_IMAGE_MAX_SIDE // 4)


def test_photo_orientation_is_applied_and_exif_removed():
    exif = Image.Exif()
    exif[ORIENTATION_TAG] = 6  # photo prise téléphone tourné
    exif[GPS_TAG] = {1: "N"}

    [result] = to_llm_images(image_bytes(size=(300, 100), exif=exif), Upload.FileType.IMAGE)

    image = Image.open(io.BytesIO(result.data))
    assert image.size == (100, 300)
    assert not image.getexif()


def test_pdf_pages_become_images():
    results = to_llm_images(pdf_bytes(pages=2), Upload.FileType.PDF)

    assert len(results) == 2
    assert max(Image.open(io.BytesIO(results[0].data)).size) == LLM_IMAGE_MAX_SIDE
