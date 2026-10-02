#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_mn64read.py --- 读 N=64 `m` 判决臂的**每变体板条数**（可在臂跑完前先看已有的快照）。

用法： _r581_mn64read.py [root] [tag ...]
"""
import os
import sys
from collections import Counter

import numpy as np

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mn64'
TAGS = sys.argv[2:] or ['A', 'B']


def main():
    print('=' * 92)
    print('N=64 `m` 判决：每变体板条数（从已落盘的快照读）')
    print('=' * 92)
    for tag in TAGS:
        d = os.path.join(ROOT, 'dry_' + tag)
        if not os.path.isdir(d):
            print('  %-3s ❌ 无目录' % tag); continue
        snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                       key=lambda f: int(f.split('_')[1].split('.')[0]))
        # 读 vgroup（若 nuc_dbg 已落盘）
        m = '?'
        p = os.path.join(d, 'nuc_dbg.json')
        if os.path.exists(p):
            import json
            cfg = json.load(open(p, encoding='utf-8')).get('nuc_cfg', {})
            vg = cfg.get('vgroup', {})
            if vg:
                cnt = Counter(int(v) for v in vg.values())
                per = sorted(set(cnt.values()))
                m = per[0] if len(per) == 1 else per
        print()
        print('  ── 臂 %s（`m` = %s）──' % (tag, m))
        for s in snaps:
            z = np.load(os.path.join(d, s))
            if 'region' not in z or 'vmap_keys' not in z:
                print('     %s：缺 region/vmap' % s); continue
            reg = z['region']
            vk = [int(x) for x in np.asarray(z['vmap_keys']).ravel()]
            vv = [int(x) for x in np.asarray(z['vmap_vals']).ravel()]
            vm = dict(zip(vk, vv))
            byvar = Counter()
            for f in np.unique(reg):
                f = int(f)
                if f > 0:
                    byvar[vm.get(f, -1)] += 1
            mx = max(byvar.values()) if byvar else 0
            flag = ''
            if isinstance(m, int):
                flag = '  ✅ ≤ m' if mx <= m else '  ❌ > m'
            print('     %-16s step=%-5d **同变体 max = %d**%s  每变体：%s'
                  % (s, int(z['step']), mx, flag, dict(sorted(byvar.items()))))
    print()
    print('=' * 92)
    print('★ 判读：臂 A（`m=4`）应当 **max = 4**（与 R58 的 N=160/m=4 判决同口径）')
    print('        ⇒ 若 A 给 4，**N=64 代理有效**；再看臂 B（`m=12`）是否 **> 4**')
    print('=' * 92)


if __name__ == '__main__':
    main()
