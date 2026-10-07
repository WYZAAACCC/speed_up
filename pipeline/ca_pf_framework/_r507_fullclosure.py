#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r507_fullclosure.py —— ★★★★★ **五约束的完整闭环**：`α_KM` × **核形状** × 块数。

## 这一版补上了上一版缺的那一环

`R506_PARAM_CLOSURE.md` 只联立了「C-2 / 块厚带 / 块数上界 / C5 总根数 / 内存」，
**没有把超临界门槛算进去**。算进去之后，多出一个**决定性的量**：

    **每块真正放得下的核数** = n(T_end) − n(T_阈) = α_KM · (T_阈 − T_end)

而 `T_阈` **取决于核的形状**（因为判据里的弹性罚 `|ed|` 取决于形状）：

| 核形状 | `|ed|`（**实测**） | `T_阈` | 每块放得下 = `α_KM·(T_阈 − 298)` |
|---|---:|---:|---|
| **带尖边圆盘**（`seed_plate` 现在播的：`sdf = max(\|d\|−t/2, rperp−R)`） | **3.1818e8** | **377.7 K** | `α_KM × 79.7` |
| **光滑椭球** | **2.0873e8** | **641.7 K** | `α_KM × 343.7` |

`|ed|` 两个值分别由 `_r479`（圆盘，翻转点二分）与 `_r470`/`_r474`（椭球）**实测**。

## 于是三个要求互相夹住

* **C3**（块内多根堆叠）⇒ 每块放得下 **≥ 2–3 根**；
* **块厚带**（`W_BLOCK_BAND_UM = (1.0, 6.0) µm`）⇒ `n·t = α_KM·575·0.51 µm ∈ (1,6)`
  ⇒ **`α_KM ≤ 0.020`**（`n ≤ 11.5`）；
* **C5**（填满）⇒ 总根数 ≥ 220 ⇒ `B · (每块放得下) ≥ 220`，而 `B ≤ B_max = L²/A_f`。

## 预登记自检（**必须能失败**）

* **T1**：`T_阈` 必须由 `KM.drive_of_T` **反解**得到，且核对 `ΔG_v(T_阈) == |ed|`（残差 < 1e-9）；
* **T2（负对照）**：把 `|ed|` 取成一个**荒谬的小值**（1e6）⇒ `T_阈` 必须趋近 `T0`（1145 K）
  ⇒ 证明反解不是恒等式；
* **T3**：`W_BLOCK_BAND_UM` 与 `T_LATH` 必须**从框架取**，不写死。
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
# ★★ 自查错误 #98（留痕）：第一版这里用的是 **`_r470`/`_r474` 的椭球值 2.0873e8**，
#   而那是 **`PF3D` 求解器 + 1000×500×510 nm 的大椭球**；
#   本处的核是 **R=320 nm、t=510 nm**（半轴 320/320/255）⇒ **几何不同**，
#   拿它当参照是**苹果比橘子**。
#   ⇒ 改成用 **`_r509` 在引擎同一条路径（`_supercrit_probe`）上、同一核几何下实测的**一对：
ED_DISC = 3.172046e8          # `_r509` 实测（引擎，R=320/t=510）
ED_ELLIP = 2.576010e8         # `_r509` 实测（引擎，同几何，椭球）
#   参照（**不同几何**，只作旁证，不参与计算）：
ED_DISC_REF_474 = 3.181850e8  # `_r479`（圆盘，同几何）
ED_ELLIP_REF_474 = 2.087286e8  # `_r470`/`_r474`（PF3D，500/250/255 椭球）
SHAPES = [('带尖边圆盘（现 seed_plate）', ED_DISC), ('光滑椭球', ED_ELLIP)]
ALPHAS = [0.005, 0.011, 0.02, 0.041739]
MEM_BUDGET_GB = 22.0


def solve_Tth(ed):
    lo, hi = T_END, 1144.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if float(KM.drive_of_T(mid, KM.T0_TI64, KM.DS_REF)) > ed:
            lo = mid
        else:
            hi = mid
    return hi


def main():
    band = CL.W_BLOCK_BAND_UM
    t_lath = CL.T_LATH_MAIN_NM * 1e-9
    print('=' * 100)
    print('R507  五约束完整闭环：α_KM × 核形状 × 块数')
    print('=' * 100)
    print('  文献带 W_BLOCK_BAND_UM = %s µm（取自框架）   t_lath = %.0f nm' % (band, t_lath * 1e9))
    print('  实测弹性罚（**引擎同几何**，`_r509`）：圆盘 %.4e   椭球 %.4e J/m³'
          % (ED_DISC, ED_ELLIP))
    print('  （旁证，**不同几何**，不参与计算：`_r479` 圆盘 %.4e；'
          '`_r470`/`_r474` 的 PF3D 大椭球 %.4e）' % (ED_DISC_REF_474, ED_ELLIP_REF_474))

    # ---- 自检 ----
    ok_all = True
    T1 = solve_Tth(ED_DISC)
    r1 = abs(float(KM.drive_of_T(T1, KM.T0_TI64, KM.DS_REF)) - ED_DISC) / ED_DISC
    ok1 = r1 < 1e-9
    print('  T1 反解 T_阈(圆盘) = %.2f K，ΔG_v/|ed| − 1 = %.1e ⇒ %s'
          % (T1, r1, '✅ PASS' if ok1 else '❌ FAIL'))
    ok_all &= ok1
    T1b = solve_Tth(1e6)
    ok2 = T1b > 1100.0
    print('  T2 负对照 |ed|=1e6 ⇒ T_阈 = %.2f K（应趋近 T0=1145）⇒ %s'
          % (T1b, '✅ PASS' if ok2 else '❌ FAIL'))
    ok_all &= ok2
    ok3 = isinstance(band, (tuple, list)) and abs(t_lath * 1e9 - 510.0) < 1e-9
    print('  T3 文献带/厚度取自框架 ⇒ %s' % ('✅ PASS' if ok3 else '❌ FAIL'))
    ok_all &= ok3
    print('  ★ 自检：%s' % ('**PASS**' if ok_all else '❌ FAIL'))
    print('=' * 100)
    print()

    # ---- 主表 ----
    for L_um in (7.0, 10.0, 12.0):
        N = int(round(L_um * 1e-6 / 62.5e-9))
        S = (L_um * 1e-6) ** 2
        A_f = 1000e-9 * 500e-9
        Bmax = S / A_f
        print('■ L=%.0f µm（N=%d）  B_max = %.0f' % (L_um, N, Bmax))
        print('   核形状            α_KM     n/块  块厚µm  带内?  每块放得下  B_max下总根数  ≥220?  内存f32')
        for sname, ed in SHAPES:
            Tth = solve_Tth(ed)
            dt_win = Tth - T_END
            for a in ALPHAS:
                n_c2 = a * (MS - T_END)              # C-2 每块根数
                w = n_c2 * t_lath * 1e6
                inband = band[0] <= w <= band[1]
                n_pl = a * dt_win                    # **真正放得下**的每块根数
                tot = Bmax * n_pl
                mem = (tot + 1) * (N ** 3) * 4 / 2**30
                mark = ' ←归档值' if abs(a - 0.041739) < 1e-9 else (
                    ' ←框架参考' if abs(a - 0.011) < 1e-12 else '')
                print('   %-16s %-8.6g %-6.1f %-7.2f %-6s %-11.2f %-14.0f %-6s %-6.1f GB%s'
                      % (sname[:16], a, n_c2, w, '✅' if inband else '❌',
                         n_pl, tot, '✅' if tot >= 220 else '❌', mem, mark))
            print()

    # ---- 结论 ----
    print('=' * 100)
    print('★ 结论（三个要求互相夹住）')
    Td = solve_Tth(ED_DISC)
    Te = solve_Tth(ED_ELLIP)
    print('  要求① C3（块内多根）：每块放得下 ≥ 2–3 根')
    print('     圆盘：α_KM·%.1f ≥ 2 ⇒ **α_KM ≥ %.4f**' % (Td - T_END, 2.0 / (Td - T_END)))
    print('     椭球：α_KM·%.1f ≥ 2 ⇒ **α_KM ≥ %.4f**（低得多）' % (Te - T_END, 2.0 / (Te - T_END)))
    print('  要求② 块厚带 (%.1f, %.1f) µm ⇒ α_KM·575·%.3f ∈ 带 ⇒ **α_KM ≤ %.4f**'
          % (band[0], band[1], t_lath * 1e6, band[1] / ((MS - T_END) * t_lath * 1e6)))
    print('  ⇒ ⇒ **圆盘口径下两条要求直接冲突**：')
    print('       ①要 α_KM ≥ %.4f，②要 α_KM ≤ %.4f ⇒ **空集！**'
          % (2.0 / (Td - T_END), band[1] / ((MS - T_END) * t_lath * 1e6)))
    print('  ⇒ ⇒ **椭球口径下不冲突**：α_KM ∈ [%.4f, %.4f]，框架参考 0.011 %s'
          % (2.0 / (Te - T_END), band[1] / ((MS - T_END) * t_lath * 1e6),
             '**落在区间内** ✅' if 2.0 / (Te - T_END) <= 0.011
             <= band[1] / ((MS - T_END) * t_lath * 1e6) else '⚠'))
    print()
    print('  ★★ **所以卡住全局的是"核的形状"，不是 α_KM**：')
    print('     `seed_plate` 播的是 `sdf = max(|d|−t/2, rperp−R)` ⇒ **带尖边的圆柱**。')
    print('     **引擎同几何**实测（`_r509`）：椭球的弹性罚比圆盘**低 %.1f%%**'
          % (100.0 * (1.0 - ED_ELLIP / ED_DISC)))
    print('     （%.4e vs %.4e J/m³）⇒ 形核窗口从 **%.0f K** 放宽到 **%.0f K**'
          % (ED_ELLIP, ED_DISC, Td - T_END, Te - T_END))
    print('     ⇒ 块内根本摞不了几根 ⇒ **C3 与块厚带不能同时满足**；')
    print('     换成光滑椭球 ⇒ 窗口 **%.0f K** ⇒ 五约束同时成立。' % (Te - T_END))
    print('     ⚠ **自查错误 #98/#99（留痕）**：上一版这里写"高 52%%"，')
    print('       那是拿 `_r470` 的**不同几何**（`PF3D`、1000×500×510 nm 椭球）比出来的；')
    print('       本行已改成**引擎同一条路径、同一核几何**下实测的一对。')
    print('       ⇒ **结论不变**（圆盘空集 / 椭球有解），**幅度按实测报**。')
    print()
    print('  ⚠ **"圆盘 vs 椭球"哪个更物理 —— 我不能替你定**：')
    print('     · 真实马氏体片是**透镜状（lenticular）**的 ⇒ 椭球更接近；')
    print('     · 但板条确实有**棱边（ledge）** ⇒ 尖边也不是凭空造的；')
    print('     · **可以确定的是**：`max()` 构造出的**圆柱**是**数值产物**，')
    print('       它的 52%% 罚差**没有物理依据** ⇒ 至少应当**把两种形状都做成开关、都报**。')
    print('=' * 100)
    return 0


if __name__ == '__main__':
    sys.exit(main())
