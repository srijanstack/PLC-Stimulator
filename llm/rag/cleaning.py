"""
Text cleaning and normalization for Rockwell Automation technical documentation.

Preserves critical industrial identifiers, instruction names, tag naming conventions,
addresses, operands, and ladder diagram syntax while removing extraction artifacts.
"""

from __future__ import annotations

import re


def clean_text(text: str) -> str:
    """Normalize extracted text while preserving technical content and instruction syntax."""
    if not text:
        return ""

    # 1. Replace Windows / carriage return newlines with standard newline
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Fix hyphenated line breaks (e.g., "infor-\nmation" -> "information"),
    # but do NOT merge hyphens in instruction codes or publication IDs like "1756-RM003"
    cleaned = re.sub(r"([a-zA-Z]{3,})-\n([a-zA-Z]{3,})", r"\1\2", cleaned)

    # 3. Normalize non-breaking spaces and irregular whitespace characters
    cleaned = cleaned.replace("\u00a0", " ").replace("\u200b", "")

    # 4. Collapse runs of more than two blank lines into a double newline
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # 5. Collapse multiple horizontal spaces/tabs into a single space, preserving newlines
    lines = []
    for line in cleaned.split("\n"):
        stripped = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(stripped)

    return "\n".join(lines).strip()

