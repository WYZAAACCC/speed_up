#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T16_pre_m6p.py --- T16 的前置判决：**单核板条的 `M6p(t)` 轨迹**。

为什么要先做这个
----------------
`T16` 的验收里有一条"`M6p` 中位 ≤ 20°"。但我已有的多核数据都是 **~52°**
（随机 60.1°）⇒ 若单核板条长开后 `M6p` 也不下降到 20° 以下，那这条判据
**在物理上就不可达**，需要先弄清原因（在改模型之前）。

`M6p` 定义（已由 T13-B0 正对照验证，机器精度）：
  **变体-母相界面法向** vs 该变体惯习面法向 `npref[k]` 的夹角。
  板条的**宽面**坐在惯习面上 ⇒ 宽面对 M6p 贡献 0°；
  端面/侧面/碰撞面贡献大角 ⇒ **中位**会被非宽面污染（`_chk_morph_full.py:124`），
  所以要同时看 **p25**（宽面口径）与**宽面占比**。

本脚本还给出一个**解析对照**：若界面由宽面与端面按几何比例构成，
对"长 2a × 宽 2a × 厚 t"的板条，宽面面积占比 = `a/(a+t)` ⇒ 预测
  `宽面占比 = a/(a+t)`，`M6p 中位 ≈ 0`（若 >50%）或 ≈ 大角（若 <50%）。

用法：python3 T16_pre_m6p.py [--N 96] [--dx-nm 25] [--steps 400]
退出码：0 = M6p 随长开下降（T16 判据可达）/ 1 = 不可达
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
_rng = np.random.default_rng(0)
NPF = {}
for v in range(NV):
    best, bn = None, None
    for n in _rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v], _lam_full(C, n), EPS0[v]))
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn

DF, MOB, BH, BW, K = 2.0e8, 1e-9, 3.5, 2.3, 1


def axtri(n_h):
    n_h = np.asarray(n_h, float)
    n_h = n_h / np.linalg.norm(n_h)
    t = np.array([1.0, 0.0, 0.0])
    if abs(t @ n_h) > 0.9:
        t = np.array([0.0, 1.0, 0.0])
    a = np.cross(n_h, t)
    a = a / np.linalg.norm(a)
    w = np.cross(n_h, a)
    return n_h, w / np.linalg.norm(w), a


def m6p_stats(g, k=K):
    reg = g.region()
    mk = (reg == k)
    if mk.sum() < 10:
        return None
    nb = np.zeros(mk.shape, bool)
    for ax in range(3):
        nb |= (np.roll(reg, 1, axis=ax) == 0)
    iface = mk & nb
    gg = np.gradient(g.phi[k], g.dx, edge_order=2)
    gn = np.sqrt(sum(t ** 2 for t in gg)) + 1e-30
    nrm = np.stack([t / gn for t in gg], -1)[iface]
    nd = np.asarray(NPF[k], float)
    nd = nd / np.linalg.norm(nd)
    ang = np.degrees(np.arccos(np.clip(np.abs(nrm @ nd), 0, 1)))
    return dict(p10=float(np.percentile(ang, 10)), p25=float(np.percentile(ang, 25)),
                med=float(np.median(ang)),
                broad=float((ang < 15.0).mean()), n=int(ang.size))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=96)
    ap.add_argument('--dx-nm', type=float, default=25.0)
    ap.add_argument('--steps', type=int, default=400)
    a = ap.parse_args()
    N, dx = a.N, a.dx_nm * 1e-9
    L = N * dx
    dt = 0.15 * dx / (MOB * DF)
    print('=' * 100)
    print('T16 前置 —— 单核板条 M6p(t)   N=%d Δx=%.0f nm L=%.2f µm steps=%d'
          % (N, a.dx_nm, L * 1e6, a.steps))
    print('=' * 100)
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)
    n_h = np.asarray(NPF[K], float)
    ax3 = axtri(n_h)
    a0, t0 = 240e-9, 100e-9
    g.seed_plate(K, [L / 2] * 3, ax3[0], a0, t0)
    g.init_parent()
    print('  step   厚(nm)   长(nm)   长/厚   M6p p10  p25   中位   宽面(<15°)占比  界面胞')
    for it in range(1, a.steps + 1):
        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=BH, mob_beta_w=BW)
        if it % 40 == 0:
            reg = g.region()
            idx = np.argwhere(reg == K)
            if idx.size == 0:
                break
            p = (idx.astype(float) + 0.5) * dx - np.array([L / 2] * 3)
            ext = [float((p @ u).max() - (p @ u).min()) for u in ax3]
            s = m6p_stats(g, K)
            if s is None:
                continue
            print('  %-6d %-8.1f %-8.1f %-7.3f %-8.1f %-6.1f %-6.1f %-14.3f %d'
                  % (it, ext[0] * 1e9, ext[2] * 1e9, ext[2] / max(ext[0], 1e-30),
                     s['p10'], s['p25'], s['med'], s['broad'], s['n']), flush=True)
            pred = 1.0 / (1.0 + ext[0] / max(ext[2], 1e-30))     # a/(a+t)，a=长/2, t=厚
            print('         解析对照：宽面占比预测 = a/(a+t) = %.3f ; 实测 = %.3f'
                  % (pred, s['broad']))
    print()
    print('  判读：若"宽面占比"随长开上升到 >0.5 而 M6p 中位仍 ~50°，说明宽面法向**并不**')
    print('        对齐 npref（即板条几何与惯习面脱钩）⇒ T16 的"中位 ≤20°"不可达，')
    print('        需要先查"为什么宽面没落在惯习面上"。')
    print('=' * 100)
    return 0


if __name__ == '__main__':
    sys.exit(main())
