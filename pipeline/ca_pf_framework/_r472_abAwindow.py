#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R472 —— **对生长窗口（N6）预测的实时检验**：`dry_abA` 的 `Vt` 在越过 `T*` 之后有没有回升？

## 预测（`_r470_growthwindow.py`，已写死）

* 门槛 `T* = 641.7 K`；`dry_abA` 的 `q = 2.3524e6 K/s`、`T_start = 849.04 K`
  ⇒ **越过 `T*` 的时刻 `t* = (849.04 − 641.7)/2.3524e6 = 8.8146e-5 s`**。
* **预测**：`t_s < t*` 时 `ΔG_v < |ed|` ⇒ 净驱动力为负 ⇒ **`Vt` 应下降**；
  `t_s > t*` 之后 `ΔG_v > |ed|` ⇒ **`Vt` 应止跌回升**。

## 预登记判据（**先写死，且必须能失败**）

* **P1（窗口外）**：`t_s < t*` 的行里，`Vt` 的**末段**（最后 20% 行）应**低于**其首段
  ⇒ 即"冷够之前确实在缩"。
* **P2（窗口内）**：`t_s > t*` 的行里，`Vt` 应**出现回升**：
  `max(Vt after t*) > min(Vt after t*)` 且 `Vt(末) > Vt(t* 处)`。
* **P3（负对照，必须能失败）**：把门槛故意取错 **+100 K**（`T*+100 = 741.7 K`）
  ⇒ 按这个错门槛，`t*` 会提前很多，于是"窗口内回升"应当**不明显/不成立**
  ⇒ 若错门槛也给"回升成立"，说明本判据**分不开对错门槛** ⇒ 结果不可信。
* ⚠ **数据还在增长**（abA 在跑）⇒ 本脚本读的是**快照式**读数，
  ⚠ 必须用 `read_rows` 反复读到稳定（9p 缓存陷阱，AGENTS §3.6）。

用法：`python3 _r472_abAwindow.py`
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_km as KM                                    # noqa: E402
from _r463_reinitcount import read_rows                     # noqa: E402
from _r470_growthwindow import E_EL_J, HALF_AXES_NM         # noqa: E402

Q_ABA = 2.3524e6
T_START = 849.04
T_END = 298.0


def t_star_for(Tstar):
    return (T_START - Tstar) / Q_ABA


def main():
    p = os.path.join('_exp/_bk_mb', 'dry_abA', 'series.csv')
    rows = read_rows(p)
    if not rows:
        print('✗ 读不到 %s' % p)
        return 2
    hdr = rows[0].split(',')
    ix = {h: i for i, h in enumerate(hdr)}
    ts, Vt, nreg, nslab = [], [], [], []
    for ln in rows[1:]:
        c = ln.split(',')
        if len(c) < len(hdr):
            continue
        try:
            ts.append(float(c[ix['t_s']]))
            Vt.append(float(c[ix['Vt']]))
            nreg.append(float(c[ix['nreg_used']]))
            nslab.append(float(c[ix['nslab_n']]))
        except ValueError:
            continue
    ts = np.array(ts); Vt = np.array(Vt); nreg = np.array(nreg); nslab = np.array(nslab)
    if len(ts) < 10:
        print('行数太少（%d）' % len(ts))
        return 2

    # 板条弹性能密度（与 _r470 同口径，**直接向它要，不重算**）
    V_m3 = (4.0 / 3.0) * np.pi * (HALF_AXES_NM[0] * 1e-9) * \
        (HALF_AXES_NM[1] * 1e-9) * (HALF_AXES_NM[2] * 1e-9)
    ed = E_EL_J / V_m3
    # 门槛 T*：直接向 KM 求根（与 _r470 同一判据）
    lo, hi = T_END, 1144.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if float(KM.drive_of_T(mid, KM.T0_TI64, KM.DS_REF)) > ed:
            lo = mid
        else:
            hi = mid
    Tstar = hi
    print('=' * 78)
    print('R472  生长窗口对 `dry_abA` 的实时检验')
    print('=' * 78)
    print('  |ed| = %.6e J/m³   T* = %.2f K' % (ed, Tstar))
    print('  判据前提核对 ΔG_v(T*) = %.6e（相对差 %.2e）'
          % (float(KM.drive_of_T(Tstar, KM.T0_TI64, KM.DS_REF)),
             abs(float(KM.drive_of_T(Tstar, KM.T0_TI64, KM.DS_REF)) - ed) / ed))
    print()

    def report(Tstar_, label):
        tst = t_star_for(Tstar_)
        m_out = ts < tst
        m_in = ts >= tst
        print('  ── %s（T* = %.1f K ⇒ t* = %.4e s）──' % (label, Tstar_, tst))
        print('     窗口外 %d 行（t_s < t*），窗口内 %d 行' % (m_out.sum(), m_in.sum()))
        if m_out.sum() >= 5:
            Vo = Vt[m_out]
            k = max(len(Vo) // 5, 1)
            print('     P1 窗口外：首段 Vt 均 %.4e → 末段 %.4e   %s'
                  % (Vo[:k].mean(), Vo[-k:].mean(),
                     '✅ 在缩' if Vo[-k:].mean() < Vo[:k].mean() else '❌ 没缩'))
        else:
            print('     P1 窗口外：行数不足')
        if m_in.sum() >= 5:
            Vi = Vt[m_in]
            v0, vmax, vmin, v1 = Vi[0], Vi.max(), Vi.min(), Vi[-1]
            ok = (v1 > v0) and (vmax > vmin)
            print('     P2 窗口内：Vt(首)=%.4e  min=%.4e  max=%.4e  Vt(末)=%.4e   %s'
                  % (v0, vmin, vmax, v1, '✅ 回升' if ok else '❌ 未回升'))
        else:
            print('     P2 窗口内：行数不足（还没跑到 t*？）')
        print()
        return (m_out, m_in, tst)

    m_out, m_in, tst = report(Tstar, '真门槛')
    report(Tstar + 100.0, '负对照（门槛故意取错 +100 K）')

    # 明细
    print('  ── 明细（每 ~10 行取 1）──')
    print('     step   t_s        T(K)   ΔG_v       ΔG_v/|ed|  Vt          nreg nslab')
    for i in range(0, len(ts), max(len(ts) // 25, 1)):
        T = float(KM.linear_cool(T_START, T_END, (T_START - T_END) / Q_ABA)(ts[i]))
        dg = float(KM.drive_of_T(T, KM.T0_TI64, KM.DS_REF))
        mark = '  <-- 越过 T*' if (i > 0 and ts[i - 1] < tst <= ts[i]) else ''
        print('     %5d  %.4e  %6.1f  %.4e  %6.3f    %.4e  %4d %3d%s'
              % (i * max(len(ts) // 25, 1), ts[i], T, dg, dg / ed, Vt[i],
                 int(nreg[i]), int(nslab[i]), mark))
    print()
    print('=' * 78)
    print('★ 判读规则（预登记）：')
    print('  · P1 ✅ + P2 ✅ + 负对照 P2 ❌  ⇒ **生长窗口被证实**')
    print('  · P1 ✅ + P2 ❌                  ⇒ **窗口预测未复现**（须查，不得硬说成立）')
    print('  · 负对照 P2 也 ✅                ⇒ **判据分不开对错门槛 ⇒ 本结果不可信**')
    print('=' * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())
