"""Validation for user-supplied image uploads."""

from fastapi import HTTPException, UploadFile

CHUNK_SIZE = 64 * 1024

# Signatures are checked against the bytes themselves. The client-declared
# Content-Type is a hint, never the decision.
_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"BM", "image/bmp"),
)

ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/gif", "image/bmp", "image/webp", "image/heic"}


def sniff_image_mime(data: bytes) -> str | None:
    """Return the real image type of `data`, or None when it is not an image."""
    for signature, mime in _SIGNATURES:
        if data.startswith(signature):
            return mime
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in (b"heic", b"heix", b"mif1"):
        return "image/heic"
    return None


def reject_oversized_body(content_length: str | None, limit: int) -> None:
    """Refuse before reading when the client already told us the body is too big."""
    if content_length is None:
        return
    try:
        declared = int(content_length)
    except ValueError:
        return
    if declared > limit:
        raise HTTPException(
            status_code=413,
            detail=f"Image must be {limit // (1024 * 1024)} MB or smaller",
        )


async def read_image_upload(file: UploadFile, limit: int) -> tuple[bytes, str]:
    """Read an upload with a hard byte cap and verify it really is an image.

    Reads incrementally and aborts as soon as the cap is exceeded, so an oversized
    upload never materialises in memory in full.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=413,
                detail=f"Image must be {limit // (1024 * 1024)} MB or smaller",
            )
        chunks.append(chunk)

    data = b"".join(chunks)
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")

    detected = sniff_image_mime(data)
    if detected is None or detected not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Upload a supported image file (PNG, JPEG, GIF, BMP, WebP, or HEIC)",
        )

    return data, detected
