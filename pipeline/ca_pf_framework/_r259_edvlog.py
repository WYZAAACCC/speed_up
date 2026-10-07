#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r259_edvlog.py —— 从**运行日志**里抽 `saSet2EDV` 的逐变体 `ed`（JSON 要跑完才落盘）。

## 为什么（`§144` 之后这条特别有价值）
`saSet2EDV` 用归档几何（**带 `--facet-proj 10`**）⇒ 按 `§144`，动力学里界面能被压制
⇒ **它近似"纯 `ed` 驱动"的实验**，正好回答条件③的核心问题：
**`ed` 是按变体组织，还是按场/位置组织？**

## 判据
* **Q-A** 变体内极差 vs 变体间极差。
* **Q-B** 跨变体 `ed` 极差/标准差随演化的趋势（分化 or 趋同）。
* **Q-C** `vol_cv` 的趋势。
* **Q-D** 内建正对照：Σ各场体积 ≈ `Vt`（该步）。
"""
from __future__ import annotations

import csv
import io
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, '_w2_r240_run.log')
SER = os.path.join(HERE, '_exp', '_bk_mb', 'dry_saSet2EDV', 'series.csv')

# 明细行： "      场1   V1    体积 0.3711    µm³  `ed` 中位 **-3.9470e+08**（均值 ..."
RE_F = re.compile(
    r'场(\d+)\s+V(\d+)\s+体积\s+([\d.]+)\s+µm³\s+`ed` 中位 \*\*([-+\d.eE]+)\*\*'
    r'（均值 ([-+\d.eE]+)；10–90 分位 ([-+\d.eE]+) … ([-+\d.eE]+)）')
RE_S = re.compile(r'⇒ 跨变体：`ed` 中位的\*\*极差 ([-+\d.eE]+)\*\*、'
                  r'\*\*标准差 ([-+\d.eE]+)\*\*（均值 ([-+\d.eE]+)）；体积 CV = ([\d.]+)')
RE_H = re.compile(r'逐变体 `ed`\*\*（`§135\.6`）@step (\d+)')


def main():
    if not os.path.exists(LOG):
        print('  ⚠ 无日志 %s' % LOG)
        return 2
    txt = io.open(LOG, encoding='utf-8', errors='replace').read()
    # 以 header 切块
    parts = RE_H.split(txt)
    recs = []
    for i in range(1, len(parts), 2):
        step = int(parts[i])
        body = parts[i + 1]
        fields = [dict(field=int(m.group(1)), variant=int(m.group(2)),
                       vol=float(m.group(3)), med=float(m.group(4)),
                       mean=float(m.group(5)))
                  for m in RE_F.finditer(body)]
        s = RE_S.search(body)
        summ = dict(spread=float(s.group(1)), std=float(s.group(2)),
                    mean=float(s.group(3)), vol_cv=float(s.group(4))) if s else {}
        recs.append(dict(step=step, fields=fields, **summ))
    print('=' * 108)
    print('_r259 —— `saSet2EDV` 逐变体 `ed`（从日志抽；真实 R165 几何，**带投影**）')
    print('=' * 108)
    if not recs:
        print('  ⚠ 日志里还没有"逐变体 `ed`"的输出')
        print('     （该打印在 `it % every == 0` 时触发，`--every 20`）')
        return 2
    print('  共 %d 条（step %s … %s）' % (len(recs), recs[0]['step'], recs[-1]['step']))
    print()
    print('  ## **Q-B/Q-C** 逐步的跨变体汇总')
    print('     %-6s %-7s %-14s %-14s %-10s' % ('step', '场数', '`ed` 极差', '`ed` 标准差', '体积 CV'))
    for r in recs:
        print('     %-6s %-7s %-14.4e %-14.4e %-10.4f'
              % (r['step'], len(r['fields']), r.get('spread', float('nan')),
                 r.get('std', float('nan')), r.get('vol_cv', float('nan'))))
    last = recs[-1]
    print()
    print('  ## 末条（step=%s）逐场明细' % last['step'])
    print('     %-5s %-6s %-12s %-15s' % ('场', '变体', '体积[µm³]', '`ed` 中位'))
    for f in sorted(last['fields'], key=lambda x: x['field']):
        print('     %-5d V%-5d %-12.4f %+.4e' % (f['field'], f['variant'],
                                                f['vol'], f['med']))
    # Q-A
    print()
    print('  ## **Q-A** `ed` 按变体还是按场/位置组织？')
    byv = {}
    for f in last['fields']:
        byv.setdefault(f['variant'], []).append(f['med'])
    within = []
    for var, meds in sorted(byv.items()):
        rng = (max(meds) - min(meds)) if len(meds) > 1 else 0.0
        if len(meds) > 1:
            within.append(rng)
        print('     变体 V%-3d：%d 个场  `ed` 中位 = %s' % (
            var, len(meds), ['%+.4e' % m for m in meds]))
        if len(meds) > 1:
            print('                  ⇒ **变体内极差 = %.4e**' % rng)
    allm = np.array([f['med'] for f in last['fields']])
    span = float(allm.max() - allm.min())
    print('     ⇒ **变体间极差**（所有场）= **%.4e**' % span)
    if within and span > 0:
        r = max(within) / span
        print('     ⇒ **变体内最大 / 变体间 = %.3f**' % r)
        print('     ⇒ ⇒ %s' % (
            '**`ed` 更像按"场/位置"组织**（同变体的两个场差得不比不同变体少）'
            if r > 0.5 else
            '**`ed` 主要按"变体"组织**（同变体的场彼此接近）'))
    elif not within:
        print('     ⇒ ⚠ 每个变体只有一个场 ⇒ **不适用**（无法分离变体内离散）')
    # Q-D 正对照
    print()
    print('  ## **Q-D** 内建正对照：Σ各场体积 ≈ `Vt`')
    if os.path.exists(SER):
        with io.open(SER, 'r', encoding='utf-8') as fh:
            rows = list(csv.DictReader(fh))
        Vt = {int(float(r['step'])): float(r['Vt']) for r in rows}
        tot = sum(f['vol'] for f in last['fields'])
        v = Vt.get(last['step'])
        if v is not None:
            print('     Σ体积 = %.4f µm³ ；`Vt` = %.4f µm³ ⇒ 相对差 %.3f%% ⇒ %s'
                  % (tot, v * 1e18, 100 * abs(tot - v * 1e18) / (v * 1e18),
                     '✅' if abs(tot - v * 1e18) / (v * 1e18) < 0.05 else '❌'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
