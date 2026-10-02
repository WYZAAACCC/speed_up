#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_ab160b_read.py --- 读 A4 判决实验（N=160）的三臂结果 + 出判决表"""
import csv
import os
import re
import sys

import numpy as np

ROOT = '_exp/_bk_alloc160'
ARMS = [('TUNED', '三变量全开（= 仓库 134 个脚本的现状）'),
        ('ARENA', '只留 MALLOC_ARENA_MAX=2（★ 用户要采用的）'),
        ('PLAIN', '都不设（参考）')]


def peak(tag):
    for p in ('_w2_r581_alloc160b_%s.time' % tag, '_w2_r581_alloc160_%s.time' % tag):
        if os.path.exists(p):
            m = re.search(r'Maximum resident set size \(kbytes\):\s*(\d+)',
                          open(p, encoding='utf-8', errors='replace').read())
            if m:
                return int(m.group(1)) / 1024.0
    return None


def series(tag):
    p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    ws = []
    for r in rows[1:]:
        try:
            ws.append(float(r.get('wall_s', '')))
        except Exception:
            pass
    return dict(n=len(rows),
                last=rows[-1][list(rows[0].keys())[0]] if rows else None,
                med=float(np.median(ws)) if ws else None)


def main():
    print('=' * 106)
    print('A4 判决：N=160 / nv=240 / 全优化（含 --ufv-c 1）/ 30 步 / 一次一臂')
    print('=' * 106)
    print('  %-7s %-13s %-12s %-9s %-8s %s' %
          ('臂', '峰值 RSS(MB)', '中位 s/步', '行数', '末步', '说明'))
    print('  ' + '-' * 102)
    res = {}
    for tag, desc in ARMS:
        pk, s = peak(tag), series(tag)
        res[tag] = dict(peak=pk, med=(s or {}).get('med'), n=(s or {}).get('n'),
                        last=(s or {}).get('last'))
        print('  %-7s %-13s %-12s %-9s %-8s %s' %
              (tag, ('%.0f' % pk) if pk else '—',
               ('%.2f' % res[tag]['med']) if res[tag]['med'] else '—',
               res[tag]['n'] or '—', res[tag]['last'] or '—', desc))
    print()
    t, a, pl = res['TUNED'], res['ARENA'], res['PLAIN']
    ok = True
    if t['peak'] and a['peak']:
        r = a['peak'] / t['peak']
        print('  ★ **峰值**：ARENA/TUNED = %.0f / %.0f = **%.3f×**' % (a['peak'], t['peak'], r))
        if r <= 1.05:
            print('     ⇒ ✅ **安全（≤1.05×）⇒ 可以改那 124 个脚本**')
        elif r <= 1.10:
            print('     ⇒ ⚠ **边缘 ⇒ 带余量再改 + 记账**')
        else:
            ok = False
            print('     ⇒ ❌ **危险区（>1.10×）⇒ **不改**，回来请示**')
    else:
        print('  ⚠ 缺 TUNED 或 ARENA 的峰值（time -v 没落盘）⇒ **无法判定**')
        ok = False
    if t['med'] and a['med']:
        sp = t['med'] / a['med']
        print('  ★ **步速**：TUNED/ARENA = %.2f / %.2f = **%.3f×**（>1 ⇒ ARENA 更快）'
              % (t['med'], a['med'], sp))
        if sp >= 1.3:
            print('     ⇒ ✅ **收益在 N=160 上复现**')
        elif sp >= 1.05:
            print('     ⇒ ⚠ **收益比 N=64 的 1.64× 小 ⇒ 记账**')
        else:
            ok = False
            print('     ⇒ ❌ **N=160 上无收益 ⇒ **不改**，回来请示**')
    else:
        print('  ⚠ 缺步速 ⇒ **无法判定**')
        ok = False
    print()
    print('  ══ **总判决：%s** ══' % ('✅ 可以改那 124 个脚本' if ok else '⚠/❌ 先别改'))
    print('=' * 106)


if __name__ == '__main__':
    main()
