from __future__ import annotations

import heapq
import threading
from typing import Dict, List, Tuple

from loguru import logger

from metadata_harvester.service.geo import db
from metadata_harvester.service.geo.sources.base import Source


def worker_loop(
    worker_id: int,
    heap: List[Tuple[int, str]],
    heap_lock: threading.Lock,
    sources: Dict[str, Source],
    email: str,
) -> None:
    """Each worker always claims the currently least-covered letter."""
    while True:
        with heap_lock:
            if not heap:
                return
            count, letter = heapq.heappop(heap)

        new_total = 0
        for source_name, source in sources.items():
            if db.is_letter_completed(source_name, letter):
                continue

            records = source.fetch_letter(letter, email)
            inserted = sum(1 for record in records if db.insert_record(record, letter))
            db.mark_progress(source_name, letter, inserted, completed=True)
            new_total += inserted
            logger.info(f"[Worker-{worker_id}] {source_name}:{letter} -> {inserted} new record(s)")

        with heap_lock:
            all_done = all(db.is_letter_completed(s, letter) for s in sources)
            if not all_done:
                heapq.heappush(heap, (count + new_total, letter))


def run_harvest(sources: Dict[str, Source], email: str, num_workers: int) -> None:
    logger.info(
        f"Starting dynamic alphabetical harvest with {num_workers} workers "
        f"across sources: {list(sources)}..."
    )
    counts = db.get_alpha_counts()
    heap: List[Tuple[int, str]] = [(counts[letter], letter) for letter in db.ALPHABET]
    heapq.heapify(heap)
    heap_lock = threading.Lock()

    threads = [
        threading.Thread(target=worker_loop, args=(i, heap, heap_lock, sources, email), daemon=True)
        for i in range(num_workers)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    logger.info("Alphabetical harvest complete across all sources (A-Z).")
