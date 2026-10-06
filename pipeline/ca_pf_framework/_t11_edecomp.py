#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_edecomp.py <tag> —— (2) **能量分解**：把"宽面净驱动为何归零"拆开。

## 物理分解（单位 J/m³）
界面的净驱动 = **化学** − **弹性** − **界面能（曲率）**：
    `dG = ΔG_chem − ΔG_el − ΔG_int`
其中 `ΔG_el = E_el_J / Vt`（弹性能密度）、`ΔG_int ≈ 2γ·A_f1/(3·Vt)`（球形化近似）。

## 判据（可 FAIL，先登记）
对一个**厚度已停止增长**的算例（如 `t5AB_B` 场 8，147→150 nm 跨 880 步）：
  · **E1**：若 `dG_wide` 的**归零**伴随 `ΔG_el` **上升到与 `ΔG_chem` 相当** ⇒ **能量平衡**（物理）✅
  · **E2**：若 `ΔG_el/Vt` 与 `ΔG_int` **都远小于** `dG_max`（即驱动仍很大）⇒
    归零**不是能量造成的** ⇒ 只能是**方向性迁移率压制** ⇒ 该通道**不是能量机制** ⚠
  · **E3**（自一致性）：`dG_max` 应 ≈ `ΔG_chem − ΔG_el`（在 `ΔG_int` 最小处）
"""
import csv
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
tag = (sys.argv[1] if len(sys.argv) > 1 else "t5AB_B")
tag = tag[4:] if tag.startswith('dry_') else tag
p = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
rows = list(csv.DictReader(open(p, encoding="utf-8")))
print("=" * 108)
print("【%s】能量分解（`ΔG_el = E_el_J/Vt`；`ΔG_int ≈ 2γ·A_f1/(3Vt)`，γ 取 `gamma0`）" % tag)
print("=" * 108)
print("  %-6s %-11s %-12s %-12s %-12s %-12s %-12s"
      % ('step', 'Vt(µm³)', 'E_el_J', 'ΔG_el', 'ΔG_int', 'dG_max', 'dG_wide'))
GAMMA = 0.25          # J/m²，生产用 gamma0
out = []
for r in rows:
    try:
        st = int(r['step'])
        vt = float(r['Vt'])
        eel = float(r['E_el_J'])
        f1 = float(r['f1_area_m2'])
        dgm = float(r['dG_max_Jm3'])
        dgw = float(r.get('dG_wide') or 'nan')
    except (TypeError, ValueError, KeyError):
        continue
    if vt <= 0:
        continue
    dgel = eel / vt
    dgint = 2.0 * GAMMA * f1 / (3.0 * vt) if f1 > 0 else float('nan')
    out.append((st, vt, eel, dgel, dgint, dgm, dgw))
    print("  %-6d %-11.4g %-12.4g %-12.4g %-12.4g %-12.4g %-12.4g"
          % (st, vt * 1e18, eel, dgel, dgint, dgm, dgw))
if len(out) < 3:
    sys.exit("数据点不足")
f, l = out[0], out[-1]
print("\n  ⇒ 首末对比：")
print("     ΔG_el  : %.4g → %.4g  (%+.1f%%)"
      % (f[3], l[3], 100 * (l[3] - f[3]) / max(abs(f[3]), 1e-30)))
print("     ΔG_int : %.4g → %.4g" % (f[4], l[4]))
print("     dG_max : %.4g → %.4g  (%+.1f%%)"
      % (f[5], l[5], 100 * (l[5] - f[5]) / max(abs(f[5]), 1e-30)))
print("     dG_wide: %.4g → %.4g" % (f[6], l[6]))
print()
# E1 / E2 判据
ratio = l[3] / max(abs(l[5]), 1e-30)
print("  ★ 判据 E1（ΔG_el 与 dG_max 相当 ⇒ 能量平衡）：ΔG_el/dG_max = **%.3f** ⇒ %s"
      % (ratio, "✅ E1 成立（弹性确实在抵消化学驱动）" if ratio > 0.5
         else "❌ E1 不成立（弹性远小于驱动）"))
print("  ★ 判据 E2（ΔG_el 与 ΔG_int 都 ≪ dG_max ⇒ 归零非能量所致）："
      "ΔG_int/dG_max = **%.3f** ⇒ %s"
      % (l[4] / max(abs(l[5]), 1e-30),
         "⚠ E2 成立 ⇒ **宽面归零不是能量造成的**（是方向性迁移率压制）"
         if l[4] / max(abs(l[5]), 1e-30) < 0.1 else "E2 不成立"))
