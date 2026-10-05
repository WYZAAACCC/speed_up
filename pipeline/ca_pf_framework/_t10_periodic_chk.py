#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_periodic_chk.py --- ★ 周期边界监控 + **量具自检**

## 为什么要做（新要求）
用户要求监控「板条长出盒子外时周期边界有没有正确发挥作用」。

## ⚠ 同时暴露一个**我自己的量具风险**
`_t10_allfields.py` / `_t10_seven.py` 用的是
`ndimage.label(mask, structure=S26)` —— **非周期**连通性。
若一根板条**横跨周期面**（+x 面 ↔ −x 面），它的胞在两个面上**物理上是一根**，
但非周期 labeling 会把它**数成两块** ⇒ **会虚增碎片、压低 ⑦**。

## 判据（**可 FAIL**）
1. **P1 存在性**：有多少个场**同时**在某个方向的**两个相对面**附近有胞？
   （这是"板条跨出盒子"的直接证据）
2. **P2 周期一致性**：把掩码按 `wrap` 补一圈后 labeling，
   分量数**是否减少**？（减少 ⇒ 非周期量具确实把跨面容错判成两块）
3. **P3 对 ⑦ 的影响**：给出**非周期**与**周期**两种口径下的
   「单一连通体场占比」—— 两者差多少。
4. **P4 物理自洽**：跨面容的 `band_val` 在相对面上是否**连续**
   （若周期 BC 正确，两侧的界面距离场应当接得上）。

⚠ 本脚本只**测量**，不改引擎；结论用于判断是否需要把量具改成周期口径。
"""
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
S26 = ndimage.generate_binary_structure(3, 3)
TAG = sys.argv[1] if len(sys.argv) > 1 else "t10PRT2_b3_1005_1213"
ST = int(sys.argv[2]) if len(sys.argv) > 2 else 100
p = os.path.join(HERE, "_exp/_bk_t5/dry_%s/snap_%05d.npz" % (TAG, ST))
with np.load(p, allow_pickle=False) as z:
    N = int(np.asarray(z["N"]))
    bi = np.asarray(z["band_idx"]).ravel().astype(np.int64)
    bv = np.asarray(z["band_val"]).ravel()
    bf = np.asarray(z["band_fld"]).ravel()
print("══ 周期边界监控  %s  step=%d  N=%d ══\n" % (TAG, ST, N))

FIELDS = [int(k) for k in np.unique(bf[bv < 0]) if int(k) != 0]
# 掩码与 band_val 立方体
cub = {}
for k in FIELDS:
    sel = (bf == k) & (bv < 0)
    idx = bi[sel]
    g = np.zeros((N, N, N), bool)
    g[idx // (N * N), (idx // N) % N, idx % N] = True
    if g.sum() < 30:
        continue
    v = np.full((N, N, N), np.nan)
    v[idx // (N * N), (idx // N) % N, idx % N] = bv[sel]
    cub[k] = (g, v)

print("  参与统计的场 = %d 个" % len(cub))

# ── P1 跨面场 ──
cross = {}
for k, (g, _v) in cub.items():
    hit = []
    for ax, nm in ((0, "x"), (1, "y"), (2, "z")):
        lo = np.take(g, 0, axis=ax)
        hi = np.take(g, N - 1, axis=ax)
        if lo.any() and hi.any():
            hit.append(nm)
    if hit:
        cross[k] = hit
print("\n  P1 同时出现在两个**相对面**附近的场 = **%d** 个" % len(cross))
for k, hit in list(cross.items())[:10]:
    print("      场 %-5d 跨 %s" % (k, "/".join(hit)))
if not cross:
    print("      （无）⇒ 当前没有板条跨出盒子")

# ── P2 周期 vs 非周期 labeling ──
def ncomp(g, periodic):
    if periodic:
        gp = np.pad(g, 1, mode="wrap")
        lab, nc = ndimage.label(gp, structure=S26)
        # 只数与原胞有交的分量
        inner = lab[1:-1, 1:-1, 1:-1]
        ids = np.unique(inner[g])
        return len(ids)
    _lab, nc = ndimage.label(g, structure=S26)
    return nc

print("\n  P2 分量数对照（非周期 → 周期）")
red = 0
one_np = one_pd = 0
for k, (g, _v) in sorted(cub.items()):
    a, b = ncomp(g, False), ncomp(g, True)
    if b < a:
        red += 1
        print("      场 %-5d %d → %d   ★ 周期口径下合并了" % (k, a, b))
    if a == 1:
        one_np += 1
    if b == 1:
        one_pd += 1
print("      ★ 因周期连通而被合并的场 = **%d** 个" % red)

# ── P3 对 ⑦ 的影响 ──
tot = len(cub)
print("\n  P3 ⑦「一场一根」占比")
print("      非周期口径（我此前一直用的）：%d/%d = **%.0f%%**" % (one_np, tot, 100.0 * one_np / tot))
print("      周期口径（物理上正确）      ：%d/%d = **%.0f%%**" % (one_pd, tot, 100.0 * one_pd / tot))
if one_pd != one_np:
    print("      ⚠ **两种口径不同** ⇒ 我的 ⑦ 量具此前**低估**了（把跨面容算成两块）")
else:
    print("      ✅ 两种口径一致 ⇒ 此前 ⑦ 的测量**未受此影响**")

# ── P4 跨面容的 band_val 连续性 ──
print("\n  P4 跨面容在相对面上的 band_val 连续性（周期 BC 是否接得上）")
for k, hit in list(cross.items())[:6]:
    g, v = cub[k]
    for nm in hit:
        ax = {"x": 0, "y": 1, "z": 2}[nm]
        lo = np.take(v, 0, axis=ax)
        hi = np.take(v, N - 1, axis=ax)
        m = ~np.isnan(lo) & ~np.isnan(hi)
        if m.sum() < 3:
            print("      场 %-5d 轴 %s ：重叠格点 %d（太少，无法判）" % (k, nm, int(m.sum())))
            continue
        d = np.abs(lo[m] - hi[m])
        print("      场 %-5d 轴 %s ：重叠 %d 格，|Δband_val| 中位 = %.4e（量级 = 界面距离）"
              % (k, nm, int(m.sum()), float(np.median(d))))
print()
print("  ⚠ 本脚本只测量；是否把量具改成周期口径，取决于 P2/P3 的结果。")
