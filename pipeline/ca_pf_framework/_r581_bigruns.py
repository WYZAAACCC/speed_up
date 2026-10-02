#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_bigruns.py --- ★★★★★ **史上所有算例**：按"盒子大小 × 步数"排出真正的大仿真

## 为什么要扫全库
用户问"**最后的大仿真实验一共跑了多少步**"。
**不许凭记忆答** —— 必须把 `_exp/**/dry_*/` 全扫一遍，
从 `meta.json`（或 `series.csv`）读出 **N、设计步数、末步、行数**，按"大"排序。
"""
import csv
import glob
import json
import os
import re
import sys

ROOTS = sys.argv[1:] or ['_exp']


def read_meta(d):
    p = os.path.join(d, 'meta.json')
    if not os.path.exists(p):
        return {}
    try:
        return json.load(open(p, encoding='utf-8', errors='replace'))
    except Exception:
        return {}


def read_steps(d):
    p = os.path.join(d, 'series.csv')
    if not os.path.exists(p):
        return None, 0, set()
    try:
        rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    except Exception:
        return None, 0, set()
    if not rows:
        return 0, 0, set()
    k = list(rows[0].keys())[0]
    try:
        last = float(rows[-1][k])
    except Exception:
        last = None
    return last, len(rows), set(rows[0].keys())


def main():
    recs = []
    for root in ROOTS:
        for d in glob.glob(os.path.join(root, '**', 'dry_*'), recursive=True):
            if not os.path.isdir(d):
                continue
            tag = os.path.basename(d)[4:]
            m = read_meta(d)
            last, nrow, cols = read_steps(d)
            N = m.get('N') or m.get('n') or m.get('box_N')
            steps = m.get('steps') or m.get('n_steps')
            if N is None:
                # 从 tag/父目录猜
                mm = re.search(r'm(\d+)', tag)
                N = None
            recs.append(dict(tag=tag, dir=d, N=N, want=steps, last=last,
                             nrow=nrow, ncol=len(cols), meta=len(m)))
    print('=' * 108)
    print('全库算例扫描：共 %d 个 `dry_*` 目录' % len(recs))
    print('=' * 108)
    # 先看 meta.json 里有什么字段
    withmeta = [r for r in recs if r['meta']]
    if withmeta:
        d0 = withmeta[0]['dir']
        try:
            keys = sorted(json.load(open(os.path.join(d0, 'meta.json'), encoding='utf-8')).keys())
            print('  `meta.json` 的字段（样例 %s）：%s' % (withmeta[0]['tag'], ', '.join(keys[:18])))
        except Exception:
            pass
    print()
    # 按 (N, 末步) 排序：先把 N 补齐
    for r in recs:
        if r['N'] is None:
            try:
                r['N'] = int(json.load(open(os.path.join(r['dir'], 'meta.json'),
                                            encoding='utf-8')).get('N'))
            except Exception:
                r['N'] = 0
    big = sorted([r for r in recs if (r['last'] or 0) > 0],
                 key=lambda r: (-(r['N'] or 0), -(r['last'] or 0)))
    print('  ── **按盒子大小优先**、同盒子里按末步降序（前 25）──')
    print('  %-22s %-7s %-9s %-9s %-7s %s' %
          ('臂', 'N', '设计步数', '末步', '行数', '目录'))
    print('  ' + '-' * 104)
    for r in big[:25]:
        print('  %-22s %-7s %-9s %-9s %-7d %s' %
              (r['tag'][:22], r['N'], r['want'] if r['want'] else '—',
               ('%.0f' % r['last']) if r['last'] is not None else '—',
               r['nrow'], r['dir']))
    print()
    # 只看 N>=96 的
    nb = [r for r in big if (r['N'] or 0) >= 96]
    print('  ── **N ≥ 96 的全部算例**（%d 条）──' % len(nb))
    print('  %-22s %-7s %-9s %-9s %-7s %s' %
          ('臂', 'N', '设计步数', '末步', '行数', '目录'))
    print('  ' + '-' * 104)
    for r in nb[:40]:
        print('  %-22s %-7s %-9s %-9s %-7d %s' %
              (r['tag'][:22], r['N'], r['want'] if r['want'] else '—',
               ('%.0f' % r['last']) if r['last'] is not None else '—',
               r['nrow'], r['dir']))
    print()
    print('  ── 步数最多的 12 条（不分盒子）──')
    for r in sorted(big, key=lambda r: -(r['last'] or 0))[:12]:
        print('  %-22s N=%-6s 末步=%-8.0f 行数=%-6d %s' %
              (r['tag'][:22], r['N'], r['last'], r['nrow'], r['dir']))
    print('=' * 108)


if __name__ == '__main__':
    main()
