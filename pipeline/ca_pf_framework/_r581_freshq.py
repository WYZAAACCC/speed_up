#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_freshq.py --- ★★★★★★ **`fresh` 通道为什么不加变体**（C5 与 C6 的共同根因）

## 已知
* **`V = 1`（E/F/G 三条臂，R135 实测）**；
* **`V = 1 + n_fresh` 在 A/B/C 上吻合（R109），在 D 上差 −1（R113）**；
* **R113 的猜测**：`random` 挑变体时**撞回了变体 1**。

## 本轮要回答
**`fresh` 事件**到底发生了几次**？**它们挑了哪个变体**？

## 数据源
`dry_<tag>/nuc_dbg.json` 的 `n_events_by_mode`（`{'attach':…, 'fresh':…, 'stack':…}`）
**⇒ 加上 R135 的 `V`=1 ⇒ 若 `fresh` > 0 而 `V`=1 ⇒ **`fresh` 挑了已有变体**（不是没发生）。
"""
import json
import os
import sys
from collections import Counter

import numpy as np

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mn64'
TAGS = sys.argv[2:] or ['A', 'B', 'C', 'D', 'E', 'F', 'G']


def main():
    print('=' * 100)
    print('`fresh` 通道为什么不加变体？（C5 与 C6 的共同根因）')
    print('=' * 100)
    print(' %-5s %-34s %-8s %-8s %-10s %s'
          % ('臂', 'n_events_by_mode', 'n_fresh', 'V(快照)', '预测 1+nf', '判定'))
    print(' ' + '-' * 92)
    for t in TAGS:
        d = os.path.join(ROOT, 'dry_' + t)
        p = os.path.join(d, 'nuc_dbg.json')
        if not os.path.exists(p):
            print(' %-5s （无 nuc_dbg.json ⇒ 臂没跑完或未落盘）' % t)
            continue
        j = json.load(open(p, encoding='utf-8'))
        modes = j.get('n_events_by_mode', {}) or {}
        nf = int(modes.get('fresh', 0))
        # 从快照读 V
        V = '?'
        snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                       key=lambda f: int(f.split('_')[1].split('.')[0]))
        if snaps:
            z = np.load(os.path.join(d, snaps[-1]))
            if 'region' in z and 'vmap_keys' in z:
                reg = z['region']
                vm = dict(zip([int(x) for x in np.asarray(z['vmap_keys']).ravel()],
                              [int(x) for x in np.asarray(z['vmap_vals']).ravel()]))
                by = Counter()
                for f in np.unique(reg):
                    f = int(f)
                    if f > 0:
                        by[vm.get(f, -1)] += 1
                V = len(by)
        pred = 1 + nf
        verdict = ''
        if isinstance(V, int):
            if V == pred:
                verdict = '✅ 取等'
            elif V < pred:
                verdict = '★ 差 %d ⇒ **`fresh` 挑了已有变体**' % (V - pred)
            else:
                verdict = '⚠ 超 %d（异常）' % (V - pred)
        print(' %-5s %-34s %-8d %-8s %-10d %s'
              % (t, str(modes)[:33], nf, V, pred, verdict))
    print()
    print('  ★ 判读：**`n_fresh` > 0 而 `V` = 1** ⇒ `fresh` 确实发生了，但**挑回了变体 1**')
    print('          **`n_fresh` = 0**          ⇒ `fresh` **根本没发生**')
    print('  ⇒ 这两者的**修法完全不同**：前者改"选变体的规则"，后者改"通道的调度（K）"。')
    print('=' * 100)


if __name__ == '__main__':
    main()
