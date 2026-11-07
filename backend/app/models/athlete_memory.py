from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class AthleteMemory:
    id: int | None

    category: str

    memory_text: str

    source: str

    confidence: float | None

    is_active: bool

    created_at: datetime

    updated_at: datetime

    status: str = "unreviewed"
    observed_on: str | None = None
    confirmed_at: datetime | None = None
    source_turn_id: str | None = None
    source_quote: str | None = None
    supersedes_id: int | None = None
