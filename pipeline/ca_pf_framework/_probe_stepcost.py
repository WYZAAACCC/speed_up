#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_stepcost.py --- 步时热点分解（**实测，不推理**）。

动机（Round 8 心跳给出的真值）：T13b 实测 **19.66 s/步**（N=96 / 64 核），
是计划里按 T3 成本律估的 ~4 s/步的 **5×**。要优化必须先知道钱花在哪。

读代码得到的**待验证假设**：
  `LevelSetMulti.advance()` 的**非 per_field 路径**自己会调
  `self.elastic_driving_pair(karr, larr)`，而后者内部用
  `self.pf.sigma_tensor(reg)` **另做一次谱解**；它**并不读** `self.ed`。
  ⇒ 生产循环里那句显式的 `g.elastic_driving()`（算 12 个 `(N³)` 驱动场）
     **可能完全是冗余的**（算完就丢）。
  ⇒ 若成立，这是一个**零物理代价的 2× 加速**。

本探针只量时间，不判物理：
  (a) 只 `advance`
  (b) `elastic_driving()` + `advance`（现状）
  (c) `elastic_driving()` 每 3 步一次 + 每步 `advance`（**交错更新**）
  (d) 只 `elastic_driving()`（单独计价）

用法：python3 _probe_stepcost.py [--N 96] [--dx-nm 50] [--n0 64] [--steps 8]
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

MOB, DF = 1e-9, 2.0e8


def mk(N, dx, n0):
    L = N * dx
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, nv=NV, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)
    rng = np.random.default_rng(7)
    ns = 0
    for _ in range(n0 * 8):
        if ns >= n0:
            break
        c = rng.random(3) * (L - 1.0e-6) + 0.5e-6
        k = int(rng.integers(1, NV + 1))
        nrm = np.asarray(NPF[k], float)
        nrm = nrm / np.linalg.norm(nrm)
        try:
            g.seed_plate(k, c, nrm, 1.5e-7, 5.0e-8)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    return g, ns


def timed(g, dx, steps, mode, every=1):
    dt = 0.15 * dx / (MOB * DF)
    t0 = time.time()
    for it in range(1, steps + 1):
        if mode in ('both', 'stagger'):
            if mode == 'both' or (it - 1) % every == 0:
                g.elastic_driving()
        elif mode == 'edonly':
            g.elastic_driving()
            continue
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                  mob_beta=3.5, mob_beta_w=2.3, adv_grad='proj2')
    return (time.time() - t0) / steps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=96)
    ap.add_argument('--dx-nm', type=float, default=50.0)
    ap.add_argument('--n0', type=int, default=64)
    ap.add_argument('--steps', type=int, default=8)
    a = ap.parse_args()
    dx = a.dx_nm * 1e-9
    print('=' * 96)
    print('步时热点分解   N=%d Δx=%.0f nm  核数=%d  每组 %d 步'
          % (a.N, a.dx_nm, a.n0, a.steps))
    print('  假设：`advance` 内部自己调 `elastic_driving_pair` ⇒ 显式 `elastic_driving()` 冗余')
    print('-' * 96)
    res = {}
    for mode, every, lab in (('advonly', 1, '(a) 只 advance'),
                             ('both', 1, '(b) elastic_driving + advance（现状）'),
                             ('stagger', 3, '(c) elastic_driving 每 3 步'),
                             ('edonly', 1, '(d) 只 elastic_driving')):
        g, ns = mk(a.N, dx, a.n0)
        t = timed(g, dx, a.steps, mode, every)
        res[mode] = t
        print('   %-38s 步时 = %7.2f s' % (lab, t), flush=True)
    print('-' * 96)
    if 'advonly' in res and 'both' in res and res['advonly'] > 0:
        print('   (b)/(a) = %.2f×  ⇒ %s'
              % (res['both'] / res['advonly'],
                 '**`elastic_driving()` 基本冗余（零物理代价的加速）**'
                 if res['both'] / res['advonly'] < 1.25
                 else '`elastic_driving()` 确有贡献（不做冗余结论）'))
        print('   (c)/(b) = %.2f×  ⇒ 交错更新（每 3 步）额外省 %.0f%%'
              % (res['stagger'] / res['both'],
                 100 * (1 - res['stagger'] / res['both'])))
    print('=' * 96)


if __name__ == '__main__':
    sys.exit(main())
