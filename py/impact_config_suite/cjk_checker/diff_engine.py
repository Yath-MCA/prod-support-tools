from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from .parser import CJKCharNode


@dataclass
class DiffRow:
    element_path: str
    original: str
    revised: str
    status: str
    char_index: int
    original_snippet: str
    revised_snippet: str


def compare_cjk_chars(original_chars: list[CJKCharNode], revised_chars: list[CJKCharNode]) -> tuple[list[DiffRow], dict]:
    rows: list[DiffRow] = []

    a = [item.char for item in original_chars]
    b = [item.char for item in revised_chars]
    matcher = SequenceMatcher(None, a, b)

    def add_row(
        path: str,
        original: str,
        revised: str,
        status: str,
        char_index: int,
        original_snippet: str,
        revised_snippet: str,
    ) -> None:
        rows.append(
            DiffRow(
                element_path=path,
                original=original,
                revised=revised,
                status=status,
                char_index=char_index,
                original_snippet=original_snippet,
                revised_snippet=revised_snippet,
            )
        )

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for left, right in zip(original_chars[i1:i2], revised_chars[j1:j2]):
                add_row(
                    path=left.path,
                    original=left.char,
                    revised=right.char,
                    status="OK",
                    char_index=left.index_in_node,
                    original_snippet=left.node_html,
                    revised_snippet=right.node_html,
                )

        elif tag == "delete":
            for left in original_chars[i1:i2]:
                status = "Tracked Delete" if left.in_del else "Deleted"
                add_row(
                    path=left.path,
                    original=left.char,
                    revised="-",
                    status=status,
                    char_index=left.index_in_node,
                    original_snippet=left.node_html,
                    revised_snippet="",
                )

        elif tag == "insert":
            for right in revised_chars[j1:j2]:
                status = "Tracked Insert" if right.in_ins else "Inserted"
                add_row(
                    path=right.path,
                    original="-",
                    revised=right.char,
                    status=status,
                    char_index=right.index_in_node,
                    original_snippet="",
                    revised_snippet=right.node_html,
                )

        elif tag == "replace":
            left_items = original_chars[i1:i2]
            right_items = revised_chars[j1:j2]
            max_len = max(len(left_items), len(right_items))

            for idx in range(max_len):
                left = left_items[idx] if idx < len(left_items) else None
                right = right_items[idx] if idx < len(right_items) else None

                if left and right:
                    tracked = left.in_del or right.in_ins
                    status = "Untracked Change" if not tracked else ("Tracked Delete" if left.in_del else "Tracked Insert")
                    add_row(
                        path=left.path,
                        original=left.char,
                        revised=right.char,
                        status=status,
                        char_index=left.index_in_node,
                        original_snippet=left.node_html,
                        revised_snippet=right.node_html,
                    )
                elif left:
                    status = "Tracked Delete" if left.in_del else "Untracked Change"
                    add_row(
                        path=left.path,
                        original=left.char,
                        revised="-",
                        status=status,
                        char_index=left.index_in_node,
                        original_snippet=left.node_html,
                        revised_snippet="",
                    )
                elif right:
                    status = "Tracked Insert" if right.in_ins else "Untracked Change"
                    add_row(
                        path=right.path,
                        original="-",
                        revised=right.char,
                        status=status,
                        char_index=right.index_in_node,
                        original_snippet="",
                        revised_snippet=right.node_html,
                    )

    summary = {
        "total_original": len(original_chars),
        "total_revised": len(revised_chars),
        "inserted": sum(1 for row in rows if row.status == "Inserted"),
        "deleted": sum(1 for row in rows if row.status == "Deleted"),
        "tracked_insert": sum(1 for row in rows if row.status == "Tracked Insert"),
        "tracked_delete": sum(1 for row in rows if row.status == "Tracked Delete"),
        "untracked_changes": sum(1 for row in rows if row.status == "Untracked Change"),
        "ok": sum(1 for row in rows if row.status == "OK"),
    }

    return rows, summary
