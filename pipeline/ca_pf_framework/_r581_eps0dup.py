#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_eps0dup.py --- ★★★★★ **验证 `_pair_normals` 优化的前提**：同变体的场，`eps0` 是否**逐位相同**？

## 为什么这是前提（R119 的发现）
`windowB_surface.py:1466` 的 `_pair_normals` 是**双重循环 `k<l` over **场**（nv 个）** ⇒ **O(nv²)**（nv=552 ⇒ 152,076 对）。
**而 `ncmp[k,l]` 只依赖**变体对**（`de = eps0[k-1] - eps0[l-1]`）—— 而变体只有 **12** 个**
⇒ **不同的变体对只有 12×11/2 = 66 个**。
**⇒ 若"同变体的场 `eps0` 逐位相同"，则 152,076 次 `argmin_normal` 里有 152,010 次是**重复计算****
⇒ **可以按 (变体,变体) 记忆化 ⇒ 加速 ~`m²` 倍**（`m = nv/12`）。

**⚠ 但这条优化**只在"逐位相同"成立时才**产生完全一致的结果****
⇒ **本节就是去实测这一点**（P3：先验证前提，再谈优化）。

## 数据来源
`_exp/_bk_mn64/dry_<tag>/meta.json`（R80 读到过 521 KB 的 meta）—— 找 `eps0` 相关键。
"""
import json
import os
import sys

import numpy as np

ROOTS = ['_exp/_bk_mn64', '_exp/_bk_p2']
TAGS = sys.argv[1:] or ['B', 'D', 'p2_b5']


def find(tag):
    for r in ROOTS:
        p = os.path.join(r, 'dry_' + tag, 'meta.json')
        if os.path.exists(p):
            return p
    return None


def main():
    print('=' * 100)
    print('验证前提：**同变体的场，`eps0` 是否逐位相同**？（决定 `_pair_normals` 能否记忆化）')
    print('=' * 100)
    for t in TAGS:
        p = find(t)
        if not p:
            continue
        print()
        print('#' * 96)
        print('# 臂 %s（%s）' % (t, p))
        print('#' * 96)
        j = json.load(open(p, encoding='utf-8'))
        # 找 eps0 相关的键
        cands = [k for k in j
                 if 'eps0' in k.lower() or 'eps' in k.lower() or 'strain' in k.lower()]
        print('  与应变有关的顶层键：%s' % (cands if cands else '（无）'))
        # 找 vmap（场 → 变体）
        vg = None
        for k in j:
            if 'vgroup' in k.lower() or 'vmap' in k.lower():
                vg = j[k]
                print('  `%s` 类型 = %s' % (k, type(vg).__name__))
        if not vg:
            print('  ⚠ 没有 `vgroup`/`vmap` ⇒ 本臂的 meta 里没有场→变体映射')
            continue
        # 取 eps0
        e0 = None
        for k in cands:
            v = j[k]
            if isinstance(v, list) and v and isinstance(v[0], list):
                e0 = np.asarray(v, dtype=float)
                print('  用 `%s` 作 eps0：shape = %s' % (k, e0.shape))
                break
        if e0 is None:
            print('  ⚠ 找不到形如 list-of-list 的 eps0 ⇒ 打印一个样本键看结构')
            for k in list(j)[:12]:
                print('    `%s` = %.80s' % (k, str(j[k])))
            continue
        # 按变体分组，比"同变体的场是否逐位相同"
        items = sorted(int(a) for a in (vg.keys() if isinstance(vg, dict) else []))
        if not items:
            print('  ⚠ vgroup 不是 dict-of-int'); continue
        from collections import defaultdict
        byvar = defaultdict(list)
        for f in items:
            byvar[int(vg[str(f)]) if str(f) in vg else int(vg[f])].append(f)
        print()
        print('  %-8s %-28s %-10s %s' % ('变体', '场列表（前 8 个）', '场数', '同变体内 eps0 全部逐位相同？'))
        print('  ' + '-' * 88)
        allok = True
        for v, fl in sorted(byvar.items()):
            arrs = [e0[f - 1] for f in fl if 1 <= f <= e0.shape[0]]
            if len(arrs) < 2:
                print('  %-8d %-28s %-10d %s' % (v, str(fl[:8]), len(fl), '（只有 1 个场，跳过）'))
                continue
            ok = all(np.array_equal(arrs[0], a) for a in arrs[1:])
            allok &= ok
            print('  %-8d %-28s %-10d %s'
                  % (v, str(fl[:8]), len(fl), '✅ 逐位相同' if ok else '❌ 有差异'))
        print()
        print('  ⇒ **结论：同变体的场 eps0 %s** ⇒ 记忆化优化**%s**'
              % ('逐位相同' if allok else '**不**逐位相同',
                 '前提成立（结果完全一致）' if allok else '**不成立**（会导致结果变化，禁用该优化）'))
    print()
    print('=' * 100)
    print('★ 若前提成立 ⇒ `_pair_normals` 可按 (变体,变体) 记忆化 ⇒ 加速 ≈ `m²`（m = nv/12）')
    print('   · nv=240（m=20）⇒ 400×  ⇒ 构造 106 min → **~16 s**')
    print('   · nv=552（m=46）⇒ 2116× ⇒ 构造 9.4 h → **~16 s**')
    print('  ⚠ 前提不成立 ⇒ **不许做这个优化**（会改结果）⇒ 另找路子')
    print('=' * 100)


if __name__ == '__main__':
    main()
