"""utils to models."""

from typing import Optional


def normalize(string_data: Optional[str]) -> str:
    """Remove all problematic characters."""
    if not isinstance(string_data, str):
        return ""

    replacements = (
        ("á", "a"),
        ("é", "e"),
        ("í", "i"),
        ("ó", "o"),
        ("ú", "u"),
        ("ñ", "n"),
        ("ń", "n"),
        (".", ""),
        ("'", ""),
    )
    cleaned = string_data.lower()
    for char1, char2 in replacements:
        cleaned = cleaned.replace(char1, char2)

    cleaned = cleaned.strip()
    return cleaned
