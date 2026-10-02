#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_mquota.py --- ★★★ **更正我自己上一轮的结论**：块为什么停在 4 根？

## 上一轮我说的话（要更正）
R30/R32 我写：「模型缺"长大过程中的形核" ⇒ `attach` 饱和 ⇒ 块停在 4 根」。
**R33 读代码发现：真正的第一原因是 `m`（= nv/12，每个变体的场配额）太小。**

## 代码证据（逐字）
`_bk_exp.py:1398`：`vgroup=vmap, nfsv=True, attach=True,`
`_bk_exp.py:1292`：`vmap = {i + 1: laths_eff[i] for i in range(nv)}`（`laths_eff` 来自 `--laths`）
`windowB_surface.py:2326-2334`（`nfsv` 的选场）：
```python
_v = vg.get(k)                                  # 场 k 的**变体**
for _j in range(1, nv + 1):
    if _j == k or vg.get(_j) != _v: continue    # 只找**同变体**的场
    if not bool((reg == _j).any()):             # 且那个场**必须是空的**
        k_new = _j; break
if k_new == k:
    _dbg['nfsv_nofield'] += 1                   # ← 找不到 ⇒ 计数
```

**⇒ `nfsv` 要一个「同变体的空场」。而 `--laths 1,1,2,2,3,3,…`（12 个变体各 m 个）⇒
每个变体**只有 `m` 个场** ⇒ `m` 次之后必然 `nfsv_nofield`。**

## ⇒ ★★★ 直接预测（**可证伪**）
> **同变体板条数的上限 == `m` == `nv/12`。**

**逐条对账（全部实测值）**
| 事实 | 数值 | 与"上限 = m = 4"一致？ |
|---|---|---|
| 我的两臂用的 `--m` | **4** | — |
| `p2_b5` 末态 `nslab_n` | **4** | ✅ |
| `p2_b3` 末态 `nslab_n` | **6** = 4（变体 1）+ 2（变体 5） | ✅ |
| `--nuc-block-target` | **5**（要求 5 根/块） | ❌ **要 5 根但只给 4 个场** ⇒ **配置自相矛盾** |
| `vmap_vals`（实测） | `{1:1,2:1,3:1,4:1,17:5,18:5,…}` | ✅ 变体 1 恰好 4 个场 |

## 我上一轮错在哪（**主动更正**）
我把"块停在 4 根"归因于**模型缺机制**。**实际第一原因是我的 `--m 4` 太小**
（goal §(14) 自己写的是 `m = 45`、`nv = 540`）。
**⇒ "缺机制"这条**可能仍然成立**（远场核确实接不上），但它**不是块停在 4 根的第一原因**。
**⇒ 在把 `m` 提上去之前，不能声称"机制缺一半"。**
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    print('=' * 92)
    print('R581-R33 —— 更正：同变体板条数上限 == `m` == `nv/12`')
    print('=' * 92)
    for tag in ('p2_b5', 'p2_b3'):
        d = os.path.join('_exp/_bk_p2', 'dry_' + tag)
        if not os.path.isdir(d):
            continue
        snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                       key=lambda f: int(f.split('_')[1].split('.')[0]))
        z = np.load(os.path.join(d, snaps[-1]))
        vk = np.asarray(z['vmap_keys']).ravel()
        vv = np.asarray(z['vmap_vals']).ravel()
        nv = len(vk)
        m = nv / 12.0
        reg = z['region']
        flds = [int(v) for v in np.unique(reg) if v > 0]
        # 每个变体在 vmap 里占几个场
        from collections import Counter
        cnt = Counter(int(x) for x in vv)
        print()
        print('★ %s' % tag)
        print('   nv = %d ⇒ **m = nv/12 = %.0f**（每变体场配额）' % (nv, m))
        print('   `vmap_vals` 里每个变体占的场数：%s' % dict(sorted(cnt.items())))
        print('   末态出现的场 %d 个：%s' % (len(flds), flds))
        # 同变体最大组
        byvar = {}
        for f in flds:
            v = int(vv[list(vk).index(f)]) if f in list(vk) else -1
            byvar.setdefault(v, []).append(f)
        print('   按变体分组：%s' % {k: len(v) for k, v in sorted(byvar.items())})
        mx = max(len(v) for v in byvar.values()) if byvar else 0
        print('   ⇒ **同变体最多出现 %d 根**；`m` = %.0f  ⇒ %s'
              % (mx, m, '✅ **一致（上限被 m 卡住）**' if mx <= m else '❌ 超过 m，另有原因'))
    print()
    print('=' * 92)
    print('★ 结论与下一步')
    print('=' * 92)
    print('  1. **同变体板条数的硬上限 = `m` = `nv/12`**（`nfsv` 只能在**同变体的空场**里选）；')
    print('  2. 我两臂用 `m=4`，而 `--nuc-block-target 5` ⇒ **要 5 根却只给 4 个场** ⇒ 配置自相矛盾；')
    print('  3. ⇒ **下一步（便宜、可判）**：把 `m` 提到 ≥ 目标根数（例如 `m=12` ⇒ `nv=144`），')
    print('     重跑短程 ⇒ 看 `nslab_n` 是否**突破 4**。')
    print('  4. ⚠ **在 `m` 提上去之前，不能声称"模型缺一半机制"** —— 那是我的配置错。')
    print('=' * 92)


if __name__ == '__main__':
    main()
