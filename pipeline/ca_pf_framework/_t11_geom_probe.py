#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_geom_probe.py —— **G7 取证**：量末态的**几何跨度**，判定越界撞的是哪个方向。

## 判据（可 FAIL）
  * 若"整块 α′"在**堆叠方向 `n*`** 上的跨度已接近 `L_box` ⇒ 越界来自**沿 t 叠不下**
    ⇒ 修法应让新片**换到面内空位**（新柱），而不是继续往外推。
  * 若跨度在**面内 (`a`/`w`)** 上接近 `L_box` ⇒ 越界来自**面内铺满** ⇒ 是另一回事。

⚠ 口径（`AGENTS.md` 明令）：**绕盒判定用"轴跨度"，`长nm`（PCA 主轴延伸）不能用于此**。
  本脚本按**稀疏快照**（`(cell, field)` 对）重建索引，再算**包围盒在三个正交方向上的跨度**：
    `n*`（堆叠方向）、`a`（长轴）、`w`（宽轴）—— 这三个才是板条的天然正交系。
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import windowB_surface as WS          # noqa: E402
import windowB_ti64_variants as V     # noqa: E402

TAG = sys.argv[1] if len(sys.argv) > 1 else "ifaceON"
SNAP = sys.argv[2] if len(sys.argv) > 2 else "snap_00400.npz"
BASE = "/mnt/f/speed_up/_exp/_bk_t5"
D = os.path.join(BASE, "dry_%s" % TAG)
sp = os.path.join(D, SNAP)
if not os.path.exists(sp):
    sys.exit(f"**找不到 {sp}**")
meta = json.load(open(os.path.join(D, "meta.json"), encoding="utf-8"))
ea = meta.get("exp_args", {}) or {}
N = int(ea.get("N", meta.get("N", 160)))
dx = float(ea.get("dx_nm", meta.get("dx_nm", 62.5))) * 1e-9
L = N * dx
nv = int(ea.get("nv", meta.get("nv", 0)))
print("=" * 94)
print(f"[{TAG}] {SNAP}   N={N}  dx={dx*1e9:.1f} nm  L={L*1e6:.3f} µm  nv={nv}")
print("=" * 94)

z = np.load(sp, allow_pickle=True)
print(f"快照键（{len(z.files)}）: {sorted(z.files)[:12]}")
ci = z["band_idx"] if "band_idx" in z.files else None
cv = z["band_val"] if "band_val" in z.files else None
cf = z["band_fld"] if "band_fld" in z.files else None
if ci is None:
    sys.exit("**快照里没有 band_idx** ⇒ 口径不符，需看该文件的键")
print(f"band_idx.shape = {ci.shape}   band_val.shape = {cv.shape}   "
      f"band_fld.shape = {cf.shape}")
# ⚠⚠ 口径（我连错三次，最后**把键全打出来**才定下来，见 `_t11_snap_shape.py`）：
#   * `band_idx` 是**线性索引** `0..N³−1`（不是三元组、也不是 (3,n)）；
#   * `band_val` = φ（m，负 = 已转变）；`band_fld` = 场号；
#   * **`region` 直接就是完整的 `(N,N,N)` 数组** —— 最干净的数据源。
#   ⇒ 本探针**用 `region`**，不再从稀疏对重建（少一层口径风险）。
reg = np.asarray(z["region"])
print(f"region shape={reg.shape}  出现的场 = {sorted(int(x) for x in np.unique(reg))}")
m_all = (reg > 0)
fld = reg[m_all]
print(f"已转变胞 = {int(m_all.sum())}")

# ---- 三个天然正交轴（用变体 1 的 n*/a/w；该算例全是变体 1）----
C = np.zeros((3, 3, 3, 3), float)
c11, c12, c44 = 134e9, 110e9, 36e9
for i in range(3):
    for j in range(3):
        C[i, i, j, j] = c11 if i == j else c12
        if i != j:
            C[i, j, i, j] = c44
            C[i, j, j, i] = c44
strains, F, meta_v = V.variants()
E = np.asarray(strains[0], float)
nref, _, _ = WS.argmin_normal_cached(C, E)
Rk = WS.LevelSetMulti._rank1_axes(E, nref)
n_hat = np.asarray(nref, float); n_hat /= np.linalg.norm(n_hat)
a_hat = np.asarray(Rk[1], float); a_hat /= np.linalg.norm(a_hat)
w_hat = np.asarray(Rk[2], float); w_hat /= np.linalg.norm(w_hat)
print(f"\n变体 1 的三轴：n*={np.round(n_hat,4)}  a={np.round(a_hat,4)}  "
      f"w={np.round(w_hat,4)}")

pos = (np.argwhere(m_all).astype(float) + 0.5) * dx
print(f"\n{'方向':>6} {'朴素跨度':>10} {'/L':>7} {'周期最小跨度':>12} {'/L':>7}  判定")


def _min_arc(pp, L):
    """★ 周期盒里的**最小包围弧长**（不是朴素包围盒！）。

    为什么必须换口径（`R623 §14.12`）：在周期盒里，若分布**绕过了边界**，
    朴素包围盒**必然 > L**（`max − min` 把两侧都算进去）—— 那是**几何假象**，
    不是"板条真的长到 1.6 L"。正确口径：把投影排序，找**最大间隙**，
    则最小包围弧长 = `L − 最大间隙`（= 能盖住全部点的最短周期区间）。
    ⚠ 这不改变任何物理，只改**读数**（`AGENTS.md` 的"量具"纪律）。
    """
    q = np.sort(np.mod(pp, L))
    if q.size < 2:
        return 0.0
    gaps = np.diff(np.concatenate([q, [q[0] + L]]))
    return float(L - gaps.max())


for nm, ax in (("n*（堆叠）", n_hat), ("a（长轴）", a_hat), ("w（宽轴）", w_hat)):
    p = pos @ ax
    span = float(p.max() - p.min())
    marc = _min_arc(p, L)
    frac, mfrac = span / L, marc / L
    verdict = ("**绕盒（朴素跨度失真，看周期跨度）**" if frac > 1.0
               else ("接近/超出盒子 ⇒ 该方向撞壁" if frac > 0.85
                     else ("偏紧" if frac > 0.6 else "有余量")))
    print(f"{nm:>10} {span*1e6:>10.3f} {frac:>7.3f} {marc*1e6:>12.3f} "
          f"{mfrac:>7.3f}  {verdict}")

print(f"\n（对照）L_box = {L*1e6:.3f} µm ；plate_t = "
      f"{float(ea.get('plate_T', 510))*1e-9*1e6:.3f} µm ；"
      f"L/t = {L/(float(ea.get('plate_T',510))*1e-9):.1f} 层")
print("\n★ 判读：若 **n* 方向**的跨度/L 接近 1 ⇒ `G7` 的越界来自**沿 t 叠不下**，")
print("   修法 = 让新片**换到面内空位**（新柱）而不是继续往外推。")
print("   若 **a/w 方向**接近 1 ⇒ 是面内铺满，属另一回事。")
print("=" * 94)
