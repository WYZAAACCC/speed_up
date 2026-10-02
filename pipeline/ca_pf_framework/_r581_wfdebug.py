#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_wfdebug.py --- 调试：为什么 `t_wf` 对 18 个场给出同一个数"""
import os
import sys
from collections import Counter

import numpy as np

FR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, FR)
import _bk_measure as BM

snap = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_blk/dry_BK6/snap_00250.npz'
dx = 62.5e-9
z = np.load(snap)
N = int(z['N'])
bc = int(z['band_cells'])
n_hab = np.asarray(z['n_hab'], float)
idx = np.asarray(z['band_idx']).ravel().astype(np.int64)
val = np.asarray(z['band_val']).ravel().astype(np.float64)
fld = np.asarray(z['band_fld']).ravel().astype(np.int32)
print('=' * 96)
print('调试 `t_wf`：%s' % snap)
print('=' * 96)
print('  band 记录数 = %d；**唯一索引数 = %d**；重复记录 = %d'
      % (idx.size, np.unique(idx).size, idx.size - np.unique(idx).size))
cnt = Counter(idx.tolist())
dups = [(k, v) for k, v in cnt.items() if v > 1]
print('  重复的索引个数 = %d；最大重复次数 = %d'
      % (len(dups), max((v for _, v in dups), default=0)))
print('  band_fld 的取值数 = %d（0=母相？）' % np.unique(fld).size)
print()
print('  ── 一个重复索引处的 φ 值是否一致？──')
if dups:
    k0 = dups[0][0]
    sel = (idx == k0)
    print('     idx=%d ⇒ 记录 %d 条：val=%s；fld=%s'
          % (k0, int(sel.sum()), val[sel][:6], fld[sel][:6]))
print()
# 按"以 fld 分组"重建：每个场只看自己的带
print('  ── 假设 band 是**逐场**存的：按 (fld, idx) 唯一化 ──')
key = fld.astype(np.int64) * (N ** 3) + idx
print('     (fld,idx) 组合数 = %d（原始 %d）⇒ 唯一化后 %d'
      % (np.unique(key).size, idx.size, np.unique(key).size))
print()
# 重建（每个索引取**绝对值最小**的 val —— 因为它最接近界面）
phi_flat = np.full(N ** 3, np.nan)
order = np.argsort(np.abs(val))          # 从小到大
phi_flat[idx[order]] = val[order]        # 后写覆盖 ⇒ 最终留下 |val| 最小的
phi = phi_flat.reshape((N, N, N))
fin = np.isfinite(phi)
print('  ── 重建（每索引留 |φ| 最小者）──')
print('     非 NaN 胞数 = %d（= 唯一索引数 %d）%s'
      % (int(fin.sum()), np.unique(idx).size,
         '✅' if int(fin.sum()) == np.unique(idx).size else '❌'))
print('     |φ|max = %.4g m = %.2f 胞（band_cells=%d）' % (np.nanmax(np.abs(phi)),
                                                          np.nanmax(np.abs(phi)) / dx, bc))
print()
# 逐场调量具并打印中间量
reg = np.asarray(z['region'])
ks = sorted(set(int(x) for x in np.unique(reg)) - {0})[:6]
print('  ── 逐场中间量（前 6 个场）──')
print('  %-6s %-9s %-11s %-13s %-13s %-11s %s' %
      ('场', 'own胞数', 'wf胞数', 'lo(nm)', 'hi(nm)', 't_wf(nm)', '返回'))
for k in ks:
    try:
        d = BM.wide_face_thickness(phi, dx, n_hab, k)
    except Exception as e:
        print('  %-6d 异常：%s' % (k, e))
        continue
    if d is None:
        print('  %-6d ⇒ **None**（不可测）' % k)
    else:
        print('  %-6d %-9s %-11s %-13.1f %-13.1f %-11.1f %s' %
              (k, '?', d.get('n_wf', '?'), d['lo'] * 1e9, d['hi'] * 1e9,
               d['t_wf'] * 1e9, sorted(d.keys())))
print()
print('  ★ 读法：**若 wf 胞数很大且 lo/hi 铺满整场 ⇒ 选出来的不是"宽面"** ⇒ 量具用错')
print('=' * 96)
