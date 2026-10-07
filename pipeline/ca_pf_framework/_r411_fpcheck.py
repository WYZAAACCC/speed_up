#!/usr/bin/env python3
"""_r411_fpcheck.py —— ★ **`--facet-proj` 缺陷的独立复核**（把机理变成可算的账）。

`_r410` 实测（`dry_saSet2`，4 个时刻）：
    excl=同变体邻域（**现行代码**）：`t=0` 时 F3 **1169 → 0**，块数 **6 → 12**
    excl=None（R73 之前）        ：`t=0` 时 F3 **1169 → 1195**，块数 **6 → 6**
⇒ 现行 `excl` 把块内低角界面**全部**抹掉。

本脚本要**独立复核机理**，不接受"看起来像"，而是要**算账对上**：

  【假设 H1】`excl` 把取跨度的点云沿 F3 法向内缩 `pad` 层，
             但**体积靶 `tgt` 仍是整个体** ⇒ 缩放因子 `s = (tgt/vp)^(1/3) > 1`
             ⇒ 盒子**各向同性放大** ⇒ 沿 `a`/`w` 侵入邻场。
  【假设 H2】盒子互相侵入 ⇒ 并集覆盖不满原来的体 ⇒ **未被任何盒子覆盖的胞 = β 膜**。
             定量：`β 膜胞数 ≈ Σ_{i<j} |box_i ∩ box_j|`（重叠体积）。

判据（**三条都要过**才算复核成立）：
  P-1  正对照：算子在解析长方体上幂等（`s=1`、体积不变）。
  P-2  `excl` 下 `s` 的中位数 **> 1**，`excl=None` 下 **≤ 1**。
  P-3  `β 膜胞数 / 重叠体积` 落在 **[0.5, 2.0]**（同一量级的两个独立算法）。

只在 `t=0`（播种态，无历史污染）上做 —— 这是**唯一**能干净归因的时刻。
"""
import os
import sys
from itertools import combinations

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import windowB_surface as W                                    # noqa: E402
from T16_verify_rve import C, EPS0, NPF                        # noqa: E402
from _r68_facet_op import facet_project_one                    # noqa: E402

PAD = 2


def P(s):
    print(s, flush=True)


def axes_tables(laths):
    npref, atab, wtab = {}, {}, {}
    for i, v in enumerate(laths):
        k = i + 1
        E = np.asarray(EPS0[v - 1], float)
        nref, _, _ = W.argmin_normal_cached(C, E)
        R = W.LevelSetMulti._rank1_axes(E, nref)
        _n = np.asarray(NPF[v], float)
        npref[k] = _n / np.linalg.norm(_n)
        atab[k] = np.asarray(R[1], float) / np.linalg.norm(np.asarray(R[1], float))
        wtab[k] = np.asarray(R[2], float) / np.linalg.norm(np.asarray(R[2], float))
    return npref, atab, wtab


def selftest_box():
    N, dx = 48, 62.5e-9
    ii = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(ii, ii, ii, indexing='ij')
    c = np.array([0.5, 0.5, 0.5]) * N * dx
    h = np.array([10.0, 6.0, 4.0]) * dx
    pr = np.stack([X - c[0], Y - c[1], Z - c[2]], -1)
    phi = np.max(np.abs(pr) - h[None, None, None, :], -1)
    v0 = int((phi < 0).sum())
    ph2, info = facet_project_one(phi, dx, (np.eye(3)[2], np.eye(3)[0], np.eye(3)[1]))
    v1 = int((ph2 < 0).sum())
    ok = (v1 == v0 and abs(info.get('s', 0) - 1.0) < 1e-9)
    P('[P-1] 正对照（解析长方体幂等）：v0=%d v1=%d s=%.8f ⇒ %s'
      % (v0, v1, info.get('s', float('nan')), '✅ PASS' if ok else '❌ FAIL'))
    return ok


def run_case(RUN, STEP):
    snap = os.path.join(RUN, 'snap_%05d.npz' % STEP)
    sd = np.load(os.path.join(RUN, 'seeds.npz'))
    d = np.load(snap if os.path.exists(snap) else os.path.join(RUN, 'seeds.npz'))
    reg = np.asarray(d['region'], np.int64)
    N = int(d['N'])
    dx = float(d['L']) / N
    _lt = d['laths'] if 'laths' in d.files else sd['laths']
    laths = [int(x) for x in np.asarray(_lt).ravel()]
    _vk = d['vmap_keys'] if 'vmap_keys' in d.files else sd['vmap_keys']
    _vv = d['vmap_vals'] if 'vmap_vals' in d.files else sd['vmap_vals']
    vmap = {int(k): int(v) for k, v in
            zip(np.asarray(_vk).ravel(), np.asarray(_vv).ravel())}
    npref, atab, wtab = axes_tables(laths)

    P('')
    P('=' * 78)
    P('复核用例：%s  step=%d   N=%d  Δx=%.2f nm' % (RUN, STEP, N, dx * 1e9))
    P('  laths=%s' % laths)
    P('=' * 78)
    body = {k: (reg == k) for k in npref}
    n_tot = sum(int(v.sum()) for v in body.values())
    P('[0] 基线：已转变胞 %d；各场胞数 %s'
      % (n_tot, [int(body[k].sum()) for k in sorted(body)]))

    for label, use_excl in (('excl=None（R73 之前）', False),
                            ('excl=同变体邻域（现行）', True)):
        P('')
        P('-' * 78)
        P('[%s]' % label)
        box = {}
        svals = {}
        for k in sorted(npref):
            phi_k = np.where(reg == k, -1.0 * dx, 1.0 * dx)
            excl = None
            if use_excl:
                vk = vmap.get(k)
                other = np.zeros_like(reg, bool)
                for k2, v2 in vmap.items():
                    if int(v2) == int(vk) and int(k2) != k:
                        other |= (reg == int(k2))
                if other.any():
                    import scipy.ndimage as _ndi
                    excl = _ndi.binary_dilation(other, iterations=PAD)
            ph, info = facet_project_one(phi_k, dx, (npref[k], atab[k], wtab[k]),
                                         excl=excl)
            if info.get('ok'):
                box[k] = (ph < 0)
                svals[k] = float(info['s'])
                # 盒子在 n* 上的跨度（用于看"沿 F3 法向"的变化）
        s_arr = np.array(sorted(svals.values()))
        P('    s（体积标定缩放）: min=%.4f  中位=%.4f  max=%.4f'
          % (s_arr.min(), np.median(s_arr), s_arr.max()))
        P('    s 逐场：%s' % {k: round(svals[k], 4) for k in sorted(svals)})

        # ---- 覆盖 / β 膜
        covered = np.zeros_like(reg, bool)
        for k, m in box.items():
            covered |= m
        vac = int(((reg > 0) & (~covered)).sum())

        # ---- 盒子两两重叠体积（**独立算法**，不看 region）
        ov = 0
        ks = sorted(box)
        for a, b in combinations(ks, 2):
            ov += int((box[a] & box[b]).sum())
        vbox = sum(int(m.sum()) for m in box.values())
        P('    Σ|box| = %d（Σ|body| = %d）⇒ 盒子总体积/体总体积 = %.4f'
          % (vbox, n_tot, vbox / max(n_tot, 1)))
        P('    Σ_{i<j}|box_i∩box_j|（**重叠**）= %d' % ov)
        P('    ★ **β 膜**（已转变但未被任何盒子覆盖）= %d' % vac)
        ratio = vac / max(ov, 1)
        P('    ⇒ β膜 / 重叠 = **%.3f**  ⇒ %s'
          % (ratio, '✅ 两法一致（H2 成立）' if 0.5 <= ratio <= 2.0
             else '❌ 两法不一致（H2 需重审）'))
        # ---- F3 保留
        c3 = 0
        for dd in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            for k in ks:
                nb = np.roll(reg, dd, axis=(0, 1, 2))
                for k2 in ks:
                    if k2 != k and _same(vmap, k, k2):
                        pass
        P('    （F3 面数见 `_r410`，本脚本只算账）')
    P('=' * 78)


def _same(vmap, a, b):
    return vmap.get(a) == vmap.get(b)


if __name__ == '__main__':
    ok = selftest_box()
    runs = sys.argv[1:] or ['_exp/_bk_mb/dry_saSet2']
    for r in runs:
        try:
            run_case(r, 0)
        except Exception as e:
            P('✗ %s 复核失败：%r' % (r, e))
    P('\n总判定（P-1 正对照）：%s' % ('✅ PASS' if ok else '❌ FAIL'))
