#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r720_calib_chain.py —— **S5：`R712 §4.4` 的四步标定链**（含**量纲自检**）。

## 为什么写它
`R712_REPAIR_SPEC.md §4.4` 给出一条**唯一可执行**的标定路径（`D-2 = A` Liu 2015 线性位点密度律）：

```
第 1 步  实测板条几何：厚 t、长 L、宽 W                     ← [待标定]（用户指示暂不定稿）
第 2 步  目标位点数密度   n_final = 1/(t·L·W)                [m^-3]
第 3 步  起始位点密度     N(M_s)  = 1/V_prior_beta           （prior-beta 由 Window A 给）
第 4 步  斜率             a = [n_final − N(M_s)] / (T_end − M_s)   [m^-3·K^-1]
```
以及推论（写进实现的语义）：
```
N(T) ≈ a·(T − M_s),  a = n_final/(T_end − M_s)
盒内事件数          N_ev  = n_final · V_box
每个核的过冷度增量   dT_step = 1/(a · V_box)
档数                N_stage = N_ev
```

## ⚠ 本脚本的**用途边界**（不许越界）
* 它**只做算术 + 量纲 + 恒等式自检**，**不测量几何**、**不跑仿真**、**不改主代码**。
* 第 1 步的 `t/L/W` **必须由外部给**（用户指示"板条几何不定稿"⇒ 本脚本**不内置猜测值**）。
* 第 3 步的 `V_prior_beta` 在本项目里**盒 ≪ 晶粒**⇒ 可忽略（`R712 §4.4` 已验：
  10 µm 晶粒占 9.6e-4、100 µm 占 9.6e-7）⇒ 本脚本**默认按可忽略处理，但把比例打印出来**。

## ★ 量纲自检（`R712 §0.3` 的教训 E6/E4：µm³→m³ 曾写错 1000 倍；`α_KM`(K⁻¹) 曾与
##   `a`(m⁻³K⁻¹) 混用）—— 本脚本对**每一个**量做单位标注与断言：

| 量 | 单位 | 断言 |
|---|---|---|
| `t`,`L`,`W` | m | 必须 > 0；输入按 µm 给，**显式换算** |
| `n_final` | m⁻³ | `= 1/(t·L·W)`，量纲 `m/(m³·m)` 自洽 |
| `V_box` | m³ | 输入按 µm 给，换算 **1 µm³ = 1e-18 m³**（★ E6 就是这个 1000 倍） |
| `N_ev` | 无量纲 | `n_final · V_box` |
| `a` | m⁻³·K⁻¹ | `n_final/(T_end−M_s)` |
| `dT_step` | K | `1/(a·V_box)` ⇒ 量纲 `1/(m⁻³K⁻¹·m³)` = K ✅ |
| `N_stage` | 无量纲 | **必须 == `N_ev`**（档数=事件数） |
| `α_KM` | **K⁻¹** | ⚠ **只打印、不参与任何计算** —— 与 `a` **不可比**（`R712 §4.5`） |

## 用法
    python3 _r720_calib_chain.py --t-um 0.22 --L-um 2.2 --W-um 0.55 \\
        --T-end 298 --Ms 873 --V-box-um3 0.216 --prior-d-um 10
    python3 _r720_calib_chain.py --selftest        # 只跑量纲自检（不给几何）
"""
import argparse
import sys

UM = 1e-6
UM3 = 1e-18          # ★ 1 µm³ = 1e-18 m³  （E6：曾写成 1e-15，差 1000 倍）


def _check(cond, msg):
    if not cond:
        print('  ⛔ 量纲/自洽断言 FAIL：%s' % msg)
        return False
    print('  ✅ %s' % msg)
    return True


def selftest():
    print('=' * 96)
    print('量纲自检（不依赖任何几何输入）')
    print('=' * 96)
    ok = True
    ok &= _check(abs(UM3 - 1e-18) < 1e-30,
                 '1 µm³ = 1e-18 m³（E6 的坑：曾写成 1e-15，差 1000 倍）')
    ok &= _check(abs(UM ** 3 - UM3) < 1e-30, '1 µm = 1e-6 m ⇒ (1e-6)³ = 1e-18 m³')
    # dT_step 的量纲：1/(a·V) = 1/(m^-3 K^-1 · m^3) = K
    a_, V_ = 1.7e14, 2.16e-16
    dT_ = 1.0 / (a_ * V_)
    ok &= _check(abs(dT_ * (a_ * V_) - 1.0) < 1e-12,
                 'dT_step = 1/(a·V_box) 与 a·V_box·dT_step = 1 互逆')
    # α_KM 与 a 不是同一个量
    ok &= _check(True, 'α_KM（K⁻¹，管**分数**）与 a（m⁻³K⁻¹，管**数密度**）'
                       '**量纲不同 ⇒ 不可比大小**（`R712 §4.5`）')
    print('⇒ %s' % ('全部通过' if ok else '**有 FAIL**'))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--t-um', type=float, help='板条**厚** t（µm）')
    ap.add_argument('--L-um', type=float, help='板条**长** L（µm）')
    ap.add_argument('--W-um', type=float, help='板条**宽** W（µm）')
    ap.add_argument('--T-end', type=float, default=298.0, help='终温（K）')
    ap.add_argument('--Ms', type=float, default=873.0, help='M_s（K）')
    ap.add_argument('--V-box-um3', type=float, default=216.0, help='仿真盒体积（µm³）')
    ap.add_argument('--prior-d-um', type=float, default=10.0, help='prior-β 晶粒直径（µm）')
    ap.add_argument('--alpha-km', type=float, default=0.041739,
                    help='KM 分数律系数（K⁻¹）—— **只打印，不参与计算**')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()

    if a.selftest or a.t_um is None:
        if not a.selftest and a.t_um is None:
            print('⚠ 未给几何（--t-um/--L-um/--W-um）⇒ 只跑量纲自检')
        ok = selftest()
        if a.selftest:
            return 0 if ok else 1
        print()

    if a.t_um is None or a.L_um is None or a.W_um is None:
        print('⛔ 第 1 步的几何未给全 ⇒ **停在这里**（`R712 §10.4`：`t/L/W` 是 `[待标定]`，'
              '不得由脚本猜）')
        return 0

    ok = selftest()
    print()
    print('=' * 96)
    print('`R712 §4.4` 四步标定链')
    print('=' * 96)
    print('【第 1 步】实测板条几何（**外部输入**，脚本不测量）')
    print('   t = %.4g µm = %.6g m   [m]' % (a.t_um, a.t_um * UM))
    print('   L = %.4g µm = %.6g m   [m]' % (a.L_um, a.L_um * UM))
    print('   W = %.4g µm = %.6g m   [m]' % (a.W_um, a.W_um * UM))
    t, L, W = a.t_um * UM, a.L_um * UM, a.W_um * UM
    ok &= _check(t > 0 and L > 0 and W > 0, '三个几何量都 > 0')

    print('\n【第 2 步】目标位点数密度')
    n_final = 1.0 / (t * L * W)
    print('   n_final = 1/(t·L·W) = %.6e m^-3      [m^-3]' % n_final)
    ok &= _check(n_final > 0, 'n_final > 0')
    print('   （等价：单根板条体积 = %.6e m³ = %.6e µm³）'
          % (t * L * W, t * L * W / UM3))

    print('\n【第 3 步】起始位点密度 N(M_s) = 1/V_prior-β')
    d = a.prior_d_um * UM
    V_g = (4.0 / 3.0) * 3.141592653589793 * (d / 2.0) ** 3
    N_Ms = 1.0 / V_g
    print('   prior-β 直径 = %.4g µm ⇒ V = %.6e m³ = %.6e µm³'
          % (a.prior_d_um, V_g, V_g / UM3))
    print('   N(M_s) = %.6e m^-3                [m^-3]' % N_Ms)
    ratio = N_Ms / n_final
    print('   ★ N(M_s)/n_final = **%.3e**（占 %.4g%%）' % (ratio, ratio * 100))
    if ratio < 1e-3:
        print('   ⇒ ✅ **可忽略**（盒 ≪ 晶粒）⇒ 后续按 `a = n_final/(T_end−M_s)` 取')
    else:
        print('   ⇒ ⚠ **不可忽略** —— 必须用 `a = [n_final − N(M_s)]/(T_end − M_s)`')

    print('\n【第 4 步】斜率 a')
    dT_win = a.T_end - a.Ms
    print('   T_end = %.2f K   M_s = %.2f K   ⇒ ΔT_win = T_end − M_s = %.2f K   [K]'
          % (a.T_end, a.Ms, dT_win))
    ok &= _check(abs(dT_win) > 1e-9, 'ΔT_win ≠ 0')
    a_slope_ign = n_final / dT_win
    a_slope_full = (n_final - N_Ms) / dT_win
    print('   a（忽略 N(M_s)）= %.6e m^-3·K^-1      [m^-3·K^-1]' % a_slope_ign)
    print('   a（含 N(M_s)）  = %.6e m^-3·K^-1' % a_slope_full)
    print('   两者相对差 = %.3e（N(M_s) 可忽略时该差 → 0）'
          % (abs(a_slope_full - a_slope_ign) / abs(a_slope_ign)))

    print('\n【推论】盒内事件数与档数')
    V_box = a.V_box_um3 * UM3
    N_ev = n_final * V_box
    dT_step = 1.0 / (a_slope_ign * V_box)
    print('   V_box = %.6g µm³ = %.6e m³          [m³]' % (a.V_box_um3, V_box))
    print('   N_ev  = n_final·V_box = **%.6g**       [无量纲]' % N_ev)
    print('   dT_step = 1/(a·V_box) = **%.6g K**     [K]' % dT_step)
    print('   N_stage = N_ev        = **%.6g**' % N_ev)

    print('\n【★ 恒等式自检】（`R712 §9.1` 的 `test_dT_step_consistency`）')
    lhs = dT_step * N_ev
    rel = abs(lhs - dT_win) / abs(dT_win)
    ok &= _check(rel < 1e-12, 'dT_step·N_stage == T_end − M_s  '
                              '（实测 %.12g vs %.12g，相对差 %.3e）' % (lhs, dT_win, rel))

    print('\n【量纲对照表】（★ `R712 §4.5`：**不同量不可比大小**）')
    print('   %-14s %-14s %s' % ('量', '单位', '作用的量'))
    print('   %-14s %-14s %s' % ('a（本脚本）', 'm^-3·K^-1', '**数密度** N = N(M_s)+a(T−M_s)'))
    print('   %-14s %-14s %s' % ('α_KM（生产）', 'K^-1', '**分数** f = 1−exp(−α_KM·ΔT)'))
    print('   ⚠ 生产现值 α_KM = %.6g K^-1 —— **只打印，不参与上面任何计算**' % a.alpha_km)
    print('   ⚠ `R712 §4.5` 实测：现状 `_tgt = min(B·n_blk, nv)` **正是两条混用**'
          '（`n_blk` 来自 KM 式、`B` 来自手写）⇒ 本脚本**不复制那个混用**')
    print()
    print('⇒ %s' % ('**全部断言通过**' if ok else '**有 FAIL —— 见上**'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
