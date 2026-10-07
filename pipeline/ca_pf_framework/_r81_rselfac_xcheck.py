#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r81_rselfac_xcheck.py —— **`r_selfac` 落盘值的独立复算**（量具交叉核对）。

为什么：`_r80_psa1_recheck.py` 从**快照**复算出的 `r_selfac` 与
`R30_AUDIT_LEDGER.md §16` 记的数**对不上**（mb2c 复算 0.4998 vs 台账 0.5097；
mb3c 复算 0.5945 vs 台账 0.6437）。**必须查清**：
  * 是台账/CSV 的数错了？
  * 是我复算的口径不同？
  * 还是快照的步号与 CSV 的行号不对应（9p 缓存 / 末行不是末步）？

做法：把 `series.csv` 的**末行**与**全部行的 `r_selfac` 列**读出来，
和按同一 `region` 复算的值逐行比。
"""
from __future__ import annotations

import csv
import glob
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _bk_measure as BM                                    # noqa: E402
from T16_verify_rve import EPS0, NPF                        # noqa: E402

MB = os.path.join(HERE, '_exp', '_bk_mb')


def main():
    tags = sys.argv[1:] or ['eng_mb2', 'eng_mb2b', 'eng_mb2c',
                            'eng_mb3', 'eng_mb3b', 'eng_mb3c']
    print('=' * 112)
    print('_r81_rselfac_xcheck —— `r_selfac` 落盘值 vs 独立复算')
    print('=' * 112)
    for t in tags:
        d = os.path.join(MB, t)
        if not os.path.isdir(d):
            print('%-10s 目录不存在' % t)
            continue
        meta = json.load(open(os.path.join(d, 'meta.json')))
        vmap = {int(k): int(v) for k, v in dict(meta['vmap']).items()}
        # ---- CSV 列 ----
        p = os.path.join(d, 'series.csv')
        rows = list(csv.DictReader(open(p)))
        csv_last = rows[-1]
        csv_r = csv_last.get('r_selfac', '')
        csv_step = csv_last.get('step', '')
        rs = [float(r['r_selfac']) for r in rows if r.get('r_selfac') not in ('', None)]
        # ---- 快照 ----
        fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                    key=lambda q: int(re.search(r'snap_(\d+)\.npz$', q).group(1)))
        snaps = [int(re.search(r'snap_(\d+)\.npz$', q).group(1)) for q in fs]
        line = ['%-10s' % t]
        line.append('CSV 末行 step=%-5s r_selfac=%-10s' % (csv_step, csv_r))
        line.append('CSV 行数=%-4d r 范围 [%.6f, %.6f]'
                    % (len(rows), min(rs), max(rs)) if rs else 'CSV 无 r 列')
        print('  '.join(line))
        print('             快照步号：%s … %s（共 %d）'
              % (snaps[:3], snaps[-3:], len(snaps)))
        # ---- 在**与 CSV 末行同一步**的快照上复算 ----
        tgt = int(float(csv_step)) if csv_step not in ('', None) else snaps[-1]
        if tgt in snaps:
            z = np.load(os.path.join(d, 'snap_%05d.npz' % tgt))
            reg = z['region']
            ax = {}
            import windowB_surface as WS
            from T16_verify_rve import C
            for v in sorted(set(vmap.values())):
                nv = np.asarray(NPF[v], float)
                e0 = np.asarray(EPS0[v - 1], float)
                nref, _, _ = WS.argmin_normal_cached(C, e0)
                R = WS.LevelSetMulti._rank1_axes(e0, nref)
                ax[v] = (nv / np.linalg.norm(nv), np.asarray(R[1], float),
                         np.asarray(R[2], float))
            b = BM.blocks(reg, dx=float(meta['dx_nm']) * 1e-9, vmap=vmap,
                          eps0_var=[np.asarray(e, float) for e in EPS0],
                          npf_var={v: ax[v][0] for v in ax}, axes_var=ax)
            print('             step %d 复算 r_selfac = %.6f   （落盘 %s，差 %+.2e）'
                  '  f_var=%s' % (tgt, b['r_selfac'], csv_r,
                                  b['r_selfac'] - float(csv_r) if csv_r else float('nan'),
                                  b['f_var']))
        else:
            print('             ⚠ CSV 末步 %d **没有**对应快照' % tgt)
        print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
