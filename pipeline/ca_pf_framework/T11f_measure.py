#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T11f_measure.py --- 判"偏的是**测量**还是**推进**"（D11 剩余嫌疑 ③，最便宜的一条）。

方法
----
同一批运行，**同一份 φ 场**，用三种互相独立的口径量前沿位移：

  A **子胞零交点**（`iface_offset`：沿主轴插值求 φ 的零点）—— 前几轮一直在用
  B **带质心**（界面带胞沿 n 的均值坐标）
  D **残差常值**（★ 真值对照，零插值）：
       精确解是纯平移 `φ_exact(x) = n·(x−x0) − v·t`
       平移 Δ 后 `resid = φ_1 − φ_exact ≈ −Δ`（带内常数）
       ⇒ `Δ = −median(resid)`，`v = Δ/t`
    它直接读 SDF 本身，**不经过任何零点插值/几何假设**。

判决
----
  * 若 **D ≈ 1.000** 而 A 明显偏离 ⇒ **偏的是测量**（A 的口径在阶梯上有偏），
    前面 T11/T11b/c/e 的"赤字"结论**作废**，需要改用 D 重测；
  * 若 **D 与 A 一致地偏离** ⇒ 偏的是**推进**，剩余嫌疑 ①② 继续成立。

用法：python3 T11f_measure.py [--L-nm 3000] [--dxs 40,50,62.5]
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

DF, MOB = 2.0e8, 1e-9
EXACT = MOB * DF


def run(L, N, dx, n_h, nstep=80, band=20):
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.0, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=1, reinit_every=0)
    g.pf = None
    n_h = np.asarray(n_h, float)
    n_h = n_h / np.linalg.norm(n_h)
    ax = int(np.argmax(np.abs(n_h)))
    c0 = np.array([L / 2] * 3)
    rel = g.XYZ - c0
    d0 = rel @ n_h
    g.phi[1] = d0
    for j in range(1, g.nreg):
        if j != 1:
            g.phi[j] = 1e3
    g.init_parent()
    dt = 0.15 * dx / EXACT
    nA0, cA0 = g.iface_offset(k=1, l=0, axis=ax)
    t = 0.0
    for _ in range(nstep):
        g.advance(dt, band_cells=band)
        t += dt
    # --- A：子胞零交点 ---
    nA1, cA1 = g.iface_offset(k=1, l=0, axis=ax)
    if nA0 == 0 or nA1 == 0:
        return None
    vA = (abs(cA1 - cA0) / t) * abs(n_h[ax])
    # --- B：带质心（沿 n） ---
    band_m = np.abs(g.phi[1]) <= 2.0 * dx
    posB = float((rel[band_m] @ n_h).mean())
    # --- D：残差常值（零插值真值） ---
    phi_ex = d0 - EXACT * t
    band_d = np.abs(phi_ex) <= 3.0 * dx
    resid = g.phi[1][band_d] - phi_ex[band_d]
    dD = -float(np.median(resid))
    vD = dD / (EXACT * t)          # ★ **相对位移误差**（≈0 = 推进精确），不是速度比
    return vA / EXACT, vD, posB, float(np.median(np.abs(resid - np.median(resid))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--L-nm', type=float, default=3000.0)
    ap.add_argument('--dxs', type=str, default='40,50,62.5')
    a = ap.parse_args()
    L = a.L_nm * 1e-9
    dxs = [float(x) * 1e-9 for x in a.dxs.split(',')]
    Ns = [int(round(L / dx)) for dx in dxs]
    tilt = np.asarray(NPF[1], float)
    tilt = tilt / np.linalg.norm(tilt)
    print('=' * 100)
    print('T11f —— 偏的是**测量**还是**推进**？   L=%.0f nm  Δx=%s nm ⇒ N=%s'
          % (a.L_nm, a.dxs, Ns))
    print('  A=子胞零交点（前几轮用）; D=残差常值（零插值真值）; 两者都除以 M·Δf')
    print('=' * 100)
    print('%-16s %-8s %-10s %-10s %-10s %-12s' %
          ('算例', 'Δx(nm)', 'A', 'D', 'A/D', '残差散布'))
    out = {}
    for lab, n_h in (('轴对齐 ẑ', np.array([0.0, 0, 1.0])), ('倾斜 npref[1]', tilt)):
        for N, dx in zip(Ns, dxs):
            r = run(L, N, dx, n_h)
            if r is None:
                print('%-16s %-8.1f 界面未找到' % (lab, dx * 1e9))
                continue
            vA, vD, posB, rs = r
            out.setdefault(lab, []).append((dx, vA, vD))
            print('%-16s %-8.1f %-10.4f %-10.4f %-10.3f %-12.3e'
                  % (lab, dx * 1e9, vA, vD, vA / max(vD, 1e-30), rs), flush=True)
        print()
    print('  判决（★ 记账：D 量的是**位移误差**，不是位移 —— 首版把语义写反了）：')
    print('    D 的残差 ≈ 0 表示"推进精确"；把它除以 MΔf·t 得到的才是**相对误差**。')
    for lab, rows in out.items():
        vA = np.array([r[1] for r in rows])
        errD = np.array([r[2] for r in rows])
        spA = float((vA.max() - vA.min()) / abs(vA.mean()))
        spE = float((errD.max() - errD.min()) / max(abs(errD.mean()), 1e-30))
        print('    %-14s A: 均值 %.4f 散布 %.4f | D 相对误差: 均值 %.4f%% 散布 %.4f'
              % (lab, vA.mean(), spA, 100 * errD.mean(), spE))
    tl = out.get('倾斜 npref[1]')
    ax_ = out.get('轴对齐 ẑ')
    if tl and ax_:
        eD_tilt = np.mean([r[2] for r in tl])
        eD_ax = np.mean([r[2] for r in ax_])
        vA_tilt = np.mean([r[1] for r in tl])
        if abs(eD_tilt) < 0.02 and abs(vA_tilt - 1.0) > 0.1:
            print('  ⇒ **偏的是测量（口径 A）**：零插值真值说倾斜档推进误差仅 %.3f%%，'
                  % (100 * eD_tilt))
            print('     而子胞零交点口径 A 报出 %.1f%% 的赤字 ⇒ **A 对倾斜前沿有偏**。'
                  % (100 * (1 - vA_tilt)))
            print('     ⇒ T11/T11b/c/e 的"赤字"结论**作废**，必须用 D 重测。')
        elif abs(eD_tilt) > 0.05:
            print('  ⇒ **偏的是推进**：D 也显示 %.1f%% 的误差 ⇒ 剩余嫌疑 ①② 成立。'
                  % (100 * eD_tilt))
        else:
            print('  ⇒ 两口径都不显示误差；需人工看残差结构。')
    print('=' * 100)
    return 0


if __name__ == '__main__':
    sys.exit(main())
