#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_var2.py --- ★★ 回答用户的问题：**两块到底离多远？**

## 背景（`nf2` 的确切语义，已回代码确认）
* `nf2` = **F2 面 = 异变体界面**的面数；
* `_bk_exp.py:1513` 逐字：**「`F2 面数 == 0` ⟺ 两块在 t=0 **真正分离**」**；
* `_bk_measure.py` 里有**正对照**：异变体贴着 ⇒ `f2_faces > 0`。

⇒ 所以 `nf2 = 0` **确实**意味着"**不同变体的块还没碰到**"。

## 本脚本给出**定量**答案
对 `t5V2` 的最新快照：
1. **各变体的场数/体积占比**（`f_var`）—— 看第 2 个变体有多小；
2. **变体 1 与变体 2 的场之间的**最小距离**（胞/µm）—— 看它们离多远；
3. **结论**：若距离 ≫ 板条宽度（~8 胞 / 0.5 µm）⇒ **它们还离得远，需要继续长**；
   若距离 ≲ 8 胞 ⇒ **即将相遇**（`nf2` 很快会 > 0）。
"""
import glob
import numpy as np

TAG = 't5V2'
cands = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
P = cands[-1]
DX = 62.5
with np.load(P, allow_pickle=False) as z:
    ks = set(z.files)
    print('=' * 88)
    print('★ 两块离多远？  快照 = %s' % P)
    print('=' * 88)
    print('  含的键: %s' % sorted(k for k in ks if k in
          ('region', 'phi', 'band_fld', 'band_idx', 'f_var', 'n_var_sig', 'n_hab')))
    reg = np.asarray(z['region']).astype(np.int32)
    # 变体归属：优先 f_var（若存了）；否则用 region 的场列表 + 日志
    fv = np.asarray(z['f_var']).ravel() if 'f_var' in ks else None
    if fv is not None:
        nz = [(i + 1, float(v)) for i, v in enumerate(fv) if v > 0]
        print('  **f_var（各变体占比）** = %s' % ['%d:%.3f' % t for t in nz])
    # 场的质心（用 region；§151：region 是**场/变体标签**）
    cents = {}
    for k in sorted(int(x) for x in np.unique(reg) if x != 0):
        idx = np.argwhere(reg == k)
        if idx.size:
            cents[k] = (idx.mean(0), idx.shape[0])

print()
print('  场数 = %d' % len(cents))
print('  %-6s %8s   %s' % ('场', '体素', '质心（µm）'))
for k, (c, n) in sorted(cents.items()):
    print('  %-6d %8d   (%.2f, %.2f, %.2f)' % (k, n, c[0] * DX / 1000, c[1] * DX / 1000, c[2] * DX / 1000))

print()
print('  ── 场之间的最小质心距离（µm）—— 最小的 8 对 ──')
import itertools
pairs = []
for a, b in itertools.combinations(sorted(cents), 2):
    d = float(np.linalg.norm(cents[a][0] - cents[b][0])) * DX / 1000.0
    pairs.append((d, a, b))
pairs.sort()
for d, a, b in pairs[:8]:
    print('    %2d – %2d : %6.3f µm' % (a, b, d))
print()
print('  ── 判读（预先写死）──')
print('  板条宽度实测 ~0.5 µm（8 胞）；质心距离是**下界估计**（质心≠表面）。')
mn = pairs[0][0] if pairs else 0
if mn < 0.5:
    print('  ⇒ 最近的场质心仅 %.3f µm ⇒ **它们极可能已经贴着** ⇒ `nf2` 应很快 > 0' % mn)
elif mn < 1.5:
    print('  ⇒ 最近 %.3f µm ⇒ **在同一量级** ⇒ 再长一段就会相遇' % mn)
else:
    print('  ⇒ 最近 %.3f µm ⇒ **离得远**（多根板条宽度）⇒ 需要结构继续长大才会相遇' % mn)
print()
print('  ⚠ 注意：**不同变体的块相遇**才计 `nf2`（同变体相遇不计）——')
print('     所以本表只是"最近的场对"，**不等于**"异变体对"。')
