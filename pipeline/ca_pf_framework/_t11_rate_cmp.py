#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_rate_cmp.py <tagA> <tagB> —— **按同一 `Vt` 比"长到该体积各用了多少步"**（正确口径）。

## 为什么不能用"同 step 比 Vt"
`R641` 我曾写"`L1` 的 `Vt` 是 `L0` 的 2.16 倍" —— 那是**同 step**（都到 step 125）比的，
而两臂的**时间步长 `dt` 不同**（`dt` 由 CFL 与 `dG_max` 定）⇒ **同 step ≠ 同物理时间**。
⇒ 正确做法：**在同一 `Vt` 上比所需 step（或物理时间 `t_s`）**，得到"生长速率之比"。
"""
import csv
import os
import sys

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
A, B = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("L0", "L1")


def load(tag):
    p = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
    rows = []
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            try:
                rows.append((int(r['step']), float(r['Vt']),
                             float(r.get('t_s') or 'nan'),
                             float(r.get('dt') or 'nan')))
            except (KeyError, ValueError):
                pass
    return rows


ra, rb = load(A), load(B)
print("=" * 96)
print("按同一 `Vt` 比『长到该体积用了多少步/多少物理时间』：A=%s  B=%s" % (A, B))
print("=" * 96)
print("  %-13s %-11s %-13s %-11s %-9s %s"
      % ('Vt(m³)', 'A.step', 'A.t_s(s)', 'B.step', 'B.t_s(s)', '步数比 A/B'))
print("  %-13s %-11s %-13s %-11s %-9s %s"
      % ('', '', '', '', '', '（>1 ⇒ A 更慢）'))
ratios = []
for st_a, vt_a, ts_a, _ in ra:
    if st_a % 50:
        continue
    cand = [(abs(vt_b - vt_a) / max(vt_a, 1e-300), st_b, ts_b)
            for st_b, vt_b, ts_b, _ in rb
            if abs(vt_b - vt_a) / max(vt_a, 1e-300) < 0.10]
    if not cand:
        continue
    _, st_b, ts_b = min(cand)
    r = st_a / max(st_b, 1)
    ratios.append(r)
    print("  %-13.4g %-11d %-13.4g %-11d %-9.4g **%.3f**"
          % (vt_a, st_a, ts_a, st_b, ts_b, r))
if ratios:
    import statistics
    print("\n  ⇒ 达到同一 `Vt` 所需步数之比的**中位** = **%.3f**"
          % statistics.median(ratios))
    print("     判读：>1 ⇒ A(`%s`) 更慢；<1 ⇒ A 更快" % A)
print()
print("  ⚠ 记账：若两臂 `dt` 不同，**步数比不等于物理时间比** ⇒ 上表同时给出 `t_s`。")
