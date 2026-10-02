#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_vfresh.py --- ★★★★★ **零成本检验**：`V = 1 + n_fresh`？

## 依据（R108 推出的关系）
**只有 `fresh` 会引入新变体**（`attach`/`stack` 都沿用已有变体，R69/R108）。
**⇒ 若初始播种只用一个变体（`--laths` 把前 `m` 个场都给变体 1）**，则：
```
V = 1 + n_fresh
```
**⇒ 这个式子可以用**已在盘上**的 `nuc_dbg.json`（有 `n_events_by_mode`）**直接检验**：**
* 臂 A：`n_events_by_mode` = `{attach: 4, fresh: 1}` ⇒ 预测 **V = 1 + 1 = 2**
* 臂 B：`n_events_by_mode` = `{attach: 10, fresh: 1, stack: 2}` ⇒ 预测 **V = 2**
* 臂 C：同 B ⇒ 预测 **V = 2**

**⇒ 与快照里实测的 `V`（每变体分组数）对照 ⇒ 公式成立与否，一眼可判。**
"""
import json
import os
import sys
from collections import Counter

import numpy as np

ROOTS = ['_exp/_bk_mn64', '_exp/_bk_p2']
TAGS = sys.argv[1:] or ['A', 'B', 'C', 'D']


def find(tag):
    for r in ROOTS:
        d = os.path.join(r, 'dry_' + tag)
        if os.path.isdir(d):
            return d
    return None


def main():
    print('=' * 100)
    print('检验 `V = 1 + n_fresh`（`n_fresh` 从 `nuc_dbg.json`，`V` 从末快照）')
    print('=' * 100)
    print(' %-5s %-24s %-8s %-10s %-10s %s'
          % ('臂', 'n_events_by_mode', 'n_fresh', '预测 V', '实测 V', '判定'))
    print(' ' + '-' * 92)
    ok = bad = 0
    for t in TAGS:
        d = find(t)
        if not d:
            continue
        p = os.path.join(d, 'nuc_dbg.json')
        if not os.path.exists(p):
            print(' %-5s （`nuc_dbg.json` 未落盘 —— 臂没跑完）' % t)
            continue
        j = json.load(open(p, encoding='utf-8'))
        modes = j.get('n_events_by_mode', {}) or {}
        nf = int(modes.get('fresh', 0))
        pred = 1 + nf
        snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                       key=lambda f: int(f.split('_')[1].split('.')[0]))
        V = '?'
        if snaps:
            z = np.load(os.path.join(d, snaps[-1]))
            if 'region' in z and 'vmap_keys' in z:
                reg = z['region']
                vm = dict(zip([int(x) for x in np.asarray(z['vmap_keys']).ravel()],
                              [int(x) for x in np.asarray(z['vmap_vals']).ravel()]))
                byvar = Counter()
                for f in np.unique(reg):
                    f = int(f)
                    if f > 0:
                        byvar[vm.get(f, -1)] += 1
                V = len(byvar)
        verdict = ''
        if isinstance(V, int):
            if V == pred:
                verdict = '✅ 吻合'; ok += 1
            else:
                verdict = '❌ 差 %d' % (V - pred); bad += 1
        print(' %-5s %-24s %-8d %-10d %-10s %s'
              % (t, str(modes)[:23], nf, pred, V, verdict))
    print()
    print('  ── 汇总：吻合 %d 条，不符 %d 条 ──' % (ok, bad))
    print()
    print('  ★ 判读（**预先写死**）')
    print('   · 全部吻合 ⇒ **`V = 1 + n_fresh` 成立** ⇒ **`V` 的旋钮是"事件数/K"，不是 `--var-rule`**（R108）')
    print('   · 有不符 ⇒ 公式不完整（可能初始播种就用了多个变体）⇒ **回去查 `--laths` 的构造**（P31）')
    print('=' * 100)


if __name__ == '__main__':
    main()
