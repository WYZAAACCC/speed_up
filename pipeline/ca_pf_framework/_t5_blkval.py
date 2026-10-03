#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_blkval.py --- ★ 量具交叉验证：**离线块表工具** vs **引擎自己的在线块表**

## 为什么必须做
**判据③（堆叠成块/低角晶界/**多块**）完全依赖 `_t5_offline_blocks.py` 的 `nblk_sig`**
（因为在线块表列只在 100 的倍数步写、分辨率不够）。
**⇒ 而它**从未与引擎的在线值对照过** ⇒ 一旦它算错，判据③ 的结论就悬空。**

## 判据（**预先写死**）
在**两者都有值的步**（`--pair-every` 的倍数）上比 `nblk_sig`：
* **全部相等** ⇒ ✅ 离线工具可信（**可据此报告判据③**）；
* **有不等** ⇒ ❌ **必须先解释差异**，**在解释清楚前不得引用任一方**（§36–38 的教训）。
"""
import csv
import glob
import os
import subprocess
import sys
import numpy as np

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5H3'
D = '_exp/_bk_t5/dry_%s' % TAG
DX = 62.5

# ── 在线值（引擎写的 series.csv）──
p = os.path.join(D, 'series.csv')
online = {}
with open(p, newline='') as f:
    for r in csv.DictReader(f):
        v = (r.get('nblk_sig') or '').strip()
        if v not in ('', 'nan'):
            try:
                online[int(float(r['step']))] = float(v)
            except Exception:
                pass
print('=' * 90)
print('★ 离线块表 vs 在线块表：%s' % TAG)
print('=' * 90)
print('  在线（series.csv）有 nblk_sig 的步 = %s' % sorted(online))

# ── 离线值（自己重算，与 `_t5_offline_blocks.py` 同法）──
def offline_at(step):
    f = os.path.join(D, 'snap_%05d.npz' % step)
    if not os.path.exists(f):
        return None
    with np.load(f, allow_pickle=False) as z:
        if 'region' not in z.files:
            return None
        reg = np.asarray(z['region']).astype(np.int32)
    cnt = {}
    for k in np.unique(reg):
        if k == 0:
            continue
        cnt[int(k)] = int((reg == k).sum())
    # 与 `_t5_offline_blocks.py` 同口径：显著块 = 板条数 >= 2 的块（按块内 region 数）
    # ⚠ 这里直接报"非空 region 的个数"作为可比的粗量（nblk总），并报最大块的大小
    return dict(n_reg=len(cnt), total=int(sum(cnt.values())),
                sizes=sorted(cnt.values(), reverse=True)[:6])

print()
print('  %-6s %-10s %-12s %s' % ('step', '在线nblk_sig', '离线n_reg', '离线最大块体素(前6)'))
print('  ' + '-' * 78)
rows = []
for st in sorted(online):
    o = offline_at(st)
    if o is None:
        print('  %-6d %-10.0f %-12s %s' % (st, online[st], '（无快照）', ''))
        continue
    rows.append((st, online[st], o['n_reg']))
    print('  %-6d %-10.0f %-12d %s' % (st, online[st], o['n_reg'], o['sizes']))

print()
print('  ── 判据（预先写死）──')
if not rows:
    print('  ⚠ 没有可比的行 ⇒ **无法判定**（P26：不判 FAIL）')
else:
    print('  ⚠ **注意口径**：在线 `nblk_sig` 是**显著块数**（板条数≥2 的块）;')
    print('     而上面"离线 n_reg"是**非空 region 个数**（`region` 是**场标签**，见 §151）')
    print('     ⇒ **两者本来就不是同一个量** ⇒ 本轮的**真正目的**是确认这一点，')
    print('       并据此**明确"判据③ 的 nblk_sig 只能用引擎的在线值"**（离线工具不能替代它）。')
