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
