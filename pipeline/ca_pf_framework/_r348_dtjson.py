#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r348_dtjson.py —— 直接读 `diag_terms.json`（权威），看 F2/F3/F1 到底有没有胞。"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')


def main():
    for tag in (sys.argv[1:] or ['saSet2P0', 'saSet2F2P0']):
        p = os.path.join(MB, 'dry_' + tag, 'diag_terms.json')
        if not os.path.exists(p):
            print('%-12s ⚠ 无 diag_terms.json' % tag)
            continue
        recs = json.load(open(p, encoding='utf-8'))
        if isinstance(recs, dict):
            print('  （顶层是 dict，键 = %s）' % sorted(recs.keys()))
            recs = recs.get('rec') or recs.get('records') or recs.get('recs') \
                or recs.get('rows') or []
        print('=' * 90)
        print('### %s  %d 条记录' % (tag, len(recs)))
        if not recs:
            continue
        # 键结构
        k0 = recs[0]
        print('  顶层键:', sorted(k0.keys()))
        for cls in ('vv', 'f3', 'vb'):
            sub = k0.get(cls)
            print('  %-4s 类型=%s 键=%s' % (cls, type(sub).__name__,
                                           sorted(sub.keys()) if isinstance(sub, dict) else '—'))
        dbg = k0.get('dbg') or {}
        print('  dbg 键:', sorted(dbg.keys()))
        print()
        print('  ## **引擎自己的 `(karr,larr)` 计数**（dbg 字段，权威）')
        print('  %-6s %8s %8s %9s %9s %9s' %
              ('step', 'n_kpos', 'n_vv_raw', 'n_samev', 'n_fin_vv', 'n_fin'))
        for r in recs[::max(len(recs) // 8, 1)] + [recs[-1]]:
            d = r.get('dbg') or {}
            print('  %-6s %8s %8s %9s %9s %9s' %
                  (r['step'], d.get('n_kpos'), d.get('n_vv_raw'),
                   d.get('n_samev'), d.get('n_fin_vv'), d.get('n_fin')))
        d0 = recs[-1].get('dbg') or {}
        print()
        print('  末条 `larr_where_kpos`（`karr>0` 时 `larr` 的取值分布）= %s'
              % (d0.get('larr_where_kpos'),))
        print('  末条 `larr_uniq`  = %s' % (d0.get('larr_uniq'),))
        print('  末条 `karr_uniq` = %s' % (d0.get('karr_uniq'),))
        print('  末条 `var_tab`   = %s' % (d0.get('var_tab'),))
        print('  %-6s %-22s %-22s %-22s' % ('step', 'vv(F2)', 'f3(F3)', 'vb(F1)'))
        for r in recs[::max(len(recs) // 10, 1)] + [recs[-1]]:
            cells = []
            for cls in ('vv', 'f3', 'vb'):
                d = r.get(cls) or {}
                n = d.get('n', None)
                me = d.get('med_ed', None)
                cells.append('n=%s med_ed=%s' % (n, ('%.3e' % me) if isinstance(me, (int, float)) else me))
            print('  %-6s %-22s %-22s %-22s' % (r['step'], cells[0], cells[1], cells[2]))
        # vv 的 n 全序列
        nvv = [ (r.get('vv') or {}).get('n', None) for r in recs ]
        print()
        print('  vv.n 的取值集合（前 20 个不同值）:', sorted(set(map(str, nvv)))[:20])
        nonnull = [x for x in nvv if isinstance(x, int)]
        print('  vv.n 为整数的记录数 = %d / %d；最大 = %s' %
              (len(nonnull), len(nvv), max(nonnull) if nonnull else '—'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
