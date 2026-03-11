from datetime import datetime
from . import report_config as cfg


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(cfg.LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
