#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r241_p45pre.py —— **P1-45 对照的前置核对**：两臂真的用了不同的 `ω` 吗？

## 为什么必须先查（`§129.6` 的同一个教训）

`_r225` 的两臂在 step 100/140 上 `f3_area` **逐位相同**（0.1169 / 0.2563）。
若 `--omega-mode` 没生效（例如被 argparse 吃掉、或 `default_omega` 走了同一分支），
那**跑满 400 步也只是浪费时间**，而且会得出**错误的"O-2 不成立"**结论。
⇒ **先证处理真的施加了，再读判决。**

## 判据（**先写死**）

* **W-1** 两臂 meta 的 `omega_mode` / `omega_max_deg` 确实不同。
* **W-2** ★ **`gamma_RS` 表确实不同**（这是处理的**直接后果**，不是代理量）。
* **W-3** 两臂的**几何/播种**参数完全一致（单变量性）。
* **W-4** 预报 F3 的 γ：`ladder` 应给 {0.0979, 0.1592}（M=6, Δθ=1°），
  `perstep` 应给 0.0540（Δθ=0.4545°）⇒ **用 `windowB_lath` 独立复算核对**。
* **W-5** 打印两臂**当前末步**（避免把中途读数当末态，硬规则③）。
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_lath as WL  # noqa: E402

MB = os.path.join(HERE, '_exp', '_bk_mb')
LATHS = [1, 1, 3, 3, 5, 5]
GAMMA0 = 0.25


def load(tag):
    p = os.path.join(MB, 'dry_' + tag, 'meta.json')
    return json.load(open(p)) if os.path.exists(p) else None


def grs(m):
    out = {}
    for k, v in (m.get('gamma_RS') or {}).items():
        if isinstance(k, str) and '-' in k and v is not None:
            try:
                i, j = (int(x) for x in k.split('-'))
            except ValueError:
                continue
            out[(i, j)] = float(v)
    return out


def main():
    print('=' * 108)
    print('_r241 —— P1-45 对照前置核对：两臂的 `ω` / γ 真的不同吗？')
    print('=' * 108)
    A, B = load('p45L'), load('p45P')
    if A is None or B is None:
        print('  ⚠ 有一臂的 meta 还没落盘 ⇒ 稍后再查')
        return 2
    ok = True
    print()
    print('  ## W-1 开关')
    for nm, m in (('p45L(ladder)', A), ('p45P(perstep)', B)):
        print('     %-16s omega_mode=%-9s omega_max_deg=%s'
              % (nm, m.get('omega_mode'), m.get('omega_max_deg')))
    d1 = (str(A.get('omega_mode')) != str(B.get('omega_mode')))
    d2 = (float(A.get('omega_max_deg', 0)) != float(B.get('omega_max_deg', 0)))
    print('     ⇒ mode 不同=%s；θ 不同=%s ⇒ %s'
          % (d1, d2, '✅ 处理施加了' if (d1 and d2) else '❌ **处理没施加**'))
    ok &= d1 and d2

    print()
    print('  ## W-2 `gamma_RS` 表（处理的直接后果）')
    ga, gb = grs(A), grs(B)
    keys = sorted(set(ga) | set(gb))
    nd = 0
    print('     %-10s %-14s %-14s %s' % ('板条对', 'p45L(ladder)', 'p45P(perstep)', '相同?'))
    for k in keys:
        va, vb = ga.get(k), gb.get(k)
        same = (va is not None and vb is not None and abs(va - vb) < 1e-15)
        nd += (not same)
        print('     %-10s %-14s %-14s %s'
              % ('%d-%d' % k,
                 ('%.6f' % va) if va is not None else '—',
                 ('%.6f' % vb) if vb is not None else '—',
                 '✅' if same else '**不同**'))
    print('     ⇒ 不同的对数 = %d / %d ⇒ %s'
          % (nd, len(keys), '✅ 确有差别' if nd else '❌ **γ 表完全相同 ⇒ 处理没生效**'))
    ok &= (nd > 0)

    print()
    print('  ## W-4 独立复算（用 `windowB_lath`，不读 meta）')
    ax = np.array([1.0, 0.0, 0.0])
    for nm, mode, deg in (('ladder', 'ladder', 5.0), ('perstep', 'perstep', 0.4545)):
        om = WL.default_omega(len(LATHS), deg, axis=ax, mode=mode)
        lt = WL.LathTable(list(LATHS), omegas=om, gamma0=GAMMA0)
        f3 = sorted({round(float(lt.gtab[i + 1, j + 1]), 6)
                     for i in range(lt.M) for j in range(i + 1, lt.M)
                     if lt.vmap[i] == lt.vmap[j]})
        print('     %-9s θ=%s ⇒ F3 γ 取值 = %s' % (nm, deg, f3))
    print('     ⇒ **预期：两臂的 F3 γ 集合必须不同**（ladder 含 1.108×γ₀ 的倒挂对）')

    print()
    print('  ## W-3 单变量性（几何/播种）')
    KEYS = ('N', 'dx_nm', 'laths', 'plate', 'gap_nm', 'block_gap_nm',
            'gamma0', 'beta_h', 'facet_proj', 'steps', 'seed', 'nthreads')
    for k in KEYS:
        a, b = A.get(k, '<缺>'), B.get(k, '<缺>')
        print('     %-16s %-30s %s %s'
              % (k, repr(a)[:30], repr(b)[:30],
                 '' if repr(a) == repr(b) else '← **不同**'))

    print()
    print('  ## W-5 当前末步（**不是末态**）')
    for tag in ('p45L', 'p45P'):
        p = os.path.join(MB, 'dry_' + tag, 'series.csv')
        if os.path.exists(p):
            with io.open(p, 'r', encoding='utf-8') as f:
                rows = list(csv.DictReader(f))
            print('     %-8s 行数 %-4d 末步 %s' % (tag, len(rows), rows[-1]['step']))
        else:
            print('     %-8s (无 series.csv)' % tag)

    print()
    print('=' * 108)
    print('  ⇒ %s' % ('✅ **两臂可比**（处理已施加、其余单变量）—— 但**必须等跑满 400 步**再读 O-2'
                       if ok else '❌ **处理未确认施加** ⇒ 现在读了也是错的'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
