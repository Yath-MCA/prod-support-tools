# IMPACT Config Suite: XML/HTML Element Extractor

This document provides the analysis of existing tools within the codebase regarding the user's requirement and details the implementation of the new HTML/XML Element Extractor tool.

---

## 1. Analysis of Existing Codebase Tools

We analyzed the current workspace to identify any existing functionality that could match or be adapted for the requirement: **extracting specific elements from single or multiple XML/HTML files and generating a timestamped HTML report**.

| Existing Tool / Component | File Path | Main Functionality | Suitability for Current Requirement |
| :--- | :--- | :--- | :--- |
| **Content Analysis Engine** | [analyses_tab.py](file:///c:/_IMPACT/tomcat/webapps/impactweb_live/untils_automation/py/impact_config_suite/analyses_tab.py) / [book_analyzer.py](file:///c:/_IMPACT/tomcat/webapps/impactweb_live/untils_automation/py/impact_config_suite/analyses/book_analyzer.py) | Scans book chapters, figures, tables, and footnotes in folders containing `impact_config.xml` to generate publication analysis reports. | **Not Suitable**: It uses hardcoded XPath expressions specifically tailored to IMPACT publication layouts. It does not allow custom tag/XPath/CSS selector inputs, nor does it work on arbitrary single files or folder scans. |
| **Report Extract Utility** | [report_extract.py](file:///c:/_IMPACT/tomcat/webapps/impactweb_live/untils_automation/py/impact_config_suite/patterns/report_extract.py) | Extracts journal configuration values and attributes from config XML files for patterns and report compilation. | **Not Suitable**: It is strictly limited to parsing `journal` attributes in configuration files, and cannot extract arbitrary elements or work with standard HTML files. |
| **XML Processor** | [xml_processor.py](file:///c:/_IMPACT/tomcat/webapps/impactweb_live/untils_automation/py/impact_config_suite/core/xml_processor.py) | Updates XML file metadata (such as contributor information, identifiers, visual editor settings). | **Not Suitable**: It is a utility for writing and modifying specific elements, not for querying/extracting custom data or generating external HTML reports. |
| **Word Extractor** | [word_extractor_tab.py](file:///c:/_IMPACT/tomcat/webapps/impactweb_live/untils_automation/py/impact_config_suite/word_extractor_tab.py) / [word_extractor.py](file:///c:/_IMPACT/tomcat/webapps/impactweb_live/untils_automation/py/impact_config_suite/core/word_extractor.py) | Extracts comma-separated alphabetic, numeric, or non-alphabetic strings from TXT/HTML files. | **Not Suitable**: It parses text content rather than DOM/XML elements, and performs character-level extractions. |

### Conclusion
There was **no existing tool** in the codebase capable of performing generic XML/HTML tag, XPath, or CSS selector queries across files and generating a timestamped, interactive HTML report. Therefore, we built a new tool to fill this gap.

---

## 2. New Tool Architecture & Implementation

We built a robust, high-performance element extraction suite consisting of two main layers:

### A. Core Engine: `core/element_extractor.py`
[element_extractor.py](file:///c:/_IMPACT/tomcat/webapps/impactweb_live/untils_automation/py/impact_config_suite/core/element_extractor.py)
* **Dual Parsing Engine**: Uses `BeautifulSoup` (with `lxml` backend) for Tag Name and CSS Selector searches, and uses `lxml.etree` for XPath execution. This combines the flexibility of CSS/tag parsing with the precise execution of XPath standard.
* **Line Number Detection**: Leverages `lxml` sourceline tracking to determine the exact line number of matches.
* **Namespace Handling**: Gracefully parses standard markup and XML schemas, keeping namespaces isolated or queryable.
* **Bulk Scanning**: Iterates recursively through folder structures filtering by custom extensions (e.g. `.xml`, `.html`).
* **HTML Report Generator**: Generates a self-contained, interactive HTML page populated with metrics, tables, and search indexes.

### B. GUI Layer: `element_extractor_tab.py`
[element_extractor_tab.py](file:///c:/_IMPACT/tomcat/webapps/impactweb_live/untils_automation/py/impact_config_suite/element_extractor_tab.py)
* **Responsive Control Panel**: Allows quick switching between Single File and Folder Scan modes.
* **Conditional Visibility**: Dynamically activates or disables input fields (e.g., recursive checks, attribute filters) depending on the selected mode and extraction method.
* **Multi-threaded Scan Execution**: Executes extraction in a background thread to prevent GUI lockups on large directories.
* **Cancellation Support**: A responsive "Cancel" button terminates thread operations safely.
* **Live Console Output**: Prints real-time log statements and extraction progress (with a `ttk.Progressbar`).
* **Branding and Theme Integration**: Integrates directly with the `CommonToolsApp` dark/bright themes and menu bar.

---

## 3. Premium Interactive HTML Report Features

The generated HTML report is built to feel premium, featuring:
1. **Glassmorphism Dark Theme**: Modern slate/dark-blue layout with card components and smooth animations.
2. **Metrics Dashboard**: Stats cards highlighting total matches, files checked, query type, and execution timestamp.
3. **Interactive Collapsible Sections**: Match cards grouped under their corresponding files. Each file block can be collapsed/expanded.
4. **Real-time Search Filter**: A client-side JavaScript filter input at the top of the report to filter matches dynamically. It scans filenames, tag names, attribute key-values, text content, and outer markup.
5. **Code Presentation**: Match codes display inside syntax-highlighted containers with the exact source line number.
6. **One-Click Copying**: A copy button copies the exact HTML/XML markup to the clipboard with visual feedback (button states and toast alerts).

---

## 4. How to Use the New Tool

1. Launch the Framework GUI (run `tools_app.py` or start the application).
2. Go to the new **🎯 Element Extractor** tab (or select it from the *Tools* menu).
3. Select **Scan Mode**:
   * *Single File*: Pick an XML/HTML file.
   * *Folder Scan*: Pick a folder, check *Recursive Search* if needed, and customize file extensions.
4. Select **Extraction Method**:
   * *Tag Name*: Type a tag (e.g., `span`, `p`, `fig`). You can optionally set an *Attribute Filter* (e.g., attribute `class` = `citation`).
   * *XPath Query*: Type an XPath query (e.g., `//xref[@rid]` or `//a[@href]`).
   * *CSS Selector*: Type a CSS selector (e.g., `div.content span`).
5. Choose the **Report Output Folder**.
6. Click **🚀 RUN ELEMENT EXTRACTION**. Once completed, the HTML report will automatically open in your default browser.
