#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_fgcmp.py --- ★★★★★ **F 与 G 的 `runs` 模式逐字相同**：查它是**构造**还是**涌现**

## 背景（P31）
臂 F（`B=74`）与臂 G（`B=150`）的 `runs` 模式**逐字相同**：
`13/12/11/10/8/3/1/2/4/5/6/7/9`，`nslab`=13、`nf3col`=12、`Vt` 只差 2%。
**⇒ 按 P31（"看到一个'不像随机'的分布，先问它是不是**构造**出来的"）**，
**必须先分清：这个相同是**
* **(a) 初始播种就决定了的**（两臂的 `--nuc-init 6` 与种子相同）⇒ **构造**；
* **(b) 饱和后**收敛**到同一结构** ⇒ **涌现**。

## 判据（预先写死）
| 观察 | 结论 |
|---|---|
| **两臂的 `snap_00000` **逐位相同**** | **初始播种 `B`-无关**（预期）⇒ **`runs` 的相同**可能**来自构造** |
| **两臂的 `snap_00000` **不同**** | **⇒ `runs` 的相同是**涌现**（饱和收敛）⇒ 更有意思 |
| **两臂的 `meta.json` 里 `n_target` 不同** | ⇒ **`B` 确实生效了**（否则 `B` 没传进去！） |
"""
import json
import os
import sys

import numpy as np

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mn64'
PAIRS = [('F', 'G'), ('E', 'F')]


def load_snap(tag, name):
    p = os.path.join(ROOT, 'dry_' + tag, name)
    if not os.path.exists(p):
        return None
    return dict(np.load(p, allow_pickle=True))


def main():
    print('=' * 100)
    print('F vs G：`runs` 逐字相同 —— 是**构造**还是**涌现**？')
    print('=' * 100)
    for a, b in PAIRS:
        print()
        print('#' * 96)
        print('# %s vs %s' % (a, b))
        print('#' * 96)
        # ---- meta 对比 ----
        for t in (a, b):
            p = os.path.join(ROOT, 'dry_' + t, 'meta.json')
            if not os.path.exists(p):
                print('  %s: 无 meta.json' % t)
                continue
            j = json.load(open(p, encoding='utf-8'))
            keys = [k for k in ('nv', 'laths', 'nuc_block_target', 'nuc_init', 'N', 'steps')
                    if k in j]
            print('  %-3s meta：%s' % (t, {k: (j[k] if k != 'laths' else '…%d 项' % len(j[k]))
                                          for k in keys}))
        # ---- 快照对比 ----
        sa = load_snap(a, 'snap_00000.npz')
        sb = load_snap(b, 'snap_00000.npz')
        if sa is None or sb is None:
            print('  ⚠ 至少一条缺 snap_00000')
            continue
        ka, kb = set(sa), set(sb)
        print()
        print('  snap_00000 的键：%s 共有 %d 个' % (a, len(ka)))
        print('  只在 %s：%s' % (a, sorted(ka - kb)))
        print('  只在 %s：%s' % (b, sorted(kb - ka)))
        print()
        print('  %-12s %-28s %s' % ('键', '形状/dtype', '两臂是否**逐位相同**'))
        print('  ' + '-' * 88)
        nsame = ndiff = 0
        for k in sorted(ka & kb):
            va, vb = sa[k], sb[k]
            if va.shape != vb.shape:
                print('  %-12s %-28s ⚠ 形状不同 %s vs %s' % (k, str(va.shape), va.shape, vb.shape))
                ndiff += 1
                continue
            if va.dtype.kind in 'fiu' and vb.dtype.kind in 'fiu' and va.dtype == vb.dtype:
                same = bool(np.array_equal(va, vb))
            else:
                same = bool(np.array_equal(np.asarray(va), np.asarray(vb)))
            nsame += same
            ndiff += (not same)
            extra = ''
            if not same and va.dtype.kind == 'f':
                d = np.abs(np.asarray(va, float) - np.asarray(vb, float))
                extra = ' max|Δ|=%.3e' % float(np.nanmax(d))
            print('  %-12s %-28s %s%s'
                  % (k, '%s %s' % (va.shape, va.dtype), '✅ 相同' if same else '❌ 不同', extra))
        print()
        print('  ── 小结：相同 %d 个键，不同 %d 个 ──' % (nsame, ndiff))
        if ndiff == 0:
            print('  ★ **snap_00000 逐位相同** ⇒ 初始播种与 `B` 无关（**构造**）')
            print('    ⇒ 但 `runs` 的相同**仍可能是涌现**（要看 step≥1 的快照）')
        else:
            print('  ★ **snap_00000 有差异** ⇒ 初始状态就不同 ⇒ `runs` 相同是**涌现****（更有意思）')
    print()
    print('=' * 100)
    print('★ 判读要点：**若初始状态相同、而 `B` 差 2 倍仍给出相同 `runs`** ⇒ 饱和收敛是真的；')
    print('  **若 `n_target` 也相同** ⇒ **`B` 根本没生效**（那是 bug，不是饱和）—— 必须排除。')
    print('=' * 100)


if __name__ == '__main__':
    main()
