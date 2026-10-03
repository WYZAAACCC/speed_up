#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_fill.py --- §144 那 7 个"包围盒被撑大"的场：**充填率**判形貌

## 判据（**预先写死**）
`fill = 胞数 / (包围盒体积)`（都用胞为单位）：
* **紧凑板条**：预期 **~0.3–0.5**（长方体的大部分）；
* **含凸起/枝晶**：预期 **≪ 0.2**（包围盒被细长分支撑大，但实心部分没变）。
**⇒ 若异常场的 `fill` **明显低于**正常场 ⇒ **它们是"带凸起/分支"的形貌**（真实物理特征，
   而不是量具问题）；若 `fill` 相当 ⇒ 是**整体变大**（另一回事，须解释）。**
"""
import sys
import numpy as np

P = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_t5/dry_t5H3/snap_01000.npz'
DX = float(sys.argv[2]) if len(sys.argv) > 2 else 62.5
ANOM = {11, 21, 24}

with np.load(P, allow_pickle=False) as z:
    reg = np.asarray(z['region']).astype(np.int32)
N = reg.shape[0]
print('=' * 96)
print('★ 充填率判形貌：%s   N=%d  dx=%.1f nm' % (P, N, DX))
print('=' * 96)
print('  %-5s %9s %16s %10s    %s' % ('场', '胞数', '包围盒(胞)', '充填率', '判定'))
print('  ' + '-' * 80)
rows = []
for k in sorted(int(x) for x in np.unique(reg) if x != 0):
    idx = np.argwhere(reg == k)
    if idx.size == 0:
        continue
    lo, hi = idx.min(0), idx.max(0)
    ext = (hi - lo + 1).astype(np.int64)
    vol = int(ext.prod())
    fill = float(idx.shape[0]) / max(vol, 1)
    rows.append((k, idx.shape[0], ext, fill))
    tag = '★ 异常场' if k in ANOM else ''
    print('  %-5d %9d %16s %10.3f    %s' %
          (k, idx.shape[0], 'x'.join(str(int(v)) for v in ext), fill, tag))

print()
fa = [r[3] for r in rows if r[0] in ANOM]
fn = [r[3] for r in rows if r[0] not in ANOM]
if fa and fn:
    print('  ── 判读（预先写死）──')
    print('  异常场(11/21/24) 充填率：%s   中位 %.3f' % (['%.3f' % x for x in fa], float(np.median(fa))))
    print('  正常场          充填率：中位 %.3f  范围 [%.3f, %.3f]'
          % (float(np.median(fn)), min(fn), max(fn)))
    print()
    if float(np.median(fa)) < 0.6 * float(np.median(fn)):
        print('  ✅ **异常场充填率明显更低 ⇒ 它们是"带凸起/分支"的形貌**（真实物理特征）⇒')
        print('     判据② 的 `t_wf`（两宽面距离）**仍然可信**（§146.5 已见它没被撑大），')
        print('     只是**包围盒口径**不适用于它们 ⇒ 应报"长宽比"时用 `t_wf`/投影的**主轴跨度**。')
    else:
        print('  ⚠ **充填率相当 ⇒ 是整体变大**（不是凸起）⇒ 须另找解释（可能是"多个场并入了同一 label"）。')
else:
    print('  ⚠ 缺数据 ⇒ 无法判定')
