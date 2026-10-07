#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_A8_table.py <step> —— **A8 的单一入口汇总表**（所有维度并入一张表）。

## 为什么需要它
A8 的读数分散在多个工具里（`_t11_thick3.py` 给形状比与三口径、
`_t11_fflat2.py` 给 `f_flat`/`f_tip`、`_t11_touchstep.py` 给撞盒窗口、
`_t11_vtstep.py` 给动力学比）。
⇒ 本工具把它们**按臂×同一 step** 并成一张表，**作为 A8 的持久化交付物**。

## 口径（**逐条声明，不可省**）
* **形状比 = PCA 主轴比**（`R666 §1.1`：三轴跨度比是**已证伪**的口径）；
* **`f_flat` = 全体界面点里 `|n·a| > cos25°` 的比例**（`R30 §56`）；
* **只取撞盒前**（`box_touch=1` 之后形状读数不可用，`R647`）；
* **必须标**：`facet_proj` 的 `N_proj`、`band_cells`、盒长、`mob_wulff`、`mob_dip`。
"""
import csv
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
COS25 = float(np.cos(np.radians(25.0)))
STEP = int(sys.argv[1]) if len(sys.argv) > 1 else 175
ARMS = sys.argv[2:] or ["L0", "W0", "W2", "W4", "G4", "C4", "F6", "F8", "B40"]


def meta(tag):
    import json
    p = os.path.join(ROOT, "dry_%s" % tag, "meta.json")
    d = {}
    if os.path.exists(p):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            d = {}
    return d


def touch(tag):
    p = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                if str(r.get("box_touch", "")).strip() in ("1", "1.0") :
                    return int(r["step"])
            except (KeyError, ValueError):
                continue
    return 0            # 0 = 全程未撞


def shape_pca(tag, st):
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % st)
    if not os.path.exists(p):
        return []
    with np.load(p, allow_pickle=False) as z:
        N = int(np.asarray(z['N']).ravel()[0])
        L = float(np.asarray(z['L']).ravel()[0])
        dx = L / N
        ii = (np.arange(N) + 0.5) * dx
        P = np.stack(np.meshgrid(ii, ii, ii, indexing='ij'), -1).reshape(-1, 3)
        idx = np.asarray(z['band_idx']); val = np.asarray(z['band_val'], float)
        fld = np.asarray(z['band_fld']); reg = np.asarray(z['region']).astype(np.int32)
    out = []
    for k in sorted(int(v) for v in np.unique(fld) if v > 0):
        m = (fld == k)
        if int(m.sum()) < 200:
            continue
        g = np.full(N ** 3, 1e3)
        g[idx[m]] = val[m]
        body = g < 0
        if int(body.sum()) < 200:
            continue
        pts = P[body]
        cen = pts - pts.mean(0)
        w_, V = np.linalg.eigh(cen.T @ cen / max(len(cen), 1))
        pr = cen @ V
        sp = np.sort(pr.max(0) - pr.min(0))[::-1]
        out.append((k, int((reg == k).sum()), float(sp[0] / max(sp[2], 1e-30))))
    return out


def fflat(tag, st):
    """★ 口径必须与 `_t11_fflat2.py` 一致（否则两张表不可比）。

    ## ⛔ 本函数第一版的 bug（`R688` 记账）
    写成 `best = max(fl, key=lambda k: int((fld == best).sum()))`（数**带内点数**）
    ⇒ 得到的场**不一定是胞数最大的那个**（`R647` 的口径）；
    且界面带用了 `1.5dx` 而仓库 `R30 §56` 用的是 **`0.5dx`**。
    ⇒ 两者叠加使 `f_flat` **虚高约 33%**（`G4`：0.1511 vs 正确的 0.113）。
    **修法**：① 按 `region` 的胞数取最大场；② 界面带用 `0.5·dx`。
    """
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % st)
    if not os.path.exists(p):
        return None
    with np.load(p, allow_pickle=False) as z:
        N = int(np.asarray(z['N']).ravel()[0])
        L = float(np.asarray(z['L']).ravel()[0])
        dx = L / N
        idx = np.asarray(z['band_idx']); val = np.asarray(z['band_val'], float)
        fld = np.asarray(z['band_fld']); reg = np.asarray(z['region']).astype(np.int32)
        a = np.asarray(z['a_ax'], float)
    fl = [int(v) for v in np.unique(fld) if v > 0]
    if not fl:
        return None
    best = max(fl, key=lambda k: int((reg == k).sum()))      # ★ 按胞数（R647 口径）
    m = (fld == best)
    g = np.full(N ** 3, 1e3)
    g[idx[m]] = val[m]
    iface = np.abs(g) <= 0.5 * dx                            # ★ 0.5dx（R30 §56 口径）
    if int(iface.sum()) < 100:
        return None
    gr = np.gradient(g.reshape(N, N, N), dx, edge_order=2)
    gn = np.sqrt(sum(x ** 2 for x in gr)) + 1e-300
    nd = np.stack([x / gn for x in gr], -1).reshape(N ** 3, 3)[iface]
    na = np.abs(nd @ a)
    return float((na > COS25).mean())


print("=" * 126)
print("★ A8 单一入口汇总表 —— step = %d（口径：PCA 主轴比 / `R30 §56` 的 `f_flat` / 只取撞盒前）"
      % STEP)
print("=" * 126)
print("  %-6s %-4s %-9s %-6s %-7s %-6s %-24s %-10s %s"
      % ('臂', 'wulff', 'fproj', 'band', 'dip', '盒长', 'PCA 长:短（逐场）',
         '最大', 'f_flat'))
rows = []
for t in ARMS:
    M = meta(t)
    N = M.get('N'); L = M.get('L')
    box = ('%.0f µm' % (L * 1e6)) if L else '?'
    sp = shape_pca(t, STEP)
    ff = fflat(t, STEP)
    tc = touch(t)
    valid = (tc == 0) or (tc is not None and STEP < tc)
    mx = max((x[2] for x in sp), default=float('nan'))
    rows.append((t, M.get('mob_wulff'), M.get('facet_proj'), M.get('band_cells'),
                 M.get('mob_dip'), box, sp, mx, ff, tc))
    s = ' '.join('%.2f' % x[2] for x in sp) if sp else '(无)'
    print("  %-6s %-4s %-9s %-6s %-7s %-6s %-24s %-10s %s%s"
          % (t, M.get('mob_wulff'), M.get('facet_proj'), M.get('band_cells'),
             M.get('mob_dip'), box, s[:24],
             ('%.2f' % mx) if mx == mx else '—',
             ('%.4f' % ff) if ff is not None else '—（点数不足）',
             '' if valid else '  ⛔撞盒@%s' % tc))
print()
print("  ⇒ 判读：")
print("     · `f_flat ≥ 0.10` 达标（`BLOCK_SELFAC §9.5`）的臂用 ✅ 标在读数后")
print("     · `⛔撞盒` 的臂**该 step 读数不可用**（`R647`）")
