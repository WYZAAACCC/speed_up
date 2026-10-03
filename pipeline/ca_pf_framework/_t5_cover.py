#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_cover.py --- 判据⑤ 的**覆盖**维度（§165.4 预先写死）

## 判据（**预先写死**，见 §165.4）
把盒划成 **2×2×2 = 8 个子区**，对每个形核场取**质心**，数它落在哪个子区：
| 观察 | 结论 |
|---|---|
| **≥6 个子区各含 ≥1 个场** | ✅ **"形核撒遍全盒"成立** ⇒ 判据⑤ 在 (B) 读法下**达成** |
| 3–5 个 | ⏳ 部分覆盖（**未到**）|
| ≤2 个 | ❌ 集中在局部（**未达成**）|

**⚠ 口径（必须写明）**：`region` 是**场/变体标签**（§151）⇒ 每个标签的质心代表**一个形核场**。
**⚠ 记账**：本条判据**晚于** ①②③ 的写死时点（§165.4 已声明）。
"""
import sys
import numpy as np

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5H3'
P = sys.argv[2] if len(sys.argv) > 2 else None
DX = 62.5
if P is None:
    import glob
    cands = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
    P = cands[-1] if cands else None
if P is None:
    print('  ⚠ 没找到快照'); sys.exit(1)

with np.load(P, allow_pickle=False) as z:
    reg = np.asarray(z['region']).astype(np.int32)
N = reg.shape[0]

print('=' * 88)
print('★ 判据⑤ 覆盖维度：%s   N=%d  盒=%.2f µm' % (P, N, N * DX / 1000.0))
print('=' * 88)
half = N // 2
cent = {}
for k in sorted(int(x) for x in np.unique(reg) if x != 0):
    idx = np.argwhere(reg == k)
    if idx.size == 0:
        continue
    c = idx.mean(0)
    cent[k] = c

# 2×2×2 分区
cells = {}
for k, c in cent.items():
    key = (0 if c[0] < half else 1, 0 if c[1] < half else 1, 0 if c[2] < half else 1)
    cells.setdefault(key, []).append(k)

print('  形核场数 = %d' % len(cent))
print('  子区（2×2×2）里各含哪些场：')
for key in sorted(cells):
    print('    %s : %s' % (key, cells[key]))
n_cov = len(cells)
print()
print('  ── 判据（§165.4 预先写死）──')
print('  覆盖的子区数 = **%d / 8**' % n_cov)
if n_cov >= 6:
    print('  ✅ **≥6 ⇒ "形核撒遍全盒"成立** ⇒ 判据⑤ 在 (B) 读法下**达成**')
elif n_cov >= 3:
    print('  ⏳ **3–5 ⇒ 部分覆盖**（**未到**，不判 FAIL）')
else:
    print('  ❌ **≤2 ⇒ 集中在局部** ⇒ 判据⑤ 在 (B) 读法下**未达成**')
print()
print('  ⚠ 附：本场空间的**质心分布范围**（各轴 min–max，µm）= %s' %
      (' / '.join('%.2f–%.2f' % (min(c[a] for c in cent.values()) * DX / 1000.0,
                                max(c[a] for c in cent.values()) * DX / 1000.0)
                  for a in range(3))))
