#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_active_fields.py --- ★★★★★ **唯一的不确定量**：N=160 上"活跃场数"随步数怎么涨

## 为什么只量这一个
每帧检查点成本 = **活跃场数 × 4.3 MB**（其余因子都是确定的）
⇒ **活跃场数是唯一需要实测外推的量**（§4'.5）。

## 口径
* **活跃场数 = `vols` 列里 `> 0` 的项数**（即真的有体积的场）
* 同时报 `nslab_n1`（自适应口径的柱数）与 `nf3` 做交叉
"""
import csv
import os
import sys

ARMS = [('_exp/_bk_p2', 'p2_b3'), ('_exp/_bk_p2', 'p2_b5'),
        ('_exp/_bk_p2', 'p2_b5ov'), ('_exp/_bk_p2', 'p2_b5ps'),
        ('_exp/_bk_blk', 'BK6'), ('_exp/_bk_blk', 'BK7')]
print('=' * 100)
print('★ "活跃场数"（= 有体积的场数）随步数的增长 —— 决定每帧检查点成本')
print('=' * 100)
for root, tag in ARMS:
    p = os.path.join(root, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        continue
    rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    if not rows or 'vols' not in rows[0]:
        print('  %-9s （没有 vols 列）' % tag)
        continue
    k = list(rows[0].keys())[0]
    N = None
    try:
        import json
        N = json.load(open(os.path.join(root, 'dry_' + tag, 'meta.json'),
                           encoding='utf-8', errors='replace')).get('N')
    except Exception:
        pass
    print()
    print('  ── %s（N=%s，共 %d 行）──' % (tag, N, len(rows)))
    print('     %-7s %-11s %-11s %-9s %s' % ('step', '活跃场数', 'nslab_n1', 'nf3', '每帧估算(MB)'))
    sel = [r for r in rows if r[k].isdigit() and int(r[k]) % 100 == 0]
    sel += [rows[-1]]
    seen = set()
    for r in sel:
        if r[k] in seen:
            continue
        seen.add(r[k])
        vs = [x for x in (r.get('vols', '') or '').split('/') if x]
        act = sum(1 for x in vs if float(x or 0) > 0)
        print('     %-7s %-11d %-11s %-9s %.1f' %
              (r[k], act, r.get('nslab_n1', '—'), r.get('nf3', '—'), act * 4.3))
    last = rows[-1]
    vs = [x for x in (last.get('vols', '') or '').split('/') if x]
    act = sum(1 for x in vs if float(x or 0) > 0)
    print('     ⇒ 末步 %s：活跃 %d 场 ⇒ **每帧 ≈ %.0f MB（f64，压缩后）**'
          % (last[k], act, act * 4.3))
print()
print('  ★ 读法：**活跃场数 × 4.3 MB = 每帧成本**（4.3 MB 来自 N=64 的实测压缩比外推）')
print('  ★ 若末步活跃场数 ≪ nv ⇒ **长跑后段才会涨** ⇒ 必须用**趋势**外推，不许拍脑袋')
print('=' * 100)
