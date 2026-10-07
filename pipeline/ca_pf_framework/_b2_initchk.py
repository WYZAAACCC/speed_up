#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_initchk.py <tag>... —— 查两臂的**初始态**是否可比（`R695` 的疑点）。

## 为什么要查
`B2L_pre` 的 `step 0` `Vt` = 2.25e-18 m³，而 `C4` 只有 1.95e-21 ⇒ **差 1150 倍**。
⇒ 两个臂的"第 0 行"**不是同一个意思**（可能一个含播种的完整堆叠、另一个不含）
⇒ **直接比它们会得出错误结论**（`P8`/`P18`：先对齐口径）。
"""
import csv
import os
import sys

ROOTS = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_block",
         "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"]
TAGS = sys.argv[1:] or ["B2L_pre", "C4", "G4"]


def find(tag):
    for r in ROOTS:
        p = os.path.join(r, "dry_%s" % tag, "series.csv")
        if os.path.exists(p):
            return p
    return None


print("=" * 110)
print("初始态可比性检查 —— 前 6 行的 step / Vt / nf3 / nslab / ed_soft")
print("=" * 110)
for t in TAGS:
    p = find(t)
    if not p:
        print("\n【%s】无 CSV" % t)
        continue
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    print("\n【%s】共 %d 行；step 列前 8 个 = %s"
          % (t, len(rows), [r.get("step") for r in rows[:8]]))
    for r in rows[:6]:
        print("     step=%-6s Vt=%-12.6g nf3=%-4s nslab=%-4s f3_area=%.4f µm²"
              % (r.get("step"), (float(r["Vt"]) if r.get("Vt") else float('nan')),
                 r.get("nf3_col"), r.get("nslab_n", "—"),
                 (float(r["f3_area_m2"]) * 1e12 if r.get("f3_area_m2") else float('nan'))))
