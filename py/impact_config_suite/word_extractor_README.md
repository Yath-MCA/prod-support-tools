# IMPACT Word Extraction Tool

A premium automation tool for extracting and categorizing character-separated values from Text, HTML, and XML files.

## 🚀 Overview

The Word Extraction Tool is designed to handle high-volume data cleaning and pattern recognition. It allows users to isolate non-alphabetic characters (often used for CJK or symbol validation), filter pure alphabetic words, or extract numeric strings with a single click.

## 🛠 Features

- **Multi-Format Support**: Process `.txt`, `.html`, `.xml`, `.xhtml`, and `.htm` files.
- **Smart Text Extraction**: Automatically strips markup and script tags from HTML/XML files to isolate content.
- **Stop-Word Filtering**: Automatically removes common English words (*the, of, was, etc.*) when generating unique word lists.
- **Segmented Analysis**:
    - **Non-Alphabetic**: Isolates symbols, CJK characters, and numbers.
    - **Alphabetic Only**: Isolates standard English words.
    - **Numeric Only**: Isolates pure digit sequences.
- **Consolidated Reporting**: Generates a high-fidelity HTML Master Report with tabbed navigation for all segments.

## ⚡ Automated Workflow (Auto Process)

The "Auto Process" button performs the following actions automatically:

### For HTML/XML Files:
1.  **Unique Word Extraction**: Extracts every unique word in the document.
2.  **Cleaning**: Filters out common stop words.
3.  **TXT Export**: Saves a `[FileName]_UniqueWords.txt` file in the source directory.
4.  **Full Pattern Scan**: Runs all extraction segments.
5.  **Master Report**: Generates and opens a consolidated `[FileName]_MasterReport.html`.

### For TXT Files:
1.  **Full Pattern Scan**: Runs all extraction segments.
2.  **Master Report**: Generates and opens a consolidated `[FileName]_MasterReport.html`.

## 📁 File Structure

- `core/word_extractor.py`: The extraction engine and HTML generator.
- `word_extractor_tab.py`: The GUI component integrated into the IMPACT Config Suite.
- `word_extractor_README.md`: This documentation.

## 📝 Usage Tips

- **Comma Separation**: The tool assumes values are separated by commas (`,`). For HTML files, it treats text nodes as comma-separated segments for extraction.
- **Same-Location Saving**: All generated reports and files are saved in the same folder as the input file for easy organization.
- **Browser Visualization**: The generated HTML reports are interactive. Use the navigation tabs at the top to switch between data segments.

---
*Developed for the IMPACT Common Tools Suite - 2026*
