"""Test script for report generation components."""

import sys
from datetime import datetime
from pathlib import Path

# Direct imports to bypass package init
sys.path.insert(0, str(Path(__file__).parent))

# Import models directly
exec(open('xml_compare/models.py').read())

# Import statistics module
exec(open('xml_compare/statistics.py').read())

# Import html_renderer module
exec(open('xml_compare/html_renderer.py').read())

# Import report_builder module
exec(open('xml_compare/report_builder.py').read())

print("=" * 60)
print("Testing StatisticsBuilder")
print("=" * 60)

# Create a sample result for testing
result = CompareResult(
    original_path=Path("test_original.xml"),
    revised_path=Path("test_revised.xml"),
    generated_time=datetime.now(),
    text_diffs=[
        TextDiff(path="/root/para[1]", old_text="Hello world", new_text="Hello there world"),
        TextDiff(path="/root/para[2]", old_text="Old content", new_text="New content"),
    ],
    format_diffs=[
        FormatDiff(path="/root/italic[1]", old_tag="italic", new_tag="bold", content="emphasized text"),
    ],
    attribute_diffs=[
        AttributeDiff(path="/root/section[1]", element_tag="section", attribute_name="id", old_value="sec-1", new_value="section-1"),
    ],
    structure_diffs=[
        StructureDiff(path="/root/new[1]", change_type="added", element_tag="new", element_preview="<new>New element</new>"),
        StructureDiff(path="/root/old[1]", change_type="deleted", element_tag="old", element_preview="<old>Deleted element</old>"),
    ],
    options=CompareOptions(text_corrections=True, formatting_only=True, include_attributes=True),
)

# Test StatisticsBuilder
stats_builder = StatisticsBuilder()
stats = stats_builder.calculate(result)

print(f"Total Differences: {stats.total_differences}")
print(f"Text Changes: {stats.text_changes}")
print(f"Format Changes: {stats.format_changes}")
print(f"Attribute Changes: {stats.attribute_changes}")
print(f"Added Nodes: {stats.added_nodes}")
print(f"Deleted Nodes: {stats.deleted_nodes}")
print(f"Total Nodes: {stats.total_nodes}")
print(f"Match Percentage: {stats.match_percentage}%")

# Verify statistics are attached to result
result.statistics = stats

print()
print("=" * 60)
print("Testing HtmlTemplateRenderer")
print("=" * 60)

renderer = HtmlTemplateRenderer()

# Test inline diff generation
inline_diff = renderer._generate_inline_diff("Hello world", "Hello there world")
print(f"Inline diff test: {inline_diff}")

# Test full report generation (not writing to file, just generating)
html_content = renderer.render_report(result)
content_size = len(html_content)
print(f"Generated HTML report size: {content_size:,} bytes ({content_size/1024:.1f} KB)")

# Verify key sections exist
assert "XML Compare Report" in html_content
assert "Comparison Overview" in html_content
assert "Text Corrections" in html_content
assert "Formatting Changes" in html_content
assert "Attribute Changes" in html_content
assert "Structure Changes" in html_content
assert "Full Compare" in html_content
assert "Statistics" in html_content
assert "sidebar" in html_content
assert "tab-panel" in html_content

print("All required sections found in HTML!")

print()
print("=" * 60)
print("Testing ReportBuilder with streaming write")
print("=" * 60)

report_builder = ReportBuilder()

# Test filename generation
output_dir = Path("./test_reports")
test_path = report_builder._generate_filename(result, output_dir)
print(f"Generated filename: {test_path.name}")
assert test_path.name.startswith("test_revised_compare_")
assert test_path.name.endswith(".html")

# Test streaming write
import tempfile
import os

with tempfile.TemporaryDirectory() as tmpdir:
    output_path = Path(tmpdir)
    report_path = report_builder.build_report(result, output_path, use_streaming=True)
    
    # Verify file was created
    assert report_path.exists(), "Report file was not created"
    
    # Read and verify content
    written_content = report_path.read_text(encoding='utf-8')
    file_size = len(written_content)
    print(f"Written report size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    
    assert "<!DOCTYPE html>" in written_content
    assert "</html>" in written_content
    assert "Text Corrections" in written_content
    assert "Formatting Changes" in written_content
    
    print(f"Report successfully written to: {report_path}")

print()
print("=" * 60)
print("All tests passed!")
print("=" * 60)
