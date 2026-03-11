from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag


# Han ideographs plus compatibility ideographs.
CJK_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]")


@dataclass
class CJKCharNode:
    char: str
    path: str
    index_in_node: int
    in_ins: bool
    in_del: bool
    original_node_text: str
    node_html: str


def extract_cjk_chars(html: str) -> list[CJKCharNode]:
    soup = BeautifulSoup(html, "lxml")
    root = soup.body or soup
    rows: list[CJKCharNode] = []

    def build_child_tag_positions(parent: Tag) -> dict[Tag, int]:
        counts: dict[str, int] = {}
        result: dict[Tag, int] = {}
        for child in parent.children:
            if isinstance(child, Tag):
                name = child.name
                counts[name] = counts.get(name, 0) + 1
                result[child] = counts[name]
        return result

    def current_path(parent_path: str, tag: Tag, tag_index: Optional[int]) -> str:
        if tag_index is None:
            return parent_path
        part = f"{tag.name}[{tag_index}]"
        if not parent_path:
            return part
        return f"{parent_path} > {part}"

    def walk(node: Tag, path: str, in_ins: bool, in_del: bool) -> None:
        tag_positions = build_child_tag_positions(node)

        for child in node.children:
            if isinstance(child, NavigableString):
                text = str(child)
                if not text.strip():
                    continue

                for idx, char in enumerate(text):
                    if CJK_RE.match(char):
                        parent_tag = child.parent if isinstance(child.parent, Tag) else None
                        node_html = str(parent_tag) if parent_tag else text
                        rows.append(
                            CJKCharNode(
                                char=char,
                                path=path,
                                index_in_node=idx,
                                in_ins=in_ins,
                                in_del=in_del,
                                original_node_text=text,
                                node_html=node_html,
                            )
                        )
            elif isinstance(child, Tag):
                tag_index = tag_positions.get(child)
                child_path = current_path(path, child, tag_index)
                walk(
                    child,
                    child_path,
                    in_ins or child.name.lower() == "ins",
                    in_del or child.name.lower() == "del",
                )

    start_path = "body" if root.name == "body" else root.name or "document"
    walk(root, start_path, False, False)
    return rows
