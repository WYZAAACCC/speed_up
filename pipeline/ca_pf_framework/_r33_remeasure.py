#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r33_remeasure.py —— **用当前量具在落盘快照上重测块表**（用户要求的那条路）。

用法：
    python3 _r33_remeasure.py _exp/_bk_mb/dry_mb1s
    python3 _r33_remeasure.py _exp/_bk_mb/dry_mb1 --sel-variant 1

输出：每个快照一行 —— `blk_laths`（不同场数，主口径）/ `blk_nlath`（同）
     / `blk_nruns`（段数，诊断；与 nlath 不等 ⇒ 柱剖面有噪声）
     / `blk_alen_nm`（沿**该块自己的**长轴 a 的跨度）/ `blk_span_nm`（沿自身 n*）。

★ 这就是"测量工具有问题也能事后重测"的实际入口：只吃 `region` + `vmap` + 变体表。
"""
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import _bk_measure as BM                                        # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NPF                         # noqa: E402


def variant_axes(v):
    n = np.asarray(NPF[v], float); n = n / np.linalg.norm(n)
    nref, _, _ = W.argmin_normal_cached(C, np.asarray(EPS0[v - 1], float))
    R = W.LevelSetMulti._rank1_axes(np.asarray(EPS0[v - 1], float), nref)
    a = np.asarray(R[1], float); a = a / np.linalg.norm(a)
    w = np.asarray(R[2], float); w = w / np.linalg.norm(w)
    return n, a, w


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    d = sys.argv[1]
    sel = 1
    if '--sel-variant' in sys.argv:
        sel = int(sys.argv[sys.argv.index('--sel-variant') + 1])
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    if not snaps:
        raise SystemExit('✗ %s 下没有快照' % d)
    print('目录 %s（%d 个快照）；`sel-variant`=V%d' % (d, len(snaps), sel))
    print('  %-7s %-9s %-10s %-10s %-10s %-11s %-11s %s'
          % ('step', 'nblk_sig', 'blk_laths', 'blk_nlath', 'blk_nruns',
             'V%d alen nm' % sel, 'V%d span nm' % sel, 'blk_vars'))
    for s in snaps:
        z = np.load(s)
        reg = z['region']
        dx = float(z['L']) / reg.shape[0]
        vm = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
        ax = {v: variant_axes(v) for v in sorted(set(vm.values()))}
        b = BM.blocks(reg, dx, vm, eps0_var=EPS0, npf_var=NPF, axes_var=ax)
        vs = [int(x) for x in (b.get('blk_vars') or '').split('/') if x]
        al = [x for x in (b.get('blk_alen_nm') or '').split('/') if x]
        sp = [x for x in (b.get('blk_span_nm') or '').split('/') if x]
        i = vs.index(sel) if sel in vs else None
        print('  %-7d %-9d %-10s %-10s %-10s %-11s %-11s %s'
              % (int(z['step']), int(b['nblk_sig']), b.get('blk_laths', ''),
                 b.get('blk_nlath', ''), b.get('blk_nruns', ''),
                 (al[i] if i is not None and i < len(al) else '—'),
                 (sp[i] if i is not None and i < len(sp) else '—'),
                 b.get('blk_vars', '')))


if __name__ == '__main__':
    main()
