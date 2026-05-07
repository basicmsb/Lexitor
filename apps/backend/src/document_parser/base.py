from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ParserError(Exception):
    """Raised when a document cannot be parsed."""


@dataclass
class ParsedItem:
    """A single item extracted from a document (a row, a paragraph, a section)."""

    position: int
    text: str
    label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    """Result of parsing an uploaded file."""

    items: list[ParsedItem]
    metadata: dict[str, Any] = field(default_factory=dict)
