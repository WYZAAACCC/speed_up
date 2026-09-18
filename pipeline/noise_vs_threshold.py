#!/usr/bin/env python3
"""
决定性诊断：那 30% 的"噪声"是【定义噪声】还是【真实涨落】？

判据：
  如果噪声来自"用硬阈值从弥散界面切面"这个定义方式，
  那么换个阈值，噪声水平应当明显变化。
  如果换阈值噪声不变，那它就是真实的物理涨落（算子应该能学到）。

做法：用不同的 min_area 阈值做提取，比较二阶/一阶差分比值。
"""
import subprocess
import sys
import os
import re

EXO = sys.argv[1] if len(sys.argv) > 1 else "/root/work/prod/prod.e"
WORK = "/root/work/noisetest"

os.makedirs(WORK, exist_ok=True)

print(f"{'min_area(单元数)':>16} {'面数':>7} {'一阶RMS':>10} {'二阶RMS':>10} {'比值':>8}")
print("-" * 58)

for mult in [1, 2, 3, 6, 12, 25]:
    out = os.path.join(WORK, f"ds{mult}")
    # 提取：--min-area 用"单元数 × 平均单元测度"表示
    r = subprocess.run(
        ["python3", "extract.py", EXO, "--out", out, "--stride", "2",
         "--min-area", str(mult * 125)],   # 单元测度 = 5×5×5 = 125
        cwd="/root/work", capture_output=True, text=True)
    if r.returncode != 0:
        print(f"{mult:>16}  提取失败: {r.stderr.strip()[:60]}")
        continue

    # 分析
    code = f'''
import csv, numpy as np, os
with open(os.path.join("{out}", "faces.csv")) as f:
    rows = list(csv.DictReader(f))
by = {{}}
for r in rows:
    by.setdefault(int(r["face_id"]), []).append(r)
for k in by: by[k].sort(key=lambda r: float(r["time"]))
d1, d2 = [], []
nface = 0
for fid, rs in by.items():
    e = np.array([float(r["solute_excess"]) for r in rs])
    if len(e) < 3: continue
    nface += 1
    d1.extend(np.diff(e)); d2.extend(np.diff(e, n=2))
d1 = np.array(d1); d2 = np.array(d2)
r1 = np.sqrt((d1**2).mean()) if len(d1) else 0
r2 = np.sqrt((d2**2).mean()) if len(d2) else 0
print(f"{{nface}} {{r1:.4f}} {{r2:.4f}} {{r2/(r1+1e-30):.4f}}")
'''
    r2 = subprocess.run(["python3", "-c", code], capture_output=True, text=True)
    try:
        nf, a1, a2, ratio = r2.stdout.strip().split()
        print(f"{mult:>16} {nf:>7} {a1:>10} {a2:>10} {ratio:>8}")
    except Exception:
        print(f"{mult:>16}  分析失败: {r2.stderr.strip()[:60]}")

print()
print("判读：")
print("  比值随阈值【显著变化】 → 是【定义噪声】，改面定义就能降")
print("  比值随阈值【基本不变】 → 是【真实涨落】，得靠更好的特征/机制")
