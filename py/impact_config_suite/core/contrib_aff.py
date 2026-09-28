"""
contrib_aff.py

Affiliations and author-notes reporting scoped to <article-meta> only
(JATS article front metadata). Body / back / whole-file scans are never used.

Locked selectors (direct children only, under article-meta):
  /article-meta/contrib-group
  /article-meta/contrib-group/aff  -> location "inside_contrib_group"
  /article-meta/aff                -> location "outside_contrib_group"
  /article-meta/author-notes       -> author-notes under article-meta
Nested <aff> inside <contrib> is NOT selected.

The existing *_elements_vN.html report remains the inventory for elements
*inside* <contrib-group>. This module writes a separate report family:

  {client}_{shortcode}_aff_v{SCRIPT_VERSION}.html   shortcode rollup
  {client}_{shortcode}_aff_v{SCRIPT_VERSION}.csv    flat per-node rows
  {client}_aff_unique_v{SCRIPT_VERSION}.html        client-wise unique patterns
                                                    across shortcodes in the
                                                    current extract session

Hierarchy: docid-wise detail -> shortcode rollup -> client unique rollup.

Public API (imported by contrib_extractor):
    extract_article_meta_block, extract_aff_nodes, extract_after_cg_nodes
    (compat alias), inventory_node, attach_aff_to_row, attach_after_cg_to_row
    (compat alias), build_aff_inventory, build_aff_report, build_aff_csv,
    update_client_aff_unique, build_client_aff_unique_report,
    reset_aff_session, get_client_aff_paths

CSV columns:
    client, shortcode, file_id_docid, node_kind, node_index, node_id,
    location, root_attrs, inner_tags, inner_attr_pairs, text_len, empty,
    parse_error, raw_excerpt

Uses the same entity/PI-friendly fragment parse style as parse_group when
possible; on failure keeps raw XML + error note.
"""

from __future__ import annotations

import csv
import html
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from html.entities import name2codepoint
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Local parse helpers (avoid circular import with contrib_extractor)
# ---------------------------------------------------------------------------

_AFF_RE = re.compile(r"<aff\b(?:[^>]*>[\s\S]*?</aff\s*>|[^>]*/>)", re.I)
_AUTHOR_NOTES_RE = re.compile(
    r"<author-notes\b(?:[^>]*>[\s\S]*?</author-notes\s*>|[^>]*/>)", re.I
)
_ARTICLE_META_RE = re.compile(
    r"<article-meta\b[^>]*>[\s\S]*?</article-meta\s*>", re.I
)
_CONTRIB_GROUP_RE = re.compile(
    r"<contrib-group\b(?:[^>]*>[\s\S]*?</contrib-group\s*>|[^>]*/>)", re.I
)
_NAMED_ENTITY_RE = re.compile(r"&([A-Za-z][A-Za-z0-9]*);")
_XML_ENTITIES = {"amp", "lt", "gt", "quot", "apos"}
_NS_DECLS = (
    'xmlns:xlink="http://www.w3.org/1999/xlink" '
    'xmlns:mml="http://www.w3.org/1998/Math/MathML" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
)
_NS_PREFIX = {
    "http://www.w3.org/1999/xlink": "xlink",
    "http://www.w3.org/1998/Math/MathML": "mml",
    "http://www.w3.org/2001/XMLSchema-instance": "xsi",
    "http://www.w3.org/XML/1998/namespace": "xml",
}
_PI = ET.ProcessingInstruction

LOC_INSIDE = "inside_contrib_group"
LOC_OUTSIDE = "outside_contrib_group"

# Session accumulator: client -> unique-pattern buckets (shortcodes in this batch)
_CLIENT_AFF_ACC: dict[str, dict] = {}


def reset_aff_session() -> None:
    """Clear client-wise unique accumulator (call with reset_session_report_dir)."""
    global _CLIENT_AFF_ACC
    _CLIENT_AFF_ACC = {}


def _fix_entity(m: re.Match) -> str:
    name = m.group(1)
    if name in _XML_ENTITIES:
        return m.group(0)
    cp = name2codepoint.get(name)
    return chr(cp) if cp else f"&amp;{name};"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _attr_label(key: str) -> str:
    if key.startswith("{"):
        ns, _, name = key[1:].partition("}")
        return f"{_NS_PREFIX.get(ns, 'ns')}:{name}"
    return key


def _parse_fragment(raw: str) -> ET.Element:
    """Parse one aff / author-notes fragment; returns synthetic <root> wrapper."""
    wrapped = f"<root {_NS_DECLS}>{_NAMED_ENTITY_RE.sub(_fix_entity, raw)}</root>"
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_pis=True))
    return ET.fromstring(wrapped, parser=parser)


def extract_article_meta_block(text: str) -> str:
    """Return the first <article-meta>...</article-meta> block, or ''."""
    if not text:
        return ""
    m = _ARTICLE_META_RE.search(text)
    return m.group(0) if m else ""


def _elem_to_raw(el: ET.Element) -> str:
    """Serialize one element to XML text for inventory_node."""
    return ET.tostring(el, encoding="unicode")


def _direct_children(parent: ET.Element, name: str) -> list[ET.Element]:
    out = []
    for kid in list(parent):
        if isinstance(kid.tag, str) and _local(kid.tag) == name:
            out.append(kid)
    return out


def _find_article_meta_el(meta_raw: str) -> ET.Element | None:
    """Parse article-meta fragment; return the article-meta element."""
    try:
        root = _parse_fragment(meta_raw)
    except ET.ParseError:
        return None
    for kid in root:
        if isinstance(kid.tag, str) and _local(kid.tag) == "article-meta":
            return kid
    return None


def _empty_extract() -> dict:
    return {
        "aff_nodes": [],
        "author_notes_nodes": [],
        "aff_count": 0,
        "author_notes_count": 0,
        "aff_inside_count": 0,
        "aff_outside_count": 0,
        "author_notes_inside_count": 0,
        "author_notes_outside_count": 0,
        # Compat aliases (v10 names = outside-of-cg counts within article-meta)
        "aff_after_count": 0,
        "author_notes_after_count": 0,
    }


def extract_aff_nodes(text: str) -> dict:
    """Collect aff / author-notes via locked article-meta direct-child paths.

    Selectors (XPath-style, first article-meta only):
      /article-meta/contrib-group/aff  -> location inside_contrib_group
      /article-meta/aff                -> location outside_contrib_group
      /article-meta/author-notes       -> under article-meta (outside_contrib_group)

    Nested <aff> inside <contrib> is not selected. Body/back ignored.
    Each element is visited once — no double-count.
    """
    meta = extract_article_meta_block(text or "")
    if not meta:
        return _empty_extract()

    meta_el = _find_article_meta_el(meta)
    if meta_el is None:
        return _empty_extract()

    aff_nodes: list[dict] = []
    notes_nodes: list[dict] = []

    # /article-meta/contrib-group/aff  and  /article-meta/aff  and  /article-meta/author-notes
    for kid in list(meta_el):
        if not isinstance(kid.tag, str):
            continue
        name = _local(kid.tag)
        if name == "contrib-group":
            for aff_el in _direct_children(kid, "aff"):
                node = inventory_node(_elem_to_raw(aff_el), "aff", len(aff_nodes))
                node["location"] = LOC_INSIDE
                aff_nodes.append(node)
        elif name == "aff":
            node = inventory_node(_elem_to_raw(kid), "aff", len(aff_nodes))
            node["location"] = LOC_OUTSIDE
            aff_nodes.append(node)
        elif name == "author-notes":
            node = inventory_node(_elem_to_raw(kid), "author-notes", len(notes_nodes))
            node["location"] = LOC_OUTSIDE
            notes_nodes.append(node)

    aff_inside = sum(1 for n in aff_nodes if n.get("location") == LOC_INSIDE)
    aff_outside = sum(1 for n in aff_nodes if n.get("location") == LOC_OUTSIDE)
    notes_inside = sum(1 for n in notes_nodes if n.get("location") == LOC_INSIDE)
    notes_outside = sum(1 for n in notes_nodes if n.get("location") == LOC_OUTSIDE)

    return {
        "aff_nodes": aff_nodes,
        "author_notes_nodes": notes_nodes,
        "aff_count": len(aff_nodes),
        "author_notes_count": len(notes_nodes),
        "aff_inside_count": aff_inside,
        "aff_outside_count": aff_outside,
        "author_notes_inside_count": notes_inside,
        "author_notes_outside_count": notes_outside,
        # Compat: "after" historically meant outside contrib-group
        "aff_after_count": aff_outside,
        "author_notes_after_count": notes_outside,
    }


def extract_after_cg_nodes(text: str) -> dict:
    """Compat alias for extract_aff_nodes (article-meta scoped, v12)."""
    return extract_aff_nodes(text)


def inventory_node(raw: str, tag: str, index: int = 0) -> dict:
    """Per-node inventory: attrs, inner tags/attrs, emptiness, optional parse error."""
    node: dict[str, Any] = {
        "tag": tag,
        "node_index": index,
        "raw": raw,
        "attrs": {},
        "inner_tags": Counter(),
        "inner_attrs": defaultdict(Counter),  # "elem/attr" -> Counter(values)
        "empty": False,
        "text_len": 0,
        "has_mixed": False,
        "parse_error": None,
        "node_id": "",
        "inner_sig": (),
        "root_attr_sig": (),
        "location": "",
    }
    try:
        root = _parse_fragment(raw)
        el = None
        for kid in root:
            if isinstance(kid.tag, str) and _local(kid.tag) == tag:
                el = kid
                break
        if el is None:
            # self-wrapping edge: first element child
            for kid in root:
                if isinstance(kid.tag, str):
                    el = kid
                    break
        if el is None:
            node["parse_error"] = "no root element after parse"
            node["empty"] = True
            return node

        attrs = {_attr_label(k): v for k, v in el.attrib.items()}
        node["attrs"] = attrs
        node["node_id"] = attrs.get("id", "")
        node["root_attr_sig"] = tuple(sorted(f"{k}={v}" for k, v in attrs.items()))

        texts: list[str] = []
        if (el.text or "").strip():
            texts.append((el.text or "").strip())

        def walk(parent: ET.Element):
            for kid in parent:
                if kid.tag is _PI or not isinstance(kid.tag, str):
                    if (kid.tail or "").strip():
                        texts.append((kid.tail or "").strip())
                    continue
                name = _local(kid.tag)
                node["inner_tags"][name] += 1
                for k, v in kid.attrib.items():
                    node["inner_attrs"][f"{name}/{_attr_label(k)}"][v] += 1
                has_child = any(isinstance(c.tag, str) for c in kid)
                has_text = bool((kid.text or "").strip()) or any(
                    (c.tail or "").strip() for c in kid
                )
                if (kid.text or "").strip():
                    texts.append((kid.text or "").strip())
                walk(kid)
                if (kid.tail or "").strip():
                    texts.append((kid.tail or "").strip())
                if not has_child and not has_text:
                    pass  # counted at rollup via empty flag on root

        walk(el)
        joined = " ".join(texts)
        node["text_len"] = len(joined)
        node["has_mixed"] = bool(texts) and bool(node["inner_tags"])
        node["empty"] = not node["inner_tags"] and not joined
        node["inner_sig"] = tuple(sorted(node["inner_tags"].keys()))
    except ET.ParseError as e:
        node["parse_error"] = str(e)
        node["empty"] = not bool((raw or "").strip())
        # best-effort tag peek for sig
        m = re.search(r"<([A-Za-z][\w.-]*)\b", raw or "")
        if m:
            node["inner_sig"] = ()
    return node


def attach_aff_to_row(row: dict, source_text: str | None) -> None:
    """Mutate row with article-meta-scoped aff / author-notes fields."""
    data = extract_aff_nodes(source_text or "")
    row["aff_nodes"] = data["aff_nodes"]
    row["author_notes_nodes"] = data["author_notes_nodes"]
    row["aff_count"] = data["aff_count"]
    row["author_notes_count"] = data["author_notes_count"]
    row["aff_inside_count"] = data["aff_inside_count"]
    row["aff_outside_count"] = data["aff_outside_count"]
    row["author_notes_inside_count"] = data["author_notes_inside_count"]
    row["author_notes_outside_count"] = data["author_notes_outside_count"]
    row["aff_after_count"] = data["aff_after_count"]
    row["author_notes_after_count"] = data["author_notes_after_count"]


def attach_after_cg_to_row(row: dict, source_text: str | None) -> None:
    """Compat alias for attach_aff_to_row."""
    attach_aff_to_row(row, source_text)


def _empty_node_fields(row: dict) -> None:
    row.setdefault("aff_nodes", [])
    row.setdefault("author_notes_nodes", [])
    row.setdefault("aff_count", 0)
    row.setdefault("author_notes_count", 0)
    row.setdefault("aff_inside_count", 0)
    row.setdefault("aff_outside_count", 0)
    row.setdefault("author_notes_inside_count", 0)
    row.setdefault("author_notes_outside_count", 0)
    row.setdefault("aff_after_count", 0)
    row.setdefault("author_notes_after_count", 0)


def build_aff_inventory(rows: list[dict]) -> dict:
    """Aggregate article-meta aff / author-notes across good rows for one shortcode."""
    aff_inner: dict = {}
    aff_root_attrs: dict = defaultdict(Counter)  # attr -> Counter(values)
    aff_specific_use: Counter = Counter()
    aff_country_attr: Counter = Counter()
    notes_inner: dict = {}
    notes_root_attrs: dict = defaultdict(Counter)
    doc_summaries: list[dict] = []
    samples: list[dict] = []
    ids = {}
    n_aff = 0
    n_notes = 0
    n_aff_inside = 0
    n_aff_outside = 0
    n_notes_inside = 0
    n_notes_outside = 0
    loc_counts: Counter = Counter()

    def entry(bucket: dict, name: str) -> dict:
        return bucket.setdefault(
            name,
            {
                "files": set(),
                "occ": 0,
                "attrs": defaultdict(Counter),
                "empty": 0,
            },
        )

    for r in rows:
        _empty_node_fields(r)
        docid = r["docid"]
        ids[docid] = r.get("file_id") or ""
        affs = r.get("aff_nodes") or []
        notes = r.get("author_notes_nodes") or []
        for kind, nodes in (("aff", affs), ("author-notes", notes)):
            for n in nodes:
                if len(samples) >= 80:
                    break
                samples.append(
                    {
                        "docid": docid,
                        "file_id": ids[docid],
                        "kind": kind,
                        "location": n.get("location") or "",
                        "node_index": n.get("node_index", 0),
                        "raw": n.get("raw") or "",
                    }
                )
        n_aff += len(affs)
        n_notes += len(notes)
        inside_a = sum(1 for n in affs if n.get("location") == LOC_INSIDE)
        outside_a = sum(1 for n in affs if n.get("location") == LOC_OUTSIDE)
        inside_n = sum(1 for n in notes if n.get("location") == LOC_INSIDE)
        outside_n = sum(1 for n in notes if n.get("location") == LOC_OUTSIDE)
        n_aff_inside += inside_a
        n_aff_outside += outside_a
        n_notes_inside += inside_n
        n_notes_outside += outside_n
        for n in affs:
            loc_counts[n.get("location") or "?"] += 1
        for n in notes:
            loc_counts[f"notes:{n.get('location') or '?'}"] += 1
        tag_set = sorted({t for n in affs for t in (n.get("inner_tags") or {})})
        doc_summaries.append(
            {
                "docid": docid,
                "file_id": ids[docid],
                "aff_count": len(affs),
                "aff_inside": inside_a,
                "aff_outside": outside_a,
                "author_notes_count": len(notes),
                "author_notes_inside": inside_n,
                "author_notes_outside": outside_n,
                "inner_tag_set": tag_set,
                "preview_rel": r.get("preview_rel") or "",
            }
        )
        for n in affs:
            for name, cnt in (n.get("inner_tags") or {}).items():
                e = entry(aff_inner, name)
                e["files"].add(docid)
                e["occ"] += cnt
            for pair, vals in (n.get("inner_attrs") or {}).items():
                # pair like "country/country"
                elem, _, attr = pair.partition("/")
                if elem in aff_inner or True:
                    e = entry(aff_inner, elem)
                    for v, c in vals.items():
                        e["attrs"][attr][v] += c
                        if elem == "country" and attr == "country":
                            aff_country_attr[v] += c
                        if attr == "specific-use":
                            aff_specific_use[v] += c
            for k, v in (n.get("attrs") or {}).items():
                aff_root_attrs[k][v] += 1
                if k == "specific-use":
                    aff_specific_use[v] += 1
            if n.get("empty"):
                # attribute emptiness on a synthetic "" entry
                e = entry(aff_inner, "(aff-root)")
                e["files"].add(docid)
                e["occ"] += 1
                e["empty"] += 1
            elif not n.get("inner_tags"):
                pass
        for n in notes:
            for name, cnt in (n.get("inner_tags") or {}).items():
                e = entry(notes_inner, name)
                e["files"].add(docid)
                e["occ"] += cnt
            for pair, vals in (n.get("inner_attrs") or {}).items():
                elem, _, attr = pair.partition("/")
                e = entry(notes_inner, elem)
                for v, c in vals.items():
                    e["attrs"][attr][v] += c
            for k, v in (n.get("attrs") or {}).items():
                notes_root_attrs[k][v] += 1

    return {
        "aff_inner": aff_inner,
        "aff_root_attrs": aff_root_attrs,
        "aff_specific_use": aff_specific_use,
        "aff_country_attr": aff_country_attr,
        "notes_inner": notes_inner,
        "notes_root_attrs": notes_root_attrs,
        "doc_summaries": doc_summaries,
        "samples": samples,
        "total": len(rows),
        "n_aff": n_aff,
        "n_notes": n_notes,
        "n_aff_inside": n_aff_inside,
        "n_aff_outside": n_aff_outside,
        "n_notes_inside": n_notes_inside,
        "n_notes_outside": n_notes_outside,
        "loc_counts": loc_counts,
        "ids": ids,
        "unique_inner": sorted(aff_inner.keys()),
    }


def _ce():
    """Lazy import to reuse page/esc helpers without circular import at load."""
    from core import contrib_extractor as ce

    return ce


def _flags_for(e: dict, total: int, rare_ok: bool, rare_max: int) -> list:
    out = []
    n = len(e["files"])
    if n < total:
        out.append(("partial", "partial", f"in {n} of {total} files"))
    if rare_ok and n <= rare_max:
        out.append(("rare", "rare", f"only in {n} file{'' if n == 1 else 's'}"))
    if e.get("empty"):
        every = e["empty"] == e["occ"]
        out.append(
            (
                "empty",
                "empty" if every else "some empty",
                f"{e['empty']} of {e['occ']} empty-ish roots",
            )
        )
    return out


def _section_inner_table(title: str, bucket: dict, total: int, ids: dict, ce) -> str:
    rare_ok = total > 2 * ce.RARE_MAX
    rows = []
    for name, e in sorted(bucket.items(), key=lambda x: x[0].lower()):
        fl = _flags_for(e, total, rare_ok, ce.RARE_MAX)
        rows.append(
            f'<tr><td><code class="tok">&lt;{ce.esc(name)}&gt;</code></td>'
            f'<td>{ce._files_cell(e["files"], total, ids)}</td><td>{e["occ"]}</td>'
            f'<td>{ce._flags_html(fl)}</td>'
            f'<td>{ce._attrs_html(e["attrs"], rare_ok)}</td></tr>'
        )
    if not rows:
        rows.append('<tr><td colspan="5"><span class="none">none found</span></td></tr>')
    return (
        f"<h3>{ce.esc(title)} - {len(bucket)} unique inner tags in {total} files</h3>"
        '<table class="elem"><tr><th>Element</th><th>Files</th><th>Occurrences</th>'
        "<th>Flags</th><th>Attributes</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def _counter_block(title: str, counter: Counter, ce) -> str:
    if not counter:
        return f"<h3>{ce.esc(title)}</h3><p><span class='none'>none</span></p>"
    parts = []
    for v, n in counter.most_common(80):
        shown = ce.esc(v) or "(empty)"
        parts.append(f"<div><code class='tok'>{shown}</code> <small>&times;{n}</small></div>")
    more = f"<div>... +{len(counter) - 80} more</div>" if len(counter) > 80 else ""
    return f"<h3>{ce.esc(title)} - {len(counter)} distinct</h3>" + "".join(parts) + more


def _root_attrs_block(title: str, attrs: dict, ce) -> str:
    if not attrs:
        return f"<h3>{ce.esc(title)}</h3><p><span class='none'>none</span></p>"
    # reuse _attrs_html shape: attrs is dict[str, Counter]
    return (
        f"<h3>{ce.esc(title)}</h3>"
        + ce._attrs_html(attrs, rare_ok=True)
    )


def _combined_id_text(file_id: str, docid: str) -> str:
    """Return the single-column CSV representation of a file/doc identifier."""
    if file_id and docid:
        return f"{file_id} ({docid})"
    return file_id or docid


def _combined_id_cell(file_id: str, docid: str, ce) -> str:
    """Render file-id and docid together, matching the elements report style."""
    if file_id and docid:
        return f"<div>{ce.esc(file_id)} <small>{ce.esc(docid)}</small></div>"
    return f"<div>{ce.esc(file_id or docid)}</div>"


def _doc_summary_table(summaries: list[dict], ce) -> str:
    rows = []
    for s in summaries:
        tags = ", ".join(f"&lt;{ce.esc(t)}&gt;" for t in s["inner_tag_set"][:12]) or "-"
        if len(s["inner_tag_set"]) > 12:
            tags += f" +{len(s['inner_tag_set']) - 12}"
        prev = ""
        if s.get("preview_rel"):
            prev = f'<a href="{ce.esc_attr(s["preview_rel"])}">preview</a>'
        aff_break = (
            f"{s['aff_count']}"
            f" <small>(in {s.get('aff_inside', 0)} / out {s.get('aff_outside', 0)})</small>"
        )
        notes_break = (
            f"{s['author_notes_count']}"
            f" <small>(in {s.get('author_notes_inside', 0)} / "
            f"out {s.get('author_notes_outside', 0)})</small>"
        )
        rows.append(
            f"<tr><td>{_combined_id_cell(s['file_id'], s['docid'], ce)}</td>"
            f"<td>{aff_break}</td><td>{notes_break}</td>"
            f"<td>{tags}</td><td>{prev or '-'}</td></tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="5"><span class="none">no documents</span></td></tr>')
    return (
        "<h3>Docid-wise summary</h3>"
        '<table class="elem"><tr><th>File-id / Docid</th><th>#aff</th>'
        "<th>#author-notes</th><th>Sample inner tags (aff)</th><th>Preview</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def _sample_preview(raw: str, ce) -> str:
    """Render one aff/author-notes body as HTML for the report preview pane."""
    try:
        root = _parse_fragment(raw)
        node = next((child for child in root if isinstance(child.tag, str)), None)
        return ce.render(node) if node is not None else ce.esc(raw)
    except Exception:
        return ce.esc(raw)


def _sample_bodies_table(samples: list[dict], ce) -> str:
    rows = []
    for sample in samples:
        raw = sample.get("raw") or ""
        preview = _sample_preview(raw, ce) or '<span class="none">(empty)</span>'
        ident = _combined_id_cell(sample.get("file_id", ""), sample.get("docid", ""), ce)
        kind = ce.esc(sample.get("kind", ""))
        loc = ce.esc(sample.get("location", ""))
        rows.append(
            f"<tr><td>{ident}</td><td>{kind}<br><small>{loc}</small></td>"
            f'<td><div class="v-preview pv">{preview}</div>'
            f'<div class="v-raw"><pre class="raw">{ce.esc(raw)}</pre></div></td></tr>'
        )
    if not rows:
        rows.append('<tr><td colspan="3"><span class="none">no aff or author-notes bodies</span></td></tr>')
    return (
        "<h3>Sample aff / author-notes bodies</h3>"
        '<p class="legend">Use the header toggle to switch between rendered HTML and raw XML.</p>'
        '<table class="elem"><tr><th>File-id / Docid</th><th>Kind / location</th>'
        "<th>Body</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def build_aff_report(
    client: str, shortcode: str, inv: dict, report_dir: Path
) -> Path:
    """Write {client}_{shortcode}_aff_vN.html under report_dir."""
    ce = _ce()
    chips = [
        ("Client", client, ""),
        ("Project shortcode", shortcode, ""),
        ("Documents", inv["total"], ""),
        ("Aff total", inv["n_aff"], ""),
        ("Aff inside cg", inv.get("n_aff_inside", 0), ""),
        ("Aff outside cg", inv.get("n_aff_outside", 0), ""),
        ("Author-notes total", inv["n_notes"], ""),
        ("Notes inside cg", inv.get("n_notes_inside", 0), ""),
        ("Notes outside cg", inv.get("n_notes_outside", 0), ""),
        ("Unique aff inner tags", len(inv["aff_inner"]), ""),
        ("Script version", f"v{ce.SCRIPT_VERSION}", ""),
        ("Generated", ce.now(), ""),
    ]
    legend = (
        '<div class="legend">Scoped to &lt;article-meta&gt; only. Affiliations and '
        "author-notes inside &lt;contrib-group&gt; "
        f'(location=<code>{LOC_INSIDE}</code>) and elsewhere in article-meta '
        f'(location=<code>{LOC_OUTSIDE}</code>). Body/back ignored. '
        "Inside-group element inventory remains in the elements report. Flags: "
        '<span class="flag partial">partial</span> / '
        '<span class="flag rare">rare</span> / '
        '<span class="flag empty">empty</span>.</div>'
    )
    body = (
        '<div class="elems">'
        + _section_inner_table(
            "Aff (article-meta) - inner tags",
            inv["aff_inner"],
            inv["total"],
            inv["ids"],
            ce,
        )
        + _root_attrs_block("Aff root attributes", inv["aff_root_attrs"], ce)
        + _counter_block("Aff specific-use values", inv["aff_specific_use"], ce)
        + _counter_block("Aff country/@country values", inv["aff_country_attr"], ce)
        + _section_inner_table(
            "Author-notes (article-meta) - inner tags",
            inv["notes_inner"],
            inv["total"],
            inv["ids"],
            ce,
        )
        + _root_attrs_block("Author-notes root attributes", inv["notes_root_attrs"], ce)
        + _doc_summary_table(inv["doc_summaries"], ce)
        + _sample_bodies_table(inv.get("samples", []), ce)
        + "</div>"
    )
    out = report_dir / f"{ce.safe_name(client)}_{ce.safe_name(shortcode)}_aff_v{ce.SCRIPT_VERSION}.html"
    ce.ensure_dir(out.parent)
    out.write_text(
        ce.page(
            f"{client} / {shortcode} - aff / author-notes (article-meta)",
            chips,
            legend + body,
            toggle=True,
            legend=False,
        ),
        encoding="utf-8",
    )
    return out


def _attrs_flat(attrs: dict) -> str:
    if not attrs:
        return ""
    return "; ".join(f"{k}={v}" for k, v in sorted(attrs.items()))


def _inner_tags_flat(tags: Counter) -> str:
    if not tags:
        return ""
    return "; ".join(f"{k}:{n}" for k, n in sorted(tags.items()))


def _inner_attr_pairs_flat(inner_attrs: dict) -> str:
    parts = []
    for pair, vals in sorted(inner_attrs.items()):
        for v, n in vals.most_common():
            parts.append(f"{pair}={v}x{n}")
    return "; ".join(parts)


def build_aff_csv(
    client: str, shortcode: str, rows: list[dict], report_dir: Path
) -> Path:
    """Write flat CSV of each article-meta aff / author-notes node."""
    ce = _ce()
    out = report_dir / f"{ce.safe_name(client)}_{ce.safe_name(shortcode)}_aff_v{ce.SCRIPT_VERSION}.csv"
    ce.ensure_dir(out.parent)
    fields = [
        "client",
        "shortcode",
        "file_id_docid",
        "node_kind",
        "node_index",
        "node_id",
        "location",
        "root_attrs",
        "inner_tags",
        "inner_attr_pairs",
        "text_len",
        "empty",
        "parse_error",
        "raw_excerpt",
    ]
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            _empty_node_fields(r)
            for kind, key in (("aff", "aff_nodes"), ("author-notes", "author_notes_nodes")):
                for n in r.get(key) or []:
                    raw = n.get("raw") or ""
                    excerpt = raw if len(raw) <= 500 else raw[:500] + "."
                    w.writerow(
                        {
                            "client": client,
                            "shortcode": shortcode,
                            "file_id_docid": _combined_id_text(
                                r.get("file_id", ""), r.get("docid", "")
                            ),
                            "node_kind": kind,
                            "node_index": n.get("node_index", 0),
                            "node_id": n.get("node_id", ""),
                            "location": n.get("location") or "",
                            "root_attrs": _attrs_flat(n.get("attrs") or {}),
                            "inner_tags": _inner_tags_flat(n.get("inner_tags") or Counter()),
                            "inner_attr_pairs": _inner_attr_pairs_flat(n.get("inner_attrs") or {}),
                            "text_len": n.get("text_len", 0),
                            "empty": bool(n.get("empty")),
                            "parse_error": n.get("parse_error") or "",
                            "raw_excerpt": excerpt.replace("\r", " ").replace("\n", " "),
                        }
                    )
    return out


def _acc_bucket(client: str) -> dict:
    if client not in _CLIENT_AFF_ACC:
        _CLIENT_AFF_ACC[client] = {
            "shortcodes": set(),
            "inner_sig": {},  # sig -> {shortcodes, occ, files}
            "root_attr_sig": {},
            "specific_use": {},
            "country_attr": {},
            "notes_inner_sig": {},
        }
    return _CLIENT_AFF_ACC[client]


def _add_unique(bucket: dict, key, shortcode: str, docid: str):
    e = bucket.setdefault(key, {"shortcodes": set(), "occ": 0, "files": set()})
    e["shortcodes"].add(shortcode)
    e["occ"] += 1
    e["files"].add(docid)


def update_client_aff_unique(client: str, shortcode: str, rows: list[dict]) -> None:
    """Fold this shortcode's article-meta aff patterns into the session client accumulator."""
    acc = _acc_bucket(client)
    acc["shortcodes"].add(shortcode)
    for r in rows:
        _empty_node_fields(r)
        docid = r["docid"]
        for n in r.get("aff_nodes") or []:
            sig = n.get("inner_sig") or ()
            _add_unique(acc["inner_sig"], sig, shortcode, docid)
            ras = n.get("root_attr_sig") or ()
            if ras:
                _add_unique(acc["root_attr_sig"], ras, shortcode, docid)
            for k, v in (n.get("attrs") or {}).items():
                if k == "specific-use":
                    _add_unique(acc["specific_use"], v, shortcode, docid)
            for pair, vals in (n.get("inner_attrs") or {}).items():
                elem, _, attr = pair.partition("/")
                if elem == "country" and attr == "country":
                    for v in vals:
                        _add_unique(acc["country_attr"], v, shortcode, docid)
                if attr == "specific-use":
                    for v in vals:
                        _add_unique(acc["specific_use"], v, shortcode, docid)
        for n in r.get("author_notes_nodes") or []:
            sig = n.get("inner_sig") or ()
            _add_unique(acc["notes_inner_sig"], sig, shortcode, docid)


def _unique_table(title: str, bucket: dict, key_label: str, ce, fmt_key) -> str:
    rows = []
    for key, e in sorted(bucket.items(), key=lambda x: (-len(x[1]["shortcodes"]), str(x[0]))):
        scs = ", ".join(sorted(e["shortcodes"]))
        rows.append(
            f"<tr><td><code class='tok'>{ce.esc(fmt_key(key))}</code></td>"
            f"<td>{ce.esc(scs)}</td><td>{e['occ']}</td><td>{len(e['files'])}</td></tr>"
        )
    if not rows:
        rows.append(f'<tr><td colspan="4"><span class="none">none</span></td></tr>')
    return (
        f"<h3>{ce.esc(title)} - {len(bucket)} unique</h3>"
        f'<table class="elem"><tr><th>{ce.esc(key_label)}</th><th>Shortcodes</th>'
        "<th>Occurrences</th><th>Files</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def build_client_aff_unique_report(client: str, report_dir: Path) -> Path | None:
    """Write {client}_aff_unique_vN.html from session accumulator."""
    ce = _ce()
    acc = _CLIENT_AFF_ACC.get(client)
    if not acc:
        return None

    def sig_fmt(sig) -> str:
        if not sig:
            return "(no inner tags)"
        if isinstance(sig, tuple):
            return "{" + ", ".join(sig) + "}"
        return str(sig)

    def attr_fmt(sig) -> str:
        if not sig:
            return "(no attrs)"
        if isinstance(sig, tuple):
            return "; ".join(sig)
        return str(sig)

    chips = [
        ("Client", client, ""),
        ("Shortcodes in session", len(acc["shortcodes"]), ""),
        ("Unique aff inner-tag sets", len(acc["inner_sig"]), ""),
        ("Unique specific-use", len(acc["specific_use"]), ""),
        ("Unique country attrs", len(acc["country_attr"]), ""),
        ("Script version", f"v{ce.SCRIPT_VERSION}", ""),
        ("Generated", ce.now(), ""),
    ]
    body = (
        '<div class="elems">'
        + _unique_table(
            "Unique aff inner-tag signatures",
            acc["inner_sig"],
            "Inner-tag set",
            ce,
            sig_fmt,
        )
        + _unique_table(
            "Unique aff root attribute patterns",
            acc["root_attr_sig"],
            "Root attrs",
            ce,
            attr_fmt,
        )
        + _unique_table(
            "Unique specific-use values",
            acc["specific_use"],
            "specific-use",
            ce,
            str,
        )
        + _unique_table(
            "Unique country/@country values",
            acc["country_attr"],
            "country",
            ce,
            str,
        )
        + _unique_table(
            "Unique author-notes inner-tag signatures",
            acc["notes_inner_sig"],
            "Inner-tag set",
            ce,
            sig_fmt,
        )
        + f"<p>Shortcodes: {ce.esc(', '.join(sorted(acc['shortcodes'])) or '-')}</p>"
        + "</div>"
    )
    out = report_dir / f"{ce.safe_name(client)}_aff_unique_v{ce.SCRIPT_VERSION}.html"
    ce.ensure_dir(out.parent)
    out.write_text(
        ce.page(f"{client} - aff unique (session)", chips, body, legend=False),
        encoding="utf-8",
    )
    return out


def get_client_aff_paths(client: str, report_dir: Path) -> dict:
    """Paths for meta (may not exist yet)."""
    ce = _ce()
    unique = report_dir / f"{ce.safe_name(client)}_aff_unique_v{ce.SCRIPT_VERSION}.html"
    return {"aff_unique_report": unique}
