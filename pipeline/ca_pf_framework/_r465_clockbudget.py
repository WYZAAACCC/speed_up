#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R465 —— **降温时钟预算**：各臂实际走完了多少冷却？（任务(1) 的 S12 取证）

## 为什么这个量是本轮新发现的关键

`_bk_exp.py:1288-1298` 的 athermal 主循环是：

    g.t += dt ; g.set_T(g.T_of_t(g.t)) ; dt = 0.15·dx/(MOB·max(_df_now,1e-300))

⇒ **"物理时刻" `t` 是由 CFL 稳定步长 `dt` 累加出来的**。而时间表
`KM.linear_cool(T_start, T_end, t_cool)` 在 `t ≥ t_cool` 之后**恒为 `T_end`**
（`windowB_km.py:150-156`，本轮核对过代码）。

**⇒ 于是有一个从来没被算过的账：一次跑到底走完了多少冷却？**
若 `t_s(末) < t_cool`，那么：
  · 温度**从没降到 T_end**；
  · 驱动力**从没到过室温那一档**（`df(298 K) = 3.512e8`）；
  · 而成功判据 C5（"块填满整个盒子"）依赖的正是"后期大驱动力"。
⇒ **"填不满"可能根本不是形核律或盒长的问题，而是"冷却没走完"。**

## 口径（全部给出来源，不猜）

| 量 | 来源 |
|---|---|
| `T_start` | `_bk_exp.py:555-556`：`a.T_start > 0` 则用它，否则 `CL.T_start_of_clock(alpha)` = `M_s − 1/α_KM` |
| `M_s` | `windowB_km.py:93` `M_S_TI64 = 873.0 K` |
| `q`（冷速） | `_bk_exp.py:567-571`：`a.cool_rate > 0` 则用它；否则 `C-3 上界 × cool_ratio` |
| `t_cool` | `KM.linear_cool(...).t_cool` = `(T_start − T_end)/q`（**直接向函数要，不自己算**） |
| `t_s(末)` | `series.csv` 的 `t_s` 列（引擎每步累加） |

## 预登记的自检（**先写死、必须能失败**）

* **T1**：`linear_cool(849.04, 298.0, (849.04−298.0)/2.3524e6).t_cool`
  必须等于 `551.04/2.3524e6 = 2.34235e-4 s`（相对误差 ≤ 1e-9）。
* **T2（负对照）**：若我把 `t_cool` 喂成 `(T_end − T_start)/q`（**符号反**），
  `linear_cool` 会 raise `ValueError`（`t_cool 必须 > 0`）⇒ 必须捕获到。
  **捕获不到 ⇒ 量具对"符号反"无感 ⇒ 不可信。**
* **T3（口径自证）**：对每一个臂，用 `t_s` 反算的 ΔT 必须与
  `T_start − T_of_t(t_s)` 一致（相对误差 ≤ 1e-6）—— 即"我的反算"与"引擎自己的时间表"
  是同一个东西。**这一条是对"我有没有用错公式"的独立核对。**

用法：
    python3 _r465_clockbudget.py                 # 扫 _exp/_bk_mb 下所有臂
    python3 _r465_clockbudget.py --tag dry_abA
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_km as KM            # noqa: E402
import windowB_closure as CL       # noqa: E402
from _r463_reinitcount import parse, read_rows   # noqa: E402

TOL_T1 = 1e-9
TOL_T3 = 1e-6


def selftest(verbose=True):
    ok = True

    def _s(x):
        if verbose:
            print(x)

    _s('=' * 78)
    _s('R465 自检（预登记）')
    _s('=' * 78)
    Ts, Te, q = 849.04, 298.0, 2.3524e6
    tc_expect = (Ts - Te) / q
    f = KM.linear_cool(Ts, Te, tc_expect)
    e1 = abs(f.t_cool - tc_expect) / tc_expect
    ok1 = e1 <= TOL_T1
    _s('T1 t_cool 闭式      : 函数给 %.10e  手算 %.10e  相对差 %.2e  %s'
       % (f.t_cool, tc_expect, e1, 'PASS' if ok1 else '❌ FAIL'))
    ok &= ok1

    ok2 = False
    try:
        KM.linear_cool(Ts, Te, (Te - Ts) / q)
    except ValueError:
        ok2 = True
    _s('T2 负对照(符号反)   : %s' % ('PASS（确实 raise ValueError）' if ok2
                                     else '❌ FAIL（符号反竟然没报错！）'))
    ok &= ok2

    # T3 的口径自证在 report() 里对每个臂做
    _s('T3 口径自证         : 见每个臂那一行的「口径自证」列')
    _s('-' * 78)
    _s('★ 自检总结论：%s' % ('**PASS ⇒ 量具可信**' if ok else '❌ **FAIL ⇒ 不可信**'))
    _s('=' * 78)
    return ok


def report(tag, root='_exp/_bk_mb'):
    got = parse(tag, root)
    if not got:
        return None
    hdr, recs = got
    idx = {h: i for i, h in enumerate(hdr)}
    # 从 meta.json 拿 exp_args 里的 alpha-km / cool-rate / T-end / T-start
    import json
    mj = os.path.join(root, tag, 'meta.json')
    ea = {}
    if os.path.exists(mj):
        with open(mj) as fh:
            m = json.load(fh)
        ea = m.get('exp_args', {}) or {}
        if not ea and isinstance(m.get('args'), dict):
            ea = m['args']
    alpha = float(ea.get('alpha_km', CL.ALPHA_KM_REF))
    q = float(ea.get('cool_rate', 0.0))
    T_end = float(ea.get('T_end', 298.0))
    T_start_arg = float(ea.get('T_start', 0.0))
    T_start = T_start_arg if T_start_arg > 0 else float(CL.T_start_of_clock(alpha))
    if q <= 0:
        # 非 athermal 或没给冷速 ⇒ 不算
        print('== %-14s  q=%.3e ⇒ 非 athermal 或缺冷速，跳过' % (tag, q))
        return None
    f = KM.linear_cool(T_start, T_end, (T_start - T_end) / q)
    t_cool = f.t_cool

    ts = np.array([r['t_s'] for r in recs])
    steps = np.array([r['step'] for r in recs])
    ts_end = float(ts[-1])
    T_end_reached = float(f(ts_end))
    dT = T_start - T_end_reached
    dT_full = T_start - T_end
    frac = dT / dT_full

    # ---- T3 口径自证：两条独立算法必须一致 ----
    dT_algebra = ts_end * q
    e3 = abs(dT_algebra - dT) / max(abs(dT), 1e-30)
    ok3 = e3 <= TOL_T3

    # 预计走完需要的步数（按实测平均 dt）
    dt_mean = ts_end / max(int(steps[-1]), 1)
    steps_need = t_cool / dt_mean if dt_mean > 0 else float('nan')

    print('== %-14s  α_KM=%.6g  q=%.4e K/s  T_start=%.2f K (T_1)  T_end=%.1f K'
          % (tag, alpha, q, T_start, T_end))
    print('   闭式 t_cool = %.6e s   （= (T_start−T_end)/q）' % t_cool)
    print('   实测 t_s(末)= %.6e s   步数 %d  平均 dt = %.4e s'
          % (ts_end, int(steps[-1]), dt_mean))
    print('   ⇒ 已走完冷却的 **%.2f%%**（ΔT = %.1f / %.1f K）；'
          '当前温度 T = **%.1f K**' % (100 * frac, dT, dT_full, T_end_reached))
    print('   ⇒ 口径自证 T3：t_s·q = %.4f K vs 时间表给 %.4f K，相对差 %.2e  %s'
          % (dT_algebra, dT, e3, '✅' if ok3 else '❌ **不一致！**'))
    if frac >= 1.0:
        print('   ✅ 冷却**已走完**（T 已钳在 T_end）')
    else:
        need = steps_need - int(steps[-1])
        print('   ⚠ **冷却没走完**：按平均 dt 还需 **%.0f 步**（总需 ≈ %.0f 步，'
              '实际跑了 %d 步）' % (need, steps_need, int(steps[-1])))
    # 驱动力对照
    dG_now = float(KM.drive_of_T(T_end_reached, KM.T0_TI64, KM.DS_REF))
    dG_end = float(KM.drive_of_T(T_end, KM.T0_TI64, KM.DS_REF))
    print('   驱动力：当前 df=%.4e  vs  T_end 处 df=%.4e  ⇒ 只拿到 **%.1f%%**'
          % (dG_now, dG_end, 100 * dG_now / dG_end))
    print()
    return dict(tag=tag, frac=frac, T_end_reached=T_end_reached, ok3=bool(ok3),
                steps_need=steps_need, t_cool=t_cool, ts_end=ts_end)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', action='append', default=[])
    ap.add_argument('--root', default='_exp/_bk_mb')
    a = ap.parse_args()
    if not selftest():
        return 2
    print()
    import glob
    tags = a.tag or sorted(os.path.basename(os.path.dirname(p))
                           for p in glob.glob(os.path.join(a.root, '*', 'series.csv')))
    res = []
    for t in tags:
        r = report(t, a.root)
        if r:
            res.append(r)
    if res:
        bad = [r for r in res if not r['ok3']]
        print('=' * 78)
        print('★ 口径自证 T3 全臂汇总：%d/%d 通过%s'
              % (len(res) - len(bad), len(res),
                 '' if not bad else ' ❌ 不通过的臂：%s' % [r['tag'] for r in bad]))
        print('★ **走完冷却的臂**：%s'
              % ([r['tag'] for r in res if r['frac'] >= 1.0] or '**一个都没有**'))
        print('★ **没走完的臂**：%s'
              % ([(r['tag'], '%.1f%%' % (100 * r['frac'])) for r in res if r['frac'] < 1.0]))
        print('=' * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())
