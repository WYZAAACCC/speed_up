#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_read_dbg.py —— 读算例的 `nuc_dbg.json` 里的关键字段（避开 PowerShell 的 JSON 坑）。

用法: _t11_read_dbg.py <tag> [键名...]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
# ⚠ 2026-10-05 实测：`--out _exp/_bk_t5` 被引擎解析到 **`F:\speed_up\_exp\_bk_t5`**
#   （不是 `pipeline/ca_pf_framework/_exp/_bk_t5`）⇒ 两处都试。
CAND = [os.path.join(ROOT, "_exp", "_bk_t5"),
        "/mnt/f/speed_up/_exp/_bk_t5"]
tag = sys.argv[1] if len(sys.argv) > 1 else "dry_drvsmoke"
keys = sys.argv[2:] or ["drive_pick", "dbg"]
EXP = next((c for c in CAND if os.path.isdir(os.path.join(c, tag))),
           os.path.join(ROOT, "_exp", "_bk_t5"))
p = os.path.join(EXP, tag, "nuc_dbg.json")
print(f"{p}\n")
if not os.path.exists(p):
    sys.exit(f"!! 不存在: {p}")
d = json.load(open(p, encoding="utf-8"))
print(f"顶层键（{len(d)}）: {sorted(d.keys())}\n")
for k in keys:
    if k in d:
        print(f"=== {k} ===")
        print(json.dumps(d[k], ensure_ascii=False, indent=1)[:2000])
        print()
    else:
        print(f"（没有键 {k!r}）\n")
# 形核相关的几个量
for k in ("n_eng_ev",):
    if k in d:
        print(f"{k} = {d[k]}")
