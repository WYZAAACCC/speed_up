#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_bandchk.py --- ★★★★★ 核实 `band_val`/`band_fld` 的含义（能否给出**逐场物理体积**）

## 为什么
用户要的是**逐根板条的三维尺寸演化**，而我先前用的是 `region`（归属标签）。
**若 `band_val` 是**符号距离 φ**（`<0` = 在相内），则：**
```
逐场物理体积 = #{ band_fld == k 且 band_val < 0 }
```
**⇒ 这是**与归属无关**的量 ⇒ 能判"某根板条的相体积是否真的在缩"。**

## 本脚本要回答
1. `band_cells` 的数值（是否 = N³ ⇒ 覆盖全盒）;
2. `band_idx` 的形态（是**胞索引**还是**列表**）;
3. `band_val` 的**分布**（是否有正有负 ⇒ 是否符号距离）;
4. **`band_fld` 与 `band_val<0` 的联合** ⇒ 能否给出逐场体积;
5. **交叉校验**：由 `band` 算出的"总相体积"是否 ≈ `series.csv` 的 `Vt`
   ⇒ **这是量具的自洽判据**（不一致就说明我理解错了）。
"""
import csv
import glob
import sys
import numpy as np

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276F'
fs = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
P = fs[-1]
ST = int(P.split('snap_')[1].replace('.npz', ''))
N = None
with np.load(P, allow_pickle=False) as z:
    print('=' * 92)
    print('★ %s step %d：`band_*` 的含义核实' % (TAG, ST))
    print('=' * 92)
    reg = np.asarray(z['region']).astype(np.int32)
    N = reg.shape[0]
    bc = int(np.asarray(z['band_cells'])) if 'band_cells' in z.files else -1
    bidx = np.asarray(z['band_idx'])
    bval = np.asarray(z['band_val'])
    bfld = np.asarray(z['band_fld'])
    print('  N³ = %d（盒 %d³） ｜ `band_cells` = %d' % (N ** 3, N, bc))
    print('  `band_idx`  shape=%s dtype=%s  前 5 = %s' % (bidx.shape, bidx.dtype, bidx[:5]))
    print('  `band_val`  shape=%s dtype=%s  前 5 = %s' % (bval.shape, bval.dtype, bval[:5]))
    print('  `band_fld`  shape=%s dtype=%s  前 5 = %s' % (bfld.shape, bfld.dtype, bfld[:5]))
    print()
    print('  ── `band_val` 分布 ──')
    print('     最小 %.4g ｜ 最大 %.4g ｜ **负值个数 = %d（%.1f%%）**'
          % (bval.min(), bval.max(), int((bval < 0).sum()),
             100.0 * (bval < 0).mean()))
    print('     ⇒ %s' % ('**有正有负 ⇒ 很可能是符号距离 φ**' if (bval < 0).any() and (bval > 0).any()
                        else '⚠ 全同号 ⇒ 可能不是符号距离'))
    print()
    print('  ── `band_fld` 的取值（非零场号）──')
    u = np.unique(bfld)
    print('     取值个数 = %d ｜ 前 20 = %s' % (len(u), u[:20]))
    print()
    # ★ 逐场物理体积（band_fld==k 且 band_val<0）
    print('  ── ★ 由 band 算的**逐场物理体积**（band_fld==k 且 band_val<0）──')
    tot_band = 0
    rowsb = []
    for k in sorted(int(x) for x in u if x != 0):
        m = (bfld == k) & (bval < 0)
        n = int(m.sum())
        tot_band += n
        if n > 0:
            rowsb.append((k, n))
    rowsb.sort(key=lambda t: -t[1])
    for k, n in rowsb[:12]:
        print('     场 %-5d 物理体积 = **%5d 胞**' % (k, n))
    print('     ⇒ 合计 = **%d 胞** ⇒ %.4f µm³' % (tot_band, tot_band * 62.5 ** 3 * 1e-9))
    print()
    # 交叉校验：与 series.csv 的 Vt 比
    try:
        rr = list(csv.DictReader(open('_exp/_bk_t5/dry_%s/series.csv' % TAG, newline='')))
        vt = None
        for r in reversed(rr):
            if abs(int(r['step']) - ST) <= 40:
                vt = float(r['Vt']); sr = r['step']; break
        if vt:
            print('  ── ★ 量具自洽判据 ──')
            print('     series.csv `Vt`（step %s）= **%.4f µm³**' % (sr, vt * 1e18))
            print('     由 band 算的相体积        = **%.4f µm³**' % (tot_band * 62.5 ** 3 * 1e-9))
            r_ = (tot_band * 62.5 ** 3) / max(vt, 1e-30)
            print('     ⇒ 比值 = **%.3f** ⇒ %s' % (r_,
                  '✅ 吻合（±15%% 内）⇒ **我理解了 band 的含义，可以逐场测物理体积**'
                  if 0.85 <= r_ <= 1.15 else
                  '⚠ 不吻合 ⇒ 我对 `band_*` 的理解**不对**，不能据此测物理体积'))
    except Exception as e:
        print('     （读 series.csv 失败：%s）' % e)
    # region 与 band 的对照
    print()
    print('  ── `region` vs `band`（同一场号）的对照（前 6 场）──')
    for k, n in rowsb[:6]:
        nr = int((reg == k).sum())
        print('     场 %-5d  region 胞数 = %-6d ｜ **band 物理胞数 = %-6d** ｜ 差 %+d'
              % (k, nr, n, n - nr))
