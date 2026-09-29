#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_pairs.py —— 逐对 F3 面积随步数（读 `--pair-every` 写出的 `f3_pairs` 列）。

用法: python3 _bk_pairs.py <dir> [<dir2> ...]

输出：每个测点一行，列出该时刻**有接触**的每一对及其面积（µm²），
并在形核步打标 —— 用来回答 R17 提出的问题：
**"每次形核把已存在的哪几对界面吃掉了多少"**。
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def parse(s):
    out = {}
    for tok in (s or '').split('/'):
        if ':' in tok:
            k, v = tok.split(':')
            try:
                out[k] = float(v)
            except ValueError:
                pass
    return out


def main():
    for d in sys.argv[1:]:
        if not os.path.isabs(d):
            d = os.path.join(HERE, d)
        p = os.path.join(d, 'series.csv')
        if not os.path.exists(p):
            print('缺 %s' % p)
            continue
        rows = list(csv.DictReader(open(p)))
        if not any(r.get('f3_pairs') for r in rows):
            print('%s: **没有 f3_pairs 数据**（该臂未加 `--pair-every`）'
                  % os.path.basename(d))
            continue
        print('=' * 104)
        print('%s —— 逐对 F3 面积（µm²）；`nsw` = nslab_n（+1 = 本步有形核）'
              % os.path.basename(d))
        print('=' * 104)
        prev, prev_n = {}, None
        for r in rows:
            cur = parse(r.get('f3_pairs'))
            if not cur:
                continue
            n = int(r['nslab_n'])
            mark = ''
            if prev_n is not None and n > prev_n:
                mark = '  ★形核'
            deltas = []
            for k in sorted(cur):
                if k in prev:
                    dv = cur[k] - prev[k]
                    if abs(dv) > 0.02:
                        deltas.append('%s%+.3f' % (k, dv))
            # 只在"有形核"或"有显著变化"时打印，避免 21 行全刷
            if mark or deltas or prev_n is None:
                print('  step %-4s nslab=%-2d  面积: %s'
                      % (r['step'], n,
                         '  '.join('%s=%.3f' % (k, cur[k]) for k in sorted(cur))))
                if deltas:
                    print('         Δ: %s' % '  '.join(deltas))
            prev, prev_n = cur, n
        print()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
