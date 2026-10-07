#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r101_elvsr2.py —— `_r99` 的**更正版**：`E_el/Vt` vs `r_selfac`。

## `_r99` 的两个错（**必须先说清楚**）

1. **变体集取错**：我用了 `blk_vars`，但它是**显著块**的变体列表
   （`blocks()` 里 `sig` 按体积降序，且只收 ≥`MIN_SIG_VOX` 的块）
   ⇒ 绝大多数运行只给出 `[1]` ⇒ `r_min(G)` 被算成 **1.0000** ⇒ `r_norm` 全 `nan`。
   **正确来源**：`meta.json` 的 `vmap` 给出变体集 `letters = sorted(set(vmap.values()))`，
   而 `f_var` 正是按 `letters` 顺序拼的（`_bk_measure.blocks()` 的 `letters`）
   ⇒ 只取 `f_var > 0` 的那些变体。
2. **`E_el_J = 0` 当成真值**：那是**没落盘**，不是"弹性能为零"。
   `_r99` 因此报出"同一个 `r` 差 100% 的能量密度"——**那是假阳性**。
   ⇒ 必须**剔除 `E_el_J <= 0`**，并**报出剔除了多少个**。

## 还加了第三条守卫（**跨 Δx 不可比**）

`E_el/Vt`（强度量）依赖**界面宽度**，而界面宽度按体素给 ⇒ **Δx 不同 = 物理不同**
⇒ 只在**同一 `N` 且同一 `dx_nm`** 的运行之间比。
"""
from __future__ import annotations

import csv
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _r78_pairselfac as R78                               # noqa: E402
from T16_verify_rve import EPS0                             # noqa: E402

E_ALL = [np.asarray(e, float) - np.trace(e) / 3.0 * np.eye(3) for e in EPS0]
SCALE = float(np.mean([np.linalg.norm(e) for e in E_ALL]))
VEC = np.array([e.reshape(-1) for e in E_ALL])


def rmin_of(vs):
    if not vs:
        return float('nan')
    if len(vs) == 1:
        return float(np.linalg.norm(E_ALL[vs[0] - 1])) / SCALE
    return R78._simplex_r(VEC[[v - 1 for v in vs]], SCALE)


def main():
    rows, drop_zero, drop_nometa, drop_fvar = [], 0, 0, 0
    for p in glob.glob(os.path.join(HERE, '_exp', '**', 'series.csv'),
                       recursive=True):
        try:
            rs = list(csv.DictReader(open(p)))
        except Exception:
            continue
        if not rs:
            continue
        if not all(c in rs[0] for c in ('r_selfac', 'E_el_J', 'Vt', 'f_var')):
            continue
        d = os.path.dirname(p)
        mj = os.path.join(d, 'meta.json')
        if not os.path.exists(mj):
            drop_nometa += 1
            continue
        try:
            meta = json.load(open(mj))
            vmap = {int(k): int(v) for k, v in dict(meta['vmap']).items()}
        except Exception:
            drop_nometa += 1
            continue
        letters = sorted(set(vmap.values()))
        tot = rs[-1]                                   # ★ 只取末行
        try:
            r = float(tot['r_selfac'])
            Eel = float(tot['E_el_J'])
            Vt = float(tot['Vt'])
        except (TypeError, ValueError):
            continue
        if Eel <= 0.0:                                 # ★ `0` = 没落盘
            drop_zero += 1
            continue
        if not (r == r) or Vt <= 0:
            continue
        fv = []
        for t in str(tot.get('f_var', '') or '').split('/'):
            try:
                fv.append(float(t))
            except ValueError:
                pass
        if len(fv) != len(letters):
            drop_fvar += 1
            continue
        vs = [v for v, f in zip(letters, fv) if f > 0]
        if not vs:
            drop_fvar += 1
            continue
        rows.append(dict(
            rel=os.path.relpath(p, HERE), r=r, Eel=Eel, Vt=Vt,
            edens=Eel / Vt, vs=vs, rmin=rmin_of(vs),
            N=meta.get('N'), dx=meta.get('dx_nm'),
            arr=['%d:%s' % (v, ('%.3f' % f)) for v, f in zip(letters, fv)],
            step=tot.get('step')))
    print('=' * 116)
    print('_r101_elvsr2 —— `E_el/Vt` vs `r_selfac`（`_r99` 的更正版）')
    print('=' * 116)
    print('  入表 %d；剔除：`E_el_J<=0`（没落盘）**%d**、无 `meta.json`/`vmap` **%d**、'
          '`f_var` 对不上 **%d**' % (len(rows), drop_zero, drop_nometa, drop_fvar))
    print()
    if not rows:
        return 1
    # 先按 (N, dx) 分组
    from collections import defaultdict
    grp = defaultdict(list)
    for d in rows:
        grp[(d['N'], d['dx'])].append(d)
    print('  %-16s %-6s %s' % ('(N, Δx nm)', '个数', '组内 r 范围'))
    for k in sorted(grp, key=lambda t: (t[0] or 0, t[1] or 0)):
        g = grp[k]
        rr = [x['r'] for x in g]
        print('  %-16s %-6d [%.4f, %.4f]' % ('(%s, %s)' % k, len(g), min(rr), max(rr)))
    print()
    for k in sorted(grp, key=lambda t: (t[0] or 0, t[1] or 0)):
        g = sorted(grp[k], key=lambda d: d['r'])
        if len(g) < 2:
            continue
        print('  ' + '=' * 112)
        print('  ### 组 (N=%s, Δx=%s nm) —— **组内可比**（同界面宽度）' % k)
        print('  %-46s %-9s %-9s %-9s %-12s %-9s %s'
              % ('运行', 'r', 'r_min(G)', 'r_norm', 'E_el/Vt', 'Vt(µm³)', 'f_var'))
        for d in g:
            rn = ((d['r'] - d['rmin']) / (1 - d['rmin'])
                  if d['rmin'] == d['rmin'] and d['rmin'] < 1 - 1e-12
                  else float('nan'))
            print('  %-46s %-9.4f %-9.4f %-9.4f %-12.4g %-9.3f %s'
                  % (d['rel'].replace('_exp/_bk_mb/', '').replace('_exp/', ''),
                     d['r'], d['rmin'], rn, d['edens'], d['Vt'] * 1e18,
                     ','.join(d['arr'])))
        # 组内找"同 r 不同能量密度"
        best = None
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                dr = abs(g[i]['r'] - g[j]['r'])
                if dr > 0.05:
                    continue
                a, b = g[i]['edens'], g[j]['edens']
                rel = abs(a - b) / max(abs(a), abs(b))
                if best is None or rel > best[0]:
                    best = (rel, g[i], g[j], dr)
        if best is None:
            print('     ⚠ 组内 |Δr| ≤ 0.05 的成对运行**没有** ⇒ 本组数据不足以判')
        else:
            rel, A, B, dr = best
            print('     ⇒ 组内最极端的一对（|Δr| = %.4f）：' % dr)
            print('        %-42s r=%.4f  E_el/Vt=%.4g' % (A['rel'], A['r'], A['edens']))
            print('        %-42s r=%.4f  E_el/Vt=%.4g' % (B['rel'], B['r'], B['edens']))
            print('        能量密度相差 **%.1f%%** ⇒ %s'
                  % (100 * rel, '**平均场判据不足以决定弹性能**'
                     if rel > 0.2 else '差异 <20%（**不能**据此说平均场够）'))
    print()
    print('  ⚠ 仍然的记账：即便同 (N, Δx)，各运行的**变体集/el_scale/步数/构型**也不同')
    print('     ⇒ 本表只回答"**有没有**反例"，**不**做定量或因果结论。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
