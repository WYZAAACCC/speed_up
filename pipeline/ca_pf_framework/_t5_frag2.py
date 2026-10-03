#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_frag2.py --- §144.4 待查项（**修好形状问题**）：7 个"包围盒被撑大"的场是否含碎片？

## 上一版错在哪（**留痕**）
我把 `band_idx`/`band_fld` 当成与 `region` 同形的三维数组去布尔索引 ——
**而它们是**稀疏**的（只在 band 内 500056 个体素）** ⇒ `IndexError: size of axis is 160 but
size of corresponding boolean axis is 500056`。
**⇒ 正确做法**：`band_idx` 是**扁平索引**（`np.ravel_multi_index` 的逆）⇒
   用 `np.unravel_index(band_idx, shape)` 还原成三维坐标，再去查 `region`。

## 判据（**预先写死**，§144.4）
* 某场含**多个不连通碎片** ⇒ **是碎片** ⇒ 判据② 应用**最大连通块**的跨度重算（量具口径问题）；
* **单连通且跨度真大** ⇒ **真实形貌** ⇒ 须解释它为何超出板条特征尺寸。
"""
import sys
import numpy as np

P = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_t5/dry_t5H3/snap_01000.npz'
DX = float(sys.argv[2]) if len(sys.argv) > 2 else 62.5

with np.load(P, allow_pickle=False) as z:
    reg = np.asarray(z['region'])
    bidx = np.asarray(z['band_idx']).ravel().astype(np.int64)
    bfld = np.asarray(z['band_fld']).ravel().astype(np.int64)

print('=' * 100)
print('★ 碎片检查（修正版）：%s   dx=%.1f nm' % (P, DX))
print('=' * 100)
print('  region 形状 = %s    band 体素 = %d' % (reg.shape, bidx.size))

shape = reg.shape
# band_idx → 三维坐标
coords = np.unravel_index(bidx, shape)
reg_at = reg[coords]                      # 每个 band 体素的 region 标签

fields = sorted(set(int(x) for x in np.unique(bfld).tolist()))
print('  band 覆盖的场 = %s' % fields)
print()
print('  %-5s %7s %9s %11s %20s  %s' %
      ('场', '体素', 'region数', '最大块体素', '最大块跨度 a/w/n (nm)', '诊断'))
print('  ' + '-' * 92)

out = {}
for f in fields:
    if f == 0:
        continue                            # 0 号是母相/背景
    sel = (bfld == f)
    n = int(sel.sum())
    if n == 0:
        continue
    rl, cnt = np.unique(reg_at[sel], return_counts=True)
    keep = rl != 0
    rl, cnt = rl[keep], cnt[keep]
    if rl.size == 0:
        print('  %-5d %7d %9s %11s %20s  %s' % (f, n, '-', '-', '-', '（全背景）'))
        continue
    big = int(rl[int(np.argmax(cnt))])
    # 该场里属于最大 region 的体素 → 坐标 → 包围盒
    m2 = sel & (reg_at == big)
    cc = np.stack([c[m2] for c in coords], axis=1)
    lo, hi = cc.min(0), cc.max(0)
    sp = tuple(float(v) * DX for v in (hi - lo + 1))
    diag = ('✅ 单连通' if rl.size == 1 else '⚠ **%d 个碎片**' % rl.size)
    print('  %-5d %7d %9d %11d %20s  %s' %
          (f, n, rl.size, int(cnt.max()), '%.0f/%.0f/%.0f' % sp, diag))
    out[f] = dict(n=n, nreg=int(rl.size), sp=sp)

print()
print('  ── 判读（§144.4 预先写死）──')
frag = sorted(f for f, d in out.items() if d['nreg'] > 1)
soli = sorted(f for f, d in out.items() if d['nreg'] == 1)
print('  含碎片的场（region 数 > 1）= %s' % (frag if frag else '（无）'))
print('  单连通的场 = %d 个：%s' % (len(soli), soli))
print()
if frag:
    print('  ⇒ **有场含碎片** ⇒ 判据② 的"未过"里**至少一部分是碎片造成的** ⇒')
    print('     应改用**最大连通块的跨度**重算（**量具口径问题，不是物理问题**）。')
else:
    print('  ⇒ **全部单连通** ⇒ 那些场"跨度大"**不是碎片造成的** ⇒ **是真实形貌** ⇒')
    print('     须解释它为何超出板条特征尺寸（**可能指向新机制** —— 更强的结论）。')
