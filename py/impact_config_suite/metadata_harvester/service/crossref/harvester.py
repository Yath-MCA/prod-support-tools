from __future__ import annotations

from typing import Optional, Tuple

import requests
from loguru import logger

from metadata_harvester.service.crossref import db


def naive_geo_parser(affiliation_str: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parses comma-delimited strings right-to-left to safely categorize
    country, district/state, and city components.
    """
    if not affiliation_str:
        return None, None, None

    parts = [p.strip() for p in affiliation_str.split(",") if p.strip()]

    city = None
    district = None
    country = None

    if len(parts) >= 1:
        country = parts[-1]
    if len(parts) >= 2:
        district = parts[-2]
    if len(parts) >= 3:
        city = parts[-3]

    return city, district, country


def harvest_crossref_task(token: str, email: str, rows: int, limit: int) -> None:
    """Streams records continuously using Crossref deep-paging cursors."""
    logger.info("Initializing active background metadata streaming session...")

    base_url = "https://api.crossref.org/works"

    headers = {
        "User-Agent": f"InternalAutoStructurePipeline/1.0 (mailto:{email})",
        "Crossref-Plus-API-Token": f"Bearer {token}",
    }

    cursor = "*"
    total_harvested = 0

    while total_harvested < limit:
        params = {
            "filter": "has-affiliation:true",
            "rows": min(rows, limit - total_harvested),
            "cursor": cursor,
        }

        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=30)
            if response.status_code != 200:
                logger.error(f"Crossref service responded with HTTP structural code: {response.status_code}")
                break

            data = response.json()
            items = data.get("message", {}).get("items", [])
            next_cursor = data.get("message", {}).get("next-cursor")

            if not items or next_cursor == cursor:
                logger.info("Encountered terminal end of active data matching filters.")
                break

            cursor = next_cursor

            for item in items:
                doi = item.get("DOI")
                for author in item.get("author", []):
                    for aff in author.get("affiliation", []):
                        raw_str = aff.get("name")
                        if not raw_str:
                            continue

                        city, district, country = naive_geo_parser(raw_str)
                        db.insert_record(raw_str, city, district, country, doi)

            total_harvested += len(items)
            logger.info(f"Synchronized and committed {total_harvested} cumulative records.")

        except Exception as e:
            logger.exception(f"Fatal anomaly encountered in batch frame processing: {e}")
            break

    logger.info("Crossref harvest process complete.")
