#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r366_repl.py —— ★★★ 独立复现驱动：把 `§173`/`§174` 的**否定结论**在**另一个变体指派**上重跑。

## 为什么这条最值钱（硬规则 ㉞）

`§173`（块-块接触不偏好 rank-1 相容对，百分位 0.179）与
`§174`（驱动力秩 0.154 是 `‖Δε⁰‖` 相近**传播**的结果，按 `R` 秩只有 0.415）
**都只在一个指派上测过**：`saSet2` 的 (V1,V2,V3,V4,V7,V8)。
⇒ 必须换一个**结构不同**的指派再测一次。

**候选（`_r360` 探针已筛）**：

| 臂 | 块指派 | `cov_norm` | 闸门 |
|---|---|---|---|
| `saSet2`（基准） | V1,V2,V3,V4,V7,V8 | 0.966 | ✅ |
| **`permB1_200`** | **V1,V4,V2,V8,V3,V7** | **0.961** | ✅ |
| `permB2`（未跑） | V2,V3,V7,V1,V8,V4 | 0.944 | ❌ |
| `permB3`（未跑） | V7,V8,V4,V3,V2,V1 | 0.892 | ❌ |

## 判据（**先写死**）

* **Y-1 复现**：`permB1` 上 `§173` 的 `R` 百分位**同样不显著**（>0.05）
  ⇒ 否定结论**复现**。
* **Y-2 复现**：`permB1` 上 `§174` 的 `|Δed|` 秩**同样低**，而按 `R` 的秩**同样≈0.4**
  ⇒ "驱动力小是 `‖Δε⁰‖` 传播、不是不变平面相容"**复现**。
* **Y-3 若不复现**：必须如实报，并把结论降级为"指派依赖"。
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = '/root/miniconda3/envs/ml/bin/python'
ENV = dict(os.environ,
           MALLOC_MMAP_THRESHOLD_='65536',
           MALLOC_TRIM_THRESHOLD_='65536',
           MALLOC_ARENA_MAX='2',
           PYTHONDONTWRITEBYTECODE='1')

TASKS = [
    ('§173 几何检验', '_r357_selfac_geom.py', ['saSet2', 'step=200']),
    ('§173 几何检验', '_r357_selfac_geom.py', ['permB1_200', 'step=200']),
    ('§174 驱动力', '_r358_ed_offline.py', ['saSet2', '200']),
    ('§174 驱动力', '_r358_ed_offline.py', ['permB1_200', '200']),
]


def main():
    print('=' * 108)
    print('_r366 —— 独立复现：同一变体池、不同"变体→块"指派（step 200）')
    print('=' * 108)
    for title, script, args in TASKS:
        print()
        print('#' * 108)
        print('# %s : %s %s' % (title, script, ' '.join(args)))
        print('#' * 108)
        r = subprocess.run([PY, '-u', os.path.join(HERE, script)] + args,
                           cwd=HERE, env=ENV, capture_output=True, text=True)
        out = (r.stdout or '') + (r.stderr or '')
        # 去掉 WSL systemd 噪声
        out = '\n'.join(l for l in out.splitlines()
                        if 'systemd user session' not in l)
        print(out)
        if r.returncode != 0:
            print('⚠ 退出码 = %d' % r.returncode)
    return 0


if __name__ == '__main__':
    sys.exit(main())
