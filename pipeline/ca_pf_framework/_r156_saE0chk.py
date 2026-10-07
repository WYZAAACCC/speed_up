#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r156_saE0chk.py —— R155（弹性归因）的启动核对 + 中期轨迹。

判据（预登记在 `_r155_saE0.sh`）：
  **E-1** el=0 时 `r` **不再上升** ⇒ 上升是**弹性碰撞**造成的；
  **E-2** el=0 时 `r` **仍然上升** ⇒ 上升是**几何**的；
  **E-3** `box_touch_core == 0` 全程、`nf2(t=0) == 0`。
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
PAIRS = [('saSet2', 'saSet2E0', '{1,2,3,4,7,8}'),
         ('saOddG', 'saOddGE0', '{1,3,5,7,9,11}')]


def load(tag):
    p = os.path.join(MB, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p)))
    out = {}
    for key in ('step', 'r_selfac', 'nf2', 'box_touch_core', 'Vt'):
        v = []
        for r in rows:
            try:
                v.append(float(r.get(key, 'nan') or 'nan'))
            except (TypeError, ValueError):
                v.append(float('nan'))
        out[key] = np.array(v)
    out['_r0'] = rows[0].get('r_selfac')
    out['_nf2_0'] = rows[0].get('nf2')
    out['_nblk0'] = rows[0].get('nblk_sig')
    out['_nprof0'] = rows[0].get('blk_nprof')
    return out


def trend(a):
    m = np.isfinite(a['r_selfac'])
    if m.sum() < 3:
        return float('nan')
    return float(np.polyfit(a['step'][m], a['r_selfac'][m], 1)[0])


def main():
    print('=' * 104)
    print('_r156 —— R155 弹性归因：`--el-scale 0` 下 `r` 还升不升？')
    print('=' * 104)
    for hi, lo, lab in PAIRS:
        A, B = load(hi), load(lo)
        if A is None or B is None:
            print('\n  ### %s：数据不全（%s=%s, %s=%s）'
                  % (lab, hi, A is not None, lo, B is not None))
            continue
        print('\n  ### `%s`' % lab)
        print('     %-11s %-9s %-9s %-11s %-11s %-9s %s'
              % ('臂', 'step 数', 'r(0)', 'r(末)', '趋势/100步', 'nf2(0)', '撞壁max'))
        for nm, d in ((hi + '（el=1）', A), (lo + '（el=0）', B)):
            m = np.isfinite(d['r_selfac'])
            print('     %-11s %-9d %-9s %-11.4f %-+11.4f %-9s %.0f'
                  % (nm, int(m.sum()), d['_r0'],
                     d['r_selfac'][m][-1], trend(d) * 100, d['_nf2_0'],
                     np.nanmax(d['box_touch_core'])))
        t1, t0 = trend(A), trend(B)
        if not np.isfinite(t0):
            print('     ⏳ **`el=0` 臂还没跑够步数**（趋势未定义）⇒ 现在**不作判读**，'
                  '等跑完 %d 步再来。' % int(np.nanmax(B['step'])))
            continue
        print('     **E-1/E-2 判读**：el=1 趋势 %+.4e/步（%s）；el=0 趋势 %+.4e/步（%s）'
              % (t1, '升' if t1 > 0 else '降/平', t0, '升' if t0 > 0 else '降/平'))
        if t1 > 0 and t0 <= 0:
            print('        ⇒ **E-1 成立**：关掉弹性后 `r` 不再上升 ⇒ **上升是弹性碰撞造成的**')
        elif t1 > 0 and t0 > 0:
            print('        ⇒ **E-2 成立**：关掉弹性后 `r` 仍升 ⇒ **上升是几何的**')
        else:
            print('        ⇒ el=1 都没升 ⇒ 与 `§112` 的终态不一致，需查')
        print('     隔离：`nf2(t=0)` = %s / %s（应 0/0）；`nblk_sig(t=0)` = %s / %s'
              % (A['_nf2_0'], B['_nf2_0'], A['_nblk0'], B['_nblk0']))
        print('     `blk_nprof(t=0)` = %s / %s' % (A['_nprof0'], B['_nprof0']))
    print()
    print('  ⚠ 记账：`--el-scale 0` 是**大扰动** ⇒ 只比**趋势符号**，不跨 el 档比绝对值。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
