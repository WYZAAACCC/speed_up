#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_vtratio.py —— **`B2-D3②` 的判据**：同 `Vt` 步数比。

## 判据定义（goal 原文）
> "达到同一 `Vt` 所需步数"与**不开投影**对照**不再差 2.3×**（靶 1.0–1.3）

## 做法
1. 取**不开投影**的臂（`W0`，`facet_proj=0`）作**分母基准**；
2. 对每个 `post`/`pre` 臂，求"达到与基准同一 `Vt` 所需的步数"；
3. 比值 = `steps(臂) / steps(基准)`。
⚠ 步号匹配用**线性插值**（两臂的 CSV 步号网格可能不同）。
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


def step_at_vt(curve, vt):
    """在 `curve`（按 step 升序）上求 `Vt == vt` 的 step（线性插值）。"""
    for i in range(1, len(curve)):
        s0, v0 = curve[i - 1]
        s1, v1 = curve[i]
        if v0 <= vt <= v1 and v1 > v0:
            return s0 + (s1 - s0) * (vt - v0) / (v1 - v0)
    return None


BASE = "W0"                     # 不开投影（facet_proj=0）
ARMS = sys.argv[1:] or ["B2P_pre", "B2P_post", "C4"]
cb = load(BASE)
print("=" * 104)
print("`B2-D3②`：同 `Vt` 步数比（分母 = **不开投影**的 `%s`）" % BASE)
print("=" * 104)
if not cb:
    print("  ⛔ 无基准臂 %s" % BASE)
    raise SystemExit(1)
print("  基准 %s：%d 行，Vt 从 %.4g 到 %.4g m³"
      % (BASE, len(cb), cb[0][1], cb[-1][1]))
# 取几个基准自身的 step 作靶
targets = [(s, v) for s, v in cb if s in (100, 150, 200, 250, 300)]
print("\n  %-8s %-13s" % ("基准step", "基准Vt(m³)") + "".join("  %-22s" % a for a in ARMS))
for sb, vb in targets:
    line = "  %-8d %-13.4g" % (sb, vb)
    for a in ARMS:
        ca = load(a)
        if not ca:
            line += "  %-22s" % "无数据"
            continue
        sa = step_at_vt(ca, vb)
        if sa is None:
            line += "  %-22s" % "未达到该Vt"
        else:
            line += "  %-22s" % ("step=%.0f  比=%.3f" % (sa, sa / sb))
    print(line)
print()
print("  ⇒ 靶（`B2-D3②`）：**比 ∈ 1.0–1.3**；不开投影与开投影的旧实测是 **0.44**（2.27×）。")
