#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_vface.py <tag> —— ★★ **直接测"面速率"**（不再从形状或 `Mfac` 反推）。

## 为什么必须换成它（本轮量具缺口的更正）
`windowB_surface.py:5074-5077` 逐字：
> 正确的"面速率"预言是 **面积加权平均的乘积** `v_face = <M(n)·dG>_face`，
> **不是** `M(标称法向) × dG 的某个百分位` —— 后一种写法在 `M(n)` 变化剧烈时会**系统性偏低**。
⇒ 我上一轮只量了 `<Mfac>` 的比值（49.4），**而面速率是 `<Mfac·dG>`** ⇒ **两者不是同一个量**。

## 本工具测什么（用已有快照 + CSV，不跑算例）
对指定场、指定 step 对：**按面族**测"界面位置沿该面法向的位移速率"，即
  `v_face = Δ(该面的平均位置) / Δstep`
面族用**引擎自己的三档定义**（`(n·a)²>0.81` 等，见 `:5084`）：`tip`/`side`/`wide`。
⇒ 得到 **`v_tip / v_wide`**（这才是"长/厚"的真实速度比）与 **`v_tip / v_side`**（长/宽）。
"""
import glob
import os
import sys

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
tag = (sys.argv[1] if len(sys.argv) > 1 else "kW1")
tag = tag[4:] if tag.startswith('dry_') else tag
field = int(sys.argv[2]) if len(sys.argv) > 2 else 2


def face_offsets(step):
    """返回该 step 上三档面的**平均外偏距离**（以场中心为基准，单位 nm）。"""
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % step)
    if not os.path.exists(p):
        return None
    with np.load(p, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        a, w, nh = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))
    m = (reg == field)
    if m.sum() < 50:
        return None
    d = distance_transform_edt(m)
    g = np.gradient(d, DX)
    gn = np.sqrt(sum(x ** 2 for x in g))
    band = m & (d <= 3.0) & (gn > 1e-9)
    nx = np.stack([g[0][band], g[1][band], g[2][band]], axis=1)
    nx = nx / np.maximum(np.linalg.norm(nx, axis=1, keepdims=True), 1e-300)
    pos = np.argwhere(band).astype(float) * DX
    c = np.argwhere(m).astype(float).mean(0) * DX      # 该场质心
    c2a = nx @ a; c2w = nx @ w; c2n = nx @ nh
    out = {}
    for name, comp, ax in (('tip', c2a, a), ('side', c2w, w), ('wide', c2n, nh)):
        sel = comp ** 2 > 0.81
        if sel.sum() < 20:
            out[name] = float('nan')
            continue
        # 该面族上"沿 ±ax"的有符号外偏，取正侧均值（板条单侧）
        off = (pos[sel] - c) @ ax
        out[name] = float(np.mean(off[off > 0])) * 1e9 if (off > 0).sum() > 10 \
            else float(np.mean(np.abs(off))) * 1e9
    return out


steps = []
for sp in sorted(glob.glob(os.path.join(ROOT, "dry_%s" % tag, "snap_*.npz"))):
    with np.load(sp, allow_pickle=False) as z:
        steps.append(int(np.asarray(z['step']).ravel()[0]))
steps.sort()
print("=" * 96)
print("【%s】场 %d 的**面速率**（直接测三档面的外偏位移）" % (tag, field))
print("=" * 96)
print("  %-7s %-11s %-11s %-11s" % ('step', 'tip(nm)', 'side(nm)', 'wide(nm)'))
tab = []
for s in steps:
    o = face_offsets(s)
    if o is None:
        continue
    tab.append((s, o))
    print("  %-7d %-11.0f %-11.0f %-11.0f"
          % (s, o['tip'], o['side'], o['wide']))
if len(tab) >= 2:
    s0, o0 = tab[0]
    s1, o1 = tab[-1]
    ds = max(s1 - s0, 1)
    vt = (o1['tip'] - o0['tip']) / ds
    vs = (o1['side'] - o0['side']) / ds
    vw = (o1['wide'] - o0['wide']) / ds
    print("\n  ⇒ 面速率（nm/步）step %d→%d：" % (s0, s1))
    print("     v_tip  = %+.4f   v_side = %+.4f   v_wide = %+.4f" % (vt, vs, vw))
    if vw > 0:
        print("     **v_tip/v_wide = %.2f**  （= 长/厚的真实速度比）" % (vt / vw))
    else:
        print("     ⚠ v_wide ≤ 0（宽面未外移）⇒ 比值无定义")
    if vs > 0:
        print("     **v_tip/v_side = %.2f**" % (vt / vs))
