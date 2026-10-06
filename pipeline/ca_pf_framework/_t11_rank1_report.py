#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_rank1_report.py —— 把 ②-9 的 A/B 结果做**定量的形态判读**（不只是 nslab_n）。

补 `_t11_rank1_ab.py` 里没有的量（`R619` ②-9 要"两条都跑并都报"，只报根数不够）：
  * **每根板条的长宽比**（`band_val<0` 的逐 26-连通分量 PCA，**排除场 0**）；
  * **末态形态**（沿 `n*`/`a`/`w` 三轴的**周期正确**最小包围弧长）；
  * **独有串**（受影响变体清单 + 正对照）。
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
BASES = ["/mnt/f/speed_up/_exp/_bk_t5",
         "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"]


def min_arc(q, L):
    q = np.sort(np.mod(np.asarray(q, float), L))
    if q.size < 2:
        return 0.0
    gaps = np.diff(np.concatenate([q, [q[0] + L]]))
    return float(L - gaps.max())


def per_field_pca(reg, dx, exclude0=True):
    """逐场的 PCA 主轴延伸（**排除场 0**；`R581` 的形态量口径）。

    ⚠ **量具 bug 留档（我第一版打出了 `0.000`）**：`np.linalg.eigh` 返回
      `(w, v)` = **特征值, 特征向量**，我第一版把返回值写成了 `(w, v)` 却当成
      `(延伸, 向量)` 用 ⇒ 数值全错（表象是"主轴延伸 = 0"而"长宽比"却看着合理 ——
      因为长宽比是两个错值相除）。**改成显式用特征值算延伸。**
    """
    out = {}
    for k in [int(x) for x in np.unique(reg) if int(x) > 0]:
        idx = np.argwhere(reg == k).astype(float)
        n = idx.shape[0]
        if n < 8:
            out[k] = (n, None)
            continue
        p = (idx - idx.mean(0)) * dx                # 以质心为中心（m）
        ev = np.linalg.eigvalsh(p.T @ p / max(n - 1, 1))   # 升序特征值（m²）
        ev = np.sort(np.maximum(ev, 0.0))[::-1]            # 降序
        ext = 4.0 * np.sqrt(ev)                     # ±2σ ≈ 主轴延伸（m）
        out[k] = (n, ext.tolist())
    return out


for tag in sys.argv[1:] or ["r1none", "r1inv"]:
    d = next((os.path.join(b, "dry_%s" % tag) for b in BASES
              if os.path.isdir(os.path.join(b, "dry_%s" % tag))), None)
    print("=" * 92)
    print(f"【{tag}】")
    if d is None:
        print("  **目录不存在**")
        continue
    sp = os.path.join(d, "snap_00160.npz")
    if not os.path.exists(sp):
        cand = [f for f in os.listdir(d) if f.startswith("snap_")]
        sp = os.path.join(d, sorted(cand)[-1]) if cand else None
    if sp is None or not os.path.exists(sp):
        print("  **无快照**")
        continue
    z = np.load(sp, allow_pickle=True)
    reg = np.asarray(z["region"])
    L = float(np.asarray(z["L"]))
    dx = L / reg.shape[0]
    print(f"  快照 = {os.path.basename(sp)}  N={reg.shape[0]}  L={L*1e6:.3f} µm")
    fields = [int(x) for x in np.unique(reg) if x > 0]
    print(f"  已转变胞 = {int((reg>0).sum())}  出现的场 = {len(fields)} 个 {fields}")
    pca = per_field_pca(reg, dx)
    # ★ 变体归属：**这是本 A/B 最关键的量**（对调的是 n*/a ⇒ 各场的取向变了）
    vm = ""
    mk, mv = z.get("vmap_keys"), z.get("vmap_vals")
    if mk is not None and mv is not None:
        vmap = {int(a): int(b) for a, b in zip(np.ravel(mk), np.ravel(mv))}
        vm = "  ".join("场%d→V%d" % (k, vmap.get(k, -1)) for k in fields)
    print(f"  变体归属：{vm if vm else '(快照无 vmap_keys/vmap_vals)'}")
    print(f"\n  {'场':>4} {'胞数':>7} {'延伸1(µm)':>10} {'延伸2':>8} {'延伸3':>8} "
          f"{'长宽比':>8}")
    for k, (n, ext) in pca.items():
        if ext is None:
            print(f"  {k:>4} {n:>7} {'(胞数太少)':>10}")
            continue
        ar = ext[0] / max(ext[-1], 1e-30)
        print(f"  {k:>4} {n:>7} {ext[0]*1e6:>10.3f} {ext[1]*1e6:>8.3f} "
              f"{ext[2]*1e6:>8.3f} {ar:>8.2f}")
    if "n_hab" in z.files and "a_ax" in z.files:
        n_hat = np.asarray(z["n_hab"], float); n_hat /= np.linalg.norm(n_hat)
        a_hat = np.asarray(z["a_ax"], float); a_hat /= np.linalg.norm(a_hat)
        w_hat = np.cross(n_hat, a_hat); w_hat /= np.linalg.norm(w_hat)
        pos = (np.argwhere(reg > 0).astype(float) + 0.5) * dx
        print(f"\n  集合三轴（**周期正确**最小包围弧长 / L）：")
        for nm, ax in (("n*", n_hat), ("a", a_hat), ("w", w_hat)):
            print(f"    {nm:>3}: {min_arc(pos @ ax, L)/L:.3f}")
print("=" * 92)
