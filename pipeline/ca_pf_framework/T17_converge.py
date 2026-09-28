#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T17_converge.py --- **T17 三重收敛**：`Δx` × 3、`L` × 2、`N_v` × 3。

依据（全部来自本轮决策与实测）
----------------------------
* **D12d 盒子下限** `L ≥ 4·ρ^{−1/3}`；立方盒 `ρ = n/L³` ⇒ 判据化简为 **`n ≥ 64`**。
* **D12e 采样点** `f ≈ 0.10`（刚碰撞后；晚段被盒子夹住 + 界面粗化污染）。
* **D12c′ 判据形式**：不比"可信 core"，比**强度量在参数变化下的稳定性**。
* **D16c** `M6p` 用 **p25**；整数计数用 `|ΔN| ≤ 1`（R4）。
* **D17** 平流用 `proj2`（新默认）。
* **R5**：格式/参数的选择必须做 Δx 收敛 —— 本脚本就是它的制度化。

三个轴
------
  `dx` ：固定**物理** `L` 与固定 `ρ`（⇒ 固定 `n`），`Δx = 50 / 37.5 / 25 nm`
  `L`  ：固定 `Δx` 与**同数密度** `ρ`（⇒ `n ∝ L³`），`L = L0 / 1.5·L0`
  `nv` ：固定 `L`、`Δx`，`n = 64 / 128 / 256`

判据（**全部是强度量**）
----------------------
  * `t = r_c^var`（板条厚，已验证量具）、`Sv`（单位体积界面面积）、
    `M6p` **p25**（惯习面取向）⇒ 每个轴的**相对散布 < 10%**
  * `N_var`（整数）⇒ `|ΔN| ≤ 1`
  * **守卫**：每个采样点都必须"未绕盒（逐变体）+ 未膨胀"

★ 记账：本脚本**不新造量具** —— `stats()` 来自 `T16_verify_rve.py`，其中
  `r_c^var` 与 `M6p` 都已过正对照（T13）。R0 见 `T13b/T16` 的输出。

用法：
  python3 T17_converge.py --axis dx  --L-um 4.8 --dx-nm 50 --n 96 --adv proj2
  python3 T17_converge.py --axis L   --L-um 4.8 --dx-nm 50 --n 64  --adv proj2
  python3 T17_converge.py --axis nv  --L-um 4.8 --dx-nm 50 --n 64  --adv proj2
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
from T13b_verify_nv import run                                  # noqa: E402

RHO_REF = None      # 由 --n/--L-um 定出，供 L 轴"同数密度"用


def case(L, dx, n, f_target, adv):
    s = run(L, dx, n, f_target, adv)
    return s


def report(axis, rows, keys):
    """rows: list of (label, s)；keys: 参与 <10% 判据的强度量。"""
    print('-' * 100)
    print('  轴 = %s' % axis)
    print('  %-14s %-9s %-9s %-9s %-9s %-9s %-9s %s'
          % ('档', 'f', 't(nm)', 'Sv(1/m)', 'N_var', 'M6p p25', '2f/Sv(nm)', '守卫'))
    for lab, s in rows:
        t2f = (2.0 * s['f'] / s['Sv'] * 1e9) if s.get('Sv') else np.nan
        print('  %-14s %-9.4f %-9.1f %-9.3e %-9d %-9.1f %-9.1f %s'
              % (lab, s['f'], s['t'] * 1e9, s['Sv'], s['nvar'], s['m6p_p25'], t2f,
                 s['guard']), flush=True)
    ok = all(s['guard'] == 'ok' for _, s in rows)
    print('  守卫（全部未绕盒/未膨胀）：%s' % ('PASS' if ok else 'FAIL'))
    out = {}
    for key in keys:
        vals = [s[key] for _, s in rows]
        if any(not np.isfinite(v) for v in vals):
            print('  %-10s 含 nan ⇒ INCONCLUSIVE' % key)
            ok = False
            continue
        sp = (max(vals) - min(vals)) / max(abs(np.mean(vals)), 1e-30)
        g = sp < 0.10
        ok &= g
        out[key] = sp
        print('  %-10s = %-42s 散布 %.3f %s'
              % (key, ' '.join('%.4g' % v for v in vals), sp, 'PASS' if g else 'FAIL'))
    nvs = [s['nvar'] for _, s in rows]
    g = (max(nvs) - min(nvs)) <= 1
    ok &= g
    print('  %-10s = %-42s |ΔN| ≤ 1 %s' % ('N_var', ' '.join(str(v) for v in nvs),
                                           'PASS' if g else 'FAIL'))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--axis', required=True, choices=('dx', 'L', 'nv'))
    ap.add_argument('--L-um', type=float, default=4.8)
    ap.add_argument('--dx-nm', type=float, default=50.0)
    ap.add_argument('--n', type=int, default=64, help='基准核数（nv 轴的最小档）')
    ap.add_argument('--f-target', type=float, default=0.10)
    ap.add_argument('--adv', default='proj2')
    a = ap.parse_args()
    L0, dx0, n0 = a.L_um * 1e-6, a.dx_nm * 1e-9, a.n
    rho = n0 / L0 ** 3
    print('=' * 104)
    print('T17 —— 三重收敛（轴 = %s）  基准：L=%.2f µm Δx=%.1f nm n=%d ⇒ ρ=%.4f /µm³'
          % (a.axis, a.L_um, a.dx_nm, a.n, rho * 1e-18))
    print('  D12d：L ≥ 4ρ^(−1/3) ⇒ 立方盒化简为 n ≥ 64（基准 n=%d）' % n0)
    print('-' * 104)
    rows = []
    if a.axis == 'dx':
        # ★ dx 轴：固定物理 L 与固定 n ⇒ `d` 固定 ✓；`t/Δx` 随 dx 变，须 ≥3
        for dxn in (50.0, 37.5, 25.0):
            s = case(L0, dxn * 1e-9, n0, a.f_target, a.adv)
            rows.append(('Δx=%.1f nm' % dxn, s))
    elif a.axis == 'L':
        # ★ L 轴：**同数密度** ⇒ `d = ρ^(−1/3)` 逐档不变 ✓（R9 自动满足）
        for fac in (1.0, 1.5):
            L = L0 * fac
            n = int(round(rho * L ** 3))
            s = case(L, dx0, n, a.f_target, a.adv)
            rows.append(('L=%.2f µm (n=%d)' % (L * 1e6, n), s))
    else:
        # ★★★ 2026-09-28 修（**规格违约**）：旧写法"固定 L、只变 n"会让
        #   `d = L/n^(1/3)` 逐档变小 ⇒ `d/2R` 从 2.67 掉到 1.68 ⇒
        #   **n=128/256 两档违反 `MEASUREMENT_SPEC R9`**（晶核初始重叠 ⇒ `N_v` 无意义）。
        #   ⇒ 改成与 `T13b` 同一个「**固定 d、L = d·n^(1/3)**」设计。
        from T13b_verify_nv import D_FIX, R_SEED, T_SEED, MIN_D_OVER_SEED
        print('  ★ `nv` 轴用**固定 d 设计**：`d = %.2f µm`、`L = d·n^(1/3)`'
              '（R9 要求 `d ≥ %.1f × 2R=%.0f nm`）'
              % (D_FIX * 1e6, MIN_D_OVER_SEED, 2 * R_SEED * 1e9))
        for n in (n0, 2 * n0, 4 * n0):
            L = D_FIX * n ** (1 / 3.0)
            ratio = D_FIX / (2 * R_SEED)
            print('     n=%-5d ⇒ L=%.2f µm  N=%-4d  **d/2R = %.2f** %s'
                  % (n, L * 1e6, int(round(L / dx0)), ratio,
                     '✓' if ratio >= MIN_D_OVER_SEED else '✗ 违约'),
                  flush=True)
            s = case(L, dx0, n, a.f_target, a.adv)
            rows.append(('n=%d (L=%.2f µm)' % (n, L * 1e6), s))
    ok = report(a.axis, rows, ('t', 'Sv', 'm6p_p25'))
    print('-' * 104)
    print('  ⇒ T17[%s] %s' % (a.axis, 'PASS' if ok else 'FAIL'))
    print('  ★ 记账：任一不收敛 ⇒ 该维度是**主控参数**，必须作为"输入 + 敏感度"显式交付')
    print('=' * 104)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
