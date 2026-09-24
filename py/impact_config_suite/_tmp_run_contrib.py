from pathlib import Path
from datetime import datetime
import json
import traceback
from core.contrib_extractor import run_contrib_extract, SCRIPT_VERSION

ROOT = Path(r"D:\NEW_GEN\LIVE_SUPPORT_2026\FOOTNOTES\From-2026-1st-to-now")
LOG = Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite\_tmp_contrib_run.log")
OUT = Path(r"C:\_IMPACT\prod-support-tools\py\impact_config_suite\_tmp_contrib_result.json")

def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

log(f"START SCRIPT_VERSION={SCRIPT_VERSION}")
log(f"ROOT={ROOT}")
try:
    result = run_contrib_extract(
        ROOT,
        shortcodes=[("LWW", "ACI"), ("LWW", "ACD"), ("LWW", "MD")],
        delay_sc=0,
        delay_cl=0,
        cancel_check=lambda: False,
        log_callback=log,
    )
    log(f"RESULT keys={list(result.keys()) if isinstance(result, dict) else type(result)}")
    # make JSON-safe
    def encode(o):
        if isinstance(o, Path):
            return str(o)
        if isinstance(o, set):
            return list(o)
        return str(o)
    with OUT.open("w", encoding="utf-8") as f:
        json.dump({"SCRIPT_VERSION": SCRIPT_VERSION, "result": result}, f, indent=2, default=encode)
    log("DONE writing result json")
except Exception:
    log("FATAL:\n" + traceback.format_exc())
    raise
