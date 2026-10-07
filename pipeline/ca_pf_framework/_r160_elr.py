#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r160_elr.py —— ★★ **框架诊断的关键一问**：自协调排布**真的**弹性能更低吗？

## 为什么这是关键

`§112` 定住：**生长竞争通道**不把组织推向自协调（两臂 `r` **都倒退**）。
而 `BLOCK_SELFAC.md §4.1` 自己说："弹性变体选择**不**导向自协调 ⇒ **要加界面能/`γ_el` 通道**"。

**但在"加通道"之前必须先回答**：**弹性能到底认不认自协调？**
* 若 `E_el`（强度量 `E_el/Vt`）**随 `r` 上升而上升** ⇒ **弹性能是认的**
  ⇒ 问题是"**动力学被别的东西盖住了**"（`df` 是常数 350 MPa，与变体无关；碰撞是几何的）
  ⇒ 补法不是"加通道"，而是**让已有的弹性项在选择上起作用**；
* 若 `E_el/Vt` **与 `r` 无关** ⇒ **弹性能根本不认 `r`** ⇒ `r` 这个判据与能量脱节
  ⇒ 那才需要**换判据**或**补通道**。

## 做法（**臂内**看，避免跨臂混杂）

对每条臂，逐步取 `(r_selfac, E_el_J/Vt)`，做**臂内**相关。
臂内 `r` 在动（`§112` 实测两臂的 `r` 都在升）⇒ 能看"`E_el/Vt` 跟不跟着动"。

⚠ **口径**：`E_el_J` 是**广延量**、`Vt` 是**广延量** ⇒ 必须用**比值**（`§84` 规程③）。
⚠ 只报**相关**，不建因果。
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
ARMS = [('saOddG', 'ODD {1,3,5,7,9,11}（下界 0）'),
        ('saSet2', 'SET2 {1,2,3,4,7,8}（下界 0.4828）'),
        ('saOddGE0', 'ODD + el=0（对照）'),
        ('saSet2E0', 'SET2 + el=0（对照）')]


def load(tag):
    p = os.path.join(MB, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p)))
    st, r, E, V = [], [], [], []
    for x in rows:
        try:
            st.append(float(x['step']))
            r.append(float(x['r_selfac']))
            E.append(float(x['E_el_J']))
            V.append(float(x['Vt']))
        except (KeyError, ValueError):
            continue
    return (np.array(st), np.array(r), np.array(E), np.array(V))


def main():
    print('=' * 108)
    print('_r160 —— **弹性能认不认自协调？**（臂内看 `E_el/Vt` 与 `r_selfac` 的关系）')
    print('=' * 108)
    print('  %-10s %-7s %-11s %-11s %-13s %-13s %s'
          % ('臂', '步数', 'r 初', 'r 末', 'E_el/Vt 初', 'E_el/Vt 末', '臂内相关'))
    for tag, lab in ARMS:
        d = load(tag)
        if d is None or len(d[0]) < 3:
            print('  %-10s （数据不足）' % tag)
            continue
        st, r, E, V = d
        ed = E / np.maximum(V, 1e-300)
        # 臂内相关（r 与 E_el/Vt）
        c = float(np.corrcoef(r, ed)[0, 1]) if len(r) > 2 else float('nan')
        print('  %-10s %-7d %-11.4f %-11.4f %-13.4g %-13.4g %+.4f'
              % (tag, len(st), r[0], r[-1], ed[0], ed[-1], c))
    print()
    print('  ---- 逐步明细（`saOddG` / `saSet2`，有 el 的两臂）----')
    for tag in ('saOddG', 'saSet2'):
        d = load(tag)
        if d is None:
            continue
        st, r, E, V = d
        ed = E / np.maximum(V, 1e-300)
        print('  ### %s' % tag)
        print('     %-7s %-11s %-13s %s' % ('step', 'r_selfac', 'E_el/Vt', '（相对首行）'))
        for i in range(0, len(st), max(1, len(st) // 8)):
            print('     %-7d %-11.4f %-13.4g %+.2f%%'
                  % (st[i], r[i], ed[i], 100 * (ed[i] / ed[0] - 1)))
        i = len(st) - 1
        print('     %-7d %-11.4f %-13.4g %+.2f%%   ← 末行'
              % (st[i], r[i], ed[i], 100 * (ed[i] / ed[0] - 1)))
        # 趋势
        sl_r = float(np.polyfit(st, r, 1)[0]) * 100
        sl_e = float(np.polyfit(st, ed, 1)[0]) * 100
        print('     ⇒ `r` 趋势 %+.4f/100步；`E_el/Vt` 趋势 %+.4g/100步 ⇒ %s'
              % (sl_r, sl_e,
                 '**同向（弹性能认自协调）**' if sl_r * sl_e > 0 else
                 '**反向或无关（弹性能不认 `r`）**'))
    print()
    print('  ---- 判读 ----')
    print('  * 若 `E_el/Vt` **随 `r` 同向上升** ⇒ 弹性能**认**自协调')
    print('    ⇒ 缺的不是"能量通道"，而是"**动力学没把它用起来**"')
    print('    （`df = 350 MPa` 是**与变体无关的常数**，而碰撞是几何的）。')
    print('  * 若 `E_el/Vt` 与 `r` **无关或反向** ⇒ `r` 与能量**脱节** ⇒ 判据本身要换。')
    print('  ⚠ 只报相关；跨臂比绝对值有混杂（`Vt`/形貌/步数），本脚本主要看**臂内**。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
