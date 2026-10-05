#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_wrapsmoke_test.py —— R623 ②-8（绕盒监控接线）的**分辨力正/负对照**。

## 为什么必须做正对照（`R581 P43` / `AGENTS.md` P12）
  接线冒烟（`dry_wrapsmoke`）跑出来三列**全是空串** ⇒ 那**不能**证明"没有绕盒"，
  也可能只是**这个量具在当前几何下永远返回空**。
  ⇒ 必须造一个**确定会绕盒**的组态，证明它**真的会报**。

## 做法
  同一 `LevelSetMulti`，两臂只差**板条质心的位置**：
    * 负对照：板条**完全在盒内** ⇒ 期望 `wrap_axes_any() == {}`
    * 正对照：板条**跨过盒壁**（`seed_plate` 用 `np.roll` 做周期 ⇒ 会折回另一侧）
      ⇒ 期望 **非空**（该场被判绕盒）
  ⚠ 正负对照只差一个因素（`AGENTS.md` 教训 21）。
"""
import sys

import numpy as np

sys.path.insert(0, ".")
import windowB_surface as WS  # noqa: E402

N = 32
DX = 62.5e-9
L = N * DX          # 2.0 µm
R = 4 * DX          # 盘半径 250 nm
T = 2 * DX          # 厚 125 nm


def build(ctr, periodic_seed):
    g = WS.LevelSetMulti(N, L, nv=2, gamma=0.0, Mob=1.0)
    g.phi[:] = 1e3
    g.phi[0] = -1e3
    # ⚠ 必须先 `nuc_cfg()`：`seed_plate` 从 `self._nuc` 读 `periodic_seed`
    #   （`windowB_surface.py:3133-3135`），而 `self._nuc` **只在 `nuc_cfg()` 里创建**。
    #   不调 ⇒ 开关恒 False ⇒ **最小镜像不生效** ⇒ 跨壁的种子被**裁掉**
    #   （实测：质心贴壁时占用胞数 104 → 52，恰好一半）。
    g.nuc_cfg(R, T, periodic_seed=bool(periodic_seed))
    g.seed_plate(1, np.asarray(ctr, float), np.array([0.0, 0.0, 1.0]), R, T)
    g.init_parent()
    return g


# 负对照：质心在盒中心 ⇒ 盘（R=250 nm）离任何壁都 >= 750 nm ⇒ 不可能绕盒
g_neg = build((L / 2, L / 2, L / 2), periodic_seed=True)
# 正对照：质心**贴在一侧壁上** ⇒ 盘跨过该壁 ⇒ 最小镜像把它接到另一侧 ⇒ 必然绕盒
g_pos = build((0.0, L / 2, L / 2), periodic_seed=True)

print("=" * 92)
print(f"N={N}  dx={DX*1e9:.1f} nm  L={L*1e6:.2f} µm  R={R*1e9:.0f} nm  t={T*1e9:.0f} nm")
print("=" * 92)

res = {}
for name, g, expect_empty in (("负对照 质心在盒中心", g_neg, True),
                              ("正对照 质心贴在 x=0 壁上", g_pos, False)):
    reg = g.region()
    occ = int((reg == 1).sum())
    wa = g.wrap_axes_any()
    ext, wax = g.region_extent(1)
    res[name] = wa
    print(f"\n  [{name}]")
    print(f"     场 1 占用胞数 = {occ}")
    print(f"     wrap_axes_any() = {wa}")
    print(f"     region_extent(1) 包围盒 = "
          f"{None if ext is None else np.round(ext*1e9, 1)} nm   轴={wax}")
    _ok = (len(wa) == 0) if expect_empty else (len(wa) > 0)
    print(f"     ⇒ {'PASS ✅' if _ok else '**FAIL** ❌'}（期望"
          f"{'无绕盒' if expect_empty else '检出绕盒'}）")

print("\n" + "=" * 92)
neg_empty = (len(res["负对照 质心在盒中心"]) == 0)
pos_nonempty = (len(res["正对照 质心贴在 x=0 壁上"]) > 0)
print("★ 分辨力自检（R581 P43）：负对照必须与正对照**不同**")
print(f"   负对照 空？ {neg_empty}      正对照 非空？ {pos_nonempty}")
ok = neg_empty and pos_nonempty
print(f"   ⇒ {'**有分辨力** ✅（同一量具能区分两种组态）' if ok else '**没有分辨力** ❌'}")
print("=" * 92)
print("总判定：" + ("**PASS**" if ok else "**FAIL**"))
print("=" * 92)
sys.exit(0 if ok else 1)
