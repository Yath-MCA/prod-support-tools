from __future__ import annotations

from typing import List

import requests
from loguru import logger

from metadata_harvester.service.config import settings
from metadata_harvester.service.geo.sources.base import LocationRecord

OPENALEX_URL = "https://api.openalex.org/autocomplete/institutions"


class OpenAlexSource:
    """OpenAlex autocomplete -- free, no-auth prefix search with a pre-formatted 'hint'."""

    name = "openalex"

    def fetch_letter(self, letter: str, email: str) -> List[LocationRecord]:
        records: List[LocationRecord] = []
        params = {"search": letter, "mailto": email}

        try:
            resp = requests.get(
                OPENALEX_URL, params=params, timeout=settings.request_timeout_seconds
            )
            if resp.status_code != 200:
                logger.error(f"[OpenAlex:{letter}] HTTP {resp.status_code}")
                return records

            data = resp.json()
            for item in data.get("results", []):
                oa_id = item.get("id")
                name = item.get("display_name") or ""
                if not oa_id or not name.upper().startswith(letter):
                    continue

                hint = item.get("hint") or ""
                parts = [p.strip() for p in hint.split(",") if p.strip()]
                city = parts[0] if len(parts) >= 1 else None
                district = parts[1] if len(parts) == 3 else None
                country = parts[-1] if parts else None
                if not country:
                    continue

                records.append(
                    LocationRecord(
                        source=self.name,
                        source_id=oa_id,
                        name=name,
                        city=city,
                        district=district,
                        country=country,
                    )
                )
        except Exception as e:
            logger.exception(f"[OpenAlex:{letter}] error: {e}")

        return records
