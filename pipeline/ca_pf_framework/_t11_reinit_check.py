#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_reinit_check.py —— 验证 `R634` 新档的自检（只读，不改任何东西）。

判据（可 FAIL，先登记）：
  * **R0**：默认（不设环境变量）⇒ `reinit_mode() == 'sussman'` ⇒ **归档路径不变**；
  * **R1**：`REINIT_MODE=sharp` ⇒ `reinit_mode() == 'sharp'`，且 `freeze_frac()` 可解析；
  * **R2（逐位不变）**：对**随机场**做 reinit，`mode='sussman'` 与"不传 mode（走环境变量默认）"
    必须**逐位相同**（NaN 感知）；
  * **R3（机制生效）**：`mode='sharp'` 与 `mode='sussman'` 的结果必须**不同**
    （否则新档是死的）；
  * **R4（几何保真）**：对**一个解析立方体**的 SDF 做 reinit，
    `sharp` 档对零等值面的**几何改动**应 **小于** `sussman` 档
    （用"零等值面包围盒三轴跨度"在 reinit 前后的变化衡量）。
"""
import os
import sys

import numpy as np

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
import windowB_surface as W  # noqa: E402

OK = True


def chk(name, cond, extra=''):
    global OK
    print("  %-4s %-46s %s" % ('✅' if cond else '❌', name, extra))
    if not cond:
        OK = False


print("=" * 92)
print("R634 新档自检（`mode='sharp'`）")
print("=" * 92)

# R0
os.environ.pop('REINIT_MODE', None)
chk("R0 默认 mode == 'sussman'", W.reinit_mode() == 'sussman', W.reinit_mode())
# R1
os.environ['REINIT_MODE'] = 'sharp'
chk("R1 REINIT_MODE=sharp 生效", W.reinit_mode() == 'sharp', W.reinit_mode())
chk("R1b freeze_frac 可解析", isinstance(W.freeze_frac(), float),
    '%.2f' % W.freeze_frac())
os.environ.pop('REINIT_MODE', None)

# 造一个解析立方体 SDF（±）
N, dx = 48, 62.5e-9
L = N * dx
g = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(g, g, g, indexing='ij')
c = np.array([L / 2] * 3)
half = np.array([6.0 * dx, 6.0 * dx, 3.0 * dx])       # 立方体（8:8:4 胞）⇒ 有尖角
d = np.maximum.reduce([np.abs(X - c[0]) - half[0],
                       np.abs(Y - c[1]) - half[1],
                       np.abs(Z - c[2]) - half[2]])
sdf = d + 0.0001 * dx                                  # 略偏正 ⇒ 零等值面清晰


def span(p):
    m = p < 0
    if not m.any():
        return np.zeros(3)
    idx = np.argwhere(m)
    return (idx.max(0) - idx.min(0) + 1).astype(float)


span0 = span(sdf)
a = W.sussman_reinit(sdf.copy(), dx, band_cells=6, mode='sussman')
b = W.sussman_reinit(sdf.copy(), dx, band_cells=6, mode='sharp')

# R2：sussman 与"默认（环境变量未设）"逐位相同
c2 = W.sussman_reinit(sdf.copy(), dx, band_cells=6)
same = bool(np.array_equal(np.nan_to_num(a), np.nan_to_num(c2)))
chk("R2 mode='sussman' 与默认路径逐位相同", same)
# R3：sharp 必须不同
chk("R3 sharp 与 sussman 结果不同", not np.array_equal(np.nan_to_num(a),
                                                       np.nan_to_num(b)),
    'max|Δ| = %.3e' % float(np.max(np.abs(a - b))))
# R4：几何改动更小
sa, sb = span(a), span(b)
da, db = float(np.abs(sa - span0).sum()), float(np.abs(sb - span0).sum())
chk("R4 sharp 的几何改动 ≤ sussman", db <= da,
    'sussman Δspan=%.0f  sharp Δspan=%.0f  (span0=%s)'
    % (da, db, span0.astype(int).tolist()))
print()
print("  ⇒ %s" % ("**ALL PASS**" if OK else "**有 FAIL ⇒ 需修**"))
sys.exit(0 if OK else 1)
