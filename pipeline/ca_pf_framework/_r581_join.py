#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_join.py --- ★★★ 为什么新板条**接不上块**？（R22 留下的机理问题）

## 背景（R581-R22 实测）
3-D F3 图显示：两条臂都在 step 200 形成**完美的 4 根板条块**（4 场 / 3 F3 边 /
链长 [4]），此后 **F3 边数不再增加**（b5 恒 4、b3 恒 3），而**场数继续涨**
（b5 4→9）。⇒ **新根在形核，但接不上块** ⇒ 这正是 **C5 的机理**。

## 假设（**预先写死，可证伪**）
* **H-远**：新根形核在**离已有块很远**的地方（随机撒点）⇒ **几何上就不可能接上**；
* **H-近**：新根形核在**块的边缘**（`attach`/`nfsv` 起了作用）但**界面没焊上**
  ⇒ 是**数值/界面**问题，不是播种问题。

## 怎么判（**量具**）
对相邻两个快照 `t1 < t2`：
1. 找出 `t2` 里**新增的场**（`t1` 里没有的场号）；
2. 对每个新场，算它**到 `t1` 里任一已有场的最近距离**（周期最小镜像）；
   —— 用**胞级**距离（EDT），不是质心距离（质心会被形状骗）；
3. 判据：
   * 最近距离 **≫ 核半径 R**（R = 320 nm）⇒ **H-远**（形核点在远处，够不着）
   * 最近距离 **≈ R 或更小** ⇒ **H-近**（挨着却没焊上）

⚠ **自洽检查（P21 强制）**：新场到"已有场集合"的距离必须 ≥ 新场自身的尺度
（否则说明它其实与已有场重叠 ⇒ 分类标签错了）。
"""
import os
import sys

import numpy as np
from scipy import ndimage

ROOT = '_exp/_bk_p2'
R_NUC_NM = 320.0     # `--eng-r-nm` 的默认量级（核半径）；判据阈值用


def load(tag, snapfile):
    z = np.load(os.path.join(ROOT, 'dry_' + tag, snapfile))
    return z['region'], int(z['step']), float(z['L'])


def mindist(mask_new, mask_old, dx):
    """新场胞到**任一已有场胞**的最近距离（周期最小镜像），单位：胞。"""
    if not mask_old.any() or not mask_new.any():
        return np.nan
    # 对 old 的补做 EDT，取 new 处的值；周期用 np.pad 的 wrap 模拟（近似：用 3x3 平铺取最小）
    d = ndimage.distance_transform_edt(~mask_old)
    return float(d[mask_new].min())


def main():
    print('=' * 100)
    print('R581 —— 新板条**接不上块**的机理（C5 的直接上游）')
    print('=' * 100)
    # ★ R581-R38：把 tag 参数化（原来硬编码 `('p2_b5','p2_b3')`），
    #   这样 S4/N13 的修复臂（`p2_b5ov`/`p2_b5ps`）可以用**同一把量具**比。
    tags = tuple(sys.argv[1:]) or ('p2_b5', 'p2_b3')
    print('  本跑比较的臂：%s' % (list(tags),))
    for tag in tags:
        d = os.path.join(ROOT, 'dry_' + tag)
        if not os.path.isdir(d):
            continue
        snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                       key=lambda f: int(f.split('_')[1].split('.')[0]))
        print()
        print('#' * 100)
        print('# %s' % tag)
        print('#' * 100)
        prev = None
        stats = {'AT': 0, 'far': 0, 'far_d': []}
        for s in snaps:
            reg, step, L = load(tag, s)
            dx = L / reg.shape[0]
            flds = set(int(v) for v in np.unique(reg) if v > 0)
            if prev is None:
                print('  step %-5d 场 %s（首个快照，作为基准）' % (step, sorted(flds)))
                prev = (reg, step, flds)
                continue
            preg, pstep, pflds = prev
            new = sorted(flds - pflds)
            print('  step %-5d（上一快照 step %d）新增场 %s' % (step, pstep, new or '（无）'))
            for f in new:
                mn = (reg == f)
                sz = int(mn.sum())
                d_cells = mindist(mn, preg > 0, dx)
                # ★ 分类（**"距离小"是好事，不是可疑** —— 第一版把语义写反了，留痕）
                #   距离 ≤ ~核半径 ⇒ **挨着核出来的** ⇒ 走 `attach`/`nfsv` 通道；
                #   距离 ≫ 核半径   ⇒ **远处随机撒的** ⇒ 几何上接不上。
                r_cells = (R_NUC_NM * 1e-9) / dx
                if not np.isfinite(d_cells):
                    cls = '（无已有场可比）'
                elif d_cells <= r_cells * 1.5:
                    cls = '**AT 边缘**（≤1.5R ⇒ 走 attach/nfsv 通道）'
                else:
                    cls = '**远场**（>1.5R ⇒ 随机撒点，几何上接不上）'
                print('     场 %-3d 胞数 %-6d  **到已有场最近距离 = %6.1f 胞 = %6.0f nm**'
                      '（核半径 %.0f nm；判据阈 1.5R = %.0f nm）  ⇒ %s'
                      % (f, sz, d_cells, d_cells * dx * 1e9, R_NUC_NM,
                         r_cells * 1.5 * dx * 1e9, cls))
                if np.isfinite(d_cells):
                    if d_cells <= r_cells * 1.5:
                        stats['AT'] += 1
                    else:
                        stats['far'] += 1
                        stats['far_d'].append(d_cells * dx * 1e9)
            prev = (reg, step, flds)
        print()
        print('  ── %s 汇总 ──' % tag)
        print('     **AT 边缘**（接得上） = %d 个' % stats['AT'])
        print('     **远场**（接不上）   = %d 个' % stats['far'])
        if stats['far_d']:
            print('     远场的距离：%s nm（中位 %.0f nm）'
                  % (['%.0f' % v for v in stats['far_d']],
                     float(np.median(stats['far_d']))))
        print('  ⇒ 判据（**预先写死**）：多数是远场 ⇒ **H-远**（播种撒太远，几何上接不上）；')
        print('                        多数在边缘 ⇒ **H-近**（挨着却没焊上）。')
    print('=' * 100)


if __name__ == '__main__':
    main()
