import os
import json
import re
from html import escape
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag
from datetime import datetime

from tkinter import Tk, filedialog

OUTPUT_DIR = r"C:\Users\9104228\Documents\impact-support-log\refs-analyses"

REF_SEMANTIC_TAGS = {
    "string-name", "year", "article-title", "chapter-title", "source",
    "volume", "issue", "fpage", "lpage",
    "publisher-name", "publisher-loc", "edition",
    "ext-link", "pub-id", "uri",
    "supplement", "comment", "collab", "etal"
}

REF_FORMAT_TAGS = {"span", "font", "italic", "sup"}

REF_LIST_SELECTOR = ".ref-list, [data-name='ref-list'], [data-role='ref-list']"
REF_SELECTOR = ".ref, [data-name='ref'], [data-role='ref']"
BOOK_PART_SELECTOR = ".book-part, [data-name='book-part'], [data-role='book-part']"
BOOK_SELECTOR = ".book, [data-name='book'], [data-role='book']"
BOOK_TITLE_SELECTOR = ".book-meta .title-group .title, [data-name='book-meta'] .title-group .title"

EDITOR_ROLE_RE = re.compile(r"\b(?:edited|editor|editors|eds?\.?)\b", re.IGNORECASE)
TRANS_ROLE_RE = re.compile(r"\b(?:translated|translator|trans\.?)\b", re.IGNORECASE)

def normalizeTemplateToken(tag):
    mapping = {
        "article-title": "article",
        "chapter-title": "chap",
        "publisher-name": "pubname",
        "publisher-loc": "publoc",
        "ext-link": "extlink",
        "string-name": "name",
        "given-names": "given",
        # preserve simple names
        "year": "year",
        "source": "source",
        "volume": "volume",
        "issue": "issue",
        "fpage": "fpage",
        "lpage": "lpage",
        "edition": "edition",
        "pub-id": "pubid",
        "uri": "uri",
        "supplement": "supplement",
        "comment": "comment",
        "collab": "collab",
        "etal": "etal"
    }
    return mapping.get(tag, tag)

def is_element(node):
    return isinstance(node, Tag)

def has_class(node, class_name):
    classes = node.get("class") or []
    if isinstance(classes, str):
        classes = classes.split()
    return class_name in classes

def is_ignorable_ref_node(node):
    if not is_element(node):
        return False
    if node.get("data-class") == "ckcommentsfull" or has_class(node, "ckcommentsfull"):
        return True
    if node.get("data-name") == "AQ":
        return True
    if node.get("data-role") == "Query to Author":
        return True
    if node.has_attr("data-user-comment-box"):
        return True
    return node.find(attrs={"data-user-comment-box": True}) is not None

def get_ref_tag(node):
    if not is_element(node):
        return None
    data_name = node.get("data-name")
    if data_name:
        return data_name
    classes = node.get("class") or []
    if isinstance(classes, str):
        classes = classes.split()
    for cls in classes:
        if cls in {
            "string-name", "surname", "given-names", "year", "article-title",
            "chapter-title", "volume", "issue", "fpage", "lpage",
            "publisher-name", "publisher-loc", "edition", "source",
            "ext-link", "pub-id", "uri", "supplement", "comment",
            "collab", "etal", "italic"
        }:
            return cls
    return node.name

def normalize_delim(text):
    if text is None:
        return ""
    value = str(text).replace("\xa0", " ")
    value = " ".join(value.split())
    return value

def preserve_edge_space(original, normalized):
    if not normalized:
        return ""
    prefix = " " if original and original[0].isspace() else ""
    suffix = " " if original and original[-1].isspace() else ""
    return f"{prefix}{normalized}{suffix}"

def parse_string_name(node):
    parts = []
    for child in node.contents:
        if is_ignorable_ref_node(child):
            continue
        if isinstance(child, NavigableString):
            raw = str(child)
            normalized = normalize_delim(raw)
            if not normalized:
                continue
            delim = preserve_edge_space(raw, normalized)
            if delim.strip() == "" and delim != ", ":
                continue
            if delim == " ":
                continue
            parts.append(delim)
            continue

        if not is_element(child):
            continue
        child_tag = get_ref_tag(child)
        if child_tag == "surname":
            parts.append("surname")
        elif child_tag == "given-names":
            parts.append("given")
        else:
            text = normalize_delim(child.get_text(" ", strip=False))
            if text:
                parts.append(text)

    return parts

def next_element_token(children, start_index):
    for j in range(start_index, len(children)):
        if is_ignorable_ref_node(children[j]):
            continue
        if is_element(children[j]):
            return normalizeTemplateToken(get_ref_tag(children[j]))
    return None

def previous_element_token(children, start_index):
    for j in range(start_index - 1, -1, -1):
        if is_ignorable_ref_node(children[j]):
            continue
        if is_element(children[j]):
            return normalizeTemplateToken(get_ref_tag(children[j]))
    return None

def previous_text_delim(children, start_index):
    for j in range(start_index - 1, -1, -1):
        if is_ignorable_ref_node(children[j]):
            continue
        if isinstance(children[j], NavigableString):
            return str(children[j])
        if is_element(children[j]):
            return ""
    return ""

def detect_string_name_role(prev_token, prev_text):
    if prev_token != "source":
        return None
    normalized = normalize_delim(prev_text)
    if not normalized:
        return None
    if TRANS_ROLE_RE.search(normalized):
        return "trans"
    if EDITOR_ROLE_RE.search(normalized):
        return "editor"
    return None

def element_output_key(children, index):
    node = children[index]
    tag = get_ref_tag(node)
    if tag != "string-name":
        return tag
    role = detect_string_name_role(
        previous_element_token(children, index),
        previous_text_delim(children, index)
    )
    if role == "editor":
        return "editor_stringName"
    if role == "trans":
        return "trans_stringName"
    return "stringName"

def next_element_signature_token(children, start_index):
    for j in range(start_index, len(children)):
        if is_ignorable_ref_node(children[j]):
            continue
        if is_element(children[j]):
            return normalize_signature_token(element_output_key(children, j))
    return None

def move_title_quotes_into_elements(parsed):
    title_pairs = [("article-title", "article"), ("chapter-title", "chap")]
    for title_key, short in title_pairs:
        if title_key not in parsed:
            continue

        values = parsed.get(title_key) or []
        if not values:
            values = [title_key]

        prefix = ""
        suffix = ""

        for key in list(parsed.keys()):
            if not key.startswith("delim_") or not key.endswith(f"_{short}"):
                continue
            delim = parsed.get(key)
            if not isinstance(delim, str):
                continue
            stripped = delim.rstrip()
            if stripped.endswith("“"):
                prefix = "“"
                parsed[key] = stripped[:-1] + (" " if delim.endswith(" ") else "")

        for key in list(parsed.keys()):
            if not key.startswith(f"delim_{short}_"):
                continue
            delim = parsed.get(key)
            if not isinstance(delim, str):
                continue
            if delim.startswith(".”"):
                suffix = ".”"
                parsed[key] = delim[2:]
            elif delim.startswith("”"):
                suffix = "”"
                parsed[key] = delim[1:]

        wrapped = []
        if prefix:
            wrapped.append(prefix)
        wrapped.extend(values)
        if suffix:
            wrapped.append(suffix)
        parsed[title_key] = wrapped

def normalize_signature_token(key):
    mapping = {
        "stringName": "author",
        "editor_stringName": "editor",
        "trans_stringName": "trans",
        "article-title": "article",
        "chapter-title": "chap",
        "publisher-name": "pubname",
        "publisher-loc": "publoc",
        "ext-link": "extlink"
    }
    return mapping.get(key, normalizeTemplateToken(key))

def build_signature(parsed, pub_type):
    order = []
    for key in parsed.keys():
        if key.startswith("delim_") or key in {"signature", "freeText"}:
            continue
        token = normalize_signature_token(key)
        if token not in order:
            order.append(token)
    return "_".join([pub_type or "other"] + order)

def normalize_full_signature_text(text):
    tokens = []
    token_map = {
        ".": "#dot",
        ",": "#comma",
        ":": "#colon",
        ";": "#semi",
        "(": "#openparen",
        ")": "#closeparen",
        "[": "#openbracket",
        "]": "#closebracket",
        "“": "#openquote",
        "”": "#closequote"
    }

    for match in re.finditer(r"\s+|[A-Za-z0-9]+|[^\sA-Za-z0-9]", str(text).replace("\xa0", " ")):
        value = match.group(0)
        if value.isspace():
            tokens.append("#space")
        elif value in token_map:
            tokens.append(token_map[value])
        else:
            tokens.append(re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_"))

    return [token for token in tokens if token]

def clean_full_signature_delim(text, prev_token, next_token):
    value = str(text)
    title_tokens = {"article", "chap"}
    if next_token in title_tokens:
        stripped = value.rstrip()
        if stripped.endswith("“"):
            value = stripped[:-1] + (" " if value.endswith(" ") else "")
    if prev_token in title_tokens:
        if value.startswith(".”"):
            value = value[2:]
        elif value.startswith("”"):
            value = value[1:]
    if re.search(r"[A-Za-z]", value):
        value = value.rstrip()
    return value

def build_signature_full(sequence, pub_type):
    parts = [pub_type or "other"]
    for index, item in enumerate(sequence):
        kind, value = item
        if kind == "element":
            parts.append(normalize_signature_token(value))
        elif kind == "text":
            prev_token = None
            next_token = None
            if index > 0 and sequence[index - 1][0] == "element":
                prev_token = normalize_signature_token(sequence[index - 1][1])
            if index + 1 < len(sequence) and sequence[index + 1][0] == "element":
                next_token = normalize_signature_token(sequence[index + 1][1])
            cleaned = clean_full_signature_delim(value, prev_token, next_token)
            parts.extend(normalize_full_signature_text(cleaned))
    return "_".join(part for part in parts if part)

def collect_free_text(parsed):
    return {
        key: value
        for key, value in parsed.items()
        if key.startswith("delim_") and isinstance(value, str)
    }

def parse_ref(ref):
    parsed = {}
    pub_type = None
    signature_sequence = []

    citation = ref.find("span", class_="mixed-citation")
    if citation:
        pub_type = citation.get("publication-type", "other")
        children = [
            c for c in citation.contents
            if (isinstance(c, NavigableString) or is_element(c)) and not is_ignorable_ref_node(c)
        ]

        for i, child in enumerate(children):
            if is_element(child):
                tag = get_ref_tag(child)
                short = normalizeTemplateToken(tag)
                output_key = element_output_key(children, i)

                if tag == "string-name":
                    parts = parse_string_name(child)
                    parsed.setdefault(output_key, []).append(parts)

                elif tag == "source":
                    if child.find("em", class_="italic") or child.find(attrs={"data-name": "italic"}):
                        parsed.setdefault("source", []).append("source_italic")
                    else:
                        parsed.setdefault("source", []).append("source")

                elif tag in REF_SEMANTIC_TAGS:
                    parsed.setdefault(tag, []).append(tag)

                signature_sequence.append(("element", output_key))

                # Look ahead for delimiter text
                if i + 1 < len(children):
                    next_sib = children[i+1]
                    if isinstance(next_sib, NavigableString) and normalize_delim(next_sib):
                        # find next element shortname
                        next_elem = next_element_token(children, i + 1)
                        next_signature_token = next_element_signature_token(children, i + 1)
                        delim = normalize_delim(next_sib)
                        if next_elem:
                            parsed[f"delim_{short}_{next_elem}"] = delim
                        else:
                            parsed[f"delim_{short}_end"] = delim
                        if next_signature_token:
                            signature_sequence.append(("text", str(next_sib)))

        move_title_quotes_into_elements(parsed)
        parsed["signature"] = build_signature(parsed, pub_type)
        parsed["signature_full"] = build_signature_full(signature_sequence, pub_type)
        parsed["freeText"] = collect_free_text(parsed)

    return pub_type or "other", parsed

def get_node_id(node, fallback):
    if not is_element(node):
        return fallback
    return node.get("id") or fallback

def closest_by_selector(node, selector):
    current = node if is_element(node) else None
    while current:
        parent = current.parent
        root = parent if is_element(parent) else current
        if current in root.select(selector):
            return current
        current = parent if is_element(parent) else None
    return None

def select_ref_lists(soup):
    return soup.select(REF_LIST_SELECTOR)

def select_refs(root, recursive=True):
    if not is_element(root):
        return []
    refs = root.select(REF_SELECTOR) if recursive else root.select(f":scope > {REF_SELECTOR}")
    return [ref for ref in refs if ref.select_one(".mixed-citation, [data-name='mixed-citation']")]

def get_title_meta(root, selector):
    title_node = root.select_one(selector) if is_element(root) else None
    if not title_node:
        return "", ""
    return normalize_delim(title_node.get_text(" ", strip=False)), title_node.get("data-label", "")

def get_ref_list_context(ref_list, index):
    book_part = closest_by_selector(ref_list, BOOK_PART_SELECTOR)
    if book_part:
        title, label = get_title_meta(book_part, ".book-part-meta .title-group .title, [data-name='book-part-meta'] .title-group .title")
        return {
            "contextType": "book-part",
            "title": title,
            "label": label,
            "fallbackId": f"book-part-ref-list_{index}"
        }

    book = closest_by_selector(ref_list, BOOK_SELECTOR)
    if book:
        title, label = get_title_meta(book, BOOK_TITLE_SELECTOR)
        return {
            "contextType": "book",
            "title": title,
            "label": label,
            "fallbackId": f"book-ref-list_{index}"
        }

    return {
        "contextType": "document",
        "title": "",
        "label": "",
        "fallbackId": f"document-ref-list_{index}"
    }

def parse_ref_list(ref_list, index=1):
    context = get_ref_list_context(ref_list, index)
    item = {
        "ref-list-id": get_node_id(ref_list, context["fallbackId"]),
        "title": context["title"],
        "label": context["label"],
        "contextType": context["contextType"],
        "refs": {}
    }
    refs = select_refs(ref_list, recursive=False)
    if not refs:
        refs = select_refs(ref_list)
    for index, ref in enumerate(refs, start=1):
        ref_id = get_node_id(ref, f"ref_{index}")
        item["refs"][ref_id] = parse_ref(ref)[1]
    return item

def parse_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    refs = select_refs(soup)
    type_map = {"other": [], "journal": [], "book": [], "refLists": []}

    for ref in refs:
        pub_type, parsed = parse_ref(ref)
        type_map[pub_type].append(parsed)

    ref_lists = select_ref_lists(soup)
    for index, ref_list in enumerate(ref_lists, start=1):
        type_map["refLists"].append(parse_ref_list(ref_list, index))

    if refs and not ref_lists:
        fallback = {
            "ref-list-id": "document-ref-list_1",
            "title": "",
            "label": "",
            "contextType": "document",
            "refs": {}
        }
        for index, ref in enumerate(refs, start=1):
            ref_id = get_node_id(ref, f"ref_{index}")
            fallback["refs"][ref_id] = parse_ref(ref)[1]
        type_map["refLists"].append(fallback)

    return type_map

def empty_result():
    return {"other": [], "journal": [], "book": [], "refLists": []}

def merge_ref_lists(existing, incoming):
    by_id = {
        item.get("ref-list-id"): item
        for item in existing
        if isinstance(item, dict) and item.get("ref-list-id")
    }
    for item in incoming:
        if not isinstance(item, dict):
            continue
        ref_list_id = item.get("ref-list-id")
        if not ref_list_id or ref_list_id not in by_id:
            existing.append(item)
            if ref_list_id:
                by_id[ref_list_id] = item
            continue
        target = by_id[ref_list_id]
        target["title"] = item.get("title", target.get("title", ""))
        target["label"] = item.get("label", target.get("label", ""))
        target_refs = target.setdefault("refs", {})
        target_refs.update(item.get("refs") or {})

def build_ref_lookup_from_ref_lists(result):
    lookup = {}
    for ref_list in result.get("refLists", []):
        if not isinstance(ref_list, dict):
            continue
        ref_list_id = ref_list.get("ref-list-id", "")
        for ref_id, entry in (ref_list.get("refs") or {}).items():
            key = json.dumps(entry, sort_keys=True)
            lookup.setdefault(key, []).append({
                "ref_id": ref_id,
                "ref_list_id": ref_list_id,
                "title": ref_list.get("title", ""),
                "label": ref_list.get("label", ""),
                "contextType": ref_list.get("contextType", "")
            })
    return lookup

def summarize_patterns(result):
    lookup = build_ref_lookup_from_ref_lists(result)
    summaries = {}
    for pub_type in ("book", "journal", "other"):
        groups = {}
        for index, entry in enumerate(result.get(pub_type, []), start=1):
            signature = entry.get("signature", "")
            signature_full = entry.get("signature_full", "")
            key = (signature, signature_full)
            item = groups.setdefault(key, {
                "signature": signature,
                "signature_full": signature_full,
                "count": 0,
                "examples": []
            })
            item["count"] += 1
            ref_matches = lookup.get(json.dumps(entry, sort_keys=True), [])
            ref_id = ref_matches[0]["ref_id"] if ref_matches else f"{pub_type}_{index}"
            context = ref_matches[0] if ref_matches else {}
            item["examples"].append({
                "ref_id": ref_id,
                "context": context,
                "entry": entry
            })
        summaries[pub_type] = sorted(
            groups.values(),
            key=lambda item: (-item["count"], item["signature"], item["signature_full"])
        )
    return summaries

def html_escape(value):
    return escape("" if value is None else str(value), quote=True)

def render_ref_entry_html(ref_id, entry):
    pretty = json.dumps(entry, indent=2, ensure_ascii=False)
    return (
        f"<div class=\"ref-entry\">"
        f"<div class=\"ref-id\">{html_escape(ref_id)}</div>"
        f"<pre>{html_escape(pretty)}</pre>"
        f"</div>"
    )

def render_pattern_section(pub_type, patterns):
    rows = []
    for index, pattern in enumerate(patterns, start=1):
        panel_id = f"pattern_{pub_type}_{index}"
        examples = []
        for example in pattern["examples"][:10]:
            context = example.get("context") or {}
            meta = " | ".join(
                part for part in [
                    context.get("ref_list_id", ""),
                    context.get("contextType", ""),
                    context.get("label", ""),
                    context.get("title", "")
                ] if part
            )
            examples.append(
                f"<div class=\"example-meta\">{html_escape(meta)}</div>"
                f"{render_ref_entry_html(example['ref_id'], example['entry'])}"
            )
        rows.append(f"""
            <tr class="click-row" data-target="{panel_id}">
                <td><button type="button" class="toggle">+</button></td>
                <td>{html_escape(pattern["signature"])}</td>
                <td>{html_escape(pattern["signature_full"])}</td>
                <td>{pattern["count"]}</td>
            </tr>
            <tr id="{panel_id}" class="details">
                <td colspan="4">{''.join(examples)}</td>
            </tr>
        """)
    return f"""
        <section>
            <h2>{html_escape(pub_type.title())} Patterns</h2>
            <table>
                <thead>
                    <tr><th></th><th>signature</th><th>signature_full</th><th>count</th></tr>
                </thead>
                <tbody>{''.join(rows) or '<tr><td colspan="4">No references</td></tr>'}</tbody>
            </table>
        </section>
    """

def render_ref_lists_section(result):
    rows = []
    for index, ref_list in enumerate(result.get("refLists", []), start=1):
        panel_id = f"reflist_{index}"
        refs = ref_list.get("refs") or {}
        ref_html = "".join(render_ref_entry_html(ref_id, entry) for ref_id, entry in refs.items())
        rows.append(f"""
            <tr class="click-row" data-target="{panel_id}">
                <td><button type="button" class="toggle">+</button></td>
                <td>{html_escape(ref_list.get("ref-list-id", ""))}</td>
                <td>{html_escape(ref_list.get("contextType", ""))}</td>
                <td>{html_escape(ref_list.get("label", ""))}</td>
                <td>{html_escape(ref_list.get("title", ""))}</td>
                <td>{len(refs)}</td>
            </tr>
            <tr id="{panel_id}" class="details">
                <td colspan="6">{ref_html}</td>
            </tr>
        """)
    return f"""
        <section>
            <h2>Ref Lists</h2>
            <table>
                <thead>
                    <tr><th></th><th>ref-list-id</th><th>context</th><th>label</th><th>title</th><th>refs</th></tr>
                </thead>
                <tbody>{''.join(rows) or '<tr><td colspan="6">No ref-lists</td></tr>'}</tbody>
            </table>
        </section>
    """

def generate_html_report(result, json_path, filepath):
    html_path = os.path.splitext(json_path)[0] + ".html"
    patterns = summarize_patterns(result)
    counts = {key: len(result.get(key, [])) for key in ("book", "journal", "other")}
    total_refs = sum(counts.values())
    source_name = os.path.basename(filepath)
    cards = [
        ("Total refs", total_refs),
        ("Book refs", counts["book"]),
        ("Journal refs", counts["journal"]),
        ("Other refs", counts["other"]),
        ("Ref-lists", len(result.get("refLists", [])))
    ]
    card_html = "".join(
        f"<div class=\"card\"><span>{html_escape(label)}</span><strong>{value}</strong></div>"
        for label, value in cards
    )
    pattern_html = "".join(render_pattern_section(pub_type, patterns[pub_type]) for pub_type in ("book", "journal", "other"))
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Reference Analysis Report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2933; background: #f7f9fb; }}
h1 {{ margin-bottom: 4px; }}
h2 {{ margin-top: 28px; }}
.muted {{ color: #667085; font-size: 13px; }}
.cards {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 18px 0; }}
.card {{ background: #fff; border: 1px solid #d9e2ec; border-radius: 6px; padding: 12px 16px; min-width: 130px; }}
.card span {{ display: block; color: #667085; font-size: 12px; }}
.card strong {{ display: block; font-size: 24px; margin-top: 4px; }}
table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d9e2ec; }}
th, td {{ padding: 9px 10px; border-bottom: 1px solid #e6edf3; text-align: left; vertical-align: top; }}
th {{ background: #eef3f8; font-size: 12px; text-transform: uppercase; letter-spacing: .03em; }}
.click-row {{ cursor: pointer; }}
.click-row:hover {{ background: #f3f7fb; }}
.toggle {{ width: 24px; height: 24px; border: 1px solid #bcccdc; background: #fff; border-radius: 4px; cursor: pointer; }}
.details {{ display: none; background: #fbfdff; }}
.details.open {{ display: table-row; }}
.ref-entry {{ margin: 8px 0 14px; }}
.ref-id {{ font-weight: 700; margin-bottom: 4px; }}
.example-meta {{ color: #667085; margin: 10px 0 2px; font-size: 12px; }}
pre {{ background: #101828; color: #f8fafc; padding: 12px; overflow: auto; border-radius: 6px; font-size: 12px; line-height: 1.45; }}
</style>
</head>
<body>
<h1>Reference Analysis Report</h1>
<div class="muted">Source: {html_escape(source_name)}</div>
<div class="muted">JSON: {html_escape(json_path)}</div>
<div class="cards">{card_html}</div>
{pattern_html}
{render_ref_lists_section(result)}
<script>
document.addEventListener('click', function (event) {{
  var row = event.target.closest('.click-row');
  if (!row) return;
  var id = row.getAttribute('data-target');
  var target = document.getElementById(id);
  if (!target) return;
  var open = target.classList.toggle('open');
  var btn = row.querySelector('.toggle');
  if (btn) btn.textContent = open ? '-' : '+';
}});
</script>
</body>
</html>"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(page)
    return html_path

def save_report(result, filepath):
    base = os.path.splitext(os.path.basename(filepath))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outname = f"{base}_{timestamp}_refs_analyses.json"
    fullpath = os.path.join(OUTPUT_DIR, outname)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # If file exists, load and merge
    if os.path.exists(fullpath):
        with open(fullpath, "r", encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = empty_result()
    for key, value in empty_result().items():
        existing.setdefault(key, value)

    # Merge without duplicates
    for key in result:
        if key == "refLists":
            merge_ref_lists(existing[key], result[key])
            continue
        for entry in result[key]:
            if entry not in existing[key]:
                existing[key].append(entry)

    with open(fullpath, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4)

    html_path = generate_html_report(existing, fullpath, filepath)
    print(f"Report saved as {fullpath}")
    print(f"HTML report saved as {html_path}")

if __name__ == "__main__":
    Tk().withdraw()
    filepath = filedialog.askopenfilename(
        title="Select an HTML file",
        filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
    )

    if filepath:
        result = parse_file(filepath)
        save_report(result, filepath)
    else:
        print("No file selected.")
