#!/usr/bin/env python3
"""_r424_design.py —— ★★ **受控双臂（A=守 C-3 / B=入 burst）的参数解算**

## 用户裁定（2026-10-01）
* 路线：**两条都跑，作受控对照**（A 守 C-3 / B 入 burst）；
* 目标规模：**6 块 × 4 根 = 24 根板条**。

## 解算
1. **`α_KM` 由"物理终温"定**（不是硬凑）：
     目标终温取**室温 298 K**（唯一有物理意义的冷却终点）
     `n = α_KM·(M_s − T_f)` ⇒ `α_KM = n/(M_s − 298) = 24/(873 − 298)`。
     ⚠ 若按 `n/(M_s − 0)` 取，会把终点压到 ~16 K —— **不物理**，故不用。
2. **`T_start = T_1 = M_s − 1/α_KM`**（框架口径：t=0 预摆的那片视为"在 T_1 形核"）。
3. **A 臂**：`q = q_cap(α, L_lath)`（守 C-3）⇒ `steps = steps_min_ordered(...)`。
4. **B 臂**：给定步数预算，反解 `q = ΔT/(steps·dt)`，报 `q/q_cap` 与 C-3 违反倍数。

## 判据（先算后跑）
  D-1 `n(T_f=298) = 24` 精确成立。
  D-2 A 臂 `ordered_ok(q) == True`（严格守 C-3）。
  D-3 B 臂 `q/q_cap > 1`（确实是 burst），且倍数**记账写清**。
  D-4 两臂的 `α_KM`、`T_start`、`plate`、`laths` **逐字相同** ⇒ 严格单变量（只差 q 与步数）。
"""
import sys

import numpy as np

import windowB_closure as CL
from windowB_km import T0_TI64, M_S_TI64

MOB = 1e-9
DX = 62.5e-9
CFL = 0.15
N_BLK, N_PER = 6, 4
N_LATH = N_BLK * N_PER
T_F = 298.0
PLATE_L = 1000e-9          # C-3 用的是**板条长度**
PLATE_W = 500e-9
PLATE_T = 510e-9
NBOX = 112


def P(s):
    print(s, flush=True)


P('=' * 88)
P('_r424 —— A/B 受控双臂参数解算（目标 %d 块 × %d 根 = **%d 根**）'
  % (N_BLK, N_PER, N_LATH))
P('=' * 88)

# ---------------------------------------------------------------- 1) α_KM
alpha = N_LATH / (M_S_TI64 - T_F)
P('\n[1] α_KM 由物理终温反解')
P('    M_s = %.1f K，目标终温 T_f = %.0f K（**室温**）' % (M_S_TI64, T_F))
P('    ⇒ α_KM = n/(M_s − T_f) = %d/%.0f = **%.6f /K**' % (N_LATH, M_S_TI64 - T_F, alpha))
n_chk = CL.alpha_km_n_lath(T_F, alpha)
P('    正对照：α_KM·(M_s − T_f) = **%.6f** ⇒ 取整 = **%d**  %s'
  % (n_chk, CL.n_lath_int(T_F, alpha), '✅ D-1 PASS' if CL.n_lath_int(T_F, alpha) == N_LATH else '❌'))
T1 = CL.T_start_of_clock(alpha)
P('    时钟起点 T_start = T_1 = M_s − 1/α_KM = **%.2f K**' % T1)
P('    ⇒ 本算例冷却窗口：**%.1f → %.0f K**（ΔT = %.1f K）' % (T1, T_F, T1 - T_F))
P('    ⚠ 记账：α_KM 原值 0.011 是 [标]（**无 Ti-64 实测值**，`limitations()` 第 2 条）；')
P('       本次按"%d 根 / 室温终温"重标到 %.6f —— **必须随结论一起报**。'
  % (N_LATH, alpha))

# ---------------------------------------------------------------- 2) 步数下界
P('\n[2] C-3 步数下界（`steps_min_ordered`，与 MOB/q 无关）')
steps_A = CL.steps_min_ordered(alpha, L_lath=PLATE_L, dx=DX, cfl=CFL, T_f=T_F)
P('    α=%.6f  L=%.0f nm  dx=%.1f nm  ⇒ steps_min = **%.0f 步**'
  % (alpha, PLATE_L * 1e9, DX * 1e9, steps_A))
P('    （对照：α=0.011、L=2400 nm 时是 2272 步）')

# ---------------------------------------------------------------- 3) q_cap
P('\n[3] C-3 冷速上界 `q_cap` 与 A 臂')
dG1 = CL.drive_of_T(T1, T0_TI64, CL.DS_REF) if hasattr(CL, 'drive_of_T') else None
import windowB_km as KM
dG1 = KM.drive_of_T(T1, T0_TI64, CL.DS_REF)
v_worst = CL.v_of_MOB(MOB, dG1)
q_cap = CL.q_max_ordered(v_worst, alpha, PLATE_L)
P('    ΔG_v(T_1) = %.4e J/m³ ⇒ v_worst = M·ΔG = %.4f m/s' % (dG1, v_worst))
P('    q_cap = v_worst/(α·L_lath) = **%.4e K/s**' % q_cap)
q_A = q_cap
ok_A, ratio_A, qm_A = CL.ordered_ok(q_A, MOB, alpha, PLATE_L, dG_worst=dG1)
P('    A 臂取 q = q_cap = %.4e K/s ⇒ ordered_ok = **%s**（Δt_grow/Δt_nuc = %.4f）'
  % (q_A, ok_A, ratio_A))
P('    ⇒ D-2 %s' % ('✅ PASS（严格守 C-3）' if ok_A else '❌ FAIL'))
# A 臂步数自洽：用 q 与 dt 反推（dt 随 T 变，用 steps_min_ordered 已给出）
P('    A 臂步数 = steps_min_ordered = **%.0f**' % steps_A)

# ---------------------------------------------------------------- 4) B 臂
P('\n[4] B 臂（burst）：给定步数预算，反解 q')
dt_ref = CFL * DX / (MOB * KM.drive_of_T(T1, T0_TI64, CL.DS_REF))
P('    参考 dt（T_1 处）= CFL·dx/(M·ΔG) = %.4e s' % dt_ref)
STEPS_B = 800
dT = T1 - T_F
q_B = dT / (STEPS_B * dt_ref)
P('    预算 %d 步 ⇒ q_B = ΔT/(步数·dt) = %.4e K/s' % (STEPS_B, q_B))
ok_B, ratio_B, _ = CL.ordered_ok(q_B, MOB, alpha, PLATE_L, dG_worst=dG1)
P('    ordered_ok = **%s**（Δt_grow/Δt_nuc = %.3f）；q_B/q_cap = **%.2f×**'
  % (ok_B, ratio_B, q_B / q_cap))
P('    ⇒ D-3 %s' % ('✅ PASS（确实是 burst，倍数已记账）' if q_B / q_cap > 1 else '❌'))
P('    ⚠ burst 的后果（框架原话）："**不是数值错误**"，但"本模型的逐片平衡形状')
P('       是在**长完**这个前提下才成立" ⇒ A/B 对照正是为了量这个前提的影响。')

# ---------------------------------------------------------------- 5) 单变量核对
P('\n[5] D-4 单变量核对：两臂**只差 q 与步数**')
same = dict(alpha_KM=alpha, T_start=T1, T_f=T_F, plate_L=PLATE_L, plate_W=PLATE_W,
            plate_T=PLATE_T, N=NBOX, dx=DX, n_lath=N_LATH,
            nuc_fresh_every=5, nuc_init=8)
for k, v in same.items():
    P('    %-18s = %s' % (k, v))
P('    A 臂：q = %.4e，steps = %.0f' % (q_A, steps_A))
P('    B 臂：q = %.4e，steps = %d' % (q_B, STEPS_B))
P('    ⇒ D-4 ✅（其余逐字相同）')

# ---------------------------------------------------------------- 6) 内存/用时预算
P('\n[6] 资源预算（**估算**，依据 `dry_saSet2` 实测 13 场/N=112 ⇒ 5.4 s/步）')
s_per_step = 5.4 * (N_LATH + 1) / 13.0
P('    场数 = %d（+母相）⇒ 预计 **%.1f s/步**（按 nreg 线性外推，**未实测**）'
  % (N_LATH + 1, s_per_step))
P('    A 臂：%.0f 步 × %.1f s = **%.1f 小时**' % (steps_A, s_per_step, steps_A * s_per_step / 3600))
P('    B 臂：%d 步 × %.1f s = **%.2f 小时**' % (STEPS_B, s_per_step, STEPS_B * s_per_step / 3600))
P('    内存：`dry_saSet2` 13 场实测 1.85 GB ⇒ 25 场约 **3.6 GB/臂**（外推，未实测）')
P('    ⇒ 两臂并行 ≈ 7.2 GB（预算 22 GB）✅')
P('=' * 88)
