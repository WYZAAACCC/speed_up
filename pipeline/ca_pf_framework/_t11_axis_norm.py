#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_axis_norm.py —— 量 12 个变体的 `n* · a`（惯习面法向 与 长轴 的夹角）。

为什么必须先量（G3 的判据阈值不能拍）：
  `windowB_surface.py:1390-1392` 自己写明
     「`a` 并不垂直于 `n`（实测 `n.a = cos(82.7°) = 0.127`）
      ⇒ `n x (n x a)` 偏离真 `a` 约 **7.3°**」
  ⇒ 断言 "along·nrm ≈ 0" **可能本身就是错的**（物理上 `a` 未必落在惯习面内）。
本工具把 12 个变体的 `n*·a`、`n*·w`、`a·w` 全部打出来，并给统计量，
**据此决定 G3 的断言到底该写什么**（而不是照搬我早先的口头假设）。
"""
import sys

import numpy as np

sys.path.insert(0, ".")
import windowB_ti64_variants as V      # noqa: E402
import windowB_surface as WS           # noqa: E402

A_B, A_A, C_A = V.A_B, V.A_A, V.C_A
# 立方弹性张量（与 `T16_verify_rve.C` 同值：134/110/36 GPa）
c11, c12, c44 = 134e9, 110e9, 36e9
C = np.zeros((3, 3, 3, 3), float)
for i in range(3):
    for j in range(3):
        C[i, i, j, j] = c11 if i == j else c12
        if i != j:
            C[i, j, i, j] = c44
            C[i, j, j, i] = c44
argmin_normal_cached = WS.argmin_normal_cached

strains, F, meta = V.variants()
nv = len(strains)
print(f"变体数 = {nv}")
print(f"{'v':>3} {'n*·a':>10} {'|n*·a|':>10} {'n*·w':>10} {'a·w':>10}  角度(n*,a)")
rows = []
for v in range(nv):
    E = np.asarray(strains[v], float)
    nref, vmin, cons = argmin_normal_cached(C, E)
    R = WS.LevelSetMulti._rank1_axes(E, nref)
    n_ = np.asarray(nref, float); n_ /= np.linalg.norm(n_)
    a_ = np.asarray(R[1], float); a_ /= np.linalg.norm(a_)
    w_ = np.asarray(R[2], float); w_ /= np.linalg.norm(w_)
    d_na = float(n_ @ a_)
    d_nw = float(n_ @ w_)
    d_aw = float(a_ @ w_)
    ang = np.degrees(np.arccos(np.clip(abs(d_na), 0, 1)))
    rows.append((v + 1, d_na, d_nw, d_aw, ang))
    print(f"{v+1:>3} {d_na:>10.6f} {abs(d_na):>10.6f} {d_nw:>10.6f} {d_aw:>10.6f}  {ang:>8.3f}°")

na = np.array([abs(r[1]) for r in rows])
print(f"\n统计 |n*·a|：min={na.min():.6f}  max={na.max():.6f}  mean={na.mean():.6f}")
print(f"  ⇒ 最大夹角（偏离 90°）= {np.degrees(np.arccos(na.min())):.3f}°"
      f" ~ {np.degrees(np.arccos(na.max())):.3f}°")
print(f"  ⇒ 与 `:1391` 记的 `n.a = 0.127`（82.7°）对照："
      f"{'一致' if abs(na.max()-0.127) < 0.05 or abs(na.min()-0.127) < 0.05 else '**不一致，需查**'}")
print(f"\n判据建议（写给 G3）：断言 `|n*·a| <= {na.max():.4f}`"
      f"（= 实测最大值的 1.05 倍 = {na.max()*1.05:.4f}）")
print("  ⚠ 若采用 `--rank1-swap invariant`，V1/V3/V8 会被对调 ⇒ 该值应**变小**（趋于 0）。")
