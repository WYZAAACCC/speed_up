#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_ratio2.py <base> <arm>... —— 同配置的**同 `Vt` 步数比**（线性插值，分母 = `base`）。

与 `_b2_vtratio.py` 的区别：那个把分母写死为 `W0`（不同配置）；
本工具**分母作为参数** ⇒ 可以做**逐条同参**的干净对照。
"""
import csv
import os
import sys

ROOTS = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_block",
         "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"]


def load(tag):
    for r in ROOTS:
        p = os.path.join(r, "dry_%s" % tag, "series.csv")
        if os.path.exists(p):
            rows = list(csv.DictReader(open(p, encoding="utf-8")))
            return [(int(x["step"]), float(x["Vt"])) for x in rows if x.get("Vt")]
    return None


def step_at(curve, vt):
    for i in range(1, len(curve)):
        s0, v0 = curve[i - 1]
        s1, v1 = curve[i]
        if v0 <= vt <= v1 and v1 > v0:
            return s0 + (s1 - s0) * (vt - v0) / (v1 - v0)
    return None


base = sys.argv[1]
arms = sys.argv[2:]
cb = load(base)
print("=" * 96)
print("同 `Vt` 步数比（**分母 = `%s`**，逐条同参的干净对照）" % base)
print("=" * 96)
if not cb:
    print("  ⛔ 无基准 %s" % base)
    raise SystemExit(1)
print("  基准 %s：%d 行，Vt %.4g → %.4g m³" % (base, len(cb), cb[0][1], cb[-1][1]))
print("\n  %-10s %-13s" % ("基准step", "基准Vt(m³)") + "".join("  %-20s" % a for a in arms))
for sb, vb in cb:
    if sb not in (100, 150, 200, 250, 300, 350, 400):
        continue
    line = "  %-10d %-13.4g" % (sb, vb)
    for a in arms:
        ca = load(a)
        if not ca:
            line += "  %-20s" % "无数据"
            continue
        sa = step_at(ca, vb)
        line += ("  %-20s" % ("step=%.0f 比=%.3f" % (sa, sa / sb))) if sa is not None \
            else ("  %-20s" % "未达到")
    print(line)
print("\n  ⇒ 靶 1.0–1.3（越接近 1.0 越『中性』）。")
