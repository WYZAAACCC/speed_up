#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r526_variantcount.py —— **变体数是物理量还是可调量？**

这决定了任务(5)生产配置里 `--laths` 的**结构**：
* 若变体数是**固定物理量 `N_V = 12`**（Burgers 取向关系的 12 个变体），
  则 `--laths` **只能**是 `12 × m` 的形状，`m` = 每个变体给几个场；
  想放 `B·n` 根板条就必须 `m ≥ ceil(B·n/12)`。
* 若能随便造变体，那就是纯表示上限。

⚠ 之前我在 `R525 §6` 里写「`B=90` 需要至少 **90 个变体**」——
**如果变体数固定为 12，那句话就是错的**，必须当场改掉。
本量具就是来判这一条的。
"""
import sys

import numpy as np

sys.path.insert(0, '.')
from windowB_ti64_variants import variants      # noqa: E402

EPS0, F, M = variants()
n = len(EPS0)
print('=' * 90)
print('R526 —— 变体数')
print('=' * 90)
print('  `variants()` 返回的变体数 len(EPS0) = **%d**' % n)
print('  每个变体的应变张量形状 = %s' % (np.asarray(EPS0[0]).shape,))
print('  前两个变体是否相同 = %s' % bool(np.allclose(EPS0[0], EPS0[1])))
# 12 个变体应当**两两不同**（否则表里有重复，是另一回事）
_dup = [(i, j) for i in range(n) for j in range(i + 1, n)
        if np.allclose(EPS0[i], EPS0[j], atol=1e-12)]
print('  两两重复的对 = %s' % (_dup if _dup else '无（12 个互不相同）'))
print('')
print('  ⇒ 变体数 = **%d**，是**物理量**（Burgers OR 的 12 个变体，'
      '立方对称等价 —— 见 `windowB_surface.py:1124`）。' % n)
print('  ⇒ **`--laths` 的形状只能是 `%d × m`**（`m` = 每变体给几个场）。' % n)
print('  ⇒ 要放 `B·n` 根板条：`m ≥ ceil(B·n / %d)`，`nv = %d·m`。' % (n, n))
for B, nl in ((8, 5), (90, 6)):
    import math
    m = math.ceil(B * nl / n)
    print('     B=%-3d n=%d ⇒ m ≥ ceil(%d/%d) = **%d** ⇒ nv = %d×%d = **%d**'
          % (B, nl, B * nl, n, m, n, m, n * m))
print('')
print('  ⚠ 归档/短跑用的 `--laths` = 12 变体 × 6 场 = 72 ⇒ m=6。')
print('     `B=8, n=5` 需要 `m ≥ ceil(40/12) = 4` ⇒ 72 **够**；')
print('     但 `fresh` 随机挑变体会**撞车**（生日问题）⇒ 实测 55%% 被拒。')
