#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_vs_abA.py --- ★★★★★ 决定性对照：新长跑 vs 归档臂 abA 的**同步数轨迹**

## 为什么先做这个（不要先猜）
step 100 时新跑的 `Vt` 在**下降**（20 步达峰后单调降）。
**在解释之前必须先问：abA 在同一步数是不是也这样？**
* 若 abA **也**先降后升 ⇒ 是**正常瞬态**（种子板条先调整，之后才长）；
* 若 abA **单调增长** ⇒ 我的配置与 abA **有实质差异**，必须找出是哪一项。

⚠ **对不齐口径**：abA 的 `every=20` 与新跑相同 ⇒ 可直接按 `step` 对齐。
"""
import csv
import os
import sys

KEYS = ['Vt', 'nslab_n', 'nslab_n1', 'nf3', 'nf3_col', 'nf2', 'nblk_sig',
        'f_var', 'r_selfac', 'box_touch', 'blk_alen_nm', 'blk_wlen_nm', 'dG_max_Jm3',
        'n_lath', 'w_lath', 'a_lath', 'ths', 'vols']


def load(p):
    if not os.path.exists(p):
        return {}
    rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    return {int(r['step']): r for r in rows}


def main():
    a = load('_exp/_bk_mb/dry_abA/series.csv')
    n = load(sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_t5/dry_t5L62/series.csv')
    tag = sys.argv[2] if len(sys.argv) > 2 else 't5L62'
    print('=' * 104)
    print('同步数对照：**abA（归档基线，N=112/7.0 µm）** vs **%s（N=160/10.0 µm）**' % tag)
    print('=' * 104)
    steps = sorted(set(list(a) + list(n)))[:11]
    for k in ('Vt', 'nslab_n', 'nf3', 'nf2', 'nblk_sig', 'f_var', 'r_selfac',
              'box_touch', 'dG_max_Jm3'):
        print()
        print('  ── %s ──' % k)
        print('     %-8s %-26s %-26s' % ('step', 'abA', tag))
        for s in steps:
            va = (a.get(s, {}).get(k) or '').strip()[:26]
            vn = (n.get(s, {}).get(k) or '').strip()[:26]
            mark = ''
            if k == 'Vt' and va and vn:
                try:
                    fa, fn = float(va), float(vn)
                    mark = '  ← abA %s / 新 %s' % ('↑' if fa > 0 else '', '↑' if fn > 0 else '')
                except ValueError:
                    pass
            print('     %-8s %-26s %-26s%s' % (s, va or '（无）', vn or '（无）', mark))
    # ★ 丰度：abA 在它的第 1..10 行里 Vt 是升还是降
    print()
    print('  ── ★ 早段趋势（前 8 行 Vt）──')
    for nm, d in (('abA', a), (tag, n)):
        vs = [(s, (d[s].get('Vt') or '').strip()) for s in sorted(d)[:8]]
        vs = [(s, v) for s, v in vs if v]
        if len(vs) >= 2:
            f = [float(v) for _, v in vs]
            trend = '单调↑' if all(f[i] < f[i + 1] for i in range(len(f) - 1)) else (
                '单调↓' if all(f[i] > f[i + 1] for i in range(len(f) - 1)) else '先升后降/波动')
            print('     %-7s 前 %d 行 Vt = %s' % (nm, len(f), ['%.4g' % x for x in f]))
            print('             ⇒ 趋势：**%s**' % trend)
    print('=' * 104)


if __name__ == '__main__':
    main()
