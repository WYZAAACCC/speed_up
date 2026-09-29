#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30-AUDIT ★ 端到端重测对照（**只读，不改任何已有文件**）。

目的：拿**已经跑完**的算例，用它落盘的 `snap_*.npz` 离线重算 `series.csv` 里
**同一个 step** 上的量，逐值比对。

口径（必须与 `_bk_exp.py:690-726` 逐行一致）：
  · `nslab_n` / `nf3_col` / `runs`  ← `_bk_measure.measure_state`
  · `f3_area_m2` = `mm['f3_area']`（**无偏 Cauchy 面积**，`_bk_measure.py:406`）
  · `f3_area_stair` = `mm['f3_area_stair']`（阶梯口径）
  · `nf3` = `mm['f3_faces']`
  · `f3_pos_m` = `mm['f3_pos_n']`（F3 胞的 `n*`·x **均值**，**角点坐标口径**）
  · `f3_pos_dx` = (`f3_pos_m` − `P0`)/dx，`P0` = **第一个非 nan 的 `f3_pos_m`**
    （`_bk_exp.py:626-628`）
  · `f3_std_m` = `mm['f3_std_n']`
  · `vols` / `ths` / `n_lath` / `w_lath` / `a_lath` 逐场

用法:
  python3 _r30_remeasure.py <算例目录>
"""
import csv
import os
import sys
import glob

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import _bk_measure as BM                                          # noqa: E402

REL = 1.0          # 与 `_bk_exp.py` 一致：`%.6g` 只有 6 位有效数字


def fnum(x, d=float('nan')):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return d
    return v


def relerr(a, b):
    if not (np.isfinite(a) and np.isfinite(b)):
        return float('nan')
    if abs(b) < 1e-300:
        return 0.0 if abs(a) < 1e-300 else float('inf')
    return abs(a - b) / abs(b)


def slash(s):
    return [x for x in s.split('/') if x != ''] if s else []


def main(d):
    p0_override = None
    if '--p0' in sys.argv:
        p0_override = float(sys.argv[sys.argv.index('--p0') + 1])
    sc = os.path.join(d, 'series.csv')
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    if not os.path.exists(sc) or not snaps:
        print('缺 series.csv 或 snap_*.npz: %s' % d)
        return 1
    with open(sc, newline='') as fh:
        rows = list(csv.DictReader(fh))
    by_step = {int(r['step']): r for r in rows}
    print('算例 %s' % d)
    print('  CSV 行数=%d  snap 数=%d  步=%s' % (len(rows), len(snaps),
                                              [int(np.load(p)['step'])
                                               for p in snaps]))

    # ---- 先扫一遍 P0（口径与 `_bk_exp.py:626-628` 相同：按时间序取首个非 nan）----
    P0 = None
    cache = {}
    for p in snaps:
        z = np.load(p)
        st = int(z['step'])
        reg = z['region']
        dx = float(z['L']) / reg.shape[0]
        vmap = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
        mm = BM.measure_state(reg, dx, z['n_hab'], z['w_ax'], z['a_ax'], vmap)
        cache[st] = (mm, vmap, dx)
        if P0 is None and np.isfinite(mm['f3_pos_n']):
            P0 = mm['f3_pos_n']
        z.close()
    if P0 is None:
        print('  ⚠ 所有快照的 f3_pos_n 都是 nan ⇒ 无 F3 界面，Δpos 不可比')
    else:
        print('  P0 (f3_pos_n 首个非 nan) = %.12g m' % P0)
    if p0_override is not None:
        print('  ★ P0 覆盖（反解 CSV 得到的真值）= %.12g m' % p0_override)
        P0 = p0_override

    nv = max(max(cache[s][1]) for s in cache)
    hdr = ['量', 'CSV', '离线重算', '|Δ|/|CSV|']
    print('  %-22s %-22s %-22s %s' % tuple(hdr))
    print('  ' + '-' * 84)
    worst = []
    for st in sorted(cache):
        if st not in by_step:
            print('  step %-6d （CSV 无此步，跳过）' % st)
            continue
        r = by_step[st]
        mm, vmap, dx = cache[st]
        pairs = [
            ('nslab_n', float(mm['nslab_n']), fnum(r['nslab_n'])),
            ('nf3_col', float(mm['nf3_col']), fnum(r['nf3_col'])),
            ('nf3(=f3_faces)', float(mm['f3_faces']), fnum(r['nf3'])),
            ('f3_area_m2', mm['f3_area'], fnum(r['f3_area_m2'])),
            ('f3_area_stair', mm['f3_area_stair'], fnum(r['f3_area_stair'])),
            ('f3_pos_m', mm['f3_pos_n'], fnum(r['f3_pos_m'])),
            ('f3_std_m', mm['f3_std_n'], fnum(r['f3_std_m'])),
            ('nreg_used', float(mm['nreg_used']), fnum(r['nreg_used'])),
            ('Vt', sum(mm['vol_%d' % k] for k in range(1, nv + 1)),
             fnum(r['Vt'])),
        ]
        if P0 is not None and np.isfinite(mm['f3_pos_n']) \
                and np.isfinite(fnum(r['f3_pos_dx'])):
            pairs.append(('f3_pos_dx', (mm['f3_pos_n'] - P0) / dx,
                          fnum(r['f3_pos_dx'])))
        # 逐场
        cv = slash(r.get('vols', ''))
        ct = slash(r.get('ths', ''))
        for k in range(1, nv + 1):
            if k - 1 < len(cv):
                pairs.append(('vol_%d' % k, mm['vol_%d' % k] * 1e18,
                              fnum(cv[k - 1])))
            if k - 1 < len(ct):
                pairs.append(('th_%d(nm)' % k, mm['n_%d' % k] * 1e9,
                              fnum(ct[k - 1])))
        if 'n_lath' in r:
            occ = [k for k in range(1, nv + 1) if mm['vol_%d' % k] > 0]
            med = (lambda f: float(np.median([f(k) for k in occ]))
                   if occ else 0.0)
            # ⚠⚠ 单位陷阱（本审计第一版踩了）：CSV 的 `n_lath/w_lath/a_lath`
            #   是**米**（`_bk_exp.py:714-716` 直接写 `mm['n_%d']`，没有 ×1e9），
            #   而 `ths` 列才是 nm（`_bk_exp.py:702` 有 `*1e9`）。
            pairs.append(('n_lath(m)', med(lambda k: mm['n_%d' % k]),
                          fnum(r['n_lath'])))
            pairs.append(('w_lath(m)', med(lambda k: mm['w_%d' % k]),
                          fnum(r['w_lath'])))
            pairs.append(('a_lath(m)', med(lambda k: mm['a_%d' % k]),
                          fnum(r['a_lath'])))
        print('  ### step %d' % st)
        for nm, a, b in pairs:
            e = relerr(a, b)
            flag = ''
            if np.isfinite(e) and e > 1e-5:
                flag = '   <== 差 %.2e' % e
            print('  %-22s %-22.10g %-22.10g %s%s'
                  % (nm, b, a, ('%.3e' % e) if np.isfinite(e) else 'nan',
                     flag))
            if np.isfinite(e):
                worst.append((e, st, nm))
    print()
    print('  === 相对差最大的 10 条 ===')
    for e, st, nm in sorted(worst, reverse=True)[:10]:
        print('   %-22s step=%-6d rel=%.4e' % (nm, st, e))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
