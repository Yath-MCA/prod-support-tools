\"\"\"
contrib_regen_pi.py - Class-based PI regen for contrib-group extracts.

Canonical config form is Option B: explicit classname on <separator>:

    <separator classname=\"given-names\" value=\"...\" pos=\"inner\"/>

Legacy tag-as-kind form (<given-names .../>) is still accepted during migration
and maps the element tag name to classname. Missing/blank classname on a
<separator> element is rejected.
\"\"\"
from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

# ---------------------------------------------------------------------------
# Errors / data model
# ---------------------------------------------------------------------------


class RegenPiError(Exception):
    \"\"\"Raised for pi-config parse or regen errors.\"\"\"


@dataclass
class RegenPiSelector:
    \"\"\"Selector for a separator rule. classname is required and non-blank.\"\"\"

    classname: str
    pos: str = \"after\"  # inner | after
    contribs: Optional[str] = None  # \"1\" | \"2\" | \"3+\" | None (any)
    when: Optional[str] = None  # last-before | last | None

    def __post_init__(self) -> None:
        cn = (self.classname or \"\").strip()
        if not cn:
            raise RegenPiError(
                \"classname is required and must be non-blank "
                \"(Option B: <separator classname=\\\"...\\\" .../>)\"
            )
        self.classname = cn
        self.pos = (self.pos or \"after\").strip().lower() or \"after\"
        if self.when is not None and self.when.strip() == \"\":
            self.when = None
        if self.contribs is not None and str(self.contribs).strip() == \"\":
            self.contribs = None


@dataclass
class RegenPiRule:
    \"\"\"A separator value paired with its selector.\"\"\"

    selector: RegenPiSelector
    value: str  # unescaped text carried by the PI

    # Flat accessors for SeparatorRule / callers that used kind/pos/contribs/when.
    @property
    def kind(self) -> str:
        return self.selector.classname

    @property
    def classname(self) -> str:
        return self.selector.classname

    @property
    def pos(self) -> str:
        return self.selector.pos

    @property
    def contribs(self) -> Optional[str]:
        return self.selector.contribs

    @property
    def when(self) -> Optional[str]:
        return self.selector.when

    @classmethod
    def from_flat(
        cls,
        *,
        classname: str,
        value: str,
        pos: str = \"after\",
        contribs: Optional[str] = None,
        when: Optional[str] = None,
    ) -> \"RegenPiRule\":
        return cls(
            selector=RegenPiSelector(
                classname=classname, pos=pos, contribs=contribs, when=when
            ),
            value=value,
        )


@dataclass
class RegenPiConfig:
    \"\"\"Parsed pi-config for one client/shortcode.\"\"\"

    client: str
    shortcode: str
    dtd: str = \"\"
    version: str = \"\"
    status: str = \"\"
    elements: Dict[str, bool] = field(default_factory=dict)
    ques: Dict[str, bool] = field(default_factory=dict)
    rules: List[RegenPiRule] = field(default_factory=list)

    # --- Compatibility with former PiConfig ---
    @property
    def separators(self) -> List[RegenPiRule]:
        \"\"\"Alias for rules (SeparatorRule-compatible via .kind/.value/...).\"\"\"
        return self.rules

    def separators_of(self, kind: str) -> List[RegenPiRule]:
        return [r for r in self.rules if r.classname == kind]

    def select(self, classname: str) -> List[RegenPiRule]:
        cn = (classname or \"\").strip()
        if not cn:
            raise RegenPiError(\"select() requires a non-blank classname\")
        return [r for r in self.rules if r.classname == cn]


# Compatibility aliases (former phase0 names).
PiConfig = RegenPiConfig
SeparatorRule = RegenPiRule


# ---------------------------------------------------------------------------
# Regex helpers (ported from contrib_phase0 regen helpers)
# ---------------------------------------------------------------------------

_CONTRIB_RE = re.compile(r\"<contrib\\b[^>]*>.*?</contrib>\", re.IGNORECASE | re.DOTALL)
_XREF_RE = re.compile(
    r\"<xref\\b[^>]*/>|<xref\\b[^>]*>.*?</xref>\",
    re.IGNORECASE | re.DOTALL,
)
_GIVEN_CLOSE_RE = re.compile(r\"</given-names>\", re.IGNORECASE)
_GIVEN_EMPTY_RE = re.compile(r\"<given-names(\\s[^>]*)?\\s*/>\", re.IGNORECASE)

_DEFAULT_SUITE_ROOT = Path(__file__).resolve().parent.parent


def _allowed_flag(raw: Optional[str]) -> bool:
    return (raw or \"\").strip().lower() in {\"yes\", \"true\", \"1\"}


def format_pi_attr_value(value: str) -> str:
    \"\"\"Serialize PI text for xml:space=\\\"...\\\". NBSP as &#x00A0; to match samples.\"\"\"
    if value == \"\\u00a0\":
        return \"&#x00A0;\"
    return (
        value.replace(\"&\", \"&amp;\")
        .replace('\"', \"&quot;\")
        .replace(\"<\", \"&lt;\")
    )


def make_pistart(value: str) -> str:
    \"\"\"Build a pistart PI matching strip_pi / extractor conventions.\"\"\"
    return f'<?pistart xml:space=\"{format_pi_attr_value(value)}\"?>'


def resolve_pi_config_path(
    client: str,
    shortcode: str,
    project_base: Path | None = None,
    suite_root: Path | None = None,
) -> Path | None:
    \"\"\"Prefer project override, else suite bundled template.\"\"\"
    name = f\"{client}_{shortcode}.xml\"
    candidates: List[Path] = []
    if project_base is not None:
        candidates.append(Path(project_base) / \"contrib_config\" / name)
    root = Path(suite_root) if suite_root is not None else _DEFAULT_SUITE_ROOT
    candidates.append(root / \"contrib_config\" / name)
    for p in candidates:
        if p.is_file():
            return p
    return None


def parse_pi_config_xml(text: str) -> RegenPiConfig:
    \"\"\"Parse pi-config XML (Option B canonical; legacy tag-as-kind accepted).\"\"\"
    root = ET.fromstring(text)
    if root.tag != \"pi-config\":
        found = root.find(\".//pi-config\")
        if found is None:
            raise RegenPiError(f\"expected <pi-config>, got <{root.tag}>\")
        root = found

    cfg = RegenPiConfig(
        client=root.get(\"client\") or \"\",
        shortcode=root.get(\"shortcode\") or \"\",
        dtd=root.get(\"dtd\") or \"\",
        version=root.get(\"version\") or \"\",
        status=root.get(\"status\") or \"\",
    )
    contrib = root.find(\"contrib\")
    if contrib is None:
        return cfg

    elems = contrib.find(\"elements\")
    if elems is not None:
        for child in list(elems):
            cfg.elements[child.tag] = _allowed_flag(child.get(\"allowed\"))

    ques = contrib.find(\"ques\")
    if ques is not None:
        for child in list(ques):
            cfg.ques[child.tag] = _allowed_flag(child.get(\"allowed\"))

    seps = contrib.find(\"separators\")
    if seps is not None:
        for child in list(seps):
            cfg.rules.append(_parse_separator_child(child))
    return cfg


def _parse_separator_child(child: ET.Element) -> RegenPiRule:
    \"\"\"Parse one separators child as Option B or legacy tag-as-kind.\"\"\"
    tag = child.tag
    raw_val = child.get(\"value\")
    if raw_val is None:
        raw_val = \"\"
    when_raw = child.get(\"when\")
    pos = (child.get(\"pos\") or \"after\").strip().lower()
    contribs = child.get(\"contribs\")

    if tag == \"separator\":
        # Option B (canonical): classname attribute required.
        classname = child.get(\"classname\")
        if classname is None or not str(classname).strip():
            raise RegenPiError(
                \"<separator> requires a non-blank classname attribute "
                '(Option B: <separator classname=\"...\" value=\"...\"/>)'
            )
        classname = str(classname).strip()
    else:
        # Legacy: element tag name is the kind/classname.
        classname = tag

    return RegenPiRule.from_flat(
        classname=classname,
        value=html.unescape(raw_val),
        pos=pos,
        contribs=contribs,
        when=when_raw if when_raw else None,
    )


def load_pi_config(
    client: str,
    shortcode: str,
    project_base: Path | None = None,
    suite_root: Path | None = None,
) -> RegenPiConfig | None:
    \"\"\"Load and parse pi-config for client/shortcode, or None if not found.\"\"\"
    path = resolve_pi_config_path(client, shortcode, project_base, suite_root)
    if path is None:
        return None
    return parse_pi_config_xml(path.read_text(encoding=\"utf-8\"))


def _contribs_match(rule_contribs: Optional[str], n: int) -> bool:
    if rule_contribs is None or rule_contribs == \"\":
        return True
    rc = rule_contribs.strip()
    if rc.endswith(\"+\"):
        try:
            return n >= int(rc[:-1])
        except ValueError:
            return False
    try:
        return n == int(rc)
    except ValueError:
        return False


def pick_between_contribs_rule(
    rules: List[RegenPiRule], index: int, n: int
) -> RegenPiRule | None:
    \"\"\"Choose between-contribs rule for contrib at 0-based index among n.\"\"\"
    if n <= 0:
        return None
    is_last = index == n - 1
    is_last_before = n >= 2 and index == n - 2

    if is_last:
        for r in rules:
            if r.when == \"last\" and _contribs_match(r.contribs, n):
                return r
    if is_last_before:
        for r in rules:
            if r.when == \"last-before\" and _contribs_match(r.contribs, n):
                return r
    if not is_last:
        for r in rules:
            if not r.when and _contribs_match(r.contribs, n):
                return r
    return None


def _insert_given_names_pis(text: str, rule: RegenPiRule) -> str:
    if rule.pos != \"inner\":
        return text
    pi = make_pistart(rule.value)

    def expand_empty(m: re.Match) -> str:
        attrs = m.group(1) or \"\"
        return f\"<given-names{attrs}>{pi}</given-names>\"

    text = _GIVEN_EMPTY_RE.sub(expand_empty, text)
    text = _GIVEN_CLOSE_RE.sub(pi + \"</given-names>\", text)
    return text


def _insert_xref_pis(contrib_xml: str, rule: RegenPiRule) -> str:
    if rule.pos != \"after\":
        return contrib_xml
    matches = list(_XREF_RE.finditer(contrib_xml))
    if len(matches) < 2:
        return contrib_xml
    pi = make_pistart(rule.value)
    parts: List[str] = []
    last = 0
    for i, m in enumerate(matches):
        parts.append(contrib_xml[last : m.end()])
        if i < len(matches) - 1:
            parts.append(pi)
        last = m.end()
    parts.append(contrib_xml[last:])
    return \"\".join(parts)


def _insert_between_contribs(text: str, rules: List[RegenPiRule]) -> str:
    matches = list(_CONTRIB_RE.finditer(text))
    n = len(matches)
    if n == 0 or not rules:
        return text
    # Insert from the end so earlier offsets stay valid.
    out = text
    for i in range(n - 1, -1, -1):
        rule = pick_between_contribs_rule(rules, i, n)
        if rule is None:
            continue
        pi = make_pistart(rule.value)
        end = matches[i].end()
        out = out[:end] + pi + out[end:]
    return out


def regen_contrib_group(strip_xml: str, config: RegenPiConfig) -> str:
    \"\"\"Rebuild contrib-group XML from strip_pi by inserting separator PIs.

    Focus: separators only (given-names, between-xrefs, between-contribs).
    Non-contrib siblings of contrib-group are left in place.
    \"\"\"
    return RegenPi(config).regen(strip_xml)


# ---------------------------------------------------------------------------
# RegenPi facade
# ---------------------------------------------------------------------------


class RegenPi:
    \"\"\"Load pi-config and regenerate separator PIs into strip_xml.\"\"\"

    def __init__(self, config: RegenPiConfig) -> None:
        self.config = config

    @classmethod
    def from_xml_path(cls, path: Union[str, Path]) -> \"RegenPi\":
        p = Path(path)
        text = p.read_text(encoding=\"utf-8\")
        return cls(parse_pi_config_xml(text))

    @classmethod
    def for_client_shortcode(
        cls,
        client: str,
        shortcode: str,
        project_base: Path | None = None,
        suite_root: Path | None = None,
    ) -> Optional[\"RegenPi\"]:
        cfg = load_pi_config(
            client, shortcode, project_base=project_base, suite_root=suite_root
        )
        if cfg is None:
            return None
        return cls(cfg)

    def select(self, classname: str) -> List[RegenPiRule]:
        \"\"\"Return rules whose classname matches (required, non-blank).\"\"\"
        return self.config.select(classname)

    def regen(self, strip_xml: str) -> str:
        \"\"\"Rebuild contrib-group XML from strip_pi by inserting separator PIs.\"\"\"
        text = strip_xml
        cfg = self.config

        gn_rules = cfg.select(\"given-names\")
        if gn_rules:
            text = _insert_given_names_pis(text, gn_rules[0])

        xref_rules = cfg.select(\"between-xrefs\")
        if xref_rules:
            rule = xref_rules[0]

            def _one_contrib(m: re.Match) -> str:
                return _insert_xref_pis(m.group(0), rule)

            text = _CONTRIB_RE.sub(_one_contrib, text)

        bc_rules = cfg.select(\"between-contribs\")
        if bc_rules:
            text = _insert_between_contribs(text, bc_rules)

        return text

    @staticmethod
    def make_pistart(value: str) -> str:
        return make_pistart(value)
