#!/usr/bin/env python3
"""_r438_logmap.py —— 从**运行日志**解析每个形核事件的「场 / 变体 / 模式」。

`nuc_dbg.json` 只在**跑完**才落盘，而双臂还在跑 ⇒ 改读日志里的事件行：
    `★★ **athermal 形核** @ step N：T=... ，df=...，场 K（累计 i/j；模式 **fresh**；累计 fresh=a stack=b）`
"""
import json
import os
import re
import sys

BASE = '_exp/_bk_mb'
LOGS = [('dry_abA', '_r426_abA.log'), ('dry_abB', '_r426_abB.log')]
PAT = re.compile(
    r'athermal 形核\*?\*? @ step (\d+)：T=([\d.]+) K.*?场 (\d+)'
    r'（累计 (\d+)/(\d+)；模式 \*\*(\w+)\*\*')


def P(s):
    print(s, flush=True)


for tag, lg in LOGS:
    mp = os.path.join(BASE, tag, 'meta.json')
    if not os.path.exists(mp) or not os.path.exists(lg):
        P('[%s] ✗ 缺 %s 或 %s' % (tag, mp, lg))
        continue
    vmap = {int(k): int(v) for k, v in json.load(open(mp)).get('vmap', {}).items()}
    txt = open(lg, encoding='utf-8', errors='replace').read()
    ev = PAT.findall(txt)
    P('=' * 100)
    P('[%s] 解析到事件 **%d** 条' % (tag, len(ev)))
    P('=' * 100)
    P('  %-7s %-8s %-6s %-6s %-9s %-8s %s'
      % ('step', 'T(K)', '场', '变体', '模式', '累计k', '该变体组的场号'))
    bymode, fresh = {}, []
    for st, T, k, kk, tgt, mode in ev:
        k = int(k)
        v = vmap.get(k, '?')
        grp = sorted(x for x, vv in vmap.items() if vv == v)
        bymode[mode] = bymode.get(mode, 0) + 1
        if mode == 'fresh':
            fresh.append((k, v, grp[0] if grp else None))
        P('  %-7s %-8.1f %-6d %-6s %-9s %-8s %s'
          % (st, float(T), k, v, mode, '%s/%s' % (kk, tgt), grp))
    P('\n  模式分布：%s' % bymode)
    if fresh:
        ok = sum(1 for k, v, lo in fresh if k == lo)
        P('\n  **fresh 落场核对**（机理：同变体的场 `ed` 逐位相同 ⇒ `np.argmax` 并列取**最小下标**')
        P('   ⇒ fresh 应恒落在该变体组的**最小场号**上）')
        for k, v, lo in fresh:
            P('    场%-3d（V%s）  组内最小 = %-3s ⇒ %s'
              % (k, v, lo, '✅' if k == lo else '❌ 不符'))
        P('    ⇒ %d/%d 吻合 ⇒ %s'
          % (ok, len(fresh), '✅ 机理成立' if ok == len(fresh) else '⚠ 机理需修正'))
    else:
        P('\n  （无 fresh 事件 ⇒ 核对不适用）')
