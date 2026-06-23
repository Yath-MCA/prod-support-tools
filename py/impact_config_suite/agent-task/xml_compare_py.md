You are a senior Python desktop application architect.

I have an existing Python Tkinter XML Compare Tool that compares two XML files and generates an HTML report using lxml and xmldiff.

Refactor and enhance the application with the following requirements.

=========================
UI ENHANCEMENTS
===============

Before comparison starts, provide user selectable options:

[✓] Text Corrections + Formatting
[✓] Formatting Only
[✓] Full Compare
[ ] Attribute Level Compare (Optional - disabled by default)
[✓] Structure Changes
[✓] Generate Statistics Dashboard

Attribute comparison can be expensive, therefore it must be optional and only run when user explicitly enables it.

=========================
REPORT GENERATION
=================

Generate a modern standalone HTML report.

Report filename format:

<xml_name>_compare_YYYYMMDD_HHMMSS.html

Example:

article_compare_20260623_153012.html

=========================
LAYOUT
======

Use a professional layout:

---

## | Sidebar Navigation                              |

| Overview                                         |
| Text Changes (count)                             |
| Formatting Changes (count)                       |
| Attribute Changes (count)                        |
| Structure Changes (count)                        |
| Full Compare (count)                             |
| Statistics                                       |
----------------------------------------------------

Main content area contains tab sections.

=========================
OVERVIEW DASHBOARD
==================

Display summary cards:

Total Differences
Text Changes
Formatting Changes
Attribute Changes
Added Elements
Deleted Elements
Match Percentage

Example:

Total Changes: 145
Text Changes: 32
Format Changes: 58
Attribute Changes: 41
Added Nodes: 10
Deleted Nodes: 4
Match Score: 98.2%

=========================
TEXT CORRECTIONS TAB
====================

Show actual content differences.

Display side-by-side comparison.

Example:

OLD:
The patient was recieved.

NEW:
The patient was received.

Highlight:

Deleted text:
background:#ffebee
color:#c62828
text-decoration:line-through

Inserted text:
background:#e8f5e9
color:#2e7d32
font-weight:bold

Use Python difflib where necessary to generate inline text differences.

=========================
FORMATTING ONLY TAB
===================

Ignore text changes.

Detect formatting changes such as:

italic → bold
italic → underline
sup → sub
named-content changes

Example display:

Change Type:
italic → bold

Content:
gene

Location:
/article/body/sec[1]/p[4]

Formatting changes should use blue visual styling.

=========================
ATTRIBUTE CHANGES TAB
=====================

Generate ONLY if user enabled Attribute Level Compare.

Detect:

id changes
rid changes
href changes
xlink:href changes
content-type changes
class changes
any attribute modifications

Example:

Element : xref
Path : /article/body/sec[2]/p[3]/xref[1]

Attribute : rid
Old Value : ref1
New Value : ref5

Display in table format.

Use orange for old values.
Use green for new values.

Include attribute change count.

=========================
STRUCTURE CHANGES TAB
=====================

Detect:

Added nodes
Deleted nodes
Moved nodes

Examples:

Added: <fig id="fig3">

Deleted: <table-wrap id="tbl4">

Display XML path.

Use:

Green = Added
Red = Deleted

=========================
FULL COMPARE TAB
================

Display all detected differences.

Use expandable sections.

Show:

Path
Change Type
Old Content
New Content

=========================
SEARCH AND FILTER
=================

Add report search box.

Allow filtering by:

Text Changes
Formatting Changes
Attribute Changes
Structure Changes

Filtering should work client-side using JavaScript.

=========================
XML PATH SUPPORT
================

Every difference must include XPath-like location.

Example:

/article/body/sec[2]/p[4]/xref[1]

=========================
REPORT HISTORY
==============

Inside sidebar show:

Generated Time
Original File
Revised File

=========================
TECHNICAL REQUIREMENTS
======================

1. Keep existing entity handling logic.
2. Keep Tkinter GUI.
3. Keep lxml parsing.
4. Continue using xmldiff where useful.
5. Use difflib for text highlighting.
6. Generate a single self-contained HTML file.
7. No external CSS or JS dependencies.
8. Use modern responsive CSS.
9. Handle XML files larger than 50MB efficiently.
10. Do not load full report into memory multiple times.

=========================
CODE QUALITY
============

Refactor into:

XMLParserService
DiffEngine
ReportBuilder
StatisticsBuilder
AttributeComparator
HtmlTemplateRenderer

Use dataclasses for difference models.

Add comments and docstrings.

Generate production-quality code.
