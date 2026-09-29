#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_bk_pair.py —— **成对界面记账**：每一对同变体板条之间到底有多少 F3 接触面积，
以及每根板条的**自由宽面**（朝向母相 β）有多大。

## 为什么必须要这一项

`nf3_col`（柱剖面里 α′ 段数 − 1）**不能证明相邻**：两段之间夹一层母相 β 时
它照样给 `M-1`（`_bk_measure` 的 docstring 早就写了这条）。所以"6 根被 5 张 F3
界面分开"这句话，**只有 `f3_area` 能支撑**。

而 `dry_gs2`（长出来的块，N=96）末态给出
  `f3_faces=1787`、`f3_area=4.4099 µm²`
按几何预期：5 张宽面 × (619 nm × 2520 nm) = **7.80 µm²** ⇒ 实测只有 **57%**。
两种可能，必须分开：
  (a) **生长堆叠留下了 β 夹层** —— 后形核的核没真正贴上前一块 ⇒ **物理问题**；
  (b) 宽面尺寸/法向读错 ⇒ **量具问题**。
本脚本用**逐对**面积 + **每根板条朝母相的暴露面积**把两者分开：
  若 (a)，则"朝母相的面积"会显著大于两个端面应有的量，且缺的面积
  正好等于缺失的 F3 面积。

## 面积估计器

`A_ij = Δx² · Σ_α f_α |n_α|`（Cauchy 无偏估计；`f_α` = 沿 α 方向跨界的格面数）。
自检：对法向 `n` 的平面，`f_α = A|n_α|/Δx²` ⇒ `Σ f_α|n_α| = A/Δx²` ✔

用法: python3 _bk_pair.py <dir> [step] [--laths]
"""
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _bk_measure as BM                                        # noqa: E402


def face_counts(mi, mj):
    """沿 3 个轴向、两个符号的跨界面格面数（每张面只数一次）。"""
    f = np.zeros(3, np.int64)
    for axx in (0, 1, 2):
        for sh in (1, -1):
            f[axx] += int((mi & np.roll(mj, sh, axis=axx)).sum())
    return f


def area_from_faces(f, n_hab, dx):
    return float((f * np.abs(np.asarray(n_hab, float))).sum()) * dx ** 2


def main():
    d = sys.argv[1]
    if not os.path.isabs(d):
        d = os.path.join(HERE, d)
    verbose = '--laths' in sys.argv
    step = next((int(x) for x in sys.argv[2:] if x.isdigit()), None)
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    if step is not None:
        snaps = [s for s in snaps if ('%05d' % step) in s]
    if not snaps:
        print('没有匹配的快照:', d)
        return 1

    for s in snaps:
        z = np.load(s)
        reg = z['region']
        N = reg.shape[0]
        L = float(z['L'])
        dx = L / N
        n_hab = np.asarray(z['n_hab'], float)
        vmap = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
        laths = sorted(vmap)
        M = len(laths)
        masks = {k: (reg == k) for k in laths}
        parent = (reg == 0)
        vol = {k: int(masks[k].sum()) for k in laths}
        print('=' * 100)
        print('%s  step=%d  N=%d  dx=%.2f nm' % (os.path.basename(s), int(z['step']),
                                                 N, dx * 1e9))

        # ---------- 每根板条：朝母相暴露的面积 ----------
        print('  %-8s %-9s %-10s %-10s %-8s %s'
              % ('板条', '体素', 'V(µm³)', '朝β面积', '等效厚度', '来源分解'))
        tot_beta = 0.0
        thick = {}
        for k in laths:
            if vol[k] == 0:
                print('  %-8d %-9d %-10s %-10s %-8s %s'
                      % (k, 0, '0', '—', '—', '**空场**'))
                continue
            fb = face_counts(masks[k], parent)
            Ab = area_from_faces(fb, n_hab, dx)
            tot_beta += Ab
            V = vol[k] * dx ** 3
            # 等效厚度 = V / (宽面面积)；宽面面积用**体积/厚度**反解太循环，
            # 这里用"朝 β 的面积"做参考量，另给 V 和逐轴尺寸
            e = {}
            for nm, ax in (('n', n_hab), ('w', z['w_ax']), ('a', z['a_ax'])):
                e[nm] = BM._linear_extent(masks[k], np.asarray(ax, float), dx)[0]
            thick[k] = e['n']
            print('  %-8d %-9d %-10.4f %-10.4f %-8.0f n/w/a=%.0f/%.0f/%.0f nm  '
                  '朝β面(法向分解 %d/%d/%d)'
                  % (k, vol[k], V * 1e18, Ab * 1e12, e['n'] * 1e9,
                     e['n'] * 1e9, e['w'] * 1e9, e['a'] * 1e9,
                     fb[0], fb[1], fb[2]))

        # ---------- 逐对 F3 ----------
        # ★ 除了面积，还算**接触斑的质心与足迹**：用来分清"接触不全"是
        #   (i) 沿 n* 留了 β 夹层（面积小、但足迹仍对齐），还是
        #   (ii) 横向（w/a）错位（接触斑挤在一边、足迹质心偏移）。
        print('  逐对 F3（面积用无偏估计；足迹=接触斑与两板条自身在 (w,a) 平面的质心）：')
        w_ax = np.asarray(z['w_ax'], float)
        a_ax = np.asarray(z['a_ax'], float)
        tot_f3 = 0.0
        f3_of = {}
        for ii, i in enumerate(laths):
            for j in laths[ii + 1:]:
                if vmap[i] != vmap[j] or vol[i] == 0 or vol[j] == 0:
                    continue
                f = face_counts(masks[i], masks[j])
                A = area_from_faces(f, n_hab, dx)
                tot_f3 += A
                f3_of[tuple(sorted((i, j)))] = A
                # 接触格：mi 的格且沿某方向邻 mj
                ctset = np.zeros(reg.shape, bool)
                for axx in (0, 1, 2):
                    for sh in (1, -1):
                        ctset |= (masks[i] & np.roll(masks[j], sh, axis=axx))
                if ctset.any():
                    cidx = np.argwhere(ctset)
                    cxyz = (cidx.mean(0) + 0.5) * dx
                    c_w = float(cxyz @ w_ax) * 1e9
                    c_a = float(cxyz @ a_ax) * 1e9
                    # 板条自身足迹质心
                    iidx = np.argwhere(masks[i])
                    jidx = np.argwhere(masks[j])
                    ixyz = (iidx.mean(0) + 0.5) * dx
                    jxyz = (jidx.mean(0) + 0.5) * dx
                    print('    %d-%d: 面 %5d/%5d/%5d  面积=%.4f µm²  接触斑质心 '
                          'w/a=%+7.1f/%+7.1f | 板条质心 w/a: %d=%+7.1f/%+7.1f '
                          '%d=%+7.1f/%+7.1f  Δ(%d−%d)=%+6.1f/%+6.1f nm'
                          % (i, j, f[0], f[1], f[2], A * 1e12, c_w, c_a,
                             i, float(ixyz @ w_ax) * 1e9, float(ixyz @ a_ax) * 1e9,
                             j, float(jxyz @ w_ax) * 1e9, float(jxyz @ a_ax) * 1e9,
                             j, i,
                             (float(jxyz @ w_ax) - float(ixyz @ w_ax)) * 1e9,
                             (float(jxyz @ a_ax) - float(ixyz @ a_ax)) * 1e9))
                else:
                    print('    %d-%d: 面 %5d/%5d/%5d  面积=%.4f µm²  （无接触格）'
                          % (i, j, f[0], f[1], f[2], A * 1e12))

        # ---------- 几何参照：每根宽面面积（用 V/厚度）----------
        # ★ 记账：n 根板条共 2n 张宽面；其中 2 张是端面（朝 β），2(n−1) 张成对
        #   拼成 (n−1) 张内部界面 ⇒ **内部界面总面积 = ΣA_宽面 · (n−1)/n**。
        print('  几何参照（只吃体素数与厚度，与法向/面无偏估计量具无关）：')
        tot_broad = 0.0
        for k in laths:
            if vol[k] == 0 or thick.get(k, 0) <= 0:
                continue
            tot_broad += (vol[k] * dx ** 3) / thick[k]
        n_occ = sum(1 for k in laths if vol[k] > 0)
        exp_int = tot_broad * (n_occ - 1) / n_occ if n_occ else 0.0
        print('     Σ 单根宽面面积 = %.4f µm²（%d 根）⇒ %d 张内部界面应占 '
              '%.4f µm²（端面另占 %.4f µm²）'
              % (tot_broad * 1e12, n_occ, max(n_occ - 1, 0), exp_int * 1e12,
                 (tot_broad - exp_int) * 1e12))
        print('     实测 Σ F3 面积 = %.4f µm²   实测 Σ 朝β面积 = %.4f µm²'
              % (tot_f3 * 1e12, tot_beta * 1e12))
        if exp_int > 0:
            print('     ⇒ F3 覆盖率 = 实测/应占 = **%.3f**' % (tot_f3 / exp_int))

        # ---------- ★ 沿 n* 的一维堆叠剖面（决定性）----------
        # 板条是**平行平板** ⇒ 沿 n* 的一维投影就完全决定"重叠 / 留缝"。
        # 用 0.5%/99.5% 分位而非 min/max：场 1 有 1–2 体素的孤儿会污染 min/max
        # （实测把 2869 nm 的板条拉成 5722 nm）。
        print('  ★ 沿 n* 的一维堆叠剖面（每根板条去掉 <32 体素的孤儿分量后再投影）：')
        from scipy import ndimage as _ndi
        st = np.zeros((3, 3, 3), bool)
        st[1, 1, 1] = st[0, 1, 1] = st[2, 1, 1] = True
        st[1, 0, 1] = st[1, 2, 1] = st[1, 1, 0] = st[1, 1, 2] = True
        rows = []
        for k in laths:
            if vol[k] == 0:
                continue
            m = masks[k]
            lab, n = _ndi.label(m, structure=st)
            if n > 1:
                sz = np.bincount(lab.ravel())
                sz[0] = 0
                keep = int(np.argmax(sz))
                m = (lab == keep)
            idx = np.argwhere(m)
            p = ((idx[:, 0] + 0.5) * n_hab[0] + (idx[:, 1] + 0.5) * n_hab[1]
                 + (idx[:, 2] + 0.5) * n_hab[2]) * dx
            q = np.percentile(p, [0.5, 50, 99.5])
            rows.append((k, q, len(idx)))
        rows.sort(key=lambda t: t[1][1])
        prev = None
        for k, q, nv in rows:
            gap = '' if prev is None else (
                '  ← 与上一片的**间隙 %+6.1f nm**（负=重叠）' % ((q[0] - prev) * 1e9))
            print('    板条%-2d  n* 投影: 0.5%%=%+8.1f  中位=%+8.1f  99.5%%=%+8.1f nm'
                  '  厚度≈%5.1f nm  (%d 体素)%s'
                  % (k, q[0] * 1e9, q[1] * 1e9, q[2] * 1e9,
                     (q[2] - q[0]) * 1e9, nv, gap))
            prev = q[2]
        # 相邻片之间的母相 β 夹层（直接数"夹在两者之间的场 0 体素"）
        # ★★ 第一版这里写错了：写的是 `parent & roll(gi, sh) & roll(gj, sh)` ——
        #   同一个 sh 要求**两侧同向**都是 i/j，于是完全漏掉真正的夹心构型
        #   （i 在 c+ê、j 在 c−ê，β 夹在中间）⇒ 15 对全部报"无 β 夹层"，是**假阴性**。
        #   正确判据：β 体素 c，其 6 邻域里**同时**存在场 i 和场 j 的体素。
        print('  ★ 相邻片之间的母相 β 夹层（数"6 邻域里同时挨着 i 和 j 的场 0 体素"）：')
        nbi = {}
        for k in laths:
            if vol[k] == 0:
                continue
            t = np.zeros(reg.shape, bool)
            for axx in (0, 1, 2):
                for sh in (1, -1):
                    t |= np.roll(masks[k], sh, axis=axx)
            nbi[k] = t
        pair_ab = []
        for a1 in range(len(rows)):
            for b1 in range(a1 + 1, len(rows)):
                i, j = rows[a1][0], rows[b1][0]
                if vmap[i] != vmap[j]:
                    continue
                tot = int((parent & nbi[i] & nbi[j]).sum())
                if tot:
                    # ★ 键必须归一化：`f3_of` 是在 `for i, for j>i`（数字序）里
                    #   建的，而这里 i/j 来自**沿 n* 排序**的 rows ⇒ 键会是 (5,3) 这种
                    #   逆序。不排序的话 `.get` 静默返回 0.0，β 占比被读成 1.00
                    #   （第一版实测正是 (5,3)、(3,1) 两对误报 1.00）。
                    pair_ab.append((tuple(sorted((i, j))),
                                    f3_of.get(tuple(sorted((i, j))), 0.0),
                                    tot * dx ** 2))
                    m = (parent & nbi[i] & nbi[j])
                    bi = np.argwhere(m)
                    bxyz = (bi.mean(0) + 0.5) * dx
                    bw = float(bxyz @ np.asarray(z['w_ax'], float)) * 1e9
                    ba = float(bxyz @ np.asarray(z['a_ax'], float)) * 1e9
                    bn = float(bxyz @ n_hab) * 1e9
                    # 该 β 夹层在 (w,a) 平面上的**足迹跨度**：若与板条同量级
                    # ⇒ 是整片薄膜；若只是一条窄带 ⇒ 是边缘/棱上的效应
                    idx_m = bi
                    e_w = (np.ptp(idx_m @ np.asarray(z['w_ax'], float))
                           + dx * np.abs(z['w_ax']).sum()) * 1e9
                    e_a = (np.ptp(idx_m @ np.asarray(z['a_ax'], float))
                           + dx * np.abs(z['a_ax']).sum()) * 1e9
                    e_n = (np.ptp(idx_m @ n_hab) + dx * np.abs(n_hab).sum()) * 1e9
                    print('    %d | %d: 夹层 β 体素 = %-4d 当量 %.4f µm²  '
                          '质心 n/w/a=%+7.1f/%+7.1f/%+7.1f  足迹跨度 n/w/a'
                          '=%.0f/%.0f/%.0f nm'
                          % (i, j, tot, tot * dx ** 2 * 1e12, bn, bw, ba,
                             e_n, e_w, e_a))
                else:
                    print('    %d | %d: 无 β 夹层' % (i, j))

        # ---------- V-7 / V-7b：界面完整性（**预登记**，阈值由对照校准）------
        # ★ 计算全部走 `_bk_measure.snapshot_coverage`（**单一实现**），这里只打印。
        #   今天已经在"两份实现悄悄分叉"上栽过两次（β 夹层判据假阴性、
        #   `pair_ab` 键序不一致），不再复制第二份判据实现。
        cv = BM.snapshot_coverage(z)
        if cv['exp_int'] > 0:
            print('     V-7  界面完整性（F3 覆盖率 ≥ 0.85）  %s  覆盖率=%.3f '
                  '（应占 %.4f，实测 %.4f µm²）'
                  % ('PASS' if cv['cov'] >= 0.85 else '**FAIL**', cv['cov'],
                     cv['exp_int'] * 1e12, cv['f3_area'] * 1e12))
            if cv['beta_frac']:
                w = cv['worst']
                print('     V-7b 无多余 β 夹层（每对 β 占该对界面 ≤ 0.25）  %s  '
                      '最差对 %d|%d 的 β 占比=%.3f   各对: %s'
                      % ('PASS' if cv['beta_frac'][w] <= 0.25 else '**FAIL**',
                         w[0], w[1], cv['beta_frac'][w],
                         '  '.join('%d|%d:%.2f' % (ij[0], ij[1], f)
                                   for ij, f in sorted(cv['beta_frac'].items(),
                                                       key=lambda t: -t[1]))))
            else:
                print('     V-7b 无多余 β 夹层  —  本快照没有任何 β 夹层')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
