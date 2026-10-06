#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_thick_probe2.py —— **判别性**探针：`seed_plate` 的 `t` 到底有没有被用？

## 为什么重做（我第一版的错）
  第一版传 `t = 312.5 nm` 与 `t = 250 nm`，**两次都量到 312.5 nm** ⇒
  要么 `t` 被改写、要么我的量法有问题。**两种都不能靠推理**（`AGENTS.md`：推理不算数）。
  ⇒ 改成**判别性**设计：传三个**差异极大**的 `t`（200 / 500 / 800 nm），
    若量到的厚度**跟着变** ⇒ `t` 生效；**不变** ⇒ `t` 被忽略/改写。
  ★ 一个判据若对"极端输入"都没反应，它就没有分辨力（`R581 P43`）。
"""
import sys

import numpy as np

sys.path.insert(0, '.')
import windowB_surface as W          # noqa: E402
from T16_verify_rve import C, EPS0   # noqa: E402

N, DX = 64, 62.5e-9
L = N * DX
R = 320e-9
n_hat = np.array([0.0, 0.0, 1.0])
c = np.array([L / 2, L / 2, L / 2])

g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.25, Mob=1e-9)
ii = (np.arange(N) + 0.0) * DX
Xg, Yg, Zg = np.meshgrid(ii, ii, ii, indexing='ij')
POS = np.stack([Xg.ravel(), Yg.ravel(), Zg.ravel()], 1)
D = (POS - c) @ n_hat                 # 预先算好法向坐标

print("=" * 88)
print(f"{'传入 t (nm)':>12} {'|φ|<=dx/2 壳点数':>18} {'厚度(nm)':>10}   "
      f"{'φ<0 胞数':>10}")
for t_nm in (200.0, 312.5, 500.0, 800.0):
    g.phi[:] = 1.0
    g.seed_plate(1, c, n_hat, R, t_nm * 1e-9, elong=1.0,
                 along=np.array([1.0, 0.0, 0.0]))
    phi = np.asarray(g.phi[1]).ravel()
    m = np.abs(phi) <= DX / 2.0
    nneg = int((phi < 0).sum())
    if m.sum() < 4:
        print(f"{t_nm:>12.1f} {int(m.sum()):>18} {'—':>10}   {nneg:>10}")
        continue
    dd = D[m]
    print(f"{t_nm:>12.1f} {int(m.sum()):>18} {(dd.max()-dd.min())*1e9:>10.1f}   "
          f"{nneg:>10}")
print("=" * 88)
print("★ 判读：")
print("  · 厚度**随 t 单调变化** ⇒ `seed_plate` 的 `t` 生效、约定 = 't 是全厚'")
print("  · 厚度**不随 t 变**   ⇒ `t` 在函数内被改写/忽略 ⇒ 必须找改写点")
