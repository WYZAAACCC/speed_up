#!/usr/bin/env python3
"""R50: **离线从落盘的 `region` 重算 core 口径撞壁**（P1-23 的收尾 + 用户"数据留盘"的回报）。

适用：所有早于 R38 的臂（`_bk_closed` 全族、`_bk_eng` 早段）—— 它们的 `series.csv`
里**没有** `box_touch_core`，但**每个快照都存了 `region`（int8）**，而 `region` 是
`box_touch_core` 的**唯一输入** ⇒ **可以事后重算，不必重跑**。

判据（预先写死）：
  * `core` 口径若为 0 而旧 `box_touch` 为 1 ⇒ 旧读数是**孤儿伪影**，几何读数**可用**；
  * `core` 口径为 1 ⇒ **真的撞壁**，该臂的几何读数**作废**。

用法： python _r50_corewall.py <臂目录> [...]
"""
import glob
import os
import re
import sys

import numpy as np

sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
import _bk_measure as BM  # noqa: E402


def core_wall(region, N):
    """与 `_bk_measure.measure_state` 里那段**逐字相同**的判据（最大分量是否触壁）。"""
    allowed = sorted({int(x) for x in np.unique(region) if int(x) > 0})
    if not allowed:
        return None
    lab, n = BM._label_periodic(np.isin(region, allowed))
    if lab is None or n == 0:
        return None
    sz = np.bincount(lab.ravel(), minlength=n + 1)
    big = int(np.argmax(sz[1:])) + 1
    mb = (lab == big)
    touch = any(bool(np.take(mb, 0, axis=ax).any())
                or bool(np.take(mb, N - 1, axis=ax).any()) for ax in (0, 1, 2))
    return dict(touch=bool(touch), core_vox=int(sz[big]), ncomp=int(n),
                total_vox=int(sz[1:].sum()))


def main():
    for d in sys.argv[1:]:
        snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
        if not snaps:
            print('%s: 无快照' % d)
            continue
        print('=' * 88)
        print('臂 %s   快照 %d 个' % (d, len(snaps)))
        print('  %-8s %-10s %-12s %-12s %-10s %s'
              % ('step', 'core壁?', 'core体素', '总转变体素', '分量数', 'core/总'))
        prev = None
        for s in snaps:
            z = np.load(s)
            reg = z['region']
            N = int(z['N'])
            step = int(z['step'])
            r = core_wall(reg, N)
            if r is None:
                continue
            prev = r
            print('  %-8d %-10s %-12d %-12d %-10d %.3f'
                  % (step, '**撞壁**' if r['touch'] else '0', r['core_vox'],
                     r['total_vox'], r['ncomp'],
                     r['core_vox'] / max(r['total_vox'], 1)))
        # 旧口径（任一转变胞触壁）作对照
        z = np.load(snaps[-1])
        reg = z['region']
        N = int(z['N'])
        old = any(bool((np.take(reg, 0, axis=ax) > 0).any())
                  or bool((np.take(reg, N - 1, axis=ax) > 0).any())
                  for ax in (0, 1, 2))
        print('  ⇒ 末态：旧口径 box_touch = %s ｜ **core 口径 = %s**'
              % (int(old), int(prev['touch']) if prev else '?'))


if __name__ == '__main__':
    main()
