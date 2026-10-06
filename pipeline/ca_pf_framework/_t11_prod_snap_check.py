#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_prod_snap_check.py —— 对**生产跑自己的快照**做绕盒/形态量具检查。

## 为什么
  `R625 §4.6.10` 判定：`elong=7` ⇒ 引擎核长轴 4.48 µm；
  生产盒 10 µm ⇒ 占 **44.8%** ⇒ **有绕盒污染风险**。
  ⇒ 必须在**生产盒**上实测「自贯通场数」，而不是只从 5 µm 盒的 dose 臂外推。

## 用法
  _t11_prod_snap_check.py <tag>     # 默认 dry_t10PROD1
"""
import glob
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
TAG = sys.argv[1] if len(sys.argv) > 1 else "dry_t10PROD1"
d = os.path.join(ROOT, TAG)
sns = sorted(glob.glob(os.path.join(d, "snap_*.npz")))
print("=" * 100)
print(f"生产快照绕盒/形态检查 —— {TAG}（{len(sns)} 个快照）")
print("=" * 100)
if not sns:
    sys.exit("  **无快照**")
print("  快照：", ", ".join(os.path.basename(s) for s in sns))

for sp in sns:
    with np.load(sp, allow_pickle=False) as z:
        keys = list(z.files)
        reg = np.asarray(z['region']).astype(np.int32)
        N = reg.shape[0]
    DXd = None
    for k in ('dx', 'dx_nm', 'dx_m'):
        if k in keys:
            DXd = float(np.asarray(z[k]).ravel()[0])
            break
    # 兜底：从 meta.json 读 dx
    if DXd is None:
        import json
        mj = os.path.join(d, "meta.json")
        if os.path.exists(mj):
            j = json.load(open(mj, encoding="utf-8"))
            a = j.get("exp_args", j)
            for k in ("dx_nm", "dx-nm"):
                if k in a:
                    DXd = float(a[k]) * 1e-9
                    break
    print(f"\n  【{os.path.basename(sp)}】N={N}  dx={None if DXd is None else DXd*1e9}"
          f" nm  盒 L={None if DXd is None else N*DXd*1e6:.2f} µm")
    print(f"     快照键：{keys}")
    if DXd is None:
        print("     ⚠ 无法确定 dx ⇒ **无法判定**（不得下结论）")
        continue
    L = N * DXd
    flds = sorted(int(v) for v in np.unique(reg) if v != 0)
    print(f"     非零场数 = {len(flds)}")
    if not flds:
        print("     （尚无产物场）")
        continue
    nself, ars = 0, []
    for k in flds:
        idx = np.argwhere(reg == k).astype(np.float64) * DXd
        if idx.shape[0] < 8:
            continue
        c = idx - idx.mean(0)
        w, v = np.linalg.eigh(c.T @ c)
        o = np.argsort(w)[::-1]
        spn, spp = [], []
        for j in range(3):
            p = np.sort(idx @ v[:, o[j]])
            spn.append(p[-1] - p[0] + DXd)
            gaps = np.diff(p)
            spp.append(L - max(gaps.max() if gaps.size else 0.0,
                               L - (p[-1] - p[0])))
        if spn[0] > 0.6 * L:
            nself += 1
        ars.append(spp[0] / max(spp[1], 1e-30))
    print(f"     **自贯通场数 = {nself}/{len(flds)}**"
          f"{'   ⚠ 有绕盒污染' if nself else '   ✅ 无绕盒'}")
    if ars:
        print(f"     β比(周期口径) 中位 {np.median(ars):.2f}  "
              f"[{min(ars):.2f}, {max(ars):.2f}]")
    print(f"     引擎核长轴 2R·elong = 4.48 µm ⇒ 占盒长 "
          f"{4.48 / (L * 1e6):.1%}")