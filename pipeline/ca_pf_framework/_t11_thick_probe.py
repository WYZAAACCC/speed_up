#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_thick_probe.py —— **判定 `seed_plate` 的厚度约定**（解析探针，不跑引擎步）。

## 为什么要它（`R625 §4.6.3/§4.6.4` 留下的"分辨力不足"）
  生产 `--eng-t-nm 250` + `--nuc-overlap-nm 62.5` ⇒ `t_nuc = 312.5 nm`（`R28` 自动补厚度）。
  而 `seed_plate(k, c, n, R, t, …)` 内部用 `|d| ≤ t/2`，同时调用点 `:1879` 用 `Tj/2` 当厚度
  ⇒ **同一个量可能被除了两次 2**。
  实测 `blk_span_nm = 507 nm` 与两种解释都不干净吻合 ⇒ 需**解析探针**。

## 探针做法（纯几何，**不推进动力学**）
  1. 造一个最小 `LevelSetMulti`（N=64、`dx=62.5 nm`）；
  2. `seed_plate(1, center, n_hat, R, t)`，`t` 取三种候选；
  3. 用**密集法向采样**（25×25×25 点）算 `d(x) = (x−c)·n̂`，
     取 `|φ|` 最小的那层壳上 `d` 的 `[min,max]` ⇒ **物理厚度**；
  4. 与 `τ`, `τ/2`, `τ+2Δx`, `τ/2+2Δx` 对比 ⇒ 判定是哪种约定。
"""
import sys

import numpy as np

sys.path.insert(0, '.')
import windowB_surface as W          # noqa: E402
# ⚠ `C`/`EPS0` 不在 `windowB_ti64_variants` 里 —— `_bk_exp.py:48` 是从
#   `T16_verify_rve` 导入的（我第一版搞错了模块名）。
from T16_verify_rve import C, EPS0   # noqa: E402

N = 64
DX = 62.5e-9
L = N * DX
ENG_R = 320e-9
ENG_T_NM = 250.0
O_NM = 62.5
TAU_NM = ENG_T_NM + O_NM             # 312.5（R28 自动补厚度）

g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.25, Mob=1e-9)
print(f"LevelSetMulti 建好：N={N}  dx={DX*1e9:.1f} nm  L={L*1e6:.3f} µm")

n_hat = np.array([0.0, 0.0, 1.0])    # 取 +z 为法向，便于读
n_hat /= np.linalg.norm(n_hat)
c = np.array([L / 2, L / 2, L / 2])

# ⚠ 第一版错：φ 是**整格**（N³=262144），而我的采样点是 25³=15625 ⇒ 索引不匹配。
#   ⇒ 改成**直接用 φ 的零水平集胞**（在整格上取 `|φ|` 最小的那一层），更简单也更准确。
ii = (np.arange(N) + 0.0) * DX
Xg, Yg, Zg = np.meshgrid(ii, ii, ii, indexing='ij')
POS = np.stack([Xg.ravel(), Yg.ravel(), Zg.ravel()], 1)      # (N³, 3)
print(f"整格点 {POS.shape[0]} 个（{N}³）")


def phys_thickness(kfield):
    """取 `|φ|` 最小的**一层壳**上的胞，量它们沿 `n̂` 的 `[min,max]` ⇒ 物理厚度。"""
    phi = np.asarray(g.phi[kfield]).ravel()
    thr = DX / 2.0
    m = np.abs(phi) <= thr
    if m.sum() < 8:
        return None, None, int(m.sum())
    d = (POS[m] - c) @ n_hat
    return float(d.min()), float(d.max()), int(m.sum())


print("\n" + "=" * 92)
print(f"{'传入 t (nm)':>12} {'壳点数':>7} {'d_min(nm)':>11} {'d_max(nm)':>11} "
      f"{'厚度(nm)':>10}   与候选式对比")
for t_nm in (TAU_NM, ENG_T_NM):
    g.phi[:] = 1.0
    g.seed_plate(1, c, n_hat, ENG_R, t_nm * 1e-9, elong=1.0,
                 along=np.array([1.0, 0.0, 0.0]))
    lo, hi, nsh = phys_thickness(1)
    if lo is None:
        print(f"{t_nm:>12.1f} {nsh:>7} {'—':>11} {'—':>11} {'—':>10}  (壳点太少)")
        continue
    th = (hi - lo) * 1e9
    cands = {
        't': t_nm,
        't/2': t_nm / 2,
        't+2Δx': t_nm + 2 * DX * 1e9,
        't/2+2Δx': t_nm / 2 + 2 * DX * 1e9,
        't+Δx': t_nm + DX * 1e9,
    }
    best = min(cands.items(), key=lambda kv: abs(kv[1] - th))
    print(f"{t_nm:>12.1f} {nsh:>7} {lo*1e9:>11.1f} {hi*1e9:>11.1f} "
          f"{th:>10.1f}   ⇒ 最接近 **{best[0]} = {best[1]:.1f} nm**")

print("=" * 92)
print("★ 判读：")
print("  · 若厚度 ≈ `t`（未再除 2）⇒ 约定 = 't 是厚度'，而偏移里的 `Tj/2` **多除了一次**")
print("  · 若厚度 ≈ `t/2`       ⇒ 约定 = 't 是半厚'，而偏移里的 `Tj/2` **是对的**")
print(f"  · 参考：生产 `t_nuc = {TAU_NM:.1f} nm` ⇒ 两种约定分别给 "
      f"**{TAU_NM:.1f}** 与 **{TAU_NM/2:.1f} nm**（差 2 倍，**可分辨**）")