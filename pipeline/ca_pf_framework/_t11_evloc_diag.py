#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_evloc_diag.py —— 查清 `evloc_*` 里"两个落点距离恰为 0"到底是哪两个场。

嫌疑：某两个场号在 `region()` 下**取到同一批胞**（例如同变体的多个场被合并，
或某场还没被 seed 进去）。⇒ 把每次事件的 (k, region 胞数, 质心) 全打出来。
"""
import sys

import numpy as np

sys.path.insert(0, ".")
import windowB_surface as WS  # noqa: E402

N, DX = 32, 62.5e-9
L = N * DX
R, T = 4 * DX, 2 * DX

g = WS.LevelSetMulti(N, L, nv=6, gamma=0.0, Mob=1.0)
g.phi[:] = 1e3
g.phi[0] = -1e3
g.nuc_cfg(R, T, periodic_seed=True)
g.init_parent()
g.vmap = {i: i for i in range(1, 7)}      # 场 k ↔ 变体 k
g.npref_tab = {i: np.array([0.0, 0.0, 1.0]) for i in range(7)}

pts = []
ctr_base = np.array([L / 2, L / 2, L / 2])
print("=" * 96)
for k in range(2, 7):
    c = ctr_base + np.array([0.0, 0.0, (k - 2) * (T + 1.0 * DX)])
    c = c % L
    try:
        g.seed_plate(k, c, np.array([0.0, 0.0, 1.0]), R, T)
    except Exception as exc:
        print(f"  seed_plate(k={k}) 抛错: {type(exc).__name__}: {exc}")
    reg = g.region()
    idx = np.argwhere(reg == k)
    ncell = int(idx.size // 3) if idx.size else 0
    ctr = ((idx + 0.5).mean(0)) * DX if ncell else None
    pts.append((k, ncell, ctr))
    print(f"  场 {k}: region 胞数={ncell:5d}  质心="
          f"{None if ctr is None else np.round(ctr*1e9,1)} nm   seed 位置="
          f"{np.round(c*1e9,1)} nm")

print("\n" + "=" * 96)
print("落点两两距离（最小镜像）:")
wm = g.wrap_axes_any()
print(f"  wrap_axes_any() = {wm}")
for i in range(len(pts)):
    for j in range(i + 1, len(pts)):
        if pts[i][2] is None or pts[j][2] is None:
            print(f"   {pts[i][0]}-{pts[j][0]}: 不可测（某场胞数为 0）")
            continue
        d = pts[i][2] - pts[j][2]
        d = d - L * np.round(d / L)
        print(f"   场 {pts[i][0]}-{pts[j][0]}: {np.linalg.norm(d)*1e9:8.1f} nm"
              f"   （胞数 {pts[i][1]} / {pts[j][1]}）")
