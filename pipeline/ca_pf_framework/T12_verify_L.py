#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T12_verify_L.py --- T12-D12b：**`L → 1.5L` 的统计稳定性**（决定 L 够不够）。

设计（单变量：只改盒子尺寸）
--------------------------
  Δx = 50 nm 固定；`L = 3.2 µm (N=64)` vs `L = 4.8 µm (N=96)`（= 1.5×）
  * **种子的数密度相同**（`n_seed = ρ·L³`，ρ 固定）⇒ 体相统计可比
  * **种子的绝对尺寸相同**（物理量不随盒子缩放）
  * 同一物理时间（同 `dt`、同步数）；重初始化用 **`reinit_dt`（物理时间）**
    而不是步数（T11 的改动，否则换 L 会改变重初始化频率）

判据：**强度量**（与体积无关）在 `L → 1.5L` 下的相对变化 **< 10%**
  `f` 转变量分数 · `Sv` 单位体积界面面积 · `N_var` 出现的变体数 ·
  **`M6p` 变体-母相界面法向 vs `npref[k]` 的中位角**（仓库既有口径）
  （⚠ `M6p` 单独列：它的中位数在"宽面占比 <50%"时会被非宽面污染，见
   `_chk_morph_full.py:124` 的记账 —— 所以同时报 p25）

用法：python3 T12_verify_L.py [--dx-nm 50] [--steps 250]
退出码：0 = PASS
"""
import os
import sys
import time
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
_rng = np.random.default_rng(0)
NPF = {}
for v in range(NV):
    best, bn = None, None
    for n in _rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v], _lam_full(C, n), EPS0[v]))
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn

DF, MOB = 2.0e8, 1e-9
RHO = 24.0 / (3.2e-6) ** 3          # 基准：3.2 µm 盒里 24 个核
R_SEED, T_SEED = 0.40e-6, 1.0e-7


def stats(g):
    reg = g.region()
    V = g.L ** 3
    f = 1.0 - float((reg == 0).sum()) / g.N ** 3
    Sv = float(g.cell_area_geom().sum()) / V
    nvar = int(sum(1 for k in range(1, g.nreg)
                   if float((reg == k).sum()) / g.N ** 3 > 0.005))
    # --- M6p：变体-母相界面法向 vs npref[k] ---
    A = []
    for k in range(1, g.nreg):
        mk = (reg == k)
        if not mk.any() or NPF.get(k) is None:
            continue
        nb = np.zeros(mk.shape, bool)
        for ax in range(3):
            nb |= (np.roll(reg, 1, axis=ax) == 0)
        iface = mk & nb
        if iface.sum() < 10:
            continue
        gg = np.gradient(g.phi[k], g.dx, edge_order=2)
        gn = np.sqrt(sum(t ** 2 for t in gg)) + 1e-30
        nrm = np.stack([t / gn for t in gg], -1)[iface]
        nd = np.asarray(NPF[k], float)
        nd = nd / np.linalg.norm(nd)
        A.append(np.degrees(np.arccos(np.clip(np.abs(nrm @ nd), 0, 1))))
    A = np.concatenate(A) if A else np.array([np.nan])
    # 随机对照
    rng = np.random.default_rng(0)
    R_ = []
    for k in range(1, g.nreg):
        if NPF.get(k) is None:
            continue
        vv = rng.normal(size=(2000, 3))
        vv /= np.linalg.norm(vv, axis=1)[:, None]
        nd = np.asarray(NPF[k], float)
        nd = nd / np.linalg.norm(nd)
        R_.append(np.degrees(np.arccos(np.clip(np.abs(vv @ nd), 0, 1))))
    R_ = np.concatenate(R_) if R_ else np.array([np.nan])
    return dict(f=f, Sv=Sv, nvar=nvar,
                M6p_med=float(np.nanmedian(A)), M6p_p25=float(np.nanpercentile(A, 25)),
                M6p_rnd=float(np.nanmedian(R_)), n_iface=int(A.size))


def run(L, dx, steps):
    N = int(round(L / dx))
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)          # ★ 物理时间重初始化（T11）
    rng = np.random.default_rng(7)
    nseed = int(round(RHO * L ** 3))
    ns = 0
    for _ in range(nseed * 6):
        if ns >= nseed:
            break
        c = rng.random(3) * (L - 2 * (R_SEED + 0.3e-6)) + (R_SEED + 0.3e-6)
        try:
            g.seed_plate(int(rng.integers(1, NV + 1)), c, NPF[1], R_SEED, T_SEED)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF)
    for _ in range(steps):
        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
    s = stats(g)
    s['nseed'] = ns
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dx-nm', type=float, default=50.0)
    ap.add_argument('--steps', type=int, default=250)
    a = ap.parse_args()
    dx = a.dx_nm * 1e-9
    print('=' * 100)
    print('T12-D12b —— L → 1.5L 的统计稳定性   Δx=%.0f nm  steps=%d' % (a.dx_nm, a.steps))
    print('=' * 100)
    res = {}
    for L in (3.2e-6, 4.8e-6):
        t0 = time.time()
        s = run(L, dx, a.steps)
        res[L] = s
        print('  L=%.1f µm (N=%-3d, 种核 %d)：f=%.4f  Sv=%.3e 1/m  N_var=%d  '
              'M6p 中位=%.1f° p25=%.1f°（随机 %.1f°）  界面点 %d  (%.0f s)'
              % (L * 1e6, int(round(L / dx)), s['nseed'], s['f'], s['Sv'], s['nvar'],
                 s['M6p_med'], s['M6p_p25'], s['M6p_rnd'], s['n_iface'],
                 time.time() - t0), flush=True)
    s1, s2 = res[3.2e-6], res[4.8e-6]
    print()
    print('  %-12s %-14s %-14s %-10s %s' % ('量', 'L=3.2', 'L=4.8', '相对变化', '判定'))
    okall = True
    for key, lab, thr in (('f', 'f 转变量分数', 0.10),
                          ('Sv', 'Sv 界面面积/体积', 0.10),
                          ('nvar', 'N_var 变体数', 0.10),
                          ('M6p_p25', 'M6p p25（宽面口径）', 0.10)):
        v1, v2 = s1[key], s2[key]
        rel = abs(v2 - v1) / max(abs(0.5 * (v1 + v2)), 1e-30)
        good = rel < thr
        okall &= good
        print('  %-12s %-14.5g %-14.5g %-10.2f%% %s'
              % (lab, v1, v2, 100 * rel, 'OK' if good else '✗'))
    print()
    print('  ★ 记账：`M6p 中位`单列 —— 它的中位数在"宽面占比 <50%%"时会被非宽面污染')
    print('    （`_chk_morph_full.py:124`），所以判据用 **p25**，中位只作对照：')
    print('    M6p 中位 %.1f° vs %.1f°（相对变化 %.1f%%）'
          % (s1['M6p_med'], s2['M6p_med'],
             100 * abs(s2['M6p_med'] - s1['M6p_med']) / max(0.5 * (s1['M6p_med'] + s2['M6p_med']), 1e-30)))
    print('    随机对照 %.1f°（两档同值，是几何量）' % s1['M6p_rnd'])
    print()
    print('=' * 100)
    print('  ⇒ T12-D12b %s（判据：四个强度量的相对变化都 < 10%%）'
          % ('PASS' if okall else 'FAIL'))
    print('=' * 100)
    return 0 if okall else 1


if __name__ == '__main__':
    sys.exit(main())
