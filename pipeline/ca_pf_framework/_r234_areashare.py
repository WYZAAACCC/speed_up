#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r234_areashare.py —— 用**已验证的量具** `measure_state` 离线算**三类界面面积占比**。

## 为什么必须离线重算（`§142`）

`§141.1` 报的 "F2 只占总界面 ~10%" 来自引擎诊断的 `(karr, larr)` **配对分类**；
而 `_r233` 的探针显示 **`karr>0` 时 `larr` 恒为 0** ⇒ 那套分类**不是**
`region`-based 的 F1/F2/F3 几何分类 ⇒ **两者不可直接比**（这就是 Q-16）。

**⇒ 正确做法**：用 `_bk_measure.measure_state`（**已过 A-1…A-5 正对照**，`§139.2`）
从归档快照的 `region` 直接算 `f1_area` / `f2_area` / `f3_area`。

⚠ **这正是用户要求的场景**：「即使测量工具有问题，之后也能使用新的测量工具
重新测量得到正确的结果」—— 归档快照只存 `region`，而 `measure_state` 只需要 `region`
⇒ **可以直接在旧数据上重测。**
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _bk_measure as BM  # noqa: E402

MB = os.path.join(HERE, '_exp', '_bk_mb')
ARMS = ('saSet2', 'saSet2F2', 'saOddG', 'saOddGF2', 'mb2fp10', 'sgG')


def main():
    print('=' * 108)
    print('_r234 —— 三类界面**面积占比**（离线重算，量具已过 A-1…A-5 正对照）')
    print('=' * 108)
    for arm in ARMS:
        d = os.path.join(MB, 'dry_' + arm)
        fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
        if not fs:
            print('  %-12s (无快照)' % arm)
            continue
        mf = os.path.join(d, 'meta.json')
        if not os.path.exists(mf):
            print('  %-12s (无 meta)' % arm)
            continue
        m = json.load(open(mf))
        dx = float(m.get('dx_nm', 62.5)) * 1e-9
        laths = [int(x) for x in m.get('laths', [])]
        vmap = {i + 1: laths[i] for i in range(len(laths))}
        print()
        print('  ## `%s`  dx=%.1f nm  laths=%s' % (arm, dx * 1e9, laths))
        print('     %-16s %-11s %-11s %-11s | %s'
              % ('快照', 'F1[µm²]', 'F2[µm²]', 'F3[µm²]', '占比 F1 / F2 / F3'))
        for f in fs[::max(1, len(fs) // 5)] + [fs[-1]]:
            z = np.load(f, allow_pickle=True)
            if 'region' not in z:
                continue
            reg = z['region']
            n_hab = np.asarray(z['n_hab'], float) if 'n_hab' in z else \
                np.array([1.0, 0.0, 0.0])
            w_ax = np.asarray(z['w_ax'], float) if 'w_ax' in z else \
                np.array([0.0, 1.0, 0.0])
            a_ax = np.asarray(z['a_ax'], float) if 'a_ax' in z else \
                np.array([1.0, 0.0, 0.0])
            try:
                r = BM.measure_state(reg, dx, n_hab, w_ax=w_ax, a_ax=a_ax,
                                     vmap=vmap, r_col=300e-9)
            except Exception as e:                             # noqa: BLE001
                print('     %-16s ⚠ %s' % (os.path.basename(f), e))
                continue
            a1, a2, a3 = r['f1_area'], r['f2_area'], r['f3_area']
            tot = a1 + a2 + a3
            st = z['step'] if 'step' in z else '?'
            print('     step=%-11s %-11.4f %-11.4f %-11.4f | **%5.1f%% / %5.1f%% / %5.1f%%**'
                  % (st, a1 * 1e12, a2 * 1e12, a3 * 1e12,
                     100 * a1 / tot if tot else float('nan'),
                     100 * a2 / tot if tot else float('nan'),
                     100 * a3 / tot if tot else float('nan')))
    print()
    print('=' * 108)
    print('  ⚠ 记账：脚本遍历快照时用 `fs[::max(1,len//5)] + [fs[-1]]` 抽样，')
    print('     **不是全部快照**；末态一定在其中（`+ [fs[-1]]`）。')
    print('  ⚠ 三类面积用**同一套** `np.roll` 格面口径（与 `f2_area`/`f3_area` 一致）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
