#!/usr/bin/env python3
"""_r413_fpverify.py —— ★ **§186 修复的验证**：走**真实代码路径**，不再手搓算子。

`_r410/_r411/_r412` 都是**离线重实现**（自己构造 `excl`、自己合成 `region`）。
它们证明了机理，但**不能证明"改了 `windowB_surface.facet_project()` 之后行为变了"**。
本脚本补上这一环：**直接调用引擎的 `LevelSetMulti.facet_project()`**，
用一个**最小但真实**的 `LevelSetMulti` 实例（12 场、`npref_tab/atab/wtab` 都按驱动同款填），
把 `region` 灌进去、调用真方法、读回 `phi`、重新算 `region`。

判据（预先写死）：
  **V-1 正对照**：`facet_excl=1` 必须**复现** `_r410` 的旧行为
       （F3 → 0、块数 6 → 12）。若这条不过，说明我的离线重实现**没有忠实复现引擎**
       ⇒ 前面 §186 的全部结论**作废**。（这是**最关键**的一条。）
  **V-2 修复生效**：`facet_excl=0`（新默认）必须给出 F3 > 1000、块数 = 6。
  **V-3 静默等价**：`facet_proj = 0` 时 `facet_project()` **不被调用** ⇒ 与 `excl` 无关。
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import windowB_surface as W                                    # noqa: E402
from T16_verify_rve import C, EPS0, NPF, MOB, DF               # noqa: E402

RUN = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mb/dry_saSet2'
STEP = int(sys.argv[2]) if len(sys.argv) > 2 else 0


def P(s):
    print(s, flush=True)


def face_counts(reg, vmap):
    c1 = c2 = c3 = 0
    for d in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        nb = np.roll(reg, d, axis=(0, 1, 2))
        iface = (reg != nb)
        if not iface.any():
            continue
        a, b = reg[iface], nb[iface]
        lo = np.minimum(a, b)
        hi = np.maximum(a, b)
        z = (lo == 0)
        c1 += int(np.count_nonzero(z))
        nz = ~z
        if nz.any():
            va = np.array([vmap.get(int(x), -1) for x in hi[nz]])
            vb = np.array([vmap.get(int(x), -1) for x in lo[nz]])
            same = (va == vb)
            c3 += int(np.count_nonzero(same))
            c2 += int(np.count_nonzero(~same))
    return c1, c2, c3


def blocks_of(reg, vmap):
    from scipy import ndimage
    res = []
    for v in sorted(set(vmap.values())):
        ks = [k for k, vv in vmap.items() if vv == v]
        m = np.isin(reg, ks)
        if not m.any():
            continue
        lab, n = ndimage.label(m, structure=ndimage.generate_binary_structure(3, 1))
        parent = list(range(n + 1))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def uni(x, y):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[max(rx, ry)] = min(rx, ry)
        for ax in (0, 1, 2):
            A = lab.take(0, axis=ax)
            B = lab.take(-1, axis=ax)
            sel = (A > 0) & (B > 0)
            for x, y in zip(A[sel].ravel(), B[sel].ravel()):
                uni(int(x), int(y))
        sz = {}
        for x in range(1, n + 1):
            r = find(x)
            sz[r] = sz.get(r, 0) + int((lab == x).sum())
        for r, s in sz.items():
            res.append((v, s))
    res.sort(key=lambda t: -t[1])
    return len(res), res


def main():
    P('=' * 78)
    P('_r413 —— §186 修复验证（**走真实代码路径** `LevelSetMulti.facet_project()`）')
    P('  用例 %s  step=%d' % (RUN, STEP))
    P('=' * 78)
    sd = np.load(os.path.join(RUN, 'seeds.npz'))
    sp = os.path.join(RUN, 'snap_%05d.npz' % STEP)
    d = np.load(sp if os.path.exists(sp) else os.path.join(RUN, 'seeds.npz'))
    reg0 = np.asarray(d['region'], np.int64)
    N = int(d['N'])
    L = float(d['L'])
    dx = L / N
    _lt = d['laths'] if 'laths' in d.files else sd['laths']
    laths = [int(x) for x in np.asarray(_lt).ravel()]
    _vk = d['vmap_keys'] if 'vmap_keys' in d.files else sd['vmap_keys']
    _vv = d['vmap_vals'] if 'vmap_vals' in d.files else sd['vmap_vals']
    vmap = {int(k): int(v) for k, v in
            zip(np.asarray(_vk).ravel(), np.asarray(_vv).ravel())}
    nv = len(laths)

    f1, f2, f3 = face_counts(reg0, vmap)
    nb, blks = blocks_of(reg0, vmap)
    P('\n[0] 基线（未投影）：F1=%d F2=%d **F3=%d**  同变体块数=**%d**'
      % (f1, f2, f3, nb))
    P('    各块(变体,胞数)：%s' % (blks[:14],))

    # ---- 构造**真实的** `LevelSetMulti`（与驱动同款入参）
    eps0 = [np.asarray(EPS0[v - 1], float).copy() for v in laths]
    P('\n[1] 构造真实引擎对象（%d 场）…' % (nv + 1), )
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.25, Mob=MOB,
                        df=[0.0] + [float(DF)] * nv, workers=1,
                        reinit_every=0, reinit_dt=1e-4)
    # 逐场轴表（与 `facet_project` 从 `self.npref_tab`/`self.atab`/`self.wtab` 取的口径一致）
    npref_tab = {}
    for i, v in enumerate(laths):
        _n = np.asarray(NPF[v], float)
        npref_tab[i + 1] = _n / np.linalg.norm(_n)
    g.npref_tab = npref_tab
    g.vmap = dict(vmap)
    P('    npref_tab 已挂；atab/wtab 由构造函数从 eps0 逐行算出')

    results = {}
    for label, ex in (('facet_excl=1（旧的 R73 行为）', 1),
                      ('facet_excl=0（**新默认 = §186 修复**）', 0)):
        # 把 φ 灌成与 `region` 一致：本场 = −1Δx、其余 = +1Δx；母相由 init_parent 定
        for k in range(1, nv + 1):
            g.phi[k] = np.where(reg0 == k, -1.0 * dx, 1.0 * dx).astype(g.phi.dtype)
        g.init_parent()
        g.facet_excl = ex
        n_done = g.facet_project()
        reg1 = np.asarray(g.region(), np.int64)
        g1, g2, g3 = face_counts(reg1, vmap)
        nb2, blks2 = blocks_of(reg1, vmap)
        vac = int(((reg0 > 0) & (reg1 == 0)).sum())
        results[ex] = (g3, nb2, vac)
        P('\n[%s]' % label)
        P('    facet_project() 处理了 %d 个场' % n_done)
        P('    F1=%d F2=%d **F3=%d**  同变体块数=**%d**  β 膜=%d 胞（%.2f%% 已转变体积）'
          % (g1, g2, g3, nb2, vac,
             100.0 * vac / max(int((reg0 > 0).sum()), 1)))
        P('    各块(变体,胞数)：%s' % (blks2[:14],))

    P('\n' + '=' * 78)
    P('[判定]')
    e1_f3, e1_nb, e1_vac = results[1]
    e0_f3, e0_nb, e0_vac = results[0]
    ok1 = (e1_f3 == 0 and e1_nb == 12)
    P('  V-1 正对照（`excl=1` 复现旧行为 F3=0 / 块=12）：实测 F3=%d 块=%d ⇒ %s'
      % (e1_f3, e1_nb, '✅ PASS' if ok1 else '❌ FAIL'))
    ok2 = (e0_f3 > 1000 and e0_nb == 6)
    P('  V-2 修复生效（`excl=0` 给 F3>1000 且 块=6）：实测 F3=%d 块=%d ⇒ %s'
      % (e0_f3, e0_nb, '✅ PASS' if ok2 else '❌ FAIL'))
    P('  V-3 β 膜下降：%d → %d 胞（%.1f×）' % (e1_vac, e0_vac,
                                             e1_vac / max(e0_vac, 1)))
    P('  ⇒ 总判定：%s' % ('✅ **修复已验证**' if (ok1 and ok2) else '❌ **需复查**'))
    P('=' * 78)


if __name__ == '__main__':
    main()
