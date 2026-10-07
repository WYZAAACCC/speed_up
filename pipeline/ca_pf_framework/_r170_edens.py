#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r170_edens.py —— ★★ **弹性能是"界面主导"还是"平均应变主导"？**

## 为什么这一问很关键

`§118/§119` 实测：**`r_selfac`（平均应变抵消）与 `E_el/Vt` 散得没有规律**
（196 对可比对里比值 0.22–66）。**为什么？** 有两种解释：

* **H-A（平均应变主导）**：`E_el` 主要由"宏观形状应变没抵消"决定 ⇒ `r` 应当代理它
  ⇒ 但实测不代理 ⇒ 说明 H-A 错，或模型里少了什么；
* **H-B（界面主导）**：`E_el` 主要由**界面/共格能**决定（∝ 界面面积）⇒
  `r` 是**体相平均场量**，**本来就管不到界面** ⇒ 不代理是**必然**的。

**⇒ 判据（可证伪）**：
把 `E_el/Vt` 对 `A_int/Vt`（`A_int = f3_area + f2_area`，**界面面积**）回归：

* 若 **`E_el/Vt ≈ c·A_int/Vt`**（相关强、且 `E_el/A_int` 在跨臂间**近似常数**）
  ⇒ **H-B 成立** ⇒ **弹性能是界面主导的**
  ⇒ **`§123` 的 F2 配对面能补法方向正确**（改界面能才动得了 `E_el`）；
* 若相关弱 ⇒ H-B 不成立 ⇒ 需要另找 `E_el` 的主导项。

⚠ **口径**：全部用**强度量**（除以 `Vt`），避免广延量混杂（`§84` 规程③）。
⚠ 只报相关，不建因果。
"""
from __future__ import annotations

import csv
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '_exp')


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float('nan')


def main():
    rows = []
    for p in glob.glob(os.path.join(ROOT, '**', 'series.csv'), recursive=True):
        try:
            rs = list(csv.DictReader(open(p)))
        except Exception:
            continue
        if not rs or not all(c in rs[0] for c in
                             ('E_el_J', 'Vt', 'f3_area_m2')):
            continue
        mj = os.path.join(os.path.dirname(p), 'meta.json')
        meta = {}
        if os.path.exists(mj):
            try:
                meta = json.load(open(mj))
            except Exception:
                meta = {}
        for r in rs:
            E, V = num(r.get('E_el_J')), num(r.get('Vt'))
            a3 = num(r.get('f3_area_m2'))
            a2 = num(r.get('f2_area_m2')) if 'f2_area_m2' in r else 0.0
            if not (np.isfinite(E) and np.isfinite(V) and V > 0
                    and np.isfinite(a3)):
                continue
            if not np.isfinite(a2):
                a2 = 0.0
            A = a3 + a2
            if E <= 0 or A <= 0:
                continue
            rows.append(dict(tag=os.path.basename(os.path.dirname(p)),
                             N=meta.get('N'), dx=meta.get('dx_nm'),
                             step=num(r.get('step')),
                             ed=E / V, ad=A / V, eperA=E / A))
    print('=' * 108)
    print('_r170 —— 弹性能是"界面主导"还是"平均应变主导"？（%d 个数据点）' % len(rows))
    print('=' * 108)
    if len(rows) < 10:
        print('  ⚠ 数据点太少'); return 1
    ED = np.array([r['ed'] for r in rows])
    AD = np.array([r['ad'] for r in rows])
    EA = np.array([r['eperA'] for r in rows])
    print('  %-28s %-14s %-14s %s' % ('量', '中位', 'Q1', 'Q3'))
    for lab, v in (('`E_el/Vt`（J/m³）', ED), ('`A_int/Vt`（1/m）', AD),
                   ('**`E_el/A_int`（J/m²）**', EA)):
        print('  %-28s %-14.4g %-14.4g %.4g'
              % (lab, np.median(v), np.percentile(v, 25), np.percentile(v, 75)))
    print()
    c_all = float(np.corrcoef(ED, AD)[0, 1])
    print('  **全库相关 `E_el/Vt` vs `A_int/Vt` = %+.4f**' % c_all)
    print()
    # ---- 分组（同 N/Δx）内的相关 ----
    from collections import defaultdict
    g = defaultdict(list)
    for r in rows:
        g[(r['N'], round(r['dx'], 3) if r['dx'] else None)].append(r)
    print('  ---- 同 `(N,Δx)` 组内的相关（去掉分辨率这个共同因子）----')
    print('     %-22s %-7s %s' % ('(N, Δx)', '点数', '组内相关'))
    cs = []
    for k in sorted(g, key=lambda t: (t[0] or 0)):
        arr = g[k]
        if len(arr) < 20:
            continue
        e = np.array([a['ed'] for a in arr])
        a_ = np.array([a['ad'] for a in arr])
        c = float(np.corrcoef(e, a_)[0, 1])
        cs.append(c)
        print('     %-22s %-7d %+.4f' % ('(%s, %s)' % k, len(arr), c))
    print()
    print('  ---- ★ **臂内**相关（配置固定，只有形貌在演化）—— **这才是干净的对照** ----')
    print('     ⚠ 第一版我按 `(N,Δx)` 分组 ⇒ 组内**混着很多不同构型**（单根/三根/六根、')
    print('       不同 `--el-scale`、不同几何）⇒ `(96,62.5)` 那一组 361 个点里相关只有 +0.08。')
    print('       正确做法：**每条臂内部**做时间序列相关（配置不变）。')
    from collections import defaultdict as _dd
    per = _dd(list)
    for r in rows:
        per[r['tag']].append(r)
    cs2 = []
    print('     %-24s %-7s %-10s %s' % ('臂', '点数', '臂内相关', '`E_el/A_int` 变化'))
    for tag in sorted(per):
        arr = sorted(per[tag], key=lambda a: a['step'])
        if len(arr) < 8:
            continue
        e = np.array([a['ed'] for a in arr])
        a_ = np.array([a['ad'] for a in arr])
        ea = np.array([a['eperA'] for a in arr])
        if np.std(e) < 1e-30 or np.std(a_) < 1e-30:
            continue
        c = float(np.corrcoef(e, a_)[0, 1])
        cs2.append(c)
        print('     %-24s %-7d %+-10.4f %.2f×'
              % (tag[:24], len(arr), c, ea.max() / max(ea.min(), 1e-300)))
    print()
    print('  ---- 判读 ----')
    med_c = float(np.median(cs2)) if cs2 else float('nan')
    n_hi = int(sum(1 for c in cs2 if c > 0.8))
    print('     **臂内相关**：中位 **%+.4f**；> 0.8 的臂 **%d / %d**'
          % (med_c, n_hi, len(cs2)))
    ea_spread = float(np.percentile(EA, 75) / max(np.percentile(EA, 25), 1e-300))
    print('     `E_el/A_int` 跨臂 Q3/Q1 = %.2f 倍' % ea_spread)
    if med_c > 0.8:
        print('  ⇒ ✅ **H-B 成立**：**臂内** `E_el/Vt` 与**界面面积密度**强相关 ⇒')
        print('     **弹性能是界面主导的** ⇒ `r`（体相平均场量）**本来就代理不了它** ⇒')
        print('     **`§123` 的"改界面能"补法方向正确**（要动 `E_el` 就得动界面能）。')
    else:
        print('  ⇒ ⚠ 臂内相关也只有 %+.2f ⇒ H-B **不成立** ⇒ `E_el` 的主导项另有其物。' % med_c)
    print()
    print('  ⚠ 只报相关；`A_int` 用 `f3_area + f2_area`（都是**无偏面积口径**）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
