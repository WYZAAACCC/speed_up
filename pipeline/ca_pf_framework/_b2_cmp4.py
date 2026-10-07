#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_cmp4.py —— 把 `B2P_pre` / `B2P_post` / `C4` 按**匹配步号**并排。

## 为什么要做
`C4` 是**已有的** `facet_proj=1`（= `pre` 口径）臂，且与 `B2P_*` **参数逐条相同**
（`_b2_arm.py` 就是照抄 `_t11_facet_arm.py` 的 argv）。
⇒ **`C4` 可以直接当 `B2P_pre` 的等效对照** ⇒ 可交叉验证口径是否真的对齐。
"""
import csv
import os
import sys

ROOTS = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_block",
         "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"]
TAGS = sys.argv[1:] or ["C4", "B2P_pre", "B2P_post"]


def load(tag):
    for r in ROOTS:
        p = os.path.join(r, "dry_%s" % tag, "series.csv")
        if os.path.exists(p):
            return {int(x["step"]): x for x in csv.DictReader(open(p, encoding="utf-8"))}
    return None


D = {t: load(t) for t in TAGS}
print("=" * 112)
print("按**匹配步号**并排：`step` | 各臂的 `Vt`（m³）与 `nf3_col`")
print("=" * 112)
have = [t for t in TAGS if D[t]]
if not have:
    print("  无数据")
    raise SystemExit(1)
steps = sorted(set().union(*[set(D[t]) for t in have]))
hdr = "  %-6s" % "step" + "".join("  %-24s" % t for t in have)
print(hdr)
for s in steps:
    row = "  %-6d" % s
    for t in have:
        r = D[t].get(s)
        if r is None:
            row += "  %-24s" % "—"
        else:
            row += "  %-24s" % ("%.5g / nf3=%s" % (float(r["Vt"]), r.get("nf3_col")))
    print(row)
print()
print("  ⇒ 若 `C4` 与 `B2P_pre` 逐行相同 ⇒ **口径对齐 ✅**（两者都是 `facet_proj=1`/`pre`）。")
