from pathlib import Path
from core import contrib_extractor as ce
from core.contrib_regen_compare import REPORT_VERSION

sample = Path(r"_patch_work/sample_regen_compare/DEMO_SAMPLE_regen_compare_v1.html")
text = sample.read_text(encoding="utf-8")
print("sample size", len(text))
print("has kpi-band", "kpi-band" in text)
print("has cause-chart", "cause-chart" in text)
print("cause-bar count", text.count('class="cause-bar"'))
print("filter JS", "activeCategory" in text and "clearCategoryFilter" in text)
print("SCRIPT_VERSION", ce.SCRIPT_VERSION)
print("REPORT_VERSION", REPORT_VERSION)

p = Path("core/contrib_extractor.py")
t = p.read_text(encoding="utf-8")
t2 = t.replace("goes into file names (_v12)", "goes into file names (_v13)")
if t2 != t:
    p.write_text(t2, encoding="utf-8")
    print("comment bumped")
