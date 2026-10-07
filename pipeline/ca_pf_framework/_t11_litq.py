#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_litq.py <关键词...> —— **检索本地文献库索引**（`_litidx/index.tsv`）。

用途：阶段 A5 / D1 / D5 需要"文献出处"时，先在**本地库**里找，再考虑联网。

索引列：`file / pages / title / category / why / err`
  · `category`：`REL`（相关）/ `JUNK`（无关）等
  · `why`：分类依据（关键词命中）

用法：
  `_t11_litq.py sharp interface elastic`   —— 任一关键词命中即可（AND 语义可选）
  `_t11_litq.py --all martensite facet`    —— 要求全部命中
  `_t11_litq.py --cat REL --n 30 lath`     —— 只看 REL 类，最多 30 条
"""
import csv
import os
import sys

IDX = "/mnt/f/speed_up/_litidx/index.tsv"
args = [a for a in sys.argv[1:]]
mode_all = '--all' in args
args = [a for a in args if a != '--all']
cat = None
nmax = 25
if '--cat' in args:
    i = args.index('--cat')
    cat = args[i + 1].upper()
    del args[i:i + 2]
if '--n' in args:
    i = args.index('--n')
    nmax = int(args[i + 1])
    del args[i:i + 2]
kws = [a.lower() for a in args]
if not kws:
    sys.exit("用法: _t11_litq.py [--all] [--cat REL] [--n 30] <关键词...>")

rows = []
with open(IDX, encoding='utf-8', errors='replace') as fh:
    rd = csv.DictReader(fh, delimiter='\t')
    for r in rd:
        rows.append(r)
print("索引共 %d 条" % len(rows))
hits = []
for r in rows:
    blob = ' '.join(str(r.get(k, '')) for k in ('file', 'title', 'why', 'err')).lower()
    ok = all(k in blob for k in kws) if mode_all else any(k in blob for k in kws)
    if not ok:
        continue
    if cat and str(r.get('category', '')).upper() != cat:
        continue
    hits.append(r)
print("命中 %d 条（关键词=%s%s%s）\n"
      % (len(hits), ','.join(kws), ' AND' if mode_all else ' OR',
         ('  cat=%s' % cat) if cat else ''))
for r in hits[:nmax]:
    print("  [%s] %s" % (r.get('category', '?'), str(r.get('file', ''))[:88]))
    t = str(r.get('title', '')).strip()
    if t:
        print("        %s" % t[:110])
