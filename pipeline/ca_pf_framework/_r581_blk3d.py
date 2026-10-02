#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_blk3d.py --- ★★★★★ **用 3-D 量复核 S4 的块结构**（R100 登记的关键复核）

## 为什么要做（R100 的发现 + 它的两种解释）
R100 实测：`p2_b5ov`（S4 开）末态 **`nslab_n` = 0、`nf3_col` = 0**，
而基线 `p2_b5` 是 **4** 与 **2**。**但 `nslab_n` 是**一维柱剖面**量**（P1-29 已知它"多读"），
所以有两种解释**必须分清**：
1. **真的塌了**（S4 让板条并成一个大块）⇒ **C3 回归**；
2. **口径问题**（柱剖面形状变了 ⇒ 读到 0）⇒ **不是物理回归**。

**⇒ 本量具用**三维、不依赖柱剖面**的量来判：**
* 对每个场（`region == f`）取**最大连通分量**，量它的**三维包围盒**与**体积**；
* 统计**场数**、**连通分量总数**、**最大分量体积**、**各分量的长宽厚**；
* 并计算 **`region>0` 的体积分数**（与 `Vt` 独立）。

## 用法
  _r581_blk3d.py <tag> [root]
"""
import os
import sys
from collections import Counter

import numpy as np

TAG = sys.argv[1] if len(sys.argv) > 1 else 'p2_b5'
ROOT = sys.argv[2] if len(sys.argv) > 2 else '_exp/_bk_p2'
DX_NM = 62.5


def cc_label(mask):
    """6-连通标记（纯 numpy 泛洪，避免 scipy 版本差异）—— 只在必要时用。"""
    from scipy import ndimage
    lab, n = ndimage.label(mask, structure=np.array(
        [[[0, 0, 0], [0, 1, 0], [0, 0, 0]],
         [[0, 1, 0], [1, 1, 1], [0, 1, 0]],
         [[0, 0, 0], [0, 1, 0], [0, 0, 0]]], dtype=bool))
    return lab, n


def extents(mask, lab, idx):
    """某个连通分量的三维包围盒（胞）与体积（胞）。"""
    m = (lab == idx)
    v = int(m.sum())
    if v == 0:
        return None
    zz, yy, xx = np.where(m)
    return (int(xx.max() - xx.min() + 1), int(yy.max() - yy.min() + 1),
            int(zz.max() - zz.min() + 1), v)


def main():
    d = os.path.join(ROOT, 'dry_' + TAG)
    print('=' * 104)
    print('S4 块结构的 **3-D** 复核：`%s`（%s）' % (TAG, d))
    print('=' * 104)
    if not os.path.isdir(d):
        print('  ❌ 无目录'); return
    snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                   key=lambda f: int(f.split('_')[1].split('.')[0]))
    if not snaps:
        print('  ❌ 无快照'); return
    z = np.load(os.path.join(d, snaps[-1]))
    keys = sorted(z.keys())
    print('  末快照 = %s ；键 = %s' % (snaps[-1], keys))
    if 'region' not in z:
        print('  ❌ 无 `region` 键'); return
    reg = z['region']
    N = reg.shape[0]
    nz_tot = int((reg > 0).sum())
    print('  网格 = %d³ ；`region>0` 的胞 = %d ；体积分数 = %.4f%%'
          % (N, nz_tot, 100.0 * nz_tot / reg.size))
    fields = [int(f) for f in np.unique(reg) if int(f) > 0]
    print('  场数（`region>0` 的不同值）= %d ：%s'
          % (len(fields), fields[:20]))
    if not fields:
        print('  ⇒ `region` 全 0 ⇒ **没有任何已转变区**（这本身就是个重要读数）'); return
    print()
    print('  %-6s %-8s %-8s %-26s %s'
          % ('场', '胞数', '连通分量', '最大分量的 (x,y,z) 胞', '最大分量体积(胞)'))
    print('  ' + '-' * 96)
    tot_cc = 0
    rows = []
    for f in fields:
        lab, n = cc_label(reg == f)
        tot_cc += n
        sizes = Counter(lab.ravel())
        sizes.pop(0, None)
        big = max(sizes, key=lambda k: sizes[k])
        e = extents(reg == f, lab, big)
        rows.append((f, int((reg == f).sum()), n, e))
        print('  %-6d %-8d %-8d %-26s %s'
              % (f, rows[-1][1], n,
                 '%d × %d × %d' % e[:3] if e else '?',
                 e[3] if e else '?'))
    print()
    print('  ── 汇总 ──')
    print('  场数 = %d ；**连通分量总数 = %d**' % (len(fields), tot_cc))
    print('  ⇒ 若"连通分量总数" ≈ 场数 ⇒ **每场一块**（结构完好）；')
    print('     若它 **≪** 场数（例如多场并成 1 个分量）⇒ **结构塌了**（R100 的解释 1）；')
    print()
    print('  ★ 单位换算（`dx = %.1f nm`）：' % DX_NM)
    for f, cells, n, e in rows[:4]:
        if e:
            print('     场 %-3d 最大分量：%.3f × %.3f × %.3f µm'
                  % (f, e[0] * DX_NM / 1000, e[1] * DX_NM / 1000, e[2] * DX_NM / 1000))
    print('=' * 104)


if __name__ == '__main__':
    main()
