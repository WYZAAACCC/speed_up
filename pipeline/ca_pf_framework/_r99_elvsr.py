#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r99_elvsr.py —— **平均场自协调判据够不够？**（纯离线，只读 F 盘已有数据）

## 问题（`BLOCK_SELFAC.md §3` 的框架缺口）

框架的自协调判据是**平均场（体积平均）**的：

@@r(G)=\Big\|\textstyle\sum_i f_i\,\mathrm{dev}\,\varepsilon^0_i\Big\|\Big/\overline{\|\mathrm{dev}\,\varepsilon^0\|}@@

它**只看体积分数、不含空间排布**（`BLOCK_SELFAC.md` 的 **L-4** 自己就记着这一条）。

**若排布不重要** ⇒ `E_el/Vt`（强度量）应当**只由 `r` 决定**（同 `Vt`、同 `r` ⇒ 同能量密度）。
**若排布重要** ⇒ 同一个 `r` 会给出**不同的** `E_el/Vt` ⇒ **平均场判据不充分**，
框架需要补一条**空间项**。这就是"框架是否完善"的直接判据。

## 做法

1. 扫全库所有带 `r_selfac` / `E_el_J` / `Vt` 的 `series.csv`；
2. 取每次运行的**末行**（★ 硬规程③：只引末行）；
3. 报 **`E_el_J/Vt`（强度量，`§84` 规程③）vs `r_selfac`**；
4. 用 `r_norm = (r − r_min(G))/(1 − r_min(G))` 归一化（`_r78` 的 `_simplex_r`）；
5. 看同一 `r` 附近的 `E_el/Vt` 散布有多大。

⚠ **不做因果结论**：不同运行之间 N/Δx/变体集/`el_scale` 都不同 ⇒ 这是**探索性**的，
只回答"**有没有**同 `r` 不同能量密度的例子"。有 ⇒ 平均场不够（存在性证明）；
没有 ⇒ 不能证明平均场够（只是没找到反例）。
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
    """给定变体列表求 `r_min(G)`。"""
    if not vs:
        return float('nan')
    if len(vs) == 1:
        return float(np.linalg.norm(E_ALL[vs[0] - 1])) / SCALE
    return R78._simplex_r(VEC[[v - 1 for v in vs]], SCALE)


def main():
    roots = [os.path.join(HERE, '_exp')]
    rows = []
    for root in roots:
        for p in glob.glob(os.path.join(root, '**', 'series.csv'), recursive=True):
            try:
                rs = list(csv.DictReader(open(p)))
            except Exception:
                continue
            if not rs:
                continue
            h = rs[0]
            need = ('r_selfac', 'E_el_J', 'Vt', 'f_var')
            if not all(c in h for c in need):
                continue
            tot = rs[-1]                      # ★ 只取末行
            try:
                r = float(tot['r_selfac'])
                Eel = float(tot['E_el_J'])
                Vt = float(tot['Vt'])
            except (TypeError, ValueError):
                continue
            if r != r or Eel != Eel or Vt <= 0:
                continue
            fv = [t for t in str(tot.get('f_var', '') or '').split('/') if t.strip()]
            # `f_var` 的顺序是 `letters`（排序后的变体号）；由 `blk_vars`/`n_var_sig`
            # 无法可靠还原 ⇒ 只在 `blk_vars` 给出完整变体集时求 r_min
            vs = []
            for t in str(tot.get('blk_vars', '') or '').split('/'):
                try:
                    vs.append(int(float(t)))
                except ValueError:
                    pass
            vs = sorted(set(vs))
            rel = os.path.relpath(p, HERE)
            # 元数据（N/Δx）用于分组
            mj = os.path.join(os.path.dirname(p), 'meta.json')
            N = dx = None
            if os.path.exists(mj):
                try:
                    m = json.load(open(mj))
                    N = m.get('N')
                    dx = m.get('dx_nm')
                except Exception:
                    pass
            rows.append(dict(rel=rel, r=r, Eel=Eel, Vt=Vt, edens=Eel / Vt,
                             vs=vs, rmin=rmin_of(vs), N=N, dx=dx,
                             step=tot.get('step')))
    print('=' * 112)
    print('_r99_elvsr —— `E_el/Vt`（强度量） vs `r_selfac`（平均场自协调残差）')
    print('=' * 112)
    print('  扫到 %d 个同时有 `r_selfac`/`E_el_J`/`Vt`/`f_var` 的**末行**' % len(rows))
    print()
    if not rows:
        return 1
    rows.sort(key=lambda d: d['r'])
    print('  %-42s %-10s %-12s %-12s %-10s %-8s %s'
          % ('运行', 'r_selfac', 'r_min(G)', 'r_norm', 'E_el/Vt', 'Vt(µm³)', 'G'))
    for d in rows:
        rn = ((d['r'] - d['rmin']) / (1 - d['rmin'])
              if d['rmin'] == d['rmin'] and d['rmin'] < 1 - 1e-12 else float('nan'))
        print('  %-42s %-10.4f %-12.4f %-12.4f %-12.4g %-8.3f %s'
              % (d['rel'].replace('_exp/', ''), d['r'], d['rmin'], rn,
                 d['edens'], d['Vt'] * 1e18, d['vs']))
    print()
    # ---- 同一 r 附近、不同能量密度？ ----
    print('  ---- 有没有"同一个 `r` 却给出很不同的 `E_el/Vt`"的例子 ----')
    best = None
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            dr = abs(rows[i]['r'] - rows[j]['r'])
            if dr > 0.05:
                continue
            a, b = rows[i]['edens'], rows[j]['edens']
            rel = abs(a - b) / max(abs(a), abs(b))
            if best is None or rel > best[0]:
                best = (rel, rows[i], rows[j], dr)
    if best is None:
        print('  在 |Δr| ≤ 0.05 内**没有**成对的运行 ⇒ 数据不足以回答（**不做结论**）')
    else:
        rel, A, B, dr = best
        print('  最大的一对（|Δr| = %.4f）：' % dr)
        print('     %-40s r=%.4f  E_el/Vt=%.4g' % (A['rel'], A['r'], A['edens']))
        print('     %-40s r=%.4f  E_el/Vt=%.4g' % (B['rel'], B['r'], B['edens']))
        print('     ⇒ 能量密度相差 **%.1f%%**' % (100 * rel))
        print()
        if rel > 0.2:
            print('  ⇒ ⚠ **同一个 `r` 给出差 %.0f%% 的能量密度** ⇒ **平均场判据不足以**' % (100 * rel))
            print('     决定弹性能 ⇒ 框架**需要补一条空间项**（`BLOCK_SELFAC` L-4 已预警）。')
        else:
            print('  ⇒ 差异 < 20%% ⇒ 在这个数据子集上**没有**反例（**不能**据此说平均场够）')
    print()
    print('  ⚠ 记账：不同运行的 N/Δx/变体集/`el_scale`/步数都不同 ⇒ 本表是**探索性**的，')
    print('     只用于"**有没有**反例"，**不**用于任何因果或定量结论。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
