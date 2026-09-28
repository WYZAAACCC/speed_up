#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_thick_dx.py --- ★ 增厚速率的 **Δx 收敛**（`MEASUREMENT_SPEC R5`）

为什么要做
---------
`_proto_nucleate.py` 的 `nuc=off` 档（N=64/Δx=50 nm/t_seed=200 nm/60 步）实测
沿 `n*` 的方向尺度 **中位 275 nm**（种子 200 nm）⇒ **+37%**，
而解析预算只有 `60 步 × 0.226 nm/步 = 13.6 nm`（+6.8%）⇒ **实测快 5.5 倍**。

两个候选解释（必须先分开，否则形貌结论不可用）：
  * **H1 离散伪影**：`t/Δx = 4` 时"宽面"的法向在胞尺度上有 ±30° 级散布，
    而 `M(n)=M0exp[−β_h(n·n*)²]` 对法向误差**极敏感** ⇒ 有效迁移率被抬高
    （`exp[−3.5cos²30°]/exp[−3.5] = 2.4×`）。⇒ **加密后应回落到解析值**。
  * **H2 真实的多驱动**：`ed_k` 在界面处叠加（T1 实测 `ed` 可达 1.4e8，与 `Δf=3.5e8` 同量级）
    ⇒ 有效驱动 > `Δf` ⇒ 增厚本来就快。⇒ **加密后不变**。

判据
----
  D-1 **固定物理时间**：`dt = 0.15Δx/(M0Δf)` ⇒ `Δx` 减半则步数加倍
      （Δx=50 nm/60 步 ⇔ Δx=25 nm/120 步）—— 不这样做就是在比不同时刻。
  D-2 **增厚量** `Δt = t_extent(末) − t_seed`：两档之差 < 30% ⇒ H2（可用）；
      Δx=25 档明显更小且趋向解析 13.6 nm ⇒ H1（**当前规格的形貌是网格伪影**）。
  D-3 量具正对照（`MEASUREMENT_SPEC R0`）：合成平板必须复现已知 t（±5%）。
  D-4 健康度：`|∇φ|` 带内中位应 ≈1。

用法：python3 _probe_thick_dx.py
"""
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF, R_SEED, T_SEED      # noqa: E402
from T24_verify_grouping import connected_components             # noqa: E402

MOB = 1e-9
DF = 3.5e8
L = 3.2e-6
N0 = 8


def thickness_along_normal(reg, NPF, dx, k, min_cells=8):
    """沿变体 `k` 的惯习面法向 `n*_k` 的方向尺度（平板 ⇒ = 厚度）。

    ⚠ 记账：多核 RVE 里**同变体**的分量会**面内**合并 ⇒ 合并**不改变** `n*` 方向展宽
      （所有同变体分量的宽面都 ⊥ `n*_k`），故本量具对"面内合并"稳健；
      但若两组分的 `n*` 一致而位置沿 `n*` 错开，展宽会偏大 ⇒ 只能当**上界**。"""
    m = (reg == k)
    if m.sum() < min_cells:
        return np.nan
    lab, n = connected_components(m)
    if n == 0:
        return np.nan
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    comp = (lab == int(np.argmax(sizes)))
    idx = np.argwhere(comp).astype(float)
    proj = idx @ np.asarray(NPF[k], float)
    return float(proj.max() - proj.min() + 1.0) * dx


def control_thickness(dx=25e-9, Lc=2.4e-6):
    """R0 正对照：合成平板，已知 t。"""
    N = int(round(Lc / dx))
    print('  【D-3 正对照】厚度量具在已知 t 的合成板条上：')
    rows = []
    for R_nm, t_nm in ((300, 200), (600, 300), (900, 300), (600, 700)):
        g = W.LevelSetMulti(N, Lc, C=None, eps0=None, nv=1, gamma=0.15, Mob=MOB,
                            df=[0.0, 1e8], workers=1, reinit_every=0)
        n0 = np.array([0.0, 0.0, 1.0])
        g.seed_plate(1, np.array([Lc / 2] * 3), n0, R_nm * 1e-9, t_nm * 1e-9)
        g.init_parent()
        got = thickness_along_normal(g.region(), {1: n0}, dx, 1)
        rows.append(abs(got / (t_nm * 1e-9) - 1.0))
        print('     R=%4d t=%3d ⇒ 量具 %.1f nm（偏差 %+.1f%%）'
              % (R_nm, t_nm, got * 1e9, (got / (t_nm * 1e-9) - 1) * 100))
    worst = max(rows)
    print('     ⇒ 最大偏差 %.1f%% ⇒ %s' % (worst * 100, 'PASS' if worst < 0.05 else 'FAIL'))
    return worst < 0.05


def run(dx, steps):
    N = int(round(L / dx))
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)
    rng = np.random.default_rng(7)
    ns = 0
    while ns < N0:
        c = rng.random(3) * (L - 2 * (R_SEED + 0.3e-6)) + (R_SEED + 0.3e-6)
        k = int(rng.integers(1, NV + 1))
        nv = np.asarray(NPF[k], float)
        try:
            g.seed_plate(k, c, nv / np.linalg.norm(nv), R_SEED, T_SEED)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    reg0 = g.region()
    t0 = [thickness_along_normal(reg0, NPF, dx, k) for k in np.unique(reg0) if k > 0]
    t0 = float(np.nanmedian(t0)) if t0 else np.nan
    dt = 0.15 * dx / (MOB * DF)
    _t = time.time()
    for it in range(1, steps + 1):
        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                  mob_beta=3.5, mob_beta_w=2.3, adv_grad='proj2')
        if it % max(20, steps // 3) == 0:
            print('     [心跳 dx=%.0f nm] step=%-4d 步时=%.1f s 已用=%.1f min'
                  % (dx * 1e9, it, (time.time() - _t) / it, (time.time() - _t) / 60), flush=True)
    reg = g.region()
    th = [thickness_along_normal(reg, NPF, dx, k) for k in np.unique(reg) if k > 0]
    th = np.array([v for v in th if np.isfinite(v)], float)
    f = 1.0 - float((reg == 0).sum()) / g.N ** 3
    # 健康度：带内 |grad phi| 中位（proj2 应 ≈1）
    gd = np.gradient(g.phi[1], dx, edge_order=2)
    gn = np.sqrt(sum(t ** 2 for t in gd))
    band = np.abs(g.phi[1]) <= 2 * dx
    return dict(t0=t0, tmed=float(np.median(th)), tmax=float(th.max()),
                n=th.size, f=f, steps=steps, dx=dx,
                gmed=float(np.median(gn[band])) if band.any() else np.nan,
                tphys=steps * dt)


print('=' * 100)
print('_probe_thick_dx —— 增厚速率的 Δx 收敛（固定**物理时间**）')
print('=' * 100)
ok3 = control_thickness()
res = {}
for dx_nm, steps in ((50.0, 60), (25.0, 120)):
    dx = dx_nm * 1e-9
    print('\n---- Δx=%.0f nm（N=%d）steps=%d ----' % (dx_nm, int(round(L / dx)), steps))
    r = run(dx, steps)
    res[dx_nm] = r
    print('   种子态厚度中位 = %.1f nm（真值 %.0f）' % (r['t0'] * 1e9, T_SEED * 1e9))
    print('   末态 f=%.4f  物理时间=%.3e s' % (r['f'], r['tphys']))
    print('   厚度：中位 %.1f nm（+%.1f nm）  max %.1f nm  n=%d  带内|∇φ|中位=%.3f'
          % (r['tmed'] * 1e9, (r['tmed'] - r['t0']) * 1e9, r['tmax'] * 1e9, r['n'], r['gmed']))

dt50 = (res[50.0]['tmed'] - res[50.0]['t0']) * 1e9
dt25 = (res[25.0]['tmed'] - res[25.0]['t0']) * 1e9
pred = res[50.0]['steps'] * MOB * DF * np.exp(-3.5) * (0.15 * 50e-9 / (MOB * DF)) * 1e9
print('\n' + '=' * 100)
print('【判读】')
print('  D-3 厚度量具正对照：%s' % ('PASS' if ok3 else 'FAIL'))
print('  解析预算（同一物理时间）：宽面 %.2f nm/步 × %d 步 = **%.1f nm**'
      % (MOB * DF * np.exp(-3.5) * (0.15 * 50e-9 / (MOB * DF)) * 1e9,
         res[50.0]['steps'], pred))
print('  D-1 实测增厚：Δx=50 nm ⇒ **+%.1f nm** ； Δx=25 nm ⇒ **+%.1f nm**' % (dt50, dt25))
d = abs(dt50 - dt25) / max(abs(dt50), 1e-30)
if d < 0.30:
    print('  D-2 两档之差 %.0f%% < 30%% ⇒ **H2（真实多驱动，加密不变）** ⇒ 现有形貌可用' % (d * 100))
elif dt25 < dt50 * 0.7:
    print('  D-2 Δx=25 档显著更小（%.0f%%）且更靠近解析 %.1f nm ⇒ **H1（离散伪影）**'
          % ((1 - dt25 / max(dt50, 1e-30)) * 100, pred))
    print('      ⇒ ⚠ **当前规格下"板条厚"的读数含网格伪影**，须以 Δx=25 nm 档为准')
else:
    print('  D-2 方向反常（Δx=25 反而更大）⇒ INCONCLUSIVE，须查量具')
print('  D-4 健康度 带内|∇φ| 中位：%.3f / %.3f（应 ≈1）'
      % (res[50.0]['gmed'], res[25.0]['gmed']))
print('=' * 100)
