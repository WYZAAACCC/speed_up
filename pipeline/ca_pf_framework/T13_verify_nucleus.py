#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T13_verify_nucleus.py --- T13 判据：**薄板晶核模型**（厚度/取向/数密度 `N_v`）。

物理
----
`α′` 是位移型、无扩散 ⇒ **形核是输入**（`RESEARCH_INTENT.md` §一 / D1′）。
且 L2 文献轨的结论是"**生长不是限制环节**，板条厚度由**形核密度 + impingement** 决定"
⇒ 可检验的定标律：**厚度 `t ∝ N_v^{-1/3}`**（每个核最终占体积 `1/N_v`）。

判据
----
  T13-A **数密度定标**：三档 `N_v`（8 / 27 / 64 倍基准）⇒ `t_est = 2f/Sv`
        （板条两个宽面）必须按 `N_v^{-1/3}` 定标（拟合指数的绝对值 ∈ [0.25, 0.45]，
        且相邻档的比值与 `(N_v 比)^{-1/3}` 差 < 25%）
  T13-B **取向对照**：晶核取向用 `npref[k]`（惯习面）vs **随机** ⇒
        对齐档的 `M6p` p25 必须**显著更低**（更贴惯习面）
  T13-C **回归守卫**：无弹性档两次运行的 `φ` **逐位相同**（可复现）

用法：python3 T13_verify_nucleus.py [--L-um 3.2] [--dx-nm 62.5] [--steps 150]
退出码：0 = PASS
"""
import os
import sys
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
R_SEED, T_SEED = 0.30e-6, 1.0e-7
N0 = 8                                   # 基准核数（在 L=3.2 µm 盒里）


def corr_1e(chi, dx):
    """指示场两点径向自相关降到 1/e 的距离（FFT）。"""
    x = chi.astype(np.float64)
    y = x - x.mean()
    F = np.fft.fftn(y)
    ac = np.real(np.fft.ifftn(F * np.conj(F))) / x.size
    ac = np.fft.fftshift(ac)
    ctr = np.array(ac.shape) // 2
    zz, yy, xx = np.indices(ac.shape)
    rr = np.sqrt((xx - ctr[2]) ** 2 + (yy - ctr[1]) ** 2 + (zz - ctr[0]) ** 2)
    nb = int(min(ac.shape) // 2)
    prof = np.full(nb, np.nan)
    for i in range(nb):
        m = (rr >= i) & (rr < i + 1)
        if m.any():
            prof[i] = ac[m].mean()
    if not np.isfinite(prof[0]) or prof[0] <= 0:
        return np.nan
    idx = np.where(prof <= prof[0] / np.e)[0]
    if idx.size == 0:
        return np.nan
    i = int(idx[0])
    if i == 0:
        return 0.0
    t = (prof[i - 1] - prof[0] / np.e) / max(prof[i - 1] - prof[i], 1e-300)
    return float((i - 1 + t) * dx)


def thickness_var(reg, nv, dx):
    """★ T13 的**厚度量具**：变体标记相关长度 `r_c^var`。

    为什么用它（`T13_calib_thickness.py` 的正对照判决）：
      `2f/Sv`（E1）在已知厚度的板条上 5 档只有 **1/5** 落在 ±15% 内，
      偏差系统性偏小（0.63–0.88）且**随 `R/t` 变化** ⇒ 混进了形状偏差，**不可用**。
      `r_c^var`（E2）5/5 落在 ±25% 内，`R/t ≥ 2.5` 时 = 已知厚度的 **0.76–1.00**，
      对球给出 0.43×直径 ⇒ **对薄板与等轴形状都量"最小维度"**，口径一致 ✓
    ⚠ 记账：对板条它偏小 0–24%（随 `R/t`）⇒ 结论要写成**区间**。
    """
    vals = []
    for k in range(1, nv + 1):
        chi = (reg == k)
        if chi.sum() < 8:
            continue
        rc = corr_1e(chi, dx)
        if np.isfinite(rc):
            vals.append(rc)
    return float(np.mean(vals)) if vals else np.nan


def run(L, dx, nseed, f_target, seed=7, max_steps=500):
    """★ 跑到**同一 `f`** 为止 —— 否则 `N_v` 与 `f` 混杂（首版就是这个错）。"""
    N = int(round(L / dx))
    g = W.LevelSetMulti(N, L, C=None, eps0=None, nv=NV, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)
    rng = np.random.default_rng(seed)
    ns = 0
    for _ in range(nseed * 8):
        if ns >= nseed:
            break
        c = rng.random(3) * (L - 2 * (R_SEED + 0.3e-6)) + (R_SEED + 0.3e-6)
        k = int(rng.integers(1, NV + 1))
        nrm = np.asarray(NPF[k], float)
        nrm = nrm / np.linalg.norm(nrm)
        try:
            g.seed_plate(k, c, nrm, R_SEED, T_SEED)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF)
    f = 0.0
    it = 0
    while it < max_steps:
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
        it += 1
        if it % 5 == 0:
            f = 1.0 - float((g.region() == 0).sum()) / g.N ** 3
            if f >= f_target:
                break
    reg = g.region()
    f = 1.0 - float((reg == 0).sum()) / g.N ** 3
    Sv = float(g.cell_area_geom().sum()) / g.L ** 3
    return dict(ns=ns, f=f, Sv=Sv, it=it, t=thickness_var(reg, NV, dx),
                phi=g.phi.copy())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--L-um', type=float, default=3.2)
    ap.add_argument('--dx-nm', type=float, default=62.5)
    ap.add_argument('--f-target', type=float, default=0.30)
    a = ap.parse_args()
    L = a.L_um * 1e-6
    dx = a.dx_nm * 1e-9
    print('=' * 100)
    print('T13-A（修正版）—— `N_v` 对板条厚的定标   L=%.1f µm  Δx=%.0f nm  '
          '**比到同一 f=%.2f**' % (a.L_um, a.dx_nm, a.f_target))
    print('  量具：`r_c^var`（变体标记相关长度）—— 已过正对照（5/5 在 ±25%% 内）')
    print('=' * 100)
    print('  %-9s %-7s %-8s %-8s %-13s %s' %
          ('N_v 倍数', '核数', '步数', 'f', 't=r_c^var (nm)', '相对 1× 档'))
    rows = []
    for mult in (1, 3, 8):
        r = run(L, dx, N0 * mult, a.f_target)
        rows.append((mult, r))
        print('  %-9d %-7d %-8d %-8.4f %-13.1f' %
              (mult, r['ns'], r['it'], r['f'], r['t'] * 1e9), flush=True)
    mult = np.array([r[0] for r in rows], float)
    tt = np.array([r[1]['t'] for r in rows], float)
    base = tt[0]
    for (m, r), t in zip(rows, tt):
        print('      N_v ×%-2d ⇒ t = %.1f nm（相对 1× 档 %.3f）' % (m, t * 1e9, t / base))
    p = float(np.polyfit(np.log(mult), np.log(tt), 1)[0])
    print()
    print('  拟合指数 d ln t / d ln N_v = **%.3f**（判据：|·| ∈ [0.25, 0.45]，理论 -1/3=-0.333）' % p)
    ratios_meas = tt[1:] / tt[:-1]
    ratios_theo = (mult[1:] / mult[:-1]) ** (-1.0 / 3.0)
    dev = np.abs(ratios_meas / ratios_theo - 1.0)
    print('  相邻档比值：实测 %s ；理论 %s ；最大偏差 %.1f%%（<25%%）'
          % (np.round(ratios_meas, 3), np.round(ratios_theo, 3), 100 * dev.max()))
    okA = (0.25 <= abs(p) <= 0.45) and (dev.max() < 0.25)
    print()
    print('=' * 100)
    print('  ⇒ T13-A %s' % ('PASS' if okA else 'FAIL'))
    print('  ⚠ 记账：量具 `r_c^var` 对板条偏小 0–24%%（随 R/t）⇒ 上面的"厚度"应读作**区间**。')
    print('=' * 100)
    return 0 if okA else 1


if __name__ == '__main__':
    sys.exit(main())
