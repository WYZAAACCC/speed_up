#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_evvar.py --- ★★★★ 从 `nuc_dbg.json` 的 **`T_events`** 读**每一次形核选了哪个变体**。

## 为什么这是关键证据
R76 的机制说：**`ed` = `np.argmax(drv)` ⇒ 每次形核都挑驱动力最大者 ⇒ 倾向反复挑同一个变体**。
**⇒ `T_events` 逐条记了 `field`（第几个场）+ `mode`（attach/fresh）**
⇒ 配上 `nuc_cfg.vgroup`（场 → 变体）**就能逐条看出"它是不是总挑同一个变体"** ——
**这是 R76 机制的**直接**证据，不必等臂 D/E。**

## 用法
  _r581_evvar.py [root] [tag ...]
"""
import json
import os
import sys
from collections import Counter

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mn64'
TAGS = sys.argv[2:] or ['A', 'B']


def one(tag):
    p = os.path.join(ROOT, 'dry_' + tag, 'nuc_dbg.json')
    if not os.path.exists(p):
        print('  %-3s ❌ 无 `nuc_dbg.json`' % tag); return
    j = json.load(open(p, encoding='utf-8'))
    cfg = j.get('nuc_cfg', {})
    vg = {int(a): int(b) for a, b in cfg.get('vgroup', {}).items()}
    ev = j.get('T_events', [])
    print()
    print('  ── 臂 %s（`var_rule` = %s，`n_events_by_mode` = %s）──'
          % (tag, cfg.get('var_rule'), j.get('n_events_by_mode')))
    if not ev:
        print('     （`T_events` 空）'); return
    print('     %-6s %-7s %-7s %-8s %-10s %s'
          % ('#', 'step', 'field', '→变体', 'mode', 'T(K)/df'))
    vseen = Counter()
    for i, e in enumerate(ev, 1):
        f = int(e.get('field', -1))
        v = vg.get(f, -1)
        vseen[v] += 1
        print('     %-6d %-7s %-7d %-8s %-10s T=%.1f df=%.3g'
              % (i, e.get('step'), f, 'V%d' % v, e.get('mode'),
                 float(e.get('T', 0)), float(e.get('df', 0))))
    print('     ⇒ **形核事件用到的变体：%s**（V_event = %d）'
          % (dict(sorted(vseen.items())), len(vseen)))
    # ★ 与快照里的总 V 对照提醒
    print('     ⚠ 注意口径：`T_events` 只记**athermal 律触发**的事件；')
    print('        **预摆的第 1 片 + 非事件通道的场**不在里面 ⇒ V_event 可能 < 快照里的 V。')


def main():
    print('=' * 92)
    print('逐次形核选了哪个变体（R76 机制的直接证据）')
    print('=' * 92)
    for t in TAGS:
        one(t)
    print()
    print('=' * 92)
    print('★ 判读（**预先写死**）')
    print('  · 若事件的变体号**几乎全是 V1** ⇒ **R76 的机制成立**（`ed` 反复挑同一个）')
    print('  · 若事件的变体号**铺开** ⇒ R76 的机制不成立，另查')
    print('=' * 92)


if __name__ == '__main__':
    main()
