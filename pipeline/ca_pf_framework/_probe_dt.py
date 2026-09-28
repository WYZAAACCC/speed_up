#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_dt.py --- `dt` 口径对照：**固定 `dt`（现状） vs `suggest_dt`（按总驱动）**。

动机（Round 22）
--------------
生产用 `dt = 0.15·Δx/(M·Δf)` —— **只用化学驱动**定 CFL。但真实驱动是
`dG = Δf + (ed_k − ed_l) − γκ`；**若弹性项是反对的**，则 `|dG| < Δf`
⇒ CFL 允许**更大**的 `dt` ⇒ 白算了机时。
项目自带的 `LevelSetMulti.suggest_dt(cfl)` 正是按 `self.dG_max`（**总驱动**，且已含 Mfac）定 `dt`。

判据（R0：先证工具可用 + 单变量）
-------------------------------
  **D1 加速比**：同一**物理时间**下两种 `dt` 口径的**步数比**。
  **D2 物理一致性**：同一物理时间下的形貌统计量（`f`、`Sv`、变体数）相对差 **<5%**。
      若 D2 不过，则 `suggest_dt` **不可用**（会改变物理）—— 那也是有价值的结论。
  **D3 稳定性**：`suggest_dt` 档的界面键数不得爆（相对 `f` 的增长应与固定档同量级）。

⚠ 记账：本测试用的是**小盒子 / 少量晶核**（纯属**口径对照**，不是交付读数），
   因此 R9 的 `d ≥ 2.5·2R` **不适用**；但 `t/Δx=4` 仍保持。

用法：python3 _probe_dt.py [--N 64] [--dx-nm 50] [--n0 8] [--tend 0.30]
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

MOB, DF = 1e-9, 3.5e8
R_SEED, T_SEED = 3.0e-7, 2.0e-7


def build(N, dx, n0):
    L = N * dx
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, nv=NV, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)
    rng = np.random.default_rng(7)
    ns = 0
    for _ in range(n0 * 12):
        if ns >= n0:
            break
        c = rng.random(3) * (L - 1.2e-6) + 0.6e-6
        k = int(rng.integers(1, NV + 1))
        nrm = np.asarray(NPF[k], float)
        nrm = nrm / np.linalg.norm(nrm)
        try:
            g.seed_plate(k, c, nrm, R_SEED, T_SEED)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    return g, ns


def stats(g):
    reg = g.region()
    f = 1.0 - float((reg == 0).sum()) / g.N ** 3
    nb = 0
    for ax in range(3):
        nb += int((reg != np.roll(reg, -1, axis=ax)).sum())
    nv = int(sum(1 for k in range(1, g.nreg)
                 if float((reg == k).sum()) / g.N ** 3 > 1e-4))
    return f, nb, nv


def run(N, dx, n0, tend, mode):
    g, ns = build(N, dx, n0)
    dt_fix = 0.15 * dx / (MOB * DF)
    t, steps, wt0 = 0.0, 0, time.time()
    dts = []
    while t < tend and steps < 5000:
        g.elastic_driving()
        if mode == 'fix':
            dt = dt_fix
        else:
            dt = g.suggest_dt(cfl=0.15, dt_prev=None, grow_max=2.0)
            if dt is None or not np.isfinite(dt) or dt <= 0:
                dt = dt_fix
            dt = min(dt, 4.0 * dt_fix)          # 上限：不让它一次跳太远（保守）
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                  mob_beta=3.5, mob_beta_w=2.3, adv_grad='proj2')
        dts.append(dt)
        t += dt
        steps += 1
    f, nb, nv = stats(g)
    return dict(f=f, nb=nb, nv=nv, steps=steps, wall=time.time() - wt0,
                dt_med=float(np.median(dts)), dt_max=float(np.max(dts)), ns=ns)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=64)
    ap.add_argument('--dx-nm', type=float, default=50.0)
    ap.add_argument('--n0', type=int, default=8)
    ap.add_argument('--tend', type=float, default=2.0e-7)
    a = ap.parse_args()
    dx = a.dx_nm * 1e-9
    print('=' * 100)
    print('dt 口径对照   N=%d Δx=%.0f nm  晶核=%d  同一**物理时间** tend=%.2e s'
          % (a.N, a.dx_nm, a.n0, a.tend))
    print('  ⚠ 本测试是小盒子/少晶核的**口径对照**，不是交付读数（R9 不适用）')
    print('  dt_fix = 0.15Δx/(MΔf) = %.4e s' % (0.15 * dx / (MOB * DF)))
    print('-' * 100)
    res = {}
    for mode, lab in (('fix', '固定 dt（现状）'), ('sug', 'suggest_dt（按总驱动）')):
        r = run(a.N, dx, a.n0, a.tend, mode)
        res[mode] = r
        print('  %-24s 步数=%-6d 墙时=%6.1f s  dt 中位=%.3e  dt 最大=%.3e'
              % (lab, r['steps'], r['wall'], r['dt_med'], r['dt_max']))
        print('  %-24s f=%.5f  界面键=%-7d 变体数=%d'
              % ('', r['f'], r['nb'], r['nv']), flush=True)
    print('-' * 100)
    rf, rs = res['fix'], res['sug']
    print('  D1 加速比：步数 %.0f → %.0f（**%.2f×**）；墙时 %.0f → %.0f s（%.2f×）'
          % (rf['steps'], rs['steps'], rf['steps'] / max(rs['steps'], 1),
             rf['wall'], rs['wall'], rf['wall'] / max(rs['wall'], 1)))
    df_ = abs(rs['f'] - rf['f']) / max(abs(rf['f']), 1e-30)
    dn_ = abs(rs['nb'] - rf['nb']) / max(abs(rf['nb']), 1e-30)
    print('  D2 物理一致性（同一物理时间）：Δf/f = **%.2f%%**、Δ键/键 = %.2f%%、ΔN_var = %d'
          % (100 * df_, 100 * dn_, rs['nv'] - rf['nv']))
    ok2 = (df_ < 0.05) and (dn_ < 0.10) and abs(rs['nv'] - rf['nv']) <= 1
    print('  D2 判定（Δf<5%% 且 Δ键<10%% 且 |ΔN_var|≤1）：%s' % ('PASS' if ok2 else 'FAIL'))
    print('  ⇒ **suggest_dt %s**' % ('可用（加速且不改物理）' if ok2 else
                                     '**不可用**（改变了物理 ⇒ 只能继续用固定 dt）'))
    print('=' * 100)


if __name__ == '__main__':
    main()
