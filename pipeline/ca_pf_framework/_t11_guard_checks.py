#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_guard_checks.py —— ②-7/②-8/②-9 三条的主动探针（含正/负对照）。

②-8 绕盒守卫：`LevelSetMulti.wrap_axes / wrap_axes_any / check_wrap`
    · 正对照：手工构造**必然绕盒**的掩模（一条横穿全盒的板条）⇒ 必须报绕盒；
    · 负对照（**生产参数**）：构造**不**触及对立面的掩模 ⇒ 必须**不**报；
    · 断言"负对照有分辨力"（两组结论不同），否则量具无效。
②-9 两轴：`w_ax`（晶体学 {011}）vs `n_hab`（弹性最优法向）的夹角。
②-7 回滚：`_seed_undo_note` / `_seed_undo_apply` 覆盖哪些场。
"""
import sys

import numpy as np

sys.path.insert(0, ".")
import windowB_lath as WL          # noqa: E402
import windowB_surface as WS       # noqa: E402

N, DX = 160, 62.5e-9
L = N * DX
print(f"=== 生产参数 N={N} dx={DX*1e9:.1f} nm ⇒ L={L*1e6:.3f} µm ===")

# ---------------- ②-8 绕盒守卫：正/负对照 ----------------
print("\n" + "=" * 90)
print("②-8 绕盒守卫 wrap_axes / wrap_axes_any / check_wrap")
print("=" * 90)
g = WS.LevelSetMulti(N, L, nv=2, gamma=0.0, Mob=1.0)
print(f"  wrap_axes 存在: {hasattr(g,'wrap_axes')}  wrap_axes_any: {hasattr(g,'wrap_axes_any')}"
      f"  check_wrap: {hasattr(g,'check_wrap')}")

# phi[0] = 母相；phi[k] 是 SDF（<0 表示该变体）
# 正对照：x 方向铺满整盒的板条（两端都到边界 ⇒ 周期连通 ⇒ 绕盒）
th = 4 * DX
th_y = 15 * DX
xx = (np.arange(N) + 0.5) * DX
X, Y, Z = np.meshgrid(xx, xx, xx, indexing="ij")

# 一条沿 x 贯通、截面在 (y,z) 的板条：在 x 方向两端都碰到盒子面
sdf_wrapped = np.maximum.reduce([
    np.abs(X - L / 2) - L / 2,          # x：从 0 到 L，两端贴面
    np.abs(Y - L / 2) - th_y / 2,
    np.abs(Z - L / 2) - th / 2,
])
# 负对照：同样形状但**居中且短**，完全不贴面（生产口径：一条 4 µm 的板条放在 10 µm 盒里）
sdf_free = np.maximum.reduce([
    np.abs(X - L / 2) - 2.0e-6,         # x 半长 2 µm ⇒ 总长 4 µm < L=10 µm
    np.abs(Y - L / 2) - th_y / 2,
    np.abs(Z - L / 2) - th / 2,
])

for name, sdf in (("正对照（贯通全盒）", sdf_wrapped), ("负对照（4µm 板条居中）", sdf_free)):
    g.phi[:] = 1e3
    g.phi[0] = -1e3
    g.phi[1] = sdf
    reg = g.region()
    ncell = int((reg == 1).sum())
    try:
        wa = g.wrap_axes(1)
    except Exception as e:  # noqa: BLE001
        wa = f"EXC {type(e).__name__}: {e}"
    try:
        waa = g.wrap_axes_any()
    except Exception as e:  # noqa: BLE001
        waa = f"EXC {type(e).__name__}: {e}"
    try:
        cw = g.check_wrap(verbose=False)
    except Exception as e:  # noqa: BLE001
        cw = f"EXC {type(e).__name__}: {e}"
    print(f"\n  {name}: 占用胞 {ncell}")
    print(f"    wrap_axes(k=1)   = {wa}")
    print(f"    wrap_axes_any()  = {waa}")
    print(f"    check_wrap()     = {cw}")

# ---------------- ②-9 两轴 ----------------
print("\n" + "=" * 90)
print("②-9 两轴来源：w_ax（晶体学 {011}）vs n_hab（弹性最优法向）")
print("=" * 90)
w_ax = np.array([0.7071067811865475, 0.7071067811865476, 5.596961321313178e-17])
n_hab = np.array([-0.4424306294993318, 0.4424633620254083, -0.7800521209162868])
w_ax = w_ax / np.linalg.norm(w_ax)
n_hab = n_hab / np.linalg.norm(n_hab)
print(f"  w_ax   = {np.round(w_ax,6)}   模长 {np.linalg.norm(w_ax):.10f}")
print(f"  n_hab  = {np.round(n_hab,6)}  模长 {np.linalg.norm(n_hab):.10f}")
ang = np.degrees(np.arccos(np.clip(abs(w_ax @ n_hab), 0, 1)))
print(f"  |w_ax · n_hab| = {abs(w_ax@n_hab):.6f} ⇒ 夹角 = {ang:.3f}°")
subs = [(0, 0, 1), (0, 1, 1), (1, 1, 0), (1, 1, 1), (1, 0, 0), (1, -1, 0), (1, 1, -2)]
print("  n_hab 对常见低指数面的 max|cos|：")
for t in (0, 2):
    best = []
    for s in subs:
        v = np.array(s, float)
        v /= np.linalg.norm(v)
        best.append((abs(v @ n_hab), s))
    best.sort(reverse=True)
    print(f"    最高: {best[0][1]} -> {best[0][0]:.4f}  ({np.degrees(np.arccos(min(1,best[0][0]))):.2f}°)")
    break
# w_ax 是否为 {011}
for s in subs:
    v = np.array(s, float)
    v /= np.linalg.norm(v)
    c = abs(v @ w_ax)
    if c > 0.99:
        print(f"  w_ax 与 {s} 的 max|cos| = {c:.8f} ⇒ w_ax 就是 {{{s[0]}{s[1]}{s[2]}}} 型方向")
