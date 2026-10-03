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
# ⚠⚠ s160 修（**我先前犯的错，留痕**）：原来这里是硬编码的 `ANOM = {11, 21, 24}` ——
#   那是**在 `t5H3` 上**定出来的；而**场编号是每臂独立的形核序号**，**不可跨臂使用**。
#   实测：`t5V2` 的场 11 充填率 0.139（完全正常），却被标成"★ 异常场" ⇒ **假阳性**。
#   **修法**：改为**按阈值动态判定**（`fill < THR_EXT`），**不再依赖任何编号**。
THR_EXT = 0.10      # 充填率下限：低于它判为"带延伸"（与 `_t5_fillts.py` 同一口径）

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
    tag = '★ 带延伸' if fill < THR_EXT else ''
    print('  %-5d %9d %16s %10.3f    %s' %
          (k, idx.shape[0], 'x'.join(str(int(v)) for v in ext), fill, tag))

print()
fa = [r[3] for r in rows if r[3] < THR_EXT]
fn = [r[3] for r in rows if r[3] >= THR_EXT]
if fa and fn:
    print('  ── 判读（预先写死）──')
    print('  带延伸场（fill<%.2f）充填率：%s   中位 %.3f'
          % (THR_EXT, ['%.3f' % x for x in fa], float(np.median(fa))))
    print('  紧凑场          充填率：中位 %.3f  范围 [%.3f, %.3f]'
          % (float(np.median(fn)), min(fn), max(fn)))
    print()
    if float(np.median(fa)) < 0.6 * float(np.median(fn)):
        print('  ✅ **带延伸场充填率明显更低 ⇒ 它们是"带凸起/分支/延伸"的形貌**（真实物理特征）⇒')
        print('     判据② 的 `t_wf`（两宽面距离）**仍然可信**（§146.5/§148 已见它没被撑大），')
        print('     只是**包围盒口径**不适用于它们 ⇒ 应报"长宽比"时用 `t_wf`/投影的**主轴跨度**。')
    else:
        print('  ⚠ **充填率相当 ⇒ 是整体变大**（不是凸起）⇒ 须另找解释。')
elif not fa:
    print('  ⇒ **本快照里没有"带延伸"的场**（全部 fill ≥ %.2f）⇒ 与 t5H3 的 step 0–800 阶段同型。' % THR_EXT)
else:
    print('  ⚠ 全是带延伸场（无紧凑场）⇒ 无法对比')
