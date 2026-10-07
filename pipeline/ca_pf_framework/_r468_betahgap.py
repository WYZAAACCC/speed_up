#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R468 —— 定位 `beta_h = 6.477` 与 `beta_h_run_average` 重算值 6.2865 的 **2.9% 缺口**。

## 背景

* `BLOCK_PARAM_CLOSURE.md:234-235` 白纸黑字写：
  「按运行时间表加权平均（权重 `dt ∝ ΔG_v`）给 **6.48**。
   **两条完全独立的路线（物理的 `1/T` 律 6.48，与算力下界 5.86）落在同一个数上**」
  ⇒ **常数 6.477 是"故意取成运行均值"的**，不是"忘了加 T 依赖"。
* 但 R467 用**框架自己的** `CL.beta_h_run_average(...)` 重算，得 **6.2865**（差 2.9%）。

**⇒ 这 2.9% 必须定位清楚**，否则 S10 的判定（非缺陷 / 真缺陷）悬空。
最可能的来源：**积分起点 `T_start` 取哪个**（`T_1 = M_s − 1/α_KM = 849.04` 还是 `M_s = 873`？），
以及**权重用 `ΔG_v ∝ (T0−T)` 还是别的**。

本脚本把 `T_start` 扫一遍，看**哪一个起点能复现 6.477**，从而判定：
* 若能复现（相对差 ≤ 0.5%）⇒ **S10 = 非缺陷**：常数就是运行均值，只是**积分起点**与我第一版不同；
* 若任何起点都复现不了 ⇒ **S10 = 真缺陷（数值与文档不一致）**。

（纪律：**不得**为了让它对上而挑起点 —— 判据先写死为"≤0.5% 才算复现"，扫完照实报。）
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_closure as CL       # noqa: E402
import windowB_km as KM            # noqa: E402

TARGET = 6.477
TOL_REPRO = 0.005          # ★ 预登记：≤0.5% 才算"复现"


def b_eff(T_start, T_f=298.0, beta_at_Ms=CL.BETA_H_AT_MS, Ms=CL.M_S_TI64,
          npts=200001, wmode='dG', p=1.0):
    Ts = float(T_start) + np.linspace(0.0, -1.0, npts) * (float(T_start) - float(T_f))
    if wmode == 'dG':
        w = np.maximum(KM.T0_TI64 - Ts, 0.0) ** float(p)
    elif wmode == 'one':                     # 等权（= 对 T 均匀，不是对 t 均匀）
        w = np.ones_like(Ts)
    elif wmode == 'invT':                    # 权重 ∝ 1/T
        w = 1.0 / Ts
    else:
        raise ValueError(wmode)
    invT = float(np.sum(w / Ts) / np.sum(w))
    return float(beta_at_Ms) * float(Ms) * invT


def main():
    print('=' * 78)
    print('R468  TARGET = %.4f   判据：相对差 ≤ %.1f%% 才算"复现"' % (TARGET, 100 * TOL_REPRO))
    print('=' * 78)
    alpha = 0.041739
    T1 = float(CL.T_start_of_clock(alpha))
    print('参考起点：T_1 = T_start_of_clock(α=%.6g) = **%.4f K**   M_s = %.1f K   T0 = %.1f K'
          % (alpha, T1, CL.M_S_TI64, KM.T0_TI64))
    print()
    cands = [('T_1 (=%.3f)' % T1, T1), ('M_s (=%.1f)' % CL.M_S_TI64, float(CL.M_S_TI64)),
             ('T0 (=%.1f)' % KM.T0_TI64, float(KM.T0_TI64))]
    best = None
    for wmode in ('dG', 'one', 'invT'):
        print('  权重口径 wmode = %s' % wmode)
        for name, Ts in cands:
            v = b_eff(Ts, wmode=wmode)
            rel = abs(v - TARGET) / TARGET
            hit = rel <= TOL_REPRO
            print('     T_start = %-14s ⇒ beta_h_eff = %.4f   相对差 %6.2f%%   %s'
                  % (name, v, 100 * rel, '✅ **复现**' if hit else ''))
            if hit and (best is None or rel < best[0]):
                best = (rel, wmode, name, v)
        # 扫一个连续区间找最近点（只在 dG 口径下扫，避免过度搜索）
        if wmode == 'dG':
            grid = np.linspace(T1, float(KM.T0_TI64), 401)
            vals = np.array([b_eff(t, wmode='dG', npts=20001) for t in grid])
            i = int(np.argmin(np.abs(vals - TARGET)))
            rel = abs(vals[i] - TARGET) / TARGET
            print('     [扫描] T_start = %.2f K 时 beta_h_eff = %.4f（相对差 %.2f%%）'
                  % (grid[i], vals[i], 100 * rel))
            # 闭式反解：要得到 TARGET，需要的 T_eff
            T_eff = CL.BETA_H_AT_MS * CL.M_S_TI64 / TARGET
            print('     [反解] 6.477 对应的"等效温度" T_eff = 3.5·873/6.477 = **%.2f K**'
                  % T_eff)
        print()
    # ★ 追加：扫**权重指数** p（w ∝ (T0−T)^p）。文档只说"权重 dt ∝ ΔG_v" ⇒ p=1，
    #   而 p=1 复现不了 6.477。若某个 p 能复现，说明文档漏写了那个指数。
    print('  扫权重指数 p（w ∝ (T0−T)^p，T_start = T_1）：')
    grid_p = np.linspace(0.5, 6.0, 221)
    vals_p = np.array([b_eff(T1, wmode='dG', p=float(pp), npts=20001) for pp in grid_p])
    i1 = int(np.argmin(np.abs(grid_p - 1.0)))
    ip = int(np.argmin(np.abs(vals_p - TARGET)))
    relp = abs(vals_p[ip] - TARGET) / TARGET
    print('     p=1.0 ⇒ %.4f（差 %.2f%%）;  最接近的 p = **%.3f** ⇒ %.4f（差 %.2f%%）%s'
          % (vals_p[i1], 100 * abs(vals_p[i1] - TARGET) / TARGET,
             grid_p[ip], vals_p[ip], 100 * relp, '  ✅ 复现' if relp <= TOL_REPRO else ''))
    if relp <= TOL_REPRO:
        best = (relp, 'dG^p', 'p=%.3f, T_start=T_1' % grid_p[ip], float(vals_p[ip]))
    print()
    print('=' * 78)
    if best:
        print('★ 复现成功：wmode=%s, T_start=%s ⇒ %.4f（相对差 %.2f%%）'
              % (best[1], best[2], best[3], 100 * best[0]))
        print('★ ⇒ **S10 判定 = 非缺陷**：常数 6.477 确实是"运行区间等效值"，'
              '只是积分起点与 R467 第一版不同。')
    else:
        print('❌ **没有任何 (口径, 起点) 组合能复现 6.477** ⇒')
        print('   ⇒ **S10 判定 = 真缺陷（文档数值与代码函数不一致）**，')
        print('     或者 6.477 来自本文件之外的另一条推导（须去 `BLOCK_PARAM_CLOSURE.md` 找原始算式）。')
    print('=' * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())
