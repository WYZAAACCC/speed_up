#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_facetjudge.py --- ★★ A-3 的判决量具：从快照的 `nhist` **离线**判断有没有长出平坦惯习面

A-3 的科学问题
--------------
"边缘是圆的"（台账 A-3）：种子是棱柱，但尖端/棱很快变圆，`fill_cal` 掉到 ≈0.5（椭球值）。
**问：`facet_lam=0.4`（尖点界面能）能否让惯习面长出平坦 facet？**

`nhist` 为什么正好能回答
------------------------
快照里的 `nhist` 是界面带上 **`((n·n*)², (n·w)²)` 的 8×8 联合直方图**（512 B）。
  * **平坦惯习面** ⇒ 大片界面的法向**严格等于** `n*` ⇒ `(n·n*)²→1` 的**顶格 bin 极高**
    且相邻 bin 很低（**尖峰**）；
  * **圆角** ⇒ 法向在 `n*` 附近**连续铺开** ⇒ 顶格与相邻 bin 的落差小（**钝峰**），
    且**中间 bin 有可观占比**。
⇒ 所以判据是**峰的锐度**与**中间bin占比**，不是单一的"面占比"。

判据（先写死）
--------------
  F-1 循步报 `habit_top` = 顶格(`(n·n*)²≥0.875`)占界面的比例；
  F-2 报 **`sharp` = 顶格 / 相邻格**（`(0.75,0.875]` 那一格）—— **锐度**；圆角 ⇒ 该比值小；
  F-3 报 **`mid` = 中间格(`0.25<(n·n*)²<0.75`)占比** —— 圆角 ⇒ 该值大；
  F-4 两臂对照：`facet_lam=0.4` 若真有造面能力 ⇒ 随步 `sharp` **上升**且 `mid` **下降**；
      若两臂曲线**重合** ⇒ **尖点界面能在本尺度上不起作用**（与 A-2 的 0.1% 论证一致）。

用法：`python3 _r1_facetjudge.py a3_facet00 a3_facet04`
"""
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EDGES = (np.arange(8) + 1) / 8.0          # 8 个 bin 的上边界
TOP = 7                                    # (n·n*)² ≥ 0.875
NEXT = 6                                   # (0.75, 0.875]


def scan(arm):
    DIR = os.path.join(HERE, '_exp', arm)
    snaps = sorted(glob.glob(os.path.join(DIR, 'snap_*.npz')))
    if not snaps:
        print('%-14s ✗ 无快照' % arm); return None
    rows = []
    for sp in snaps:
        z = np.load(sp)
        if 'nhist' not in z.files:
            continue
        H = z['nhist'].astype(float)
        tot = H.sum()
        if tot <= 0:
            continue
        marg = H.sum(1)                     # 沿 (n·n*)² 的边际
        top = marg[TOP] / tot
        nxt = marg[NEXT] / tot
        mid = marg[2:6].sum() / tot
        sharp = top / max(nxt, 1e-12)
        rows.append((int(z['step']), top, sharp, mid, tot))
    return rows


def report(arm):
    rows = scan(arm)
    if not rows:
        return None
    print('\n' + '=' * 88)
    print('%s ：%d 个带 `nhist` 的快照' % (arm, len(rows)))
    print('   %8s %10s %12s %10s %10s'
          % ('step', 'habit_top', 'sharp', 'mid', '带胞数'))
    for st, top, sharp, mid, tot in rows[:: max(1, len(rows) // 10)] + [rows[-1]]:
        print('   %8d %10.4f %12.2f %10.4f %10.0f' % (st, top, sharp, mid, tot))
    a, b = rows[0], rows[-1]
    print('   ⇒ 变化：`sharp` %.2f → **%.2f**（%+.0f%%）；`mid` %.4f → **%.4f**'
          % (a[2], b[2], 100 * (b[2] / max(a[2], 1e-12) - 1), a[3], b[3]))
    print('      判据（F-4）：**造面成功** ⇒ `sharp` **升**且 `mid` **降**；')
    print('                    两者都平 ⇒ 该机制在本尺度不起作用')
    return rows


arms = sys.argv[1:] or ['a3_facet00', 'a3_facet04']
R = {a: report(a) for a in arms}
R = {k: v for k, v in R.items() if v}
if len(R) == 2:
    (a1, r1), (a2, r2) = list(R.items())
    print('\n' + '=' * 88)
    print('F-4 **两臂对照**（%s vs %s）：' % (a1, a2))
    print('   %-14s %10s %10s %10s' % ('臂', 'sharp末', 'mid末', 'habit_top末'))
    for a, r in ((a1, r1), (a2, r2)):
        print('   %-14s %10.2f %10.4f %10.4f' % (a, r[-1][2], r[-1][3], r[-1][1]))
    d_sharp = r2[-1][2] / max(r1[-1][2], 1e-12) - 1
    d_mid = r2[-1][3] - r1[-1][3]
    print('   ⇒ %s 相对 %s：`sharp` %+.0f%%、`mid` %+.4f' % (a2, a1, 100 * d_sharp, d_mid))
    if d_sharp > 0.10 and d_mid < -0.01:
        print('   ⇒ ✅ **尖点界面能确实在造面**（锐度升、中间格降）')
    elif abs(d_sharp) < 0.10 and abs(d_mid) < 0.01:
        print('   ⇒ ⛔ **两臂几乎一致 ⇒ 该机制在本尺度不起作用**'
              '（与 A-2 的"界面能只占驱动 0.1%"一致）')
    else:
        print('   ⇒ ⚠ 混合/不显著 ⇒ 报数并**不下结论**')
print('=' * 88)
