#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_thick3.py <tag>@<step> —— **D5：用三个口径量厚度**（修掉"包围盒跨度"伪影）。

## 为什么要三个口径（`R581_TASK5_VERDICT.md:7236-7253`，仓库已定论）
> `n_%d`（= 板条胞沿 `n*` 的**包围盒跨度**）**不是板条厚度**：
> 实测 `mb1s` 场 1 的包围跨度 624 → **2631 nm**，而由 `φ` 量出的两张宽面之间距离只有 780 → **732 nm**
> ⇒ 包围跨度被**碎片**与 **`n*` 与真实板条法向的 7.3° 夹角**（`n*·a = −0.127`）撑大
> ⇒ **R29 那批 `V-8b` FAIL 至少部分是口径伪影**

仓库给的**两个正确口径**（`:7249-7253` 的实测表）：
| 口径 | 性质 |
|---|---|
| **PCA 主轴跨度** | ✅ **对倾斜免疫** |
| **S/V 反解厚度** | ✅ **对碎片/倾斜稳健** |

⚠ **而我一直用的"三轴跨度比"正是被证伪的那个口径** ⇒ 本工具同时报三个，供对账。

## 判据（先登记）
| 量 | 期望 |
|---|---|
| 三口径的**厚度**是否一致（相对差 ≤30%） | 若差很大 ⇒ 证实"包围盒跨度"有伪影 |
| S/V 反解厚度 | **稳健值** ⇒ 作为"厚度"的可信读数 |
| PCA 长/厚 | 与 S/V 反解一致则互相支持 |
"""
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"


def load(tag, st):
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % (st,))
    if not os.path.exists(p):
        return None
    with np.load(p, allow_pickle=False) as z:
        N = int(np.asarray(z['N']).ravel()[0])
        L = float(np.asarray(z['L']).ravel()[0])
        dx = L / N
        ii = (np.arange(N) + 0.5) * dx
        P = np.stack(np.meshgrid(ii, ii, ii, indexing='ij'), -1).reshape(-1, 3)
        return dict(N=N, dx=dx, P=P,
                    idx=np.asarray(z['band_idx']),
                    val=np.asarray(z['band_val'], float),
                    fld=np.asarray(z['band_fld']),
                    reg=np.asarray(z['region']).astype(np.int32),
                    U=np.stack([np.asarray(z['n_hab'], float),
                                np.asarray(z['a_ax'], float),
                                np.asarray(z['w_ax'], float)], 0))


print("=" * 112)
print("D5：厚度三口径对照（修掉『包围盒跨度』伪影；仓库 `R36`/`P1-21` 已证伪该口径）")
print("=" * 112)
print("  %-7s %-6s %-6s %-30s %-26s %-12s %s"
      % ('tag', 'step', '场', '① 三轴跨度比 a/厚 (旧口径)', '② PCA 主轴比 长/厚',
         '③ S/V 厚度', '②③自洽?'))
for spec in (sys.argv[1:] or ["L0@300", "B40@300"]):
    tag, _, st = spec.partition('@')
    c = load(tag, int(st))
    if c is None:
        print("  缺 %s" % spec)
        continue
    N, dx, P = c['N'], c['dx'], c['P']
    for k in sorted(int(v) for v in np.unique(c['fld']) if v > 0):
        m = (c['fld'] == k)
        if int(m.sum()) < 200:
            continue
        g = np.full(N ** 3, 1e3)
        g[c['idx'][m]] = c['val'][m]
        body = g < 0
        nb = int(body.sum())
        if nb < 200:
            continue
        pts = P[body]
        # ① 旧口径：三轴（n*,a,w）跨度
        pr = pts @ c['U'].T
        span = pr.max(0) - pr.min(0)
        r_old = span[1] / max(span[2], 1e-30)      # a / n*（厚）
        # ② PCA 主轴跨度（对倾斜免疫）
        cen = pts - pts.mean(0)
        C = cen.T @ cen / max(len(cen), 1)
        w_, V = np.linalg.eigh(C)
        pr2 = cen @ V
        sp2 = pr2.max(0) - pr2.min(0)
        o = np.argsort(-sp2)
        r_pca = sp2[o[0]] / max(sp2[o[2]], 1e-30)
        # ③ S/V 反解厚度：等体积平板 t = 2V/S（把界面带胞数当面积）
        nif = int((np.abs(g) <= 1.5 * dx).sum())
        S = nif * dx * dx
        Vv = nb * dx ** 3
        t_sv = 2.0 * Vv / max(S, 1e-300)
        # 自洽：PCA 最短跨度 vs S/V 厚度
        ok = '✅' if abs(sp2[o[2]] - t_sv) / max(t_sv, 1e-30) < 0.5 else '⚠差%.0f%%' % (
            100 * abs(sp2[o[2]] - t_sv) / max(t_sv, 1e-30))
        print("  %-7s %-6d %-6d %-30s %-26s %-12s %s"
              % (tag, int(st), k,
                 '%.2f  [%.0f,%.0f,%.0f]nm' % (r_old, span[0]*1e9, span[1]*1e9, span[2]*1e9),
                 '%.2f  (最短 %.0fnm)' % (r_pca, sp2[o[2]]*1e9),
                 '%.0f nm' % (t_sv * 1e9), ok))
print()
print("  ⇒ 判读：若 ①（旧口径）**显著大于** ②③ ⇒ 证实仓库 `R36` 的结论（跨度被碎片与 7.3° 夹角撑大）")
print("     ⇒ 则**我此前的所有『三轴跨度比』读数都偏大**，须以 ②③ 为准。")
