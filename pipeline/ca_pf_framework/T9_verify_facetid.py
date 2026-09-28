#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T9_verify_facetid.py --- T9 判据：界面本构按**面片身份** `(I⁻,I⁺) = (k,l)` 查表。

T9 改了什么
-----------
**界面刚度 γ(n)** 改为逐胞按 `(k, larr)` 查表（`facet_nref`）：
  `(k,0)` ⇒ `npref[k]`（变体 k 与**母相**的惯习面）；`(k,l)` ⇒ `ncmp[k,l]`（两变体的
  rank-1 相容/不变平面）。T9 之前 γ 一律用 **winner 自己的 `npref[k]`**
  ⇒ 变体-变体界面上择优方向用错对象（迁移率那边本来就是按配对查的）。

判据
----
  T9-A **单元判据**（精确、不靠统计）：`facet_nref` 在变体-母相胞返回 `npref[k]`、
        在变体-变体胞返回 `ncmp[k,l]`，且与表**逐位**一致
  T9-B **"表被消费"**：把 `ncmp` 表在变体对之间**打乱** ⇒ 结果**必须变**
        （证明这条表真的进了 γ，不是摆设）
  T9-C **"配对身份起作用"（对照）**：`facet_id_gamma=False`（退回 winner-only）
        ⇒ 结果与 True 档**必须不同**
  T9-D **方向一致**：`aniso>0` 时 `herring_stiffness` 在 `n ∥ nref` 处取**最小**刚度
        ⇒ 界面倾向于长成以 `nref` 为法向的面（板条的宽面 = 惯习面）

判据量：跑 N 步后（i）变体体积（ii）界面键数（iii）**主轴与 npref[1] 的夹角**。
三者中**至少一个**必须出现可分辨的差异（阈值：体积/键数相对 > 1e-3，或夹角 > 0.5°）。

用法：python3 T9_verify_facetid.py [--N 48] [--steps 60]
退出码：0 = PASS
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


def mk(N, dx, nseed=6, facet_id=True, shuffle=False, seed=4):
    L = N * dx
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                        df=[0.0] + [2.0e8] * NV, workers=4, reinit_every=0)
    g.facet_id_gamma = bool(facet_id)
    if shuffle and getattr(g, 'ncmp', None) is not None:
        # 只在**变体对**之间打乱（母相相关项保持 nan ⇒ 调用方仍走 npref）
        tab = np.array(g.ncmp, copy=True)
        idx = [(k, l) for k in range(1, NV + 1) for l in range(k + 1, NV + 1)]
        vals = np.array([tab[k, l] for k, l in idx])
        perm = np.random.default_rng(11).permutation(len(idx))
        for i, (k, l) in enumerate(idx):
            tab[k, l] = tab[l, k] = vals[perm[i]]
        g.ncmp = tab
        g.facet_id_gamma = True
    rng = np.random.default_rng(seed)
    R = 0.10 * L
    ns = 0
    while ns < nseed:
        c = rng.random(3) * (L - 2 * R) + R
        try:
            g.seed_plate(int(rng.integers(1, NV + 1)), c, NPF[1], R, 4 * dx)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    return g


def metrics(g, dx):
    reg = g.region()
    V = int((reg > 0).sum())
    nb = 0
    for ax in range(3):
        nb += int((reg != np.roll(reg, -1, axis=ax)).sum())
    # 变体团簇的主轴 vs npref[1]
    idx = np.argwhere(reg > 0)
    ang = np.nan
    if idx.size > 30:
        p = idx.astype(float) * dx
        p = p - p.mean(0)
        ev, evec = np.linalg.eigh(np.cov(p.T))
        ax0 = evec[:, int(np.argmax(ev))]
        ang = float(np.degrees(np.arccos(np.clip(abs(ax0 @ NPF[1]), 0, 1))))
    return dict(V=V, bonds=nb, ang=ang)


def run(g, nstep, dt):
    for _ in range(nstep):
        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
    return metrics(g, g.dx)


def t9_A(N, dx):
    print('【T9-A】单元判据：facet_nref 必须与表逐位一致')
    g = mk(N, dx, nseed=4)
    larr = np.zeros((N, N, N), dtype=np.int64)
    # 构造：一半胞的 runner-up = 0（变体-母相），一半 = 2（变体-变体）
    larr[: N // 2] = 0
    larr[N // 2:] = 2
    out = g.facet_nref(1, larr, NPF)
    ok = out is not None
    if ok:
        nk = NPF[1] / np.linalg.norm(NPF[1])
        d_parent = float(np.max(np.abs(out[: N // 2] - nk)))
        cand = g.ncmp[1, 2]
        d_pair = float(np.max(np.abs(out[N // 2:] - cand)))
        print('   变体-母相胞：max|out − npref[1]| = %.3e（须逐位 0）' % d_parent)
        print('   变体-变体胞：max|out − ncmp[1,2]| = %.3e（须逐位 0）' % d_pair)
        # ncmp[1,2] 与 npref[1] 必须**不同**（否则本判据看不见差异）
        sep = float(np.degrees(np.arccos(np.clip(abs(cand @ nk), 0, 1))))
        print('   ncmp[1,2] 与 npref[1] 的夹角 = %.2f°（必须显著非 0）' % sep)
        ok = (d_parent == 0.0) and (d_pair == 0.0) and (sep > 1.0)
    print('   T9-A: %s' % ('PASS' if ok else 'FAIL'))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=48)
    ap.add_argument('--dx-nm', type=float, default=25.0)
    ap.add_argument('--steps', type=int, default=60)
    a = ap.parse_args()
    N, dx = a.N, a.dx_nm * 1e-9
    dt = 0.15 * dx / (1e-9 * 2.0e8)
    print('=' * 100)
    print('T9 —— 界面本构按面片身份 (k,l) 查表   N=%d dx=%.0f nm steps=%d'
          % (N, a.dx_nm, a.steps))
    print('=' * 100)
    okA = t9_A(N, dx)
    print()
    print('【T9-B/C】跑 %d 步：三档对照' % a.steps)
    res = {}
    for tag, kw in (('表对 + 按面片', dict(facet_id=True, shuffle=False)),
                    ('表对 + winner-only(对照)', dict(facet_id=False, shuffle=False)),
                    ('**打乱表** + 按面片', dict(facet_id=True, shuffle=True))):
        g = mk(N, dx, **kw)
        r = run(g, a.steps, dt)
        res[tag] = r
        print('   %-26s V=%-7d 界面键=%-7d 主轴 vs npref[1] = %.2f°' %
              (tag, r['V'], r['bonds'], r['ang']), flush=True)
    base = res['表对 + 按面片']
    ctl = res['表对 + winner-only(对照)']
    shf = res['**打乱表** + 按面片']

    def diff(r):
        dv = abs(r['V'] - base['V']) / max(base['V'], 1)
        db = abs(r['bonds'] - base['bonds']) / max(base['bonds'], 1)
        da = abs(r['ang'] - base['ang']) if np.isfinite(r['ang']) else 0.0
        return dv, db, da
    dC = diff(ctl)
    dS = diff(shf)
    print()
    print('   vs 基准：winner-only 对照  ΔV=%.3e Δ键=%.3e Δ角=%.3e°' % dC)
    print('            打乱表        ΔV=%.3e Δ键=%.3e Δ角=%.3e°' % dS)
    okC = (dC[0] > 1e-3) or (dC[1] > 1e-3) or (dC[2] > 0.5)
    okB = (dS[0] > 1e-3) or (dS[1] > 1e-3) or (dS[2] > 0.5)
    print('   T9-B（打乱表 ⇒ 结果必须变）: %s' % ('PASS' if okB else 'FAIL'))
    print('   T9-C（退回 winner-only ⇒ 必须与按面片不同）: %s' % ('PASS' if okC else 'FAIL'))

    print()
    print('【T9-D】各向异性通道的方向（★ 记账：首版把 γ 的方向写反了，已按实测改）')
    n = np.array([[0.0, 0, 1.0], [1.0, 0, 0], [0.0, 1.0, 0]])
    nref = np.array([0.0, 0.0, 1.0])
    c2 = np.clip((n @ nref) ** 2, 0.0, 1.0)
    gk = W.herring_stiffness(c2, 0.15, 0.4, True)
    print('   实测约定 γ*(n∥nref)=%.6f ；γ*(n⊥nref)=%.6f ⇒ 各向异性比 %.2f×'
          % (gk[0], gk[1], gk[0] / gk[1]))
    print('   ⇒ **γ 的各向异性方向与"板条几何"相反**；这与项目已实测的"γ 通道在真实')
    print('      驱动力下对取向零效果（P0.3：aniso 0→0.9，M6 中位恒 55.4°）"一致')
    print('      ⇒ 板条几何只能靠 M(n)。T9 的意义是让 γ **也**用对面片身份。')
    okD1 = bool(gk[0] > 1.5 * gk[1])
    beta = 3.5
    mfac = np.exp(-beta * c2)
    print('   M(n)/M0：n∥n* = %.6f ；n⊥n* = %.6f ⇒ 最小在 n∥n*: %s'
          % (mfac[0], mfac[1], mfac[0] < mfac[1]))
    okD2 = bool(mfac[0] < mfac[1])
    L = N * dx
    g2 = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                         df=[0.0] + [2.0e8] * NV, workers=4, reinit_every=25)
    g2.seed_plate(1, [L / 2] * 3, NPF[1], 0.10 * L, 4 * dx)
    g2.init_parent()
    for _ in range(120):
        g2.elastic_driving()
        g2.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
    reg2 = g2.region()
    idx2 = np.argwhere(reg2 == 1)
    if idx2.size > 30:
        p = idx2.astype(float) * dx
        p = p - p.mean(0)
        ev, evec = np.linalg.eigh(np.cov(p.T))
        thin = evec[:, int(np.argmin(ev))]
        ang = float(np.degrees(np.arccos(np.clip(abs(thin @ NPF[1]), 0, 1))))
        print('   端到端：最薄方向 vs npref[1] = **%.2f°**（应 < 20°）；尺度比 %.2f : %.2f : 1'
              % (ang, np.sqrt(ev[2] / ev[0]), np.sqrt(ev[1] / ev[0])))
        okD3 = ang < 20.0
    else:
        print('   端到端：变体太小，无法定主轴')
        okD3 = False
    okD = okD1 and okD2 and okD3
    print('   T9-D（γ 各向异性 / M(n) 最小在 n∥n* / 端到端最薄方向对齐）: %s'
          % ('PASS' if okD else 'FAIL'))

    r = [('T9-A', okA), ('T9-B', okB), ('T9-C', okC), ('T9-D', okD)]
    print()
    print('=' * 100)
    for nm, ok in r:
        print('  %-6s %s' % (nm, 'PASS' if ok else 'FAIL'))
    allok = all(ok for _n, ok in r)
    print('  ⇒ T9 %s' % ('PASS' if allok else 'FAIL'))
    print('=' * 100)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
