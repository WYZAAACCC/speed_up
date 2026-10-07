#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_box_verify.py <tag>@<step> —— **核实"场到底是不是一个盒子"**（正面对账）。

## 为什么（`R650`）
我的"填充率"判据给出 0.16–0.29（看起来"不是盒子"），但 `facet_project` 会**替换** `φ_k` 为盒子
⇒ 若投影真的生效，填充率应 ≈ 1。矛盾 ⇒ 必须逐层查：
  ① 三轴是否**正交**（不正交 ⇒ 我的投影坐标错）；
  ② 每个轴上**实际占用的格点层数**（盒子应"层数 ≈ 跨度"且是**连续**的）；
  ③ **`region == k` 是不是"盒子减去别人"**（winner-take-all 会切掉重叠部分）。
"""
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
spec = sys.argv[1] if len(sys.argv) > 1 else "B40@700"
tag, _, st = spec.partition('@')
st = int(st)
p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % st)
with np.load(p, allow_pickle=False) as z:
    reg = np.asarray(z['region']).astype(np.int32)
    L = float(np.asarray(z['L']).ravel()[0])
    N = int(np.asarray(z['N']).ravel()[0])
    dx = L / N
    nh = np.asarray(z['n_hab'], float)
    a = np.asarray(z['a_ax'], float)
    w = np.asarray(z['w_ax'], float)
U = np.stack([nh, a, w], 0)
print("=" * 88)
print("【%s】step %d" % (tag, st))
print("=" * 88)
print("  ① 三轴正交性：n*·a=%.4f  n*·w=%.4f  a·w=%.4f"
      % (float(nh @ a), float(nh @ w), float(a @ w)))
print("     ⚠ `R628 §9` 已记账：`a` 与 `n*` **不正交**（a·n* = 0.127）")
print()
print("  %-6s %-9s %-30s %s" % ('场', '胞数', '三轴：跨度 / 占用层数', '填充率'))
for k in sorted(int(v) for v in np.unique(reg) if v > 0):
    m = (reg == k)
    n0 = int(m.sum())
    if n0 < 50:
        continue
    idx = np.argwhere(m).astype(float)
    pr = idx @ U.T
    row = []
    boxvox = 1.0
    for j, nm in enumerate(('n*', 'a', 'w')):
        lo, hi = pr[:, j].min(), pr[:, j].max()
        span = hi - lo + 1.0
        # 该轴上"占用层数"：把坐标四舍五入到整数层，数唯一的层
        occ = len(np.unique(np.round(pr[:, j]).astype(int)))
        boxvox *= span
        row.append('%s: %.0f胞/%d层' % (nm, span, occ))
    print("  %-6d %-9d %-30s %.3f" % (k, n0, '  '.join(row), n0 / max(boxvox, 1)))
print()
print("  ⇒ 判读：若『占用层数 ≈ 跨度』且填充率 ≈ 1 ⇒ 是实心盒子；")
print("           若『占用层数 ≪ 跨度』⇒ 该轴方向是稀疏的（不是实心盒子）。")
