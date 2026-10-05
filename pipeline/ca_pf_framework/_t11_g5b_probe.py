#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_g5b_probe.py —— `G5b`（钝化）的**前置分辨力自检**（`R623 §7.2` 要求的）。

## 要回答的三个问题（每个都可 FAIL）
  Q1 `aniso_elastic` 路径（生产档）下，`elastic_driving()` 在**母相胞**上是否非零
     ⇒ 若非零，它在母相胞上就是 `ε⁰_p : σ_existing`，**正是 R-B 的相互作用能**
       （母相处 `φ_p = 0` ⇒ 无自作用）。
  Q2 **板条长大前后**，同一个母相胞上的 `ed` 是否**改变**
     ⇒ 这是 `G5b` 的**分辨力判据**（"该处应力是否被松弛"必须有可观测的变化）。
     ⚠ 负对照断言：**必须 ≠ 0**（`R581 P12`）。
  Q3 `σ` 场本身的可达性与量级（走 `AnisoElastic.sigma6`）。

## 做法
  同一网格造两个组态：**1 根板条** vs **2 根板条**（第二根远处），
  比较**同一批母相胞**上的 `ed`。
"""
import sys

import numpy as np

sys.path.insert(0, ".")
import windowB_surface as WS          # noqa: E402
import windowB_ti64_variants as V     # noqa: E402

N = 32
DX = 62.5e-9
L = N * DX

# 立方弹性张量（与 `T16_verify_rve.C` 同值 134/110/36 GPa）
c11, c12, c44 = 134e9, 110e9, 36e9
C = np.zeros((3, 3, 3, 3), float)
for i in range(3):
    for j in range(3):
        C[i, i, j, j] = c11 if i == j else c12
        if i != j:
            C[i, j, i, j] = c44
            C[i, j, j, i] = c44

strains, F, meta = V.variants()
NV = 4                                   # 小规模：只取 4 个变体
eps0 = [np.asarray(strains[v], float) for v in range(NV)]


def build(n_plates, aniso):
    """n_plates = 1 或 2；aniso 决定走逐变体模量路径还是 PF3D 路径。"""
    g = WS.LevelSetMulti(N, L, C=C, eps0=eps0, nv=NV,
                         gamma=0.0, Mob=1.0, aniso_elastic=aniso)
    g.phi[:] = 1e3
    g.phi[0] = -1e3
    g.init_parent()
    ctr1 = np.array([L * 0.25, L * 0.5, L * 0.5])
    g.seed_plate(1, ctr1, np.array([0.0, 0.0, 1.0]), 3 * DX, 2 * DX)
    if n_plates >= 2:
        ctr2 = np.array([L * 0.75, L * 0.5, L * 0.5])
        g.seed_plate(2, ctr2, np.array([0.0, 0.0, 1.0]), 3 * DX, 2 * DX)
    return g


print("=" * 96)
print(f"N={N}  dx={DX*1e9:.1f} nm  L={L*1e6:.2f} µm  nv={NV}")
print("=" * 96)

for aniso in (True, False):
    tag = 'aniso_elastic=True（★生产档）' if aniso else 'aniso_elastic=False（PF3D 档）'
    print(f"\n──────── {tag} ────────")
    try:
        g1 = build(1, aniso)
        g2 = build(2, aniso)
        ed1 = g1.elastic_driving()
        ed2 = g2.elastic_driving()
    except Exception as exc:
        print(f"  **无法构造/求解**：{type(exc).__name__}: {exc}")
        continue
    reg = g1.region()
    par = (reg == 0)
    print(f"  ed 形状={ed1.shape}  母相胞数={int(par.sum())}")
    # Q1：母相胞上是否非零
    for v in range(1, NV + 1):
        vals = ed1[v][par]
        print(f"   变体 {v}：母相胞上 ed  min={vals.min():+.4e}  max={vals.max():+.4e} "
              f" mean={vals.mean():+.4e}  非零占比={float((vals != 0).mean()):.3f}")
    # Q2：1 根 vs 2 根，同一批母相胞上的差异（只在两组的**共同**母相胞上比）
    reg2 = g2.region()
    par2 = (reg2 == 0)
    both = par & par2
    print(f"  两组共同母相胞数 = {int(both.sum())}")
    if int(both.sum()) == 0:
        print("  ⇒ **无法比较**（没有共同母相胞）—— 本探针作废，需换几何")
        continue
    for v in range(1, NV + 1):
        d = np.abs(ed2[v][both] - ed1[v][both])
        den = max(float(np.abs(ed1[v][both]).max()), 1e-300)
        print(f"   变体 {v}：|Δed|  max={d.max():.4e}  mean={d.mean():.4e}"
              f"  相对={d.max()/den:.3e}")
    dmax = max(float(np.abs(ed2[v][both] - ed1[v][both]).max())
               for v in range(1, NV + 1))
    print(f"  ★ Q2 判定：max|Δed| = {dmax:.6e}")
    print(f"     ⇒ {'**有分辨力** ✅（板条数变化 ⇒ 母相胞上的 ed 变化）' if dmax > 0 else '**无分辨力** ❌（ed 不随已有板条改变 ⇒ G5b 无从实现）'}")
