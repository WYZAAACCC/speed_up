#!/usr/bin/env python3
"""_r422_c3budget.py —— ★★ **C-3 算力预算表**（正对照 + 外推）。

## 目的
`§188` 查明：400 步窗口里 athermal 律给不出事件。本脚本把"**要多少步才能按物理次序
长出 n 根板条**"算成一张表，并用**代码自己打印的数**做正对照。

## 正对照（**先过这条才看别的**）
`_r414_smoke.log` 打印：`C-3 步数下界 = 2272（从 T_1 起）`
（那次的参数：α_KM=0.011、q=4.56e6×0.8、dx=62.5 nm、N=64、`--plate-L` 取默认 2400 nm）。
⇒ 本脚本用**同一个** `windowB_closure.steps_min_ordered` 复算，必须复现 **2272**。

## 外推
框架自带的闭式（`windowB_closure.py:263`，**已推导、已注释**）：
    N_steps ≥ ΔT·[(T0−T_start) + ΔT/2]·α_KM·L_lath / (cfl·dx·(T0−T_start))
而根数 `n = α_KM·ΔT` ⇒ **每根板条的步数代价**
    N_steps/n = [(T0−T_start) + ΔT/2]·L_lath / (cfl·dx·(T0−T_start))
⇒ **与 α_KM、q、MOB 都无关**（这正是该闭式最强的地方）。
"""
import math
import sys

import numpy as np

import windowB_closure as CL
from windowB_km import T0_TI64, M_S_TI64

ALPHA = 0.011
T_F = 298.0


def P(s):
    print(s, flush=True)


P('=' * 84)
P('_r422 —— C-3 算力预算表（α_KM=%.4f，T_f=%.0f K）' % (ALPHA, T_F))
P('=' * 84)

# ---------------------------------------------------------------- 正对照
P('\n[P-1] 正对照：复现 `_r414_smoke.log` 打印的「C-3 步数下界 = 2272」')
Ts = CL.T_start_of_clock(ALPHA)
dT = Ts - T_F
n_full = CL.alpha_km_n_lath(T_F, ALPHA)
P('    T_start = T_1 = %.2f K   ΔT = %.2f K   n_full = α·ΔT = %.3f'
  % (Ts, dT, n_full))
for L_nm, dx_nm in ((2400.0, 62.5),):
    st = CL.steps_min_ordered(ALPHA, L_lath=L_nm * 1e-9, dx=dx_nm * 1e-9, T_f=T_F)
    P('    L_lath=%.0f nm, dx=%.1f nm ⇒ steps_min = **%.0f**（代码打印 2272）'
      % (L_nm, dx_nm, st))
    ok_p1 = abs(st - 2272) <= 2
    P('    ⇒ %s' % ('✅ PASS（差 ≤2 步）' if ok_p1 else '❌ FAIL（差 %.0f 步）'
                    % (st - 2272)))

# ---------------------------------------------------------------- 每根板条的步数
P('\n[P-2] **每根板条的步数代价** N_steps/n（与 α_KM、q、MOB 无关）')
P('    闭式：N/n = [(T0−T_start) + ΔT/2]·L_lath / (cfl·dx·(T0−T_start))')
P('')
P('    %-12s %-10s %-14s %-14s %s' % ('L_lath (nm)', 'dx (nm)', 'steps_min',
                                      'n_full', '**steps / 板条**'))
rows = []
for L_nm in (500.0, 1000.0, 2400.0, 4500.0):
    for dx_nm in (62.5, 125.0):
        st = CL.steps_min_ordered(ALPHA, L_lath=L_nm * 1e-9, dx=dx_nm * 1e-9, T_f=T_F)
        per = st / max(n_full, 1e-9)
        rows.append((L_nm, dx_nm, st, n_full, per))
        P('    %-12.0f %-10.1f %-14.0f %-14.2f **%.0f**' % (L_nm, dx_nm, st, n_full, per))

# ---------------------------------------------------------------- 目标构型
P('\n[P-3] 目标构型的**总步数**（C-3 有序 regime）')
P('    %-22s %-12s %-16s %s' % ('目标', 'L_lath (nm)', 'dx (nm)', 'steps_min (全窗口)'))
TARGETS = [(6, 4), (4, 4), (3, 4)]
for nblk, npl in TARGETS:
    n_tot = nblk * npl
    P('    %-22s' % ('%d 块 × %d 根 = %d 根' % (nblk, npl, n_tot)))
    done = False
    for L_nm in (1000.0, 2400.0):
        for dx_nm in (62.5,):
            # 需要的 ΔT 使 n = n_tot；反解 T_f
            T_f_needed = M_S_TI64 - n_tot / ALPHA
            if T_f_needed <= 0:
                P('        L=%.0f dx=%.1f ⇒ **T_f 需要 %.0f K < 0 ⇒ 物理上不可能**'
                  % (L_nm, dx_nm, T_f_needed))
                continue
            st = CL.steps_min_ordered(ALPHA, L_lath=L_nm * 1e-9,
                                      dx=dx_nm * 1e-9, T_f=T_f_needed)
            P('        L=%.0f nm  dx=%.1f nm  ⇒ **%.0f 步**'
              '（T_f 需要降到 %.0f K；按 5.4 s/步 ≈ %.1f 小时）'
              % (L_nm, dx_nm, st, T_f_needed, st * 5.4 / 3600))
            done = True
    if not done:
        P('        ⇒ **α_KM=%.4f 时，Ms−T_f 的上限只有 %.0f K**'
          ' ⇒ n 的上限 = α_KM·Ms = **%.1f 根** ⇒ 该目标不可达'
          % (ALPHA, M_S_TI64, ALPHA * M_S_TI64))

# ---------------------------------------------------------------- 要达到 n_tot 需要的 α_KM
P('\n[P-4] 若**坚持** C-3 有序，且只用 400 步：**反解 α_KM 的上限**')
P('    N_steps ∝ α_KM·ΔT = n（在 L、dx 固定时）⇒ 400 步能容纳的根数：')
for L_nm in (1000.0, 2400.0, 4500.0):
    for dx_nm in (62.5, 125.0):
        per = CL.steps_min_ordered(ALPHA, L_lath=L_nm * 1e-9, dx=dx_nm * 1e-9,
                                   T_f=T_F) / max(n_full, 1e-9)
        P('    L=%.0f nm dx=%.1f nm ⇒ %.0f 步/根 ⇒ **400 步只够 %.1f 根**'
          % (L_nm, dx_nm, per, 400.0 / per))
P('')
P('=' * 84)
P('结论口径：`steps_min_ordered` 是**物理下界**（与 MOB、q 都无关）——')
P('  想按物理次序长出 n 根板条，**调 MOB 或调冷速都省不下来**。')
P('=' * 84)
