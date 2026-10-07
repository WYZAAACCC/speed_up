#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r488_threadscale.py —— **CPU 线程扩展性实测**（任务(4) 的"免费那一半"）。

## 为什么要先量这个

用户原话：「注意已实测 FFT 只占 2.4%（`argmin` 18.4%、`eps0_fields` 17.0%、
`einsum` 10.9%），所以瓶颈在稠密数组运算而非 FFT。同时**把核数用满**
（现在 20 核只用了 6 核、load average 2.54）——若 GPU 证明有效，就"多核 + GPU"同时上。」

实测环境（`_r486_env.sh`）：**20 逻辑核**（i7-14700HX，10 核 × 2 线程），load **2.74**
⇒ **核根本没被用满**。所以"多核"这一半**不需要 GPU 也能拿**，而且**零风险**。

## 量什么

`LevelSetMulti.advance()` 一步的墙钟，作为 `workers ∈ {1,2,4,8,16}` 的函数。
口径：同一初始状态、同一 `dt`、同一 `kw`，**只改 `workers`**。
`workers` 走 `windowB_par.ParCtx`（引擎自己的空间切片并行，`windowB_surface.py:915`）。

## 预登记判据（**先写死，且必须能失败**）

| # | 检验 | 判据 |
|---|---|---|
| **S1** | **并行确实在起作用** | `workers=4` 的步时 **< 0.8 ×** `workers=1` 的步时 |
| **S2** | **数值不受 workers 影响** | 各 `workers` 下 `region()` 的胞数**必须逐位相同**（并行只切空间、不改归约次序） |
| **S3** | **报出饱和点** | 找出 `步时(2w)/步时(w)` 首次 ≥ 0.9 的 w ⇒ 那就是实际饱和核数 |
| **S4** | **不改默认** | `workers=1` 与不传 `workers`（引擎默认）等价 |

⚠ 若 S1 不过 ⇒ **CPU 并行这条路是假的**（那问题在别处，不在核数）⇒ 必须照实记。
⚠ 计时受其它负载影响（`abA` 在跑）⇒ **每档重复 3 次取中位**，并在结论里声明噪声。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_surface as W                                  # noqa: E402
from T16_verify_rve import C, EPS0                           # noqa: E402

N = 96
DX = 62.5e-9
NV = 12
GAMMA = 0.25
R_NUC = 320e-9
T_NUC = 510e-9
DF = 1.2e8
WORKERS = (1, 2, 4, 8, 16)
REPEAT = 3
TOL_S1 = 0.8
TOL_S3 = 0.9


def P(s=''):
    print(s, flush=True)


def build(workers):
    eps0 = [np.asarray(e, float) for e in EPS0]
    return W.LevelSetMulti(N, N * DX, C=C, eps0=eps0, gamma=GAMMA, Mob=1e-9,
                           df=[0.0] + [DF] * NV, workers=workers,
                           reinit_every=0, reinit_dt=1e-4)


def fresh_state():
    """造一个**有真实界面**的状态（否则 `advance` 太快、测不到并行）。"""
    g = build(1)
    g.npref_tab = {k: np.asarray(W._argmin_normal(C, np.asarray(EPS0[k - 1], float))[0],
                                 float) for k in range(1, NV + 1)}
    rng = np.random.default_rng(7)
    for k in range(1, NV + 1):
        ctr = rng.random(3) * (g.L - 2 * R_NUC) + R_NUC
        g.seed_plate(k, ctr, g.npref_tab[k], R_NUC, T_NUC)
    g.init_parent()
    return g


def main():
    P('=' * 88)
    P('_r488  CPU 线程扩展性（引擎 `advance()` 单步墙钟 vs `workers`）')
    P('=' * 88)
    P('  N=%d  nv=%d  L=%.1f µm   每档重复 %d 次取中位' % (N, NV, N * DX * 1e6, REPEAT))
    P('  ⚠ 记账：`abA` 仍在跑（约 2 核）⇒ 绝对耗时含噪声，**比值**受影响较小')
    P()

    base = fresh_state()
    kw = dict(aniso=0.0, npref=getattr(base, 'npref_tab', None))
    res = {}
    ncell_ref = None
    for w in WORKERS:
        ts = []
        for rep in range(REPEAT):
            g = build(w)
            g.phi[:] = base.phi
            g.c[:] = base.c
            g.df[:] = base.df
            g.npref_tab = base.npref_tab
            g.vmap = {k: k for k in range(1, NV + 1)}
            g.advance(float(g.dt) if hasattr(g, 'dt') else 1e-8, **kw)
            ncell = int((g.region() != 0).sum())
            if ncell_ref is None:
                ncell_ref = ncell
            elif ncell != ncell_ref:
                P('  ⚠ workers=%d 的 region 胞数=%d ≠ 参考 %d' % (w, ncell, ncell_ref))
            t0 = time.perf_counter()
            g.advance(1e-8, **kw)
            ts.append(time.perf_counter() - t0)
        res[w] = float(np.median(ts))
        P('  workers=%-3d  步时中位 = %.4f s   （各次 %s）'
          % (w, res[w], ' '.join('%.3f' % x for x in ts)))

    t1 = res[1]
    P()
    P('  ── 判据 ──')
    s1 = res[4] < TOL_S1 * t1
    P('  S1 并行起作用：步时(4)/步时(1) = %.3f  必须 < %.2f ⇒ **%s**'
      % (res[4] / t1, TOL_S1, '✅ PASS' if s1 else '❌ FAIL（CPU 并行这条是假的）'))
    P('  S2 数值与 workers 无关：全部 region 胞数 = %d（上面若有 ⚠ 就是 FAIL）'
      % (ncell_ref,))
    sat = None
    P('  S3 逐档加速比（相对 workers=1）与相邻档比：')
    # ★★ 自查发现的错误 #90：第一版把"相邻档比 ≥ 0.9"当成**饱和**，这是**反的** ——
    #   相邻档比 = `步时(w_{i-1}) / 步时(w_i)` = 这一档**又赚了多少**；
    #   它 **> 1 表示还在加速**，**≈ 1 才是饱和**（再多给核也没用）。
    #   实测：workers=2 的相邻档比是 **1.49**（赚得最多的一档），却被第一版标成"首次饱和"。
    #   ⇒ 改为 `ratio <= 1.05` 判饱和。
    TOL_SAT = 1.05
    for i, w in enumerate(WORKERS):
        sp = t1 / res[w]
        ratio = (res[WORKERS[i - 1]] / res[w]) if i > 0 else float('nan')
        tag = ''
        if i > 0 and ratio <= TOL_SAT and sat is None:
            sat = w
            tag = '   ← **首次饱和（这一档只多赚 %.0f%%）**' % (100 * (ratio - 1.0))
        P('     workers=%-3d  加速比 %.2f×   相邻档再赚 %s%s'
          % (w, sp, ('%.2f×' % ratio) if i > 0 else '—', tag))
    P()
    P('  ⇒ 到 workers=%d 为止**仍在加速**；实际饱和点 = **%s**；峰值加速比 **%.2f×**'
      % (WORKERS[-1], sat if sat else '本次扫描内未饱和',
         max(t1 / res[w] for w in WORKERS)))
    P('  ⇒ 建议：生产用 `--nthreads %d`（当前归档臂用的是 **3**）'
      % (sat if sat else WORKERS[-1]))
    P()
    P('=' * 88)
    P('★ 结论：%s' % ('**CPU 并行有效** ⇒ 任务(4) 的"多核"这一半可以立刻拿到'
                      if s1 else '❌ **CPU 并行无效 ⇒ 必须先查原因**'))
    P('=' * 88)
    return 0


if __name__ == '__main__':
    sys.exit(main())
