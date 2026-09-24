"""
extract_contrib.py

For every document in documents.json (using meta.json for client / shortcode):

  1. Finds the document XML inside its folder (e.g. JATS/<docid>/)
  2. Extracts the <contrib-group> XML        -> <folder>/contrib_group.xml
  3. Builds an HTML preview of all contribs   -> <folder>/contrib_preview.html
  4. Builds ONE report per client + shortcode -> <root>/contrib_reports/<client>_<shortcode>_contrib.html

Report
------
  * Sticky header (title, client, shortcode, doc/contrib counts, issue count,
    generated time, Preview/Raw toggle). The column header row sticks below it.
  * Columns: File ID | Docid | First contrib | Last before | Last contrib

  Which contrib goes in which column (decided by the number of contribs):
      1 contrib    -> Last contrib only            (First, Last before = "-")
      2 contribs   -> Last before + Last contrib   (First = "-")
      3+ contribs  -> First, Last before (2nd from the end), Last contrib
  A single author has no trailing separator, so it behaves like a last contrib;
  the first of two authors carries a separator, so it behaves like a last-before.
  * Toggle: "Preview HTML" (pistart values restored as text) / "Raw XML".

Statistics (top of every report)
--------------------------------
  For the three report columns (First / Last before / Last) every file is
  reduced to two patterns and files are grouped by them:
      PI attr value : the ordered list of pistart values in that contrib
      PI position   : the ordered list of places (element path + neighbours)
                      where a pistart sits
  Files are first split into xref groups (xref 0 / 1 / 2 ... in that contrib),
  because the number of <xref> changes where pistarts sit. Inside each xref
  group every file gets "pattern-N  <files with it>/<files in the group>";
  pattern-1 is the most common one of its group and the group header shows
  <files in group>/<overall files>. Every other pattern lists its files (docid) and says what
  differs: differs / missing / extra. The same pattern-N tags are shown under
  each cell of the file table, and clicking a file in the statistics jumps to
  its row. Files that have no contrib for a column are counted as "n/a" there.

Preview rule
------------
    <?pistart xml:space=",&#x00A0;"?>  ->  the attribute value is put back as
    real text at that position. Other PIs (<?attributepistart ...?>,
    <?PageID ?>) and comments are ignored.

Consistency check  ("same value, same position")
------------------------------------------------
  A "position" is a gap inside a <contrib>, identified by
      (element path, previous sibling, next sibling, occurrence)
  e.g. contrib/name/surname [start -> end]  or  contrib [xref -> xref].
  The value of a position is the text of the pistart PIs sitting there
  ("" if none). Across ALL documents of one report (same client + shortcode)
  contribs are compared only with contribs of the same kind: same class
  (last / last before / other) and same xref group - so " and " before the
  last author is not confused with ", " elsewhere. Where a position has more
  than one distinct
  value, the most common value is the expected one and every contrib that
  differs is flagged:
      red highlight  = different / unexpected pistart value
      red warning    = expected pistart missing at that position
  xref groups: a contrib can have 0, 1, 2 ... <xref> children and that moves
  the pistarts around, so contribs are split by their xref count first
  (XREF_SUBGROUP_BY = "types" splits by the ref-type mix instead, e.g. aff+aff+fn).
  Every contrib (not only the 3 shown in the report) is checked; the File ID
  cell shows an issue badge and the per-document preview lists all issues.

Selection + meta-contrib.json
-----------------------------
  Only documents whose meta.json "dtd" is JATS are used (RUN_DTD below; BITS
  is ignored). You are asked for the client(s) and then the shortcode(s):

      JATS clients:
        1) LWW     3 shortcodes    120 docs   1 to generate
        2) PLOS    2 shortcodes     40 docs   all generated
      Client (number/name, comma for several, 'all'):

  Before anything runs, an overview lists Clients -> Shortcodes with doc counts
  and whether each one is already filled (generated) or not.

  The shortcode menu shows every shortcode of the client with its doc count
  and a status: [not filled] / [filled <date>] / [update (+N new docs)].
      Enter  = every shortcode that is not filled or has new docs   (default)
      1,3    = the numbers / names you type (asks before redoing a done one)
      all    = regenerate everything for the chosen client(s)

  Every generated shortcode is recorded in root/meta-contrib.json so it is
  not generated again:

      { "JATS": { "LWW": { "INF": {
            "generated_at": "...", "logic": 2, "report": "contrib_reports/JATS/LWW_INF_contrib.html",
            "documents": 45, "failed": 0, "off_pattern_files": 3,
            "consistency_issues": 4,
            "docids": { "<docid>": {"file-id": "...", "contribs": 18, "status": "ok"}, ... }
      } } } }

  Run order: strictly one shortcode at a time (report written and recorded in
  meta-contrib.json), then a pause, then the next shortcode of that client.
  When a client is complete there is a (longer) pause and the next client
  starts. Pauses are asked once (Enter = defaults DELAY_SHORTCODE_SEC /
  DELAY_CLIENT_SEC). Ctrl+C stops cleanly; finished shortcodes stay recorded.

  A shortcode counts as "update" when meta.json has docids that are not
  recorded yet, or when it was generated by an older LOGIC_VERSION. Regenerating a shortcode always rebuilds its whole report
  (statistics need all of its files).

Expected layout:
    root/documents.json
    root/meta.json
    root/meta-contrib.json      (created / updated by this script)
    root/<folder from documents.json>/...xml
    root/contrib_reports/JATS/<client>_<shortcode>_contrib.html

Usage:
    python extract_contrib.py
    (then enter the project root folder, client and shortcode when prompted)

Requires Python 3.10+. No extra packages.
"""

import difflib
import html
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from html.entities import name2codepoint
from pathlib import Path

DOCS_NAME = "documents.json"
META_NAME = "meta.json"
DONE_NAME = "meta-contrib.json"   # what has already been generated
REPORT_DIR = "contrib_reports"
RUN_DTD = "JATS"                 # only this DTD is processed
LOGIC_VERSION = 3                # bump when column/pattern logic changes -> old reports become "update"
XREF_SUBGROUP_BY = "count"       # "count" (xref 0/1/2..) or "types" (xref 3 = aff+aff+fn)
DELAY_SHORTCODE_SEC = 5          # default pause between two shortcodes of one client
DELAY_CLIENT_SEC = 10            # default pause when the next shortcode belongs to another client
OUT_XML = "contrib_group.xml"
OUT_HTML = "contrib_preview.html"

# xml files that must never be treated as the document xml
SKIP_XML = {"impact_config.xml", OUT_XML}

HIGHLIGHT_PI = True  # yellow background on text restored from pistart

CONTRIB_GROUP_RE = re.compile(r"<contrib-group\b.*?</contrib-group>", re.S)
CONTRIB_RE = re.compile(r"<contrib(?=[\s>]).*?</contrib>", re.S)
NAMED_ENTITY_RE = re.compile(r"&([A-Za-z][A-Za-z0-9]*);")
PI_VALUE_RE = re.compile(r"""xml:space\s*=\s*(?:"([^"]*)"|'([^']*)')""")
WS_RE = re.compile(r"[ \t\r\n]+")  # NOTE: does not match nbsp on purpose
XML_ENTITIES = {"amp", "lt", "gt", "quot", "apos"}

NS_DECLS = (
    'xmlns:xlink="http://www.w3.org/1999/xlink" '
    'xmlns:mml="http://www.w3.org/1998/Math/MathML" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
)

INLINE_TAGS = {"sup": "sup", "sub": "sub", "italic": "i", "bold": "b"}

PI = ET.ProcessingInstruction


# ----------------------------------------------------------------- io helpers

def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_name(s: str) -> str:
    return re.sub(r"[^\w.-]+", "_", s.strip()) or "unknown"


# ------------------------------------------------------------ locating files

def doc_folder(base: Path, docid: str, item: dict, meta: dict) -> Path:
    folder = item.get("folder")
    if folder:
        return base / folder
    return base / meta.get("dtd", "") / docid


def candidate_xml_files(base: Path, folder: Path, item: dict) -> list[Path]:
    found: list[Path] = []

    def add(p: Path):
        if (
            p.suffix.lower() == ".xml"
            and p.name.lower() not in SKIP_XML
            and p.exists()
            and p not in found
        ):
            found.append(p)

    # 1) anything documents.json already knows about
    for rel in (item.get("files") or {}).values():
        if isinstance(rel, str):
            add(base / rel)

    # 2) any other xml sitting in the folder
    if folder.is_dir():
        for p in sorted(folder.glob("*.xml")):
            add(p)

    return found


def extract_contrib_groups(folder: Path, base: Path, item: dict):
    """Return (source_path, raw_contrib_group_xml) or (None, None)."""
    for p in candidate_xml_files(base, folder, item):
        text = p.read_text(encoding="utf-8-sig", errors="replace")
        groups = CONTRIB_GROUP_RE.findall(text)
        if groups:
            return p, "\n\n".join(groups)
    return None, None


# ------------------------------------------------------------------- parsing

def _fix_entity(m: re.Match) -> str:
    name = m.group(1)
    if name in XML_ENTITIES:
        return m.group(0)
    cp = name2codepoint.get(name)
    # unknown named entity (DTD not loaded) -> keep it visible, but well-formed
    return chr(cp) if cp else f"&amp;{name};"


def parse_contribs(group_xml: str) -> list[ET.Element]:
    wrapped = f"<root {NS_DECLS}>{NAMED_ENTITY_RE.sub(_fix_entity, group_xml)}</root>"
    # insert_pis=True keeps <?pistart ...?> in the tree (ElementTree drops them otherwise)
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_pis=True))
    root = ET.fromstring(wrapped, parser=parser)
    return list(root.iter("contrib"))


def tidy_raw(raw: str) -> str:
    """Remove the source indentation so each raw <contrib> reads from column 0."""
    lines = raw.split("\n")
    rest = [l for l in lines[1:] if l.strip()]
    indent = min((len(l) - len(l.lstrip(" \t")) for l in rest), default=0)
    out = [lines[0]] + [l[indent:] if l.strip() else "" for l in lines[1:]]
    return "\n".join(out).replace("\t", "  ")


def raw_contribs(group_xml: str) -> list[str]:
    return [tidy_raw(m) for m in CONTRIB_RE.findall(group_xml)]


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def pi_value(pi: ET.Element) -> str | None:
    """Text carried by a <?pistart xml:space="..."?>, or None for any other PI."""
    data = (pi.text or "").strip()
    if not data or data.split(None, 1)[0] != "pistart":
        return None
    m = PI_VALUE_RE.search(data)
    if not m:
        return None
    raw = m.group(1) if m.group(1) is not None else m.group(2)
    return html.unescape(raw)  # &#x00A0; -> nbsp (parser does not decode PI data)


# ----------------------------------------------------------- consistency check

@dataclass
class Gap:
    key: tuple                 # (path, prev sibling, next sibling, occurrence)
    value: str                 # concatenated pistart text at this position
    pis: list = field(default_factory=list)   # the PI elements sitting here
    parent: ET.Element | None = None
    before: ET.Element | None = None          # real child that follows (None = end)


@dataclass
class Ctx:
    """Where to draw red marks while rendering one document."""
    pi_bad: dict = field(default_factory=dict)        # id(pi element) -> tooltip
    miss_before: dict = field(default_factory=dict)   # id(child) -> [tooltip]
    miss_end: dict = field(default_factory=dict)      # id(parent) -> [tooltip]


def analyze(contrib: ET.Element) -> list[Gap]:
    gaps: list[Gap] = []
    occ: Counter = Counter()

    def walk(el: ET.Element, path: str):
        prev = "^"
        pis: list = []
        vals: list = []

        def close(nxt: str, before):
            base = (path, prev, nxt)
            key = base + (occ[base],)
            occ[base] += 1
            gaps.append(Gap(key, "".join(vals), list(pis), el, before))

        for kid in el:
            if kid.tag is PI:
                v = pi_value(kid)
                if v is not None:
                    pis.append(kid)
                    vals.append(v)
                continue
            if not isinstance(kid.tag, str):
                continue
            tag = local(kid.tag)
            close(tag, kid)
            pis, vals, prev = [], [], tag
            walk(kid, f"{path}/{tag}")
        close("$", None)

    walk(contrib, "contrib")
    return gaps


def xref_key(contrib: ET.Element) -> tuple:
    """(number of <xref> children, ref-type mix or '') - the xref group of a contrib."""
    refs = [k for k in contrib if isinstance(k.tag, str) and local(k.tag) == "xref"]
    sig = "+".join(k.get("ref-type", "?") for k in refs) if XREF_SUBGROUP_BY == "types" else ""
    return (len(refs), sig)


def xref_label(key: tuple) -> str:
    n, sig = key
    return f"xref {n}" + (f" ({sig})" if sig else "")


def contrib_class(i: int, n: int) -> str:
    """last / last before / other - same idea as the report columns."""
    if i == n - 1:
        return "last"
    if i == n - 2:
        return "before"
    return "other"


CLASS_LABEL = {"last": "last", "before": "last before", "other": "other"}


def expected_values(items) -> dict:
    """
    items: (class key, gaps of one contrib). Returns
    (class key, position) -> most common value, only where the values disagree.
    """
    counts: dict = defaultdict(Counter)
    for cls, gaps in items:
        for g in gaps:
            counts[(cls, g.key)][g.value] += 1
    return {k: c.most_common(1)[0][0] for k, c in counts.items() if len(c) > 1}


def vis(v: str) -> str:
    return v.replace("\xa0", "<nbsp>")


def pos_label(key: tuple) -> str:
    path, prev, nxt = key[0], key[1], key[2]
    a = "start" if prev == "^" else prev
    b = "end" if nxt == "$" else nxt
    return f"{path} [{a} -> {b}]"


def build_ctx(gap_lists, classes, expected: dict):
    """Return (Ctx for rendering, list of issue dicts) for one document."""
    ctx, issues = Ctx(), []
    for n, (gaps, cls) in enumerate(zip(gap_lists, classes), 1):
        for g in gaps:
            exp = expected.get((cls, g.key))
            if exp is None or g.value == exp:
                continue
            if g.value == "":
                kind, what = "missing", f'expected "{vis(exp)}", found nothing'
            elif exp == "":
                kind, what = "unexpected", f'expected nothing, found "{vis(g.value)}"'
            else:
                kind, what = "different", f'expected "{vis(exp)}", found "{vis(g.value)}"'
            text = f"{pos_label(g.key)} ({CLASS_LABEL[cls[0]]}, {xref_label(cls[1])}): {what}"
            issues.append({"n": n, "kind": kind, "text": text})
            if g.pis:
                for p in g.pis:
                    ctx.pi_bad[id(p)] = text
            elif g.before is not None:
                ctx.miss_before.setdefault(id(g.before), []).append(text)
            else:
                ctx.miss_end.setdefault(id(g.parent), []).append(text)
    return ctx, issues


# ----------------------------------------------------- pattern statistics

ROLES = [("first", "First contrib"), ("before", "Last before"), ("last", "Last contrib")]
KINDS = [("attr", "PI attr value"), ("pos", "PI position")]


def role_index(n: int, role: str):
    """
    Index of the contrib shown in a report column (None = no contrib there).
        n == 1 : only "last"
        n == 2 : "before" (index 0) + "last" (index 1)
        n >= 3 : first (0), before (n-2), last (n-1)
    """
    if role == "first":
        return 0 if n >= 3 else None
    if role == "before":
        return n - 2 if n >= 2 else None
    return n - 1 if n >= 1 else None


def pos_short(key: tuple) -> str:
    path = key[0]
    if path.startswith("contrib/"):
        path = path[len("contrib/"):]
    a = "start" if key[1] == "^" else key[1]
    b = "end" if key[2] == "$" else key[2]
    return f"{path} [{a} -> {b}]"


def pi_sequences(gaps: list) -> dict:
    hit = [g for g in gaps if g.pis]
    return {
        "attr": tuple(g.value for g in hit),
        "pos": tuple(pos_short(g.key) for g in hit),
    }


def build_stats(rows: list[dict]) -> dict:
    """Per column and kind: files split by xref group, then grouped by pattern."""
    total = len(rows)
    cards = {}
    for role, _ in ROLES:
        for kind, _ in KINDS:
            by_x: dict = {}
            na = []
            for r in rows:
                i = role_index(len(r["contribs"]), role)
                if i is None:
                    na.append(r)
                    r["pat"][(role, kind)] = None
                    r["xk"][role] = None
                    continue
                xk = r["xkeys"][i]
                r["xk"][role] = xk
                by_x.setdefault(xk, {}).setdefault(r["seqs"][i][kind], []).append(r)
            subgroups = []
            for xk in sorted(by_x):
                ordered = sorted(by_x[xk].items(), key=lambda kv: -len(kv[1]))  # stable on ties
                patterns = []
                for n, (seq, rs) in enumerate(ordered, 1):
                    for r in rs:
                        r["pat"][(role, kind)] = n
                    patterns.append({"n": n, "seq": seq, "rows": rs})
                subgroups.append(
                    {
                        "xk": xk,
                        "files": sum(len(p["rows"]) for p in patterns),
                        "patterns": patterns,
                        "base": ordered[0][0],
                    }
                )
            cards[(role, kind)] = {"subgroups": subgroups, "na": na}
    return {"total": total, "cards": cards}


def off_pattern_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if any(n not in (None, 1) for n in r["pat"].values())]


def row_id(docid: str) -> str:
    return "row-" + safe_name(docid)


def tok_val(v: str) -> str:
    return v.replace("\xa0", "[nbsp]").replace(" ", "\u00b7") or "(empty)"


def tok(kind: str, x: str) -> str:
    if kind == "attr":
        return f'<code class="tok">{esc(tok_val(x))}</code>'
    return f'<code class="tok pos">{esc(x)}</code>'


def seq_diff(base: tuple, seq: tuple, kind: str):
    """Tokens of `seq` that differ from `base`, plus human readable lines."""
    bad: set = set()
    lines: list = []
    if len(base) == len(seq):  # same length: compare slot by slot (clearest for separators)
        for j, (x, y) in enumerate(zip(base, seq)):
            if x != y:
                bad.add(j)
                lines.append(
                    f'<b class="k differs">differs</b> #{j + 1} expected {tok(kind, x)}, found {tok(kind, y)}'
                )
        return bad, lines
    sm = difflib.SequenceMatcher(None, base, seq, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        exp = " ".join(tok(kind, x) for x in base[i1:i2])
        got = " ".join(tok(kind, x) for x in seq[j1:j2])
        if tag == "replace":
            lines.append(f'<b class="k differs">differs</b> expected {exp}, found {got}')
            bad.update(range(j1, j2))
        elif tag == "delete":
            lines.append(f'<b class="k missing">missing</b> {exp}')
        else:
            lines.append(f'<b class="k extra">extra</b> {got}')
            bad.update(range(j1, j2))
    return bad, lines


def file_rows(rows: list[dict]) -> str:
    return "".join(
        f'<div class="frow"><a href="#{esc(row_id(r["docid"]))}">{esc(r["file_id"] or r["docid"])}</a>'
        f'<span class="did">{esc(r["docid"])}</span></div>'
        for r in sorted(rows, key=lambda r: (r["file_id"] or r["docid"]).lower())
    )


def files_details(rows: list[dict], open_: bool) -> str:
    s = "" if len(rows) == 1 else "s"
    return (
        f'<details{" open" if open_ else ""}><summary>{len(rows)} file{s}</summary>'
        f"{file_rows(rows)}</details>"
    )


def render_card(kind: str, card: dict, total: int) -> str:
    out = []
    for sg in card["subgroups"]:
        base, size = sg["base"], sg["files"]
        body = []
        for p in sg["patterns"]:
            n, rs = p["n"], p["rows"]
            minor = n > 1
            bad, diff = seq_diff(base, p["seq"], kind) if minor else (set(), [])
            items = "".join(
                f'<li class="{"bad" if i in bad else ""}">{tok(kind, x)}</li>'
                for i, x in enumerate(p["seq"])
            ) or '<li class="none">(no pistart)</li>'
            diff_html = "".join(f"<div>{d}</div>" for d in diff)
            label = "differs from pattern-1" if minor else "most common"
            body.append(
                f'<div class="pat{" minor" if minor else ""}">'
                f'<div class="pat-h"><b>pattern-{n}</b><span class="cnt">{len(rs)}/{size}</span>'
                f'<span class="pct">{len(rs) / size * 100:.1f}%</span>'
                f'<span class="lbl">{label}</span></div>'
                f'<ol class="seq">{items}</ol>'
                + (f'<div class="diff">{diff_html}</div>' if diff_html else "")
                + files_details(rs, open_=minor)
                + "</div>"
            )
        out.append(
            '<div class="xg"><div class="xg-h">'
            f'<b>{esc(xref_label(sg["xk"]))}</b><span class="cnt">{size}/{total} files</span></div>'
            + "".join(body)
            + "</div>"
        )
    na = card["na"]
    if na:
        out.append(
            '<div class="pat na"><div class="pat-h"><b>n/a</b>'
            f'<span class="cnt">{len(na)}/{total}</span>'
            '<span class="lbl">no contrib at this index</span></div>'
            + files_details(na, open_=False)
            + "</div>"
        )
    return "".join(out) or '<div class="none">-</div>'


def stats_html(stats: dict | None) -> str:
    if not stats:
        return ""
    total = stats["total"]
    head = "".join(f"<th>{label}</th>" for _, label in ROLES)
    rows = ""
    for kind, klabel in KINDS:
        tds = "".join(
            f'<td>{render_card(kind, stats["cards"][(role, kind)], total)}</td>'
            for role, _ in ROLES
        )
        rows += f'<tr><th class="rl">{klabel}</th>{tds}</tr>'
    return (
        '<details class="stats" open><summary>Statistics - pistart patterns by contrib index '
        f'<span class="sub">pattern-N &nbsp;files with it / files in its xref group &nbsp;&middot;&nbsp; '
        "<code class=\"tok\">\u00b7</code> = space, <code class=\"tok\">[nbsp]</code> = non-breaking space"
        "</span></summary>"
        '<div class="legend" style="margin:8px 12px 0">Which contrib is in which column: '
        "1 contrib = Last &middot; 2 contribs = Last before + Last &middot; "
        "3+ contribs = First, Last before, Last. Files are split by xref count first; "
        f"a pattern is compared only inside its xref group (group header = files in group / {total} overall)."
        "</div>"
        f'<table class="stat"><tr><th></th>{head}</tr>{rows}</table></details>'
    )


def na_title(n: int) -> str:
    if n == 1:
        return "1 contrib - counted as Last contrib"
    return f"{n} contribs - counted as Last before + Last contrib"


def cell_tags(r: dict, role: str) -> str:
    out = []
    xk = r["xk"].get(role)
    if xk is not None:
        out.append(f'<span class="tag xref" title="xref group">{esc(xref_label(xk))}</span>')
    for kind, label in (("attr", "attr"), ("pos", "pos")):
        n = r["pat"].get((role, kind))
        if n is None:
            continue
        cls = "tag" if n == 1 else "tag bad"
        full = dict(KINDS)[kind]
        out.append(f'<span class="{cls}" title="{full} pattern (inside the xref group)">{label}: pattern-{n}</span>')
    return f'<div class="tags">{"".join(out)}</div>' if out else ""


# ----------------------------------------------------------------- rendering

def esc(s: str) -> str:
    return html.escape(s, quote=False)


def esc_attr(s: str) -> str:
    return html.escape(s, quote=True).replace("\n", "&#10;")


def chunk(s: str | None) -> str:
    """Collapse indentation whitespace; drop whitespace-only chunks between tags."""
    if not s or not s.strip(" \t\r\n"):
        return ""
    return esc(WS_RE.sub(" ", s))


def marker(tip: str) -> str:
    return f'<span class="pi miss" title="{esc_attr(tip)}">&#9888;</span>'


def render_pi(pi: ET.Element, ctx: Ctx | None) -> str:
    value = pi_value(pi)
    if value is None:
        return ""
    out = esc(value)
    tip = ctx.pi_bad.get(id(pi)) if ctx else None
    if tip:
        return f'<span class="pi bad" title="{esc_attr(tip)}">{out or "&#9888;"}</span>'
    return f'<span class="pi">{out}</span>' if HIGHLIGHT_PI else out


def render(el: ET.Element, ctx: Ctx | None = None) -> str:
    out = [chunk(el.text)]
    for child in el:
        if child.tag is PI:
            out.append(render_pi(child, ctx))
        elif isinstance(child.tag, str):
            if ctx:
                out += [marker(t) for t in ctx.miss_before.get(id(child), [])]
            inner = render(child, ctx)
            wrap = INLINE_TAGS.get(local(child.tag))
            out.append(f"<{wrap}>{inner}</{wrap}>" if wrap else inner)
        out.append(chunk(child.tail))
    if ctx:
        out += [marker(t) for t in ctx.miss_end.get(id(el), [])]
    return "".join(out)


# --------------------------------------------------------------------- pages

CSS = """
*{box-sizing:border-box}
body{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:0;color:#1f2328}
header#top{position:sticky;top:0;z-index:5;background:#fff;border-bottom:1px solid #d0d7de;
  padding:12px 24px;display:flex;flex-wrap:wrap;align-items:center;gap:8px 20px}
header#top .ttl{font-size:18px;font-weight:700}
.chips{display:flex;flex-wrap:wrap;gap:6px;flex:1}
.chip{font-size:12px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:999px;padding:2px 10px;color:#57606a}
.chip b{color:#1f2328;font-weight:600}
.chip.warn{background:#ffebe9;border-color:#f0625d;color:#b42318}
.chip.good{background:#dafbe1;border-color:#4ac26b;color:#1a7f37}
main{padding:16px 24px 32px}
.legend{font-size:12px;color:#57606a;margin-bottom:12px}
.legend .pi{padding:0 4px}
table{border-collapse:separate;border-spacing:0;width:100%;font-size:14px;
  border-left:1px solid #d0d7de;border-top:1px solid #d0d7de}
th,td{border-right:1px solid #d0d7de;border-bottom:1px solid #d0d7de;padding:8px 10px;
  text-align:left;vertical-align:top}
th{background:#f6f8fa}
table.files th{position:sticky;top:var(--hh,64px);z-index:2}
tr:nth-child(even) td{background:#fafbfc}
td.fid{white-space:nowrap;font-weight:600}
td.na{color:#9aa4ad}
td.err{color:#b42318;background:#fff1f0}
td.docid{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:#57606a;word-break:break-all}
td.chk ul{margin:0;padding-left:16px;font-size:12px;color:#b42318}
td.chk .ok{color:#1a7f37;font-size:12px}
.pi{background:#fff3b0;border-radius:2px}
.pi.bad{background:#ffd8d3;outline:1px solid #f0625d}
.pi.miss{background:#ffd8d3;color:#b42318;font-weight:700;padding:0 2px;outline:1px solid #f0625d}
.badge{display:inline-block;margin-left:6px;font-size:11px;font-weight:600;color:#b42318;
  background:#ffebe9;border:1px solid #f0625d;border-radius:999px;padding:0 7px;cursor:help}
.toggle{display:inline-flex;border:1px solid #d0d7de;border-radius:6px;overflow:hidden}
.toggle button{border:0;background:#fff;padding:6px 14px;font-size:13px;cursor:pointer;color:#1f2328}
.toggle button.on{background:#0969da;color:#fff}
body[data-view=preview] .v-raw{display:none}
body[data-view=raw] .v-preview{display:none}
pre.raw{margin:0;font:12px/1.45 ui-monospace,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;tab-size:2}
sup{font-size:.75em}
a{color:#0969da;text-decoration:none} a:hover{text-decoration:underline}
tr[id]{scroll-margin-top:calc(var(--hh,64px) + 44px)}
tr:target td{background:#fff8c5!important}
.tags{margin-top:6px;display:flex;gap:4px;flex-wrap:wrap}
.tag{font-size:11px;border:1px solid #d0d7de;border-radius:4px;padding:0 5px;color:#57606a;background:#fff}
.tag.bad{border-color:#f0625d;background:#ffebe9;color:#b42318;font-weight:600}
.tag.xref{background:#ddf4ff;border-color:#54aeff;color:#0550ae}
.xg{margin-bottom:14px}
.xg-h{display:flex;gap:8px;align-items:baseline;margin:0 0 6px;font-size:13px}
.xg-h b{background:#ddf4ff;border:1px solid #54aeff;border-radius:999px;padding:0 9px;color:#0550ae}
.xg-h .cnt{color:#57606a;font-size:12px}
details.stats{margin-bottom:20px;border:1px solid #d0d7de;border-radius:8px;background:#fff}
details.stats>summary{cursor:pointer;font-weight:600;padding:10px 14px;background:#f6f8fa;border-radius:8px}
details.stats>summary .sub{font-weight:400;color:#57606a;font-size:12px;margin-left:8px}
table.stat{width:calc(100% - 24px);margin:12px}
table.stat th{position:static}
table.stat th.rl{white-space:nowrap;width:1%}
table.stat td{background:#fff!important;width:33%}
.pat{border:1px solid #d0d7de;border-radius:6px;padding:8px;margin-bottom:8px;background:#fff}
.pat.minor{border-color:#f0625d;background:#fff8f7}
.pat.na{background:#f6f8fa}
.pat-h{font-size:13px;margin-bottom:6px;display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}
.pat-h .cnt{font-weight:700}
.pat-h .pct{color:#57606a;font-size:12px}
.pat-h .lbl{font-size:11px;padding:0 6px;border-radius:999px;border:1px solid #d0d7de;color:#57606a}
.pat.minor .lbl{border-color:#f0625d;color:#b42318}
ol.seq{margin:0 0 6px;padding-left:22px;font-size:12px}
ol.seq li{margin:2px 0}
ol.seq li.none{list-style:none;color:#9aa4ad;margin-left:-22px}
ol.seq li.bad code{background:#ffd8d3;outline:1px solid #f0625d}
code.tok{background:#eef1f4;border-radius:3px;padding:0 4px;font:12px ui-monospace,Consolas,monospace;white-space:pre-wrap}
.diff{font-size:12px;margin:4px 0 6px}
.diff .k{font-size:11px;text-transform:uppercase;margin-right:4px}
.diff .k.differs{color:#9a6700}.diff .k.missing{color:#b42318}.diff .k.extra{color:#8250df}
.pat details{font-size:12px}
.pat summary{cursor:pointer;color:#57606a}
.frow{display:flex;gap:8px;align-items:baseline;padding:2px 0}
.frow a{font-weight:600;white-space:nowrap}
.frow .did{font:11px ui-monospace,Consolas,monospace;color:#57606a;word-break:break-all}
"""

TOGGLE = (
    '<div class="toggle" role="group" aria-label="Column view">'
    '<button type="button" data-view="preview" class="on">Preview HTML</button>'
    '<button type="button" data-view="raw">Raw XML</button></div>'
)

LEGEND = (
    '<div class="legend"><span class="pi">text</span> restored from pistart &middot; '
    '<span class="pi bad">text</span> differs from the most common value at the same position &middot; '
    '<span class="pi miss">&#9888;</span> pistart missing where other files have it</div>'
)

JS = """<script>
(function () {
  var h = document.getElementById('top');
  function fit() { document.documentElement.style.setProperty('--hh', h.offsetHeight + 'px'); }
  fit(); window.addEventListener('resize', fit); window.addEventListener('load', fit);
  document.querySelectorAll('.toggle button').forEach(function (b) {
    b.addEventListener('click', function () {
      document.body.setAttribute('data-view', b.dataset.view);
      document.querySelectorAll('.toggle button').forEach(function (x) {
        x.classList.toggle('on', x === b);
      });
    });
  });
})();
</script>"""


def page(title: str, chips: list, body: str, toggle: bool = False) -> str:
    """chips: list of (label, value, style) with style in '', 'warn', 'good'."""
    chips_html = "".join(
        f'<span class="chip {style}"><b>{esc(label)}</b> {esc(str(value))}</span>'
        for label, value, style in chips
    )
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{esc(title)}</title><style>{CSS}</style></head>"
        '<body data-view="preview">'
        f'<header id="top"><div class="ttl">{esc(title)}</div>'
        f'<div class="chips">{chips_html}</div>{TOGGLE if toggle else ""}</header>'
        f"<main>{LEGEND}{body}</main>{JS}</body></html>"
    )


def issue_chip(n: int) -> tuple:
    return ("Consistency issues", n, "warn" if n else "good")


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def write_doc_outputs(row: dict, client: str, shortcode: str, ctx: Ctx, issues: list):
    folder: Path = row["folder"]
    (folder / OUT_XML).write_text(row["raw_group"], encoding="utf-8")

    by_n: dict = defaultdict(list)
    for i in issues:
        by_n[i["n"]].append(i["text"])

    trs = []
    for n, c in enumerate(row["contribs"], 1):
        if by_n[n]:
            chk = "<ul>" + "".join(f"<li>{esc(t)}</li>" for t in by_n[n]) + "</ul>"
        else:
            chk = '<span class="ok">OK</span>'
        trs.append(f'<tr><td>{n}</td><td>{render(c, ctx)}</td><td class="chk">{chk}</td></tr>')

    body = (
        "<table class=\"files\"><tr><th>#</th><th>Contrib</th><th>Consistency</th></tr>"
        + "".join(trs)
        + "</table>"
    )
    chips = [
        ("Docid", row["docid"], ""),
        ("Client", client, ""),
        ("Shortcode", shortcode, ""),
        ("Contribs", len(row["contribs"]), ""),
        issue_chip(len(issues)),
        ("Generated", now(), ""),
    ]
    title = row["file_id"] or row["docid"]
    (folder / OUT_HTML).write_text(page(title, chips, body), encoding="utf-8")


def pick_cells(contribs, raws, ctx: Ctx) -> list:
    """
    first / last-before / last as (preview_html, raw_xml) pairs (see role_index),
    None where the document has no contrib for that column.
    """
    n = len(contribs)

    def cell(i):
        raw = raws[i] if i < len(raws) else "(raw xml not available)"
        return render(contribs[i], ctx), raw

    out = []
    for role, _ in ROLES:
        i = role_index(n, role)
        out.append(cell(i) if i is not None else None)
    return out


def build_report(client: str, shortcode: str, rows: list[dict], report_dir: Path, stats):
    rows = sorted(rows, key=lambda r: (r["file_id"] or r["docid"]).lower())
    trs = []
    for r in rows:
        fid = esc(r["file_id"] or r["docid"])
        if r["preview_rel"]:
            fid = f'<a href="{esc(r["preview_rel"])}">{fid}</a>'
        if r["issues"]:
            tips = [i["text"] for i in r["issues"][:8]]
            if len(r["issues"]) > 8:
                tips.append(f"... +{len(r['issues']) - 8} more")
            fid += (
                f' <span class="badge" title="{esc_attr(chr(10).join(tips))}">'
                f'&#9888; {len(r["issues"])}</span>'
            )
        did = f'<td class="docid">{esc(r["docid"])}</td>'
        rid = esc(row_id(r["docid"]))
        if r["error"]:
            trs.append(
                f'<tr id="{rid}"><td class="fid">{fid}</td>{did}'
                f'<td class="err" colspan="3">{esc(r["error"])}</td></tr>'
            )
            continue
        cells = "".join(
            (
                f'<td><div class="v-preview">{c[0]}</div>'
                f'<div class="v-raw"><pre class="raw">{esc(c[1])}</pre></div>'
                f'{cell_tags(r, role)}</td>'
            )
            if c
            else f'<td class="na" title="{esc_attr(na_title(len(r["contribs"])))}">-</td>'
            for (role, _), c in zip(ROLES, r["cells"])
        )
        trs.append(f'<tr id="{rid}"><td class="fid">{fid}</td>{did}{cells}</tr>')

    body = (
        stats_html(stats)
        + '<table class="files"><tr><th>File ID</th><th>Docid</th>'
        "<th>First contrib</th><th>Last before</th><th>Last contrib</th></tr>"
        + "".join(trs)
        + "</table>"
    )

    good = [r for r in rows if r["contribs"]]
    n_issues = sum(len(r["issues"]) for r in good)
    off = off_pattern_rows(good)
    chips = [
        ("Client", client, ""),
        ("Project shortcode", shortcode, ""),
        ("Documents", len(rows), ""),
        ("Contribs checked", sum(len(r["contribs"]) for r in good), ""),
        ("Off-pattern files", f"{len(off)}/{len(good)}", "warn" if off else "good"),
        issue_chip(n_issues),
    ]
    failed = len(rows) - len(good)
    if failed:
        chips.append(("Failed docs", failed, "warn"))
    chips.append(("Generated", now(), ""))

    out = report_dir / f"{safe_name(client)}_{safe_name(shortcode)}_contrib.html"
    out.write_text(
        page(f"{client} / {shortcode} - contrib report", chips, body, toggle=True),
        encoding="utf-8",
    )
    return out, len(off)


# ------------------------------------------------------------- one document

def read_doc(base: Path, docid: str, item: dict, meta: dict) -> dict:
    """Read + parse one document. Never raises; problems go into row['error']."""
    row = {
        "docid": docid,
        "file_id": meta.get("file-id", ""),
        "folder": doc_folder(base, docid, item, meta),
        "preview_rel": "",
        "cells": None,
        "error": None,
        "contribs": None,
        "raws": [],
        "gaps": [],
        "raw_group": "",
        "issues": [],
        "xkeys": [],
        "cmp_cls": [],
        "xk": {},
        "seqs": [],
        "pat": {},
    }
    folder = row["folder"]
    if not folder.is_dir():
        row["error"] = f"folder not found: {folder}"
        print(f"[MISSING] {docid} - {row['error']}")
        return row

    src, raw = extract_contrib_groups(folder, base, item)
    if not raw:
        row["error"] = "no <contrib-group> found in any xml in folder"
        print(f"[NO CONTRIB] {docid} - {row['error']}")
        return row

    try:
        contribs = parse_contribs(raw)
    except ET.ParseError as e:
        row["error"] = f"contrib-group parse error: {e}"
        print(f"[FAILED] {docid} - {row['error']}")
        return row

    if not contribs:
        row["error"] = "<contrib-group> has no <contrib>"
        print(f"[EMPTY] {docid} - {row['error']}")
        return row

    raws = raw_contribs(raw)
    if len(raws) != len(contribs):
        print(f"[WARN] {docid} - raw/parsed contrib count differs ({len(raws)} vs {len(contribs)})")

    row["contribs"] = contribs
    row["raws"] = raws
    row["raw_group"] = raw
    row["src"] = src.name
    row["gaps"] = [analyze(c) for c in contribs]
    n = len(contribs)
    row["xkeys"] = [xref_key(c) for c in contribs]
    row["cmp_cls"] = [(contrib_class(i, n), row["xkeys"][i]) for i in range(n)]
    row["seqs"] = [pi_sequences(g) for g in row["gaps"]]
    return row


# ------------------------------------------------------ one client + shortcode

def process_group(base: Path, docs: dict, metas: dict, client: str, shortcode: str, docids: list) -> dict:
    """Build per-doc outputs and the ONE report for a client + shortcode."""
    report_dir = base / REPORT_DIR / RUN_DTD
    report_dir.mkdir(parents=True, exist_ok=True)

    rows = [read_doc(base, d, docs[d], metas[d]) for d in docids]
    good = [r for r in rows if r["contribs"]]

    expected = expected_values(
        (cls, gl) for r in good for cls, gl in zip(r["cmp_cls"], r["gaps"])
    )
    stats = build_stats(good) if good else None

    total_issues = 0
    for r in good:
        ctx, issues = build_ctx(r["gaps"], r["cmp_cls"], expected)
        r["issues"] = issues
        write_doc_outputs(r, client, shortcode, ctx, issues)
        r["cells"] = pick_cells(r["contribs"], r["raws"], ctx)
        r["preview_rel"] = Path(os.path.relpath(r["folder"] / OUT_HTML, report_dir)).as_posix()
        total_issues += len(issues)
        tag = f", {len(issues)} consistency issue(s)" if issues else ""
        print(f"[OK] {r['docid']} ({r['src']}) - {len(r['contribs'])} contribs{tag}")

    out, n_off = build_report(client, shortcode, rows, report_dir, stats)
    print(f"[REPORT] {out.relative_to(base)} ({len(rows)} docs, {n_off} off-pattern)")

    return {
        "generated_at": now(),
        "logic": LOGIC_VERSION,
        "report": out.relative_to(base).as_posix(),
        "documents": len(rows),
        "failed": len(rows) - len(good),
        "off_pattern_files": n_off,
        "consistency_issues": total_issues,
        "docids": {
            r["docid"]: {
                "file-id": r["file_id"],
                "contribs": len(r["contribs"]) if r["contribs"] else 0,
                "status": "ok" if r["contribs"] else f"error: {r['error']}",
            }
            for r in rows
        },
    }


# ------------------------------------------------ what is in meta / what is done

def dtd_of(item: dict, meta: dict) -> str:
    return meta.get("dtd") or item.get("folder", "").split("/", 1)[0]


def build_index(docs: dict, metas: dict) -> dict:
    """{client: {shortcode: [docid, ...]}} for RUN_DTD documents only."""
    index: dict = {}
    for docid, meta in metas.items():
        item = docs.get(docid)
        if item is None or dtd_of(item, meta) != RUN_DTD:
            continue
        client = meta.get("client") or "unknown"
        shortcode = meta.get("project-shortcode") or "unknown"
        index.setdefault(client, {}).setdefault(shortcode, []).append(docid)
    return index


def load_done(base: Path) -> dict:
    p = base / DONE_NAME
    return load_json(p) if p.exists() else {}


def save_done(base: Path, data: dict):
    p = base / DONE_NAME
    tmp = p.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, p)  # never leaves a half written file behind


def done_entry(done: dict, client: str, shortcode: str):
    return done.get(RUN_DTD, {}).get(client, {}).get(shortcode)


def status_of(done: dict, client: str, shortcode: str, docids: list):
    """('new'|'update'|'done', number of docids not recorded yet)"""
    e = done_entry(done, client, shortcode)
    if not e:
        return "new", 0
    seen = e.get("docids", {})
    fresh = [d for d in docids if d not in seen]
    if fresh:
        return "update", len(fresh)
    if e.get("logic") != LOGIC_VERSION:  # generated by an older version of the logic
        return "update", 0
    return "done", 0


# ----------------------------------------------------------------- questions

def parse_choice(raw: str, options: list):
    """'1,3' or 'LWW plos' -> matching option names, None if anything is unknown."""
    lookup = {o.lower(): o for o in options}
    out = []
    for part in re.split(r"[,\s]+", raw.strip()):
        if not part:
            continue
        if part.isdigit() and 1 <= int(part) <= len(options):
            name = options[int(part) - 1]
        elif part.lower() in lookup:
            name = lookup[part.lower()]
        else:
            return None
        if name not in out:
            out.append(name)
    return out


def cnt(n: int, word: str = "doc") -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def status_note(done: dict, client: str, shortcode: str, docids: list) -> str:
    st, n = status_of(done, client, shortcode, docids)
    if st == "new":
        return "not filled"
    if st == "update":
        if n == 0:
            return "update (older logic, regenerate)"
        return f"update (+{n} new doc{'' if n == 1 else 's'})"
    e = done_entry(done, client, shortcode)
    bad = f", {e['failed']} failed" if e.get("failed") else ""
    return f"filled {e.get('generated_at', '')}{bad}"


def print_overview(docs: dict, metas: dict, index: dict, done: dict):
    """Unique counts Clients -> Shortcodes and whether each is already filled."""
    clients = sorted(index, key=str.lower)
    pairs = [(c, sc) for c in clients for sc in sorted(index[c], key=str.lower)]
    n_docs = sum(len(v) for scs in index.values() for v in scs.values())
    unique_sc = {sc for _, sc in pairs}
    states = Counter(status_of(done, c, sc, index[c][sc])[0] for c, sc in pairs)

    extra = "" if len(unique_sc) == len(pairs) else f"  ({len(unique_sc)} unique shortcode names)"
    print(f"\n{RUN_DTD} overview:  {len(clients)} clients | {len(pairs)} shortcodes | {n_docs} docs{extra}")
    print(
        f"  filled: {states['done']}  |  not filled: {states['new']}  |  "
        f"update (new docs): {states['update']}"
    )
    print()
    for c in clients:
        scs = index[c]
        filled = sum(status_of(done, c, sc, ids)[0] == "done" for sc, ids in scs.items())
        docs_c = sum(len(v) for v in scs.values())
        print(f"  {c}   {len(scs)} shortcodes, {docs_c} docs   ({filled}/{len(scs)} filled)")
        for sc in sorted(scs, key=str.lower):
            print(f"      {sc:<14}{len(scs[sc]):>6} docs   [{status_note(done, c, sc, scs[sc])}]")

    notes = []
    others = Counter(
        dtd_of(docs[d], m) or "?" for d, m in metas.items() if d in docs and dtd_of(docs[d], m) != RUN_DTD
    )
    if others:
        notes.append("not " + RUN_DTD + ": " + ", ".join(f"{k} {cnt(v)}" for k, v in sorted(others.items())))
    no_meta = sum(1 for d in docs if d not in metas)
    if no_meta:
        notes.append(f"{cnt(no_meta)} without a {META_NAME} entry")
    blank = sum(len(v) for sc_map in index.values() for sc, v in sc_map.items() if sc == "unknown")
    blank += sum(len(v) for c, sc_map in index.items() if c == "unknown" for v in sc_map.values())
    if blank:
        notes.append(f"{cnt(blank)} with a blank client or shortcode (grouped as 'unknown')")
    if notes:
        print("\n  ignored / check: " + "; ".join(notes))


def choose_clients(index: dict, done: dict) -> list:
    clients = sorted(index, key=str.lower)
    print(f"\n{RUN_DTD} clients:")
    for i, c in enumerate(clients, 1):
        scs = index[c]
        pending = sum(status_of(done, c, sc, ids)[0] != "done" for sc, ids in scs.items())
        n_docs = sum(len(v) for v in scs.values())
        tail = f"{pending} to generate" if pending else "all filled"
        print(f"  {i}) {c:<14}{len(scs):>4} shortcodes{n_docs:>8} docs   {tail}")
    while True:
        raw = input("Client (number/name, comma for several, 'all'): ").strip()
        if raw.lower() == "all":
            return clients
        picked = parse_choice(raw, clients)
        if picked:
            return picked
        print("  not recognised, try again")


def choose_shortcodes(clients: list, index: dict, done: dict) -> list:
    """Return the (client, shortcode) pairs to generate."""
    scs = None
    if len(clients) == 1:
        c = clients[0]
        scs = sorted(index[c], key=str.lower)
        print(f"\n{RUN_DTD} / {c} shortcodes:")
        for i, sc in enumerate(scs, 1):
            note = status_note(done, c, sc, index[c][sc])
            print(f"  {i}) {sc:<14}{len(index[c][sc]):>6} docs   [{note}]")
        prompt = (
            "Shortcode (number/name, comma for several; Enter = all not filled/updated; "
            "'all' = regenerate everything): "
        )
    else:
        prompt = (
            f"Shortcodes for {', '.join(clients)} (Enter = all not filled/updated; "
            "'all' = regenerate everything): "
        )

    while True:
        raw = input(prompt).strip()
        low = raw.lower()
        if low in ("", "new", "all"):
            pairs = []
            for c in clients:
                for sc in sorted(index[c], key=str.lower):
                    st, _ = status_of(done, c, sc, index[c][sc])
                    if low == "all" or st != "done":
                        pairs.append((c, sc))
            return pairs
        picked = parse_choice(raw, scs) if scs else None
        if picked:
            pairs = []
            for sc in picked:
                st, _ = status_of(done, clients[0], sc, index[clients[0]][sc])
                if st == "done":
                    ans = input(f"  {sc} is already filled. Regenerate? [y/N]: ").strip().lower()
                    if ans != "y":
                        continue
                pairs.append((clients[0], sc))
            return pairs
        print("  not recognised, try again")


# ---------------------------------------------------------------------- main

def ask_delay(label: str, default: float) -> float:
    while True:
        raw = input(f"{label} in seconds [{default:g}]: ").strip()
        if not raw:
            return default
        try:
            v = float(raw)
            if v >= 0:
                return v
        except ValueError:
            pass
        print("  enter a number of seconds (0 = no pause)")


def pause(seconds: float, why: str):
    if seconds > 0:
        print(f"  ... pausing {seconds:g}s before {why} (Ctrl+C to stop)")
        time.sleep(seconds)


def main():
    base = Path(input("Project Folder: ").strip().strip('"'))
    if not (base / DOCS_NAME).exists() or not (base / META_NAME).exists():
        print(f"Missing {DOCS_NAME} or {META_NAME} in {base}")
        return

    docs = load_json(base / DOCS_NAME)
    metas = load_json(base / META_NAME)
    index = build_index(docs, metas)
    if not index:
        print(f"No {RUN_DTD} documents found in {META_NAME} (is the 'dtd' field filled in?)")
        return

    done = load_done(base)
    print_overview(docs, metas, index, done)

    clients = choose_clients(index, done)
    pairs = choose_shortcodes(clients, index, done)  # already ordered client -> shortcode
    if not pairs:
        print("\nNothing to generate (everything selected is already in "
              f"{DONE_NAME}; pick it by number or type 'all' to redo).")
        return

    total = len(pairs)
    delay_sc = delay_cl = 0.0
    if total > 1:
        print()
        delay_sc = ask_delay("Pause between shortcodes", DELAY_SHORTCODE_SEC)
        if len({c for c, _ in pairs}) > 1:
            delay_cl = ask_delay("Pause between clients", DELAY_CLIENT_SEC)

    left: Counter = Counter(c for c, _ in pairs)
    finished = []
    try:
        for i, (client, shortcode) in enumerate(pairs, 1):
            ids = index[client][shortcode]
            print(f"\n=== [{i}/{total}] {RUN_DTD} / {client} / {shortcode} ({cnt(len(ids))}) ===")
            entry = process_group(base, docs, metas, client, shortcode, ids)
            if entry["failed"] == entry["documents"]:
                print(f"[SKIP RECORD] every document failed, {shortcode} not marked as filled")
            else:
                done.setdefault(RUN_DTD, {}).setdefault(client, {})[shortcode] = entry
                save_done(base, done)  # recorded BEFORE the pause, so a stop keeps it
            finished.append((client, shortcode, entry))

            left[client] -= 1
            if left[client] == 0:
                print(f"[CLIENT COMPLETE] {client}")
            if i < total:
                nxt_client, nxt_sc = pairs[i]
                if nxt_client != client:
                    pause(delay_cl, f"client {nxt_client}")
                else:
                    pause(delay_sc, f"shortcode {nxt_client}/{nxt_sc}")
    except KeyboardInterrupt:
        print("\nStopped by user. Finished shortcodes are already saved in " + DONE_NAME)

    print(f"\nSummary ({len(finished)}/{total} shortcodes processed):")
    for client, shortcode, e in finished:
        print(
            f"  {client} / {shortcode:<12} {e['documents']:>5} docs  {e['failed']:>3} failed  "
            f"{e['off_pattern_files']:>3} off-pattern  -> {e['report']}"
        )
    print(f"Progress saved in {DONE_NAME}")


if __name__ == "__main__":
    main()
