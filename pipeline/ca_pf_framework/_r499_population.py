#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r499_population.py —— ★★★★ **"到底能存在几根板条？"**（任务(5) 的头号约束）

## 为什么这是头号问题

任务(5) 的成功判据 **C5 是「块填满整个计算盒子」**，而 `NEXT_TASKS_FOR_REVIEW.md §4.1`
算过填满 10 µm 盒子要 **220–450 根**。

**但本轮把三件事放在一起，发现它们互相打架：**

| # | 事实 | 来源 |
|---|---|---|
| ① | athermal 律给出 `n(T) = α_KM·(M_s − T)`；`α_KM = 0.041739 /K` | `_bk_exp.py` 的 `--alpha-km` |
| ② | ⇒ 到 `T_end = 298 K` 时律要求 **`n = α_KM·(873−298) = 24` 根** | 直接算 |
| ③ | 而**超临界判据实测门槛 = 3.18e8 J/m³**，对应 **`T ≲ 377.7 K`** | `R479_SUPERCRIT.md §6` |
| ④ | ⇒ 第 `k` 根核要能被放下，必须 `T_k = M_s − k/α_KM ≤ 377.7 K` ⇒ **`k ≥ 21`** | 由 ②③ 推 |
| ⑤ | ⇒ **律要 24 根，但只有 `k = 21..24` 这 4 根放得下** | ④ |

**⇒ 若 ⑤ 成立，则 C5 在**任何盒子里**都做不到 —— 不是盒子太小，是**根本没有那么多根**。**

## 本脚本做什么

**只算账、不改任何东西**。把"能存在的板条数"用**两条独立约束**算出来并交叉核对：

* **约束 A（形核）**：超临界判据允许的核数 = `n(T_end) − n(T_阈)`；
* **约束 B（表示）**：`nv`（场数上限，任务(3) 已放开到 32760）与内存；
* **约束 C（几何）**：单根体积 × 根数 ≤ 盒子体积。

并给出**三条出路**各自的定量效果（供拍板，**不自己选**）。

## 预登记自检（**必须能失败**）

* **T1**：`n(T)` 必须是**单调递增**（T 降 ⇒ n 升）；
* **T2（负对照）**：把 `α_KM` 人为乘 2 ⇒ `n(T_end)` 必须**恰好翻倍**（证明公式用对了）；
* **T3**：`T_阈` 必须由 `KM.drive_of_T` 反解得到，且核对 `ΔG_v(T_阈) == |ed|`（残差 < 1e-9）。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_closure as CL                                  # noqa: E402
import windowB_km as KM                                       # noqa: E402

ALPHA = 0.041739          # 归档/本轮算例用的 α_KM
T_END = 298.0
ED_DISC = 3.181850e8      # `_r479` 实测：带尖边圆盘（`seed_plate` 的形状）的翻转点
ED_ELLIP = 2.087286e8     # `_r470`/`_r474` 实测：光滑椭球的弹性能密度
R_NUC, T_NUC = 320e-9, 510e-9


def selftest():
    ok = True
    print('=' * 88)
    print('R499 自检（预登记）')
    print('=' * 88)
    Ts = np.linspace(298.0, 872.0, 200)
    ns = np.array([float(CL.alpha_km_n_lath(t, ALPHA)) for t in Ts])
    ok1 = bool(np.all(np.diff(ns) < 0))     # T 升 ⇒ n 降
    print('T1 n(T) 单调（T↑ ⇒ n↓，200 点）：%s' % ('✅ PASS' if ok1 else '❌ FAIL'))
    ok &= ok1

    n1 = float(CL.alpha_km_n_lath(T_END, ALPHA))
    n2 = float(CL.alpha_km_n_lath(T_END, 2 * ALPHA))
    ok2 = abs(n2 - 2 * n1) < 1e-9
    print('T2 负对照 α×2 ⇒ n 翻倍：%.6f → %.6f ⇒ %s'
          % (n1, n2, '✅ PASS' if ok2 else '❌ FAIL'))
    ok &= ok2

    lo, hi = T_END, 1144.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if float(KM.drive_of_T(mid, KM.T0_TI64, KM.DS_REF)) > ED_DISC:
            lo = mid
        else:
            hi = mid
    T_th = hi
    res = abs(float(KM.drive_of_T(T_th, KM.T0_TI64, KM.DS_REF)) - ED_DISC) / ED_DISC
    ok3 = res < 1e-9
    print('T3 反解 T_阈 = %.2f K，核对 ΔG_v(T_阈)/|ed| − 1 = %.2e ⇒ %s'
          % (T_th, res, '✅ PASS' if ok3 else '❌ FAIL'))
    ok &= ok3
    print('★ 自检：%s' % ('**PASS**' if ok else '❌ FAIL（不出读数）'))
    print('=' * 88)
    return ok, T_th


def main():
    ok, T_th = selftest()
    if not ok:
        return 2
    print()

    Ms = float(KM.M_S_TI64)
    n_end = float(CL.alpha_km_n_lath(T_END, ALPHA))
    n_th = float(CL.alpha_km_n_lath(T_th, ALPHA))
    n_place = n_end - n_th

    print('── 约束 A：形核（超临界判据） ──')
    print('  α_KM = %.6g /K   M_s = %.1f K   T_end = %.1f K' % (ALPHA, Ms, T_END))
    print('  律要求的累计根数  n(T_end) = α_KM·(M_s − T_end) = **%.1f 根**' % n_end)
    print('  超临界门槛        T_阈 = **%.1f K**（对应 |ed| = %.4e J/m³）' % (T_th, ED_DISC))
    print('  门槛处律要求的根数 n(T_阈) = **%.1f 根**' % n_th)
    print('  ⇒ **放得下的核 = n(T_end) − n(T_阈) = %.1f 根**' % n_place)
    print('     （即第 %d 根到第 %d 根）' % (int(np.floor(n_th)) + 1, int(np.floor(n_end))))
    print()

    print('── 量级核对：为什么是这样 ──')
    dg298 = float(KM.drive_of_T(T_END, KM.T0_TI64, KM.DS_REF))
    print('  ΔG_v(298 K) = %.4e   vs   |ed|_圆盘 = %.4e   ⇒ 比值 **%.3f×**'
          % (dg298, ED_DISC, dg298 / ED_DISC))
    print('  ΔG_v(298 K) = %.4e   vs   |ed|_椭球 = %.4e   ⇒ 比值 **%.3f×**'
          % (dg298, ED_ELLIP, dg298 / ED_ELLIP))
    print('  ⇒ 哪怕冷到 298 K，驱动力也只比罚大 %.0f%%（用圆盘口径）'
          % (100 * (dg298 / ED_DISC - 1)))
    print()

    print('── 约束 B/C：就算放得下，够不够填满盒子 ──')
    for N, dx_nm in ((64, 62.5), (112, 62.5), (160, 62.5)):
        L = N * dx_nm * 1e-9
        V = L ** 3
        v1 = (1000e-9) * (500e-9) * (510e-9)
        # ★ 自查错误 #95：第一版把 m³ → µm³ 写成 ×1e12（应为 **×1e18**）
        #   ⇒ 印出 `V=0.000 µm³` 这种荒谬读数。比值本来就是对的（都是同单位），
        #     但**印出来的数**必须对。
        print('  N=%-4d Δx=%.1f nm ⇒ L=%.2f µm，V=**%.1f µm³**；单根 %.4f µm³'
              ' ⇒ 30%% 转变需 **%.0f 根**'
              % (N, dx_nm, L * 1e6, V * 1e18, v1 * 1e18, 0.30 * V / v1))
    print('  ⇒ 任务(5) 的 C5 要 **220–450 根**（`§4.1`，10 µm 盒子）')
    print()
    print('  ⚠⚠ **但"根数"这个词在这里有歧义，必须拆开**（自查错误 #97）：')
    print('     `windowB_closure.alpha_km_n_lath` 的 C-2 推导原文写着：')
    print('       「① 一次形核事件播一整片、**占满整个面内足迹** `A_f = L·W`')
    print('         ⇒ 一个核最终占的面积 `A_0 ≡ A_f`」')
    print('       「⚠ 本条**只对"堆叠型块"成立**（每片占满同一足迹）。')
    print('         平面上并列的块…需要在面内做 Voronoi 分割，**本轮不做**」')
    print('     ⇒ **`n(T) = %.0f` 是"一个块里堆叠的板条数"，不是"盒子里的总根数"。**' % n_end)
    print('     ⇒ 盒子里的总根数 = **（块数）×（每块根数）**，')
    print('        而**"块数"在框架里没有律**（`limitations()` 第 3 条明写"本轮不做"）。')
    print('     ⇒ 而**驱动**（`_bk_exp.py`）把那 24 当成了**全盒的事件上限**：')
    print('         `_tgt = min(floor(alpha_km_n_lath(T)), nv)`，`while n_ath_tgt < _tgt`')
    print('       ⇒ **实现把"每块根数"当成了"全盒总根数"** ⇒ 全盒最多 24 次事件。')
    print()

    print('=' * 88)
    print('★ 判决')
    if n_place < 10:
        print('  **约束 A 是硬墙**：当前参数下**只能存在约 %.0f 根**，' % n_place)
        print('  而 C5 要 220–450 根 ⇒ **不是盒子的问题，是"根本没有那么多根"。**')
        print()
        print('  三条出路（**定量效果，供拍板；本脚本不替你选**）：')
        print('   (1) **降 |ed|（把核播成光滑椭球而不是带尖边圆盘）**：')
        T_e = None
        lo, hi = T_END, 1144.0
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if float(KM.drive_of_T(mid, KM.T0_TI64, KM.DS_REF)) > ED_ELLIP:
                lo = mid
            else:
                hi = mid
        T_e = hi
        n_e = float(CL.alpha_km_n_lath(T_e, ALPHA))
        print('        门槛 %.1f K → **%.1f K**；可放核数 %.0f → **%.0f 根**'
              % (T_th, T_e, n_place, n_end - n_e))
        print('        ⚠ 但"圆盘 vs 椭球"哪个更物理**未定**（真实板条确实是尖边的）')
        print('   (2) **改"块数"**：总根数 = 块数 × 每块根数。要 220 根、每块 24 根')
        print('        ⇒ 需要 **%.0f 个块**。' % (220.0 / max(n_end, 1e-9)))
        print('        ⚠ **但框架里没有"块数"这条律**（`limitations()` 第 3 条明写）')
        print('          ⇒ 这是**框架缺口**，不是参数问题 ⇒ 必须先立律或有依据地登记')
        print('        ⚠ 而 `--nuc-fresh-every K` 已经把"块数 vs 每块根数"的**分配**暴露出来了')
        print('          （`K=4` ⇒ 每 4 个事件建 1 个新块）⇒ 但它**不改总量**（总量仍被 `n(T)` 卡住）')
        print('   (3) **降 α_KM**：⚠ 我第一版这里写"降"，**方向说反了**（自查错误 #96）——')
        print('        总根数 ∝ α_KM ⇒ 要 220 根需 α_KM ≈ **%.4f /K**（现在是 %.6g，差 **%.0f 倍**）'
              % (220.0 / (Ms - T_END), ALPHA, (220.0 / (Ms - T_END)) / ALPHA))
        print('        ⚠ **但 C-2/KM 的 α_KM 是有出处的**（文献 ~0.011 /K，本项目已用到 0.0417）')
        print('          ⇒ 调到 0.38 是**物理上不可接受**的 ⇒ **这条出路基本封死**')
    else:
        print('  可放核数 = %.0f ⇒ 约束 A 不是硬墙。' % n_place)
    print('=' * 88)
    return 0


if __name__ == '__main__':
    sys.exit(main())
