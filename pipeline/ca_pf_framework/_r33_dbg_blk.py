#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r33_dbg_blk.py —— 诊断：为什么 `blk_nlath`（不同场数）会大于 `blk_laths`。"""
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import _bk_measure as BM                                        # noqa: E402
from _r33_remeasure import variant_axes                         # noqa: E402
from T16_verify_rve import EPS0, NPF                            # noqa: E402

d = sys.argv[1]
for s in sorted(glob.glob(os.path.join(d, 'snap_*.npz'))):
    z = np.load(s)
    reg = z['region']
    dx = float(z['L']) / reg.shape[0]
    vm = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
    ax = {v: variant_axes(v) for v in sorted(set(vm.values()))}
    b = BM.blocks(reg, dx, vm, eps0_var=EPS0, npf_var=NPF, axes_var=ax)
    print('step=%d  blk_laths=%s  blk_nlath=%s  blk_nruns=%s  blk_vars=%s'
          % (int(z['step']), b['blk_laths'], b['blk_nlath'], b['blk_nruns'],
             b['blk_vars']))
    # 手工复算第一个块
    laths = sorted(int(k) for k in vm)
    for v in sorted(set(vm.values())):
        ks = [k for k in laths if vm[k] == v]
        m = np.zeros(reg.shape, bool)
        for k in ks:
            m |= (reg == k)
        if not m.any():
            continue
        lab, nlab = BM._label_periodic(m)
        for bi in range(1, nlab + 1):
            mb = (lab == bi)
            ids = [k for k in ks if bool((mb & (reg == k)).any())]
            n_b = np.asarray(ax[v][0], float)
            n_b = n_b / np.linalg.norm(n_b)
            ii = np.arange(reg.shape[0]) * dx
            rel = [ii[:, None, None] - 0.0, ii[None, :, None] - 0.0,
                   ii[None, None, :] - 0.0]
            vv = (n_b[0] * rel[0] + n_b[1] * rel[1] + n_b[2] * rel[2])[mb]
            ed = np.arange(vv.min() - 0.5 * dx, vv.max() + 1.5 * dx, dx)
            ids_flat = reg[mb]
            ib = np.digitize(vv, ed) - 1
            prof = [int(np.bincount(ids_flat[ib == t]).argmax())
                    if (ib == t).any() else 0 for t in range(len(ed) - 1)]
            dist = sorted({int(x) for x in prof if int(x) != 0})
            runs = []
            for val in prof:
                if runs and runs[-1][0] == val:
                    runs[-1][1] += 1
                else:
                    runs.append([val, 1])
            runs = [r for r in runs if r[0] != 0]
            print('   V%-2d 块#%d  体积=%-7d  ids=%s(=%d)  不同场=%s(=%d)  段=%d'
                  % (v, bi, int(mb.sum()), ids, len(ids), dist, len(dist),
                     len(runs)))
