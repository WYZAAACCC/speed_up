#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_regchk.py --- ★★★★★ 我读的 `region` 到底是不是**完整的三维归属图**？

## 为什么要查（**用户的质疑逼出来的**）
用户看 3D 图说："新场是**联通**并且**长宽比正常**的" —— 而我的数字说"碎裂、长宽比 ~1"。
**两者必有一错。最可能的错法是：我读的 `region` **不是完整图****（例如只存了界面带/子采样）。

## 决定性判据（**预先写死**）
**引擎自己算的已转变体积 `Vt`（`series.csv`）应与"`reg>0` 的体素体积"一致**：
```
Vt_引擎  ≈  (reg>0 的体素数) × (62.5 nm)³
```
* **若吻合（±10%）** ⇒ `region` 是**完整图** ⇒ 我的"碎裂"测量**有可能**成立 ⇒ 需另找原因；
* **若差很多（例如只占 1/5）** ⇒ **`region` 是**部分/稀疏**的** ⇒ **我的所有形状测量都作废**。

## 同时报
* `region` 的 dtype/shape/非零数；
* 快照里**所有键**（看有没有别的、更完整的图，如 `phi` 或 `band_*`）。
"""
import glob
import csv
import os
import numpy as np

DX = 62.5
VOX_UM3 = DX ** 3 * 1e-9
TAG = 't5N276'
snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
P = snaps[-1]
st = int(P.split('snap_')[1].replace('.npz', ''))

with np.load(P, allow_pickle=False) as z:
    print('=' * 96)
    print('★ 快照 %s（step %d）里**所有键**与形状' % (os.path.basename(P), st))
    print('=' * 96)
    for k in sorted(z.files):
        a = z[k]
        info = 'shape=%s dtype=%s' % (getattr(a, 'shape', '?'), getattr(a, 'dtype', '?'))
        try:
            if a.ndim >= 1 and a.dtype.kind in 'iuf':
                nz = int((a != 0).sum())
                info += '  非零=%d  最大=%.4g' % (nz, float(np.max(a)))
        except Exception:
            pass
        print('  %-22s %s' % (k, info))
    reg = np.asarray(z['region']).astype(np.int32)

n_total = int(reg.size)
n_nz = int((reg > 0).sum())
print()
print('  ── region 统计 ──')
print('     形状 = %s（总胞数 = %d）' % (reg.shape, n_total))
print('     非零胞数 = **%d**（占 **%.2f%%**）' % (n_nz, 100.0 * n_nz / n_total))
V_from_reg = n_nz * VOX_UM3
print('     ⇒ 由 region 算出的已转变体积 = **%.4f µm³**' % V_from_reg)

# 引擎自己的 Vt（series.csv 的 Vt 列，单位 m³）
vt = None
try:
    rows = list(csv.DictReader(open('_exp/_bk_t5/dry_%s/series.csv' % TAG, newline='')))
    for r in reversed(rows):
        try:
            if abs(int(r['step']) - st) <= 40:
                vt = float(r['Vt']) * 1e18
                sr = r['step']
                break
        except Exception:
            pass
    if vt is None and rows:
        vt = float(rows[-1]['Vt']) * 1e18
        sr = rows[-1]['step']
except Exception as e:
    print('     （读 series.csv 失败：%s）' % e)

print()
print('  ── ★ 决定性对比 ──')
if vt:
    print('     引擎 series.csv 的 Vt（最近行 step=%s）= **%.4f µm³**' % (sr, vt))
    print('     由 region 非零胞算出的体积      = **%.4f µm³**' % V_from_reg)
    ratio = V_from_reg / vt
    print('     ⇒ 比值 = **%.3f**' % ratio)
    print()
    print('  ── 判据（预先写死）──')
    if 0.9 <= ratio <= 1.1:
        print('     ✅ 吻合 ⇒ **region 是完整图** ⇒ 我的形状测量**在数据上是对的**')
        print('        ⇒ 那就得另找"为什么看起来连通"的原因（很可能是**画图时 marker 太大**把碎块视觉上连起来了）')
    else:
        print('     ❌ **不吻合（比值 %.3f）** ⇒ `region` **不是完整图**（部分/稀疏）' % ratio)
        print('        ⇒ **我先前所有基于 region 的形状结论（长/宽/厚/长宽比/实心度/连通段）全部作废**')
else:
    print('     （拿不到 Vt，无法对比）')
