#!/usr/bin/env python3
"""R52: **第三个口径**（孤儿免疫的三轴尺寸）—— 用来裁决前两个口径的矛盾。

## 矛盾
`_r52_stall.py` 实测 `dry_mb1s62` 全程：
  `d(tip_sep_nm)/dstep` = **+0.244**（面簇中位位置之差）
  `d(a_lath)/dstep`     = **+1.499**（该场全部体素的**包围跨度**）
⇒ 差 **6 倍**，且 500–1000 窗口差 **15.7 倍**（+0.038 vs +0.598）。
⇒ **"端面停住"（§34）能否成立，取决于用哪个口径 —— 这是不允许的状态。**

## 本口径（第三个，独立于前两个）
对每个场，先取**最大连通分量**（`_bk_measure._label_periodic`，孤儿免疫），
再在**自己的 (n,w,a) 正交基**上做投影取 `max−min`：
  * 不是"面簇中位位置"⇒ 不被尖端变钝骗；
  * 不是"全场的包围盒"⇒ 不被同场的碎屑/长指撑大。
"""
import glob
import os
import sys

import numpy as np

sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
import _bk_measure as BM  # noqa: E402

D = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mb/dry_mb1s62'
snaps = sorted(glob.glob(os.path.join(D, 'snap_*.npz')))
print('臂 %s  快照 %d 个' % (D, len(snaps)))
print()
print('  %-6s %-9s %-9s %-9s %-9s %-9s %s'
      % ('step', 'core a', 'core w', 'core n', 'core体素', '全场体素', 'core/全场'))
rec = []
for s in snaps:
    z = np.load(s)
    reg = z['region']
    N = int(z['N'])
    L = float(z['L'])
    dx = L / N
    aa = np.asarray(z['a_ax'], float)
    ww = np.asarray(z['w_ax'], float)
    nn = np.asarray(z['n_hab'], float)
    step = int(z['step'])
    # 所有非母相胞看成一个整体，取最大连通分量（**孤儿免疫**）
    mask = (reg > 0)
    if not mask.any():
        continue
    lab, n = BM._label_periodic(mask)
    if lab is None or n == 0:
        continue
    sz = np.bincount(lab.ravel(), minlength=n + 1)
    big = int(np.argmax(sz[1:])) + 1
    core = (lab == big)
    idx = np.argwhere(core).astype(float) * dx          # 单位：**米**
    ext = {}
    for name, u in (('a', aa), ('w', ww), ('n', nn)):
        pr = idx @ u
        ext[name] = (pr.max() - pr.min()) * 1e9         # → nm
    rec.append((step, ext['a'], ext['w'], ext['n'],
                int(core.sum()), int(mask.sum())))
    print('  %-6d %-9.0f %-9.0f %-9.0f %-9d %-9d %.3f'
          % (step, ext['a'], ext['w'], ext['n'],
             int(core.sum()), int(mask.sum()),
             core.sum() / max(mask.sum(), 1)))
print()
print('=== 分段速率（孤儿免疫的 core 口径）')
print('  %-14s %-13s %-13s %-13s %s'
      % ('窗口', 'd(core a)', 'd(core w)', 'd(core n)', 'a/w 谁快'))
for lo, hi in ((0, 500), (500, 1000), (1000, 1500), (0, 1500)):
    seg = [r for r in rec if lo <= r[0] <= hi]
    if len(seg) < 3:
        print('  %-14s （点不足）' % ('%d–%d' % (lo, hi)))
        continue
    out = []
    for col in (1, 2, 3):
        xs = np.array([r[0] for r in seg], float)
        ys = np.array([r[col] for r in seg], float)
        out.append(float(np.polyfit(xs, ys, 1)[0]))
    print('  %-14s %+-13.3f %+-13.3f %+-13.3f %s'
          % ('%d–%d' % (lo, hi), out[0], out[1], out[2],
             ('**a 快**（拉长）' if out[0] > out[1] else
              '**w 快**（肥化）' if out[1] > out[0] else '相等')))
print()
print('★ 判读：把本表与 `_r52_stall.py` 的三列并排看 ——')
print('  · 若本口径的 `d(core a)` 与 `a_lath` 同量级 ⇒ 面簇口径（`tip_sep`）**偏低**，')
print('    §34 的"端面停住"应**撤回**；')
print('  · 若本口径与 `tip_sep` 同量级 ⇒ `a_lath` 被碎屑/长指撑大，停住是真的。')
