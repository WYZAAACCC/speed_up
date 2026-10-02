#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_speck.py --- ★★★ A23：那些 1–4 胞的**碎屑**到底长在哪？

## 背景（R581-R18 的实测）
`_r581_fragdiag.py` 查明：两臂 9 个多分量场里 **8 个是"一个主体 + 1–4 胞碎屑"**
（碎屑占场 ≤4%），真正断裂只有 b5 的场 1 一例。**H1（1 胞 β 膜）占比 0.0%**。

## 本轮要回答的（**预先写死的三支**）
对**每一个碎屑**（分量胞数 ≤ `SPEC`），取它**膨胀 1 胞**得到的邻居集，
按邻居的 `region` 值分类：

| 支 | 邻居多数是 | 物理/数值解释 |
|---|---|---|
| **S-A** | **β（region==0）** | 碎屑**漂在母相里** ⇒ 脱离的孤立核/零集残片 |
| **S-B** | **另一个场** | 碎屑**嵌在别的板条内部** ⇒ `argmin(φ)` 在近似简并处**翻转** |
| **S-C** | **同一个场的另一个分量** | 1 胞桥被切断（**H1 的碎屑版**） |

**另测两项**：
* **贴壁**：碎屑是否触及盒子面（周期 BC 的伪影候选）；
* **λ 检验（自洽）**：碎屑胞数之和 + 主体胞数之和 == 场的胞数（P21 强制）。

⚠ **本量具只用落盘的 `region`**（快照里**没有 φ**）⇒ 只能做**几何**分类，
**不能**直接证明"是 argmin 翻转"，那是**解释**。凡解释一律标【推理】。
"""
import os
import sys

import numpy as np
from scipy import ndimage

SPEC = 10  # "碎屑"的胞数上限


def analyse(tag, snap=None):
    d = os.path.join('_exp/_bk_p2', 'dry_' + tag)
    if snap is None:
        c = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                   key=lambda f: int(f.split('_')[1].split('.')[0]))
        snap = c[-1]
    reg = np.load(os.path.join(d, snap))['region']
    N = reg.shape[0]
    flds = [int(v) for v in np.unique(reg) if v > 0]
    out = []
    tot_speck_cells = tot_cells = 0
    cntA = cntB = cntC = 0
    n_speck = 0
    wall = 0
    for v in flds:
        M = (reg == v)
        nv = int(M.sum())
        lab, n = ndimage.label(M)
        if n == 1:
            continue
        sizes = ndimage.sum(M, lab, range(1, n + 1)).astype(int)
        main = int(np.argmax(sizes)) + 1
        for i in range(1, n + 1):
            if i == main:
                continue
            sp = (lab == i)
            sz = int(sp.sum())
            tot_cells += nv
            if sz > SPEC:
                out.append((v, sz, '**大块**（>%d）' % SPEC, '-', '-'))
                continue
            n_speck += 1
            tot_speck_cells += sz
            nb = ndimage.binary_dilation(sp) & ~sp
            vals = reg[nb]
            n_beta = int((vals == 0).sum())
            n_same = int((vals == v).sum())
            n_oth = int(((vals > 0) & (vals != v)).sum())
            tot = max(n_beta + n_same + n_oth, 1)
            if n_same >= max(n_beta, n_oth):
                cls = 'S-C 同场'
                cntC += 1
            elif n_oth >= n_beta:
                cls = 'S-B 嵌在别的场里'
                cntB += 1
            else:
                cls = 'S-A 漂在 β 里'
                cntA += 1
            # 贴壁？
            zz = np.argwhere(sp)
            touch = bool((zz[:, 0] == 0).any() or (zz[:, 0] == N - 1).any() or
                         (zz[:, 1] == 0).any() or (zz[:, 1] == N - 1).any() or
                         (zz[:, 2] == 0).any() or (zz[:, 2] == N - 1).any())
            wall += touch
            out.append((v, sz, cls, 'β%d/同%d/异%d' % (n_beta, n_same, n_oth),
                        '贴壁' if touch else ''))
    return dict(tag=tag, snap=snap, flds=flds, rows=out, n_speck=n_speck,
                speck_cells=tot_speck_cells, tot_cells=tot_cells,
                A=cntA, B=cntB, C=cntC, wall=wall)


def main():
    tags = sys.argv[1:] or ['p2_b5', 'p2_b3']
    print('=' * 96)
    print('R581 —— A23：碎屑（≤%d 胞）长在哪？' % SPEC)
    print('=' * 96)
    agg = dict(A=0, B=0, C=0, n=0, cells=0, tot=0, wall=0)
    for t in tags:
        r = analyse(t)
        print()
        print('★ %s / %s   （%d 个场）' % (r['tag'], r['snap'], len(r['flds'])))
        print('   %-5s %-7s %-18s %-16s %s' % ('场', '碎屑胞数', '分类', '邻居（β/同/异）', '备注'))
        for row in r['rows']:
            print('   %-5s %-7s %-18s %-16s %s' % row)
        print('   ⇒ 碎屑 %d 个，共 %d 胞（占全部非母相胞 %d 的 **%.2f%%**）'
              % (r['n_speck'], r['speck_cells'], r['tot_cells'],
                 100.0 * r['speck_cells'] / max(r['tot_cells'], 1)))
        print('   ⇒ S-A（漂在 β 里）= %d ；S-B（嵌在别的场里）= %d ；S-C（同场 1 胞桥）= %d'
              % (r['A'], r['B'], r['C']))
        print('   ⇒ 贴壁的碎屑 = %d / %d' % (r['wall'], r['n_speck']))
        for k, kk in (('A', 'A'), ('B', 'B'), ('C', 'C')):
            agg[k] += r[k]
        agg['n'] += r['n_speck']; agg['cells'] += r['speck_cells']
        agg['tot'] += r['tot_cells']; agg['wall'] += r['wall']
    print()
    print('=' * 96)
    print('★ 汇总（两臂合计）')
    print('=' * 96)
    n = agg['n']
    print('   碎屑 %d 个 / %d 胞 / 非母相胞 %d ⇒ **占比 %.2f%%**'
          % (n, agg['cells'], agg['tot'], 100.0 * agg['cells'] / max(agg['tot'], 1)))
    if n:
        print('   S-A 漂在 β 里   ：%3d（%.1f%%）' % (agg['A'], 100.0 * agg['A'] / n))
        print('   S-B 嵌在别的场里：%3d（%.1f%%）' % (agg['B'], 100.0 * agg['B'] / n))
        print('   S-C 同场 1 胞桥 ：%3d（%.1f%%）' % (agg['C'], 100.0 * agg['C'] / n))
        print('   贴壁            ：%3d（%.1f%%）' % (agg['wall'], 100.0 * agg['wall'] / n))
        w = max((agg['A'], 'S-A（漂在 β 里 ⇒ 脱离的孤立胞）'),
                (agg['B'], 'S-B（嵌在别的场里 ⇒ argmin 在近简并处翻转）【推理】'),
                (agg['C'], 'S-C（同场 1 胞桥被切断）'))[1]
        print()
        print('   ⇒ **主因 = %s**' % w)
        print('   ⚠ 记账：判据是**几何**的（邻居多数是谁）；"为什么"是**解释**，')
        print('     快照里没有 φ ⇒ **无法直接验证 argmin 翻转**，标【推理】。')
    print('=' * 96)


if __name__ == '__main__':
    main()
