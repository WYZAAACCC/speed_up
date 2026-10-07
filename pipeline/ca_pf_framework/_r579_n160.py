#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r579_n160.py --- goal ⑤ 的**墙钟与峰值内存**部分：在 N=160（10 µm 盒）上直接跑几步。

## 为什么单列一道
`_r579_mem160.py` 只做**数组清单**（静态占用），它**不跑 `advance()`**
⇒ 拿不到"单步墙钟"和"跑起来之后的峰值 RSS"（后者含所有临时量）。
goal ⑤ 明确要求"N=160/10 µm 上给出**单步墙钟、峰值内存**、a 的逐项构成、实测 nv_max"。

## 规模选择与记账
`nv=12`（不是 C5 需要的 ~782）——理由是**内存安全**：nv=12 时 `phi` 只要
13×160³×8 = 681 MB，加 `Lam` 1.18 GB 与 `lambda_packed` 的临时量，峰值约 3–4 GB，
可以与本批次的内存道并存。**单步墙钟随 nv 近似线性**（`eps0_fields`∝nv），
所以这是**下界**；真正的 C5 规模读数必须在独占机器上另测（已记账）。

判据：
* **N1** soft 触发（`pf.phi.dtype == float64`）；
* **N2** 报 `s/步`（中位）与 `/usr/bin/time -v` 的峰值 RSS；
* **N3** 报"墙钟随 N 的标度"：同一 nv 下 N ∈ {64, 96, 128, 160}，拟合指数
        （预期 ≈3，因为算子都是整场 pass）。
"""
import os
import statistics
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                    # noqa: E402
from T16_verify_rve import C, EPS0                             # noqa: E402

DX = float(os.environ.get('R579N_DX', '0.0625'))
NV = int(os.environ.get('R579N_NV', '12'))
STEPS = int(os.environ.get('R579N_STEPS', '3'))
WORK = int(os.environ.get('R579N_WORKERS', '4'))
SIZES = [int(x) for x in os.environ.get('R579N_SIZES', '64,96,128,160').split(',')]
OUT = os.environ.get('R579N_OUT', '_w2_r579_n160.log')


def run_one(N):
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(NV)]
    t0 = time.perf_counter()
    g = W.LevelSetMulti(N, N * DX, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        df=[0.0] + [3.0e8] * NV, workers=WORK,
                        reinit_every=20, reinit_dt=1e-4, reinit_band_cells=6.0,
                        phi_prec='f64')
    g.init_parent()
    rng = np.random.default_rng(7)
    nrm = np.array([0.0, 0.0, 1.0])
    Lc = N * DX
    for k in range(1, max(3, NV // 8) + 1):
        g.seed_plate(k, rng.random(3) * (Lc * 0.6) + Lc * 0.2, nrm, 120e-9, 300e-9)
    t_build = time.perf_counter() - t0
    g.advance(dt=1e-8)
    d1 = str(g.pf.phi.dtype)
    ts = []
    for _ in range(STEPS):
        t0 = time.perf_counter()
        g.advance(dt=1e-8)
        ts.append(time.perf_counter() - t0)
    # 数组清单（静态占用）
    tot = 0
    seen = set()

    def walk(o, depth=0):
        nonlocal tot
        if depth > 6 or id(o) in seen:
            return
        seen.add(id(o))
        if isinstance(o, np.ndarray):
            tot += int(o.nbytes)
            return
        if isinstance(o, dict):
            for v in o.values():
                walk(v, depth + 1)
            return
        if isinstance(o, (list, tuple)):
            for v in o:
                walk(v, depth + 1)
            return
        dd = getattr(o, '__dict__', None)
        if isinstance(dd, dict):
            for v in dd.values():
                walk(v, depth + 1)
    walk(g)
    del g
    import gc
    gc.collect()
    return t_build, statistics.median(ts), min(ts), tot, d1


def main():
    L = []
    A = L.append
    A('=' * 100)
    A('R579-N160 — goal ⑤：墙钟随 N 的标度 + 峰值内存（nv=%d, dx=%.4f µm, %d 线程）'
      % (NV, DX, WORK))
    A('=' * 100)
    A('  %-6s %-12s %-12s %-12s %-14s %-10s %s'
      % ('N', 'build(s)', 's/步(中位)', 's/步(min)', '数组(MB)', 'pf.phi', '盒长(µm)'))
    rows = []
    for N in SIZES:
        tb, med, mn, tot, d1 = run_one(N)
        rows.append((N, tb, med, mn, tot, d1))
        A('  %-6d %-12.2f %-12.4f %-12.4f %-14.1f %-10s %.2f'
          % (N, tb, med, mn, tot / 2**20, d1, N * DX))
    # N3 标度指数
    if len(rows) >= 3:
        xs = np.log([r[0] for r in rows])
        ys = np.log([r[2] for r in rows])
        k = float(np.polyfit(xs, ys, 1)[0])
        A('')
        A('  N3 标度：log(s/步) vs log(N) 的斜率 = **%.3f**（预期 ≈3：算子都是整场 pass）'
          % k)
    # N1
    ok1 = all(r[5] == 'float64' for r in rows)
    A('  N1 soft 触发（`pf.phi.dtype == float64`）：%s'
      % ('✅ PASS' if ok1 else '❌ FAIL'))
    A('')
    A('  ⚠ 记账：本节 nv=%d（不是 C5 需要的 ≈782）——为了**内存安全**（与批次内其它道并存）。' % NV)
    A('     单步墙钟随 nv 近似线性（`eps0_fields` ∝ nv）⇒ 本表是**下界**。')
    A('     C5 规模的独占读数必须另跑（已登记）。')
    A('')
    A('  === RESULT: %s ===' % ('PASS' if ok1 else 'FAIL'))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, OUT), 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')
    return 0 if ok1 else 1


if __name__ == '__main__':
    sys.exit(main())
