#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_armhealth.py --- 所有算例的**守卫健康表**（修正 `nb` 遮蔽 bug 之后）

为什么需要
----------
`_r1_analyze.py` 里 `nb`（盒壁计数）被后一行 `sb, r2b, nb = reg(...)` **覆盖**
⇒ 每个算例都会打出「⛔ 但 G-1 已触发」，**即使守卫汇总写着"盒壁 0 次"**。
⇒ 「哪些臂的形貌读数真的无效」此前**无法从分析器输出判断**。

本脚本**直接读 `series.csv` 的守卫列**，不经过分析器，给出可信的表：
  * `box_touch>0` 的步数（G-1）与**首次**触发的 step；
  * `ncomp>1` 的步数（G-2）；
  * `band_bad>0` 的步数（G-3）；
  * **最后一步有效数据**的 step 与 `fill_cal`（C-5 判据用的量）。
"""
import csv
import os
import re

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r'^\s*\[\s*(\d+)\]\s')
EXCLUDE = ('_csvfix_smoke', 'paircorr', 'pairsat', 'drive')


def fnum(r, k):
    try:
        v = float(r[k])
        return v if np.isfinite(v) else np.nan
    except (TypeError, ValueError, KeyError):
        return np.nan


def every_of(d):
    lp = os.path.join(HERE, '_exp', d, 'log.txt')
    if os.path.exists(lp):
        mk = [int(m.group(1)) for m in
              (PAT.match(l) for l in open(lp, errors='replace')) if m]
        if len(mk) > 2:
            return float(np.median(np.diff(mk)))
    return 4.0


rows_out = []
for d in sorted(os.listdir(os.path.join(HERE, '_exp'))):
    if any(x in d for x in EXCLUDE):
        continue
    p = os.path.join(HERE, '_exp', d, 'series.csv')
    if not os.path.exists(p):
        continue
    try:
        rows = list(csv.DictReader(open(p)))
    except Exception:                                            # noqa: BLE001
        continue
    if len(rows) < 3:
        continue
    ev = every_of(d)
    st = np.arange(len(rows), dtype=float) * ev
    g1 = np.array([fnum(r, 'box_touch') for r in rows]) > 0
    g2 = np.array([fnum(r, 'ncomp') for r in rows]) > 1
    g3 = np.array([fnum(r, 'band_bad') for r in rows]) > 0
    good = ~(g1 | g2 | g3)
    fc = np.array([fnum(r, 'fill_cal') for r in rows])
    if not np.isfinite(fc).any():                 # 旧算例没有这一列，现算
        L = np.array([fnum(r, 'L_cal') for r in rows])
        W = np.array([fnum(r, 'W_cal') for r in rows])
        T = np.array([fnum(r, 'T_cal') for r in rows])
        V = np.array([fnum(r, 'V') for r in rows])
        fc = V / np.maximum(L * W * T, 1e-30)
    rows_out.append(dict(
        d=d, n=len(rows), last=st[-1], ev=ev,
        ng1=int(g1.sum()), ng2=int(g2.sum()), ng3=int(g3.sum()),
        g1_first=(float(st[g1][0]) if g1.any() else None),
        nvalid=int(good.sum()),
        lastvalid=(float(st[good].max()) if good.any() else None),
        fc_first=(float(fc[0]) if np.isfinite(fc[0]) else float('nan')),
        fc_last=(float(fc[np.where(np.isfinite(fc))[0][-1]])
                 if np.isfinite(fc).any() else float('nan'))))

hdr = ('%-18s %5s %7s %6s %6s %6s %9s %9s %8s %8s'
       % ('算例', 'n', '末step', 'G-1', 'G-2', 'G-3', 'G-1首次', '末有效',
          'fill_cal初', 'fill_cal末'))
print('=' * 108)
print(hdr)
print('=' * 108)
for r in sorted(rows_out, key=lambda x: x['d']):
    print('%-18s %5d %7g %6d %6d %6d %9s %9s %8.3f %8.3f'
          % (r['d'], r['n'], r['last'], r['ng1'], r['ng2'], r['ng3'],
             ('%g' % r['g1_first']) if r['g1_first'] is not None else '—',
             ('%g' % r['lastvalid']) if r['lastvalid'] is not None else '—',
             r['fc_first'], r['fc_last']))
print('=' * 108)
clean = [r['d'] for r in rows_out if r['ng1'] == 0]
touch = [r['d'] for r in rows_out if r['ng1'] > 0]
print('✅ 全程未触盒壁（G-1=0）的算例 %d 个：%s' % (len(clean), ', '.join(clean)))
print('⛔ 触过盒壁（G-1>0）的算例 %d 个：%s' % (len(touch), ', '.join(touch)))
print('\n⚠ `_r1_analyze.py` 的 `nb` 遮蔽 bug 已修（正/负对照已过），')
print('  此前它对**每个**算例都打「G-1 已触发」⇒ 请以本表为准。')
print('=' * 108)
