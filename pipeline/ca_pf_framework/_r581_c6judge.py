#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_c6judge.py --- 任务(5) 的 **C1–C6 判读器**（goal §(18)）。

## 数据源（都在 `_exp/_bk_p2/dry_<tag>/`）
| 文件 | 提供 |
|---|---|
| `series.csv` | 逐步读数（`nslab_n`/`nf3_col`/`nf2`/`Vt`/`r_selfac`/`E_el_J` …） |
| `snap_<step>.npz` | `region`(N,N,N) int16 + `vmap_keys/vals` + 惯习面标架 `n_hab/a_ax/w_ax` |
| `meta.json` | 全部 CLI 实参（**口径可追溯**） |
| `nuc_dbg.json` | 形核诊断（**跑完才有**；C1 需要） |

## ★★ 量具纪律（goal 硬要求）：先过**解析已知答案**的自检
在**合成的** `region` 上放一个**已知尺寸**的长方体，再量它的三向尺寸
⇒ 必须与解析值**逐位一致**。**自检不过，下面的数一个都不许用。**

## 判据（逐条对应 goal §(18)）
* **C2** 单根几何：沿 `(n_hab, a_ax, w_ax)` 的三个尺寸 = **(厚, 长, 宽)**；
  报**长宽比 / 长厚比**；⚠ 与文献带的对照**必须给出出处**，没有就标【未核实】。
* **C3** 多根堆叠：`series.csv` 的 `nf3_col == nslab_n − 1`（逐行）；
  **面积级完整性**需要 S4 修复臂对照（本脚本给出两臂的对照表）。
* **C5** 填满：`region>0` 的**体积分数**（可从快照直接数）—— 与 `Vt/V0` **交叉核对**；
  **双口径**都报（220–450 根 / 30% 体积分数）。
* **C6** 自协调：`r_selfac` 的实测值 vs **随机取向对照**（把"变体↔体积分数"随机重排
  的零模型，做**置换检验**）⇒ 给出**排除人为来源**的论证。
* **C1** 随机形核：需要 `nuc_dbg.json`；缺失就明确标 **待跑完**。
"""
import json
import os
import sys

import numpy as np
from scipy import ndimage

R = '_exp/_bk_p2'
EPS0 = None
NPF = None


# ---------------------------------------------------------------- 量具自检
def selftest():
    """★ 先过解析已知答案：合成一个 20×40×10 胞的长方体，量出来的三向尺寸必须逐位一致。"""
    L = ['  ── 量具自检（解析已知答案）──']
    ok = True
    N = 64
    d = 62.5e-9
    # 沿 (x,y,z) 放一个 20×40×10 的盒子
    reg = np.zeros((N, N, N), np.int16)
    reg[10:30, 5:45, 20:30] = 1
    axes = {'x': np.array([1.0, 0, 0]), 'y': np.array([0, 1.0, 0]),
            'z': np.array([0, 0, 1.0])}
    ext = extents_of(reg, 1, axes['x'], axes['y'], axes['z'], d)
    exp = {'thick(沿n_hab=x)': 20 * d, 'len(沿a_ax=y)': 40 * d,
           'wid(沿w_ax=z)': 10 * d}
    for k, want in exp.items():
        got = ext[k]
        good = abs(got - want) < 1e-18
        ok &= good
        L.append('    %-22s 解析=%9.4f nm  实测=%9.4f nm  %s'
                 % (k, want * 1e9, got * 1e9, '✅' if good else '❌'))
    L.append('    ⇒ 自检：%s' % ('✅ PASS（下面的数才可用）' if ok else '❌ FAIL ⇒ 不许用下面的数'))
    # 负对照：把一个方向的尺寸改 1 胞，必须量出不同的值
    reg2 = np.zeros((N, N, N), np.int16)
    reg2[10:30, 5:45, 20:31] = 1          # z 厚 11 而不是 10
    ext2 = extents_of(reg2, 1, axes['x'], axes['y'], axes['z'], d)
    nc_ok = abs(ext2['wid(沿w_ax=z)'] - 11 * d) < 1e-18
    L.append('    负对照（z 改 11 胞）：解析=%9.4f nm 实测=%9.4f nm ⇒ %s'
             % (11 * d * 1e9, ext2['wid(沿w_ax=z)'] * 1e9,
                '✅ 有分辨力' if nc_ok else '❌ **判据失效**'))
    ok &= nc_ok
    return ok, L


def extents_of(reg, v, n_hab, a_ax, w_ax, dx):
    """场 `v` 的**最大连通分量**的三向尺寸（胞数 × dx）。

    ★★★ **第一版是错的（留痕）**：它直接对 `reg == v` 的**全部**胞求包围盒。
    在 `p2_b5` 上这给出「场 1 = 1187 × 7447 × 1432 nm ⇒ 12.66 µm³」——
    **比全盒总体积 `Vt` = 2.37 µm³ 还大** ⇒ 数字自己就不自洽（这正是
    AGENTS §7.5 **P13**「结论荒谬要先怀疑量具」那条）。

    **真相**（`_r581_frag.py` 实测）：**场是碎的** ——
    场 1 有 **3 个连通分量**（最大 1021 胞）、场 4 有 **12 个**。
    按场求包围盒量到的是「**碎片云的包络**」，不是一根板条。

    ⇒ 修法：先 `ndimage.label` 取**最大分量**再量。
    ⚠ 仍留一条记账：**分量数会一起报出来**，让"这个场是不是碎的"变成落盘数字。
    """
    m = (reg == v)
    if not m.any():
        return {'thick(沿n_hab=x)': 0.0, 'len(沿a_ax=y)': 0.0,
                'wid(沿w_ax=z)': 0.0, 'n_vox': 0, 'ncomp': 0}
    lab, n = ndimage.label(m)
    if n > 1:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        big = int(np.argmax(sizes)) + 1
        idx = np.argwhere(lab == big)
    else:
        idx = np.argwhere(m)
    p = (idx.astype(float) + 0.5) * dx
    out = {}
    for nm, ax in (('thick(沿n_hab=x)', n_hab), ('len(沿a_ax=y)', a_ax),
                   ('wid(沿w_ax=z)', w_ax)):
        proj = p @ (np.asarray(ax, float) / (np.linalg.norm(ax) + 1e-300))
        out[nm] = float(proj.max() - proj.min()) + dx
    out['n_vox'] = int(idx.shape[0])
    out['ncomp'] = int(n)
    return out


# ---------------------------------------------------------------- 主判读
def main():
    tags = sys.argv[1:] or ['p2_b5', 'p2_b3']
    L = ['=' * 100,
         'R581 —— 任务(5) 的 C1–C6 判读（goal §(18)）',
         '=' * 100]
    ok, sub = selftest()
    L += sub
    if not ok:
        print('\n'.join(L))
        print('\n❌ **量具自检不过 ⇒ 拒绝给出下面的判读**')
        return 2
    L.append('')

    for tag in tags:
        d = os.path.join(R, 'dry_' + tag)
        if not os.path.isdir(d):
            L.append('── %s：（目录不存在）' % tag); continue
        meta = json.load(open(os.path.join(d, 'meta.json')))
        ea = meta.get('exp_args', {})
        L.append('=' * 100)
        L.append('★ %s' % tag)
        L.append('  口径（从 `meta.json` 读，不猜）：N=%s  L=%.3f µm  nv=%s  plate=%s'
                 % (meta.get('N'), meta.get('L', 0) * 1e6, meta.get('nv'),
                    meta.get('plate')))
        L.append('    S4  `nuc_overlap_nm`   = %s' % ea.get('nuc_overlap_nm'))
        L.append('    N13 `nuc_periodic_seed`= %s' % ea.get('nuc_periodic_seed'))
        L.append('    B=%s  K=%s  plate_L=%s  gamma0=%s'
                 % (ea.get('nuc_block_target'), ea.get('nuc_fresh_every'),
                    ea.get('plate_L'), ea.get('gamma0')))

        # ---- 找最后一张快照 ----
        snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')])
        if not snaps:
            L.append('  （无快照）'); continue
        sf = os.path.join(d, snaps[-1])
        z = np.load(sf, allow_pickle=True)
        reg = z['region']
        N = int(z['N'])
        dx = float(z['L']) / N
        n_hab, a_ax, w_ax = z['n_hab'], z['a_ax'], z['w_ax']
        vk, vv = z['vmap_keys'], z['vmap_vals']
        vmap = {int(a): int(b) for a, b in zip(vk, vv)}
        step = int(z['step'])
        L.append('  ── 用快照 %s（step=%d）──' % (snaps[-1], step))

        # ---- C5 体积分数（**直接从快照数**）----
        nocc = int((reg > 0).sum())
        fv = nocc / float(N ** 3)
        L.append('  ── C5 填满盒子（**直接从 region 数**）──')
        L.append('     region>0 的胞数 = %d / %d ⇒ **体积分数 = %.4f%%**'
                 % (nocc, N ** 3, 100 * fv))
        pres = np.unique(reg[reg > 0])
        L.append('     出现的场 = %d 个（%s…）' % (len(pres), pres[:12]))
        # 双口径
        pl = meta.get('plate', {})
        # ⚠ 单位：`plate` 里的 L/W/T 是 **nm**（`meta.json` 实测 `{'L': 1000.0, ...}`）
        #   第一版当成米 ⇒ 印出"单根体积 2.5e26 µm³"这种荒谬值。
        #   **"结论荒谬要先怀疑量具"**（AGENTS §7.5 P13）⇒ 已修。
        v1 = (float(pl.get('L', 0)) * 1e-9) * (float(pl.get('W', 0)) * 1e-9) \
            * (float(pl.get('T', 0)) * 1e-9)                    # m³
        Vbox = float(meta.get('L', 1)) ** 3
        L.append('     ⚠ 口径：单根体积 = %.5f µm³（plate L/W/T = %s nm）'
                 % (v1 * 1e18, (pl.get('L'), pl.get('W'), pl.get('T'))))
        L.append('       ⇒ **220 根 = %.2f%%，450 根 = %.2f%%**；'
                 '**30%% = %.0f 根**'
                 % (220 * v1 / Vbox * 100, 450 * v1 / Vbox * 100,
                    0.30 * Vbox / max(v1, 1e-300)))
        L.append('       （引擎自己的横幅口径：单根 0.2550 µm³、30%% 可容 1176 根 —— '
                 '本行应与它一致）')
        L.append('     ⇒ C5 判决：%s'
                 % ('❌ 未达成' if fv < 0.077 else '⚠ 见上'))

        # ---- C2 单根三维几何 ----
        L.append('  ── C2 单根三维几何（**按最大连通分量**，不是按场！）──')
        L.append('     ⚠ 第一版按"场"求包围盒 ⇒ 量到的是碎片云的包络（场 1 报 7.4 µm 长，')
        L.append('       而它其实有 3 个分量、最大分量只有 1.57 µm）⇒ 已修，见 `extents_of` 的说明。')
        L.append('     %-5s %-5s %-6s %-9s %-11s %-11s %-11s %-9s %s'
                 % ('场', '变体', '分量数', '最大胞数', '厚 nm', '长 nm', '宽 nm',
                    '长/厚', '长/宽'))
        rows = []
        for v in pres[:14]:
            e = extents_of(reg, int(v), n_hab, a_ax, w_ax, dx)
            t, ln, wd = (e['thick(沿n_hab=x)'], e['len(沿a_ax=y)'],
                         e['wid(沿w_ax=z)'])
            rows.append((int(v), vmap.get(int(v), -1), e['ncomp'], e['n_vox'],
                         t, ln, wd, ln / max(t, 1e-30), ln / max(wd, 1e-30)))
            L.append('    %-5d %-5d %-6d %-9d %-11.1f %-11.1f %-11.1f %-9.2f %.2f'
                     % (int(v), vmap.get(int(v), -1), e['ncomp'], e['n_vox'],
                        t * 1e9, ln * 1e9, wd * 1e9,
                        ln / max(t, 1e-30), ln / max(wd, 1e-30)))
        if rows:
            ar = np.array([r[8] for r in rows])
            nf = np.array([r[2] for r in rows])
            L.append('     ⇒ 长/宽 中位 **%.2f**（min %.2f, max %.2f）'
                     % (np.median(ar), ar.min(), ar.max()))
            L.append('     ⇒ **分量数 > 1 的场：%d / %d**（最多 %d 个分量）'
                     % (int((nf > 1).sum()), len(nf), int(nf.max())))
            if (nf > 1).any():
                L.append('     ⚠⚠ **场是碎的** —— 这不是量具问题，是**物理/数值事件**'
                         '（板条被切断）。登记为待查。')
            L.append('     ⚠ **与文献带的对照未做** —— 本脚本只报数，'
                     '**判据要另找出处**（【未核实】）')

        # ---- C3 ----
        L.append('  ── C3 多根堆叠（从 series.csv 逐行）──')
        csvp = os.path.join(d, 'series.csv')
        if os.path.exists(csvp):
            with open(csvp) as fh:
                hdr = fh.readline().strip().split(',')
            a = np.genfromtxt(csvp, delimiter=',', names=True)
            if 'nslab_n' in hdr and 'nf3_col' in hdr:
                x = np.atleast_1d(a['nslab_n']).astype(float)
                y = np.atleast_1d(a['nf3_col']).astype(float)
                m = np.isfinite(x) & np.isfinite(y)
                good = (y[m] == x[m] - 1)
                L.append('     `nf3_col == nslab_n − 1`：**%d/%d 行成立** ⇒ %s'
                         % (int(good.sum()), int(m.sum()),
                            '✅' if good.all() else '⚠ 部分行不成立'))
                L.append('     末值 nslab_n=%d  nf3_col=%d' % (x[-1], y[-1]))

        # ---- C6 自协调 + **随机对照** ----
        L.append('  ── C6 涌现自协调：置换检验（**零模型 = 随机重排 变体↔体积**）──')
        try:
            from T16_verify_rve import EPS0 as _E
            Es = []
            for i in range(len(_E)):
                A = np.asarray(_E[i], float)
                Es.append(A - np.trace(A) / 3.0 * np.eye(3))
            scale = float(np.mean([float(np.sqrt(np.sum(e ** 2))) for e in Es]))
            vols = {}
            for v in pres:
                vols[int(v)] = float((reg == v).sum())
            tot = float(sum(vols.values()))
            obs_acc = np.zeros((3, 3))
            for v, n in vols.items():
                obs_acc = obs_acc + (n / tot) * Es[vmap.get(v, 1) - 1]
            obs = float(np.sqrt(np.sum(obs_acc ** 2))) / scale
            vs = sorted({vmap.get(int(v), 1) for v in pres})
            L.append('     `r_selfac`（实测，本快照）= **%.4f**' % obs)
            L.append('     出现的变体集合 = %s' % vs)
            # ★★ 零模型的选择（**第一版错了，留痕**）：
            #   第一版从"**当前盒子里出现的**变体集合"里抽（`rng.choice(vs, ...)`）
            #   ⇒ 那个零模型已经把"选了哪些变体"这件事**当成给定的**了
            #   ⇒ 它检验的只是"体积分配是否随机"，**不是**"变体选择是否自协调"。
            #   正确的零模型必须从 **全部 12 个变体**里抽 ⇒ 它才回答
            #   「弹性能是不是从 12 个可能里挑出了一个自协调的子集」。
            fr = np.array([vols[int(v)] for v in pres], float)
            fr = fr / fr.sum()
            rng = np.random.default_rng(20261002)
            n_all = len(Es)
            for mode in ('all12', 'present'):
                pool = list(range(1, n_all + 1)) if mode == 'all12' else vs
                null = []
                for _ in range(4000):
                    pick = rng.choice(pool, size=len(pres), replace=True)
                    acc = np.zeros((3, 3))
                    for w_, vv_ in zip(fr, pick):
                        acc = acc + w_ * Es[int(vv_) - 1]
                    null.append(float(np.sqrt(np.sum(acc ** 2))) / scale)
                null = np.array(null)
                pv = float((null <= obs).mean())
                L.append('     零模型[%s]：中位 %.4f，5%% 分位 %.4f，min %.4f'
                         % (mode, np.median(null), np.percentile(null, 5), null.min()))
                L.append('       ⇒ p = P(随机 ≤ 实测) = **%.4f** ⇒ %s'
                         % (pv, '✅ 实测**显著低于**随机 ⇒ 自协调是涌现的'
                            if pv < 0.05 else '❌ 与随机**不可区分**'))
                if mode == 'all12':
                    L.append('       ★ **这个才是主判据**（从 12 个变体里抽 ⇒ 检验'
                             '"选择"而不是"分配"）')
            L.append('     ⚠ **排除人为来源的论证**：变体由 `--nuc-*` 的 `var_rule` 选'
                     '（不是人为规定取向）；零模型正是"随机选变体"'
                     '⇒ 只有实测显著更低，才说明是弹性能挑出来的。')

            # ★★★ 最强的判据：**枚举**所有同规模的变体组合，看实测那一组排第几。
            #   ⚠ **第一版有 bug（留痕）**：我写 `zip(fr, comb)`，而 `fr` 有 8 个元素、
            #     `comb` 只有 2 个 ⇒ `zip` **截断** ⇒ 只用了 2 个权重
            #     ⇒ 枚举出来的名次是错的。
            #   ⇒ 修法：**用标准（与权重无关）的表述** —— 候选集合内**等权** 1/k。
            #     这正是"哪些变体组合自协调"这个问题的常规问法。
            #     同时把**观测集合的等权值**算出来做**同口径**比较。
            k = len(vs)
            obs_eq = None
            if k:
                acc0 = np.zeros((3, 3))
                for vv_ in vs:
                    acc0 = acc0 + (1.0 / k) * Es[int(vv_) - 1]
                obs_eq = float(np.sqrt(np.sum(acc0 ** 2))) / scale
            if k <= 4:
                import itertools
                cands = []
                for comb in itertools.combinations(range(1, n_all + 1), k):
                    acc = np.zeros((3, 3))
                    for vv_ in comb:
                        acc = acc + (1.0 / k) * Es[int(vv_) - 1]
                    cands.append((float(np.sqrt(np.sum(acc ** 2))) / scale,
                                  tuple(int(z) for z in comb)))
                cands.sort()
                vals = np.array([r_ for r_, _ in cands], float)
                # ★★ **并列必须处理**（第一版把并列当成了名次 ⇒ "第 1/66" 是假象）：
                #   实测里 [1,5] / [1,11] / [2,7] 的 r 值**到 3 位小数全一样**。
                #   正确统计量 = **P(随机的组合不比实测差)** = #{c: r_c ≤ r_obs}/总数。
                #   这才是"在全部可能性里的分位"。
                r_obs = obs_eq
                n_le = int((vals <= r_obs + 1e-12).sum())
                n_min = int((vals <= vals.min() + 1e-12).sum())
                rank = next((i for i, (r_, c_) in enumerate(cands)
                             if set(c_) == set(vs)), None)
                rr = n_le / len(cands)
                L.append('     ★ **枚举判据（等权；**并列已处理**）**：k=%d ⇒ C(%d,%d)=%d 种组合'
                         % (k, n_all, k, len(cands)))
                L.append('       实测集合 %s 的 r_selfac（等权）= **%.10f**；'
                         '（按实测体积加权）= %.10f'
                         % (vs, obs_eq, obs))
                L.append('       ⇒ **不比实测差的组合数 = %d / %d**（分位 **%.3f**）'
                         % (n_le, len(cands), rr))
                L.append('       达到全局最小 %.10f 的组合数 = **%d**（并列极多 ⇒ '
                         '"名次"本身没意义，必须用上面的分位）'
                         % (vals.min(), n_min))
                L.append('       最好的 3 个：%s'
                         % ' / '.join('%s=%.6f' % (list(c_), r_)
                                      for r_, c_ in cands[:3]))
                L.append('       ⇒ 判据（**预先写死**：分位 ≤ 0.05 才算"选出来了"）：%s'
                         % ('✅ PASS' if rr <= 0.05 else
                            '❌ **FAIL**（分位 %.3f > 0.05）—— **不放宽阈值，照实记 FAIL**'
                            % rr))
                L.append('       ⚠ 记账：**并列极多**（%d/%d 个组合达到全局最小）'
                         '⇒ 只要实测落在"最小档"，分位就会很小 ⇒ '
                         '**这个判据对"选得好不好"的分辨力有限**，'
                         '必须与"零模型 p 值"一起读。' % (n_min, len(cands)))
            else:
                L.append('     （k=%d > 4 ⇒ 枚举组合数太大，只用上面的抽样零模型）' % k)
        except Exception as e:
            L.append('     ⚠ 无法计算：%r' % (e,))

    out = '\n'.join(L)
    print(out)
    open('_w2_r581_c6judge.log', 'w').write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
