#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_normwhy.py --- ★★★ 机理：**法向噪声如何压缩 `M(n)` 的各向异性**

问题（第 2 轮筛出来的唯一有效杠杆）
-----------------------------------
同 Δx、同种子、只改 `norm_smooth`（对 `∇d` 做盒式平滑再归一化）：
    0  →  ΔL:ΔW:ΔT = 1 : 0.625 : 0.194   （设计 1 : 0.100 : 0.030）✗
    2  →  ΔL:ΔW:ΔT = 1 : 0.145 : 0.032   ✓
**为什么？** 本脚本给两条独立证据。

判据（先写死）
--------------
  N-1 **解析敏感度**：`M(n)=M0·exp[−β_h(n·n*)²−β_w(n·w)²]` 在慢方向（`n*`、`w`）上
      **极小**，而极小点**就在设计轴上** ⇒ 任何法向角误差都**单边抬高**慢方向的 M。
      给出 `M(δ)/M(0)` 对 δ 的表，以及 `M(尖端)/M(宽面)` 这个"有效各向异性比"随 δ 的塌缩。
  N-2 **实测法向散布**：在**真实演化态**上量
        `n_raw = ∇d/|∇d|`  与  `n_sm = smooth3(∇d)/|smooth3(∇d)|`
      的角偏差分布，以及两者给出的
        `M̄(尖端族)` / `M̄(侧面族)` / `M̄(宽面族)`  与  **有效各向异性比**。
  N-3 **判定**：若 `norm_smooth=2` 让 `M̄(宽面)/M̄(尖端)` 显著下降（各向异性恢复）
      且 `M̄` 的三族对比向设计值靠拢 ⇒ 机理确认。

用法：python3 _r1_normwhy.py --N 96 --dx-nm 250 --seed-scale 2 --steps 120
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np                                              # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=96)
ap.add_argument('--dx-nm', type=float, default=250.0)
ap.add_argument('--seed-scale', type=float, default=2.0)
ap.add_argument('--steps', type=int, default=120)
ap.add_argument('--bh', type=float, default=3.5)
ap.add_argument('--bw', type=float, default=2.3)
ap.add_argument('--th', type=int, default=2)
ap.add_argument('--state', default='_r1_normwhy_state.npz',
                help='演化态缓存（存在则直接加载，跳过时间步进）')
a = ap.parse_args()
dx = a.dx_nm * 1e-9

print('=' * 100)
print('_r1_normwhy   N=%d Δx=%.1f nm  β_h=%.1f β_w=%.1f  设计比 1 : %.3f : %.3f'
      % (a.N, a.dx_nm, a.bh, a.bw, np.exp(-a.bw), np.exp(-a.bh)))
print('=' * 100, flush=True)

# ============================================================================
# N-1 **解析敏感度**：法向角误差如何单边抬高慢方向的 M
# ============================================================================
print('\n【N-1 解析敏感度】法向偏差 δ（绕"最陡方向"）对 M/M0 的抬升')
print('  记号：尖端 n=a（理想 M=1）；侧面 n=w（理想 %.3f）；宽面 n=n*（理想 %.3f）'
      % (np.exp(-a.bw), np.exp(-a.bh)))
print('  %6s | %10s %10s %10s | %12s %10s' %
      ('δ(°)', 'M_尖/M0', 'M_侧/M0', 'M_宽/M0', 'M_尖/M_宽', '相对33.3'))
ideal_ratio = 1.0 / np.exp(-a.bh)
for d in (0, 2, 5, 10, 15, 20, 25, 30):
    t = np.radians(d)
    # 尖端：n 从 a 偏 δ（朝 n*）⇒ n·n* = sinδ ；侧面：n 从 w 偏 δ（朝 a）⇒ n·w=cosδ
    Mt = np.exp(-a.bh * np.sin(t) ** 2 - a.bw * 0.0)
    Ms = np.exp(-a.bh * 0.0 - a.bw * np.cos(t) ** 2)
    # 宽面：n 从 n* 偏 δ（朝 a）⇒ n·n*=cosδ
    Mf = np.exp(-a.bh * np.cos(t) ** 2 - a.bw * 0.0)
    print('  %6.1f | %10.4f %10.4f %10.4f | %12.2f %9.2fx'
          % (d, Mt, Ms, Mf, Mt / Mf, (Mt / Mf) / ideal_ratio))
print('  ⇒ **慢方向的 M 是"谷底"，噪声只会把它抬高**（单边）');
print('     所以测到的"有效各向异性比"**必然低于设计**，且随法向噪声单调塌缩。')

# ============================================================================
# N-2 实测：真实演化态上的法向散布
# ============================================================================
print('\n【N-2 实测】在真实演化态上量 `n_raw` vs `n_sm`（norm_smooth=2）', flush=True)
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF, DF, MOB            # noqa: E402
from _r1_exp import SHAPES, axes_of, seed_one                   # noqa: E402

L = a.N * dx
K = 1
_CACHE = os.path.join(HERE, a.state)
n_hab = None
if os.path.exists(_CACHE):
    z = np.load(_CACHE)
    phi_saved = z['phi']
    n_hab, w_ax, a_ax = (z['n_hab'], z['w_ax'], z['a_ax'])
    print('  ★ 从缓存加载演化态 %s（跳过时间步进）' % _CACHE, flush=True)
    g = W.LevelSetMulti(a.N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=1, reinit_every=0,
                        reinit_dt=None, reinit_band_cells=6.0)
    g.phi = phi_saved
else:
    g = W.LevelSetMulti(a.N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=a.th, reinit_every=0,
                        reinit_dt=None, reinit_band_cells=6.0)
    n_hab, w_ax, a_ax = axes_of(g, K)
    shape = dict(SHAPES['mid'])
    if a.seed_scale != 1.0:
        for kk in ('L', 'W', 'T', 'R'):
            if kk in shape:
                shape[kk] = shape[kk] * a.seed_scale
    seed_one(g, K, shape, np.array([L / 2] * 3), a_ax, n_hab)
    g.init_parent()
    print('  种子 %s（L/W/T = %.0f/%.0f/%.0f nm）⇒ %.1f/%.1f/%.1f 胞'
          % (shape, shape['L'], shape['W'], shape['T'],
             shape['L'] / a.dx_nm, shape['W'] / a.dx_nm, shape['T'] / a.dx_nm),
          flush=True)
    dt = 0.15 * dx / (MOB * DF)
    KW = dict(aniso=0.4, npref=NPF, band_cells=20, mob_beta=a.bh, mob_beta_w=a.bw,
              adv_grad='proj2', norm_smooth=0)
    for it in range(1, a.steps + 1):
        g._t_since_reinit = 0.0
        g.advance(dt, **KW)
    np.savez_compressed(_CACHE, phi=g.phi, n_hab=n_hab, w_ax=w_ax, a_ax=a_ax)
    print('  已推进 %d 步（norm_smooth=0，与基线臂一致）；演化态已缓存到 %s'
          % (a.steps, _CACHE), flush=True)

reg = g.region()
karr = np.argmin(g.phi, axis=0)
order = np.argsort(g.phi, axis=0)
larr = order[1]
# ★ 记账：`g.phi[karr]` 是**花式索引**，在 (nreg,N,N,N) 上会广播成 (N,N,N,N,N,N)
#   —— 我第一版就写成那样，numpy 报 "Unable to allocate 5.70 TiB"。
d = (np.take_along_axis(g.phi, karr[None], 0)[0]
     - np.take_along_axis(g.phi, larr[None], 0)[0])
gd = np.gradient(d, dx, edge_order=2)
gdn = np.sqrt(sum(x ** 2 for x in gd))
band = (np.abs(d) <= 1.5 * dx) & (gdn > 1e-9)
print('  带内（|d|≤1.5dx）胞数 = %d ；`|∇d|` 中位 = %.4f（应 ≈2，因为 d=φ_k−φ_l）'
      % (int(band.sum()), float(np.median(gdn[band]))), flush=True)


def smooth3(f, m):
    k = np.ones(2 * m + 1) / (2 * m + 1)
    for ax in range(3):
        f = np.apply_along_axis(lambda v: np.convolve(v, k, mode='same'), ax, f)
    return f


def normals(gd_, m=0):
    if m > 0:
        gd_ = [smooth3(x, m) for x in gd_]
    n = np.stack([x[band] for x in gd_], 1)
    nn = np.linalg.norm(n, axis=1, keepdims=True) + 1e-300
    return n / nn


def mfac(nv):
    return np.exp(-a.bh * (nv @ n_hab) ** 2 - a.bw * (nv @ w_ax) ** 2)


res = {}
for m in (0, 1, 2, 4):
    nv = normals(gd, m)
    mf = mfac(nv)
    ca, cw, cn = np.abs(nv @ a_ax), np.abs(nv @ w_ax), np.abs(nv @ n_hab)
    sel = np.argmax(np.stack([ca, cw, cn], 0), axis=0)
    res[m] = dict(
        mtip=float(mf[sel == 0].mean()) if (sel == 0).sum() > 0 else float('nan'),
        mside=float(mf[sel == 1].mean()) if (sel == 1).sum() > 0 else float('nan'),
        mface=float(mf[sel == 2].mean()) if (sel == 2).sum() > 0 else float('nan'),
        mall=float(mf.mean()),
        f_a=float((sel == 0).mean()), f_w=float((sel == 1).mean()),
        f_n=float((sel == 2).mean()),
    )

print('\n  %-6s %10s %10s %10s %10s | %14s %10s' %
      ('平滑 m', 'M̄尖端', 'M̄侧面', 'M̄宽面', 'M̄全体', 'M̄尖/M̄宽', '相对设计'))
for m in sorted(res):
    r = res[m]
    ratio = r['mtip'] / max(r['mface'], 1e-30)
    print('  %-6d %10.4f %10.4f %10.4f %10.4f | %14.2f %9.2fx'
          % (m, r['mtip'], r['mside'], r['mface'], r['mall'], ratio,
             ratio / ideal_ratio))
print('\n  面族占比（按**法向最接近哪条轴**分族）：')
for m in sorted(res):
    r = res[m]
    print('    m=%d  |n·a|最大 %.1f%%   |n·w|最大 %.1f%%   |n·n*|最大 %.1f%%'
          % (m, 100 * r['f_a'], 100 * r['f_w'], 100 * r['f_n']))

print('\n' + '=' * 100)
print('N-3 判定：看 `M̄尖/M̄宽` 这一列 —— 设计值 %.2f；' % ideal_ratio)
print('  若它在 m=0 时**远低于**设计、随 m 上升而**回升** ⇒ 机理确认（法向噪声压缩各向异性）。')
print('  若 m=0 与 m=2 差别不大 ⇒ 机理否证，另找原因。')
print('=' * 100)
