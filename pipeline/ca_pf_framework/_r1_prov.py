#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_prov.py --- ★★ 溯源审计：这些算例到底是不是**同一个引擎**跑出来的？

为什么必须查
------------
本会话里我**多次改过引擎**（`windowB_surface.py` / 新增 `windowB_par.py`）：
  ParCtx 并行接入、`sussman_reinit` 抽 `_sussman_core`、`reinitialize` 懒构造、
  `reinit_bbox` 默认改 False、记账计时……
如果某个算例是在**改动之前**跑的，那它与之后的算例**不可比** —— 而报告里我把它们放在同一张表里。

判据（先写死）
--------------
  P-1 列出每个算例 `meta.json` 里的 `sha256`（windowB_surface / windowB_pf3d / windowB_par）
      与 git HEAD。
  P-2 **分组**：把 SHA 相同的算例归为一组 ⇒ **只有同组之间才能比**。
  P-3 与**当前**工作区的 SHA 比对，指出哪些算例"不是当前引擎"跑的。
  P-4 检查每个算例的记录完整性：`series.csv` / `meta.json` / `snap_*.npz` / `log.txt` 是否齐全。
"""
import os
import json
import glob
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


CUR = {f: sha(os.path.join(HERE, f)) for f in
       ('windowB_surface.py', 'windowB_pf3d.py', 'windowB_par.py')
       if os.path.exists(os.path.join(HERE, f))}
print('=' * 104)
print('当前工作区引擎 SHA256：')
for k, v in CUR.items():
    print('   %-22s %s' % (k, v[:16]))
print('=' * 104)

dirs = sorted(d for d in glob.glob(os.path.join(HERE, '_exp', '*'))
              if os.path.isdir(d))
print('\n%-22s %-18s %-10s %-10s %s' %
      ('算例', 'surface sha(前16)', 'series', 'meta', 'snaps'))
groups = {}
rows = []
for d in dirs:
    name = os.path.basename(d)
    mp = os.path.join(d, 'meta.json')
    s = '（无 meta.json）'
    if os.path.exists(mp):
        try:
            m = json.load(open(mp))
            s = (m.get('sha256') or {}).get('windowB_surface.py', '?')[:16]
        except Exception as e:
            s = '（meta 读取失败 %s）' % e
    ns = len(glob.glob(os.path.join(d, 'series.csv'))) 
    nsnap = len(glob.glob(os.path.join(d, 'snap_*.npz')))
    has_meta = os.path.exists(mp)
    print('%-22s %-18s %-10s %-10s %d' %
          (name, s, '有' if ns else '**无**', '有' if has_meta else '**无**', nsnap))
    groups.setdefault(s, []).append(name)
    rows.append((name, s, ns, has_meta, nsnap))

print('\n' + '-' * 104)
print('★ P-2 按引擎 SHA 分组（**只有同组内可比**）：')
for s, names in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    cur = ' ← **与当前工作区一致**' if s == CUR['windowB_surface.py'][:16] else ''
    print('   %s  （%d 个）：%s%s' % (s, len(names), ', '.join(names), cur))

print('\n★ P-3 用**非当前引擎**跑的算例：')
bad = [n for n, s, _, _, _ in rows
       if s != CUR['windowB_surface.py'][:16] and not s.startswith('（')]
if bad:
    for n in bad:
        print('   ⚠ %s' % n)
    print('   ⇒ 这些算例与"当前引擎"的算例**跨组不可比**；报告引用时必须注明。')
else:
    print('   （无 —— 全部与当前工作区一致，或没有 meta.json）')

print('\n★ P-4 记录完整性：')
miss = []
for n, s, ns, hm, nsnap in rows:
    if not ns or not hm:
        miss.append(n)
    elif nsnap == 0:
        miss.append(n + '(无快照)')
if miss:
    print('   ⚠ 不完整：%s' % ', '.join(miss))
else:
    print('   ✅ 全部齐全（series.csv + meta.json + 快照）')
print('=' * 104)
print('★ 报告纪律：跨 SHA 组的表格**不得**直接放在一起比；')
print('  若必须并列，须标注"引擎版本不同，仅示演化趋势"。')
