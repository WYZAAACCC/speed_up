#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_frag.py --- §144.4 的待查项：7 个"包围盒被撑大"的场是否**含多个不连通碎片**？

## 判据（**预先写死**，见 `R581_T5_RESTART.md §144.4`）
* 若某场含**多个不连通碎片** ⇒ **是碎片** ⇒ 判据② **不受影响**（应改用**最大连通块**的跨度重算）；
* 若**单连通且跨度真大** ⇒ **是真实形貌** ⇒ 须解释它为何超出板条特征尺寸（**可能指向新机制**）。

## 方法（**不引新量具**）
快照里有 `region`（**它本身就是逐体素的连通分量标签**）与 `band_fld`（该体素属于哪个场）。
**⇒ 对每个场，数它跨了几个 `region` 标签**：
    `n_region == 1` ⇒ 单连通；`> 1` ⇒ **碎片**。
**⇒ 再对**最大的那个 region** 单独算包围盒跨度** ⇒ 与 `t_wf` 比。
"""
import sys
import numpy as np

P = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_t5/dry_t5H3/snap_01000.npz'
DX = float(sys.argv[2]) if len(sys.argv) > 2 else 62.5   # nm

with np.load(P, allow_pickle=False) as z:
    reg = np.asarray(z['region'])
    fld = np.asarray(z['band_fld'])
    bidx = np.asarray(z['band_idx'])
    bval = np.asarray(z['band_val'])

print('=' * 104)
print('★ 碎片检查：%s   dx=%.1f nm' % (P, DX))
print('=' * 104)
# band 里的体素才是"在界面带内"的；用它当"该场的代表点"
m = (bidx >= 0)
print('  band 体素数 = %d' % int(m.sum()))

fields = sorted(set(int(x) for x in fld[m].tolist())) if m.any() else []
print('  band 覆盖的场 = %s' % fields)
print()
print('  %-6s %8s %10s %10s %14s %14s' %
      ('场', '体素', 'region数', '最大region体素', '最大region跨度(nm)', '诊断'))
print('  ' + '-' * 88)

def span_of(mask):
    """包围盒跨度（nm）—— 与 `_t5_proj.py` 同一口径"""
    idx = np.argwhere(mask)
    if idx.size == 0:
        return (0.0, 0.0, 0.0)
    lo, hi = idx.min(0), idx.max(0)
    return tuple(float(v) * DX for v in (hi - lo + 1))

out = {}
for f in fields:
    sel = m & (fld == f)
    n = int(sel.sum())
    if n == 0:
        continue
    rl, cnt = np.unique(reg[sel], return_counts=True)
    # 去掉背景标签（通常 0）
    keep = rl != 0
    rl, cnt = rl[keep], cnt[keep]
    if rl.size == 0:
        print('  %-6d %8d %10s %10s %14s %14s' % (f, n, '-', '-', '-', '（全是背景）'))
        continue
    big = rl[int(np.argmax(cnt))]
    bigmask = (reg == big) & (fld == f)
    sp = span_of(bigmask)
    diag = ('✅ 单连通' if rl.size == 1 else
            '⚠ **%d 个碎片** ⇒ 判据② 应改用最大连通块' % rl.size)
    print('  %-6d %8d %10d %10d %14s %14s' %
          (f, n, rl.size, int(cnt.max()),
           '%.1f/%.1f/%.1f' % sp, diag))
    out[f] = dict(n=n, nreg=int(rl.size), sp=sp, big=int(big))

print()
print('  ── 判读（§144.4 预先写死）──')
frag = [f for f, d in out.items() if d['nreg'] > 1]
soli = [f for f, d in out.items() if d['nreg'] == 1]
print('  含碎片的场（n_region > 1）= %s' % (frag or '（无）'))
print('  单连通的场               = %d 个' % len(soli))
print()
if frag:
    print('  ⇒ **有场含碎片** ⇒ 判据② 的"未过"里**至少一部分是碎片造成的**，')
    print('     应改用**最大连通块的跨度**重算（量具口径问题，不是物理问题）。')
else:
    print('  ⇒ **全部单连通** ⇒ 那 7 个场的"跨度大"**不是碎片造成的** ⇒ **是真实形貌**，')
    print('     须解释它为何超出板条特征尺寸（**可能指向新机制** —— 这是更强的结论）。')
