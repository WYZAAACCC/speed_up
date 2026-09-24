#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PF 判据（2026-09-25 新增）：**按场推进**（`advance(per_field=True)`，方案 (a)）。
   PF-1 平界面速度标定（周期 slab + 亚胞射线交点）：|v|/MΔf 应 1.000（判据 <0.02）
   PF-2 多界面**场健康度**：每个 φ_k 在**它自己**的界面带内 |∇φ_k| 中位应保持 ~1
        （这正是"被推进的场集合在空间上跳变 ⇒ φ 出现跳变并被 |∇φ| 自放大"的直接观测量）
   ★ 记账（2026-09-25 补）：本文件原来的 PF-3（M2 A/B，**固定 dt**）**已作废**：
     那个对比里 per_field 的爆掉与"带胞塌缩"**都是 dt 超 CFL 的假象**（当时 dt 只按 Δf 定，
     而弹性项比 Δf 大 ~5 倍 ⇒ 实际每步位移 0.6–0.75dx）。M2 的 A/B 请看 `_chk_m2c.py`
     （自适应 dt，三个配置全部健康）。
用法：_chk_pf.py <N> <nstep>    （只跑 PF-1/PF-2）
"""
import sys
import numpy as np
import windowB_surface as W
from windowB_pf3d import C_iso3, _lam_full
from windowB_ti64_variants import variants


def field_health(g, band=1.5):
    """每场在其**自己**界面带内的 |∇φ_k| 中位；返回 (最大, 中位, 最差场号)"""
    karr = np.argsort(g.phi, axis=0)[0]
    larr = np.argsort(g.phi, axis=0)[1]
    meds = []
    for k in range(g.nreg):
        lk = np.where(karr == k, larr, karr)
        d = g.phi[k] - np.take_along_axis(g.phi, lk[None], 0)[0]
        gd = np.gradient(d, g.dx)
        gdn = np.sqrt(sum(x ** 2 for x in gd))
        m = np.abs(d) <= band * g.dx * np.maximum(gdn, 1e-30)
        gk = np.sqrt(sum(x ** 2 for x in np.gradient(g.phi[k], g.dx)))
        meds.append(float(np.median(gk[m])) if m.any() else np.nan)
    meds = np.array(meds)
    return float(np.nanmax(meds)), float(np.nanmedian(meds)), int(np.nanargmax(meds))


def build_m2(N, t_dx=6.0, aniso=0.4):
    C = C_iso3(113e9, 0.34)
    eps0, Fs, meta = variants()
    nv = len(eps0)
    g = W.LevelSetMulti(N, N * 1e-8, C=C, eps0=eps0, gamma=0.15, Mob=1e-9,
                        df=[0.0] + [-1e8] * nv, workers=6, reinit_every=25)
    npref = {}
    rng = np.random.default_rng(0)
    for v in range(nv):
        best = None
        bn = None
        for n in rng.normal(size=(400, 3)):
            n = n / np.linalg.norm(n)
            val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n),
                                        eps0[v]))
            if best is None or val < best:
                best, bn = val, n
        npref[v + 1] = bn
    R = 0.22 * N * 1e-8
    for v in range(nv):
        g.seed_plate(v + 1, (rng.random(3) * (N * 1e-8 - 2 * R) + R), npref[v + 1],
                     R, t_dx * 1e-8)
    g.init_parent()
    return g, npref


def m2_ab(N=32, nstep=25, aniso=0.4, cfl=0.15):
    print('---- PF-3 M2 多界面 A/B（aniso=%.2f, cfl=%.2f, N=%d）----' % (aniso, cfl, N))
    print('   %-10s %5s %7s %10s %12s %12s' %
          ('per_field', 'step', '带胞', '|g|中位', '场|g|中位max', '场|g|中位中位'))
    for pf in (False, True):
        g, npref = build_m2(N, aniso=aniso)
        dt = cfl * 1e-8 / (1e-9 * 1e8)
        for s in range(nstep + 1):
            if s % 5 == 0 or s == nstep:
                karr = np.argsort(g.phi, axis=0)[0]
                phiw = np.take_along_axis(g.phi, karr[None], 0)[0]
                gn = np.sqrt(sum(x ** 2 for x in np.gradient(phiw, g.dx)))
                A = g.cell_area_geom()
                m = A > 0
                fm, fmed, fk = field_health(g)
                print('   %-10s %5d %7d %10.3f %12.3f %12.3f  (最差场 %d)' %
                      (str(pf), s, int(m.sum()),
                       float(np.median(gn[m])) if m.any() else np.nan, fm, fmed, fk))
            if s == nstep:
                break
            g.advance(dt, aniso=aniso, npref=npref, per_field=pf, iface_band=2.0)


if __name__ == '__main__':
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 32
    nstep = int(sys.argv[2]) if len(sys.argv) > 2 else 25
    print('---- PF-1 平界面速度（周期 slab + 亚胞射线交点）----')
    for pf in (False, True):
        r, c = W and __import__('_chk_w2').run(per_field=pf)
        print('   per_field=%-5s : 射线 v/MDf = %.4f | 计数 = %.4f   %s'
              % (str(pf), r, c, 'PASS' if abs(r - 1) < 0.02 else 'FAIL'))
    print('   判据：|v/MDf - 1| < 0.02')
    print('---- PF-2 平界面 + 0.4dx 平移（分辨力）----')
    for pf in (False, True):
        r4, c4 = __import__('_chk_w2').run(nstep=4, per_field=pf)
        print('   per_field=%-5s : 射线 %.4f | 计数 %.4f' % (str(pf), r4, c4))
    print('（M2 A/B 已移到 _chk_m2c.py —— 见文件头记账）')
