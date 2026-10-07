#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r506_paramclosure.py —— ★★★★ **任务(5) 的参数闭环**：让五个约束同时成立。

## 起因（本轮的发现）

`windowB_km.py:348-349`：

    ALPHA_KM_BAND = (5.0e-3, 1.1e-2, 2.0e-2)   # 1/K  [A] 占位（文献常见量级 1e-2）
    ALPHA_KM_REF  = 1.1e-2                      # 1/K  [A] 默认占位

而**所有归档 A/B 臂与本轮算例**用的是 `--alpha-km 0.041739`
⇒ **是参考值的 3.8 倍、是文献带上沿的 2.1 倍。**

这重要，因为 `α_KM` 同时定住**块厚** `W_block = n·t`：

| `α_KM` | `n(T_end=298) = α_KM·575` | 块厚 `n·t`（t=510 nm） | 对 `W_BLOCK_BAND_UM=(1.0, 6.0)` |
|---|---|---|---|
| **0.011**（框架参考） | **6.3 根** | **3.2 µm** | ✅ **在带内** |
| **0.041739**（归档用的） | **24.0 根** | **12.2 µm** | ❌ **超 2 倍** |

## 本脚本把**五个约束**放在一起解

| # | 约束 | 来源 |
|---|---|---|
| **①** | **块厚** `n·t ∈ (1.0, 6.0) µm` | `W_BLOCK_BAND_UM`（文献带，`[仍未检索到]` 只作上限判据） |
| **②** | **每块根数** `n = α_KM·(M_s − T_end)` | C-2（`windowB_closure.alpha_km_n_lath`） |
| **③** | **块数几何上界** `B ≤ S/A_f = L_box²/(plate_L·plate_W)` | `R502_BLOCKCOUNT.md`（本轮新增） |
| **④** | **C5 的总根数** `B·n ∈ 220–450` | `NEXT_TASKS_FOR_REVIEW.md §4.1` |
| **⑤** | **内存** `(B·n+1)·N³·w ≤ 22 GB` | `R502 §3` |

## 预登记自检（**必须能失败**）

* **T1**：`n(T)` 用框架函数算，且与手算 `α_KM(M_s−T)` 一致（相对差 < 1e-12）；
* **T2（负对照）**：把 `α_KM` 取归档值 ⇒ **①必须 FAIL**（否则说明我的带/公式读错了）；
* **T3**：`W_BLOCK_BAND_UM` 必须真的来自 `windowB_closure`（不自己写死）。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_closure as CL                                  # noqa: E402
import windowB_km as KM                                       # noqa: E402

MS = float(KM.M_S_TI64)
T_END = 298.0
T_LATH = 510e-9                # `T_LATH_MAIN_NM`
PLATE_L, PLATE_W = 1000e-9, 500e-9
A_F = PLATE_L * PLATE_W
MEM_BUDGET_GB = 22.0
DX = 62.5e-9

CASES = [
    ('N=112 (7 µm)', 112),
    ('N=160 (10 µm)', 160),
    ('N=192 (12 µm)', 192),
]
ALPHAS = [0.005, 0.011, 0.02, 0.041739]


def main():
    band = CL.W_BLOCK_BAND_UM
    print('=' * 96)
    print('R506  任务(5) 参数闭环')
    print('=' * 96)
    print('  文献带 W_BLOCK_BAND_UM = %s µm（取自 `windowB_closure`，不写死）' % (band,))
    print('  M_s = %.1f K   T_end = %.1f K   t_lath = %.0f nm   A_f = %.4f µm²'
          % (MS, T_END, T_LATH * 1e9, A_F * 1e12))
    print()

    # ---- T1 ----
    ok_all = True
    a0 = 0.011
    n_func = float(CL.alpha_km_n_lath(T_END, a0))
    n_hand = a0 * (MS - T_END)
    e1 = abs(n_func - n_hand) / n_hand
    ok1 = e1 < 1e-12
    print('  T1 `alpha_km_n_lath` 与手算一致：%.10f vs %.10f，相对差 %.2e ⇒ %s'
          % (n_func, n_hand, e1, '✅ PASS' if ok1 else '❌ FAIL'))
    ok_all &= ok1

    # ---- T2 负对照 ----
    n_arch = float(CL.alpha_km_n_lath(T_END, 0.041739))
    w_arch = n_arch * T_LATH * 1e6
    bad = not (band[0] <= w_arch <= band[1])
    print('  T2 负对照：α=0.041739 ⇒ n=%.1f、块厚 %.2f µm ⇒ %s'
          % (n_arch, w_arch, '**超带**（预期）✅' if bad else '**在带内** ❌（说明带或公式读错了）'))
    ok_all &= bad

    # ---- T3 ----
    ok3 = isinstance(band, (tuple, list)) and len(band) == 2
    print('  T3 文献带取自框架：%s ⇒ %s' % (band, '✅ PASS' if ok3 else '❌ FAIL'))
    ok_all &= ok3
    print('  ★ 自检：%s' % ('**PASS**' if ok_all else '❌ FAIL'))
    print('=' * 96)
    print()

    # ---- 主表：每个 α × 每个盒子 ----
    for nm, N in CASES:
        L = N * DX
        S = L * L
        Bmax = S / A_F
        print('■ %s   L=%.1f µm   S=%.1f µm²   **B_max = %.0f**' % (nm, L * 1e6, S * 1e12, Bmax))
        print('   α_KM      n/块   块厚(µm)  ①带内?  要达 220–450 根需 B=  ③B≤B_max?  ⑤内存(f32)')
        for a in ALPHAS:
            n = a * (MS - T_END)
            w = n * T_LATH * 1e6
            inband = band[0] <= w <= band[1]
            B_lo, B_hi = 220.0 / n, 450.0 / n
            bok = B_hi <= Bmax
            Ntot = B_hi * n
            mem = (Ntot + 1) * (N ** 3) * 4 / 2**30
            memok = mem <= MEM_BUDGET_GB
            mark = ' ←**归档值**' if abs(a - 0.041739) < 1e-9 else (
                ' ←**框架参考**' if abs(a - 0.011) < 1e-12 else '')
            print('   %-9.6g %-6.1f %-9.2f %-7s %-21s %-11s %-6.1f GB %s%s'
                  % (a, n, w, '✅' if inband else '❌',
                     '%.0f–%.0f' % (B_lo, B_hi), '✅' if bok else '❌',
                     mem, '✅' if memok else '❌', mark))
        print()

    # ---- 结论 ----
    print('=' * 96)
    print('★ 结论')
    print('  1. `α_KM = 0.041739`（**所有归档 A/B 臂用的值**）使块厚 **%.1f µm**'
          % (0.041739 * (MS - T_END) * T_LATH * 1e6))
    print('     ⇒ **超出文献带 %s µm 两倍**。这是本轮新查出的一处**参数不闭环**。' % (band,))
    print('  2. **框架自己的参考值 `α_KM = 0.011`** 给 n = %.1f ⇒ 块厚 **%.1f µm**'
          % (0.011 * (MS - T_END), 0.011 * (MS - T_END) * T_LATH * 1e6))
    print('     ⇒ **正好落在带内** ⇒ 三条约束（C-2 / 块厚带 / 内存）同时满足。')
    print('  3. ⇒ 任务(5) 的目标配置：**`α_KM = 0.011`**、')
    n11 = 0.011 * (MS - T_END)
    print('     `B ≈ %.0f`（= 450/%.1f）块 × %.1f 根 = **%.0f 根**，'
          % (450.0 / n11, n11, n11, 450.0))
    L = 160 * DX
    print('     `N = 160`（10 µm）、f32 ⇒ 内存 **%.1f GB** ✅'
          % ((450.0 + 1) * (160 ** 3) * 4 / 2**30))
    print('     `B_max = %.0f` ⇒ `B = %.0f` **在几何界内** ✅'
          % ((L * L) / A_F, 450.0 / n11))
    print()
    print('  ⚠ **但这会改掉全部归档 A/B 的物理**（`α_KM` 从 0.0417 → 0.011）')
    print('     ⇒ 必须显式记账：**归档 A/B 的"板条数/块厚"结论作废**，')
    print('        而"块结构会形成 / F3 会出现 / 块间会接触"这类**拓扑**结论仍成立（与根数无关）。')
    print('=' * 96)
    return 0


if __name__ == '__main__':
    sys.exit(main())
