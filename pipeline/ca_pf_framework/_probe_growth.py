#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_growth.py --- **门控问题**：`Δf = 2e8 J/m³` 下板条到底长不长得动？

动机（Round 9 心跳）：缩小的种子（`R=150 nm / t=50 nm`）在 20 步内 `f` 只从 0.00208
涨到 0.00217 —— **停止生长**。若 `Δf=2e8` 本身不足以驱动单变体板条长大，
那么 T13b/T16/T24 的**全部规格都需要重排**，这是必须最先回答的问题。

物理预期（R2：先写下期望再量）
------------------------------
单变体板条是**相干**的：弹性能密度 ~ `½Cε⁰²`（`C~1e11`、`ε⁰~0.1`）≈ **5e8 J/m³**，
**与 `Δf = 2e8` 可比甚至更大** ⇒ 净驱动力可能 ≈ 0 或为负。
⇒ **期望：单变体板条在 `Δf=2e8` 下几乎不长；要大长得把 `Δf` 提到 ≥ 弹性能量级。**
反向可能：`ed` 只有**偏量部分**抵消，且 `mob_beta` 钉扎会进一步压低速度 ⇒ 需要实测。

判据
----
  **G1 单变体板条的 `dV/V0` vs `Δf`**（`2e8 / 4e8 / 8e8`，同一物理时间）
  **G2 自协调对照**：两块**互相自协调**的变体（`ε⁰` 反号配对）放在一起 ⇒ 弹性能被抵消
        ⇒ **必须比单变体长得快**。若 G2 也长不动，则问题不在弹性。
  **G3 弹性关闭对照**：`C=None`（无弹性）⇒ **必须长得最快**（这是上界）。

用法：python3 _probe_growth.py [--N 64] [--dx-nm 50] [--steps 60]
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

MOB = 1e-9


def mk(N, dx, useC=True, nv=NV):
    L = N * dx
    g = W.LevelSetMulti(N, L, C=(C if useC else None),
                        eps0=(EPS0 if useC else None), nv=nv, gamma=0.15, Mob=MOB,
                        df=[0.0] + [2.0e8] * nv, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)
    return g, L


def growth(N, dx, df, useC=True, two=False, steps=60, R=3.0e-7, t=1.0e-7):
    g, L = mk(N, dx, useC)
    g.df[1:] = df
    c0 = np.array([L / 2] * 3)
    g.seed_plate(1, c0, np.asarray(NPF[1], float), R, t)
    if two:
        # 第二个变体放在旁边、取向取 npref[2]
        g.seed_plate(2, c0 + np.array([0.35 * L, 0, 0]),
                     np.asarray(NPF[2], float), R, t)
    g.init_parent()
    dt = 0.15 * dx / (MOB * max(df, 1e-30))
    reg0 = g.region()
    v0 = float((reg0 > 0).sum())
    t0 = time.time()
    for _ in range(steps):
        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                  mob_beta=3.5, mob_beta_w=2.3, adv_grad='proj2')
    reg1 = g.region()
    v1 = float((reg1 > 0).sum())
    return (v1 / max(v0, 1e-30) - 1.0,
            float((reg1 > 0).sum()) / g.N ** 3,
            float((reg0 > 0).sum()) / g.N ** 3,
            time.time() - t0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=64)
    ap.add_argument('--dx-nm', type=float, default=50.0)
    ap.add_argument('--steps', type=int, default=60)
    a = ap.parse_args()
    N, dx = a.N, a.dx_nm * 1e-9
    print('=' * 100)
    print('生长可行性门控测试   N=%d Δx=%.0f nm  L=%.2f µm  %d 步  种子 R=300/t=100 nm'
          % (N, a.dx_nm, N * a.dx_nm / 1000.0, a.steps))
    print('  R2 期望：弹性能密度 ~½Cε⁰² ≈ 5e8 J/m³ 与 Δf=2e8 可比 ⇒ 单变体板条应"几乎不长"')
    print('-' * 100)
    print('  %-34s %-12s %-12s %-10s %s'
          % ('配置', 'f_初', 'f_末', 'dV/V0', '墙时(s)'))
    rows = []
    for lab, kw in (('单变体  Δf=2e8  有弹性', dict(df=2.0e8, useC=True)),
                    ('单变体  Δf=4e8  有弹性', dict(df=4.0e8, useC=True)),
                    ('单变体  Δf=8e8  有弹性', dict(df=8.0e8, useC=True)),
                    ('单变体  Δf=2e8  **无弹性**', dict(df=2.0e8, useC=False)),
                    ('**双变体** Δf=2e8  有弹性', dict(df=2.0e8, useC=True, two=True))):
        d, f1, f0, wt = growth(N, dx, steps=a.steps, **kw)
        rows.append((lab, d))
        print('  %-34s %-12.6f %-12.6f %-10.4f %.1f' % (lab, f0, f1, d, wt), flush=True)
    print('-' * 100)
    print('  G1 单变体：Δf 从 2e8 提到 8e8 时 dV/V0 是否显著上升 ⇒ %s'
          % ('是（⇒ Δf=2e8 不够，规格要改）'
             if rows[2][1] > 3 * max(rows[0][1], 1e-9) else '否（⇒ Δf 不是瓶颈，另找）'))
    print('  G2 自协调（双变体）相对单变体：%.4f vs %.4f ⇒ %s'
          % (rows[4][1], rows[0][1],
             '自协调确实更快 ✓' if rows[4][1] > rows[0][1] else '**没有更快** ⇒ 瓶颈不在弹性'))
    print('  G3 无弹性上界：%.4f（应远大于有弹性档）%s'
          % (rows[3][1], '✓' if rows[3][1] > 3 * max(rows[0][1], 1e-9) else '✗'))
    print('=' * 100)


if __name__ == '__main__':
    main()
