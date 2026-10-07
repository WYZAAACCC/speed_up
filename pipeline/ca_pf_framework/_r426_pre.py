#!/usr/bin/env python3
"""_r426_pre.py —— A/B 双臂的**开跑前复核**（把要传的 q 与 steps 再算一遍，防止打错数）。"""
import windowB_closure as CL
import windowB_km as KM

MS, TF = 873.0, 298.0
N_TARGET = 24
alpha = N_TARGET / (MS - TF)
L = 1000e-9
dx = 62.5e-9
T1 = CL.T_start_of_clock(alpha)
dG = KM.drive_of_T(T1, KM.T0_TI64, CL.DS_REF)
qcap = CL.q_max_ordered(CL.v_of_MOB(1e-9, dG), alpha, L)
st_min = CL.steps_min_ordered(alpha, L_lath=L, dx=dx, T_f=TF)

print('alpha       = %.6f /K   (n(298) = %d)' % (alpha, CL.n_lath_int(TF, alpha)))
print('T_start     = %.2f K' % T1)
print('q_cap       = %.4e K/s' % qcap)
print('steps_min   = %.0f  (在 q = q_cap 上)' % st_min)
print()
print('%-4s %-14s %-10s %-12s %-14s %s'
      % ('臂', 'q (K/s)', 'steps', 'q/q_cap', 'Δt_grow/Δt_nuc', 'ordered_ok'))
for name, q in (('A', 0.8 * qcap), ('B', qcap * st_min / 800.0)):
    steps = st_min * qcap / q
    ok, ratio, _ = CL.ordered_ok(q, 1e-9, alpha, L, dG_worst=dG)
    print('%-4s %-14.4e %-10.0f %-12.4f %-14.4f %s'
          % (name, q, steps, q / qcap, ratio, ok))
print()
print('落盘参数（直接抄进 _r426_ab.sh）：')
print('  A: --cool-rate %.4e --steps %d' % (0.8 * qcap, round(st_min / 0.8)))
print('  B: --cool-rate %.4e --steps %d' % (qcap * st_min / 800.0, 800))
