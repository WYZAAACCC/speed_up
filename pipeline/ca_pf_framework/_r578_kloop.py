#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r578_kloop.py --- `k_loop_mode='act'` 的**逐位判据 + 负对照**。

## 判据（先写死，必须能失败）

* **V1 逐位相同**：同一初始状态、同 `dt`、连续 `STEPS` 步，
  `k_loop_mode='full'` 与 `'act'` 的 `g.phi` **逐位相同**（`max|Δ| == 0.0`）。
  逐步比，不只比末态 —— 只比末态会漏掉"中途分叉又收敛"。
* **V2 活跃集非退化**：`nact` 必须 **> 0 且 < nreg**（否则这个开关根本没被考验）。
* **V3 负对照（必须有分辨力）**：把 `act` 故意**去掉一个真正活跃的场**
  ⇒ `g.phi` 必须**明显不同**（`max|Δ| > 0`）。若负对照也给 0 ⇒ 量具没有分辨力，V1 不算数。
* **V4 覆盖两档驱动**：至少跑两种构型（只有 F1 界面 / 有 F3 同变体界面），
  因为 `act` 的大小在两种构型下不同。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import windowB_surface as W                                     # noqa: E402
import windowB_par as PAR                                       # noqa: E402
from T16_verify_rve import C, EPS0                              # noqa: E402

N = int(os.environ.get('R578_N', '48'))
NV = int(os.environ.get('R578_NV', '8'))
DX = float(os.environ.get('R578_DX', '0.0625'))
STEPS = int(os.environ.get('R578_STEPS', '6'))
WORK = int(os.environ.get('R578_WORKERS', '4'))
SEED = int(os.environ.get('R578_SEED', '7'))


def build(mode, extra_seeds=0):
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(NV)]
    g = W.LevelSetMulti(N, N * DX, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        df=[0.0] + [3.0e8] * NV, workers=WORK,
                        reinit_every=20, reinit_dt=1e-4, reinit_band_cells=6.0,
                        phi_prec='f64', k_loop_mode=mode)
    g.init_parent()
    rng = np.random.default_rng(SEED)
    Lc = N * DX
    nrm = np.array([0.0, 0.0, 1.0])
    nseed = max(3, NV // 8)
    for k in range(1, nseed + 1):
        g.seed_plate(k, rng.random(3) * (Lc * 0.6) + Lc * 0.2, nrm, 120e-9, 300e-9)
    # ★ V4：额外的**同变体**种子（`vgroup` 让它们进新场但同变体 ⇒ 产生 F3 界面）
    if extra_seeds:
        vg = getattr(g, 'vgroup', None)
        for j in range(extra_seeds):
            k = nseed + 1 + j
            if k >= NV + 1:
                break
            if isinstance(vg, dict):
                vg[k] = 1
            g.seed_plate(k, rng.random(3) * (Lc * 0.6) + Lc * 0.2, nrm,
                         120e-9, 300e-9)
    return g


def run(mode, extra_seeds, drop_last_active=False):
    """跑 STEPS 步，逐步记录 `g.phi` 的副本 + `nact`。

    ★ 负对照的做法（v1 写错过，记账）：v1 去劫持 `np.unique` 让它少返回一个 k。
      那会**同时**改掉 `advance()` 里所有其它 `np.unique` 调用（诊断块、`_bbox_pad`…），
      ⇒ 差异出现了，但**不是"少遍历一个活跃场"造成的** ⇒ 负对照**归因错误**
      （与 `AGENTS.md` 教训 21「隔离实验必须只差一个因素」同类）。
    现改为**只包 `ParCtx.for_each` 的 `advance.k_loop` 这一路**，并且**只在 `act` 臂上**
    丢最后一个元素 —— `act` 的每个元素**按定义**都是活跃场 ⇒ 丢掉的**一定**是活跃场。
    """
    g = build(mode, extra_seeds)
    if not drop_last_active:
        return _run_steps(g)
    _fe = PAR.ParCtx.for_each

    def _fe_drop(self, items, tag=None):
        if tag == 'advance.k_loop' and len(items) > 1:
            items = items[:-1]           # ← act 臂：最后一个**一定**是活跃场
        return _fe(self, items, tag=tag)
    PAR.ParCtx.for_each = _fe_drop
    try:
        return _run_steps(g)
    finally:
        PAR.ParCtx.for_each = _fe


def _run_steps(g):
    snaps, nacts = [], []
    for _ in range(STEPS):
        g.advance(dt=1e-8)
        snaps.append(g.phi.copy())
        nacts.append(int(getattr(g, '_t3_nact', -1)))
    return snaps, nacts


def main():
    L = []
    A = L.append
    A('=' * 96)
    A('R578 — `k_loop_mode` 逐位判据 (N=%d nv=%d steps=%d workers=%d)'
      % (N, NV, STEPS, WORK))
    A('=' * 96)
    ok_all = True

    for tag, extra in (('F1-only（3 个种子，无同变体叠加）', 0),
                       ('F1+F3（额外 3 个同变体种子）', 3)):
        A('')
        A('  ---- 构型 %s ----' % tag)
        sa, na = run('full', extra)
        sb, nb = run('act', extra)
        worst = 0.0
        for i, (x, y) in enumerate(zip(sa, sb)):
            d = float(np.max(np.abs(x - y)))
            worst = max(worst, d)
            if d != 0.0:
                A('    step %d: max|Δ| = %.3e  ❌' % (i + 1, d))
        A('    V1 逐位：%d 步内 max|Δ| = **%.3e**  ⇒ %s'
          % (STEPS, worst, '✅ 逐位相同' if worst == 0.0 else '❌ 不等价'))
        ok_all = ok_all and worst == 0.0
        A('    V2 活跃集：full 侧 nact=%s   act 侧 nact=%s'
          % (na, nb))
        v2 = all(0 < x < NV + 1 for x in nb)
        A('    V2 判定（0 < nact < nreg=%d）：%s' % (NV + 1,
                                                  '✅' if v2 else '❌ 退化'))
        ok_all = ok_all and v2

        # V3 负对照：**同样走 `act` 臂**，只是丢最后一个元素（一定是活跃场）
        sc, _ = run('act', extra, drop_last_active=True)
        wneg = 0.0
        for x, y in zip(sb, sc):
            wneg = max(wneg, float(np.max(np.abs(x - y))))
        A('    V3 负对照（`act` 臂丢最后一个活跃场）：max|Δ| = **%.3e**  ⇒ %s'
          % (wneg, '✅ 量具有分辨力' if wneg > 0 else '❌ 量具没有分辨力，V1 不算数'))
        ok_all = ok_all and wneg > 0

    A('')
    A('  === RESULT: %s ===' % ('ALL PASS' if ok_all else 'FAIL'))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r578_kloop.log'), 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')
    return 0 if ok_all else 1


if __name__ == '__main__':
    sys.exit(main())
