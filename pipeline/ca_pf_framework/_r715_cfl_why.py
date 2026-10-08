#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r715_cfl_why.py —— **只读**：把 `cfl_used` 反解成 `dG_max/Δf`（规范 §6.3 要的那个比值）。

## 口径（与 `series.csv` 同名列一致，`_bk_exp.py:2630/:2639/:3589`）
    dt       = 0.15·dx / (MOB·Δf)          ← 只用**化学**驱动定步长
    cfl_used = dt·MOB·dG_max/dx            ← 用**总**驱动（含弹性 + 曲率）
    ⇒ **cfl_used = 0.15 · (dG_max/Δf)**   ⇒  **dG_max/Δf = cfl_used / 0.15**
    ⇒ 反解化学驱动   Δf = 0.15·dG_max / cfl_used

⇒ 所以 `cfl_used` 大**只有两个可能**：`dG_max` 大（总驱动被弹性/曲率推高）或 `Δf` 小。
本脚本把两者都算出来，并按变体/投影设置并列，便于定位。

## 用法
    python3 _r715_cfl_why.py <tag> [tag ...]
tag 在 `_exp/_bk_t5/` 或 `_exp/_bk_block/` 下（自动找，加不加 `dry_` 都行）。
"""
import csv
import json
import os
import sys

ROOTS = ['_exp/_bk_t5', '_exp/_bk_block']


def find(tag):
    for r in ROOTS:
        for name in ('dry_%s' % tag, tag):
            d = os.path.join(r, name)
            if os.path.isdir(d):
                return d
    return None


def peak(path):
    """返回 (cfl_max, dG_max_Jm3, step) 或 None。"""
    best = None
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            try:
                c = float(row['cfl_used'])
                g = float(row.get('dG_max_Jm3') or 'nan')
            except (ValueError, KeyError, TypeError):
                continue
            if c != c or g != g:            # NaN
                continue
            if best is None or c > best[0]:
                best = (c, g, row.get('step'))
    return best


def main():
    print('=' * 110)
    print('cfl_used 反解：cfl_used = 0.15·(dG_max/Δf)   ⇒   dG_max/Δf = cfl_used/0.15')
    print('=' * 110)
    print('%-22s %5s %6s %9s %11s %9s %11s' %
          ('tag', 'N', 'fproj', 'cfl_peak', 'dG_max', 'dG/Δf', 'Δf_反解'))
    print('-' * 110)
    for tag in sys.argv[1:]:
        d = find(tag)
        if d is None:
            print('%-22s  ⚠ 找不到' % tag)
            continue
        N = fp = None
        mp = os.path.join(d, 'meta.json')
        if os.path.isfile(mp):
            try:
                m = json.load(open(mp))
                N = m.get('N')
                ea = m.get('exp_args') or {}
                fp = ea.get('facet_proj', m.get('facet_proj'))
            except Exception:
                pass
        p = os.path.join(d, 'series.csv')
        if not os.path.isfile(p):
            print('%-22s  ⚠ 无 series.csv' % tag)
            continue
        b = peak(p)
        if b is None:
            print('%-22s  ⚠ 无有效行' % tag)
            continue
        c, g, st = b
        ratio = c / 0.15                    # = dG_max/Δf
        df = g / ratio                      # = 0.15·g/c
        print('%-22s %5s %6s %9.4f %11.3e %9.2f %11.3e   @step %s'
              % (tag, N, fp, c, g, ratio, df, st))
    print('-' * 110)
    print('★ `dG/Δf` 就是规范 §6.3 要的那个比值；`Δf_反解` = 0.15·dG_max/cfl_used。')
    print('★ 判据（`R712 §10.3b`）：cfl_used ≤ 1.0  ⇔  dG_max/Δf ≤ 6.67')


if __name__ == '__main__':
    main()
