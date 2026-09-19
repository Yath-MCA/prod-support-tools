from __future__ import annotations


def attrs_for_uniqueness(attrs: dict | None) -> dict:
    if not attrs:
        return {}
    out = {}
    for key, value in attrs.items():
        if key == "xlink:href" or (isinstance(key, str) and key.endswith("}href")):
            continue
        out[key] = value
    return out


def unique_key(match: dict) -> tuple:
    tag = match.get("tag", "")
    normalized = attrs_for_uniqueness(match.get("attributes") or {})
    return (tag, frozenset(normalized.items()))


def annotate_unique_matches(matches: list) -> list:
    """Annotate in place: is_unique + unique_group_size. Keep first of each key."""
    if not matches:
        return matches

    groups: dict[tuple, list] = {}
    order: list[tuple] = []
    for match in matches:
        key = unique_key(match)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(match)

    for key in order:
        members = groups[key]
        size = len(members)
        for index, match in enumerate(members):
            match["is_unique"] = index == 0
            match["unique_group_size"] = size
    return matches


def filter_unique_matches(matches: list) -> list:
    return [m for m in matches if m.get("is_unique")]


def annotate_selector_results(all_selector_results: list) -> list:
    for selector_data in all_selector_results or []:
        scan_results = selector_data.get("scan_results") or {}
        for _path, data in scan_results.items():
            if not data.get("ok", True):
                continue
            matches = data.get("matches") or []
            if matches:
                annotate_unique_matches(matches)
    return all_selector_results
