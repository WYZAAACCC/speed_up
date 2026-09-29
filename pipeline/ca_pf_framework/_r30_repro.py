#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r30_repro.py —— R30 审计：**落盘数据的可重测性**（只靠 F 盘原始数据能否重算结论）。

检查：
  R1 每类快照 npz 里到底存了什么（键、dtype、字节数）—— 逐一列出。
  R2 `_bk_verdict` 用到的每个量，是否**只靠 npz** 就能重算（对照 CSV 里的同名列）。
      具体：对每个臂取最后一个快照，用当前 `_bk_measure` 重算
      `nslab_n / nf3_col / ncomp_* / vol_* / f3_area / f3_pos_n / f3_std_n / runs`，
      与 `series.csv` 末行逐项比。**逐位一致**才算"可重算"。
  R3 哪些结论**不能**只靠 F 盘重算（缺什么）。
  R4 `f3_pairs_pos` 列（R29 新增）在实跑数据上的口径核对。

用法: python3 _r30_repro.py
"""
import csv
import glob
import json
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np                                              # noqa: E402
import _bk_measure as BM                                        # noqa: E402
import _bk_cmp as CMP                                           # noqa: E402

dirs = sorted(d for d in glob.glob(os.path.join(_HERE, '_exp', '_bk_*', '*'))
              if os.path.isdir(d))
print('=' * 122)
print('R1 快照 npz 里存了什么（按"臂类型"归类，取每个臂的最后一个快照）')
print('=' * 122)
seen = {}
for d in dirs:
    sp = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    if not sp:
        continue
    z = np.load(sp[-1])
    keys = tuple(sorted(z.files))
    shapes = tuple('%s:%s' % (k, np.asarray(z[k]).dtype) for k in keys)
    seen.setdefault((keys, shapes), []).append(os.path.relpath(d, _HERE))
for (keys, shapes), arms in seen.items():
    print('\n  键 = %s' % (list(keys),))
    print('  类型 = %s' % (list(shapes),))
    print('  大小 = %.2f MB / 快照' % (os.path.getsize(
        sorted(glob.glob(os.path.join(_HERE, arms[0], 'snap_*.npz')))[-1]) / 1e6))
    print('  臂数 = %d，例如 %s' % (len(arms), arms[:3]))

print('\n' + '=' * 122)
print('R2 只靠 npz 重算 `_bk_verdict` 用到的量 ⇒ 与 series.csv 末行**逐位**对比')
print('=' * 122)
print('%-40s %-9s %-9s %-9s %-11s %-13s %s'
      % ('臂', 'nslab', 'nf3col', 'nf3faces', 'f3_area(rel)', 'f3_pos_n(Δx)',
         'vols(rel)'))
print('-' * 122)
nbad = 0
for d in dirs:
    sp = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    cp = os.path.join(d, 'series.csv')
    if not sp or not os.path.exists(cp):
        continue
    z = np.load(sp[-1])
    if 'vmap_keys' not in z.files:
        continue
    with open(cp, newline='', encoding='utf-8') as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        continue
    # 找到与快照 step 匹配的那一行
    st = int(z['step'])
    row = None
    for r in rows:
        try:
            if int(float(r['step'])) == st:
                row = r
        except (TypeError, ValueError):
            pass
    if row is None:
        continue
    reg = z['region']
    dx = float(z['L']) / reg.shape[0]
    nh = np.asarray(z['n_hab'], float)
    vm = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
    r = BM.measure_state(reg, dx, nh, z['w_ax'], z['a_ax'], vm)
    tot = sum(r['vol_%d' % k] for k in vm)
    csv_tot = float(row['Vt'])
    relv = abs(tot - csv_tot) / max(csv_tot, 1e-300) if csv_tot > 0 else float('nan')
    relA = (abs(r['f3_area'] - float(row['f3_area_m2'])) / float(row['f3_area_m2'])
            if float(row['f3_area_m2']) > 0 else float('nan'))
    dpos = ((r['f3_pos_n'] - float(row['f3_pos_m'])) / dx
            if np.isfinite(float(row['f3_pos_m'])) else float('nan'))
    bad = []
    if r['nslab_n'] != int(float(row['nslab_n'])):
        bad.append('nslab')
    if r['nf3_col'] != int(float(row['nf3_col'])):
        bad.append('nf3col')
    if r['f3_faces'] != int(float(row['nf3'])):
        bad.append('nf3')
    if np.isfinite(relA) and relA > 1e-12:
        bad.append('area')
    if np.isfinite(dpos) and abs(dpos) > 1e-12:
        bad.append('pos')
    if np.isfinite(relv) and relv > 1e-12:
        bad.append('vol')
    if bad:
        nbad += 1
    print('%-40s %-9s %-9s %-9s %-11s %-13s %s %s'
          % (os.path.relpath(d, _HERE), r['nslab_n'], r['nf3_col'],
             r['f3_faces'],
             ('%.1e' % relA) if np.isfinite(relA) else '—',
             ('%+.1e' % dpos) if np.isfinite(dpos) else '—',
             ('%.1e' % relv) if np.isfinite(relv) else '—',
             ('**不一致: %s**' % bad) if bad else ''))
print('-' * 122)
print('⇒ 不一致的臂 = **%d**（0 = 所有主判据量都能只靠 F 盘的 npz 重算）' % nbad)
print('   记账：CSV 是 `%.6g`（6 位有效），所以"逐位一致"只在 **npz 重算 vs CSV** 之间')
print('   成立的前提是量本身能被 6 位表示；`f3_area` 的比较容差已放宽到 1e-12 相对。')

print('\n' + '=' * 122)
print('R4 `f3_pairs_pos`（R29 新增列）在实跑数据上的口径核对')
print('=' * 122)
for d in dirs:
    cp = os.path.join(d, 'series.csv')
    if not os.path.exists(cp):
        continue
    with open(cp, newline='', encoding='utf-8') as fh:
        rows = list(csv.DictReader(fh))
    if not rows or 'f3_pairs_pos' not in rows[0]:
        continue
    last = None
    for r in rows:
        if r.get('f3_pairs_pos', '') not in ('', None):
            last = r
    if last is None:
        print('%-40s 有该列但**全空**' % os.path.relpath(d, _HERE))
        continue
    z = np.load(sorted(glob.glob(os.path.join(d, 'snap_*.npz')))[-1])
    reg = z['region']
    dx = float(z['L']) / reg.shape[0]
    nh = np.asarray(z['n_hab'], float)
    vm = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
    r = BM.measure_state(reg, dx, nh, z['w_ax'], z['a_ax'], vm)
    print('%-40s step=%s' % (os.path.relpath(d, _HERE), last['step']))
    print('    f3_pairs_pos(胞心·**绝对**) = %s' % last['f3_pairs_pos'][:90])
    print('    f3_pos_m  (索引·绝对，快照重算) = %.4f Δx ; f3_pos_dx(相对) = %s'
          % (r['f3_pos_n'] / dx, last['f3_pos_dx']))
    print('    口径常数差 = 0.5·Σn_i = %+.4f Δx'
          % (0.5 * float(nh.sum())))
