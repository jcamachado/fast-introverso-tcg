import os
from typing import Optional


def card_name_from_filename(filename: str) -> str:
    basename = os.path.basename(filename.replace("\\", "/"))
    name = os.path.splitext(basename)[0]
    name = "".join(character for character in name if character.isprintable()).strip()
    if not name:
        raise ValueError("An image filename is required to name the card.")
    return name[:100]


def is_jpeg_upload(content_type: Optional[str], content: bytes) -> bool:
    return content_type == "image/jpeg" and content.startswith(b"\xff\xd8\xff")
