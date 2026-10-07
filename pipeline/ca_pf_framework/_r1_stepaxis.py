#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_stepaxis.py --- 从 `log.txt` **实测**步轴，供丢失 `step` 列的旧算例重建。

背景
----
`_r1_exp.py` 的 `series.csv` 曾把 `step`/`t_s` 列写成空（已修）。旧算例只能用
`行号 × every` 重建，而 `every` 在旧 `meta.json` 里**没有** ⇒ 只能默认 5。
但 `mid250_*`/`mid192_*` 实际用的是 **4** ⇒ 绝对速率被高估 5/4 倍。

本脚本不猜：`emit()` 每写一行 CSV 都会在 `log.txt` 里打一条 `  [ NNN] …`
⇒ **把日志里的步号序列抠出来**，就是那一行对应的真实 `step`。

判据
----
  A-1 抠出的步号个数必须 == CSV 行数（否则日志有截断/重复，**拒绝使用**）。
  A-2 步号必须严格单调递增。
  A-3 报出实测的 `every`（步号差分的中位数），供与 `meta.every` 对照。
"""
import os
import re
import csv
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r'^\s*\[\s*(\d+)\]\s')


def steps_from_log(d):
    p = os.path.join(HERE, '_exp', d, 'log.txt')
    if not os.path.exists(p):
        return None, 'no log.txt'
    out = []
    for line in open(p, errors='replace'):
        m = PAT.match(line)
        if m:
            out.append(int(m.group(1)))
    if not out:
        return None, 'no step markers'
    return np.array(out, int), ''


def check(d):
    p = os.path.join(HERE, '_exp', d, 'series.csv')
    if not os.path.exists(p):
        return None
    nrow = sum(1 for _ in open(p)) - 1
    st, err = steps_from_log(d)
    if st is None:
        return dict(dir=d, rows=nrow, log_steps=None, every=None, ok=False,
                    why=err)
    ok_n = (st.size == nrow)
    ok_mono = bool(np.all(np.diff(st) > 0))
    ev = float(np.median(np.diff(st))) if st.size > 1 else float('nan')
    return dict(dir=d, rows=nrow, log_steps=int(st.size), every=ev,
                every_all_same=bool(st.size > 1 and np.all(np.diff(st) == ev)),
                ok=bool(ok_n and ok_mono), why=err or 'ok',
                first=int(st[0]), last=int(st[-1]))


DIRS = sys.argv[1:] or ['mid250_ns4', 'mid250_base', 'mid250_ns1', 'mid250_ns2',
                        'mid192_ns4', 'mid192_s2_ns4', 'mid192_ns2',
                        'lath192_ns4', 'e7_selfac', 'equi192_ns4',
                        'lath1', 'mid1', 'e4_lath6', 'e5_equi6', 'e6_mid6']
print('=' * 104)
print('%-18s %6s %10s %8s %6s %10s %s'
      % ('dir', 'rows', 'log_steps', 'every', '均匀?', 'step 范围', '判定'))
print('=' * 104)
for d in DIRS:
    r = check(d)
    if r is None:
        print('%-18s  (无 series.csv)' % d); continue
    if r['log_steps'] is None:
        print('%-18s %6d %10s %8s %6s %10s ⛔ %s'
              % (d, r['rows'], '-', '-', '-', '-', r['why'])); continue
    print('%-18s %6d %10d %8.1f %6s %10s %s'
          % (d, r['rows'], r['log_steps'], r['every'],
             '✅' if r['every_all_same'] else '⚠',
             '%d…%d' % (r['first'], r['last']),
             '✅ 可用' if r['ok'] else '⛔ 个数不匹配（%d vs %d）'
             % (r['log_steps'], r['rows'])))
print('=' * 104)
