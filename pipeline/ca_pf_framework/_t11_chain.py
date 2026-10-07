#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_chain.py <tag> —— **传递链分解**：把 `Mfac` 设计极比 585 → 实测 `Λ` 3.25 的每一级损耗量出来。

## 为什么做这一步（`R658 §4.2`）
A2 的修正判据已确认**极图非凸**（刻面在数学上允许），
但实测兑现率只有 **0.43–0.79%** ⇒ 瓶颈在"各向异性 → 形状"的传递。
**阶段 C 是否值得做，取决于这一级的损耗是不是"数值表示"造成的。**

## 传递链（4 级）与各自的判据
| 级 | 量 | 来源 |
|---|---|---|
| ① | `Mfac` 极图极比 = **585.4** | `_t11_A2b_wulff.py`（解析） |
| ② | **界面法向速度比** `v_tip/v_side` | CSV 列 `v_tip_nabs` / `v_side_nabs` |
| ③ | **形状跨度比** `Λ_shape` = (a 跨度)/(厚度跨度) | 快照逐场（与 `R647` 同口径） |
| ④ | 实测 `Λ`（回转张量 `R1/R3`） | `_t11_cmp3.py` |

⇒ **每级的"兑现率" = 本级 / 上一级**，即可定位损耗发生在哪一级。
"""
import csv
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
MFAC_RATIO = 585.4          # `_t11_A2b_wulff.py` 实测
MFAC_W = 8.35               # Mfac(a)/Mfac(w) = 0.9006/0.1079


def rows(tag):
    p = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
    out = {}
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                out[int(r["step"])] = r
            except (KeyError, ValueError):
                pass
    return out


def f(r, k):
    try:
        v = float(r.get(k, "") or "nan")
        return v
    except ValueError:
        return float("nan")


print("=" * 108)
print("传递链分解（`γ·κ/Δf` 之外的另一条线）：设计极比 585.4 → 实测 Λ")
print("=" * 108)
for tag in (sys.argv[1:] or ["L0", "B40"]):
    R = rows(tag)
    if not R:
        print("【%s】无 CSV" % tag)
        continue
    print("\n【%s】" % tag)
    print("  %-6s %-11s %-11s %-13s %-12s %-12s %s"
          % ("step", "v_tip_nabs", "v_side_nabs", "② v_tip/v_side",
             "②兑现率", "dG_obl", "n_obl"))
    for st in sorted(R):
        if st % 100 and st != 0:
            continue
        r = R[st]
        vt, vs = f(r, "v_tip_nabs"), f(r, "v_side_nabs")
        vw = f(r, "v_wide_nabs")
        ratio = vt / vs if vs and vs == vs and vs > 0 else float("nan")
        # ②兑现率 = (比-1)/(设计比-1)
        r2 = (ratio - 1.0) / (MFAC_RATIO - 1.0) if ratio == ratio else float("nan")
        print("  %-6d %-11.4g %-11.4g %-13.3f %-12.3e %-12.4g %s"
              % (st, vt, vs, ratio, r2, f(r, "dG_obl"),
                 r.get("n_obl", "?")))
    # 形状跨度比（③）：用快照
    print()
    print("  ③ 形状跨度比（逐场，`(n*,a,w)` 三轴）：")
    d = os.path.join(ROOT, "dry_%s" % tag)
    sts = sorted(int(x[5:10]) for x in os.listdir(d) if x.startswith("snap_"))
    if sts:
        for st in sts[::max(1, len(sts) // 5)][:6]:
            with np.load(os.path.join(d, "snap_%05d.npz" % st), allow_pickle=False) as z:
                N = int(np.asarray(z["N"]).ravel()[0])
                L = float(np.asarray(z["L"]).ravel()[0])
                dx = L / N
                idx = np.asarray(z["band_idx"])
                val = np.asarray(z["band_val"], float)
                fl = np.asarray(z["band_fld"])
                reg = np.asarray(z["region"]).astype(np.int32)
                U = np.stack([np.asarray(z["n_hab"], float),
                              np.asarray(z["a_ax"], float),
                              np.asarray(z["w_ax"], float)], 0)
                ii = (np.arange(N) + 0.5) * dx
                P = np.stack(np.meshgrid(ii, ii, ii, indexing="ij"), -1).reshape(-1, 3)
            fls = [int(v) for v in np.unique(fl) if v > 0]
            best = None
            for k in fls:
                nk = int((reg == k).sum())
                if best is None or nk > best[1]:
                    best = (k, nk)
            if best is None:
                continue
            k = best[0]
            g = np.full(N ** 3, 1e3)
            m = (fl == k)
            g[idx[m]] = val[m]
            pr = P[g < 0] @ U.T
            if len(pr) < 100:
                continue
            span = pr.max(0) - pr.min(0)
            print("     step %-5d 场%-4d 胞%-7d  跨度[%.0f, %.0f, %.0f] nm"
                  "  ⇒ **a/厚 = %.2f**  a/w = %.2f"
                  % (st, k, int((reg == k).sum()), span[0] * 1e9, span[1] * 1e9,
                     span[2] * 1e9, span[1] / max(span[2], 1e-30),
                     span[1] / max(span[0], 1e-30)))
print()
print("  ⇒ 判读：")
print("     · **②兑现率** 若远小于 1 ⇒ 损耗在'驱动力/迁移率 → 界面速度'这一步（表示层）")
print("     · **②高但 ③低** ⇒ 损耗在'速度 → 形状'的积分（曲率/邻域耦合）")
print("     · 设计参照：`Mfac(a)/Mfac(n*)` = %.1f、`Mfac(a)/Mfac(w)` = %.2f"
      % (MFAC_RATIO, MFAC_W))
