from __future__ import annotations

import time
from typing import List

import requests
from loguru import logger

from metadata_harvester.service.config import settings
from metadata_harvester.service.geo.sources.base import LocationRecord

ROR_URL = "https://api.ror.org/v2/organizations"


class RorSource:
    """ROR (Research Organization Registry) -- free, no-auth prefix search."""

    name = "ror"

    def fetch_letter(self, letter: str, email: str) -> List[LocationRecord]:
        records: List[LocationRecord] = []
        headers = {"User-Agent": f"GeoHarvester/2.0 (mailto:{email})"}

        for page in range(1, settings.ror_max_pages + 1):
            params = {"query.advanced": f"names.value:{letter}*", "page": page}
            try:
                resp = requests.get(
                    ROR_URL,
                    params=params,
                    headers=headers,
                    timeout=settings.request_timeout_seconds,
                )
                if resp.status_code != 200:
                    logger.error(f"[ROR:{letter}] HTTP {resp.status_code}")
                    break

                data = resp.json()
                items = data.get("items", [])
                if not items:
                    break

                for org in items:
                    ror_id = org.get("id")
                    if not ror_id:
                        continue

                    names = org.get("names", [])
                    display_name = next(
                        (n["value"] for n in names if "ror_display" in n.get("types", [])),
                        names[0]["value"] if names else None,
                    )

                    locations = org.get("locations", [])
                    if not locations:
                        continue

                    geo = locations[0].get("geonames_details", {}) or {}
                    city = geo.get("name")
                    district = geo.get("country_subdivision_name")
                    country = geo.get("country_name")
                    if not country:
                        continue

                    records.append(
                        LocationRecord(
                            source=self.name,
                            source_id=ror_id,
                            name=display_name,
                            city=city,
                            district=district,
                            country=country,
                        )
                    )

                time.sleep(settings.ror_page_delay_seconds)  # be polite to the free endpoint
            except Exception as e:
                logger.exception(f"[ROR:{letter}] error: {e}")
                break

        return records
