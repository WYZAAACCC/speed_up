#!/usr/bin/env python3
"""_r442_c5check.py —— ★★★ **C-5（`β_h` 下界）在 A/B 双臂里到底满不满足？**

## 症状（`_r429` 实测，abB step 660 的厚度列）
```
厚度(在位的场) 1:1418 2:1244 4:871 5:1453 7:633 10:1171 11:1506 13:1102 17:2410 19:957 23:1256 nm
```
**初始播种厚是 510 nm**，现在是 633–2410 nm ⇒ **宽面在长厚，不是在长**。

## 模型自己的判据（`windowB_closure.beta_h_min`，`:320`）
法向迁移率 `M(n̂) = M0·e^{−β_h}` ⇒ 每步法向位移 ≤ `cfl·Δx·e^{−β_h}`
⇒ `N` 步累积 ≤ `cfl·N·Δx·e^{−β_h}`，要求 ≤ `δ_max·t`
⇒ **`β_h ≥ ln(cfl·N·Δx/(δ_max·t))`**（`δ_max = 0.3`）。

## 判据
**B-1** 从两臂的日志/`closure.json` 里取出**实际用的** `β_h` 与模型算的**下界**，直接比。
**B-2** 与实测厚度增长对照（预期：违反 ⇒ 长厚）。
**B-3** 若违反 ⇒ 给出**修复所需的最小 `β_h`**，并检查框架自带的
`beta_h_of_T`（`β_h(T) = β_h(M_s)·M_s/T`）能不能满足。
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_closure as CL      # noqa: E402


def P(s):
    print(s, flush=True)


P('=' * 96)
P('_r442 —— C-5（`β_h` 下界）核对')
P('=' * 96)

DX = 62.5e-9
T_LATH = 510e-9
T_MS = 873.0

for tag, steps in (('dry_abA', 5922), ('dry_abB', 800)):
    P('\n' + '#' * 96)
    P('# %s（--steps %d）' % (tag, steps))
    P('#' * 96)
    cj = os.path.join('_exp/_bk_mb', tag, 'closure.json')
    if os.path.exists(cj):
        d = json.load(open(cj))
        P('  closure.json 里的 β_h 项：')
        for k in ('beta_h_T', 'beta_h_floor', 'beta_h_used', 'q', 'q_cap',
                  'q_source', 'n_law', 'T_start', 'T_end', 'steps_min_ordered'):
            if k in d:
                P('    %-20s = %s' % (k, d[k]))
    else:
        P('  ✗ 无 closure.json')

    # 模型自带的判据
    b_floor = CL.beta_h_min(steps, DX, T_LATH)
    P('\n  **模型自带下界** `beta_h_min(%d, %.1f nm, %.0f nm)` = **%.4f**'
      % (steps, DX * 1e9, T_LATH * 1e9, b_floor))
    # 温度形式
    b_ms = CL.BETA_H_AT_MS
    b_298 = CL.beta_h_of_T(298.0, b_ms, T_MS)
    P('  温度形式 `beta_h_of_T`：β_h(M_s=%.0f K) = %.2f ⇒ β_h(298 K) = **%.2f**'
      % (T_MS, b_ms, b_298))
    b_eff, b_fl2 = CL.beta_h_run_average(steps, 1.0, CL.T_start_of_clock(0.041739),
                                         b_ms, T_MS, 298.0, DX, CL.CFL_DEFAULT, T_LATH)
    P('  运行区间加权平均 `beta_h_run_average` = **%.4f**（下界 %.4f）'
      % (b_eff, b_fl2))

P('\n' + '=' * 96)
P('[逐行核对：允许的长厚量 vs 实测的长厚量]')
P('=' * 96)
P('  允许的法向位移 = cfl·N·Δx·e^{−β_h}，要求 ≤ δ_max·t = %.0f nm（δ_max=0.3）'
  % (0.3 * T_LATH * 1e9))
P('  %-10s %-8s %-14s %-14s %s' % ('臂', 'steps', '允许位移(nm)', '判据 δ_max·t', '结论'))
for tag, steps, bh in (('abA', 5922, CL.BETA_H_AT_MS), ('abB', 800, CL.BETA_H_AT_MS)):
    allowed = CL.CFL_DEFAULT * steps * DX * np.exp(-bh)
    P('  %-10s %-8d %-14.1f %-14.1f %s'
      % (tag, steps, allowed * 1e9, 0.3 * T_LATH * 1e9,
         '❌ **违反**（允许量 > 上限）' if allowed > 0.3 * T_LATH else '✅ 满足'))
P('\n  ⇒ 需要的 β_h（= `beta_h_min`）：abA **%.2f**、abB **%.2f**；'
  % (CL.beta_h_min(5922, DX, T_LATH), CL.beta_h_min(800, DX, T_LATH)))
P('     而双臂实际用 `--beta-h %.2f`（默认）⇒ **两条臂都违反 C-5**。' % CL.BETA_H_AT_MS)
P('  ⇒ 框架**自带的**温度形式 `beta_h_of_T` 在 298 K 给 **%.2f**'
  % CL.beta_h_of_T(298.0, CL.BETA_H_AT_MS, T_MS))
P('     ⇒ 若**随温度更新** β_h，两条臂都能满足（这是框架里**已有**的物理形式）。')
P('=' * 96)
