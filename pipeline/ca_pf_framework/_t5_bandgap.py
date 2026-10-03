#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_bandgap.py --- ⚠⚠⚠ 解决量具差异：`band` 是否**漏算**了远离界面的内部胞？

## 观测到的矛盾（**必须先解决才能下结论**）
```
场 1 的体积（B4S，同一 step）：
   `band` 量具（band_fld==1 且 band_val<0）：**136 胞**
   `region` 量具（region==1）：             **553 胞**
⇒ 差 **417 胞** ⇒ 有一个量具错了。
```

## 两个假说
| # | 假说 | 预测 |
|---|---|---|
| **A** | **`band` 只存界面附近的胞** ⇒ 深处内部的胞**没有记录** ⇒ `band` **漏算** | `region==1` 的胞里，**大量**在 band 里**完全没有针对场 1 的记录** |
| **B** | **`region` 把 φ₁>0 的胞也算作场 1**（`argmin` 语义）| `region==1` 的胞里，band 记录显示 **φ₁ > 0** |

## 判据（**预先写死**）
对每个 `region==1` 的胞，查它在 `band` 里**针对场 1** 的记录：
* **没有记录** ⇒ **假说 A**（band 漏算内部）⇒ **`band` 不能用作逐场体积**;
* **有记录且 φ₁ ≥ 0** ⇒ **假说 B**（region 语义更宽）⇒ **`region` 不能用作"相体积"**;
* **有记录且 φ₁ < 0** ⇒ 两者应当一致 ⇒ 差异另有原因。
"""
import glob
import sys
import numpy as np

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5B4S'
K = int(sys.argv[2]) if len(sys.argv) > 2 else 1
fs = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
if not fs:
    print('  ⚠ 无快照'); sys.exit(1)
P = fs[-1]
ST = int(P.split('snap_')[1].replace('.npz', ''))
with np.load(P, allow_pickle=False) as z:
    N = int(np.asarray(z['N']))
    reg = np.asarray(z['region']).astype(np.int32)
    bc = int(np.asarray(z['band_cells'])) if 'band_cells' in z.files else -1
    bi = np.asarray(z['band_idx']).ravel().astype(np.int64)
    bv = np.asarray(z['band_val']).ravel()
    bf = np.asarray(z['band_fld']).ravel()

flat = (bi // (N * N)) * (N * N) + ((bi // N) % N) * N + (bi % N)
print('=' * 94)
print('★ %s step %d：量具差异定位（场 %d）｜ `band_cells` = %s' % (TAG, ST, K, bc))
print('=' * 94)
n_reg = int((reg == K).sum())
n_band = int(((bf == K) & (bv < 0)).sum())
print('  `region==%d` 的胞数 = **%d**' % (K, n_reg))
print('  `band` 报 φ<%d 的胞数 = **%d**' % (K, n_band))
print('  差 = **%d**' % (n_reg - n_band))
print()
# region==1 的胞号
cells_reg = np.flatnonzero(reg.ravel() == K).astype(np.int64)
# 这些胞在 band 里针对 K 的记录
m = (bf == K)
have = np.zeros(N ** 3, bool); val = np.full(N ** 3, np.nan)
have[flat[m]] = True
val[flat[m]] = bv[m]
n_have = int(have[cells_reg].sum())
n_none = n_reg - n_have
print('  ── 对 `region==%d` 的胞，查 band 里**针对场 %d** 的记录 ──' % (K, K))
print('     **有记录** = %d（%.0f%%）' % (n_have, 100.0 * n_have / max(n_reg, 1)))
print('     **无记录** = %d（%.0f%%）' % (n_none, 100.0 * n_none / max(n_reg, 1)))
if n_have:
    vv = val[cells_reg][have[cells_reg]]
    print('     有记录者的 φ 值：min=%.4g  max=%.4g  **φ<0 的比例 = %.1f%%**'
          % (vv.min(), vv.max(), 100.0 * (vv < 0).mean()))
print()
# 也查：band 报 K 为负、但 region 不是 K 的胞
cells_b = np.flatnonzero((bf == K) & (bv < 0))
cells_b = np.unique(flat[cells_b])
n_notK = int((reg.ravel()[cells_b] != K).sum())
print('  ── 反向：`band` 报场 %d 为负、但 `region` 不是 %d 的胞 = **%d** ──' % (K, K, n_notK))
print('     ⇒ 若这个数很大 ⇒ `region` **低估**（归属被别的场抢）')
print()
print('  ── 判据（**预先写死**）──')
if n_none > 0.3 * n_reg:
    print('  ⇒ **假说 A 成立**：`band` 缺少远离界面的内部记录（%.0f%% 的 region 胞**无 band 记录**）'
          % (100.0 * n_none / n_reg))
    print('     ⇒ **`band` 不能用作逐场体积量具** ⇒ 我先前基于它的"体积流失"结论**必须重审**;')
    print('     ⇒ 正确的逐场"相体积"应用 **`region`**（或让引擎落盘 φ）。')
else:
    print('  ⇒ 假说 A 不成立（无记录者仅 %.0f%%）⇒ 差异另有原因，需继续查。'
          % (100.0 * n_none / n_reg))
