#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r76_remeasure.py —— **离线重测**（只读 F 盘原始快照，不跑仿真）。

## 为什么

用户硬要求：「将仿真过程的全部数据保存在 F 盘下 …… 之后也能使用新的
测量工具重新测量得到正确的结果，并且在原始数据上查错。」
本脚本正是这件事的一次执行：R75 的 `series.csv` 里**没有**逐块口径
（`blocks()` 算了 `blk_nprof`/`blk_nruns`，`_blk_cols` 没转发 ⇒ **P1-33**），
而快照里有 `region` + `meta.json` 里有 `vmap`/`npf`/`eps0`
⇒ **可以完全不重跑仿真，把逐块口径补出来。**

## 口径

对每个 `snap_*.npz`：

  1. `blocks(region, dx, vmap, npf_var=NPF, axes_var=ax)` —— 逐块、沿**该块自己的 n***
     投影分箱、取每箱众数场号，再数：
       * `blk_nlath`  该连通分量**覆盖的场数**（**上界**；层并成一片也照样报 3）
       * `blk_nprof`  剖面众数里**出现过的不同场数**（**主口径**，对分箱噪声免疫）
       * `blk_nruns`  剖面**连续段数**（诊断；分箱抖动会**多读**）
  2. 与 `series.csv` 里当时落盘的 `nslab_n`（全局柱、并集质心 ⇒ 多块下**无效**）并排。

## 用法

    python _r76_remeasure.py dry_mb2fp10 [dry_mb2fp0 ...]
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _bk_measure as BM                                    # noqa: E402
import windowB_surface as WS                                # noqa: E402
import windowB_wulff as W                                   # noqa: E402
from T16_verify_rve import C, EPS0, NPF                     # noqa: E402

MB = os.path.join(HERE, '_exp', '_bk_mb')


def load_meta(d):
    with open(os.path.join(d, 'meta.json')) as f:
        return json.load(f)


def build_inputs(meta):
    """从 `meta.json` + `T16_verify_rve` 的 Burgers 表重建 `blocks()` 的入参。

    ⚠ 逐项断言：**取不到就抛**，不静默回退 —— 否则量具会退化成一个"看起来在跑"
      的空壳（本仓库 `mu0` 守卫就是这么静默失效过一次的）。
    ⚠ `meta.json` 里**只有** `laths[0]` 的 `n_hab/w_ax/a_ax` ⇒ 块 1（镜面变体）
      的轴**必须**从 `NPF[v]` 重算，**不能**复用 `meta['n_hab']`。
      这正是 `_bk_exp.py:890` 那个调用点的缺陷来源。
    """
    vmap = {int(k): int(v) for k, v in dict(meta['vmap']).items()}
    if not vmap:
        raise KeyError('meta.json 的 vmap 为空')
    ax = {}
    for v in sorted(set(vmap.values())):
        n_b = np.asarray(NPF[v], float)
        if n_b.shape != (3,):
            raise ValueError('NPF[%d] 形状 %s != (3,)' % (v, n_b.shape))
        e0 = np.asarray(EPS0[v - 1], float)
        nref, _, _ = WS.argmin_normal_cached(C, e0)
        R = WS.LevelSetMulti._rank1_axes(e0, nref)
        ax[v] = (n_b / np.linalg.norm(n_b),
                 np.asarray(R[1], float), np.asarray(R[2], float))
    npf = {v: ax[v][0] for v in ax}
    # ⚠ `blocks()` 的 `eps0_var` 是**按「变体号-1」索引的列表**
    #   （`_bk_measure.py:446` `range(len(eps0_var))` 与 `:454` `E[v-1]`），
    #   **不是**按场号的字典 —— 传字典会 KeyError: 0。
    eps0 = [np.asarray(e, float) for e in EPS0]
    return vmap, npf, eps0, ax


def series_col(d, name):
    """从 `series.csv` 取某列（`step -> 值`），用于并排对照。"""
    import csv
    p = os.path.join(d, 'series.csv')
    if not os.path.exists(p):
        return {}
    out = {}
    with open(p) as f:
        for r in csv.DictReader(f):
            try:
                out[int(r['step'])] = r.get(name, '')
            except (KeyError, ValueError):
                pass
    return out


def step_of(path):
    m = re.search(r'snap_(\d+)\.npz$', os.path.basename(path))
    return int(m.group(1)) if m else -1


def run(tag, dx, vmap, npf, eps0, ax):
    d = os.path.join(MB, tag)
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')), key=step_of)
    if not snaps:
        print('  %s：无快照' % tag)
        return None
    ns = series_col(d, 'nslab_n')
    print('=' * 112)
    print('### %s   共 %d 个快照    %s' % (tag, len(snaps), d))
    print('  %-7s %-9s %-8s %-9s %-9s %-9s %-9s %-8s %s'
          % ('step', 'nblk_sig', 'vars', 'nlath↑界', 'nprof★', 'nruns诊',
             'span_nm', 'nslab_n', 'blk_laths'))
    res = []
    for sp in snaps:
        st = step_of(sp)
        z = np.load(sp)
        if 'region' not in z.files:
            print('  step %-4d ⚠ 快照无 `region`（键：%s）' % (st, z.files))
            continue
        reg = z['region']
        b = BM.blocks(reg, dx, vmap, eps0_var=eps0, npf_var=npf, axes_var=ax)
        row = dict(step=st, nblk=int(b['nblk_sig']), vars=b['blk_vars'],
                   nlath=b.get('blk_nlath', ''), nprof=b.get('blk_nprof', ''),
                   nruns=b.get('blk_nruns', ''), span=b.get('blk_span_nm', ''),
                   nslab=ns.get(st, ''), laths=b['blk_laths'])
        res.append(row)
        if st % 100 == 0 or st == 0 or st == step_of(snaps[-1]):
            print('  %-7d %-9d %-8s %-9s %-9s %-9s %-9s %-8s %s'
                  % (st, row['nblk'], row['vars'], row['nlath'], row['nprof'],
                     row['nruns'], row['span'], row['nslab'], row['laths']))
    return res


def per(s):
    s = (s or '').strip()
    return [int(float(t)) for t in s.split('/') if t.strip()] if s else []


def main():
    tags = sys.argv[1:] or ['mb2fp10', 'mb2fp0']
    allres = {}
    for t in tags:
        d = os.path.join(MB, t)
        meta = load_meta(d)
        dx = float(meta['dx_nm']) * 1e-9
        vmap, npf, eps0, ax = build_inputs(meta)
        print('%-10s N=%s dx=%.3f nm  vmap=%s' % (t, meta.get('N'), dx * 1e9, vmap))
        allres[t] = run(t, dx, vmap, npf, eps0, ax)
    # ---- 终态并排 ----
    if len(tags) >= 2 and all(r for r in allres.values()):
        print()
        print('=' * 112)
        print('### 终态并排（★ 主口径 = `blk_nprof`）')
        print('  %-10s %-9s %-9s %-9s %-9s %-9s %s'
              % ('臂', 'vars', 'nlath↑界', 'nprof★', 'nruns诊', 'nblk_sig', 'nslab_n'))
        for t in tags:
            r = allres[t][-1]
            print('  %-10s %-9s %-9s %-9s %-9s %-9s %s'
                  % (t, r['vars'], r['nlath'], r['nprof'], r['nruns'],
                     r['nblk'], r['nslab']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
