#!/usr/bin/env python3
"""_r440_modeoutcome.py —— ★★★ **通道 × 结局**：把每个形核事件与它的最终命运对上。

## 要回答的问题
`§193` 看到 `abB` 里 **V1 的场全溶、V7/V9 的场全长**。
`§192` 发现 `f_nuc^crit` 判据**只覆盖 `fresh` 通道**（`stack`/`attach` 通道**完全没有**驱动力门槛）。

**假设 H**：**结局与"走哪条通道"相关** —— 受判据保护的 `fresh` 事件活下来，
无保护的 `attach` 事件死掉。

## 判据（**可证伪**）
**C-1** 把两臂的**全部事件**按 `mode` 分组，统计各组的"长/溶"计数。
**C-2** 若 `fresh` 组长率 **显著高于** `attach` 组 ⇒ H 成立。
    若两组差不多 ⇒ **H 不成立**，须另找解释。
**C-3** **反例必须报出来**（不能只报支持 H 的证据）。

## 数据来源（都在 F 盘）
* 事件（step / field / variant / mode）：从 `_r426_ab{A,B}.log` 解析（`_r438_logmap` 同款正则）。
* 结局（各场体积轨迹）：从 `series.csv` 的 `vols` 列（斜杠分隔）。
"""
import csv
import json
import os
import re
import sys

import numpy as np

BASE = '_exp/_bk_mb'
ARMS = [('dry_abA', '_r426_abA.log'), ('dry_abB', '_r426_abB.log')]
PAT = re.compile(
    r'athermal 形核\*?\*? @ step (\d+)：T=([\d.]+) K.*?场 (\d+)'
    r'（累计 (\d+)/(\d+)；模式 \*\*(\w+)\*\*')


def P(s):
    print(s, flush=True)


def parse_list(s):
    if s is None:
        return []
    s = s.strip()
    if not s or s.lower() in ('none', 'nan'):
        return []
    for ch in '[],;':
        s = s.replace(ch, '/')
    out = []
    for tok in s.split('/'):
        tok = tok.strip()
        if tok:
            try:
                out.append(float(tok))
            except ValueError:
                pass
    return out


rows_all = []
for tag, lg in ARMS:
    mp = os.path.join(BASE, tag, 'meta.json')
    sp = os.path.join(BASE, tag, 'series.csv')
    if not (os.path.exists(mp) and os.path.exists(sp) and os.path.exists(lg)):
        P('[%s] ✗ 缺文件' % tag)
        continue
    vmap = {int(k): int(v) for k, v in json.load(open(mp)).get('vmap', {}).items()}
    series = {}
    for r in csv.DictReader(open(sp, newline='')):
        st = int(float(r['step']))
        v = parse_list(r.get('vols'))
        for i, x in enumerate(v):
            if x > 0:
                series.setdefault(i + 1, []).append((st, x))
    ev = PAT.findall(open(lg, encoding='utf-8', errors='replace').read())

    P('=' * 96)
    P('[%s] 事件 %d 条' % (tag, len(ev)))
    P('=' * 96)
    P('  %-7s %-6s %-6s %-9s %-11s %-11s %s'
      % ('step', '场', '变体', '模式', '该场峰值', '该场末值', '结局'))
    for st, T, k, kk, tgt, mode in ev:
        k = int(k)
        s = series.get(k, [])
        if not s:
            P('  %-7s %-6d %-6s %-9s %-11s %-11s %s'
              % (st, k, vmap.get(k, '?'), mode, '—', '—', '（无数据）'))
            continue
        v0 = s[0][1]
        vmax = max(x for _, x in s)
        vend = s[-1][1]
        if vmax > v0 * 1.15:
            verdict = '长'
        elif vmax < v0 * 0.85:
            verdict = '溶'
        else:
            verdict = '平'
        rows_all.append(dict(arm=tag, step=int(st), field=k, var=vmap.get(k),
                             mode=mode, verdict=verdict, v0=v0, vmax=vmax,
                             vend=vend))
        P('  %-7s %-6d %-6s %-9s %-11.4f %-11.4f %s'
          % (st, k, vmap.get(k, '?'), mode, vmax, vend, verdict))

P('\n' + '=' * 96)
P('[C-1/C-2] **通道 × 结局** 汇总（两臂合并）')
P('=' * 96)
P('  %-10s %-8s %-8s %-8s %-8s %s'
  % ('模式', '长', '溶', '平', '合计', '长率'))
stats = {}
for r in rows_all:
    d = stats.setdefault(r['mode'], dict(长=0, 溶=0, 平=0))
    d[r['verdict']] += 1
for m, d in sorted(stats.items()):
    n = sum(d.values())
    P('  %-10s %-8d %-8d %-8d %-8d %.2f'
      % (m, d['长'], d['溶'], d['平'], n, d['长'] / max(n, 1)))
if len(stats) >= 2:
    fr = stats.get('fresh', {})
    at = stats.get('attach', {})
    nf, na = sum(fr.values()), sum(at.values())
    rf = fr.get('长', 0) / max(nf, 1)
    ra = at.get('长', 0) / max(na, 1)
    P('\n  ⇒ `fresh` 长率 = %.2f（n=%d）；`attach` 长率 = %.2f（n=%d）'
      % (rf, nf, ra, na))
    P('  ⇒ C-2：%s' % ('✅ 支持 H（受判据保护的通道活得更好）' if rf > ra + 0.15
                       else ('⚠ H **不成立**（两组差不多）' if abs(rf - ra) <= 0.15
                             else '⚠ 反向：attach 反而更好 ⇒ H 被否证')))

P('\n[C-3] **反例**（不得只报支持证据）')
P('  · `attach` 里**长**的：')
for r in rows_all:
    if r['mode'] == 'attach' and r['verdict'] == '长':
        P('     %s step=%-5d 场%-3d V%s  %.4f→%.4f'
          % (r['arm'], r['step'], r['field'], r['var'], r['v0'], r['vmax']))
P('  · `fresh` 里**溶**的：')
n_ff = 0
for r in rows_all:
    if r['mode'] == 'fresh' and r['verdict'] == '溶':
        n_ff += 1
        P('     %s step=%-5d 场%-3d V%s  %.4f→%.4f'
          % (r['arm'], r['step'], r['field'], r['var'], r['v0'], r['vmax']))
if n_ff == 0:
    P('     （无）')
P('=' * 96)
