#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_m6.py --- 审计判据本身：**M6（界面法向 vs 配对相容法向）有没有分辨力？**

M6 的口径（_chk_morph.py / _chk_m6_route.py / _chk_morph_full.py 三处同源）：
    chi = gaussian_filter(reg==k0, 1.5) ; 界面法向 n = grad chi / |grad chi| ;
    带 = 0.2<chi<0.8 ; 与 ncmp[k,l] 取夹角 ; **中位数**。
这里做**正对照**：人为构造一个**严格落在相容法向平面上的平面界面**，
若 M6 判据有分辨力，它必须给 ≈0 deg；否则说明判据本身没有分辨力。
"""
import os, sys
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy import ndimage as ndi
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants()
nv = len(eps0)
N, dx = 64, 1e-8
L = N * dx
x = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
xyz = np.stack([X, Y, Z], -1)

# 配对相容法向表（与类内 _pair_normals 同算法）
rng = np.random.default_rng(0)
ns = rng.normal(size=(600, 3)); ns /= np.linalg.norm(ns, axis=1)[:, None]
Lam = np.array([_lam_full(C, n) for n in ns])
E = [np.asarray(e, float) for e in eps0]
best = None
for k in range(1, nv + 1):
    for l in range(k + 1, nv + 1):
        de = E[k - 1] - E[l - 1]
        val = 0.5 * np.einsum('ij,sijkl,kl->s', de, Lam, de)
        i = int(np.argmin(val))
        if best is None or val[i] < best[0]:
            best = (val[i], ns[i], k, l)
_, ncl, kk, ll = best
print('取最相容的一对 V%d-V%d，ncmp = %s' % (kk, ll, np.array2string(ncl, precision=4)))


def m6(reg, ncl, tag):
    chi = ndi.gaussian_filter((reg == kk).astype(float), 1.5)
    gr = np.array(np.gradient(chi, dx))
    bnd = (chi > 0.2) & (chi < 0.8)
    nn = np.moveaxis(gr, 0, -1)[bnd]
    nrm = np.linalg.norm(nn, axis=1)
    nn = nn[nrm > 1e-30] / nrm[nrm > 1e-30][:, None]
    c = np.abs(nn @ ncl)
    a = np.degrees(np.arccos(np.clip(c, 0, 1)))
    print('   %-28s 带胞 %7d  M6 中位 %5.1f deg   p25 %5.1f   P(<20deg) %.3f'
          % (tag, nn.shape[0], np.median(a), np.percentile(a, 25), (a < 20).mean()))


def plane(u, tag):
    p = xyz @ u
    reg = np.where(p < 0.5 * (p.min() + p.max()), kk, ll)
    m6(reg, ncl, tag)


# 正对照 A：界面严格落在 ncmp 平面上（法向 = ncmp）
plane(ncl, '正对照: 界面法向 == ncmp')
# 正对照 B：偏离 10 / 30 / 60 度
t1 = np.cross(ncl, [0.0, 0.0, 1.0]); t1 /= np.linalg.norm(t1)
for th in (10, 30, 60, 90):
    u = np.cos(np.radians(th)) * ncl + np.sin(np.radians(th)) * t1
    plane(u, '偏离 ncmp %2d deg' % th)
# 负对照：随机方向平面界面
for s in range(3):
    u = rng.normal(size=3); u /= np.linalg.norm(u)
    plane(u, '随机方向 %d' % (s + 1))

# 附加对照：球（完全各向同性）
r = np.linalg.norm(xyz - 0.5 * L, axis=-1)
reg = np.where(r < 0.2 * L, kk, ll)
m6(reg, ncl, '球（各向同性）')
