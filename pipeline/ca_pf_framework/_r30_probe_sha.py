#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_probe_sha.py —— R30 审计：落盘臂的 meta.json 记录 sha 与**当前磁盘上的代码**是否一致。

用法: python3 _r30_probe_sha.py [臂目录 ...]
"""
import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


FILES = ['_bk_exp.py', '_bk_measure.py', 'windowB_surface.py',
         'windowB_lath.py', 'windowB_par.py']
CUR = {f: sha(os.path.join(HERE, f)) for f in FILES}

dirs = sys.argv[1:]
if not dirs:
    dirs = sorted(glob.glob(os.path.join(HERE, '_exp', '_bk_*', '*')))
    dirs = [d for d in dirs if os.path.isfile(os.path.join(d, 'meta.json'))]

print('=' * 118)
print('R30：落盘臂 meta.json 的 sha vs **当前磁盘代码**的 sha（不一致 ⇒ 归档数字不是这份代码产的）')
print('=' * 118)
for f in FILES:
    print('  当前 %-22s %s' % (f, CUR[f][:16]))
print('-' * 118)
print('%-40s %-6s %-6s %-6s %-6s %-6s  %s'
      % ('臂目录', 'exp', 'meas', 'surf', 'lath', 'par', 'COLS 含 f3_pairs_pos?'))
print('-' * 118)
for d in dirs:
    mp = os.path.join(d, 'meta.json')
    if not os.path.isfile(mp):
        continue
    try:
        m = json.load(open(mp, encoding='utf-8'))
    except Exception as e:
        print('%-40s  meta 读失败 %r' % (os.path.relpath(d, HERE), e))
        continue
    marks = []
    for f in FILES:
        got = m.get('sha_' + f[:-3].replace('_bk_', 'bk_').replace('windowB_', 'windowB_'))
        marks.append('  --  ' if not got else ('同    ' if got == CUR[f] else '**异**'))
    csvp = os.path.join(d, 'series.csv')
    cols = ''
    if os.path.exists(csvp):
        with open(csvp, newline='', encoding='utf-8') as fh:
            cols = fh.readline().strip()
    # meta 里键名其实叫 sha_exp/sha_measure/sha_windowB_*
    keys = ['sha_exp', 'sha_measure', 'sha_windowB_surface', 'sha_windowB_lath',
            'sha_windowB_par']
    marks = []
    for f, k in zip(FILES, keys):
        got = m.get(k)
        marks.append('  --  ' if not got else ('同    ' if got == CUR[f] else '**异**'))
    print('%-40s %s  %s' % (os.path.relpath(d, HERE), ' '.join(marks),
                            'YES' if 'f3_pairs_pos' in cols.split(',') else 'no'))
print('-' * 118)
print('记账：`同` = 归档时的代码与现在磁盘上的**逐字节一致** ⇒ 可用当前量具直接重算；')
print('      `**异**` = 代码改过 ⇒ 归档数字必须用**当时那份代码**（git 历史）才能复现，')
print('      或者用当前量具在**落盘快照**上重算（这正是 npz 里存全量 region 的目的）。')
