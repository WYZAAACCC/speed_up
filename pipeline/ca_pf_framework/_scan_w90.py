#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3/S4 敏感度扫描: 界面宽 w90 与驱动比 dg_ratio 对"纯度/变体分配"的影响
输出: bench/windowB_rve3d/SCAN_w90_dg.txt
判读: "pure" = max_v phi_v > 0.9 的已转变胞占比。物理正确的弥散界面应 -> 1。
"""
import os
import numpy as np
from windowB_pf3d import PF3D, C_iso3
from windowB_ti64_variants import variants
from windowB_rve3d import seed_variants, calibrate_L

OUT = '/mnt/f/speed_up/bench/windowB_rve3d'
N, dx, nstep = 64, 1e-9, 250
C = C_iso3(113e9, 0.34)
eps0, Fs, meta = variants()
lines = []
for w_over in (2.0, 4.0, 8.0):
    for dgr in (0.02, 0.05, 0.20):
        L = N * dx
        w90 = w_over * dx
        W = 13.183297 * 0.15 / w90
        dG = dgr * W
        pf = PF3D(N, L, C, eps0, gamma=0.15, w90=w90, Lmob=1.0, dG=dG, workers=4)
        Lmob, v1 = calibrate_L(pf, dG, 50.0)
        pf.Lmob = Lmob
        dt = 0.4 * dx / 50.0
        seed_variants(pf, vol_frac=0.12, rng=7)
        for _ in range(nstep):
            pf.step(dt)
        s = pf.phi.sum(0)
        mx = pf.phi.max(0)
        tr = s > 0.5
        pure = (mx > 0.9) & tr
        frac = pf.phi.reshape(pf.nv, -1).mean(1)
        rec = ('w90/dx=%.0f  dg_ratio=%.2f  W=%.3e dG=%.3e | 转变分数=%.4f  纯胞占比=%.4f  '
               '变体分数 max/min=%.2f  最大phi=%.3f'
               % (w_over, dgr, W, dG, tr.mean(), pure.sum() / max(tr.sum(), 1),
                  frac.max() / max(frac.min(), 1e-12), mx.max()))
        print(rec, flush=True)
        lines.append(rec)
np.savetxt(os.path.join(OUT, 'SCAN_w90_dg.txt'), np.array(lines), fmt='%s')
