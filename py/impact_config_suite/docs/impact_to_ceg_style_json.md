# IMPACT to CEG/PGM Style JSON Guide

Configuration file:

```text
impact_to_ceg.json
```

The converter runs in two phases:

1. Existing source attributes are renamed to `data-impact-*`.
2. Rules from `impact_to_ceg.json` rename tags, add new attributes, insert child nodes, or hide matched elements.

Top-level JSON sections:

```json
{
  "display": {},
  "inline": {},
  "hide": []
}
```

- `display`: block or paragraph-level mappings.
- `inline`: inline mappings.
- `hide`: rules that add `style="display:none"` directly to matched elements.

## Basic Rule

```json
"front": {
  "match": {
    "data-impact-class": "front",
    "data-impact-name": "front"
  },
  "tag": "div",
  "attrs": {
    "class": "front",
    "data-alias": "front"
  }
}
```

Input after phase 1:

```html
<div data-impact-class="front" data-impact-name="front">
```

Output:

```html
<div class="front" data-alias="front" data-impact-class="front" data-impact-name="front">
```

## Paragraph Rule

```json
"para-flush-left": {
  "match": {
    "data-impact-class": "p",
    "data-impact-content-type": "flush left"
  },
  "tag": "p",
  "attrs": {
    "class": "ParaFlushLeft",
    "data-label": "†Para_FlushLeft",
    "data-name": "†Para_FlushLeft"
  }
}
```

Generic fallback:

```json
"para-ind": {
  "match": {
    "data-impact-class": "p"
  },
  "tag": "p",
  "attrs": {
    "class": "ParaInd",
    "data-label": "†Para_Ind",
    "data-name": "†Para_Ind"
  }
}
```

More specific rules win over generic rules.

## Inline Rule

Use unique rule names. Duplicate JSON keys overwrite earlier rules.

```json
"xref-fig": {
  "match": {
    "data-impact-class": "xref",
    "data-impact-ref-type": "fig"
  },
  "tag": "a",
  "attrs": {
    "class": "citationfigure",
    "data-alias": "FigureRef"
  }
}
```

## Immediate Parent Match

Use `parent_match` when the direct parent must match.

```json
"name-given-names": {
  "parent_match": {
    "data-impact-class": "name"
  },
  "match": {
    "data-impact-class": "given-names"
  },
  "tag": "span",
  "attrs": {
    "class": "fmauGivenName",
    "data-name": "‡fm_auGivenName"
  }
}
```

## Parent Of Parent Match

Use `grandparent_match` when the parent of the parent must match.

```json
"fn-para": {
  "grandparent_match": {
    "data-impact-name": "author-notes"
  },
  "parent_match": {
    "data-impact-name": "fn"
  },
  "match": {
    "data-impact-class": "p",
    "data-impact-name": "p"
  },
  "tag": "p",
  "attrs": {
    "class": "FM_Note_Correspondence",
    "data-alias": "FM_Note_Correspondence",
    "data-label": "†FM_Note_Correspondence",
    "data-name": "†FM_Note_Correspondence"
  }
}
```

## Any Ancestor Or Root Scope

Use `root_match` to apply a rule only inside a root container such as `front`, `body`, or `back`.

```json
"body-xref": {
  "root_match": {
    "class": ["front", "body", "back"]
  },
  "match": {
    "data-impact-class": "xref"
  },
  "tag": "a",
  "attrs": {
    "class": "citationRef"
  }
}
```

`root_match` checks converted ancestor classes, so it can match:

```html
<div class="front">
<div class="body">
<div class="back">
```

Use `ancestor_match` when any ancestor with source attributes should match:

```json
"inside-abstract": {
  "ancestor_match": {
    "data-impact-name": "abstract"
  },
  "match": {
    "data-impact-class": "p"
  },
  "tag": "p",
  "attrs": {
    "class": "FMAbstractParaFlushLeft",
    "data-label": "†FM_Abstract_Para_FlushLeft",
    "data-name": "†FM_Abstract_Para_FlushLeft"
  }
}
```

## Insert A Label Child

Use `prepend` to insert a child at the beginning of a matched element.

```json
"title-level-1": {
  "match": {
    "data-impact-class": "title",
    "data-impact-levels": "1",
    "data-impact-name": "title"
  },
  "tag": "span",
  "attrs": {
    "class": "HeadA",
    "data-label": "†HeadA",
    "data-name": "†HeadA"
  },
  "prepend": [
    {
      "tag": "span",
      "attrs": {
        "class": "label",
        "data-name": "‡label"
      },
      "text_from": "data-impact-label"
    }
  ]
}
```

Input:

```html
<div data-impact-class="title" data-impact-label="3." data-impact-levels="1" data-impact-name="title">Introduction</div>
```

Output:

```html
<span class="HeadA" data-label="†HeadA" data-name="†HeadA">
  <span class="label" data-name="‡label">3.</span>
  Introduction
</span>
```

## Hide Rules

Hide rules add `style="display:none"` directly to matched elements.

```json
"hide": [
  {
    "match": {
      "data-impact-class": "journal-meta"
    }
  }
]
```

Output:

```html
<div data-impact-class="journal-meta" style="display:none">
```

Child hide rule:

```json
{
  "match": {
    "data-impact-class": "article-meta"
  },
  "child_match": {
    "data-impact-class": "pub-date"
  }
}
```

This hides only the child element when its immediate parent matches.

For a specific child tag:

```json
{
  "match": {
    "data-impact-class": "contrib-group"
  },
  "child_tag": "br",
  "child_match": {
    "data-impact-type": "_moz"
  }
}
```

## Revert Or Re-Run Conversion

The converter writes new output files and does not overwrite the source file.

- Single file output uses `*_CEG_<timestamp>.xhtml`.
- Directory output creates a timestamped output folder and writes `.xhtml` files.
- Older generated outputs are moved to an `archive` folder by the UI workflow.

To revert a conversion result, use the original source file again or restore the previous generated output from the `archive` folder.

The old PGM HTML Clone Processor remains separate and still writes `.html` output.

## Notes

- `match` is required for style rules.
- `tag` is optional. If omitted, the tag name stays unchanged.
- `attrs` is optional. If omitted, existing attributes stay unchanged.
- `data-impact-class` and `class` support token matching.
- Rule names must be unique.
- More specific rules win over generic fallback rules.
