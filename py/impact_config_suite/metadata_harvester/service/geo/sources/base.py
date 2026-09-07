from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol


@dataclass(frozen=True)
class LocationRecord:
    """A single parsed institution/affiliation location, before DB insertion."""

    source: str
    source_id: str
    name: Optional[str]
    city: Optional[str]
    district: Optional[str]
    country: Optional[str]


class Source(Protocol):
    """Shared shape for every geo data source."""

    name: str

    def fetch_letter(self, letter: str, email: str) -> List[LocationRecord]:
        """Fetch and parse all available records whose name starts with `letter`.

        Deduplication against what's already stored happens later, at
        insert time (see geo.db.insert_record) -- sources only fetch and
        parse, they never touch the database.
        """
        ...
