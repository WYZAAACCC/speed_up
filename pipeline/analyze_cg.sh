#!/bin/bash
# 分析竞争生长实验：gr0（theta=0，与热梯度对齐）在凝固区中的面积分数随时间变化。
# 判据：A_ani=0.7 时应单调上升超过 0.5；A_ani=0 时无择优。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate ml
python3 - <<'PY'
import csv, os

def load(tag, fn):
    p = f"/root/work/cg/{tag}/{fn}"
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p)))
    out = []
    for r in rows:
        try:
            a, b = float(r["gr0_total"]), float(r["gr1_total"])
        except (KeyError, ValueError):
            continue
        out.append((float(r["time"]), a, b, a / (a + b) if (a + b) > 0 else float("nan")))
    return out

for tag, fn, label in (("T2", "cgA7_out.csv", "A_ani=0.7 (对齐晶粒应有优势)"),
                       ("T3", "cgA0_out.csv", "A_ani=0.0 (对照，应无择优)")):
    d = load(tag, fn)
    print("=" * 66)
    print(f"{tag}  {label}")
    print("=" * 66)
    if not d:
        print("  无数据")
        continue
    print(f"  {'time':>10} {'∫gr0':>11} {'∫gr1':>11} {'gr0 占比':>9}")
    step = max(1, len(d) // 10)
    for row in d[::step] + [d[-1]]:
        print(f"  {row[0]:10.3e} {row[1]:11.4e} {row[2]:11.4e} {row[3]:9.4f}")
    f0, f1 = d[0][3], d[-1][3]
    print(f"  --> gr0 占比: 初始 {f0:.4f}  最终 {f1:.4f}  变化 {f1-f0:+.4f}")
    print()
PY
