import os
import re
from bs4 import BeautifulSoup, Comment
import json
import logging


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Tags inside <body> that are skipped from attribute transformation
# (no data-pgm-* cloning, no class/data-name injection)
IGNORED_TAGS = {'header', 'style', 'title', 'meta', 'link', 'del', 'ins', 'insert'}

# Attributes that must NOT be cloned to data-pgm-*
# - Table structural attrs that CKEditor/browsers rely on for layout
# - data-* attrs are also excluded (handled inline) to avoid data-pgm-data-col ugliness
# Note: 'id' is handled separately — it is never cloned.
NO_CLONE_ATTRS = {'rowspan', 'colspan', 'width', 'data-col', 'data-split', 'data-label'}


class PGMProcessor:
    def __init__(self):
        pass

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def process_file(self, input_path: str, output_path: str, extra_mapping: dict | None = None) -> dict:
        """
        Reads an HTML/XHTML file, applies transformation rules, and saves to output_path.

        Transformation is scoped ONLY to elements inside <body>.

        Returns a result dict:
          { 'ok': bool, 'tags_processed': int, 'tags_skipped': int,
            'bkmark_removed': int, 'style_removed': int,
            'font_spans_unwrapped': int, 'cleanup_details': list,
            'cleanup_segments': list, 'error': str|None }
        """
        result = {
            'ok': False,
            'input_path': input_path,
            'output_path': output_path,
            'tags_processed': 0,
            'tags_skipped': 0,
            'bkmark_removed': 0,
            'tab_spans_removed': 0,
            'style_removed': 0,
            'font_spans_unwrapped': 0,
            'span_unwrapped': 0,
            'cleanup_details': [],
            'cleanup_segments': [],
            'error': None,
        }
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse — use lxml-xml for xhtml/xml, lxml for html
            is_xml = input_path.lower().endswith(('.xml', '.xhtml'))
            soup = BeautifulSoup(content, 'lxml-xml' if is_xml else 'lxml')

            body = soup.find('body')
            if body is None:
                # Fallback: treat whole document as body scope
                body = soup

            # Phase 1: Remove bookmark spans
            result['bkmark_removed'] = self._remove_bookmark_spans(
                body, result['cleanup_details']
            )
            result['tab_spans_removed'] = self._remove_empty_tab_spans(
                body, result['cleanup_details']
            )

            style_only_spans_unwrapped = self._unwrap_style_only_spans(
                body, result['cleanup_details']
            )
            
            # Phase 1a: Remove 'style' attribute from ALL elements
            result['style_removed'] = self._remove_all_style_attributes(
                body, result['cleanup_details']
            )

            # Apply style class mappings
            self._apply_style_mapping(body, extra_mapping)



            # ── Phase 3: Transform remaining body elements ───────────────
            for tag in body.find_all(True):
                skipped = self._transform_tag(tag)
                if skipped:
                    result['tags_skipped'] += 1
                else:
                    result['tags_processed'] += 1

            # Final cleanup: unwrap placeholder spans that carry only empty
            # IMPACT defaults such as <span class="" data-name="">...</span>.
            result['font_spans_unwrapped'] = (
                style_only_spans_unwrapped
                + self._unwrap_style_spans(
                body, result['cleanup_details']
                )
            )
            result['span_unwrapped'] = result['font_spans_unwrapped']
            result['cleanup_segments'] = self._summarize_cleanup_segments(
                result['cleanup_details']
            )

            output_html, final_style_only_unwrapped = self._unwrap_style_only_span_markup(
                str(soup)
            )
            output_html, final_mso_styles_removed = self._remove_mso_style_attributes_from_markup(
                output_html
            )
            if final_style_only_unwrapped:
                result['font_spans_unwrapped'] += final_style_only_unwrapped
                result['span_unwrapped'] = result['font_spans_unwrapped']
                for _ in range(final_style_only_unwrapped):
                    result['cleanup_details'].append({
                        'segment': 'Body / document',
                        'action': 'unwrap_element',
                        'target': 'span[style]',
                        'tag': 'span',
                        'path': 'final output cleanup',
                        'value': '',
                        'text': '',
                    })
                result['cleanup_segments'] = self._summarize_cleanup_segments(
                    result['cleanup_details']
                )
            if final_mso_styles_removed:
                result['style_removed'] += final_mso_styles_removed
                for _ in range(final_mso_styles_removed):
                    result['cleanup_details'].append({
                        'segment': 'Body / document',
                        'action': 'remove_attribute',
                        'target': 'style',
                        'tag': '',
                        'path': 'final output cleanup',
                        'value': 'mso-fareast-font-family:Times New Roman',
                        'text': '',
                    })
                result['cleanup_segments'] = self._summarize_cleanup_segments(
                    result['cleanup_details']
                )

            # Save output
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_html)

            result['ok'] = True

        except Exception as e:
            logger.error(f"Error processing file {input_path}: {e}")
            result['error'] = str(e)

        return result

    # ------------------------------------------------------------------ #
    #  Phase 1 — Remove bookmark spans                                    #
    # ------------------------------------------------------------------ #

    def _remove_bookmark_spans(self, body, details=None) -> int:
        """
        Remove all <span data-bkmark="..."> elements entirely (decompose).
        Returns count of removed elements.
        """
        removed = 0
        for span in body.find_all('span', attrs={'data-bkmark': True}):
            if self._is_ignored_tag_or_descendant(span):
                continue
            self._add_cleanup_detail(
                details,
                action='remove_element',
                element=span,
                target='span[data-bkmark]',
                value=span.get('data-bkmark', ''),
            )
            span.decompose()
            removed += 1
        return removed

    def _remove_empty_tab_spans(self, body, details=None) -> int:
        """
        Remove empty PGM tab placeholder spans, for example:
        <span data-tab="true" style="padding-left: 68px;">  </span>
        """
        removed = 0
        for span in list(body.find_all(True)):
            if not self._is_span_tag(span):
                continue
            if self._is_ignored_tag_or_descendant(span):
                continue
            if span.get('data-tab', '').lower() != 'true':
                continue
            if span.get_text().strip():
                continue

            self._add_cleanup_detail(
                details,
                action='remove_element',
                element=span,
                target='span[data-tab="true"]',
                value=self._stringify_attr_value(span.get('style', '')),
            )
            span.decompose()
            removed += 1
        return removed

    def _remove_all_style_attributes(self, body, details=None) -> int:
        """
        Remove the 'style' attribute from ANY element inside the body.
        Returns the count of modified elements.
        """
        stripped = 0
        for element in body.find_all(True):
            if self._is_ignored_tag_or_descendant(element):
                continue
            if 'style' in element.attrs:
                self._add_cleanup_detail(
                    details,
                    action='remove_attribute',
                    element=element,
                    target='style',
                    value=element.attrs.get('style', ''),
                )
                del element.attrs['style']
                stripped += 1
        return stripped

    # ------------------------------------------------------------------ #
    #  Phase 2 — Final placeholder span cleanup                           #
    # ------------------------------------------------------------------ #

    def _unwrap_style_only_spans(self, body, details=None) -> int:
        """
        Unwrap spans that carry only inline styling, such as:
        <span style="mso-fareast-font-family:Times New Roman">,</span>
        """
        unwrapped = 0
        for span in list(body.find_all(True)):
            if not self._is_span_tag(span):
                continue
            if self._is_ignored_tag_or_descendant(span):
                continue
            if {key.lower() for key in span.attrs.keys()} != {'style'}:
                continue

            self._add_cleanup_detail(
                details,
                action='unwrap_element',
                element=span,
                target='span[style]',
                value=self._element_text_preview(span),
            )
            span.unwrap()
            unwrapped += 1
        return unwrapped

    def _unwrap_style_spans(self, body, details=None) -> int:
        """
        Unwrap placeholder <span> elements that only carry empty default
        IMPACT attributes.
        """
        unwrapped = 0
        for span in list(body.find_all(True)):
            if not self._is_span_tag(span):
                continue
            if self._is_ignored_tag_or_descendant(span):
                continue
            attr_keys = set(span.attrs.keys())
            if attr_keys - {'class', 'data-name'}:
                continue

            span_class = span.get('class', "")
            if isinstance(span_class, list):
                class_is_empty = all(not value for value in span_class)
            else:
                class_is_empty = not span_class

            data_name_is_empty = not span.get('data-name')
            if not class_is_empty or not data_name_is_empty:
                continue

            self._add_cleanup_detail(
                details,
                action='unwrap_element',
                element=span,
                target='span[class="", data-name=""]',
                value=self._element_text_preview(span),
            )
            span.unwrap()
            unwrapped += 1
        return unwrapped

    def _add_cleanup_detail(self, details, action: str, element, target: str, value='') -> None:
        if details is None:
            return
        details.append({
            'segment': self._segment_label(element),
            'action': action,
            'target': target,
            'tag': element.name if getattr(element, 'name', None) else '',
            'path': self._element_path(element),
            'value': self._stringify_attr_value(value),
            'text': self._element_text_preview(element),
        })

    def _summarize_cleanup_segments(self, details: list) -> list:
        segments = {}
        for item in details:
            segment = item.get('segment') or 'Document'
            stats = segments.setdefault(segment, {
                'segment': segment,
                'remove_attribute': 0,
                'remove_element': 0,
                'unwrap_element': 0,
                'total': 0,
            })
            action = item.get('action')
            if action in stats:
                stats[action] += 1
            stats['total'] += 1
        return sorted(segments.values(), key=lambda item: item['segment'].lower())

    def _segment_label(self, element) -> str:
        for node in [element] + list(element.parents):
            name = getattr(node, 'name', None)
            if not name or name in {'[document]', 'body', 'html'}:
                continue

            data_name = node.get('data-name')
            class_value = self._stringify_attr_value(node.get('class', ''))
            is_section = (
                name in {'section', 'sec', 'article'}
                or data_name in {'sec', 'section', 'chapter', 'part'}
                or 'sec' in class_value.split()
            )
            if is_section:
                ident = node.get('id') or node.get('data-id') or ''
                label = name
                if data_name:
                    label += f"[data-name={data_name}]"
                if ident:
                    label += f"#{ident}"
                label += f" ({self._element_path(node)})"
                return label
        return 'Body / document'

    def _element_path(self, element) -> str:
        parts = []
        for node in [element] + list(element.parents):
            name = getattr(node, 'name', None)
            if not name or name == '[document]':
                break

            same_name_index = 1
            sibling = node
            while sibling.previous_sibling is not None:
                sibling = sibling.previous_sibling
                if getattr(sibling, 'name', None) == name:
                    same_name_index += 1
            parts.append(f"{name}[{same_name_index}]")
            if name == 'body':
                break
        return ' > '.join(reversed(parts))

    def _element_text_preview(self, element, limit: int = 90) -> str:
        text = ' '.join(element.get_text(' ', strip=True).split())
        if len(text) > limit:
            return text[:limit - 3] + '...'
        return text

    def _stringify_attr_value(self, value) -> str:
        if isinstance(value, list):
            return ' '.join(str(item) for item in value)
        return '' if value is None else str(value)

    def _unwrap_style_only_span_markup(self, html_text: str) -> tuple[str, int]:
        pattern = re.compile(
            r'<(?P<tag>(?:[\w-]+:)?span)\s+style\s*=\s*(?P<quote>["\'])'
            r'(?P<style>.*?)(?P=quote)\s*>(?P<content>.*?)</(?P=tag)>',
            re.IGNORECASE | re.DOTALL,
        )

        def replace(match):
            return match.group('content')

        return pattern.subn(replace, html_text)

    def _remove_mso_style_attributes_from_markup(self, html_text: str) -> tuple[str, int]:
        tag_pattern = re.compile(
            r'<(?P<tag>(?!/?(?:del|ins|insert)\b)[\w:-]+)(?P<attrs>[^<>]*?)>',
            re.IGNORECASE | re.DOTALL,
        )
        style_pattern = re.compile(
            r'\sstyle\s*=\s*(?P<quote>["\'])(?P<value>.*?)(?P=quote)',
            re.IGNORECASE | re.DOTALL,
        )
        changed_count = 0

        def replace(match):
            nonlocal changed_count
            attrs = match.group('attrs')
            style_match = style_pattern.search(attrs)
            if not style_match:
                return match.group(0)

            cleaned_style, removed = self._remove_mso_declaration_from_style_value(
                style_match.group('value')
            )
            if not removed:
                return match.group(0)

            changed_count += 1
            if cleaned_style:
                quote = style_match.group('quote')
                new_style_attr = f' style={quote}{cleaned_style}{quote}'
                attrs = attrs[:style_match.start()] + new_style_attr + attrs[style_match.end():]
            else:
                attrs = attrs[:style_match.start()] + attrs[style_match.end():]

            return f"<{match.group('tag')}{attrs}>"

        cleaned_html = tag_pattern.sub(replace, html_text)
        return cleaned_html, changed_count

    def _remove_mso_declaration_from_style_value(self, style_value: str) -> tuple[str, bool]:
        kept = []
        removed = False
        for declaration in self._stringify_attr_value(style_value).split(';'):
            declaration = declaration.strip()
            if not declaration:
                continue
            if ':' not in declaration:
                kept.append(declaration)
                continue

            key, value = declaration.split(':', 1)
            normalized_key = key.strip().lower()
            normalized_value = value.strip().strip('"\'').lower()
            normalized_value = re.sub(r'\s+', ' ', normalized_value)
            if (
                normalized_key == 'mso-fareast-font-family'
                and normalized_value == 'times new roman'
            ):
                removed = True
                continue
            kept.append(declaration)

        return '; '.join(kept), removed

    def _apply_style_mapping(self, body, extra_mapping: dict | None = None) -> None:
        """Map specific class values or tag names to new attributes and tag names.
        The mapping is defined in a JSON file `style_mapping.json` located next to this script.
        Example entry:
        {
            "Heading": {"class": "sec", "data-name": "sec"},
            "ParaFlushLeft8": {"class": "p", "data-name": "p", "content-type": "flush left", "data-pgm-tag": "p"},
            "ParaInd9": {"class": "p", "data-name": "p", "tag": "span"}
        }
        """
        try:
            mapping_path = os.path.join(os.path.dirname(__file__), 'style_mapping.json')
            with open(mapping_path, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            if extra_mapping:
                mapping.update(extra_mapping)
        except Exception as e:
            logger.error(f"Failed to load style mapping: {e}")
            return
        original_attrs_by_element = {
            id(element): dict(element.attrs)
            for element in body.find_all(True)
        }
        for element in body.find_all(True):
            if self._is_ignored_tag_or_descendant(element):
                continue

            cls = element.get('class')
            if isinstance(cls, list):
                cls_list = cls
            elif cls:
                cls_list = [cls]
            else:
                cls_list = []

            new_attrs = {}
            new_tag_name = None

            specs = mapping.get(element.name)
            if specs:
                if 'class' in specs:
                    new_attrs['class'] = specs['class']
                if 'tag' in specs:
                    new_tag_name = specs['tag']
                for key, val in specs.items():
                    if key in {'class', 'tag'}:
                        continue
                    new_attrs[key] = val

            for c in cls_list:
                specs = mapping.get(c)
                if specs is None:
                    specs = self._find_numbered_class_mapping(c, mapping)
                if specs:
                    if 'class' in specs:
                        new_attrs['class'] = specs['class']
                    if 'tag' in specs:
                        new_tag_name = specs['tag']
                    for key, val in specs.items():
                        if key in {'class', 'tag'}:
                            continue
                        new_attrs[key] = val

            for selector, specs in mapping.items():
                if not self._is_supported_selector(selector):
                    continue
                if not self._element_matches_selector(
                    element, selector, original_attrs_by_element
                ):
                    continue
                if 'class' in specs:
                    new_attrs['class'] = specs['class']
                if 'tag' in specs:
                    new_tag_name = specs['tag']
                for key, val in specs.items():
                    if key in {'class', 'tag'}:
                        continue
                    new_attrs[key] = val

            if new_attrs:
                # set attributes on element
                for k, v in new_attrs.items():
                    element[k] = v
            if new_tag_name:
                element.name = new_tag_name
        # end of method

    def _find_numbered_class_mapping(self, class_name: str, mapping: dict) -> dict | None:
        """
        Allow one mapping like 'ParaFlushLeft8' to cover sibling classes such as
        'ParaFlushLeft9' or 'ParaFlushLeft10' by matching on the shared non-digit prefix.
        """
        match = re.match(r'^(.*?)(\d+)$', class_name)
        if not match:
            return None

        class_prefix = match.group(1)
        for key, specs in mapping.items():
            key_match = re.match(r'^(.*?)(\d+)$', key)
            if key_match and key_match.group(1) == class_prefix:
                return specs
        return None

    def _is_supported_selector(self, selector: str) -> bool:
        return (
            self._is_attribute_selector(selector)
            or self._is_tag_attribute_selector(selector)
            or self._is_direct_child_selector(selector)
        )

    def _is_attribute_selector(self, selector: str) -> bool:
        return bool(re.fullmatch(r"\[[\w:-]+=(['\"]).*?\1\]", selector.strip()))

    def _is_tag_attribute_selector(self, selector: str) -> bool:
        return bool(re.fullmatch(r"[\w:-]+\[[\w:-]+=(['\"]).*?\1\]", selector.strip()))

    def _is_direct_child_selector(self, selector: str) -> bool:
        return bool(re.fullmatch(
            r"\[[\w:-]+=(['\"]).*?\1\]\s*>\s*[\w:-]+",
            selector.strip(),
        ))

    def _element_matches_selector(
        self, element, selector: str, original_attrs_by_element: dict
    ) -> bool:
        selector = selector.strip()
        if self._is_attribute_selector(selector):
            return self._element_matches_attribute_selector(
                element, selector, original_attrs_by_element
            )
        if self._is_tag_attribute_selector(selector):
            return self._element_matches_tag_attribute_selector(
                element, selector, original_attrs_by_element
            )

        match = re.fullmatch(
            r"(\[[\w:-]+=(['\"]).*?\2\])\s*>\s*([\w:-]+)",
            selector,
        )
        if not match:
            return False

        parent_selector = match.group(1)
        child_tag = match.group(3).lower()
        if self._local_tag_name(element) != child_tag:
            return False

        parent = getattr(element, 'parent', None)
        if parent is None:
            return False
        return self._element_matches_attribute_selector(
            parent, parent_selector, original_attrs_by_element
        )

    def _element_matches_tag_attribute_selector(
        self, element, selector: str, original_attrs_by_element: dict
    ) -> bool:
        match = re.fullmatch(r"([\w:-]+)(\[[\w:-]+=(['\"]).*?\3\])", selector)
        if not match:
            return False
        tag_name = match.group(1).lower()
        attr_selector = match.group(2)
        if self._local_tag_name(element) != tag_name:
            return False
        return self._element_matches_attribute_selector(
            element, attr_selector, original_attrs_by_element
        )

    def _element_matches_attribute_selector(
        self, element, selector: str, original_attrs_by_element: dict
    ) -> bool:
        match = re.fullmatch(r"\[([\w:-]+)=(['\"])(.*?)\2\]", selector)
        if not match:
            return False
        attr_name = match.group(1)
        expected_value = match.group(3)
        original_attrs = original_attrs_by_element.get(id(element), {})
        candidate_values = {
            self._stringify_attr_value(element.get(attr_name, '')),
            self._stringify_attr_value(original_attrs.get(attr_name, '')),
        }
        if attr_name == 'data-name':
            candidate_values.add(self._stringify_attr_value(element.get('data-label', '')))
            candidate_values.add(self._stringify_attr_value(original_attrs.get('data-label', '')))
        return expected_value in candidate_values

    # ------------------------------------------------------------------ #

    def _transform_tag(self, tag) -> bool:
        """
        Applies transformation rules to a single body tag.
        Returns True if the tag was skipped, False if transformed.
        """
        tag_name = tag.name.lower() if tag.name else ''

        # Skip structural/metadata tags even if they appear inside body
        if self._is_ignored_tag_or_descendant(tag):
            return True

        # 1. Capture current attributes
        original_attrs = dict(tag.attrs)

        # 2. Clone attributes into data-pgm-* with exclusions:
        #    - 'id'        : never cloned (DOM identity / anchor / CKEditor safety)
        #    - data-* attrs: already namespaced → would produce data-pgm-data-col
        #    - NO_CLONE_ATTRS: table structural attrs needed by browser/CKEditor
        for attr, value in original_attrs.items():
            if attr.lower() == 'id':
                continue
            if attr.lower().startswith('data-'):
                continue
            if attr.lower() in NO_CLONE_ATTRS:
                continue

            value_str = " ".join(value) if isinstance(value, list) else str(value)
            tag[f"data-pgm-{attr}"] = value_str

        # 3. Inject IMPACT attributes if not already present
        if 'class' not in tag.attrs:
            tag['class'] = ""

        if 'data-name' not in tag.attrs:
            tag['data-name'] = ""

        return False  # transformed

    def _is_ignored_tag(self, tag) -> bool:
        tag_name = self._local_tag_name(tag)
        return tag_name in IGNORED_TAGS

    def _is_ignored_tag_or_descendant(self, tag) -> bool:
        if self._is_ignored_tag(tag):
            return True
        return any(self._is_ignored_tag(parent) for parent in getattr(tag, 'parents', []))

    def _is_span_tag(self, tag) -> bool:
        return self._local_tag_name(tag) == 'span'

    def _local_tag_name(self, tag) -> str:
        name = str(getattr(tag, 'name', '') or '').lower()
        return name.rsplit(':', 1)[-1].rsplit('}', 1)[-1]

    # ------------------------------------------------------------------ #
    #  Directory batch                                                     #
    # ------------------------------------------------------------------ #

    def process_directory(self, input_dir: str, output_dir: str, callback=None, extra_mapping: dict | None = None):
        """
        Processes all HTML/XHTML/XML files in input_dir (recursively).
        All output files are saved as .html regardless of source extension.

        Returns (processed_count, error_count, file_results).
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        extensions = ('.html', '.xhtml', '.xml', '.htm')
        processed_count = 0
        error_count = 0
        file_results = []

        for root, _, files in os.walk(input_dir):
            for file in files:
                if file.lower().endswith(extensions):
                    input_path = os.path.join(root, file)
                    rel_path = os.path.relpath(input_path, input_dir)

                    # Always output as .html (xhtml/xml → html)
                    rel_path_html = os.path.splitext(rel_path)[0] + '.html'
                    output_path = os.path.join(output_dir, rel_path_html)

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
