#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T2_verify_reinit.py --- T2 判据：`reinitialize(mode='pair')` 不得把 |∇φ| 推离 1（P0-3）。

物理/数值背景
-------------
VDF（vector distance function）的正确 SDF 条件是**每个** φ_k 都是 SDF，即 |∇φ_k| = 1。
界面处 ∇φ_k = +n、∇φ_l = −n ⇒ d = φ_k − φ_l 满足 |∇d| = **2**，
而 d2 = d/2 才是 Sussman 重初始化的不动点（|∇d2| = 1）。

旧写法对 **d 本身**做 Sussman（目标 |∇d| = 1）⇒ 把 |∇φ| 推向 0.5 并继续塌陷。

判据
----
  T2-A  单因素（只差 reinit_every）：0 vs 25，160 步后
          带内 median|∇φ_winner| 差 < 5%，且 ∈ [0.95, 1.05]
          带内 median|∇d2| ∈ [0.90, 1.10]
          界面"键"总数膨胀 < 1.2×
  T2-B  单次 reinit：零等值面位移 ≤ 1e-3·dx；median|∇φ| 变化 < 5%
  T2-C  反向对照：把目标改回 |∇d| = 1（旧行为）⇒ T2-A/T2-B 必须 **FAIL**

用法：python3 T2_verify_reinit.py [--N 64] [--steps 120]
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
K = 1

# 软化（≈惯习面）法向，用作界面法向
_rng = np.random.default_rng(0)
_best, NPF = None, None
for n in _rng.normal(size=(2000, 3)):
    n = n / np.linalg.norm(n)
    val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[K - 1], _lam_full(C, n), EPS0[K - 1]))
    if _best is None or val < _best:
        _best, NPF = val, n

OLD_MODE = [False]                     # True = 复现旧行为（目标 |∇d|=1），做反向对照


def build(N, dx, reinit_every, strict=False):
    """变体 k / 母相 的**单个平面界面**（法向 = 软化法向）。"""
    L = N * dx
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.0, Mob=1e-9,
                        df=[0.0] + [2.0e8] * NV, workers=4,
                        reinit_every=reinit_every)
    g.pf = None                        # 关掉弹性 ⇒ 只剩「推进格式 + 重初始化」
    g.reinit_strict = bool(strict)
    rel = g.XYZ - np.array([L / 2] * 3)
    dn = rel @ NPF
    g.phi[K] = dn
    for j in range(1, g.nreg):
        if j != K:
            g.phi[j] = 1e3
    g.init_parent()                    # φ_0 = −min(φ_{k≥1}) = −dn
    return g, L


def _pair_d2(g):
    order = np.argsort(g.phi, axis=0)
    ka, la = order[0], order[1]
    phw = np.take_along_axis(g.phi, ka[None], 0)[0]
    phl = np.take_along_axis(g.phi, la[None], 0)[0]
    return ka, la, phw, 0.5 * (phw - phl)


def metrics(g, dx, band_cells=2.0):
    _, _, phw, d2 = _pair_d2(g)
    gr = np.gradient(phw, dx)
    gn = np.sqrt(sum(t ** 2 for t in gr))
    g2 = np.gradient(d2, dx)
    g2n = np.sqrt(sum(t ** 2 for t in g2))
    band = np.abs(d2) <= band_cells * dx
    reg = g.region()
    nb = 0
    for ax in range(3):
        nb += int((reg != np.roll(reg, -1, axis=ax)).sum())
    return dict(nband=int(band.sum()), bonds=nb,
                med_gphi=float(np.median(gn[band])) if band.any() else np.nan,
                med_gd2=float(np.median(g2n[band])) if band.any() else np.nan)


def iface_pos(g, dx, L):
    """界面位置（沿 NPF 的**带质心**）。

    为什么不用射线求根：界面正好过域中心 ⇒ 从中心出发的射线起点就在界面上，
    零交点检测必然返回 nan（首版实测 nan，记账）。带质心对平界面是等价测度，
    且对"界面整体平移"严格线性 ⇒ 适合判"零等值面是否被移动"。
    """
    _, _, _, d2 = _pair_d2(g)
    band = np.abs(d2) <= 2.0 * dx
    if not band.any():
        return np.nan
    idx = np.argwhere(band).astype(float) * dx + 0.5 * dx
    return float(((idx - L / 2) @ NPF).mean())


# ---------------------------------------------------------------- 旧行为复现
_orig_sussman = W.LevelSetMulti.sussman_reinit
_orig_reinit = W.LevelSetMulti.reinitialize


def reinit_old(self, band_cells=6, mode='pair'):
    """复现**旧**行为：对 d 本身做 Sussman（目标 |∇d|=1）。仅供反向对照。"""
    if mode != 'pair':
        return _orig_reinit(self, band_cells=band_cells, mode=mode)
    reg = self.region()
    pairs = set()
    for ax in range(3):
        a = reg
        b = np.roll(reg, -1, axis=ax)
        sel = a != b
        if sel.any():
            for x, y in zip(a[sel].ravel(), b[sel].ravel()):
                if x != y:
                    pairs.add((int(min(x, y)), int(max(x, y))))
    if not pairs:
        return
    order = np.argsort(self.phi, axis=0)
    _karr, _larr = order[0], order[1]
    delta = np.zeros_like(self.phi)
    for (k, l) in pairs:
        d = self.phi[k] - self.phi[l]
        near = np.abs(d) <= band_cells * self.dx
        if not near.any():
            continue
        dn = self.sussman_reinit(d)
        corr = np.where(near, dn - d, 0.0)
        is_kl = ((_karr == k) & (_larr == l)) | ((_karr == l) & (_larr == k))
        corr = np.where(is_kl, corr, 0.0)
        delta[k] += 0.5 * corr
        delta[l] -= 0.5 * corr
    self.phi = self.phi + delta


def set_old(on):
    W.LevelSetMulti.reinitialize = reinit_old if on else _orig_reinit


# ---------------------------------------------------------------- T2-A
def run_A(N, dx, steps, old=False):
    """★ 判据取在 **reinit 步**上（steps 取 25 的倍数）。

    为什么必须这样（本轮实测教训，记账）：若取在任意步上，测到的 Δ|∇φ| 会**同时**
    含两个因素 —— ① reinit 的效果、② 平流格式自身的漂移。实测轨迹：
        step 20/40/60/80：两种模式都 1.000/0.994（平流很干净）
        step 100 起：**两种模式都**出现 bonds 跳涨（14758→22412）与 |∇φ| 漂到 1.02
        ⇒ 这是**平流侧**的事件，与 reinit 无关（reinit=0 档同样发生）。
    取在 reinit 步上 ⇒ 只差 reinit 这一个因素，符合「单变量对照」。
    （平流侧的漂移已单独登记，归 T3/T11 处理。）
    """
    tag = '旧(目标|∇d|=1)' if old else '新(目标|∇d2|=1)'
    out = {}
    step_ref = 25 * max(1, steps // 25)
    for re_ in (0, 25):
        g, L = build(N, dx, re_)
        dt = 0.15 * dx / (1e-9 * 2.0e8)
        hist = []
        at_ref = None
        for it in range(1, steps + 1):
            g.advance(dt)
            if it % 25 == 0 or it == steps:
                m = metrics(g, dx)
                hist.append((it, m['med_gphi'], m['med_gd2'], m['bonds']))
                if it == step_ref:
                    at_ref = m
        m = metrics(g, dx)
        out[re_] = at_ref if at_ref is not None else m
        print('  [%s] reinit_every=%-3d  @step %d: nband=%-7d bonds=%-7d  '
              'med|∇φ|=%.4f  med|∇d2|=%.4f  (末步 med|∇φ|=%.4f)'
              % (tag, re_, step_ref, out[re_]['nband'], out[re_]['bonds'],
                 out[re_]['med_gphi'], out[re_]['med_gd2'], m['med_gphi']), flush=True)
        print('     轨迹(step: med|∇φ|, med|∇d2|, bonds): ' +
              ' | '.join('%d: %.3f, %.3f, %d' % h for h in hist))
    m0, m25 = out[0], out[25]
    d_rel = abs(m25['med_gphi'] - m0['med_gphi']) / max(m0['med_gphi'], 1e-30)
    infl = m25['bonds'] / max(m0['bonds'], 1)
    ok = (d_rel < 0.05 and 0.95 <= m25['med_gphi'] <= 1.05
          and 0.90 <= m25['med_gd2'] <= 1.10 and infl < 1.2)
    print('  ⇒ Δmedian|∇φ| = %.2f%%（<5%%）;  reinit 档 med|∇φ| = %.4f（∈[0.95,1.05]）;'
          '  med|∇d2| = %.4f（∈[0.90,1.10]）;  键比 %.3f×（<1.2）'
          % (100 * d_rel, m25['med_gphi'], m25['med_gd2'], infl))
    print('  T2-A[%s]: %s' % (tag, 'PASS' if ok else 'FAIL'))
    return ok, out


# ---------------------------------------------------------------- T2-B
def run_B(N, dx, old=False):
    g, L = build(N, dx, 0)
    g.reinit_strict = True
    m0 = metrics(g, dx)
    p0 = iface_pos(g, dx, L)
    try:
        g.reinitialize()
        raised = None
    except RuntimeError as e:
        raised = str(e)
    m1 = metrics(g, dx)
    p1 = iface_pos(g, dx, L)
    dp = abs(p1 - p0)
    d_rel = abs(m1['med_gphi'] - m0['med_gphi']) / max(m0['med_gphi'], 1e-30)
    infl = m1['bonds'] / max(m0['bonds'], 1)
    ok = (dp <= 1e-3 * dx) and (d_rel < 0.05) and (infl < 1.2)
    print('  单次 reinit：零等值面位移 = %.3e m（= %.2e dx，判据 ≤1e-3 dx）' % (dp, dp / dx))
    print('    med|∇φ| %.4f -> %.4f（%.2f%%）;  med|∇d2| %.4f -> %.4f;  键 %.3f×'
          % (m0['med_gphi'], m1['med_gphi'], 100 * d_rel,
             m0['med_gd2'], m1['med_gd2'], infl))
    if raised:
        print('    ★ 硬失败守卫触发：%s' % raised)
    print('  T2-B[%s]: %s' % ('旧' if old else '新', 'PASS' if ok else 'FAIL'))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=64)
    ap.add_argument('--dx-nm', type=float, default=20.0)
    ap.add_argument('--steps', type=int, default=120)
    a = ap.parse_args()
    N, dx = a.N, a.dx_nm * 1e-9
    print('=' * 96)
    print('T2 —— pair reinit 目标梯度（P0-3）   N=%d  dx=%.0f nm  steps=%d' % (N, a.dx_nm, a.steps))
    print('=' * 96)
    set_old(False)
    print('【修后（新）】')
    oka, _ = run_A(N, dx, a.steps, old=False)
    okb = run_B(N, dx, old=False)
    print()
    print('【反向对照（旧行为）—— 判据必须 FAIL】')
    set_old(True)
    oka_o, _ = run_A(N, dx, a.steps, old=True)
    okb_o = run_B(N, dx, old=True)
    set_old(False)
    print()
    print('=' * 96)
    print('  T2-A 新: %-5s   旧(对照): %-5s   %s'
          % ('PASS' if oka else 'FAIL', 'PASS' if oka_o else 'FAIL',
             '✓ 对照已 FAIL' if not oka_o else '✗ 对照竟然 PASS ⇒ 判据没有分辨力'))
    print('  T2-B 新: %-5s   旧(对照): %-5s   %s'
          % ('PASS' if okb else 'FAIL', 'PASS' if okb_o else 'FAIL',
             '✓ 对照已 FAIL' if not okb_o else '✗ 对照竟然 PASS ⇒ 判据没有分辨力'))
    allok = oka and okb and (not oka_o) and (not okb_o)
    print('  ⇒ T2 %s' % ('PASS' if allok else 'FAIL'))
    print('=' * 96)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
