#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_kvaudit.py --- C-7 的影响面审计：哪些臂的 `K0=--kv` **不在**它播种的变体里？

规则（`_r1_exp.py`）：`--kv` 默认 1，`K0 = a.kv` 是 `measure()` 测的目标变体；
而播种用的是 `--variants` 列表。⇒ 若 `K0 ∉ variants`，则该臂的**几何全是 NaN**。

判据
----
  A-1 对每个 `_exp/*/meta.json` 取出 `kv` 与 `variants`，判定 `kv ∈ variants`？
  A-2 对**判定受影响**的臂，再去 `series.csv` 核实是否真的 `ncell` 全 0 / `L_cal` 全 nan
      （**不能只凭 meta 下结论** —— 万一还有别的机制在起作用）。
  A-3 输出一张"哪些臂可用、哪些作废"的表。
"""
import csv
import glob
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def fnum(r, k):
    try:
        v = float(r[k])
        return v if np.isfinite(v) else np.nan
    except (TypeError, ValueError, KeyError):
        return np.nan


rows = []
for mp in sorted(glob.glob(os.path.join(HERE, '_exp', '*', 'meta.json'))):
    d = os.path.basename(os.path.dirname(mp))
    try:
        m = json.load(open(mp))
    except Exception:                                                # noqa: BLE001
        continue
    kv = m.get('kv')
    vs = m.get('variants')
    if kv is None or vs is None:
        rows.append((d, kv, vs, None, None, None))
        continue
    vs = list(vs) if isinstance(vs, (list, tuple)) else [vs]
    inlist = (kv in vs)
    # A-2：去 CSV 核实
    sp = os.path.join(HERE, '_exp', d, 'series.csv')
    ncell_ok = nc_n = None
    if os.path.exists(sp):
        try:
            rr = list(csv.DictReader(open(sp)))
            nc = np.array([fnum(x, 'ncell') for x in rr])
            lc = np.array([fnum(x, 'L_cal') for x in rr])
            nc_n = int(np.isfinite(nc).sum())
            ncell_ok = bool(np.isfinite(nc).any() and np.nanmax(nc) > 0
                            and np.isfinite(lc).any())
        except Exception:                                            # noqa: BLE001
            pass
    rows.append((d, kv, vs, inlist, ncell_ok, nc_n))

print('=' * 104)
print('%-18s %5s %-22s %9s %12s %s'
      % ('臂', 'kv', 'variants', 'kv∈vs?', 'CSV 有真实读数?', '判定'))
print('-' * 104)
bad = []
for d, kv, vs, inlist, ok, nn in sorted(rows):
    if vs is None:
        print('%-18s %5s %-22s %9s %12s %s' % (d, kv, vs, '—', '—', '（无 variants/kv 字段）'))
        continue
    v = ('**受影响**' if (inlist is False) else '正常')
    if inlist is False:
        bad.append(d)
    print('%-18s %5s %-22s %9s %12s %s'
          % (d, kv, ','.join(map(str, vs)), '✅' if inlist else '⛔',
             '✅' if ok else ('⛔' if ok is False else '—'), v))
print('-' * 104)
print('⇒ 按 meta 判定**受影响**的臂 %d 个：%s' % (len(bad), bad if bad else '（无）'))
print('   注：`e7b_selfac12` 与 `e7_selfac` 天然不受影响（variants 含 1）。')
print('=' * 104)
