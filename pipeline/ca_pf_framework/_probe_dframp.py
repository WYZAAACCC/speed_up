#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_dframp.py --- 检验 Round 40 暴露的"模型-文献张力"的**候选解释 ③**。

张力（`_t21g.log` + `_probe_growth.py`）
--------------------------------------
  | `Δf` | 模型 AR | 2D 长/宽 AR 参考（**带限定**） | 长得动？ |
  |---|---|---|---|
  | 2.0e8 | 3.70 | ✅ 在带内 | ❌ `dV/V0`=0.17@60 步 |
  | 3.5e8 | 1.03–1.21 | ❌ 远低 | ✅ 能长 |
⇒ **不能同时满足**。且提高 `β` 救不了（β 全范围只动 ×0.85）。

候选解释 ③（**本脚本要检验的**）
-----------------------------
真实过程里 `Δf = ΔS(T0−T)` 是**随时间上升**的（降温）⇒ 可能是
"**先低驱动长成板条、后高驱动增厚**"。若如此，用**阶梯/斜坡 `Δf(t)`**
应当**同时**得到"长得动"与"AR 落带"。

判据（三臂对照，**同一物理时间**，R0 正对照已由 `_chk_seedAR.py` 给出）
------------------------------------------------------------------
  A 常值 `Δf=2.0e8`（低驱动）
  B 常值 `Δf=3.5e8`（高驱动，= 生产）
  C **斜坡** `Δf: 2.0e8 → 3.5e8`（模拟降温）
  ⇒ **假设成立的条件**：`f_C > f_A`（长得动）**且** `AR_C > AR_B`（不被压钝）。
  ⇒ 若 `AR_C ≈ AR_B` ⇒ **斜坡救不了** ⇒ 解释 ③ 被否定，张力仍在。
  ⇒ 同时报 `AR_A` 作上界参照。

用法：python3 _probe_dframp.py [--N 64] [--dx-nm 50] [--steps 120]
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
from T21_beta_calib import section_ar_2d, _slice2d               # noqa: E402

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

MOB = 1e-9
R_SEED, T_SEED = 3.0e-7, 2.0e-7
BETA, BETA_W = 3.5, 2.3


def _ar_and_f(g):
    reg = g.region()
    m = (reg == 1)
    f = float(m.sum()) / g.N ** 3
    if m.sum() < 50:
        return np.nan, f
    idx = np.argwhere(m)
    ctr = idx.mean(0)
    ev, evec = np.linalg.eigh(np.cov((idx - ctr).T))
    ars = []
    for i in range(3):
        ax = int(np.argmax(np.abs(evec[:, i])))
        c = max(0, min(g.N - 1, int(round(ctr[ax]))))
        rem = [k for k in range(3) if k != ax]
        ar, _L, _W2, _A = section_ar_2d(_slice2d(m, ax, c, rem), g.dx)
        if np.isfinite(ar):
            ars.append(ar)
    return (float(np.median(ars)) if ars else np.nan), f


def run(N, dx, arm, steps, df_lo=2.0e8, df_hi=3.5e8, t_end=None):
    L = N * dx
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, nv=NV, gamma=0.15, Mob=MOB,
                        df=[0.0] + [df_hi] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)
    g.seed_plate(1, [L / 2] * 3, np.asarray(NPF[1], float), R_SEED, T_SEED)
    g.init_parent()
    dt = 0.15 * dx / (MOB * df_hi)          # ★ 三臂共用同一 dt ⇒ 同一物理时间
    if t_end is None:
        t_end = steps * dt
    t = 0.0
    hist = []
    for it in range(1, steps + 1):
        if arm == 'A':
            df = df_lo
        elif arm == 'B':
            df = df_hi
        else:                                # C：斜坡
            df = df_lo + (df_hi - df_lo) * min(t / t_end, 1.0)
        g.df[1:] = df
        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                  mob_beta=BETA, mob_beta_w=BETA_W, adv_grad='proj2')
        t += dt
        if it % 20 == 0:
            ar, f = _ar_and_f(g)
            hist.append((it, t, f, ar))
    return hist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=64)
    ap.add_argument('--dx-nm', type=float, default=50.0)
    ap.add_argument('--steps', type=int, default=120)
    a = ap.parse_args()
    dx = a.dx_nm * 1e-9
    print('=' * 100)
    print('斜坡 Δf 检验（候选解释 ③）  N=%d Δx=%.0f nm  单核 R=300/t=200 nm  %d 步'
          % (a.N, a.dx_nm, a.steps))
    print('  A=常值 2.0e8（低）  B=常值 3.5e8（高/生产）  C=斜坡 2.0e8→3.5e8')
    print('  ★ 三臂共用同一 dt ⇒ **同一物理时间**（R7）；β 固定 3.5/2.3；Δf 只从这一条通道进')
    print('-' * 100)
    print('  %-4s %-8s %-10s %-10s' % ('臂', 'step', 'f', '2D AR'))
    res = {}
    for arm in ('A', 'B', 'C'):
        h = run(a.N, dx, arm, a.steps)
        res[arm] = h
        for (it, t, f, ar) in h:
            print('  %-4s %-8d %-10.5f %-10.3f' % (arm, it, f, ar), flush=True)
    print('-' * 100)
    fA, fB, fC = res['A'][-1][2], res['B'][-1][2], res['C'][-1][2]
    aA, aB, aC = res['A'][-1][3], res['B'][-1][3], res['C'][-1][3]
    print('  末态对照（同一物理时间）：')
    print('     f   : A=%.5f  B=%.5f  C=%.5f   ⇒ C 比 A 长得动？ %s'
          % (fA, fB, fC, '是 ✓' if fC > fA * 1.1 else '**否 ✗**'))
    print('     AR  : A=%.3f  B=%.3f  C=%.3f   ⇒ C 比 B 更接近文献带 [2.8,8.4]？ %s'
          % (aA, aB, aC, '是 ✓' if aC > aB * 1.2 else '**否 ✗**'))
    print('  ⇒ **解释 ③（斜坡救场）%s**'
          % ('成立 ✓（张力有解）' if (fC > fA * 1.1 and aC > aB * 1.2)
             else '**被否定** —— 斜坡救不了，张力仍在（须走 ①/② 或如实报缺口）'))
    print('=' * 100)


if __name__ == '__main__':
    main()
