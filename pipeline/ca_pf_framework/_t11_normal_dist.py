#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_normal_dist.py —— **真实界面上"界面法向"的分布**（判 `Mfac` 的有效各向异性）。

## 为什么这是关键判据
`Mfac = exp(−β_h(n·n*)²−β_w(n·w)²)` 的**有效各向异性**取决于**界面上真实的 `n` 分布**：
  · 若界面**平坦**（`n` 集中在 `n*` 或 `a/w`）⇒ `Mfac` 面内比 = `e^{β_w}` ≈ **10**；
  · 若界面**弥散/起伏**（`n` 连续铺满所有取向）⇒ `Mfac` 被**角平均** ⇒ 比值塌到 **~2**
    （这正是 `R30_AUDIT_LEDGER.md:2655` 的"角平均 1.97"）。
⇒ **本工具直接量这个分布**，不再从形状反推。

## 怎么量（用已有快照，不跑算例）
对某场的界面胞（`|φ|` 最小的那一层，由 `region` 边界近似）：
  · 该场与其"母相"的分界 ≈ `region != k`
  · 界面法向用**距离场梯度**：对该场的胞集合做 EDT ⇒ `∇d` 即法向
  · 统计 `(n·n*)²` 与 `(n·w)²` 的分布 ⇒ 代入 `Mfac` 求**有效面内比**
"""
import glob
import os
import sys

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
tag = (sys.argv[1] if len(sys.argv) > 1 else "kW1")
tag = tag[4:] if tag.startswith('dry_') else tag
field = int(sys.argv[2]) if len(sys.argv) > 2 else 1
step = int(sys.argv[3]) if len(sys.argv) > 3 else 200
BH, BW = 6.477, 2.3

p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % step)
if not os.path.exists(p):
    sys.exit("缺 %s" % p)
with np.load(p, allow_pickle=False) as z:
    reg = np.asarray(z['region']).astype(np.int32)
    a, w, nh = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))

m = (reg == field)
if m.sum() < 50:
    sys.exit("场 %d 太小（%d 胞）" % (field, m.sum()))
# 距离场：到场外的距离 ⇒ 梯度指向外法向
d = distance_transform_edt(m)
g = np.gradient(d, DX)
gn = np.sqrt(sum(x ** 2 for x in g))
# 只取**界面附近**（0.5–3 胞）
band = m & (d <= 3.0) & (gn > 1e-9)
idx = np.argwhere(band)
nx = np.stack([g[0][band], g[1][band], g[2][band]], axis=1)
nx = nx / np.maximum(np.linalg.norm(nx, axis=1, keepdims=True), 1e-300)
c2n = np.clip(nx @ nh, -1, 1) ** 2
c2w = np.clip(nx @ w, -1, 1) ** 2
c2a = np.clip(nx @ a, -1, 1) ** 2
MF = np.exp(-BH * c2n) * np.exp(-BW * c2w)
print("=" * 92)
print("【%s】场 %d @ step %d ：界面法向分布（界面胞 %d 个）" % (tag, field, step, idx.shape[0]))
print("=" * 92)
print("  (n·n*)²  分位：p10=%.3f  p50=%.3f  p90=%.3f" %
      tuple(np.percentile(c2n, [10, 50, 90])))
print("  (n·a )²  分位：p10=%.3f  p50=%.3f  p90=%.3f" %
      tuple(np.percentile(c2a, [10, 50, 90])))
print("  (n·w )²  分位：p10=%.3f  p50=%.3f  p90=%.3f" %
      tuple(np.percentile(c2w, [10, 50, 90])))
print()
print("  `Mfac` 分位：p10=%.4f  p50=%.4f  p90=%.4f  mean=%.4f"
      % (np.percentile(MF, 10), np.percentile(MF, 50),
         np.percentile(MF, 90), MF.mean()))
# 按"宽面 / 面内"分组，算有效比值
wide = c2n > 0.5          # 宽面（法向≈n*）
inpl = c2n < 0.1          # 面内（法向⊥n*）
r_in = MF[inpl].mean() if inpl.sum() > 10 else float('nan')
r_wi = MF[wide].mean() if wide.sum() > 10 else float('nan')
print()
print("  · 宽面胞（(n·n*)²>0.5）: %d 个（%.1f%%），其 `Mfac` 均值 = **%.4f**"
      % (wide.sum(), 100.0 * wide.mean(), r_wi))
print("  · 面内胞（(n·n*)²<0.1）: %d 个（%.1f%%），其 `Mfac` 均值 = **%.4f**"
      % (inpl.sum(), 100.0 * inpl.mean(), r_in))
print()
print("  ⇒ **有效面内/宽面 迁移率比 = %.3f**" % (r_in / max(r_wi, 1e-30)))
print("     （设计值 `e^{β_w}` = %.3f；`R30_AUDIT` 的『角平均』 = 1.97）" % np.exp(BW))
print()
print("  ⇒ 若该比值 ≈ 设计值 ⇒ `Mfac` 本身没被角平均 ⇒ **冲销在平流**；")
print("     若该比值 ≈ 2 ⇒ **`Mfac` 自己就被角平均了**（因界面法向分布弥散）。")
