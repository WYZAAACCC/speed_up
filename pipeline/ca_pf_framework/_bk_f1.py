#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_f1.py —— 给 `eng3` 逐条核 F-1..F-4（**预登记判据**，逐点打分）。"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
F = []


def ck(tag, ok, det=''):
    print('  %-56s %s %s' % (tag, 'PASS' if ok else '**FAIL**', det))
    if not ok:
        F.append(tag)


for tag in ('eng3', 'eng2'):
    p = os.path.join(HERE, '_exp/_bk_eng', 'eng_%s' % tag, 'series.csv')
    rows = list(csv.DictReader(open(p)))
    print('=' * 96)
    print('臂 %s（%d 个测点，末 step=%s）' % (tag, len(rows), rows[-1]['step']))
    print('=' * 96)
    # F-1：nslab_n 首次达到 6 的 step
    first6 = next((int(r['step']) for r in rows if int(r['nslab_n']) >= 6), None)
    mx = max(int(r['nslab_n']) for r in rows)
    if tag == 'eng3':
        ck('F-1 nslab_n 在 step ≤ 150 达到 6', first6 is not None and first6 <= 150,
           '首次达到 6 的 step=%s；全程最大 nslab_n=%d' % (first6, mx))
        fin = rows[-1]
        fa = float(fin['f3_area_m2']) * 1e12
        vt = float(fin['Vt']) * 1e18
        ck('F-2 末态 f3_area ∈ [6.0, 8.5] µm²', 6.0 <= fa <= 8.5, '%.4f µm²' % fa)
        ck('F-3 末态 Vt ∈ [2.4, 2.9] µm³', 2.4 <= vt <= 2.9, '%.4f µm³' % vt)
        # F-4 需要快照，另由 _bk_pair.py 判
        ck('F-1b **无过形核**：全程 nslab_n ≤ 6（场用完就应停）',
           mx <= 6, '全程最大 nslab_n=%d（7 = 场用完后又在已有场里多播了一片）' % mx)
        ck('F-1c **柱内不重复**：runs 里每个场至多出现一次',
           all(len(set(r['runs'].split('/'))) == len(r['runs'].split('/'))
               for r in rows if r['runs']),
           '末态 runs=%s' % fin['runs'])
        ck('F-5 无显著碎裂（ncompbig_max ≤ 2）',
           int(fin['ncompbig_max']) <= 2, 'ncompbig_max=%s' % fin['ncompbig_max'])
    else:
        print('  （对照臂，只列关键量）首次达到 6 的 step=%s，全程最大 nslab_n=%d，'
              '末态 runs=%s' % (first6, mx, rows[-1]['runs']))
    # 轨迹
    print('  轨迹: ' + '  '.join('%s:%s片/F3=%.2f/Vt=%.2f'
                                % (r['step'], r['nslab_n'],
                                   float(r['f3_area_m2']) * 1e12,
                                   float(r['Vt']) * 1e18)
                                for r in rows if int(r['step']) % 50 == 0))
print('=' * 96)
print('FAIL = %d %s' % (len(F), F if F else ''))
