#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_sdftest.py --- ★ 直接单测 `seed_plate` 的 `sdf` 连通性（**逐字复刻源码公式**）。

## 公式来源（`windowB_surface.py:2866-2895`，**照抄，不自造**）
```python
_nc = getattr(self, '_nuc', None) or {}
if bool(_nc.get('periodic_seed', False)):
    rel = rel - self.L * np.round(rel / self.L)
d = rel @ n
u = rel - d[..., None] * n
rperp = np.linalg.norm(u, axis=-1)
if elong > 1.0 and along is not None:
    al = normalize(along)
    e_par = u @ al
    e_per = np.linalg.norm(u - e_par[..., None] * al, axis=-1)
    rperp = np.sqrt((e_par / elong) ** 2 + e_per ** 2)
...
if <along 分支>:
    sdf = np.maximum(np.maximum(np.abs(d) - t / 2, np.abs(e_par) - elong * R), e_per - R)
    return
sdf = np.maximum(np.abs(d) - t / 2, rperp - R)          # disc
if shape == 'ellipsoid':
    _r = np.sqrt((d / max(t / 2, 1e-30)) ** 2 + (rperp / max(R, 1e-30)) ** 2)
    sdf = (_r - 1.0) * min(t / 2, R)
```
⚠ 注意：`along` 分支用的是 **`e_par` / `e_per` 原值**，而 `rperp` 被**椭圆化**过 —— 两条分支的口径不同。

## 参数（**用算例实际值**）
`dx = 62.5 nm`、`N = 160`（10 µm 盒）、`t = 312.5 nm`（核厚 = 250 + 咬入 62.5）、
`R = 320 nm`（`--eng-r-nm`）、`elong = 7.0` ⇒ 长半轴 `elong*R = 2240 nm`

## 判据
对多个随机 `center`/`normal`/`along`，数 `sdf < 0` 的 26-连通分量数：
**若出现 ≥2 ⇒ sdf 不连通 ⇒ 病灶在 sdf；若恒为 1 ⇒ 病灶在别处。**
"""
import sys

import numpy as np
from scipy import ndimage

S26 = ndimage.generate_binary_structure(3, 3)
DX = 62.5e-9
N = 160
L = N * DX
T = 312.5e-9
R = 320e-9
ELONG = 7.0
CASES = int(sys.argv[1]) if len(sys.argv) > 1 else 40


def sdf_along(center, normal, along):
    x = (np.arange(N) + 0.5) * DX
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    rel = np.stack([X - center[0], Y - center[1], Z - center[2]], -1)
    n = np.asarray(normal, float); n /= np.linalg.norm(n)
    al = np.asarray(along, float);  al /= np.linalg.norm(al)
    d = rel @ n
    u = rel - d[..., None] * n
    e_par = u @ al
    e_per = np.linalg.norm(u - e_par[..., None] * al, axis=-1)
    return np.maximum(np.maximum(np.abs(d) - T / 2, np.abs(e_par) - ELONG * R),
                      e_per - R)


def sdf_ellipsoid(center, normal, along):
    x = (np.arange(N) + 0.5) * DX
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    rel = np.stack([X - center[0], Y - center[1], Z - center[2]], -1)
    n = np.asarray(normal, float); n /= np.linalg.norm(n)
    al = np.asarray(along, float);  al /= np.linalg.norm(al)
    d = rel @ n
    u = rel - d[..., None] * n
    e_par = u @ al
    e_per = np.linalg.norm(u - e_par[..., None] * al, axis=-1)
    rperp = np.sqrt((e_par / ELONG) ** 2 + e_per ** 2)
    _r = np.sqrt((d / max(T / 2, 1e-30)) ** 2 + (rperp / max(R, 1e-30)) ** 2)
    return (_r - 1.0) * min(T / 2, R)


rng = np.random.default_rng(0)
for name, fn in (("along(矩形盒)", sdf_along), ("ellipsoid(椭球)", sdf_ellipsoid)):
    multis = 0
    sizes = []
    for i in range(CASES):
        c = np.array([rng.uniform(0.25, 0.75) * L for _ in range(3)])
        nv = rng.normal(size=3)
        av = rng.normal(size=3)
        s = fn(c, nv, av)
        m = np.moveaxis(s, 0, 0) < 0
        lab, nc = ndimage.label(m, structure=S26)
        sizes.append(int(m.sum()))
        if nc > 1:
            multis += 1
            if multis <= 3:
                sz = np.bincount(lab.ravel())[1:]
                print("    ⚠ 例 %d：nc=%d 分量胞数=%s  中心=(%.0f,%.0f,%.0f)nm"
                      % (i, nc, sorted(sz, reverse=True)[:5], c[0] * 1e9, c[1] * 1e9, c[2] * 1e9))
    print("  %-16s 多连通例数 = %d / %d ；sdf<0 胞数 min/中位/max = %d/%d/%d"
          % (name, multis, CASES, min(sizes), int(np.median(sizes)), max(sizes)))
print()
print("  ⇒ 若某分支出现多连通例 ⇒ **该分支的 sdf 不连通，就是「一场多块」的病灶**")
