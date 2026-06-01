"""
Input sanitization utilities.
Strips HTML tags and control characters from user-supplied strings.
"""
import re

# Matches any HTML/XML tag
_TAG_RE = re.compile(r"<[^>]+>")
# Matches script/style blocks including content
_SCRIPT_RE = re.compile(r"<(script|style)[^>]*>.*?</(script|style)>", re.IGNORECASE | re.DOTALL)
# Null bytes and other dangerous control chars (keep newlines/tabs)
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize(value: str, max_length: int | None = None) -> str:
    """
    Strip HTML tags, script/style blocks, and control characters.
    Optionally truncate to max_length.
    """
    value = _SCRIPT_RE.sub("", value)
    value = _TAG_RE.sub("", value)
    value = _CONTROL_RE.sub("", value)
    value = value.strip()
    if max_length is not None:
        value = value[:max_length]
    return value

