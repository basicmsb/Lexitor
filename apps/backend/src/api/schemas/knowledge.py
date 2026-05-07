from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SearchHitPublic(BaseModel):
    klasa: str
    predmet: str
    page: int | None
    chunk_index: int
    text: str
    score: float
    pdf_url: str | None
    odluka_datum: str | None
    year: str | None


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHitPublic]


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    limit: int = Field(default=5, ge=1, le=20)
    year: str | None = None
    source: Literal["zjn", "dkom", "vus", "eu"] | None = None


class IndexedSource(BaseModel):
    source: str
    klasa: str
    predmet: str
    narucitelj: str | None = None
    vrsta: str | None = None
    year: str | None = None
    odluka_datum: str | None = None
    pdf_url: str | None = None
    article_number: int | None = None


class SourcesResponse(BaseModel):
    items: list[IndexedSource]
    total: int
