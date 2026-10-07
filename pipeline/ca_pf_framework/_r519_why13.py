#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r519_why13.py —— **为什么只成了 13 个核**（`n_target_final = 23`）？

## 已知（`_r516` + `nuc_dbg.json`）

| 量 | abA | abB |
|---|---|---|
| `n_target_final` | **23** | **23** |
| `n_athermal_ev` | **13** | **13** |
| `n_events_by_mode` | `{attach: 7, fresh: 5, stack: 1}` | `{attach: 8, fresh: 5}` |
| `Traceback` | 0 | 0 |

**两臂都是 13、目标都是 23 ⇒ 缺口 10 个，且与冷速无关（两臂冷速差 7.4 倍）**
⇒ **强烈提示是结构性的（表示/几何），不是物理的。**

## 本脚本做什么

把 `nuc_dbg.json` 的**全部字段**摊开（含 `dbg` 的每个拒绝计数与 `T_events` 全表），
并逐条核对**可能的解释**：

* **H1 表示上限**：`nv`（= `--laths` 个数）用尽？ abA/abB 的 `--laths` 是 24 ⇒ `nv=24`。
  13 个事件远小于 24 ⇒ **H1 不成立**（除非每个事件占用多个场）。
* **H2 `nfsv` 找不到空场**：`dbg['nfsv_nofield']`？
* **H3 落位失败**：`dbg['fresh_blocked']` / `oob` / `cov`？
* **H4 温度没降够**：`n(T)` 只到 13 ⇒ 需要 `T` 只降到 `M_s − 13/α`。
  但 `n_target_final = 23` 说明驱动**算出的目标**是 23 ⇒ **H4 不成立**。
* **H5 `cap=1` + 事件节奏**：`max_per_step=1`，每步最多 1 个。

**⇒ 判据：把 `dbg` 里所有计数加总，看缺口 10 落在哪一项上。**
"""
from __future__ import annotations

import json
import os
import sys

ROOT = '_exp/_bk_mb'


def main():
    print('=' * 92)
    print('R519  为什么只成了 13 个核（目标 23）')
    print('=' * 92)
    for tag in ('dry_abA', 'dry_abB'):
        p = os.path.join(ROOT, tag, 'nuc_dbg.json')
        if not os.path.exists(p):
            print('✗ 缺 %s' % p)
            continue
        with open(p) as fh:
            d = json.load(fh)
        print('■ %s' % tag)
        for k in ('nuc_law', 'n_eng_ev', 'n_athermal_ev', 'n_target_final',
                  'nuc_fresh_every', 'n_fresh_fallback_to_stack'):
            print('   %-28s = %s' % (k, d.get(k)))
        print('   %-28s = %s' % ('n_events_by_mode', d.get('n_events_by_mode')))
        print('   %-28s = %s' % ('n_events_by_requested_mode',
                                 d.get('n_events_by_requested_mode')))
        cfg = d.get('nuc_cfg') or {}
        print('   nuc_cfg: R=%.0f nm  t=%.0f nm  cap=%s  n_init=%s  nfsv=%s  attach=%s'
              % (cfg.get('R', 0) * 1e9, cfg.get('t', 0) * 1e9, cfg.get('cap'),
                 cfg.get('n_init'), cfg.get('nfsv'), cfg.get('attach')))
        dbg = d.get('dbg') or {}
        print('   dbg 全部计数：')
        for k in sorted(dbg):
            print('      %-22s = %s' % (k, dbg[k]))
        ev = d.get('T_events') or []
        print('   T_events 共 %d 条；前 3 条与末 2 条：' % len(ev))
        sel = ev[:3] + ev[-2:] if len(ev) > 5 else ev
        for e in sel:
            print('      step %-6s T=%.1f K  field=%-3s n_target=%-3s k=%-3s mode=%s'
                  % (e.get('step'), e.get('T', float('nan')), e.get('field'),
                     e.get('n_target'), e.get('k'), e.get('mode')))
        # 温度跨度
        if ev:
            Ts = [e.get('T') for e in ev if e.get('T') is not None]
            print('   ⇒ 事件温度范围：%.1f → %.1f K（%.1f K 跨度）'
                  % (max(Ts), min(Ts), max(Ts) - min(Ts)))
        print()

    # 判读
    print('=' * 92)
    print('★ 判读（把缺口 23−13=10 归到具体计数上）')
    a = json.load(open(os.path.join(ROOT, 'dry_abA', 'nuc_dbg.json')))
    dbg = a.get('dbg') or {}
    keys = ('att', 'oob', 'cov', 'exc', 'ok', 'nocand', 'nfsv_ok', 'nfsv_nofield',
            'fresh_blocked', 'nan_ed', 'fcrit', 'supercrit', 'sites_refilled')
    for k in keys:
        if k in dbg:
            print('   %-18s = %s' % (k, dbg[k]))
    print()
    print('   ⚠ **注意**：这些 `dbg` 计数是**引擎内部按"尝试"记的**，')
    print('     不等于"被拒的核数"。**要归因缺口，必须把 `T_events` 的 `n_target` 序列')
    print('     与"每个 target 上是否成功"对齐** —— 本脚本只摊开数据，**不擅自归因**。')
    print('=' * 92)
    return 0


if __name__ == '__main__':
    sys.exit(main())
