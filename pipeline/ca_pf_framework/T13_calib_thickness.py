#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T13_calib_thickness.py --- **厚度估计量的正对照**（先验证量具，再量东西）。

背景（本轮教训 #4）
------------------
T13-A 用 `t_est = 2f/Sv` 当"板条厚度"，三档 `N_v` 给出**反向**趋势。
但那可能是**量具坏**（估计量与 `f` 混杂、各向异性未长开），不是物理。
⇒ 按本项目教训 #19：**先拿"已知答案"跑通量具，再相信它对未知答案的读数。**

正对照构造
----------
用 `seed_plate(k, c, n, R, t)` 造**厚度 `t` 已知**的板条（`R` 为面内半径）：
  * `R/t = 10` ⇒ 边缘可忽略 ⇒ `2f/Sv` **应当精确等于 `t`**（纯几何恒等式）
  * `R/t = 5, 2.5` ⇒ 边缘占比增大 ⇒ 看偏差怎么长
负对照：**球**（`t` 无意义）⇒ `2f/Sv` 应给出 ≈ 直径（球：f=4πR³/3L³, Sv=4πR²/L³ ⇒ 2f/Sv = 2R/3 ≠ 2R）
  ⇒ 说明 `2f/Sv` **只对薄板有效**，对等轴形状无效。

同时算 **变体标记相关长度** `r_c^var`（D12c 里实测 0.285 µm ≈ 板条厚）作为候选量具。

用法：python3 T13_calib_thickness.py
退出码：0 = 至少一个量具通过正对照
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402

L = 2.4e-6
DX = 25e-9
N = int(round(L / DX))


def corr_1e(chi, dx):
    x = chi.astype(np.float64)
    f = x.mean()
    y = x - f
    F = np.fft.fftn(y)
    ac = np.real(np.fft.ifftn(F * np.conj(F))) / x.size
    ac = np.fft.fftshift(ac)
    ctr = np.array(ac.shape) // 2
    zz, yy, xx = np.indices(ac.shape)
    rr = np.sqrt((xx - ctr[2]) ** 2 + (yy - ctr[1]) ** 2 + (zz - ctr[0]) ** 2)
    nb = int(min(ac.shape) // 2)
    prof = np.array([ac[(rr >= i) & (rr < i + 1)].mean() if ((rr >= i) & (rr < i + 1)).any()
                     else np.nan for i in range(nb)])
    c0 = prof[0]
    if not np.isfinite(c0) or c0 <= 0:
        return np.nan
    idx = np.where(prof <= c0 / np.e)[0]
    if idx.size == 0:
        return np.nan
    i = int(idx[0])
    if i == 0:
        return 0.0
    t = (prof[i - 1] - c0 / np.e) / max(prof[i - 1] - prof[i], 1e-300)
    return float((i - 1 + t) * dx)


def var_mark_corr(reg, nv, dx):
    tot, cnt = None, 0
    for k in range(1, nv + 1):
        chi = (reg == k)
        if chi.sum() < 8:
            continue
        rc = corr_1e(chi, dx)
        if not np.isfinite(rc):
            continue
        tot = rc if tot is None else tot + rc
        cnt += 1
    return tot / cnt if cnt else np.nan


def build(shape, R, t):
    g = W.LevelSetMulti(N, L, C=None, eps0=None, nv=1, gamma=0.15, Mob=1e-9,
                        df=[0.0, 1e8], workers=1, reinit_every=0)
    c0 = np.array([L / 2] * 3)
    if shape == 'plate':
        g.seed_plate(1, c0, np.array([0.0, 0.0, 1.0]), R, t)
    else:
        g.seed_sphere(1, c0, R)
    g.init_parent()
    reg = g.region()
    f = float((reg == 1).sum()) / g.N ** 3
    Sv = float(g.cell_area_geom().sum()) / L ** 3
    return 2.0 * f / max(Sv, 1e-30), var_mark_corr(reg, 1, DX), f, Sv


print('=' * 100)
print('厚度估计量正对照   L=%.1f µm  Δx=%.0f nm  N=%d' % (L * 1e6, DX * 1e9, N))
print('=' * 100)
print('%-26s %-12s %-14s %-14s %s' %
      ('构型', '已知 t (nm)', 'E1=2f/Sv (nm)', 'E1/已知', 'E2=r_c^var (nm)'))
okE1 = []
for R_nm, t_nm in ((600, 60), (600, 120), (600, 240), (300, 60), (150, 60)):
    e1, e2, f, Sv = build('plate', R_nm * 1e-9, t_nm * 1e-9)
    ratio = e1 / (t_nm * 1e-9)
    okE1.append(ratio)
    print('%-26s %-12.0f %-14.1f %-14.3f %.1f'
          % ('板条 R=%d t=%d (R/t=%.1f)' % (R_nm, t_nm, R_nm / t_nm),
             t_nm, e1 * 1e9, ratio, e2 * 1e9))
print()
print('负对照：等轴形状（球）——`2f/Sv` **不应**等于直径，说明它只对薄板有效')
for R_nm in (200, 300):
    e1, e2, f, Sv = build('sphere', R_nm * 1e-9, 0)
    print('%-26s %-12.0f %-14.1f %-14.3f %.1f'
          % ('球 R=%d（直径 %d）' % (R_nm, 2 * R_nm), 2 * R_nm, e1 * 1e9, e1 / (2 * R_nm * 1e-9),
             e2 * 1e9))
print()
r = np.array(okE1)
good = (np.abs(r - 1.0) < 0.15).sum()
print('⇒ E1（2f/Sv）在 5 个薄板档里，比值落在 [0.85,1.15] 的有 **%d/5**' % good)
print('  E1 是否可用作"板条厚度"量具: %s' % ('**可用**' if good >= 4 else '**不可用**'))
print('=' * 100)
