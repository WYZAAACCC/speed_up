#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_v1b_lead.py <idx> --- 修正后的"淘汰"指标：逐晶粒的【前沿推进量 lead(vs t)】+ 体积
WC 淘汰的严格定义：错取向晶粒的 lead 停滞（被邻晶超越），而不是"是否接触液相"。'''
import os, sys, json, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ca3d as C3
from ca3d import CA3D, IRF
import verify_ca3d_wc_cet as W

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_v1_out')
DX, N, DTU, NST = 4e-6, 110, 16.0, 300
IRED = IRF()
n = W.nhat_tilt(35.0)
X, Y, Z = None, None, None


def main(idx):
    t0 = time.time()
    V = float(IRED(DTU)); dt = DX / (4 * V)
    ca = CA3D(N, N, N, DX, irf=IRED, seed=4000 + idx, periodic=(False, True, False),
              capture='envelope')
    rng = np.random.default_rng(4001 + idx)
    quats = [C3.rand_quat(rng) for _ in range(9)]
    gids = [int(g) for g in W.place_seeds_on_perp_plane(ca, n, 3, 3, 25, quats=quats)]
    als = {}
    for g in gids:
        P = ca.axes[g]
        als[g] = round(max(abs(float(P[:, a] @ n)) for a in range(3)), 4)
    Xc, Yc, Zc = ca.coords()
    sp = Xc * n[0] + Yc * n[1] + Zc * n[2]
    hist = []
    for s in range(NST):
        ca.t = s * dt
        ca.step(dt, ca.T_iso(DTU), window='full')
        if (s + 1) % 30 == 0:
            solid = ca.gid > 0
            liq = ~solid
            nb = np.zeros_like(solid)
            for o, _ in C3.OFFSETS:
                pr = ca._pair(o, (0, N, 0, N, 0, N))
                if pr is None:
                    continue
                sx, tx = pr
                nb[tx] |= liq[sx]
            front = solid & nb
            lead = float(sp[front].max()) if front.any() else float(sp[solid].max())
            rec = []
            for g in gids:
                m = (ca.gid == g)
                cel = int(m.sum())
                ld = float(sp[m].max()) if cel else float('nan')
                act = bool((front & m).any())
                rec.append([g, als[g], cel, round(ld * 1e6, 2), int(act)])
            hist.append([s + 1, round(lead * 1e6, 2), rec])
    # 淘汰判定: 末态 lead 落在"全体最大 lead"以下 > 2 胞 视为被超越
    last = hist[-1]
    leads = {r[0]: r[3] for r in last[2]}
    t = time.time() - t0
    out = dict(task='t6b_lead', idx=idx, align=als, hist=hist, lead_last=leads, wall_s=round(t, 1))
    with open(os.path.join(OUT, 't6b_lead__%d.json' % idx), 'w') as f:
        json.dump(out, f, ensure_ascii=False)
    print('t6b_lead #%d %5.1fs' % (idx, t), flush=True)


if __name__ == '__main__':
    main(int(sys.argv[1]))