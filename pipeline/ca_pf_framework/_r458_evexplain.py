#!/usr/bin/env python3
"""_r458_evexplain.py —— ★★★ **为什么 athermal 目标 23 次、实际只有 13 次？**

`_r428` 的 R-1 判据说 `n_athermal_ev = 13`，而 `n_target_final = 23`。
⇒ 10 次事件**被引擎拒了**。本脚本把**拒的原因**挖出来（`nuc_dbg.json` 的 `dbg` 计数）。
"""
import json
import os

P = print
P('=' * 88)
P('_r458 —— 形核事件被拒的原因')
P('=' * 88)

for tag in ('dry_abB', 'dry_abA'):
    p = os.path.join('_exp/_bk_mb', tag, 'nuc_dbg.json')
    P('\n[%s]' % tag)
    if not os.path.exists(p):
        P('    ✗ 还没有 nuc_dbg.json（跑完才写）')
        continue
    d = json.load(open(p))
    P('    n_athermal_ev   = %s' % d.get('n_athermal_ev'))
    P('    n_target_final  = %s   ← athermal 律"应该有"的次数' % d.get('n_target_final'))
    P('    by_requested    = %s' % d.get('n_events_by_requested_mode'))
    P('    fallback(fresh→stack) = %s' % d.get('n_fresh_fallback_to_stack'))
    dbg = d.get('dbg') or {}
    P('    dbg（拒因计数）：')
    for k in sorted(dbg):
        P('      %-18s = %s' % (k, dbg[k]))
    # 缺口
    try:
        gap = int(d.get('n_target_final')) - int(d.get('n_athermal_ev'))
    except (TypeError, ValueError):
        gap = None
    if gap:
        P('    ⇒ **缺口 %d 次**。主因（按 `dbg`）：' % gap)
        cand = {k: v for k, v in dbg.items()
                if k in ('nfsv_nofield', 'fresh_blocked', 'cov', 'oob', 'exc',
                         'nfsv_novgroup', 'fcrit', 'nan_ed') and v}
        for k, v in sorted(cand.items(), key=lambda kv: -kv[1]):
            P('       %-18s %d 次' % (k, v))
P('=' * 88)
