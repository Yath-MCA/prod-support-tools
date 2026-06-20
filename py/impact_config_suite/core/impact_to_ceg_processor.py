import json
import logging
import os
import sys

from core.pgm_processor import PGMProcessor

logger = logging.getLogger(__name__)


class ImpactToCEGProcessor(PGMProcessor):
    """
    Convert IMPACT HTML into CEG/PGM-compatible HTML.

    Existing attributes are preserved under data-impact-*; id remains a normal
    id, and the original tag name is stored in data-impact-tag.
    """
    def __init__(self):
        super().__init__()
        self._runtime_extra_mapping = {}
        self._impact_to_ceg_mapping = self._load_impact_to_ceg_mapping()
        self.cleanup_details = []

    def process_file(self, input_path: str, output_path: str, extra_mapping: dict | None = None) -> dict:
        self.cleanup_details = []
        result = super().process_file(input_path, output_path, extra_mapping)
        result['cleanup_details'].extend(self.cleanup_details)
        return result

    def _apply_style_mapping(self, body, extra_mapping: dict | None = None) -> None:
        self._runtime_extra_mapping = extra_mapping or {}

    def _transform_tag(self, tag) -> bool:
        tag_name = tag.name.lower() if tag.name else ''

        if self._is_ignored_tag_or_descendant(tag):
            return True

        original_attrs = dict(tag.attrs)
        original_tag_name = self._local_tag_name(tag)

        tag.attrs.clear()
        for attr, value in original_attrs.items():
            attr_lower = attr.lower()
            if attr_lower == 'id':
                tag[attr] = value
                continue
            if attr_lower.startswith('data-impact-'):
                if attr not in tag.attrs:
                    tag[attr] = value
                continue

            target_attr = self._impact_attr_name(attr)
            if target_attr in tag.attrs:
                continue
            tag[target_attr] = self._stringify_attr_value(value)

        if 'data-impact-tag' not in tag.attrs:
            tag['data-impact-tag'] = original_tag_name or tag_name

        self._apply_json_style_mapping(tag)
        self._apply_hide_style(tag)
        return False

    def _impact_attr_name(self, attr: str) -> str:
        attr_lower = attr.lower()
        if attr_lower.startswith('data-'):
            return f"data-impact-{attr[5:]}"
        return f"data-impact-{attr}"

    def _apply_json_style_mapping(self, tag) -> None:
        matched_rules = []
        for order_index, (rule_name, rule) in enumerate(self._iter_mapping_rules()):
            if not isinstance(rule, dict):
                continue
            if not self._tag_matches_rule(tag, rule):
                continue
            score = self._rule_specificity(rule)
            matched_rules.append((score, order_index, rule_name, rule))

        if not matched_rules:
            return

        # Apply all matching rules from least specific to most specific so
        # generic structure rules can run first and targeted overrides can win.
        matched_rules.sort(key=lambda item: (item[0], item[1]))

        applied_rule_names = []
        changes = []
        for _score, _order_index, rule_name, rule in matched_rules:
            applied_rule_names.append(rule_name)
            self._apply_single_rule(tag, rule, changes)

        if changes:
            self.cleanup_details.append({
                'action': 'apply_rule',
                'tag': tag.name,
                'details': f"Applied rule(s) {applied_rule_names}: {'; '.join(changes)}"
            })

    def _apply_single_rule(self, tag, rule: dict, changes: list[str]) -> None:
        new_tag = rule.get('tag')
        if isinstance(new_tag, str) and new_tag:
            changes.append(f"changed tag name to {new_tag}")
            tag.name = new_tag

        attrs = rule.get('attrs', {})
        if isinstance(attrs, dict):
            for attr, value in attrs.items():
                tag[attr] = self._stringify_attr_value(value)
            if attrs:
                changes.append(f"added attributes {list(attrs.keys())}")

        self._insert_child_nodes(tag, rule)
        self._insert_after_nodes(tag, rule)
        self._wrap_tag_content(tag, rule)

    def _iter_mapping_rules(self):
        for group_name in ('display', 'inline'):
            group = self._impact_to_ceg_mapping.get(group_name, {})
            if isinstance(group, dict):
                yield from group.items()

        for group_name in ('display', 'inline'):
            group = self._runtime_extra_mapping.get(group_name, {})
            if isinstance(group, dict):
                yield from group.items()

    def _apply_hide_style(self, tag) -> None:
        for rule in self._iter_hide_rules():
            if self._tag_matches_hide_rule(tag, rule):
                tag['style'] = 'display:none'
                self.cleanup_details.append({
                    'action': 'hide_element',
                    'tag': tag.name,
                    'details': f"Applied hide rule to element with attrs {dict(tag.attrs)}"
                })
                return

    def _iter_hide_rules(self):
        hide_rules = self._impact_to_ceg_mapping.get('hide', [])
        if isinstance(hide_rules, list):
            yield from hide_rules

        runtime_hide_rules = self._runtime_extra_mapping.get('hide', [])
        if isinstance(runtime_hide_rules, list):
            yield from runtime_hide_rules

    def _tag_matches_hide_rule(self, tag, rule) -> bool:
        if not isinstance(rule, dict):
            return False

        match_attrs = rule.get('match', {})
        if isinstance(match_attrs, dict) and match_attrs:
            if not self._attrs_match(tag, match_attrs):
                return False

        child_match_attrs = rule.get('child_match', {})
        if isinstance(child_match_attrs, dict) and child_match_attrs:
            child_tag = rule.get('child_tag')
            if isinstance(child_tag, str) and child_tag:
                children = tag.find_all(child_tag, recursive=True)
            else:
                children = tag.find_all(True, recursive=True)

            return any(self._attrs_match(child, child_match_attrs) for child in children)

        return True

    def _tag_matches_rule(self, tag, rule: dict) -> bool:
        match_attrs = rule.get('match', {})
        if not isinstance(match_attrs, dict) or not match_attrs:
            return False

        if not self._attrs_match(tag, match_attrs):
            return False

        parent_match_attrs = rule.get('parent_match', {})
        if isinstance(parent_match_attrs, dict) and parent_match_attrs:
            parent = getattr(tag, 'parent', None)
            if parent is None or not self._attrs_match(parent, parent_match_attrs):
                return False
        grandparent_match_attrs = rule.get('grandparent_match', {})
        if isinstance(grandparent_match_attrs, dict) and grandparent_match_attrs:
            grandparent = getattr(getattr(tag, 'parent', None), 'parent', None)
            if grandparent is None or not self._attrs_match(grandparent, grandparent_match_attrs):
                return False
        ancestor_match = rule.get('ancestor_match', {})
        if not self._ancestor_rule_matches(tag, ancestor_match):
            return False
        root_match = rule.get('root_match', {})
        if not self._ancestor_rule_matches(tag, root_match):
            return False
        return True

    def _attrs_match(self, tag, match_attrs: dict) -> bool:
        for attr, expected in match_attrs.items():
            actual = self._stringify_attr_value(tag.get(attr, ''))
            if isinstance(expected, list):
                expected_values = {self._stringify_attr_value(item) for item in expected}
                if self._is_token_attr(attr):
                    actual_values = set(actual.split())
                    if not actual_values.intersection(expected_values):
                        return False
                elif actual not in expected_values:
                    return False
            elif self._is_token_attr(attr):
                if self._stringify_attr_value(expected) not in actual.split():
                    return False
            elif actual != self._stringify_attr_value(expected):
                return False
        return True

    def _is_token_attr(self, attr: str) -> bool:
        return attr in {'class', 'data-impact-class'}

    def _rule_specificity(self, rule: dict) -> int:
        score = self._match_specificity(rule.get('match', {}))
        score += 10 * self._match_specificity(rule.get('parent_match', {}))
        score += 20 * self._match_specificity(rule.get('grandparent_match', {}))
        score += 5 * self._ancestor_specificity(rule.get('ancestor_match', {}))
        score += 5 * self._ancestor_specificity(rule.get('root_match', {}))
        return score

    def _match_specificity(self, match_attrs) -> int:
        return len(match_attrs) if isinstance(match_attrs, dict) else 0

    def _ancestor_specificity(self, ancestor_match) -> int:
        if isinstance(ancestor_match, dict):
            return self._match_specificity(ancestor_match)
        if isinstance(ancestor_match, list):
            return max((self._match_specificity(item) for item in ancestor_match if isinstance(item, dict)), default=0)
        return 0

    def _ancestor_rule_matches(self, tag, ancestor_match) -> bool:
        if not ancestor_match:
            return True

        if isinstance(ancestor_match, dict):
            return self._has_matching_ancestor(tag, ancestor_match)

        if isinstance(ancestor_match, list):
            match_items = [item for item in ancestor_match if isinstance(item, dict)]
            if not match_items:
                return True
            return any(self._has_matching_ancestor(tag, item) for item in match_items)

        return True

    def _has_matching_ancestor(self, tag, match_attrs: dict) -> bool:
        for ancestor in getattr(tag, 'parents', []):
            if self._attrs_match(ancestor, match_attrs):
                return True
        return False

    def _insert_child_nodes(self, tag, rule: dict) -> None:
        for insert_mode in ('prepend', 'append'):
            children = rule.get(insert_mode, [])
            if not isinstance(children, list):
                continue
            for child_spec in children:
                child = self._build_child_node(tag, child_spec)
                if child is None:
                    continue
                if self._has_matching_child(tag, child):
                    continue
                if insert_mode == 'prepend':
                    tag.insert(0, child)
                else:
                    tag.append(child)

    def _insert_after_nodes(self, tag, rule: dict) -> None:
        children = rule.get('after', [])
        if not isinstance(children, list):
            return
        for child_spec in children:
            child = self._build_child_node(tag, child_spec)
            if child is None:
                continue
            if self._has_matching_after(tag, child):
                continue
            tag.insert_after(child)

    def _has_matching_after(self, tag, child) -> bool:
        child_class = self._stringify_attr_value(child.get('class', ''))
        child_data_name = self._stringify_attr_value(child.get('data-name', ''))
        child_text = child.get_text('', strip=True)

        sibling = tag.next_sibling
        while sibling is not None:
            if getattr(sibling, 'name', None) == child.name:
                if (
                    self._stringify_attr_value(sibling.get('class', '')) == child_class
                    and self._stringify_attr_value(sibling.get('data-name', '')) == child_data_name
                    and sibling.get_text('', strip=True) == child_text
                ):
                    return True
            sibling = sibling.next_sibling
        return False

    def _wrap_tag_content(self, tag, rule: dict) -> None:
        """Wrap the tag's current content in a new wrapper element."""
        wrap_spec = rule.get('wrap')
        if not isinstance(wrap_spec, dict):
            return

        wrap_tag_name = wrap_spec.get('tag')
        if not isinstance(wrap_tag_name, str) or not wrap_tag_name:
            return

        # Don't wrap if already wrapped by this rule (check for wrapper already present)
        if len(tag.contents) == 1:
            first_child = tag.contents[0]
            if hasattr(first_child, 'name') and first_child.name == wrap_tag_name:
                wrap_attrs = wrap_spec.get('attrs', {})
                if isinstance(wrap_attrs, dict):
                    has_all_attrs = all(
                        self._stringify_attr_value(first_child.get(attr, '')) == self._stringify_attr_value(value)
                        for attr, value in wrap_attrs.items()
                    )
                    if has_all_attrs:
                        return  # Already wrapped

        # Create wrapper tag
        soup = self._owner_soup(tag)
        wrapper = soup.new_tag(wrap_tag_name)

        # Apply wrapper attributes
        wrap_attrs = wrap_spec.get('attrs', {})
        if isinstance(wrap_attrs, dict):
            for attr, value in wrap_attrs.items():
                wrapper[attr] = self._stringify_attr_value(value)

        # Move all current children into wrapper
        for child in list(tag.children):
            wrapper.append(child)

        # Add wrapper as the only child of original tag
        tag.append(wrapper)

    def _build_child_node(self, tag, child_spec):
        if not isinstance(child_spec, dict):
            return None

        child_tag_name = child_spec.get('tag')
        if not isinstance(child_tag_name, str) or not child_tag_name:
            return None

        text = self._child_text_value(tag, child_spec)
        if text == '':
            return None

        soup = self._owner_soup(tag)
        child = soup.new_tag(child_tag_name)
        attrs = child_spec.get('attrs', {})
        if isinstance(attrs, dict):
            for attr, value in attrs.items():
                child[attr] = self._stringify_attr_value(value)
        child.string = text
        return child

    def _child_text_value(self, tag, child_spec: dict) -> str:
           # Prefer explicit 'value'
        if 'value' in child_spec:
            return str(child_spec['value'])
        if 'text' in child_spec:
            return self._stringify_attr_value(child_spec.get('text'))

        text_from = child_spec.get('text_from') or child_spec.get('textFrom')
        if isinstance(text_from, str) and text_from:
            return self._stringify_attr_value(tag.get(text_from, ''))

        return ''

    def _has_matching_child(self, tag, child) -> bool:
        child_class = self._stringify_attr_value(child.get('class', ''))
        child_data_name = self._stringify_attr_value(child.get('data-name', ''))
        child_text = child.get_text('', strip=True)

        for existing in tag.find_all(child.name, recursive=False):
            if (
                self._stringify_attr_value(existing.get('class', '')) == child_class
                and self._stringify_attr_value(existing.get('data-name', '')) == child_data_name
                and existing.get_text('', strip=True) == child_text
            ):
                return True
        return False

    def _owner_soup(self, tag):
        for parent in [tag] + list(getattr(tag, 'parents', [])):
            if callable(getattr(parent, 'new_tag', None)):
                return parent
        raise RuntimeError('Unable to find BeautifulSoup owner for tag insertion.')

    def process_directory(self, input_dir: str, output_dir: str, callback=None, extra_mapping: dict | None = None):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        extensions = ('.html', '.xhtml', '.xml', '.htm')
        processed_count = 0
        error_count = 0
        file_results = []

        for root, _, files in os.walk(input_dir):
            for file in files:
                if not file.lower().endswith(extensions):
                    continue

                input_path = os.path.join(root, file)
                rel_path = os.path.relpath(input_path, input_dir)
                rel_path_xhtml = os.path.splitext(rel_path)[0] + '.xhtml'
                output_path = os.path.join(output_dir, rel_path_xhtml)

                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                if callback:
                    callback(f"Processing: {rel_path}")

                result = self.process_file(input_path, output_path, extra_mapping)
                result['relative_path'] = rel_path
                file_results.append(result)
                if result['ok']:
                    processed_count += 1
                    if callback:
                        callback(
                            f"  ✔ Done — {result['tags_processed']} transformed, "
                            f"{result['tags_skipped']} skipped, "
                            f"{result['bkmark_removed']} bookmarks removed, "
                            f"{result.get('tab_spans_removed', 0)} tabs removed, "
                            f"{result['style_removed']} styles removed, "
                            f"{result['font_spans_unwrapped']} spans unwrapped"
                        )
                else:
                    error_count += 1
                    if callback:
                        callback(f"  ✘ Error: {result['error']}")

        return processed_count, error_count, file_results

    def _load_impact_to_ceg_mapping(self) -> dict:
        candidate_paths = self._impact_to_ceg_mapping_candidates()
        last_error = None
        for mapping_path in candidate_paths:
            if not os.path.exists(mapping_path):
                continue
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                try:
                    mapping = json.loads(text)
                except json.JSONDecodeError:
                    cleaned_text = self._strip_trailing_commas(text)
                    mapping = json.loads(cleaned_text)
                return mapping if isinstance(mapping, dict) else {}
            except Exception as e:
                last_error = e
                logger.error(f"Failed to load impact_to_ceg mapping from {mapping_path}: {e}")

        if last_error is None:
            logger.error(
                "Failed to load impact_to_ceg mapping: no candidate path found. Tried %s",
                candidate_paths,
            )
        return {}

    def _impact_to_ceg_mapping_candidates(self) -> list[str]:
        candidates = []

        meipass = getattr(sys, '_MEIPASS', '')
        if meipass:
            candidates.append(os.path.join(meipass, 'impact_to_ceg.json'))

        module_dir = os.path.dirname(__file__)
        package_root = os.path.dirname(module_dir)
        candidates.append(os.path.join(package_root, 'impact_to_ceg.json'))
        candidates.append(os.path.join(module_dir, 'impact_to_ceg.json'))
        candidates.append(os.path.join(os.getcwd(), 'impact_to_ceg.json'))

        # Preserve order while removing duplicates.
        unique_candidates = []
        for path in candidates:
            if path not in unique_candidates:
                unique_candidates.append(path)
        return unique_candidates

    def _strip_trailing_commas(self, text: str) -> str:
        cleaned = []
        in_string = False
        escape = False
        for char in text:
            if escape:
                cleaned.append(char)
                escape = False
                continue
            if char == '\\':
                cleaned.append(char)
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                cleaned.append(char)
                continue
            if not in_string and char in '}]':
                idx = len(cleaned) - 1
                while idx >= 0 and cleaned[idx].isspace():
                    idx -= 1
                if idx >= 0 and cleaned[idx] == ',':
                    del cleaned[idx]
                cleaned.append(char)
                continue
            cleaned.append(char)
        return ''.join(cleaned)
