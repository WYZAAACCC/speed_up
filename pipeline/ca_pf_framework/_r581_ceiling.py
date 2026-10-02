#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_ceiling.py --- ★★★★★ **真正的天花板是哪一层？**

## 起因（R91 的发现）
| 臂 | `m` | step 100 | step 200 | step 250 |
|---|---|---|---|---|
| A | 4  | **4** | **4** | **4** |
| B | **12** | **5** | **10** | **11** |
| C | **20** | **5** | （待） | （待） |

**⇒ 臂 B 与臂 C 在 step 100 **完全相同（都是 5）** ⇒ **涨的速率与 `m` 无关**！**

## 三层天花板（本量具要分辨的）
1. **`m`**（每变体的**场数**上限）—— `nfsv` 只能在同变体空场里选；
2. **`n_target`**（**athermal 律**给的**核数**上限）—— `n_target(T) = floor(α_KM·(M_s − T))`；
3. **`V`**（**用到的变体数**）—— `ed` 下受温度档数限制。

**⇒ 单变体的根数 = min(`m`, `n_target` 里分给该变体的部分)**；
**⇒ 总根数 ≈ Σ_变体 min(m, …) ≤ V · min(m, n_target)**。

## 本量具
从各臂的 `nuc_dbg.json` 读 `n_target_final` / `n_athermal_ev` / `n_events_by_mode`，
与快照里的**实测总根数**对照 ⇒ **指出哪一层才是绑定约束**。
"""
import json
import os
import sys
from collections import Counter

import numpy as np

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mn64'
TAGS = sys.argv[2:] or ['A', 'B', 'C', 'D', 'E']


def main():
    print('=' * 100)
    print('三层天花板：`m` / `n_target` / `V` —— 哪一层在绑定？')
    print('=' * 100)
    print(' %-4s %-6s %-10s %-12s %-10s %-12s %s'
          % ('臂', 'm', 'n_target', 'athermal事件', '模式分布', '实测总根数', 'V'))
    print(' ' + '-' * 96)
    for t in TAGS:
        d = os.path.join(ROOT, 'dry_' + t)
        if not os.path.isdir(d):
            continue
        p = os.path.join(d, 'nuc_dbg.json')
        nt = ev = modes = '?'
        if os.path.exists(p):
            j = json.load(open(p, encoding='utf-8'))
            cfg = j.get('nuc_cfg', {})
            vg = cfg.get('vgroup', {})
            m = len(vg) // 12 if vg else '?'
            nt = j.get('n_target_final', '?')
            ev = j.get('n_athermal_ev', '?')
            modes = j.get('n_events_by_mode', '?')
        else:
            m = '?'
        snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                       key=lambda f: int(f.split('_')[1].split('.')[0]))
        tot = V = '?'
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
                tot = sum(byvar.values()); V = len(byvar)
        print(' %-4s %-6s %-10s %-12s %-10s %-12s %s'
              % (t, m, nt, ev, str(modes)[:9], tot, V))
    print()
    print('=' * 100)
    print('★ 判读（**预先写死**）')
    print('  · 若 **实测总根数 ≈ n_target**（而不是 ≈ m）⇒ **绑定层是 athermal 律的 `n_target`**')
    print('    ⇒ **要更多根，必须提 `α_KM`（或降 `T_end`）—— 而不是提 `m`！**')
    print('  · 若 **实测总根数 ≈ m** ⇒ 绑定层是 `m`（R74/R79 的结论）')
    print('  · 若 **总根数 ≪ 两者** ⇒ 绑定层是 `V`（R76/R80 的结论）')
    print('  ⚠ `n_target(T) = floor(α_KM·(M_s − T))`；本配置 `α_KM=0.011`、`M_s=782.09`、`T_end=350`')
    print('    ⇒ 估算 `n_target ≈ floor(0.011 × 432.09) = floor(4.75) = 4`（**与实测 n_target 对照**）')
    print('=' * 100)


if __name__ == '__main__':
    main()
