#!/usr/bin/env python3
"""_r412_fpgap.py —— ★ **`--facet-proj` 缺陷：把"缝"量出来**（修正后的机理，可证伪）。

## 背景（诚实记账）
`_r411` 的 **H1 被自己的数据否证**：我原以为 `s = (tgt/vp)^(1/3) > 1`（盒子被放大）。
实测 `s ≈ 0.93–1.00`，**恒 < 1**（盒子总是**缩小**到体积靶）。
但 `_r411` 同时给出两条**硬事实**：
  * `excl=None`：盒子两两重叠 266–272 胞，β 膜 135–192 胞（**同一量级**）；
  * `excl`（现行）：盒子两两重叠 **恒为 0**，β 膜 **1447–1451 胞**（**大 7.6 倍**）。
⇒ β 膜**不是**重叠造成的（现行路径根本没有重叠）。那它是**缝**。

## 修正后的机理（**本脚本要证的**）
`excl` = "与同变体另一个场相邻的胞"膨胀 `pad=2` 层。
对堆叠中的一根板条，这正好是它**朝 F3 那一侧**的最外 2 层胞。
于是 `lo/hi` 在那**唯一一侧**被内缩 `2Δx`；而 `tgt = body.sum()` **没变**，
`s < 1` 又让它再缩一点 ⇒
    **盒子的 F3 侧面退到体之外 ⇒ 相邻两场的盒子之间张开一条缝**
    ⇒ 缝里的胞对所有 `k≥1` 都 `φ_k > 0`，
      而 `φ_0 = −min_k φ_k`（`init_parent`）在缝里**仍然 < 0**（投影**不更新 φ_0**）
    ⇒ `argmin` 判 `region = 0` ⇒ **β 膜**。

## 判据（三条，全过才算机理成立）
  **P-1 正对照**：解析长方体上算子幂等（`s=1`、体积不变）。**先过这条才看别的**。
  **P-2 缝宽**：对每一对同变体相邻板条 `(i, j)`，比较
      `gap_excl  = min(box_j·n*) − max(box_i·n*)`
      `gap_none  = min(box_j·n*) − max(box_i·n*)`（`excl=None`）
      以及投影前 `gap_body = min(body_j·n*) − max(body_i·n*)`（应为 ≈ 0，即"贴着"）。
      判据：`gap_excl` 显著大于 `gap_body`，且 `gap_none ≤ gap_excl`。
  **P-3 缝就是 β 膜**：β 膜胞的 `n*` 投影**落在缝区间的比例 ≥ 0.8**。
      若成立 ⇒ 缝与 β 膜是**同一个东西**，机理闭合。

⚠ 只在 `t=0`（播种态）上做 —— 唯一没有历史污染的时刻。
"""
import os
import sys

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


def main():
    RUN = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mb/dry_saSet2'
    STEP = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    P('=' * 78)
    P('_r412 —— `--facet-proj` 的"缝"直测（修正机理）')
    P('  用例 %s  step=%d' % (RUN, STEP))
    P('=' * 78)
    ok_pos = selftest_box()

    sd = np.load(os.path.join(RUN, 'seeds.npz'))
    sp = os.path.join(RUN, 'snap_%05d.npz' % STEP)
    d = np.load(sp if os.path.exists(sp) else os.path.join(RUN, 'seeds.npz'))
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

    ii = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(ii, ii, ii, indexing='ij')
    XYZ = np.stack([X, Y, Z], -1)

    body = {k: (reg == k) for k in npref}
    n_tot = int((reg > 0).sum())

    # ---- 同变体的相邻场对（就是每个块内的板条对）
    pairs = []
    for v in sorted(set(vmap.values())):
        ks = sorted(k for k, vv in vmap.items() if vv == v)
        for a, b in zip(ks[:-1], ks[1:]):
            pairs.append((a, b, v))
    P('\n[1] 同变体相邻对（块内板条对）：%s'
      % ', '.join('(场%d,场%d,V%d)' % t for t in pairs))

    res = {}
    for label, use_excl in (('excl=None', False), ('excl（现行）', True)):
        box = {}
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
        res[label] = box

    P('\n[2] 每对同变体板条：沿 **n\\*** 的"贴合 / 缝"（单位：胞 = Δx）')
    P('    %-6s %-6s | %-28s | %-28s' % ('场i', '场j',
                                          'gap_body（投影前）', 'gap_box（投影后）'))
    gaps = {}
    for label, box in res.items():
        gl = []
        for a, b, v in pairs:
            u = npref[a]                     # 同变体 ⇒ 两场 n* 相同
            pa = XYZ[body[a]] @ u
            pb = XYZ[body[b]] @ u
            g_body = (pb.min() - pa.max()) / dx
            qa = XYZ[box[a]] @ u
            qb = XYZ[box[b]] @ u
            g_box = (qb.min() - qa.max()) / dx
            gl.append((a, b, g_body, g_box))
        gaps[label] = gl
    for i, (a, b, v) in enumerate(pairs):
        gb = gaps['excl=None'][i][2]
        gn = gaps['excl=None'][i][3]
        ge = gaps['excl（现行）'][i][3]
        P('    %-6d %-6d | body gap = %+7.2f 胞        | none: %+7.2f 胞   '
          'excl: %+7.2f 胞' % (a, b, gb, gn, ge))
    gn_arr = np.array([t[3] for t in gaps['excl=None']])
    ge_arr = np.array([t[3] for t in gaps['excl（现行）']])
    gb_arr = np.array([t[2] for t in gaps['excl=None']])
    P('    中位：body %+.2f 胞 | excl=None %+.2f 胞 | excl（现行）%+.2f 胞'
      % (np.median(gb_arr), np.median(gn_arr), np.median(ge_arr)))
    ok_gap = bool(np.median(ge_arr) > np.median(gb_arr) + 0.5
                  and np.median(gn_arr) <= np.median(ge_arr) + 1e-9)
    P('    ⇒ P-2（excl 张开缝、none 不张开）：%s' % ('✅ PASS' if ok_gap else '❌ FAIL'))

    P('\n[3] 缝与 β 膜是不是同一个东西？（P-3）')
    ok_p3_all = True
    for label, box in res.items():
        covered = np.zeros_like(reg, bool)
        for m in box.values():
            covered |= m
        vac = (reg > 0) & (~covered)
        nvac = int(vac.sum())
        if nvac == 0:
            P('    %-12s：β 膜 0 胞 ⇒ **不适用**' % label)
            continue
        # 每个 β 膜胞：到"同变体界面"的 n* 向位置，是否落在该对的缝区间内
        # ★★ 自纠错（**本脚本第一版的 #1 号错误**）：原写
        #     `lo = pa.max() + g_box*dx`，而 `g_box*dx = qb.min() − qa.max()`
        #     ⇒ 化简后 `lo = qb.min()`，再与 `hi = pb.min()` 比
        #     ⇒ 因盒子比体**内缩**（`qb.min() > pb.min()`）而**恒有 hi < lo ⇒ continue**
        #     ⇒ 分母不为 0 而分子恒 0，报出 **0.0%** 的假阴性。
        #   正确的缝区间 = 场 i 的盒子**末端** → 场 j 的盒子**起端**：`[qa.max(), qb.min()]`。
        in_gap = 0
        for (a, b, v), (_, _, g_body, g_box) in zip(pairs, gaps[label]):
            u = npref[a]
            qa = XYZ[box[a]] @ u
            qb = XYZ[box[b]] @ u
            lo, hi = qa.max(), qb.min()
            if hi <= lo:
                continue
            pv = XYZ[vac] @ u
            in_gap += int(np.count_nonzero((pv >= lo) & (pv <= hi)))
        frac = in_gap / max(nvac, 1)
        P('    %-12s：β 膜 %d 胞，其中 **%.1f%%** 落在"缝区间"内 ⇒ %s'
          % (label, nvac, 100 * frac,
             '✅ 缝≡β膜' if frac >= 0.8 else '⚠ 部分重合'))
        if label.startswith('excl（') and frac < 0.8:
            ok_p3_all = False

    P('\n' + '=' * 78)
    P('总判定：P-1 %s | P-2 %s | P-3 %s'
      % ('✅' if ok_pos else '❌', '✅' if ok_gap else '❌',
         '✅' if ok_p3_all else '❌'))
    P('=' * 78)


if __name__ == '__main__':
    main()
