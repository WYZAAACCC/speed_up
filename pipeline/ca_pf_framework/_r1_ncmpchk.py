#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_ncmpchk.py --- ★★ 核实：`ncmp` 到底有多少对是「非有限」？

为什么这是要紧事
----------------
第 24 轮的 `_r1_pairgel.py` 报出 **`ncmp[1,2]` 非有限** —— 而 `[1,2]` 正是**实验 7 用的那一对**。

`advance` 里的回退逻辑（`windowB_surface.py`）：
```python
badp = ~np.isfinite(nd_ref).all(-1)
if badp.any():
    nd_ref = np.where(badp[..., None], np_arr[ki], nd_ref)   # ← 退回 winner 的 npref
```
⇒ 若某对 `ncmp` 非有限，那条界面就**静默地**改用"winner 自己的惯习面法向"作为
`M(n)` 的参考取向 —— **不是**两变体的不变平面。**不报错，只是物理悄悄换了。**

判据（先写死）
--------------
  N-1 统计 66 对里有多少对 `ncmp` 非有限。
  N-2 检查**实验 7 用到的那些对**（V1–V2 界面、以及各变体与母相）是否受影响。
  N-3 若 V1–V2 非有限 ⇒ **实验 7 的"自协调"前提被削弱**（模型没有为这一对定义相容法向），
      必须在报告里显式记账。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF, DF, MOB            # noqa: E402

print('=' * 96)
print('核实 `ncmp`（两变体不变平面法向）的有限性')
print('=' * 96, flush=True)
g = W.LevelSetMulti(16, 16 * 2.5e-8, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                    df=[0.0] + [DF] * NV, workers=1, reinit_every=0)
ncl = g.ncmp
print('`g.ncmp` 形状 =', None if ncl is None else ncl.shape)

if ncl is None:
    print('✗ ncmp 是 None —— 整条配对法向通道都没有！')
    sys.exit(1)

bad = []
ok = []
for i in range(1, NV + 1):
    for j in range(i + 1, NV + 1):
        v = ncl[i, j]
        if not np.all(np.isfinite(v)):
            bad.append((i, j))
        else:
            ok.append((i, j))
print('\nN-1 统计：**非有限 %d 对 / 有限 %d 对**（共 %d）'
      % (len(bad), len(ok), len(bad) + len(ok)))
if bad:
    print('   非有限的那些对：')
    for i, j in bad:
        print('      V%-2d–V%-2d   ncmp = %s' % (i, j, ncl[i, j]))
print('\n   有限的那些对（前 12）：')
for i, j in ok[:12]:
    print('      V%-2d–V%-2d   ncmp = [%+.4f %+.4f %+.4f]'
          % (i, j, *ncl[i, j]))

print('\nN-2 实验 7 用到的对：')
for (i, j) in ((1, 2), (5, 6)):
    v = ncl[i, j]
    fin = bool(np.all(np.isfinite(v)))
    print('   V%-2d–V%-2d  %s  ⇒ %s'
          % (i, j, '有限' if fin else '**非有限**',
             '可用' if fin else '**会静默退回 winner 的 `npref`（不是不变平面）**'))

print('\nN-3 判定：')
if (1, 2) in bad:
    print('   ⛔ **V1–V2 的 `ncmp` 非有限** ⇒ 实验 7 里 V1/V2 界面的 `M(n)` 参考取向'
          '**不是两变体的不变平面**，而是 winner 的惯习面法向。')
    print('      ⇒ **实验 7 的"自协调"前提被削弱**：模型并未为这一对定义相容界面。')
    print('      ⇒ 必须在 `R1_EXPERIMENTS_ANSWER.md` 里显式记账，且**不得**把 S-1 的结果')
    print('        解释成"晶体学自协调"。')
else:
    print('   ✅ V1–V2 的 `ncmp` 有限 ⇒ 实验 7 的前提不受影响。')
print('=' * 96)
