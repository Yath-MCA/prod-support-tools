import glob

from . import report_config as cfg
from .report_log import log
from .report_extract import process_config
from .report_patterns import build_patterns, save_patterns_json
from .report_writer import write_json, write_html, write_excel

def main():
    log("Start...")
    files=glob.glob(cfg.SEARCH_PATTERN,recursive=True)
    log(f"Found {len(files)} XMLs")
    reps=[]
    for f in files:
        r=process_config(f)
        if r: reps.append(r)

    patterns,mapping,sigs = build_patterns(reps)
    save_patterns_json(patterns,cfg.OUT_PATTERNS)

    write_json(reps, patterns, cfg.OUT_JSON)
    write_html(reps,patterns,mapping,sigs,cfg.OUT_HTML,cfg.RUN_TIMESTAMP)
    write_excel(reps, patterns, cfg.OUT_XLSX)

    log("Done.")

if __name__=="__main__":
    main()
