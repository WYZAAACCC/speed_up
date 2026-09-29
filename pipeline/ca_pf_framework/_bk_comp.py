#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_comp.py —— **分量级**诊断：某一快照里每个场的每个连通分量在哪、多大。

用法: python3 _bk_comp.py <dir> [step] [--top N]

为什么需要它：`_bk_measure` 只给"该场有几个分量 + 整体包围尺寸"。
`dry_gs2` 末态报出**场 1 有 4 个分量、沿 a 延伸 5722 nm**（盒子才 6000 nm），
而单根板条种子只有 2400 nm ⇒ 光看聚合量分不清是
  (a) 一根板条被后续形核**切槽**了，
  (b) 场里出现了**孤立碎块**（数值噪声/再初始化伪影），
  (c) 板条真的分裂并**漂移**开了。
本脚本把每个分量单独列出来（体积 + 质心 + 自身三轴尺寸），一次分清。
"""
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from scipy import ndimage as ndi
except Exception as exc:                                        # pragma: no cover
    print('需要 scipy:', exc)
    raise SystemExit(1)


def comps(mask):
    """6-连通分量 ⇒ [(体素数, 质心下标), ...]，按体素降序。"""
    lab, n = ndi.label(mask, structure=np.zeros((3, 3, 3), bool)
                       + np.array([[[0, 0, 0], [0, 1, 0], [0, 0, 0]],
                                   [[0, 1, 0], [1, 1, 1], [0, 1, 0]],
                                   [[0, 0, 0], [0, 1, 0], [0, 0, 0]]], bool))
    out = []
    for i in range(1, n + 1):
        idx = np.argwhere(lab == i)
        out.append((int(idx.shape[0]), idx.mean(0), idx))
    out.sort(key=lambda t: -t[0])
    return out


def main():
    d = sys.argv[1]
    if not os.path.isabs(d):
        d = os.path.join(HERE, d)
    step = None
    top = 4
    # ★ 别用"见到纯数字就当 step"的写法：`--top 5` 里的 5 会被当成 step
    #   （第一版就这么错，症状是"没有匹配的快照"）。
    i = 2
    while i < len(sys.argv):
        x = sys.argv[i]
        if x == '--top':
            top = int(sys.argv[i + 1])
            i += 2
            continue
        if x.isdigit():
            step = int(x)
        i += 1
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    if step is not None:
        snaps = [s for s in snaps if ('%05d' % step) in s]
    if not snaps:
        print('没有匹配的快照:', d)
        return 1

    for s in snaps:
        z = np.load(s)
        reg = z['region']
        N = reg.shape[0]
        L = float(z['L'])
        dx = L / N
        n_hab = np.asarray(z['n_hab'], float)
        w_ax = np.asarray(z['w_ax'], float)
        a_ax = np.asarray(z['a_ax'], float)
        vmap = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
        print('=' * 104)
        print('%s  step=%d  N=%d  dx=%.2f nm  L=%.0f nm'
              % (os.path.basename(s), int(z['step']), N, dx * 1e9, L * 1e9))
        tot = int(reg.size)
        # 母相（0）与空场也要看：空场 = 全场都是 1e3
        for k in [0] + sorted(vmap):
            m = (reg == k)
            nv = int(m.sum())
            if nv == 0:
                print('  场%2d (变体%s): **0 体素**' % (k, vmap.get(k, '—')))
                continue
            cs = comps(m)
            print('  场%2d (变体%s): %d 体素 (%.3f%%)  %d 个分量'
                  % (k, vmap.get(k, '—'), nv, 100.0 * nv / tot, len(cs)))
            for rank, (sz, cm, idx) in enumerate(cs[:top]):
                xyz = (cm + 0.5) * dx
                pn = float(xyz @ n_hab) * 1e9
                pw = float(xyz @ w_ax) * 1e9
                pa = float(xyz @ a_ax) * 1e9
                # 该分量自己的三轴尺寸（子盒精确）
                en = (idx[:, 0].max() - idx[:, 0].min() + 1) * dx
                ew = (idx[:, 1].max() - idx[:, 1].min() + 1) * dx
                ea = (idx[:, 2].max() - idx[:, 2].min() + 1) * dx
                print('       #%d 体素=%-7d 质心 n/w/a=%+8.1f/%+8.1f/%+8.1f nm  '
                      '盒向尺寸 %5.0f/%5.0f/%5.0f nm%s'
                      % (rank + 1, sz, pn, pw, pa, en * 1e9, ew * 1e9, ea * 1e9,
                         '' if rank < top - 1 or len(cs) <= top
                         else '  …(还有 %d 个)' % (len(cs) - top)))
                # ★ 小分量（< 16 体素）**额外查它周围是什么场** —— 用来判断
                #   碎点是"漂到母相里的孤儿"还是"贴在别的板条/三叉线上的伪影"。
                if sz < 16:
                    nb = {}
                    for ax in range(3):
                        for d1 in (-1, 1):
                            sh = idx.copy()
                            sh[:, ax] = (sh[:, ax] + d1) % N
                            v, c = np.unique(reg[sh[:, 0], sh[:, 1], sh[:, 2]],
                                             return_counts=True)
                            for a_, b_ in zip(v, c):
                                nb[int(a_)] = nb.get(int(a_), 0) + int(b_)
                    print('            邻居场: %s'
                          % '  '.join('场%d×%d' % (a_, nb[a_])
                                      for a_ in sorted(nb)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
