#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_bandself.py --- ★★★★★ 量具自查：`band` 的 `band_fld`/`band_val` 语义是否如我所想？

## 为什么必须自查（**用户强调"尤其注意量具的正确性"**）
我把 `band_val` 当**符号距离 φ**、`band_fld` 当"该胞属于哪个场"，
据此得出"一个场有多块 / 体积流失"等**全部结论**。
**但"合计 ≈ Vt（差 1%）"只能说明**总量**对，不能排除**标注混淆**（例如同一胞被多个场报负）。**

## 判据（**预先写死**）
对快照里每个胞，数**有多少个场把它报成 φ<0**：
| 结果 | 含义 |
|---|---|
| **绝大多数胞 = 1 个场** | **✅ 量具无误** ⇒ `φ<0` 的集合互不重叠 ⇒ 前面结论**成立** |
| **大量胞 = 2+ 个场** | **❌ 语义与我想的不同**（例如 `band_val` 不是"该场的 φ"）⇒ **结论要重审** |
| **有胞 = 0 个场** | 正常（母相）|

**同时报**：`band_idx` 的**重复率**（同一胞是否在 `band_idx` 里出现多次）
—— 这能直接看出"每个胞有几个场在它身上有记录"。
"""
import glob
import sys
import numpy as np
from collections import Counter

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276F'
ST = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
fs = [f for f in sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG)) if ('%05d' % ST) in f]
if not fs:
    print('  ⚠ 无 step %d 的快照' % ST); sys.exit(1)
with np.load(fs[0], allow_pickle=False) as z:
    N = int(np.asarray(z['N']))
    bi = np.asarray(z['band_idx']).ravel().astype(np.int64)
    bv = np.asarray(z['band_val']).ravel()
    bf = np.asarray(z['band_fld']).ravel()

flat = (bi // (N * N)) * (N * N) + ((bi // N) % N) * N + (bi % N)
print('=' * 92)
print('★ %s step %d：量具自查（N³ = %d 胞；band 记录条数 = %d）' % (TAG, ST, N ** 3, bv.size))
print('=' * 92)
print('  ⇒ **每条记录 / 每胞 = %.2f**（>1 ⇒ 一个胞被多个场记录）' % (bv.size / (N ** 3)))
print()
# ① 每胞被多少条记录覆盖
cnt_rec = np.bincount(flat, minlength=N ** 3)
print('  ── ① 每个胞的**记录条数**分布 ──')
u, c = np.unique(cnt_rec, return_counts=True)
for uu, cc in list(zip(u, c))[:8]:
    print('     %d 条记录：%d 胞（%.1f%%）' % (uu, cc, 100.0 * cc / (N ** 3)))
print()
# ② ★ 每胞被**多少个场**报为 φ<0
neg = bv < 0
cnt_neg = np.zeros(N ** 3, np.int32)
sel = flat[neg]
fk = bf[neg]
# 用"场号 + 胞号"去重（同一场对同一胞可能有多条）
pair = np.unique(sel.astype(np.int64) * 100000 + fk.astype(np.int64))
cells = pair // 100000
np.add.at(cnt_neg, cells, 1)
print('  ── ② ★ 每个胞被**多少个场**报成 φ<0（**核心判据**）──')
u2, c2 = np.unique(cnt_neg, return_counts=True)
for uu, cc in zip(u2, c2):
    tag = {0: '母相（无场报负）', 1: '**正常（1 个场）**'}.get(int(uu), '⚠ **%d 个场同时报负**' % uu)
    print('     %d 个场：%8d 胞（%6.2f%%）  %s' % (uu, cc, 100.0 * cc / (N ** 3), tag))
print()
tot_neg = int((cnt_neg >= 1).sum())
multi = int((cnt_neg >= 2).sum())
print('  ── 判据（**预先写死**）──')
print('     报负的胞 = %d（%.2f%% 盒）｜ 其中**多场重叠** = %d（%.2f%%）'
      % (tot_neg, 100.0 * tot_neg / (N ** 3), multi, 100.0 * multi / (N ** 3)))
if multi <= 0.02 * max(tot_neg, 1):
    print('  ⇒ **✅ 量具无误**：`φ<0` 的集合**基本互不重叠**（重叠 %.2f%%）'
          % (100.0 * multi / max(tot_neg, 1)))
    print('     ⇒ 前面基于 `band` 的结论（一场多块、体积流失）**成立**。')
else:
    print('  ⇒ **❌ 语义与我想的不同**：有 %.1f%% 的报负胞被多个场同时报负'
          % (100.0 * multi / max(tot_neg, 1)))
    print('     ⇒ **必须重审**前面所有基于 `band` 的结论。')
    # 打印一个重叠胞的明细
    w = np.flatnonzero(cnt_neg >= 2)[:3]
    for cc in w:
        m = (flat == cc) & neg
        print('     例：胞 %d 被场 %s 报负，值 %s'
              % (cc, bf[m].tolist(), np.round(bv[m], 12).tolist()))
