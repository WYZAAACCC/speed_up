#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_regdiff.py --- ★★★★★★ **`region` 到底差了多少**（f32 vs f64）？

## 为什么这是关键
R169 判：**`region` 不同 ⇒ f32 改了 `argmin` 次序 ⇒ 判为降精度**。
**但"不同"有两种性质**：
* **差 1–2 个胞** ⇒ **病态格点（并列/近并列）的翻转** ⇒ **数值上不可避免**，**量级上无害**；
* **差 10³–10⁶ 个胞** ⇒ **整片区域易主** ⇒ **真·不同构型** ⇒ **必须否掉**。
**⇒ 本脚本量化它，并把结论写清楚（这是"判决要给幅度"的要求）。**
"""
import os
import sys

import numpy as np

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_f32'


def load(tag):
    d = os.path.join(ROOT, 'dry_' + tag)
    if not os.path.isdir(d):
        return None
    f = sorted([x for x in os.listdir(d) if x.startswith('snap_')],
               key=lambda x: int(x.split('_')[1].split('.')[0]))
    if not f:
        return None
    z = np.load(os.path.join(d, f[-1]))
    return {k: z[k] for k in z.files}, f[-1]


def main():
    la, lb = load('P64'), load('P32')
    if la is None or lb is None:
        print('  ⚠ 缺快照')
        return
    a, fa = la
    b, fb = lb
    if a is None or b is None:
        print('  ⚠ 缺快照')
        return
    ra, rb = np.asarray(a['region']), np.asarray(b['region'])
    print('=' * 96)
    print('f32 vs f64：`region`（= argmin 的结果）的差异**量化**')
    print('=' * 96)
    print('  形状        : %s vs %s' % (ra.shape, rb.shape))
    print('  dtype       : %s vs %s' % (ra.dtype, rb.dtype))
    if ra.shape != rb.shape:
        print('  ❌ 形状不同 ⇒ 无法逐胞比')
        return
    n = ra.size
    nd = int(np.sum(ra != rb))
    print('  **不同胞数** : **%d / %d = %.6f%%**' % (nd, n, 100.0 * nd / n))
    if nd:
        # 差异的位置分布
        idx = np.argwhere(ra != rb)
        print('  差异胞的坐标范围: %s … %s' % (idx.min(axis=0), idx.max(axis=0)))
        # 涉及的"场号"集合
        fa_ = set(np.unique(ra[ra != rb]).tolist())
        fb_ = set(np.unique(rb[ra != rb]).tolist())
        print('  差异处**旧**场号(%d 个): %s' % (len(fa_), sorted(fa_)[:14]))
        print('  差异处**新**场号(%d 个): %s' % (len(fb_), sorted(fb_)[:14]))
        # 连通性：差异是不是连成一片
        try:
            from scipy import ndimage
            lab, nl = ndimage.label(ra != rb, structure=np.ones((3, 3, 3)))
            sizes = np.bincount(lab.ravel())[1:]
            print('  ★ 差异的**连通块数** = %d；最大块 = %d 胞；中位块 = %.0f 胞'
                  % (nl, sizes.max() if len(sizes) else 0,
                     np.median(sizes) if len(sizes) else 0))
        except Exception as e:
            print('  （连通性算不出：%s）' % e)
    # 顺带：phi 的差
    if 'phi' in a and 'phi' in b:
        pa, pb = np.asarray(a['phi'], float), np.asarray(b['phi'], float)
        if pa.shape == pb.shape:
            d = np.abs(pa - pb)
            m = max(np.nanmax(np.abs(pa)), 1e-300)
            print('  `phi` 最大绝对差 = %.3e（相对 %.3e）；不同元素 = %d/%d'
                  % (np.nanmax(d), np.nanmax(d) / m, int(np.sum(pa != pb)), pa.size))
    print()
    print('  ★ 判读：')
    print('   · **几个胞（≪0.01%）且分散** ⇒ **病态格点的翻转** ⇒ 数值上不可避免、量级无害**')
    print('   · **成片（≥0.1% 或一个大连通块）** ⇒ **区域易主** ⇒ 真·不同构型 ⇒ **必须否掉 f32**')
    print('=' * 96)


if __name__ == '__main__':
    main()
