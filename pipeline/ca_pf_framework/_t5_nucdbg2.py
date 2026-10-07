#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_nucdbg2.py --- 只读 `nuc_dbg.json`（形核计数器）—— 判定碎片化的真正原因"""
import json
import os

for TAG in ('t5N276', 't5NR'):
    F = '_exp/_bk_t5/dry_%s/nuc_dbg.json' % TAG
    print('=' * 84)
    print('★ %s  nuc_dbg.json' % TAG)
    print('=' * 84)
    if not os.path.exists(F):
        print('  （不存在）')
        # 退而求其次：从日志里抓那一行
        L = '_w2_t5_short_%s.log' % TAG
        if os.path.exists(L):
            for line in open(L, errors='ignore'):
                if '形核诊断已落盘' in line:
                    print('  日志行：')
                    print('   ', line.strip()[:400])
        print()
        continue
    j = json.load(open(F))
    if isinstance(j, dict):
        for k in sorted(j):
            v = j[k]
            if isinstance(v, dict):
                print('  %s:' % k)
                for k2 in sorted(v):
                    print('     %-18s %s' % (k2, v[k2]))
            else:
                print('  %-22s %s' % (k, v))
    else:
        print(' ', j)
    print()
