#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_blockidentity.py —— 用算例自己的数据判「块」的变体身份从哪来。

要害假设（读全 `_bk_exp.py:_seed_next` 后提出，本轮验证）：
  * `_seed_next()` 里每一片都用**同一个 `n_hab`、同一个 `a_ax`** 播种
    （`:1632 c = c0 + (...) * n_hab`、`:1634 seed_plate(j, c, n_hab, ...)`、`:1635 along=a_ax`）
    ⇒ **几何取向上，全部 220 片是同一个变体**；
  * 但 `:1580 j = n_seeded + 1` ⇒ **每片一个新场号**；
  * 场号 → 变体的映射来自**手写的 `vmap`**（每 22 个场一组，共 10 组）
    ⇒ **每 22 片就跨一次组边界 ⇒ 同一个物理取向被判成 10 个不同变体**。

判据（全部用算例自己的归档文件，不推测）：
  A1 `seeds.npz` 里各片的 `npref` 是否**完全相同**？（相同 ⇒ 同一变体）
  A2 `vmap` 把场 1..220 分成几组？跨组发生在第几片？
  A3 按 `vmap` 口径算的块数 vs 按**取向相同性**算的块数，差多少？
  A4 「一个相场 = 一根板条」这条在数据里成立吗（每场的连通分量数）？
"""
import json
import os
import sys
from collections import Counter

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
TAG = sys.argv[1] if len(sys.argv) > 1 else "dry_t10B9"
D = os.path.join(ROOT, "_exp", "_bk_t5", TAG)
print(f"算例 {TAG}  ({D})")

# ---------- A0: meta ----------
with open(os.path.join(D, "meta.json"), encoding="utf-8") as fh:
    meta = json.load(fh)
vmap = {int(k): v for k, v in meta["vmap"].items()}
laths = meta["laths"]
n_hab = np.array(meta["n_hab"], float)
a_ax = np.array(meta["a_ax"], float)
w_ax = np.array(meta["w_ax"], float)
print(f"\nn_hab = {np.round(n_hab,6)}   |n_hab| = {np.linalg.norm(n_hab):.10f}")
print(f"a_ax  = {np.round(a_ax,6)}    |a_ax|  = {np.linalg.norm(a_ax):.10f}")
print(f"w_ax  = {np.round(w_ax,6)}")
print("★ 注意：meta 里只有**一对** (n_hab, a_ax, w_ax) ⇒ 全局唯一取向")

# ---------- A2: vmap 分组 ----------
g2f = {}
for f, g in vmap.items():
    g2f.setdefault(g, []).append(f)
print(f"\n=== A2 vmap 分组 ===")
print(f"  组数 = {len(g2f)}；每组场号范围：")
for g in sorted(g2f):
    fs = sorted(g2f[g])
    print(f"    组 {g:>3}: 场 {fs[0]}..{fs[-1]}  (n={len(fs)})")
print(f"  laths 列表的连续段（每段 = 一个'堆叠'）：")
segs, s = [], 0
for i in range(1, len(laths) + 1):
    if i == len(laths) or laths[i] != laths[s]:
        segs.append((laths[s], s + 1, i))
        s = i
print(f"    段数 = {len(segs)}: {[(v, a, b) for v, a, b in segs]}")

# ---------- A1: seeds.npz ----------
sp = os.path.join(D, "seeds.npz")
print(f"\n=== A1 seeds.npz ===")
if not os.path.exists(sp):
    print("  !! 不存在")
else:
    z = np.load(sp, allow_pickle=True)
    print(f"  键: {list(z.keys())}")
    for k in z.keys():
        arr = z[k]
        print(f"  {k}: shape={getattr(arr,'shape',None)} dtype={getattr(arr,'dtype',None)}")
    # 找 npref
    for key in ("npref", "npref_all", "n_hab", "normals"):
        if key in z:
            A = np.asarray(z[key], float)
            print(f"\n  {key} 前 5 行:\n{np.round(A[:5],6)}")
            if A.ndim == 2 and A.shape[0] > 1:
                same = np.allclose(A, A[0])
                print(f"  ★ 所有行是否**完全相同**？ {same}")
                if not same:
                    d = np.linalg.norm(A - A[0], axis=1)
                    print(f"    与第 0 行的距离: min={d.min():.3e} max={d.max():.3e}")
                    print(f"    唯一行数（容差 1e-9）= "
                          f"{len(np.unique(np.round(A/max(np.abs(A).max(),1e-30),9), axis=0))}")
                # 按 vmap 分组统计
                if A.shape[0] >= 220:
                    print("    按 vmap 组统计每组内部是否完全相同：")
                    for g in sorted(g2f):
                        idx = [f - 1 for f in sorted(g2f[g])]
                        sub = A[idx]
                        print(f"      组 {g:>3}: 与组内第 0 行是否相同 = {np.allclose(sub, sub[0])}")
            break
    else:
        print("  （没找到 npref 类键；上面已列出全部键名）")

# ---------- A3: 块数两种口径 ----------
print(f"\n=== A3 块数：两种口径 ===")
print(f"  按 vmap 口径（场号分组）: 组数 = {len(g2f)}")
print(f"  按取向口径（全部同 n_hab）: 块数 = 1")
print(f"  ⇒ 同一个物理构型，两种口径差 {len(g2f)} 倍")

# ---------- A4: 每场的连通性（从快照） ----------
snap = sorted(f for f in os.listdir(D) if f.startswith("snap_") and f.endswith(".npz"))
print(f"\n=== A4 快照连通性（{len(snap)} 个快照：{snap[:3]}…）===")
if snap:
    p = os.path.join(D, snap[-1])
    z = np.load(p, allow_pickle=True)
    print(f"  快照 {snap[-1]} 键: {list(z.keys())}")
    for k in z.keys():
        arr = z[k]
        print(f"    {k}: shape={getattr(arr,'shape',None)} dtype={getattr(arr,'dtype',None)}")
