#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_wrap.py --- §145 路径 C：异常场（11/21/24）是否**跨盒面**（周期镜像假设的决定性检验）

## 假设（§145.3）
**`--nuc-periodic-seed 1` + 周期边界 ⇒ 跨边界的板条在**环绕表示**下裂成 ≥2 块，
其**包围盒跨度被人为撑大**（因为两份拷贝落在盒的两侧）。**

## 判据（**预先写死**）
对每个场，看它的 band 体素是否**同时触到某轴的两端**（`i==0 or i==N-1` 等）：
| 观察 | 结论 |
|---|---|
| **异常场（11/21/24）触到两端，而正常场不触** | ⇒ **周期镜像假设成立** ⇒ §144 的"未过"是**口径伪影**，判据② 实为通过 |
| **异常场也不触两端** | ⇒ **不是周期伪影** ⇒ 须另找解释（回到 §144.4 的"未解释"）|

## ⚠ 口径
**"触到两端"用一个薄层判据（最外 2 层胞）**，避免边界数值噪声误判。
"""
import sys
import numpy as np

P = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_t5/dry_t5H3/snap_01000.npz'
DX = float(sys.argv[2]) if len(sys.argv) > 2 else 62.5

with np.load(P, allow_pickle=False) as z:
    bidx = np.asarray(z['band_idx']).ravel().astype(np.int64)
    bfld = np.asarray(z['band_fld']).ravel().astype(np.int64)
    bval = np.asarray(z['band_val']).ravel().astype(np.float64)
    # 推断形状：region 若在，用它；否则从最大索引猜（立方）
    if 'region' in z.files:
        shape = np.asarray(z['region']).shape
    else:
        n = int(np.ceil((bidx.max() + 1) ** (1.0 / 3.0)))
        shape = (n, n, n)

N = shape[0]
print('=' * 100)
print('★ 跨盒面检查（周期镜像假设）：%s' % P)
print('=' * 100)
print('  推断网格 = %s   dx=%.1f nm   盒=%.2f µm   band 体素=%d' %
      (shape, DX, N * DX / 1000.0, bidx.size))

coords = np.unravel_index(bidx, shape)          # 三维坐标
# 只看**填充相**（band_val 的符号：负 = 已转变侧）
sign = np.sign(bval)
print('  band_val 符号分布：负=%d  零=%d  正=%d' %
      (int((sign < 0).sum()), int((sign == 0).sum()), int((sign > 0).sum())))
inside = sign < 0                                # 已转变的胞
print('  ⇒ 只对**内部**（band_val<0）统计，%d 个胞' % int(inside.sum()))
print()

ANOM = {11, 21, 24}                              # §144 里未过的场
fields = sorted(set(int(x) for x in np.unique(bfld[inside]).tolist()))
print('  %-5s %7s %9s %9s %9s   %s' %
      ('场', '胞数', '触x两端', '触y两端', '触z两端', '判定'))
print('  ' + '-' * 84)

res = {}
for f in fields:
    if f == 0:
        continue
    sel = inside & (bfld == f)
    if not sel.any():
        continue
    touch = []
    for ax in range(3):
        c = coords[ax][sel]
        lo = (c <= 1).any()          # 最外 2 层
        hi = (c >= N - 2).any()
        touch.append(bool(lo and hi))
    res[f] = touch
    tag = '★ 异常场' if f in ANOM else ''
    print('  %-5d %7d %9s %9s %9s   %s' %
          (f, int(sel.sum()), touch[0], touch[1], touch[2],
           ('**跨面** ✓' if any(touch) else '不跨面') + ' ' + tag))

print()
print('  ── 判读（预先写死）──')
anom_wrap = [f for f in ANOM if f in res and any(res[f])]
norm_wrap = [f for f in res if f not in ANOM and any(res[f])]
print('  异常场（11/21/24）中**跨面**的 = %s' % (sorted(anom_wrap) or '（无）'))
print('  正常场中**跨面**的         = %s' % (sorted(norm_wrap) or '（无）'))
print()
if anom_wrap and not norm_wrap:
    print('  ✅ **周期镜像假设成立**：异常场跨面、正常场不跨 ⇒')
    print('     §144 的"7 个场未过"是**口径伪影**（环绕表示把一份拷贝算成两块）⇒')
    print('     **判据② 的实质结论仍然是"通过"**（应改用"只看最大连通块"或"解环绕"重算）。')
elif anom_wrap and norm_wrap:
    print('  ⚠ **部分成立**：跨面的场里既有异常也有正常 ⇒ 跨面**不足以**解释差异，')
    print('     须再加一条判据（例如"跨度/最大块跨度"的比值）。')
else:
    print('  ❌ **周期镜像假设不成立**：异常场**也不跨面** ⇒ 须另找解释。')
    print('     ⇒ §144.4 的待查项**保持"未解释"**。')
