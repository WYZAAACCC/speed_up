#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T8_verify_Mcalib.py --- T8 判据：界面迁移率 `M` 的**标定**与其数值自洽性。

两件事
------
(i) **物理标定**（由 `t_growth ≲ t_cool` 反推 `M` 的**下界**）：
      模型里 `v_n = M·Δf`（`Δf` 单位 J/m³ ⇒ `M` 单位 m⁴/(J·s) = m/(s·Pa)）。
      板条要长到 `L_lath` 必须 `v ≥ L_lath / t_cool` ⇒ `M ≥ L_lath/(t_cool·Δf)`。
      冷速三档（文献区间 10³–10⁸ K/s，L2 轨）各给一个下界 ⇒ 得到 `M` 的**可用带**。
      ★ 记账：`t_cool` 是【推理】（`ΔT/q`），代表冷却曲线段【未核实】；本判据只给**量级带**。
(ii) **数值自洽性**（`M` 不该改变形貌）：
      无量纲时间 `τ = t·v/a₀` 固定时，形貌应与 `M` 无关（`M` 只决定"多快"）。
      做法：扫 `M ∈ {1e-10, 1e-9, 1e-8}`，每档取 `dt ∝ 1/M` 使**每步位移相同**、
      步数相同 ⇒ `τ` 相同。若三者形貌比散布 > 5% ⇒ **判为数值未收敛**（不是物理）。

用法：python3 T8_verify_Mcalib.py [--N 64]
退出码：0 = PASS
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
import windowB_km as K                                          # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
_rng = np.random.default_rng(0)
NPF = {}
for v in range(NV):
    best, bn = None, None
    for n in _rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v], _lam_full(C, n), EPS0[v]))
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn

# --- L2 文献轨的锚点（片段级，见 docs/agent-notes/LITPARAM_TI64_MARTENSITE_ANCHORS.md）
L_LATH = 4.0e-6          # m，板条长度（【用户/几何设定】）
T_BETA, T_RT = 1268.0, 298.0


def M_lower(L_lath, q, df):
    """由 `v ≥ L/t_cool` 反推 M 的下界 [m^4/(J·s)]。t_cool = ΔT/q。"""
    t_cool = (T_BETA - T_RT) / float(q)
    v_need = L_lath / t_cool
    return v_need / float(df), t_cool, v_need


def one(M, N, dx, steps, df):
    L = N * dx
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=M,
                        df=[0.0] + [float(df)] * NV, workers=4, reinit_every=25)
    R = 0.10 * L
    g.seed_plate(1, [L / 2] * 3, NPF[1], R, 4 * dx)
    g.init_parent()
    dt = 0.15 * dx / (M * df)          # 每步位移 = 0.15 dx（与 M 无关）
    for _ in range(steps):
        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
    reg = g.region()
    idx = np.argwhere(reg == 1)
    if idx.size == 0:
        return None
    p = idx.astype(float) * dx
    p = p - p.mean(0)
    Cv = np.cov(p.T) if len(p) > 3 else np.eye(3)
    ev, evec = np.linalg.eigh(Cv)
    evec = evec[:, np.argsort(ev)[::-1]]
    ext = np.array([(p @ evec[:, j]).max() - (p @ evec[:, j]).min() for j in range(3)])
    return dict(AR1=float(ext[0] / max(ext[1], 1e-30)),
                AR2=float(ext[0] / max(ext[2], 1e-30)),
                AR3=float(ext[1] / max(ext[2], 1e-30)),
                V=int((reg == 1).sum()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=64)
    ap.add_argument('--dx-nm', type=float, default=25.0)
    ap.add_argument('--steps', type=int, default=200)
    a = ap.parse_args()
    N, dx = a.N, a.dx_nm * 1e-9
    print('=' * 100)
    print('T8 —— 界面迁移率 M 的标定与数值自洽性   N=%d dx=%.0f nm' % (N, a.dx_nm))
    print('=' * 100)

    # ---------------- (i) 物理标定 ----------------
    T0 = K.T0_from_Ms(K.M_S_TI64, K.DG_CRIT_REF, K.DS_REF)
    df_ms = float(K.drive_of_T(K.M_S_TI64, T0, K.DS_REF))
    print('【T8-i】由 t_growth ≲ t_cool 反推 M 的下界（L_lath = %.1f µm, Δf = %.3e J/m³）'
          % (L_LATH * 1e6, df_ms))
    print('   %-10s %-14s %-14s %-16s %s' %
          ('q (K/s)', 't_cool (s)', 'v_need (m/s)', 'M_lower', '与生产 M=1e-9 之比'))
    rows = []
    for q in (1e3, 1e5, 1e6, 1e8):
        Ml, tc, vn = M_lower(L_LATH, q, df_ms)
        rows.append((q, tc, vn, Ml))
        print('   %-10.0e %-14.3e %-14.3e %-16.3e %.2e' % (q, tc, vn, Ml, 1e-9 / Ml))
    M_need = rows[-1][3]                      # 最快冷速要求的下界（最苛刻）
    ok_i = (1.0e-9 >= M_need)
    print('   ⇒ 最苛刻档（q=1e8 K/s）要求 M ≥ %.3e；生产 M = 1e-9 ⇒ %s'
          % (M_need, '够' if ok_i else '**不够**（4 µm 长不完）'))
    print('   T8-i: %s' % ('PASS' if ok_i else 'FAIL'))

    # ---------------- (ii) 数值自洽性 ----------------
    print()
    print('【T8-ii】同一 τ（每步位移相同、步数相同）下形貌必须与 M 无关')
    res = {}
    for M in (1e-10, 1e-9, 1e-8):
        r = one(M, N, dx, a.steps, df_ms)
        res[M] = r
        if r is None:
            print('   M=%.0e ⇒ 变体消失（算例退化）' % M)
        else:
            print('   M=%.0e  长/厚=%.3f  长/宽=%.3f  宽/厚=%.3f  V=%d'
                  % (M, r['AR1'], r['AR2'], r['AR3'], r['V']), flush=True)
    good = [r for r in res.values() if r is not None]
    if len(good) < 3:
        print('   ⚠ 有档次退化 ⇒ 本判据失效（不能下"自洽"的结论）')
        return 2
    spread = {}
    for key in ('AR1', 'AR2', 'AR3'):
        v = np.array([r[key] for r in good], float)
        spread[key] = float((v.max() - v.min()) / max(abs(v.mean()), 1e-30))
    worst = max(spread.values())
    print('   相对散布：长/厚 %.4f、长/宽 %.4f、宽/厚 %.4f  ⇒ 最大 %.4f（判据 < 0.05）'
          % (spread['AR1'], spread['AR2'], spread['AR3'], worst))
    ok_ii = worst < 0.05
    print('   T8-ii: %s（%s）' % ('PASS' if ok_ii else 'FAIL',
                                 '自洽' if ok_ii else '**数值未收敛**'))
    print()
    print('=' * 100)
    print('  T8-i %s | T8-ii %s' % ('PASS' if ok_i else 'FAIL', 'PASS' if ok_ii else 'FAIL'))
    allok = ok_i and ok_ii
    print('  ⇒ T8 %s' % ('PASS' if allok else 'FAIL'))
    print('=' * 100)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
