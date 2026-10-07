#!/usr/bin/env python3
"""_r437_nucmap.py —— 把**每个形核事件**落到「场 → 变体 → 通道」上（`§193` 的最后一块拼图）。

`nuc_dbg.json` 的 `T_events` 每条含 `(step, T, field, mode, ...)`。
把它与 `meta.json` 的 `vmap` 拼起来，就能回答：
  * `fresh` 事件落进了**哪些场**？是不是**永远是该变体组里序号最小的那个**？
    （机理候选：`ed = +ε⁰_v:σ` 只依赖**变体** ⇒ **同变体的场 `ed` 逐位相同**
     ⇒ `np.argmax(drv)` 在并列时返回**最小下标** ⇒ fresh 只可能用场 1..6）
  * `attach`/`stack` 事件落进了哪些场？（`nfsv` 找**同变体里第一个空场**）
"""
import json
import os

BASE = '_exp/_bk_mb'


def P(s):
    print(s, flush=True)


for tag in ('dry_abA', 'dry_abB'):
    mp = os.path.join(BASE, tag, 'meta.json')
    np_ = os.path.join(BASE, tag, 'nuc_dbg.json')
    if not (os.path.exists(mp) and os.path.exists(np_)):
        P('[%s] ✗ 缺 meta.json 或 nuc_dbg.json' % tag)
        continue
    vmap = {int(k): int(v) for k, v in json.load(open(mp)).get('vmap', {}).items()}
    d = json.load(open(np_))
    ev = d.get('T_events') or []
    P('=' * 96)
    P('[%s] 事件 %d 条；n_athermal_ev=%s；by_requested=%s；fallback=%s'
      % (tag, len(ev), d.get('n_athermal_ev'),
         d.get('n_events_by_requested_mode'), d.get('n_fresh_fallback_to_stack')))
    P('=' * 96)
    P('  %-6s %-8s %-7s %-7s %-9s %s'
      % ('step', 'T(K)', '场', '变体', '模式', '该变体的场号（同变体组）'))
    bymode = {}
    fresh_fields = []
    for e in ev:
        k = e.get('field')
        try:
            k = int(k)
        except (TypeError, ValueError):
            continue
        v = vmap.get(k, '?')
        mode = e.get('mode', '?')
        bymode[mode] = bymode.get(mode, 0) + 1
        grp = sorted(kk for kk, vv in vmap.items() if vv == v)
        if mode == 'fresh':
            fresh_fields.append((k, v, grp[0] if grp else None))
        P('  %-6s %-8.1f %-7d %-7s %-9s %s'
          % (e.get('step'), e.get('T', float('nan')), k, v, mode, grp))
    P('\n  模式分布：%s' % bymode)
    if fresh_fields:
        P('\n  **fresh 事件的落场核对**（机理：`np.argmax` 并列取最小下标 ⇒ 应恒为该变体组的**最小**场号）')
        ok = 0
        for k, v, lo in fresh_fields:
            hit = (k == lo)
            ok += int(hit)
            P('    场%-3d（V%s）：该变体组最小场号 = %s ⇒ %s'
              % (k, v, lo, '✅ 吻合' if hit else '❌ **不符**'))
        P('    ⇒ %d/%d 条吻合 ⇒ %s'
          % (ok, len(fresh_fields),
             '✅ 机理成立' if ok == len(fresh_fields) else '⚠ 机理需修正'))
    else:
        P('\n  （本算例没有 fresh 事件 ⇒ 该核对**不适用**）')
