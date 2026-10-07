#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_meas.py <root> <tag> <step> —— PCA 长:短 + `f_flat`（口径照抄 `_t11_A8_table.py`）。

## 为什么要新写
`_t11_A8_table.py` / `_t11_fflat2.py` 把实验根目录**写死**为 `_exp/_bk_t5`，
而 `B2P_*` 落在 `_exp/_bk_block`（因为 `_b2_arm.py` 传了 `--out`）。
⇒ 本工具**把 root 作为参数**，其余口径**逐条照抄**：
* 形状比 = **PCA 主轴比**（`R666 §1.1`：三轴跨度比是**已证伪**的口径）；
* `f_flat` = `|n·a| > cos25°` 的比例，界面带 **`|φ| ≤ 0.5·dx`**（`R30 §56`）；场取**胞数最大**者。
"""
import os
import sys

import numpy as np

COS25 = float(np.cos(np.radians(25.0)))
root, tag, step = sys.argv[1], sys.argv[2], int(sys.argv[3])
p = os.path.join(root, "dry_%s" % tag, "snap_%05d.npz" % step)
print("=" * 100)
print("【%s @%d】%s" % (tag, step, p))
print("=" * 100)
if not os.path.exists(p):
    print("  ⛔ 快照不存在")
    raise SystemExit(1)
with np.load(p, allow_pickle=False) as z:
    N = int(np.asarray(z['N']).ravel()[0])
    L = float(np.asarray(z['L']).ravel()[0])
    dx = L / N
    ii = (np.arange(N) + 0.5) * dx
    P = np.stack(np.meshgrid(ii, ii, ii, indexing='ij'), -1).reshape(-1, 3)
    idx = np.asarray(z['band_idx']); val = np.asarray(z['band_val'], float)
    fld = np.asarray(z['band_fld']); reg = np.asarray(z['region']).astype(np.int32)
    a = np.asarray(z['a_ax'], float)
fl = [int(v) for v in np.unique(fld) if v > 0]
print("  N=%d  dx=%.2f nm  场数=%d" % (N, dx * 1e9, len(fl)))
# ★★★ 修（`R697`）：`f_flat` 用**全体界面点合计**（`R30 §56` 的原始口径），
#   不再只算"胞数最大的那个场" —— 后者在最大场只剩 3 万胞时统计量偏少，
#   会**把量具的噪声误判成物理**（`P6`/`P21`）。
_all_nd, _all_if = [], 0
for k in fl:
    m = (fld == k)
    g = np.full(N ** 3, 1e3)
    g[idx[m]] = val[m]
    iface = np.abs(g) <= 0.5 * dx
    ni = int(iface.sum())
    if ni < 50:
        continue
    _all_if += ni
    gr = np.gradient(g.reshape(N, N, N), dx, edge_order=2)
    gn = np.sqrt(sum(x ** 2 for x in gr)) + 1e-300
    _all_nd.append(np.stack([x / gn for x in gr], -1).reshape(N ** 3, 3)[iface])
FF_ALL = (float((np.abs(np.concatenate(_all_nd) @ a) > COS25).mean())
          if _all_nd else float('nan'))
print("  ★ f_flat（**全体界面点合计**，%d 点）= **%.4f**  %s"
      % (_all_if, FF_ALL, "✅ 达标" if FF_ALL >= 0.10 else "❌ 未达标"))
print()
print("  %-5s %-6s %-9s %-12s %s" % ("场", "胞数", "PCA长:短", "f_flat(该场)", "界面点数"))
mx = 0.0
for k in fl:
    m = (fld == k)
    g = np.full(N ** 3, 1e3)
    g[idx[m]] = val[m]
    body = g < 0
    nb = int(body.sum())
    if nb < 200:
        continue
    pts = P[body]
    cen = pts - pts.mean(0)
    w_, V = np.linalg.eigh(cen.T @ cen / max(len(cen), 1))
    pr = cen @ V
    sp = np.sort(pr.max(0) - pr.min(0))[::-1]
    lam = float(sp[0] / max(sp[2], 1e-30))
    mx = max(mx, lam)
    iface = np.abs(g) <= 0.5 * dx
    ni = int(iface.sum())
    if ni >= 100:
        gr = np.gradient(g.reshape(N, N, N), dx, edge_order=2)
        gn = np.sqrt(sum(x ** 2 for x in gr)) + 1e-300
        nd = np.stack([x / gn for x in gr], -1).reshape(N ** 3, 3)[iface]
        ff = float((np.abs(nd @ a) > COS25).mean())
    else:
        ff = float('nan')
    print("  %-5d %-6d %-9.2f %-12s %d" % (k, nb, lam, ("%.4f" % ff) if ff == ff else "—", ni))
print("\n  ⇒ **PCA 最大 = %.2f**" % mx)
print("  ⇒ 口径：PCA 主轴比（`R666 §1.1`）/ `f_flat` = **全体界面点合计**`|n·a|>cos25°`，带 `0.5dx`（`R30 §56`）")
