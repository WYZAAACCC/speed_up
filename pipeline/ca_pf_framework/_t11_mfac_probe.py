#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_mfac_probe.py —— **直接观测** `Mfac`：只调一次 `advance`，把 `Mfac` 场抓出来。

## 为什么
`F-flat` 三个取向给出**同一个** `Mfac`（0.00154 = `e^{−β_h}`）⇒ 高度怀疑 `nd_ref_` 恒为 `(0,0,1)`。
不能靠推理 —— **直接在 `advance` 前把 `v_cell` 的调制因子截获**。

## 做法（不改主代码）
用 `unittest.mock` 给 `np.exp` 打桩？不行（太侵入）。
改为**读引擎自己写的量**：`advance` 在结束时会把 `Mfac` 的累积量算进 `self.dG_max`；
更直接的是**用两个不同 `n*` 跑同一个界面，比较界面速度**——但这正是 F-flat 已做的。

⇒ 因此本探针改为**检查 `nd_ref_` 的来源**：打印
  · `nreg`（场数）
  · 写进 `np_arr` 的键与向量
  · `karr` 在界面上的取值
从而判断"我给的 `n*` 有没有进到 `np_arr[ki]` 那一行"。
"""
import sys

import numpy as np

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
import windowB_surface as W  # noqa: E402

N, dx = 32, 2e-9
z_ = np.array([0., 0., 1.])
x_ = np.array([1., 0., 0.])

for tag, gh in (('n*=z', z_), ('n*=x', x_)):
    g = W.LevelSetMulti(N, N * dx, nv=1, gamma=0.0, Mob=1e-9,
                        df=[0.0, -1e7], reinit_every=0)
    z = (np.arange(N)[None, None, :] + 0.5) * dx
    a = (N // 2) * dx
    L = N * dx
    g.phi[1] = np.where(z <= a, -np.minimum(z, a - z),
                        np.minimum(z - a, L - z)) * np.ones((N, N, N))
    g.near0 = a
    g.init_parent()
    g.npref = {1: gh}
    g.wtab = np.full((2, 3), np.nan)
    g.wtab[1] = np.array([0., 1., 0.])
    g.advance(0.1 * dx / (1e-9 * 1e7), extend='edt', band_cells=20,
              mob_beta=6.477, mob_beta_w=0.0, mob_iform='exp2',
              npref=g.npref, pin_min=True)
    r = g.region()
    print("  [%s] nreg=%d  场号集合=%s  npref=%s"
          % (tag, getattr(g, 'nreg', -1), sorted(np.unique(r).tolist()),
             {k: np.round(v, 3).tolist() for k, v in (g.npref or {}).items()}))
    print("       dG_max=%.4g   (若两档不同 ⇒ Mfac 确实变了)"
          % float(getattr(g, 'dG_max', float('nan'))))
