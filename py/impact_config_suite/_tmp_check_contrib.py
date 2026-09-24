from pathlib import Path
from core.contrib_extractor import load_project, pending_pairs

root = Path(r"D:\NEW_GEN\LIVE_SUPPORT_2026\FOOTNOTES\From-2026-1st-to-now")
root, docs, meta, index, done = load_project(root)
print("index type", type(index), "len", len(index))
clients = sorted(index.keys())
print("clients count", len(clients))
print("LWW in index", "LWW" in index)
if "LWW" in index:
    scs = sorted(index["LWW"].keys())
    print("LWW shortcode count", len(scs))
    for sc in ["ACI", "ACD", "MD"]:
        present = sc in index["LWW"]
        n = len(index["LWW"][sc]) if present else 0
        print(f"  {sc}: present={present} docs={n}")
    missing = [s for s in ["ACI","ACD","MD"] if s not in index["LWW"]]
    print("missing among requested:", missing)
else:
    print("LWW client NOT in index; sample clients:", clients[:20])
try:
    pp = list(pending_pairs(index, done, clients=["LWW"], regenerate_all=True))
    hit = [p for p in pp if p[0] == "LWW" and p[1] in {"ACI","ACD","MD"}]
    print("pending matching", hit)
except Exception as e:
    print("pending_pairs err", type(e).__name__, e)
