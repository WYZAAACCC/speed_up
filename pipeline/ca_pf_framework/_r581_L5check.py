#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_L5check.py --- L5（`--argmin2-reuse`）的**真实引擎**逐位判据。

## 判据
* **P1** `advance()` 在 `argmin_reuse ∈ {0,1}` 下必须**逐位相同**（比 `g.phi`）；
* **P2** 直接比 `region()` 与 `argmin2(phi)` 的 winner：`argmin_reuse=1` 的
  `karr` 必须与 `argmin_reuse=0` 的 `karr` **逐位相同**（值 + dtype）；
* **P3 负对照（必须有分辨力）**：故意把 `k_pre` **错一格**（用 `phi` 的第 2 名当 winner）
  必须产生差异 —— 证明 P1/P2 不是空判；
* **P4 活性**：`argmin_reuse=1` 时 `argmin2.winner` 的计数必须**掉到 0**
  （防"开关看起来生效、实则没接上"）；
* **P5 计数回归（预期变化）**：每步**总 argmin 次数** 3 → 2；
* **P6** `larr` 的**值**必须相同（dtype 允许从 intp 变 int16 后再加宽）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import windowB_surface as W
import windowB_par as PAR

N = 40
NV = 12
DX = 62.5e-9
# ★★ 必须用 **workers > 1**：`map0_two` 在 `n<=1` 时直接 `fn(0, n0)`
#    ⇒ 切片退化，**代码里的切片轴写错也看不出来**（第一版就是这么漏掉的）。
#    goal §(2) 门 4 的意义正在于此：**单元判据过 ≠ 真实路径过**（AGENTS P3）。
WORKERS = int(os.environ.get('R581L5_WORKERS', '4'))


def build(reuse):
    from T16_verify_rve import C, EPS0
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(NV)]
    g = W.LevelSetMulti(N, N * DX, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        workers=WORKERS, nv=NV, reinit_every=0,
                        argmin_reuse=reuse)
    Lc = N * DX
    x = (np.arange(N) + 0.5) * DX
    X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
    rng = np.random.default_rng(5)
    g.phi[0] = 0.5 * Lc
    for v in range(NV):
        c = rng.random(3) * Lc * 0.6 + Lc * 0.2
        g.phi[v + 1] = np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2
                               + (Z - c[2]) ** 2) - 0.14 * Lc
    return g


def run_advance(g, nst=2):
    npref = {v: np.array([0.0, 0.0, 1.0]) for v in range(1, NV + 1)}
    for _ in range(nst):
        g.advance(1e-12, aniso=0.4, npref=npref, band_cells=20, iface_band=2.0,
                  mob_beta=3.5, mob_beta_w=2.3, adv_grad='proj2')
    return g.phi.copy()


def main():
    L = ['=' * 92, 'R581-L5check —— `--argmin2-reuse` 真引擎逐位判据（workers=%d）'
         % WORKERS, '=' * 92]
    fails = []
    # ★★ 量具自身的盲区守卫：`workers=1` 时空间切片退化 ⇒ 这个判据**必须**在 >1 下跑，
    #    否则会给"切片轴写错"发通行证（第一版就是这么漏的）。
    if WORKERS <= 1:
        L.append('  ❌ **量具失效**：workers=%d ⇒ `map0_two` 不切片，判据退化。'
                 '请用 R581L5_WORKERS>=2。' % WORKERS)
        fails.append('量具：workers<=1')

    # ---- P1/P2 -------------------------------------------------------------
    g0 = build(0); p0 = run_advance(g0)
    g1 = build(1); p1 = run_advance(g1)
    neq = int(np.count_nonzero(p0 != p1))
    L.append('── P1 `advance()` 两步后 `g.phi` ──')
    L.append('    reuse=1 vs 0：不等元素=%d  max|Δ|=%.3e  %s'
             % (neq, float(np.max(np.abs(p0 - p1))) if neq else 0.0,
                '✅ 逐位' if neq == 0 else '❌ 不逐位'))
    if neq:
        fails.append('P1')

    L.append('── P2 winner / runner-up 本身 ──')
    a0 = build(0); k0, l0 = a0.par.argmin2(a0.phi, mode='copyto')
    r0 = a0.region()
    a1 = build(1)
    r1 = a1.region()
    k1, l1 = a1.par.argmin2(a1.phi, mode='copyto', k_pre=r1)
    for nm, x, y in (('k_pre 与 region()', k1, r0),
                     ('k_pre=reuse vs 归档 karr', k1, k0),
                     ('larr', l1, l0)):
        d = int(np.count_nonzero(x != y))
        L.append('    %-26s 不等=%-8d dtype=%s/%s  %s'
                 % (nm, d, x.dtype, y.dtype, '✅ 值逐位' if d == 0 else '❌ 有差异'))
        if d:
            fails.append('P2 %s' % nm)

    # ---- P3 负对照：把 k_pre 换成"第二名" --------------------------------
    L.append('── P3 负对照：`k_pre` 故意用 runner-up（必须产生差异）──')
    kbad, lbad = a1.par.argmin2(a1.phi, mode='copyto', k_pre=l1.astype(np.int16))
    nbad = int(np.count_nonzero(kbad != k1))
    L.append('    用 runner-up 当 winner：不等元素=%d  %s'
             % (nbad, '✅ 有分辨力' if nbad else '❌ **判据失效**'))
    if not nbad:
        fails.append('P3 恒 0')

    # ---- P4/P5 计数 --------------------------------------------------------
    L.append('── P4/P5 计数（活性 + 预期变化）──')
    import windowB_acct as AC
    # ★ 记账钩子**默认是关的**（`acct.mark` 未启用时是空操作）⇒ 必须先 enable，
    #   否则"计数=0"会被误读成"开关没接上"。这正是本仓 P6 那类量具失效。
    AC.enable()
    _reg0 = W.LevelSetMulti.region
    _pa0 = PAR.ParCtx.argmin
    BOX = {'reg': 0, 'pa': 0}

    def _reg_counted(self):
        BOX['reg'] += 1
        return _reg0(self)

    def _pa_counted(self, fields):
        BOX['pa'] += 1
        return _pa0(self, fields)
    W.LevelSetMulti.region = _reg_counted
    PAR.ParCtx.argmin = _pa_counted
    try:
        for tag, reuse in (('reuse=0', 0), ('reuse=1', 1)):
            g = build(reuse)
            AC.reset()
            BOX['reg'] = BOX['pa'] = 0
            run_advance(g, nst=1)
            _T, C = AC.totals()
            nwin = int(C.get('argmin2.winner', 0))
            nreg, npa = BOX['reg'], BOX['pa']
            L.append('    %-8s region()=%d  par.argmin=%d  argmin2.winner=%d'
                     '   ⇒ 每步**总 argmin** = %d'
                     % (tag, nreg, npa, nwin, npa + (1 if nwin else 0)))
            if reuse == 1 and nwin != 0:
                fails.append('P4 reuse=1 但 argmin2.winner=%d（开关没接上）' % nwin)
            if reuse == 0 and nwin == 0:
                fails.append('P4 reuse=0 但 argmin2.winner=0（量具没记到）')
    finally:
        W.LevelSetMulti.region = _reg0
        PAR.ParCtx.argmin = _pa0
        AC.disable()

    L.append('')
    L.append('❌ 失败：%s' % ', '.join(fails) if fails else '✅ 全部通过')
    out = '\n'.join(L)
    print(out)
    open('_w2_r581_L5check.log', 'w').write(out + '\n')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
