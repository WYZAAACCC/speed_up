#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_wrap_diag.py —— 分清两种"绕盒"（`R623 §14.12` 的判据 4 细化）。

## 为什么必须分（我的"绕盒"判据此前分辨力不足）
  `wrap_axes_any()` 判的是**单个场 `k` 自身**是否周期贯通。而实测 `g7ON` 报了
  **20+ 个场绕盒**，且三轴最小跨度都 ≈ L。两种完全不同的情形会给出这个读数：

  * **(a) 单根板条跨过盒壁**（`elong*R` 与盒尺寸同量级时**必然发生**）
    ⇒ 物理上正常（用户 ⑧ 明确要求"监控周期边界有没有正确发挥作用"）；
  * **(b) 整个 α′ 网络沿某方向**渗透**（= 跨场连成一条贯通链）
    ⇒ 那是 `impingement` 的表现，但**也会让"长度/长径比"读数失效**。

  判据：对每个场，算**它自己**的最小包围弧长（周期口径）。
    * `单场弧长/L` 都 **< 1** ⇒ 只有 (a)（每根是有限长的，只是跨了壁）；
    * 有场的弧长 **≈ L** ⇒ 该场**自身**就贯通 ⇒ (b)。

  另外**逐场胞数**也很关键：若某场胞数远小于"一根完整板条"的体积，那它根本不是
  一整根（是碎片/被啃掉），`wrap` 读数对它没有物理意义。
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

BASES = ["/mnt/f/speed_up/_exp/_bk_t5",
         "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"]
tags = sys.argv[1:] or ["g7OFF", "g7ON"]


def min_arc(q, L):
    q = np.sort(np.mod(np.asarray(q, float), L))
    if q.size < 2:
        return 0.0
    gaps = np.diff(np.concatenate([q, [q[0] + L]]))
    return float(L - gaps.max())


for tag in tags:
    d = next((os.path.join(b, "dry_%s" % tag) for b in BASES
              if os.path.isdir(os.path.join(b, "dry_%s" % tag))), None)
    print("=" * 92)
    print(f"【{tag}】")
    if d is None:
        print("  **目录不存在**")
        continue
    sp = os.path.join(d, "snap_00400.npz")
    if not os.path.exists(sp):
        print("  **无 snap_00400.npz**")
        continue
    z = np.load(sp, allow_pickle=True)
    reg = np.asarray(z["region"])
    L = float(np.asarray(z["L"]))
    dx = L / reg.shape[0]
    n_hat = np.asarray(z["n_hab"], float); n_hat /= np.linalg.norm(n_hat)
    a_hat = np.asarray(z["a_ax"], float); a_hat /= np.linalg.norm(a_hat)
    w_hat = np.cross(n_hat, a_hat); w_hat /= np.linalg.norm(w_hat)
    fields = [int(x) for x in np.unique(reg) if x > 0]
    print(f"  N={reg.shape[0]}  L={L*1e6:.3f} µm  dx={dx*1e9:.1f} nm  "
          f"出现的场 = {len(fields)} 个")
    print(f"  已转变胞 = {int((reg > 0).sum())}")
    # 逐场
    print(f"\n  {'场':>3} {'胞数':>7} {'体积(µm³)':>10} "
          f"{'n*弧/L':>8} {'a弧/L':>8} {'w弧/L':>8}  备注")
    n_self_span = 0
    for k in fields:
        m = (reg == k)
        n = int(m.sum())
        p = (np.argwhere(m).astype(float) + 0.5) * dx
        fr = [min_arc(p @ ax, L) / L for ax in (n_hat, a_hat, w_hat)]
        note = ""
        if max(fr) > 0.95:
            note = "**该场自身贯通**"
            n_self_span += 1
        print(f"  {k:>3} {n:>7} {n*dx**3*1e18:>10.4f} "
              f"{fr[0]:>8.3f} {fr[1]:>8.3f} {fr[2]:>8.3f}  {note}")
    print(f"\n  ★ 自身贯通的场数 = {n_self_span} / {len(fields)}")
    print("     ⇒ " + ("**存在 (b)：单场自身贯通** ⇒ 该场的长度读数无效"
                       if n_self_span else
                       "**只有 (a)：没有单场自身贯通** ⇒ 逐根板条仍是有限长，"
                       "只是跨了盒壁（周期边界在正常工作）"))
print("=" * 92)
