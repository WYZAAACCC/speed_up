#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_banner_diff.py —— 比对两臂 banner 的关键行（硬步骤 C：开跑后读全文）。

判据（可 FAIL）：**两臂 banner 必须只差 `--nuc-iface-nucleation` 那一项**。
若有别的差异 ⇒ **不是单因素对照** ⇒ 结论作废。
"""
import os
import re
import sys

LOGS = {"OFF": "/mnt/f/speed_up/_w2_ifaceOFF.log",
        "ON": "/mnt/f/speed_up/_w2_ifaceON.log"}
# 只挑**决定性**的键（banner 里以 `key=` 或 `key =` 出现）
KEYPAT = re.compile(
    r"(nuc_iface_nucleation|nuc_resample_ungated|nuc_count_mode|per_field_axes|"
    r"nuc_order_by_drive|nuc_law|nuc_init|nuc_block_target|nuc_block_parallel|"
    r"alpha_km|T_end|qs_clock|qs_max_relax|nv=|N=|steps=)\s*[=:]?\s*([\w.\-+e]+)")


def scan(p):
    if not os.path.exists(p):
        return None
    out = {}
    for ln in open(p, encoding="utf-8", errors="replace"):
        for k, v in KEYPAT.findall(ln):
            out.setdefault(k, v)
    return out


a, b = scan(LOGS["OFF"]), scan(LOGS["ON"])
print("=" * 84)
print("两臂 banner 关键项比对（硬步骤 C）")
print("=" * 84)
if a is None or b is None:
    sys.exit(f"**缺日志** OFF={a is not None} ON={b is not None}")
keys = sorted(set(a) | set(b))
diff = []
for k in keys:
    va, vb = a.get(k, "(缺)"), b.get(k, "(缺)")
    flag = "" if va == vb else "   ← **不同**"
    if va != vb:
        diff.append(k)
    print(f"  {k:24} OFF={va:<14} ON={vb:<14}{flag}")

print("\n" + "=" * 84)
print(f"不同的项（{len(diff)}）：{diff}")
ok = diff in ([], ["nuc_iface_nucleation"])
if ok:
    print("  ⇒ ✅ **两臂只差 `nuc_iface_nucleation`** ⇒ 单因素对照成立")
else:
    print("  ⇒ ❌ **不止差一项** ⇒ **不是单因素对照，结论作废**，必须重跑")
print("=" * 84)
