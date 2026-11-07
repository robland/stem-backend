import io

from PIL import Image


def image_bytes(fmt="JPEG", size=(400, 300), color=(255, 255, 255), exif=None):
    buffer = io.BytesIO()
    image = Image.new("RGB", size, color)
    kwargs = {"exif": exif} if exif is not None else {}
    image.save(buffer, format=fmt, **kwargs)
    return buffer.getvalue()


def pdf_bytes(pages=1, size=(595, 842)):
    buffer = io.BytesIO()
    images = [Image.new("RGB", size, (255, 255, 255 - i)) for i in range(pages)]
    images[0].save(buffer, format="PDF", save_all=True, append_images=images[1:])
    return buffer.getvalue()


def extraction_response(*exercises):
    return {"is_exercise_document": True, "exercises": list(exercises)}


def extracted(statement="Exercice 1\nDévelopper $(x+2)^2$.", subject="maths", level="3e", chapter_hint=None):
    return {"statement": statement, "subject": subject, "level": level, "chapter_hint": chapter_hint}
