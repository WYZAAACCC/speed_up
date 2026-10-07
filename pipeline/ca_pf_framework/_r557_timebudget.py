#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r557_timebudget.py —— **任务(5) 的用时包线**（实测 + 留一法验证，不外推裸猜）。

## 为什么
`R550 §6` 已清掉 10 µm 盒的**内存**门槛（`--phi-prec f32` ⇒ `nv_max 605 → 1089`）。
但**用时**还没量过。而 `N=160` 相对 `N=64` 的代价是 `(160/64)³ = 15.6×`，
再乘上 `nv` 从 120 → ~1089（**9.1×**）⇒ 【推理】可能到 **~140×** ⇒
`1.2 s/步 × 140 ≈ 170 s/步`，600 步 ⇒ **~28 h** ⇒ **可能不可行**。
**⇒ 这是"能不能上 10 µm"的另一半，必须实测。**

## 做法
直接构造 `LevelSetMulti` 并调 `advance()`（**不含** `_bk_measure` 的测量开销 —— 那部分
在驱动层每 `--every` 步才发生一次，**单独记账**）。
扫一组 `(N, nv)`，拟合 `s/步 = A·nv·N³/2²⁰ + B·N³/2²⁰ + C`，**留一法**验证。

## 判据（先写死）
* **T1**：拟合的留一法最大相对误差 ≤ **25%**（沿用 `_r550` 的做法）。
* **T2**：`A > 0` 且 `B ≥ 0`（时间随 `nv`、随 `N` 都**单调不减**）—— 物理上必然。
* **T3**：给出 10 µm 候选（`N=160, nv=1089`）的**预测 s/步**与 **600 步墙钟**，
  并与"可接受用时"对比。**阈值取 24 h**（用户约束是"可接受用时之内"，未给数；
  24 h 是本机的合理上限，**必须显式标注这是我定的口径**）。
"""
import gc
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                    # noqa: E402
from T16_verify_rve import C, EPS0                             # noqa: E402

STEPS = 12          # 取末 6 步的均值当稳态
HOUR_LIMIT = 24.0   # ⚠ **本量具自定的"可接受用时"口径**（用户未给数）


def timeit(N, nv, prec, dx_nm=62.5, workers=4):
    L = N * dx_nm * 1e-9
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(nv)]
    g = W.LevelSetMulti(N, L, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        df=[0.0] + [3.0e8] * nv, workers=workers,
                        reinit_every=20, reinit_dt=1e-4, reinit_band_cells=6.0,
                        phi_prec=prec)
    g.init_parent()
    rng = np.random.default_rng(7)
    nrm = np.array([0.0, 0.0, 1.0]); along = np.array([1.0, 0.0, 0.0])
    for k in (1, 2, 3):
        if k > nv:
            break
        c = rng.random(3) * (L - 4e-6) + 2e-6 if L > 6e-6 else rng.random(3) * L * 0.5 + L * 0.25
        g.seed_plate(k, c, nrm, min(120e-9, L * 0.05), min(300e-9, L * 0.1))
    ts = []
    for i in range(STEPS):
        t0 = time.time()
        g.advance(dt=1e-8)
        ts.append(time.time() - t0)
    del g
    gc.collect()
    per = float(np.mean(ts[-6:]))
    return per, ts


def main():
    pts = [(32, 8), (32, 24), (48, 12), (48, 24), (64, 12), (64, 24), (80, 12)]
    data = []
    L = ['=' * 100, 'R557 —— 任务(5) 用时包线（实测，`advance()` 的时间）', '=' * 100,
         '  每点 %d 步，取末 6 步均值；`workers=4`（`R531` 实测的真实负载最优）'
         % STEPS, '']
    for N, nv in pts:
        per, ts = timeit(N, nv, 'f32')
        data.append((N, nv, per))
        L.append('  N=%-3d nv=%-3d ⇒ **%.4f s/步**（首步 %.4f ⇒ 稳态 %.4f）'
                 % (N, nv, per, ts[0], per))

    X = np.array([[nv * N ** 3 / 2**20, N ** 3 / 2**20, 1.0] for N, nv, _ in data])
    y = np.array([p for _, _, p in data])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    A, B, C = (float(coef[0]), float(coef[1]), float(coef[2]))
    errs = []
    for k in range(len(data)):
        idx = [j for j in range(len(data)) if j != k]
        ck, *_ = np.linalg.lstsq(X[idx], y[idx], rcond=None)
        pred = float(ck[0]) * X[k][0] + float(ck[1]) * X[k][1] + float(ck[2])
        errs.append(abs(pred - y[k]) / max(abs(y[k]), 1e-12))
    worst = max(errs)
    L.append('')
    L.append('  ── 拟合 `s/步 = A·nv·N³/2²⁰ + B·N³/2²⁰ + C` ──')
    L.append('     **A = %.4e s**（每 `nv`·每百万胞）  B = %.4e s  C = %.4e s'
             % (A, B, C))
    L.append('     留一法最大相对误差 = **%.1f%%**（判据 ≤25%%）⇒ %s'
             % (100 * worst, '✅ PASS' if worst <= 0.25 else '❌ FAIL ⇒ **不得外推**'))
    L.append('     逐点留一误差 = %s' % ', '.join('%.1f%%' % (100 * e) for e in errs))
    ok2 = (A > 0) and (B >= 0)
    L.append('     T2 `A>0 且 B≥0`（时间对 nv、N 单调不减）：%s（A=%.3e, B=%.3e）'
             % ('✅ PASS' if ok2 else '❌ FAIL', A, B))

    # ★★★★★ 2026-10-04：**T1 FAIL 之后的正确处理 —— 不调阈值，改成"在需要答案的地方量"**
    #   ## 为什么全局 3 参数模型对**时间**不成立（对内存却是精确的）
    #     逐点看**同 N 下的每 nv 斜率**：
    #       N=32: (0.0601−0.0421)/0.5  = **0.0360**
    #       N=48: (0.1009−0.0805)/1.2656 = **0.0161**
    #       N=64: (0.2004−0.1610)/3.0   = **0.0131**
    #     ⇒ **斜率随 N 下降** ⇒ `A·nv·N³` 这个形式**错了**（缓存/并行/访存效应）。
    #     而内存**是严格可加的**（`_r550` 留一法 0.13%）⇒ 两者性质不同，
    #     **不能拿内存那套模型套时间**。
    #   ## 做法
    #     直接在 **N=160（就是 10 µm）** 上量几个 `nv` ⇒ 用**局部**斜率外推到 1089。
    #     这比"全局拟合再外推"稳得多，而且**外推距离短**（480 → 1089 是 2.3×）。
    L.append('')
    L.append('  ── T1 的补救：**直接在 N=160 上量**（外推距离从 8× 缩到 2.3×） ──')
    loc = []
    for nv in (24, 120, 480):
        per, _ = timeit(160, nv, 'f32', workers=4)
        loc.append((nv, per))
        L.append('     N=160 nv=%-4d ⇒ **%.3f s/步**' % (nv, per))
    # 局部线性：用最大的两点定斜率（最接近目标区间）
    (nv1, p1), (nv2, p2) = loc[-2], loc[-1]
    slope = (p2 - p1) / (nv2 - nv1)
    pred1089 = p2 + slope * (1089 - nv2)
    L.append('     ⇒ 局部斜率（nv %d→%d）= **%.6f s/步/根**' % (nv1, nv2, slope))
    L.append('     ⇒ 外推到 **nv=1089**：**%.2f s/步** ⇒ 600 步 = **%.2f h**'
             % (pred1089, pred1089 * 600 / 3600))
    L.append('     ⇒ 外推到 nv=540：**%.2f s/步** ⇒ 600 步 = **%.2f h**'
             % (loc[1][1] + slope * (540 - 120),
                (loc[1][1] + slope * (540 - 120)) * 600 / 3600))
    L.append('     ⚠ 局部斜率法**未做留一法**（只有 3 个点）⇒ 标【推理】，'
             '但它的外推距离只有 2.3×，且**起点就在 N=160 上**。')

    # ---- T3：10 µm 候选 ----
    L.append('')
    L.append('  ── T3：候选配置的**预测用时**（600 步 ≈ 全程冷却） ──')
    for lbl, N, nv in (('本轮短跑 N=64, nv=120', 64, 120),
                       ('B=4 配置 N=64, nv=120', 64, 120),
                       ('**10 µm 填 28%** N=160, nv=1089', 160, 1089),
                       ('10 µm 折中 N=160, nv=540', 160, 540),
                       ('10 µm 保守 N=160, nv=223', 160, 223)):
        per = A * nv * N ** 3 / 2**20 + B * N ** 3 / 2**20 + C
        hrs = per * 600 / 3600
        L.append('     %-32s ⇒ **%7.2f s/步** ⇒ 600 步 = **%6.2f h** %s'
                 % (lbl, per, hrs,
                    '✅ <%.0fh' % HOUR_LIMIT if hrs <= HOUR_LIMIT
                    else '❌ **超 %.0fh 上限 %.1f×**' % (HOUR_LIMIT, hrs / HOUR_LIMIT)))
    L.append('')
    L.append('  ⚠ 记账：上面的 `s/步` **不含** `_bk_measure.measure_state`（每 `--every` 步一次）'
             '与快照/CSV 落盘；那些是**另一笔**开销，`--every` 取大可以压到很小。')
    L.append('  ⚠ "可接受用时"本量具**自定 24 h**（用户未给数）—— 换口径请改 `HOUR_LIMIT`。')

    npass = sum([worst <= 0.25, ok2])
    L.append('')
    L.append('★ 汇总：T1=%s  T2=%s（%d/2）'
             % ('PASS' if worst <= 0.25 else 'FAIL', 'PASS' if ok2 else 'FAIL', npass))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r557_timebudget.log'), 'w') as fh:
        fh.write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
