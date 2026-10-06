#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_vface2.py <tag> [...] —— ★★★ **用引擎自己的 `φ` 做"按取向测速度"**（已校准量具）。

## 为什么换成本工具（`R636 §6` 的量具被推翻后的替代）
我此前两个量具都有缺陷：
  · `_t11_normal_dist.py`：法向用 **EDT 近似**、带取 `d ≤ 3dx` ⇒ 带太宽、法向被平均；
  · `_t11_vface*.py`：同上，且只取质心单侧均值 ⇒ 阈值一改结论就翻转。
**本工具改用仓库**已过正对照**的做法**（`_r45_facechk.py`，三档相对差 ≤2.4%）：
  · 法向 = **`∇φ`**（`φ` 直接取自快照的 **`band_val`**，就是引擎自己的场）；
  · 界面带 = **`|φ| ≤ 1.5·dx`**（`_r45_facechk.py:54`）；
  · 三档阈值 = **`(n·u)² > 0.81`**（`windowB_surface.py:5084`）；
  · 保留 **`oblique`** 档并**报其占比**（量具正对照里光滑长方体该档 ≈4.7%）。

## 判据（可 FAIL，先登记）
  · **W1（量具自洽）**：`oblique` 占比应 **< 20%**（正对照 4.7%；超过说明界面确实很乱）；
  · **W2**：三档都要**测得到**（每档 ≥ 30 胞）；
  · **W3（长厚速度比）**：`v_tip/v_wide` —— 与设计值对照。

## 怎么测速度
对两个快照，按"该档面的**平均有符号外偏**沿其轴"算位移/步（分正负两侧，取两侧平均）。
"""
import glob
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"


def load(tag, step):
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % step)
    if not os.path.exists(p):
        return None
    with np.load(p, allow_pickle=False) as z:
        N = int(np.asarray(z['N']).ravel()[0])
        L = float(np.asarray(z['L']).ravel()[0])
        dx = L / N
        phi = np.full((N, N, N), np.nan)
        idx = np.asarray(z['band_idx'])
        val = np.asarray(z['band_val'], float)
        ii, jj, kk = np.unravel_index(idx, (N, N, N))
        phi[ii, jj, kk] = val
        return dict(phi=phi, dx=dx, N=N,
                    a=np.asarray(z['a_ax'], float),
                    w=np.asarray(z['w_ax'], float),
                    nh=np.asarray(z['n_hab'], float))


def faces_and_pos(d, C, step):
    """返回 {档: (胞数, 该类胞的坐标数组)} 与 oblique 占比。"""
    phi = np.nan_to_num(C['phi'], nan=1e9)
    dx = C['dx']
    g = np.gradient(phi, dx, edge_order=1)
    gn = np.sqrt(sum(x ** 2 for x in g)) + 1e-30
    iface = np.abs(phi) <= 1.5 * dx
    nd = [x / gn for x in g]
    c2 = {}
    for tag, u in (('tip', C['a']), ('side', C['w']), ('wide', C['nh'])):
        c2[tag] = np.clip(sum(nd[i] * u[i] for i in range(3)) ** 2, 0.0, 1.0)
    tot = int(iface.sum())
    hit = np.zeros(iface.shape, bool)
    out = {}
    for tag in ('tip', 'side', 'wide'):
        m = iface & (c2[tag] > 0.81)
        out[tag] = m
        hit |= m
    obl = iface & (~hit)
    return out, c2, obl, tot


for tag in (sys.argv[1:] or ["kW1"]):
    t = tag[4:] if tag.startswith('dry_') else tag
    ps = sorted(glob.glob(os.path.join(ROOT, "dry_%s" % t, "snap_*.npz")))
    steps = []
    for sp in ps:
        with np.load(sp, allow_pickle=False) as z:
            steps.append(int(np.asarray(z['step']).ravel()[0]))
    steps.sort()
    if len(steps) < 3:
        print("【%s】快照不足" % t)
        continue
    s0, s1 = steps[1], steps[-1]
    C0, C1 = load(t, s0), load(t, s1)
    if C0 is None or C1 is None:
        continue
    print("=" * 96)
    print("【%s】按取向测速度（engine φ；step %d→%d）" % (t, s0, s1))
    print("=" * 96)
    f0, c0, obl0, tot0 = faces_and_pos(None, C0, s0)
    f1, c1, obl1, tot1 = faces_and_pos(None, C1, s1)
    print("  界面胞 %d→%d ；`oblique` 占比 %.1f%%→%.1f%%（正对照 4.7%%）"
          % (tot0, tot1, 100.0 * obl0.sum() / max(tot0, 1),
             100.0 * obl1.sum() / max(tot1, 1)))
    dx, N = C0['dx'], C0['N']
    ds = max(s1 - s0, 1)
    print("  %-7s %-9s %-13s %-13s %s"
          % ('档', '胞数', 'r0(nm)', 'r1(nm)', 'v(nm/步)'))
    res = {}
    for tag2, u in (('tip', C0['a']), ('side', C0['w']), ('wide', C0['nh'])):
        pos0 = np.argwhere(f0[tag2]).astype(float) * dx
        pos1 = np.argwhere(f1[tag2]).astype(float) * dx
        if len(pos0) < 30 or len(pos1) < 30:
            print("  %-7s %-9d %-13s %-13s ⚠ 胞数不足" % (tag2, len(pos0), '—', '—'))
            continue
        ctr0 = np.argwhere(~np.isnan(C0['phi'])).astype(float).mean(0) * dx
        ctr1 = np.argwhere(~np.isnan(C1['phi'])).astype(float).mean(0) * dx
        o0 = (pos0 - ctr0) @ u
        o1 = (pos1 - ctr1) @ u
        r0 = float(np.mean(np.abs(o0))) * 1e9
        r1 = float(np.mean(np.abs(o1))) * 1e9
        v = (r1 - r0) / ds
        res[tag2] = v
        print("  %-7s %-9d %-13.1f %-13.1f **%+.4f**" % (tag2, len(pos0), r0, r1, v))
    if 'tip' in res and 'wide' in res and abs(res['wide']) > 1e-9:
        print("\n  ⇒ **`v_tip/v_wide` = %+.2f**  （= 长/厚的真实速度比）"
              % (res['tip'] / res['wide']))
    if 'tip' in res and 'side' in res and abs(res['side']) > 1e-9:
        print("  ⇒ **`v_tip/v_side` = %+.2f**" % (res['tip'] / res['side']))
