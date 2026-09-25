#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""collect_thin.py --- 读 `drive_thin.py` 的末态剖面，给出 ALPHA*(W) 的判定表。

观测量（与 README §4.4b 一致）：
  c_int = 末态剖面上 φ 首次跨 0.5 处的 c ;  target = c_inf/k_e(T_int) = 0.056664
另外报 c 剖面的**拉伸宽 L_c**（c 从 10%→90% 过渡的宽度）用于核对 §4.6 的 `ALPHA*·W ~ 2.9 L_c`。
用法：collect_thin.py <目录前缀，默认 p1c_alpha2>
"""
import io
import os
import re
import sys
import numpy as np

TARGET = 0.056664
HERE = os.path.dirname(os.path.abspath(__file__))
pref = sys.argv[1] if len(sys.argv) > 1 else "p1c_alpha2"


def read_final_profile(d):
    fs = [f for f in os.listdir(d) if re.match(r"profile_line_\d+\.csv$", f)]
    if not fs:
        return None
    f = max(fs, key=lambda f: int(re.search(r"_(\d+)\.csv$", f).group(1)))
    rows = io.open(os.path.join(d, f), encoding="utf-8").read().strip().splitlines()
    hdr = rows[0].split(",")
    ix = {h: i for i, h in enumerate(hdr)}
    arr = np.array([[float(v) for v in r.split(",")] for r in rows[1:]])
    return arr[:, ix["x"]], arr[:, ix["c"]], arr[:, ix["phi"]]


print("观测量 c_int（末态 φ=0.5 处）；目标 %.6f" % TARGET)
print("%-22s %-6s %-10s %-10s %-10s %-9s" %
      ("case", "W(nm)", "ALPHA", "c_int", "vs目标", "L_c(nm)"))
res = {}
for d in sorted(os.listdir(HERE)):
    if not d.startswith(pref + "_W") or not os.path.isdir(os.path.join(HERE, d)):
        continue
    m = re.search(r"_W([0-9.]+)_A([0-9.]+)$", d)
    if not m:
        continue
    Wnm, A = float(m.group(1)), float(m.group(2))
    pr = read_final_profile(os.path.join(HERE, d))
    if pr is None:
        print("%-22s %-6g %-10g %s" % (d, Wnm, A, "（无剖面，可能还没跑完）"))
        continue
    x, c, phi = pr
    k = int(np.argmax(phi < 0.5)) if (phi < 0.5).any() else None
    if k is None or k == 0:
        print("%-22s %-6g %-10g %s" % (d, Wnm, A, "（找不到 φ=0.5 交叉）"))
        continue
    c_int = float(c[k])
    lo, hi = np.nanmin(c), np.nanmax(c)
    if hi > lo + 1e-12:
        i10 = int(np.argmax(c > lo + 0.1 * (hi - lo)))
        i90 = int(np.argmax(c > lo + 0.9 * (hi - lo)))
        Lc = float(abs(x[max(i10, i90)] - x[min(i10, i90)])) * 1e9
    else:
        Lc = float("nan")
    res[(Wnm, A)] = c_int
    print("%-22s %-6g %-10g %-10.6f %+8.1f%% %-9.1f" %
          (d, Wnm, A, c_int, 100 * (c_int / TARGET - 1), Lc))
print()
print("按 W 分组的 ALPHA*（线性插值到 c_int = target）：")
Ws = sorted(set(w for w, _ in res))
for W in Ws:
    pts = sorted([(a, v) for (w, a), v in res.items() if w == W])
    astar = None
    for (a1, v1), (a2, v2) in zip(pts, pts[1:]):
        if (v1 - TARGET) * (v2 - TARGET) <= 0 and abs(v2 - v1) > 1e-12:
            astar = a1 + (a2 - a1) * (TARGET - v1) / (v2 - v1)
            break
    print("   W = %-6g nm  ⇒  ALPHA* = %s   （VW/D_L = %.4f）"
          % (W, ("%.3f" % astar) if astar is not None else "未穿越目标",
             W * 1e-9 * 0.1 / 9.5e-9))