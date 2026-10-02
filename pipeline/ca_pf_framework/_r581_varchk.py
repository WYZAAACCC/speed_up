#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_varchk.py --- 查 `nuc_dbg.json` 里**关于变体选择**记了什么（判臂 D/E 的前置）。

R76/R79 指出：**总根数 = 「变体数 V」×「每变体根数 m」**，而 `m` 只抬高第二个因子。
⇒ **`V` 是本轮最关键的未知数**，而它由 `--var-rule` 决定。
⇒ 本量具先回答「**落盘产物里能不能直接读出 `V`（或推出 `V` 的字段）**」，
   免得臂 D/E 跑完后又得临时找量具（P21/P28 的教训）。
"""
import json
import os
import sys
from collections import Counter

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mn64'
TAGS = sys.argv[2:] or ['A', 'B']


def main():
    print('=' * 92)
    print('查 `nuc_dbg.json` 里关于**变体选择**的记录（判臂 D/E 的前置）')
    print('=' * 92)
    for tag in TAGS:
        p = os.path.join(ROOT, 'dry_' + tag, 'nuc_dbg.json')
        if not os.path.exists(p):
            print('  %-3s ❌ 无 `nuc_dbg.json`（臂没跑完）' % tag); continue
        j = json.load(open(p, encoding='utf-8'))
        cfg = j.get('nuc_cfg', {})
        print()
        print('#' * 92)
        print('# 臂 %s' % tag)
        print('#' * 92)
        print('  顶层键：%s' % sorted(j.keys()))
        print('  `nuc_cfg` 键（%d 个）：%s' % (len(cfg), sorted(cfg.keys())))
        # ★ 与变体有关的字段
        print()
        print('  ── ★ 与**变体**可能有关的字段 ──')
        for k in sorted(cfg):
            if any(s in k.lower() for s in ('var', 'group', 'lath', 'vmap', 'ks',
                                            'orient', 'seed', 'rule')):
                v = cfg[k]
                s = str(v)
                print('    `%s` = %s' % (k, s[:160] + ('…' if len(s) > 160 else '')))
        # 事件列表
        print()
        print('  ── 事件类字段（找"每次形核选了哪个变体"）──')
        for k in sorted(j):
            if k == 'nuc_cfg':
                continue
            v = j[k]
            if isinstance(v, list):
                print('    `%s`：list，%d 项；首项 = %s'
                      % (k, len(v), str(v[0])[:150] if v else '（空）'))
            elif isinstance(v, dict):
                print('    `%s`：dict，键 = %s' % (k, list(v.keys())[:12]))
            else:
                print('    `%s` = %s' % (k, str(v)[:120]))
        # 若事件里有变体号，直接统计 V
        for k in sorted(j):
            v = j[k]
            if not isinstance(v, list) or not v:
                continue
            first = v[0]
            if isinstance(first, dict):
                keys = sorted(first.keys())
                if any('var' in x.lower() or 'v' == x.lower() for x in keys):
                    print()
                    print('    ★★ `%s` 的条目里有变体字段 %s ⇒ 可直接统计 V' % (k, keys))
                    vk = [x for x in keys if 'var' in x.lower()][0]
                    c = Counter(int(x[vk]) for x in v if vk in x)
                    print('       出现过的变体：%s' % dict(sorted(c.items())))
                    print('       ⇒ **V = %d**' % len(c))
    print()
    print('=' * 92)
    print('★ 用途：臂 D/E 跑完后，用同一套字段直接算 **V**（不必临时写量具）')
    print('=' * 92)


if __name__ == '__main__':
    main()
