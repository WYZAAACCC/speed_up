#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_readdf.py --- ★★★★★★ 直接从**断点文件**读 `df`（判"化学驱动力是否恒为 0"）

## 为什么能这么干（**零代码改动**）
`_bk_exp.py:674-676`：
```python
_df = np.asarray(z['df'])
if _df.shape == np.asarray(g.df).shape:
    g.df[...] = _df
```
⇒ **`df` 被存进了断点文件** ⇒ 直接读，**不用改任何代码、不用重跑**。

## 判据（**预先写死**）
`df` 的定义（`_bk_exp.py:1193`）：`df=[0.0] + [_df_start] * nv`
* **`df[0]` 应恒为 0.0**（母相基准）;
* **`df[1]` 应 = `drive_of_T(T)`**，Ms 以下应为 **正且大**（1.2e8–3.5e8）。
**⇒ 若 `df[1] == 0.0` ⇒ **化学驱动力整个丢了**（接线缺陷 ⇒ 代码 bug）;**
**⇒ 若 `df[1] > 0` 而诊断仍报 `df_k−df_l = 0` ⇒ **诊断里 `karr/larr` 的索引不是 `df` 的下标**（量具问题）。**
"""
import glob
import os
import sys
import numpy as np

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5B4D'
cands = []
for pat in ('_exp/_bk_t5/dry_%s/ckpt/*.npz' % TAG, '_exp/_bk_t5/dry_%s/ckpt_*.npz' % TAG,
            '_exp/_bk_t5/dry_%s/*.npz' % TAG):
    cands += sorted(glob.glob(pat))
cands = [c for c in cands if 'snap_' not in os.path.basename(c)]
print('=' * 92)
print('★ %s：从断点读 `df`（候选文件 %d 个）' % (TAG, len(cands)))
print('=' * 92)
if not cands:
    print('  ⚠ 没找到断点文件'); sys.exit(1)
for P in cands[-2:]:
    try:
        with np.load(P, allow_pickle=False) as z:
            keys = list(z.files)
            if 'df' not in keys:
                print('  %s：无 `df` 键（键 = %s）' % (os.path.basename(P), keys[:10]))
                continue
            df = np.asarray(z['df']).ravel()
            step = int(np.asarray(z['step'])) if 'step' in keys else -1
            T = float(np.asarray(z['T'])) if 'T' in keys else float('nan')
    except Exception as e:
        print('  %s：读取失败（%s）' % (os.path.basename(P), e)); continue
    print()
    print('  ── %s（step %d，T = %.2f K）──' % (os.path.basename(P), step, T))
    print('     `df` 形状 = %s' % (df.shape,))
    print('     `df[0]`（母相）= **%.6e**' % df[0])
    print('     `df[1]`（变体1）= **%.6e**' % df[1] if df.size > 1 else '     （无 df[1]）')
    if df.size > 1:
        print('     `df[1:]` 取值集合 = %s' % np.unique(np.round(df[1:], 6))[:8])
    print()
    print('     ── 判据 ──')
    if df.size > 1:
        d = df[1] - df[0]
        print('     **`df[1] − df[0]` = %.6e**' % d)
        if abs(d) < 1e-6 * max(abs(df[1]), 1.0):
            print('     ⇒ ❌ **化学驱动力恒为 0** ⇒ **接线缺陷（代码 bug）**')
            print('        （`df[1]` 本身 = %.3e ⇒ %s）'
                  % (df[1], '**没被更新**' if abs(df[1]) < 1e-6
                     else '被更新了但恰为 0（T 恰在 Ms？需核 T）'))
        else:
            print('     ⇒ ✅ `df[1] − df[0]` **非零**（%.3e）⇒ 化学项**有值**')
            print('        ⇒ 那么诊断报 0 ⇒ **诊断里 `karr/larr` 的下标语义与 `df` 不同**（量具问题）')
