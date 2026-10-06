#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_probe_state.py —— 打印平界面算例的**真实状态**（region / phi / 截获的 gd_）。

## 为什么
`_t11_probe_ndir.py` 的第一档给出 `dfield ∈ [-1, 1]` —— 那是**场编号差**而非两个 φ 之差
⇒ 说明 `karr/larr` 与我的假设不同。**不再假设，直接看数**。
"""
import sys

import numpy as np

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
import windowB_surface as W  # noqa: E402

CAP = {}
_orig = np.stack


def spy(arrays, *a, **k):
    try:
        lst = list(arrays)
        if len(lst) == 3 and all(getattr(x, 'ndim', 0) == 3 for x in lst):
            CAP['gd'] = [np.array(x, copy=True) for x in lst]
    except TypeError:
        pass
    return _orig(arrays, *a, **k)


N, dx, M, df = 32, 2e-9, 1e-9, 1e7
z_ = np.array([0., 0., 1.])

for tag, axis in (('∇φ∥x', 0), ('∇φ∥z', 2)):
    np.stack = _orig
    g = W.LevelSetMulti(N, N * dx, nv=1, gamma=0.0, Mob=M, df=[0.0, -df],
                        reinit_every=0)
    r = (np.arange(N)[None, None, :] + 0.5) * dx
    a, L = (N // 2) * dx, N * dx
    prof = np.where(r <= a, -np.minimum(r, a - r), np.minimum(r - a, L - r))
    sh = [1, 1, 1]; sh[axis] = N
    g.phi[1] = prof.reshape(sh) * np.ones((N, N, N))
    g.near0 = a
    g.init_parent()
    g.npref = {1: z_}
    g.wtab = np.full((2, 3), np.nan); g.wtab[1] = np.array([0., 1., 0.])
    reg = g.region()
    print("=" * 92)
    print("【%s】advance 前：region 取值 = %s" % (tag, sorted(np.unique(reg).tolist())))
    print("   φ[0] 范围 [%.3g, %.3g]  φ[1] 范围 [%.3g, %.3g]"
          % (g.phi[0].min(), g.phi[0].max(), g.phi[1].min(), g.phi[1].max()))
    CAP.clear()
    np.stack = spy
    try:
        g.advance(0.1 * dx / (M * df), extend='edt', band_cells=20,
                  mob_beta=6.477, mob_iform='exp2', npref=g.npref, pin_min=True)
    finally:
        np.stack = _orig
    if 'gd' not in CAP:
        print("   ⚠ 未截获")
        continue
    gd = CAP['gd']
    gdn = np.sqrt(sum(x ** 2 for x in gd))
    dfi = gd[0] - gd[1]          # 我原以为的 dfield（实为 φ0−φ1）
    print("   截获 gd_：各分量范围 x[%.3g,%.3g] y[%.3g,%.3g] z[%.3g,%.3g]"
          % (gd[0].min(), gd[0].max(), gd[1].min(), gd[1].max(),
             gd[2].min(), gd[2].max()))
    print("   |∇| 分位 p50=%.4g p90=%.4g max=%.4g；`φ0−φ1` 范围 [%.3g, %.3g]"
          % (np.percentile(gdn, 50), np.percentile(gdn, 90), gdn.max(),
             dfi.min(), dfi.max()))
    # 正确的界面判据：|∇| 足够大（界面处 |∇(φ0−φ1)| ≈ 2/dx 量级）
    thr = 0.2 * gdn.max()
    iface = gdn >= thr
    print("   界面判据 |∇| ≥ 0.2·max ⇒ 界面胞 **%d**" % int(iface.sum()))
    if iface.any():
        nd = np.stack([x / (gdn + 1e-30) for x in gd], -1)
        nd = nd / (np.linalg.norm(nd, axis=-1, keepdims=True) + 1e-300)
        c2 = np.clip(nd @ z_, -1, 1) ** 2
        v = c2[iface]
        print("   界面上 (n·n*)² 分位 p10=%.3f p50=%.3f p90=%.3f"
              % tuple(np.percentile(v, [10, 50, 90])))
        print("   ⇒ 满足 >0.81 的界面胞 = %d / %d（%.1f%%）"
              % (int((v > 0.81).sum()), v.size, 100.0 * (v > 0.81).mean()))
