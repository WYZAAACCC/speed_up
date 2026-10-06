#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_dupcheck2.py <tagA> <tagB> —— **核实两臂是否真的逐位相同**（防量具读错目录）。

## 为什么必须查（`R647`）
`B60@500` 的逐场数字与 `B40@500` **逐位相同**。两种可能：
  (a) **真实饱和**：`band_cells ≥ 40` 后行为不变（确定性 ⇒ 逐位相同是**应有的**）；
  (b) **量具错**：读到了同一个目录。
判据：比 `series.csv` 的 `Vt` 序列与快照 `region` 的**字节哈希**。
  · 若**全同** ⇒ (a) 成立（真的饱和）；
  · 若**不同** ⇒ (b) 成立（我的读数错了）。
"""
import csv
import hashlib
import os
import sys

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
A, B = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("B40", "B60")


def vts(tag):
    p = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
    d = {}
    for r in csv.DictReader(open(p, encoding="utf-8")):
        try:
            d[int(r['step'])] = float(r['Vt'])
        except (KeyError, ValueError):
            pass
    return d


def hsh(tag, st):
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % st)
    if not os.path.exists(p):
        return None
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]


va, vb = vts(A), vts(B)
common = sorted(set(va) & set(vb))
print("=" * 88)
print("核实 %s vs %s 是否逐位相同" % (A, B))
print("=" * 88)
print("  %-7s %-16s %-16s %-10s %s" % ('step', 'A.Vt', 'B.Vt', 'Vt 相同?', 'region 哈希'))
same = 0
for st in common:
    eq = (va[st] == vb[st])
    same += eq
    ha, hb = hsh(A, st), hsh(B, st)
    hh = ('—' if ha is None or hb is None else
          ('**相同**' if ha == hb else '不同'))
    print("  %-7d %-16.8g %-16.8g %-10s %s  A=%s B=%s"
          % (st, va[st], vb[st], '是' if eq else '否', hh, ha, hb))
print()
print("  ⇒ `Vt` 逐位相同的 step：**%d / %d**" % (same, len(common)))
print("  ⇒ 判读：若全同 ⇒ **(a) 真实饱和**（`band_cells >= 40` 后行为不变）；")
print("           若有不同 ⇒ **(b) 我的量具读数有误**。")
