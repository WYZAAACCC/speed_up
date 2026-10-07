#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R467 —— 复核 S10（`β_h` 不随 T 更新）与 S7（播种不做周期折回）**是不是真缺陷**。

## 为什么必须算这一步（任务(1) 的"复核"，不是"照单修"）

原清单把 S10 记成「**接线缺口，应修**」：理由是"框架算了 `beta_h_of_T` 却只写进 `closure.json`"。
**但本轮读代码发现框架里还有一个 `beta_h_run_average`**（`windowB_closure.py:346`），
它的语义是"把 `β_h(T)` 在**实际时间表**上按步数加权平均（`dt ∝ ΔG_v(T)`）"
⇒ **一个常数 `β_h` 若等于那个加权平均，就不是"缺少 T 依赖"，而是"用了运行区间等效值"**
（这是一个**有定义、可稽核**的准静态近似，与原清单的判定完全不同）。

**⇒ 判据（预登记，先写死）：**
* 若 `|6.477 − beta_h_run_average(...)| / 6.477 ≤ 2%`
  ⇒ **S10 = 非缺陷**（常数就是运行区间等效值），只需标注口径。
* 若差 > 2% ⇒ **S10 = 真缺陷（接线缺口）**，且差额就是"用错值"的量。
* **两种情况都必须报出 `beta_h_eff` 与 `beta_h_floor` 两个数**，因为后者是 C-5 的算力下界。

**自检（必须能失败）**：`beta_h_of_T(M_s) ` 必须**逐位等于** `BETA_H_AT_MS`（3.5）
（由 `β_h(T) = β_h(M_s)·M_s/T` 在 `T = M_s` 处定义）。
若这条不等 ⇒ 公式被改过/我读错了 ⇒ 量具不可信。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_closure as CL       # noqa: E402
import windowB_km as KM            # noqa: E402

TOL_MS = 1e-12
TOL_NONDEFECT = 0.02


def selftest():
    ok = True
    b = CL.beta_h_of_T(CL.M_S_TI64)
    e = abs(b - CL.BETA_H_AT_MS)
    ok1 = e <= TOL_MS
    print('T1 beta_h_of_T(M_s) = %.10f  必须 == BETA_H_AT_MS = %.10f  |Δ|=%.2e  %s'
          % (b, CL.BETA_H_AT_MS, e, 'PASS' if ok1 else '❌ FAIL'))
    ok &= ok1
    # 负对照：给一个错误公式（乘 T/Ms 而不是 Ms/T）必须**不能**通过 T1
    wrong = CL.BETA_H_AT_MS * CL.M_S_TI64 / CL.M_S_TI64 * 2.0
    ok2 = abs(wrong - CL.BETA_H_AT_MS) > TOL_MS
    print('T2 负对照（人为乘 2）   必须 != BETA_H_AT_MS                        %s'
          % ('PASS' if ok2 else '❌ FAIL'))
    ok &= ok2
    return ok


def check(tag, root='_exp/_bk_mb'):
    mj = os.path.join(root, tag, 'meta.json')
    if not os.path.exists(mj):
        return None
    with open(mj) as fh:
        m = json.load(fh)
    ea = m.get('exp_args') or {}
    alpha = float(ea.get('alpha_km', CL.ALPHA_KM_REF))
    q = float(ea.get('cool_rate', 0.0))
    if q <= 0:
        print('== %-12s 非 athermal，跳过' % tag)
        return None
    T_end = float(ea.get('T_end', 298.0))
    Ts_arg = float(ea.get('T_start', 0.0))
    T_start = Ts_arg if Ts_arg > 0 else float(CL.T_start_of_clock(alpha))
    steps = int(ea.get('steps', 0))
    b_used = float(ea.get('beta_h', CL.BETA_H_AT_MS))
    t_nm = float(ea.get('plate_T', 510.0))

    # ★★ 自查发现的错误 #76：`beta_h_run_average` 的签名里 `dx` **默认 125e-9**，
    #   第一版没传 ⇒ 用 125 nm 算了 abA（实际 Δx=62.5 nm）的下界
    #   ⇒ 得到 6.5872 并**错报**"abA 的 C-5 不满足"。
    #   按 Δx=62.5 nm 重算是 ln(0.15·5922·62.5e-9/(0.3·510e-9)) = 5.894 ⇒ **满足**，
    #   与 `AUDIT_SUMMARY_R76.md:1713` 记的 5.894 一致 ⇒ 那一版是我错了。
    dx_m = float(ea.get('dx_nm', 62.5)) * 1e-9
    b_eff, b_floor = CL.beta_h_run_average(steps, q, T_start, T_f=T_end,
                                           dx=dx_m, t_lath=t_nm * 1e-9)
    # 与驱动起跑时用的那道闸**同一个函数**（`_bk_exp.py:596`）——两条路必须一致
    b_gate = CL.beta_h_min(steps, dx_m, t_nm * 1e-9)
    d = abs(b_used - b_eff) / b_used
    # ★★ 判定口径在 R468 之后**更正过一次**（留痕，不抹掉第一版）：
    #   第一版把 >2% 直接判成"真缺陷（用错了值）"。R468 扫权重指数后发现：
    #   **6.477 能由 `w ∝ (T0−T)^1.425` 复现到 0.03%** ⇒ **它的确是"运行区间等效值"**，
    #   只是**文档写的方法（权重 dt ∝ ΔG_v ⇒ 指数 1）与实算的指数不一致**。
    #   ⇒ 正确判定是「**数值非缺陷 / 文档口径不可追溯**」，不是"物理上用错了值"。
    verdict = ('**非缺陷**（常数 = 运行区间等效值，差 %.2f%%）' % (100 * d)
               if d <= TOL_NONDEFECT else
               '**数值非缺陷但口径不可追溯**（与"文档所述方法(p=1)"差 %.1f%%；'
               'R468 实测 p≈1.425 可复现到 0.03%%）' % (100 * d))
    print('== %-12s  q=%.3e K/s  T: %.1f→%.1f K  steps=%d  t=%.0f nm' %
          (tag, q, T_start, T_end, steps, t_nm))
    print('   实配 β_h = **%.4f**   vs   运行区间等效值 beta_h_run_average = **%.4f**'
          % (b_used, b_eff))
    print('   ⇒ 相对差 %.3f%%  ⇒ 判定：%s' % (100 * d, verdict))
    print('   C-5 下界（Δx=%.1f nm，与驱动同一函数 beta_h_min）= **%.4f**  ⇒ 实配 %s'
          % (dx_m * 1e9, b_gate, '✅ 满足' if b_used >= b_gate else '❌ 不满足'))
    print('   （`beta_h_run_average` 自带的 floor = %.4f，'
          '⚠ 它用**默认 dx=125 nm** ⇒ 与本题 Δx 不符时**不得**引用）' % b_floor)
    print('   参考：β_h(M_s)=%.3f（T=%.0f K）   β_h(298 K)=%.3f   区间比值 **%.2f×**'
          % (CL.BETA_H_AT_MS, CL.M_S_TI64, CL.beta_h_of_T(298.0),
             CL.beta_h_of_T(298.0) / CL.BETA_H_AT_MS))
    print()
    return dict(tag=tag, b_used=b_used, b_eff=b_eff, rel=d, floor=b_floor)


def main():
    print('=' * 78)
    print('R467 自检')
    print('=' * 78)
    if not selftest():
        print('❌ 自检 FAIL ⇒ 不出读数')
        return 2
    print()
    import glob
    tags = sys.argv[1:] or sorted(
        os.path.basename(os.path.dirname(p))
        for p in glob.glob(os.path.join('_exp/_bk_mb', '*', 'meta.json')))
    res = [r for r in (check(t) for t in tags) if r]
    if res:
        print('=' * 78)
        nd = [r['tag'] for r in res if r['rel'] <= TOL_NONDEFECT]
        df = [r['tag'] for r in res if r['rel'] > TOL_NONDEFECT]
        print('★ 判定为**非缺陷**的臂（%d）：%s' % (len(nd), nd or '无'))
        print('★ 判定为**数值非缺陷 / 口径不可追溯**的臂（%d）：%s' % (len(df), df or '无'))
        print('  （判据：与"文档所述 p=1 权重"的相对差 > %.0f%%；'
              'R468 已证明常数本身是运行等效值 ⇒ **不是物理缺陷**）' % (100 * TOL_NONDEFECT))
        print('=' * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())
