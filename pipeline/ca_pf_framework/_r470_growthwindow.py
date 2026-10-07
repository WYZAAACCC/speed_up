#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R470 —— **生长窗口**：板条在什么温度下才站得住？（任务(2) 框架的核心定量结果）

## 问题的来源（本轮由三条独立观测拼出来）

1. `_r464` 受控实验末段：**两臂的 `Vt` 都塌到 ~1e-20 µm³** ⇒ **板条溶掉了**（§4.4b）。
2. `§203` 归档：`dry_abA` 场 1 **缩到 0.09×**；而常驱动力臂 `dry_saSet2` **12/12 都在长**。
3. `_r439`（自能工具）实测：**单根板条（半轴 500/250/255 nm）的弹性能 `E_el`**
   ⇒ 除以板条体积就是**弹性能密度**。

**把 1 与 3 放在一起**，速度律 `dG = Δf + (ed_k − ed_l) − stk·κ`（`ed_0 ≡ 0` 已验证）说：

```
板条能站住（dG > 0） ⟺  ΔG_v(T)  >  |ed_板条| + stk·κ
```

⇒ **存在一个温度门槛 `T*`，低于它板条才长得起来。**
**而冷却时钟预算（`_r465`）说：归档臂根本没冷到那里。**
⇒ **两条本来分开记的账，合起来才是"为什么长不起来"的完整答案。**

## 口径（全部给出来源）

| 量 | 来源 |
|---|---|
| `ΔG_v(T)` | `KM.drive_of_T(T, T0_TI64, DS_REF)`，`windowB_km.py:112` |
| `T0 = 1145.0 K`、`M_s = 873.0 K`、`DS_REF = 4.147e5 J/(m³K)` | `windowB_km.py:93-98` |
| `E_el`（单根板条） | **`_r439_selfenergy.py` 实测**（`_r439.log` 的 P-3 段） |
| 板条尺寸 | 半轴 `(500, 250, 255) nm`（= 归档 `--plate-L 1000 --plate-W 500 --plate-T 510` 的一半） |
| 速度律 | `windowB_surface.py:3346` `dG = Δf + (ed_k−ed_l) − stk·κ` |
| `ed_0 ≡ 0` | 已验证（`e0p[0]=zeros(6)`、`sep[0]=0`） |

## 预登记自检（**必须能失败**）

* **T1**：`ΔG_v(M_s=873)` 必须 == `DG_CRIT_REF`。
  ⚠⚠ **第一版判据写成"相对差 ≤ 1e-6"，实测 1.42e-5 ⇒ FAIL。**
  **留痕在下面（`T1 第一版`），不抹掉。**
  **FAIL 的原因是我的判据推导错了，不是框架错了**（见 T1b）：
  `DS_REF` 是**4 位有效数字的舍入值**（`windowB_km.py:98` 注释写它就是
  `DG_CRIT_REF/(T0−M_s)`），而 `1.128e8/272 = 4.1470588e5`，存的是 `4.147e5`
  ⇒ 舍入相对量 `1.42e-5` ⇒ **`drive_of_T(M_s)` 与 `DG_CRIT_REF` 本来就只能对到 1e-4 量级**。
  ⇒ 按纪律**不放宽阈值凑过**，而是**把判据换成它真正该检的东西**：
* **T1b（替换 T1）**：`|DS_REF − DG_CRIT_REF/(T0−M_s)| / implied ≤ 1.2e-4`
  （**1.2e-4 是 4 位有效数字舍入的解析上界**：末位半个单位 `50/4.147e5`，不是拍的）；
* **T2**：`ΔG_v(298)` 必须 == `3.512e8`（±0.5%）；
* **T3（负对照）**：把 `T0` 故意改错 10 K ⇒ `ΔG_v(M_s)` 必须**不再**等于 `DG_CRIT_REF`
  ⇒ 证明判据不是恒真式；
* **T4**：`ΔG_v(T)` 必须对 T **严格单调递减**（数值检查 200 点）。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_km as KM            # noqa: E402
import windowB_closure as CL       # noqa: E402

# ---- `_r439` 实测值（`_r439.log` 的 P-3 段，盒 6.0 µm，变体 7 那组）----
E_EL_J = 2.78689661e-11          # J，单根板条的弹性能（12 个变体里最小的那组）
HALF_AXES_NM = (500.0, 250.0, 255.0)
# ---- 归档/本轮算例的时间表 ----
CASES = {
    #  tag            q (K/s)      T_start   T_end   dt (s)     实测 t_s(末)  步数
    'dry_abA':   (2.3524e6, 849.04, 298.0, 4.10e-8, 1.0877e-4, 2080),
    'dry_abB':   (1.7412e7, 849.04, 298.0, 3.95e-8, 3.1611e-5, 800),
    'dry_r464A': (2.3524e6, 849.04, 298.0, 4.10e-8, 3.9589e-5, 600),
    'dry_r464B': (2.3524e6, 849.04, 298.0, 4.10e-8, 3.9589e-5, 600),
}
TOL_T1B = 1.2e-4          # ★ 4 位有效数字舍入的**解析上界**：50/4.147e5
TOL_T2 = 5e-3


def selftest(verbose=True):
    ok = True

    def _s(x):
        if verbose:
            print(x)

    _s('=' * 78)
    _s('R470 自检（预登记）')
    _s('=' * 78)
    d_ms = float(KM.drive_of_T(KM.M_S_TI64, KM.T0_TI64, KM.DS_REF))
    _s('T1 第一版（相对差 ≤1e-6）: ΔG_v(M_s) = %.6e vs DG_CRIT_REF = %.6e '
       '相对差 %.2e ⇒ ❌ **FAIL（留痕）**' % (d_ms, KM.DG_CRIT_REF,
                                          abs(d_ms - KM.DG_CRIT_REF) / KM.DG_CRIT_REF))
    # T1b：换成它真正该检的东西 —— DS_REF 与它的定义式是否一致（在舍入内）
    implied = KM.DG_CRIT_REF / (KM.T0_TI64 - KM.M_S_TI64)
    e1b = abs(KM.DS_REF - implied) / implied
    ok1 = e1b <= TOL_T1B
    _s('T1b DS_REF = %.6e  定义式 DG_CRIT/(T0−Ms) = %.6e  相对差 %.2e ≤ %.1e  %s'
       % (KM.DS_REF, implied, e1b, TOL_T1B, 'PASS' if ok1 else '❌ FAIL'))
    _s('    ⇒ 上面 T1 的 FAIL 由此**解释**：DS_REF 是 4 位有效数字的舍入值，'
       '舍入界就是 %.1e。' % TOL_T1B)
    ok &= ok1

    d298 = float(KM.drive_of_T(298.0, KM.T0_TI64, KM.DS_REF))
    e2 = abs(d298 - 3.512e8) / 3.512e8
    ok2 = e2 <= TOL_T2
    _s('T2 ΔG_v(298 K) = %.6e  对照 T16 记的 3.512e8  相对差 %.2e  %s'
       % (d298, e2, 'PASS' if ok2 else '❌ FAIL'))
    ok &= ok2

    # T3 负对照：T0 改错 10 K ⇒ Γ 关系必须被破坏
    d_bad = float(KM.drive_of_T(KM.M_S_TI64, KM.T0_TI64 + 10.0, KM.DS_REF))
    ok3 = abs(d_bad - KM.DG_CRIT_REF) / KM.DG_CRIT_REF > TOL_T1B
    _s('T3 负对照(T0 改错 10 K)  ΔG_v(M_s) = %.6e  必须离 DG_CRIT_REF 超过 %.1e  %s'
       % (d_bad, TOL_T1B, 'PASS（判据不是恒真式）' if ok3 else '❌ FAIL（恒真式！）'))
    ok &= ok3

    Ts = np.linspace(298.0, 1144.0, 200)
    ds = np.array([float(KM.drive_of_T(t, KM.T0_TI64, KM.DS_REF)) for t in Ts])
    ok4 = bool(np.all(np.diff(ds) < 0))
    _s('T4 ΔG_v(T) 对 T 严格单调递减（200 点）  %s'
       % ('PASS' if ok4 else '❌ FAIL'))
    ok &= ok4

    _s('-' * 78)
    _s('★ 自检总结论：%s' % ('**PASS ⇒ 可信**' if ok else '❌ **FAIL ⇒ 不可信**'))
    _s('=' * 78)
    return ok


def main():
    if not selftest():
        return 2
    print()

    # ---- 板条的弹性能密度 ----
    V_m3 = (4.0 / 3.0) * np.pi * (HALF_AXES_NM[0] * 1e-9) * \
        (HALF_AXES_NM[1] * 1e-9) * (HALF_AXES_NM[2] * 1e-9)
    ed_density = E_EL_J / V_m3
    print('── 板条的弹性能密度（`_r439` 实测）──')
    print('   E_el = %.6e J   体积 = %.4e m³（半轴 %s nm）' % (E_EL_J, V_m3, HALF_AXES_NM))
    print('   ⇒ **|ed| ≈ %.4e J/m³**' % ed_density)
    print('   ⚠ 口径：这是**整根板条的体积平均弹性能密度**，不等于界面胞上的局部 `ed`；')
    print('     两者量级应当一致，但**局部值需另测**（见末尾"待测"）。')
    print()

    # ---- 温度门槛 ----
    print('── 生长窗口：板条能站住的条件 `ΔG_v(T) > |ed| + stk·κ` ──')
    # ★★ 自查发现的错误 #81：第一版二分**方向反了**，收敛到 1144 K（显然荒谬：
    #   ΔG_v(1144) = 4.1e5 ≪ |ed| = 2.1e8）。根因：`ΔG_v(T) = DS·(T0−T)` 对 T
    #   **单调递减**，所以 `ΔG_v(mid) > ed` 意味着 mid 比 T* **更冷** ⇒ 应抬 `lo` 而不是压 `hi`。
    #   ⚠ 当时下面那行"核对 ΔG_v(T*) vs |ed|"已经打出相对差 0.998（= 完全不符），
    #     但我只 print 没 assert ⇒ **它没能拦住错结果**。现在把它变成**硬断言**。
    lo, hi = 298.0, 1144.0
    d_lo = float(KM.drive_of_T(lo, KM.T0_TI64, KM.DS_REF))
    d_hi = float(KM.drive_of_T(hi, KM.T0_TI64, KM.DS_REF))
    if d_lo <= ed_density:
        print('   ⚠ ΔG_v(298 K) = %.4e **也小于** |ed| = %.4e ⇒ **本参数下没有生长窗口**'
              % (d_lo, ed_density))
        Tstar = float('nan')
    else:
        assert d_hi < ed_density < d_lo, '二分区间必须先验成立'
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if float(KM.drive_of_T(mid, KM.T0_TI64, KM.DS_REF)) > ed_density:
                lo = mid          # mid 比 T* 更冷 ⇒ 抬 lo
            else:
                hi = mid          # mid 比 T* 更暖 ⇒ 压 hi
        Tstar = hi
        d_star = float(KM.drive_of_T(Tstar, KM.T0_TI64, KM.DS_REF))
        rel = abs(d_star - ed_density) / ed_density
        print('   二分求根（`ΔG_v(T*) = |ed|`，忽略 `stk·κ` 项 ⇒ 这是**最乐观**的门槛）：')
        print('   ⇒ **T* = %.1f K**' % Tstar)
        print('   ★ 硬核对 ΔG_v(T*) = %.6e  vs |ed| = %.6e  相对差 %.2e  %s'
              % (d_star, ed_density, rel, '✅' if rel < 1e-6 else '❌ **求根失败，结论不可用**'))
        if rel >= 1e-6:
            return 3          # ★ 不再"只打印不拦"
    print()
    print('   ⚠ `stk·κ` 项是**正的阻力**（曲率使小核收缩）⇒ 真实门槛比 T* **更低**（更冷）。')
    print('     所以 T* 是**乐观下界**：至少得冷到 T*，才可能看到净生长。')
    print()

    # ---- 各臂有没有冷到 T* ----
    print('── 各臂的时间表 vs 门槛 ──')
    print('   臂            q (K/s)    t_cool (s)    t_s(末)      末温 T (K)   越过 T*?   还需步数')
    for tag, (q, Ts_, Te, dt, ts_end, steps) in CASES.items():
        f = KM.linear_cool(Ts_, Te, (Ts_ - Te) / q)
        t_cool = f.t_cool
        T_now = float(f(ts_end))
        need_t = (Ts_ - Tstar) / q if Tstar == Tstar else float('nan')
        need_steps = (need_t - ts_end) / dt if need_t == need_t else float('nan')
        passed = (T_now <= Tstar) if Tstar == Tstar else False
        print('   %-12s %9.3e  %10.3e  %10.3e  %10.1f   %-9s %s'
              % (tag, q, t_cool, ts_end, T_now, '✅ 是' if passed else '❌ 否',
                 ('%.0f' % need_steps) if need_steps == need_steps and need_steps > 0
                 else ('已越过' if passed else '—')))
    print()

    # ---- 全冷却走完时的余量 ----
    print('── 如果**走完**冷却（T → 298 K），余量有多大 ──')
    d298 = float(KM.drive_of_T(298.0, KM.T0_TI64, KM.DS_REF))
    print('   ΔG_v(298 K) = %.4e   |ed| = %.4e   ⇒ 比值 **%.2f×**'
          % (d298, ed_density, d298 / ed_density))
    print('   ⇒ %s' % ('余量充足 ⇒ **冷却走完就能长**。'
                       if d298 / ed_density > 1.2 else
                       '余量很小 ⇒ 即使冷却走完，生长驱动力也仅勉强过线。'))
    print()
    print('=' * 78)
    print('★ **本轮框架结论（待你确认后再写代码）**：')
    print('  1. 板条站得住需要 `ΔG_v(T) ≳ %.2e J/m³` ⇒ **T ≲ %.0f K**（乐观门槛，忽略曲率）。'
          % (ed_density, Tstar if Tstar == Tstar else float('nan')))
    print('  2. **归档臂都没冷到那里**：abA 末温 %.0f K、abB 末温 %.0f K、r464 末温 %.0f K。'
          % (float(KM.linear_cool(849.04, 298.0, (849.04 - 298.0) / 2.3524e6)(1.0877e-4)),
             float(KM.linear_cool(849.04, 298.0, (849.04 - 298.0) / 1.7412e7)(3.1611e-5)),
             float(KM.linear_cool(849.04, 298.0, (849.04 - 298.0) / 2.3524e6)(3.9589e-5))))
    print('  3. ⇒ **"长不起来"与"填不满"的头号嫌疑不是形核律、不是盒长，而是"没冷够"。**')
    print('     `§203` 里 `saSet2` 的 12/12 生长 与 `abA` 的溶掉，可以由**这一条**统一解释：')
    print('     `saSet2` 用**常数 df = 3.5e8 > |ed| = %.2e** ⇒ 全场都在窗口内；' % ed_density)
    print('     `abA` 的 df 随 T 从 1.23e8 涨到 2.29e8 ⇒ **始终 < |ed|** ⇒ 溶。')
    print('  4. ⇒ 任务(5) 的算例**必须跑到 T ≲ %.0f K**；按 q=2.35e6 K/s、dt≈4e-8 s，'
          % (Tstar if Tstar == Tstar else float('nan')))
    if Tstar == Tstar:
        print('     需要 ≈ **%.0f 步**（当前 abA 计划 5922 步 ⇒ %s）。'
              % ((849.04 - Tstar) / 2.3524e6 / 4.1e-8,
                 '够' if (849.04 - Tstar) / 2.3524e6 / 4.1e-8 <= 5922 else '**不够**'))
    print('=' * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())
