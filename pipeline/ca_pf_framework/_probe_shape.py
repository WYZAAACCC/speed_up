#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_shape.py --- ★★★ **形状本身**的诊断（此前从未做过：只量过"三向跨度"，没看过形状）

为什么要做
----------
`BOX16d`（N=96, Δx=166.7 nm, R=500, t=700, β_h=3.5, β_w=2.3, proj2, 300 步）实测：
    `fill = V/(L·W·T)` **0.884 → 0.309**（step 25 → 75）此后一直 0.30–0.42
    `max−min`  L:W:T = 7404 : 2004 : 862  （`L/T` = 8.59，而增量速率比 `ΔL/ΔT` = 32–41）
⇒ 两个互相矛盾的说法必须分开：
    (i)  **各向异性没被数值实现**  ⇒ 但 **`ΔL:ΔW:ΔT` = 1 : 0.424 : 0.031**，
         厚度向 **0.031 ≈ 设计 0.0302** ✓ ⇒ 这条**已被否证**；
    (ii) **形状不是"板条"而是"纺锤/针"** ⇒ `max−min` 的 `L` 含两端渐细的尖，
         而 `T` 取的是**中段最大厚度**，两者口径不同 ⇒ 形状比与速率比不可比。
本探针用**四个从未量过的量**判 (ii)：
    M-1 **长度方向的截面积剖面** `A(x)`（12 槽，归一化）—— 纺锤 ⇒ 三角形；板条 ⇒ 矩形；
    M-2 **中段截面**（`|x−x_c| < 0.1L` 内的 W/T 跨度）—— 与全体 `max−min` 对比；
        若中段 T ≪ 全体 T ⇒ `T_span` 被别处的凸起顶高（⇒ `max−min` 口径失真）；
    M-3 **界面法向直方图**（`|n·a|`, `|n·w|`, `|n·n*|`）—— 板条应有**大面积的
        `|n·n*|≈1`（宽面）与 `|n·w|≈1`（侧面）**；纺锤只有尖端一小块 `|n·a|≈1`；
    M-4 **各晶面族自身的推进速率**（对 `|n·axis|>0.8` 的界面胞取该轴投影的极值，
        跨采样点做差）—— 这是"面法向速度"，不是"跨度速度"。
⇒ 判据（**先写死，再看数**）：
    若 M-1 是三角形 且 M-3 里 `|n·w|>0.9` 的面积占比 < 5% ⇒ **形状是纺锤/针**
      ⇒ `长:厚` 必须改用"中段厚度"口径，且 `fill` 低是**几何后果不是数值缺陷**；
    若 M-1 是矩形 且 M-3 有宽面/侧面 ⇒ 形状是板条 ⇒ `fill=0.32` 另有原因（查 M-4）。

⚠ 记账：本探针**不改引擎**（只读 `g.phi` / `g.region()`），`engine_sha` 见 `_run_arm.sh` 清单。
用法：python3 _probe_shape.py --N 64 --dx-nm 166.7 --steps 150 --every 25
"""
import os
import sys
import time
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402

MOB = 1e-9
DF = 3.5e8


def axes_of(g, K):
    n_hab = np.asarray(NPF[K], float)
    n_hab = n_hab / np.linalg.norm(n_hab)
    w_ax = np.asarray(g.wtab[K], float)
    w_ax = w_ax / np.linalg.norm(w_ax)
    a_ax = np.asarray(g.atab[K], float)
    a_ax = a_ax - (a_ax @ n_hab) * n_hab
    a_ax = a_ax / np.linalg.norm(a_ax)
    return n_hab, w_ax, a_ax


def span(reg, axis, dx):
    m = (reg > 0)
    if m.sum() < 8:
        return np.nan
    p = np.argwhere(m).astype(float) @ np.asarray(axis, float)
    return float(p.max() - p.min()) * dx, float(p.min()) * dx, float(p.max()) * dx


def report(g, K, a_ax, w_ax, n_hab, dx, tag, prev, ed_all=None, bh=0.0, bw=0.0):
    reg = g.region()
    m = (reg == K)
    ncell = int(m.sum())
    if ncell < 8:
        print('        [%s] 胞数 %d 太少，跳过' % (tag, ncell), flush=True)
        return prev
    Vol = ncell * dx ** 3
    idx = np.argwhere(m).astype(float)
    pa = idx @ a_ax
    pw = idx @ w_ax
    pn = idx @ n_hab
    La, Wa, Ta = (pa.max() - pa.min()) * dx, (pw.max() - pw.min()) * dx, (pn.max() - pn.min()) * dx
    fill = Vol / max(La * Wa * Ta, 1e-30)
    # ★★★ 2026-09-28（量具正对照 `--selftest` 抓到）：**`fill` 的口径偏差**。
    #   `max−min` 是**胞中心**之差 ⇒ 一个 `n` 胞厚的方向只报 `(n−1)·dx`（`R3` 的"不加 dx"约定）。
    #   对**长度读数**这是对的（加 dx 会把薄板抬高 25%），但对**体积比 `fill`** 就**有偏**：
    #     离散长方体（n_x,n_y,n_z 胞）实测 `fill` = `n_x n_y n_z /((n_x−1)(n_y−1)(n_z−1))` **> 1**；
    #     实测（`--selftest`，24×12×6 胞的长方体）：`fill = 1.366`，**不是 1.0**。
    #   ⇒ 报两个口径：`fill`（与归档可比）与 **`fill_n`（"加一胞"无偏口径）**。
    #     后者对长方体 = 1.000、对椭球 = π/6 = 0.5236 ⇒ **这才是可与"紧凑度"对话的量**。
    fill_n = Vol / max((La + dx) * (Wa + dx) * (Ta + dx), 1e-30)

    # ---- M-1 长度方向截面积剖面（12 槽，按 `a`）----
    nb = 12
    edges = np.linspace(pa.min(), pa.max() + 1e-9, nb + 1)
    hist, _ = np.histogram(pa, bins=edges)
    prof = hist / max(hist.max(), 1)

    # ---- M-2 中段截面 ----
    sel = np.abs(pa - 0.5 * (pa.min() + pa.max())) <= 0.10 * (pa.max() - pa.min() + 1e-9)
    if sel.sum() >= 8:
        Wmid = (pw[sel].max() - pw[sel].min()) * dx
        Tmid = (pn[sel].max() - pn[sel].min()) * dx
        Vmid = sel.sum() * dx ** 3
        fill_mid = Vmid / max((pa[sel].max() - pa[sel].min()) * dx * Wmid * Tmid, 1e-30)
    else:
        Wmid = Tmid = fill_mid = float('nan')

    # ---- M-3 / M-4 界面法向 ----
    phi = g.phi[K].astype(np.float64)
    gr = np.gradient(phi, dx, edge_order=2)
    gm = np.sqrt(gr[0] ** 2 + gr[1] ** 2 + gr[2] ** 2)
    iface = (np.abs(phi) <= 1.5 * dx) & (gm > 1e-9)
    nif = int(iface.sum())
    if nif >= 20:
        nv = np.stack([gr[0][iface] / gm[iface], gr[1][iface] / gm[iface],
                       gr[2][iface] / gm[iface]], axis=1)
        ca = np.abs(nv @ a_ax)
        cw = np.abs(nv @ w_ax)
        cn = np.abs(nv @ n_hab)
        fA = float((ca > 0.9).mean())
        fW = float((cw > 0.9).mean())
        fN = float((cn > 0.9).mean())
        med = float(np.median(gm[iface]))
        # 各晶面族自身的推进速率：极值面的位置
        iif = np.argwhere(iface).astype(float)
        qa, qw, qn = iif @ a_ax, iif @ w_ax, iif @ n_hab
        mid_a = 0.5 * (qa.min() + qa.max())
        mid_w = 0.5 * (qw.min() + qw.max())
        mid_n = 0.5 * (qn.min() + qn.max())
        rate = {}
        for nm, q, selm in (('tip+a', qa, (ca > 0.8) & (qa > mid_a)),
                            ('tip-a', qa, (ca > 0.8) & (qa < mid_a)),
                            ('side+w', qw, (cw > 0.8) & (qw > mid_w)),
                            ('side-w', qw, (cw > 0.8) & (qw < mid_w)),
                            ('face+n', qn, (cn > 0.8) & (qn > mid_n)),
                            ('face-n', qn, (cn > 0.8) & (qn < mid_n))):
            if selm.sum() < 10:
                continue
            v = q[selm]
            rate[nm] = (float(v.max()) * dx, float(v.min()) * dx, int(selm.sum()))
    else:
        fA = fW = fN = med = float('nan')
        rate = {}

    print('        [%s] 胞=%d  V=%.3e m³  `max−min` L=%.1f W=%.1f T=%.1f nm  '
          '**fill=%.3f**  **`fill_n(+dx)`=%.3f**'
          % (tag, ncell, Vol, La * 1e9, Wa * 1e9, Ta * 1e9, fill, fill_n), flush=True)
    print('           M-2 中段(|Δx|<0.1L)：W_mid=%.1f  T_mid=%.1f nm  fill_mid=%.3f   '
          '⇒ T_mid/T_span=%.2f' % (Wmid * 1e9, Tmid * 1e9, fill_mid, Tmid / max(Ta, 1e-30)),
          flush=True)
    print('           M-1 A(x) 剖面（12 槽，归一化）：%s'
          % ' '.join('%.2f' % v for v in prof), flush=True)
    # ★★★ 2026-09-28 新增 **M-0 连通分量**：`BOX16d` 的 `[分量]` 实测 n=2..5（最大分量只占
    #   71.5%–99.8%），而 `_probe_LT.extent()` 与 `fill` 都用**全体胞**口径 ⇒
    #   `max−min` 被**离群碎片**绑架。本行把这件事变成**一眼可见**。
    try:
        from scipy import ndimage as _nd
        lab, ncomp = _nd.label(m)
        if ncomp > 1:
            ii = tuple(idx.T.astype(int))
            lv = lab[ii]                                   # 每个胞的分量号（1-D，与 pa 对齐）
            sizes = np.bincount(lv)
            big = int(np.argmax(sizes[1:])) + 1
            mb = (lv == big)
            Lb = (pa[mb].max() - pa[mb].min()) * dx
            print('           M-0 **连通分量 n=%d**（占胞 %.1f%%）⇒ 全体 L=%.1f vs **最大分量 L=%.1f**'
                  '（差 %+.1f%%）%s'
                  % (ncomp, 100.0 * sizes[1:].max() / sizes[1:].sum(), La * 1e9, Lb * 1e9,
                     100 * (La / max(Lb, 1e-30) - 1),
                     '  ⚠ **`max−min` 被离群碎片绑架**' if La > 1.05 * Lb else ''),
                  flush=True)
        else:
            print('           M-0 **连通分量 n=1** ⇒ 全体口径 = 最大分量口径（读数可信）', flush=True)
    except Exception as _e:
        print('           M-0 分量诊断跳过：%s' % _e, flush=True)
    print('           M-3 界面胞=%d  |∇φ| 中位=%.3f ；面积占比 `|n·a|>0.9`=%.1f%%  '
          '`|n·w|>0.9`=%.1f%%  `|n·n*|>0.9`=%.1f%%'
          % (nif, med, 100 * fA, 100 * fW, 100 * fN), flush=True)
    if rate:
        print('           M-4 晶面族极值面位置（nm，相对上一采样）：%s'
              % '  '.join('%s=%.1f(n=%d)' % (nm, rate[nm][0] * 1e9, rate[nm][2])
                          for nm in ('tip+a', 'tip-a', 'side+w', 'side-w',
                                     'face+n', 'face-n') if nm in rate), flush=True)
    # ★★★ 2026-09-28 新增 **M-5 "实际被施加的迁移率"直方图** —— `F-1` 的**机理级**量化。
    #   动机：`M(n) = M0·exp[−β_h(n·n*)² − β_w(n·w)²]` 的设计对比是 1 : e^{−β_w} : e^{−β_h}
    #   = 1 : 0.100 : 0.030，但"设计"指的是**界面法向恰好等于某个设计轴**的情形。
    #   真实界面的法向是**分布**的 ⇒ 必须量**面积加权的 `M/M0` 分布**，
    #   而不是只看"有没有该晶面族"（那是 M-3）。
    #   ⚠ 口径：本行用 `∇φ_K` 归一化（与 `M-3` 同）；引擎内部用的是 `∇(h_k−h_l)` 并可选
    #     `norm_smooth` ⇒ 两者**口径不同**，本行只作**机理诊断**，不作"引擎施加值"的复现。
    if nif >= 20 and bh + bw > 0:
        E = bh * (nv @ n_hab) ** 2 + bw * (nv @ w_ax) ** 2
        mf = np.exp(-E)
        # 各晶面族的条件均值（该族内 M/M0 的面积加权均值）
        def _cm(mask):
            return float((mf[mask]).mean()) if mask.sum() >= 10 else float('nan')
        print('           M-5 界面 **M(n)/M0** 面积加权均值 = **%.3f**（设计在三个面上分别'
              ' 1.000 / %.3f / %.3f）；占比 `M/M0>0.5` = %.1f%%'
              % (mf.mean(), np.exp(-bw), np.exp(-bh), 100 * (mf > 0.5).mean()), flush=True)
        print('               族内条件均值：`|n·a|>0.8`→%.3f  `|n·w|>0.8`→%.3f  `|n·n*|>0.8`→%.3f'
              % (_cm(ca > 0.8), _cm(cw > 0.8), _cm(cn > 0.8)), flush=True)
    # ★★★ 2026-09-28 新增 **M-6 分面弹性能 `ed[K]`** —— `F-1` 必须排除的**竞争解释**。
    #   若"尖端不推进"其实是"尖端被弹性能顶住"（`Δed` 在尖端为负），那就是**弹性**故事，
    #   不是迁移率故事。两条必须**分别量**（`AGENTS.md §3.27`：两个机制在同一工况重合时分不开）。
    #   ⚠ 口径：`ed[K]` 是**体驱动力**，与 `dG = Δf + Δed − stk·κ` 里的 `Δed = ed[K] − ed[parent]`
    #     差一个 `ed[parent]`（parent 是均匀相 ⇒ 空间上近似常数，但**不是零**）。
    if nif >= 20 and ed_all is not None:
        try:
            edk = ed_all[K]
            v_tip = edk[iface][ca > 0.8]
            v_side = edk[iface][cw > 0.8]
            v_face = edk[iface][cn > 0.8]
            v_all = edk[iface]
            print('           M-6 界面 `ed[V%d]` 分面（J/m³，n 为界面胞数）：'
                  '**尖端 %.3e**(n=%d)  侧面 %.3e(n=%d)  宽面 %.3e(n=%d)  全体 %.3e'
                  % (K, v_tip.mean() if v_tip.size else float('nan'), v_tip.size,
                     v_side.mean() if v_side.size else float('nan'), v_side.size,
                     v_face.mean() if v_face.size else float('nan'), v_face.size,
                     v_all.mean()), flush=True)
            # ★★★ 2026-09-28 追加：**必须同时报母相的 `ed[0]`** —— `dG` 里用的是 `Δed = ed[K] − ed[0]`。
            #   实测（`_w2_terms.log` step 150）：尖端 `ed[V1] = −2.517e8`、侧面 `−4.16e7`、宽面 `−6.66e7`
            #   ⇒ **尖端比侧面低 2.1e8**（而 `Δf = 3.5e8`）⇒ 尖端 `dG` 可能被弹性能吃掉一大截。
            #   ⚠ 没有 `ed[0]` 就**读不出** `Δed` 的绝对值 —— 这是上一版 M-6 的记账缺口。
            _p = ed_all[0]
            print('               母相参照 `ed[0]`：空间均值 %.3e ；**分面 `Δed = ed[V%d] − ed[0]`**：'
                  '尖端 %.3e  侧面 %.3e  宽面 %.3e（`Δf = df[%d] − df[0] = %.3e`）'
                  % (_p.mean(), K,
                     (v_tip - _p[iface][ca > 0.8]).mean() if v_tip.size else float('nan'),
                     (v_side - _p[iface][cw > 0.8]).mean() if v_side.size else float('nan'),
                     (v_face - _p[iface][cn > 0.8]).mean() if v_face.size else float('nan'),
                     K, g.df[K] - g.df[0]), flush=True)
        except Exception as _e:
            print('           M-6 弹性能诊断跳过：%s' % _e, flush=True)
    if prev and rate:
        msg = []
        for nm in ('tip+a', 'side+w', 'face+n'):
            if nm in rate and nm in prev[1]:
                d = rate[nm][0] - prev[1][nm][0]
                msg.append('%s Δ=%.1f nm/窗' % (nm, d * 1e9))
        if msg:
            print('           M-4b 单侧推进增量：%s' % '  '.join(msg), flush=True)
    return (tag, rate)


ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=64)
ap.add_argument('--dx-nm', type=float, default=166.7)
ap.add_argument('--steps', type=int, default=150)
ap.add_argument('--every', type=int, default=25)
ap.add_argument('--kv', type=int, default=1)
ap.add_argument('--r-nm', type=float, default=500.0)
ap.add_argument('--t-nm', type=float, default=700.0)
ap.add_argument('--elong', type=float, default=None,
                help='面内长/宽比；给定则覆盖所有臂（>1 需配 --flat-end 才是平端棱柱）')
ap.add_argument('--flat-end', action='store_true', help='强制所有臂用平端棱柱种子')
ap.add_argument('--arms', default='aniso,iso',
                help='逗号分隔：aniso(3.5/2.3,ns0) | aniso_s2(3.5/2.3,ns2) | iso(0/0) | '
                     'iso_s2(0/0,ns2) | bw5(3.5/5.0) | bh5(5.0/2.3)')
ap.add_argument('--adv', default='proj2', choices=('central', 'upwind', 'proj', 'proj2'))
ap.add_argument('--selftest', action='store_true',
                help='★ 只做**量具正对照**：用**解析已知形状**跑 M-0/M-1/M-2/M-3，'
                     '与解析值比对，不跑引擎（AGENTS §3.19：探针必须先做正对照）')
ap.add_argument('--norm-smooth', type=int, default=-1,
                help='≥0 ⇒ 覆盖所有臂的 norm_smooth；-1 ⇒ 用臂自带值')
a_ap = ap.parse_args()
dx = a_ap.dx_nm * 1e-9
L = a_ap.N * dx

# ★★★ 2026-09-28：`norm_smooth` 升为**臂的属性**（原先是全局开关）——
#   动机：同一 Δx=166.7 / 同 β / 同 R,t 下，
#     `BOX16d`（N=96, norm_smooth=**2**）实测 `fill` 0.884→**0.309**、`L` 100 步涨 **3115 nm**；
#     本探针（N=64, norm_smooth=**0**）实测 `fill` **0.80–0.91**、`L` 100 步只涨 **55.6 nm**。
#   ⇒ 两者只差 **N** 与 **norm_smooth**；Δx 相同、物理是局部的 ⇒ **`norm_smooth` 是首要嫌疑**。
#   ⇒ 必须做成**单因素**：同 N、同 β、只差 `norm_smooth`。这是 `R12`（`norm_smooth` = 数值正则化）
#     的**恰当性检验**：正则化**不得**改变形态学。
ARMS = {'aniso': (3.5, 2.3, 0, 1.0, False),
        'aniso_s2': (3.5, 2.3, 2, 1.0, False),
        'iso': (0.0, 0.0, 0, 1.0, False),
        'iso_s2': (0.0, 0.0, 2, 1.0, False),
        'bw5': (3.5, 5.0, 0, 1.0, False),
        'bh5': (5.0, 2.3, 0, 1.0, False),
        # ★★★ 2026-09-28 新增：**棱柱种子**（平端面 ⊥ a）。
        #   动机（`_w2_shape2.log` 实测）：椭球种子 + ns=0 时，界面里 `|n·a|>0.9` 只占 **1.9–3.2%**
        #   ⇒ **根本没有 {a} 法向的面** ⇒ 尖端有效法向离 `a` 约 65° ⇒ `M(tip) ≈ 0.15·M0`
        #   ⇒ 实测 长:宽:厚 速率比 = 1 : 0.98 : 0.31（设计 1 : 0.10 : 0.03）**各向异性被压缩 ~10×**。
        #   `windowB_surface.py:1515-1519` 自己就写了："矩形棱柱的端面严格垂直 a ⇒
        #   它是唯一能'只增加 L'的面" —— 但这个开关**从未被测过**。
        #   ⇒ `prism4` = elong 4 的矩形棱柱（端面 2R×t = 1000×700 nm ≈ 6×4.2 胞）。
        'prism4': (3.5, 2.3, 0, 4.0, True),
        'prism4_s2': (3.5, 2.3, 2, 4.0, True),
        }
print('=' * 100)
print('_probe_shape —— **形状本身**（截面积剖面 / 中段截面 / 界面法向 / 晶面自身速率）')
print('  N=%d Δx=%.1f nm L=%.2f µm steps=%d every=%d arms=%s adv=%s norm_smooth_override=%d'
      % (a_ap.N, a_ap.dx_nm, L * 1e6, a_ap.steps, a_ap.every, a_ap.arms, a_ap.adv,
         a_ap.norm_smooth))
print('=' * 100)

# ============================================================================
# ★ 量具正对照（`--selftest`）：把 `report()` 喂给**解析已知形状**，比对解析值。
#   动机（`AGENTS.md §3.19`）：本探针的 M-0..M-4 **全部是新量具**，从未与已知答案比过。
#   实现手法：`report()` 只用到 `g.region()` 与 `g.phi[K]` ⇒ 用桩对象即可，**零重构**。
# ============================================================================
if a_ap.selftest:
    class _Stub(object):
        def __init__(self, phi):
            self.phi = phi

        def region(self):
            return np.argmin(self.phi, axis=0).astype(np.int8)

    _N = a_ap.N
    _dx = a_ap.dx_nm * 1e-9
    _L = _N * _dx
    _c = np.array([_L / 2] * 3)
    _X = (np.arange(_N) + 0.5) * _dx
    _gx = _X[:, None, None] - _c[0]
    _gy = _X[None, :, None] - _c[1]
    _gz = _X[None, None, :] - _c[2]
    # 手工给一组**正交**设计轴（避免依赖引擎的 wtab/atab），并满足 a ⊥ n*, w ⊥ 两者
    _n = np.array([0.0, 0.0, 1.0])
    _w = np.array([0.0, 1.0, 0.0])
    _a = np.array([1.0, 0.0, 0.0])
    _ea, _ew, _en = _gx, _gy, _gz
    _D = _dx
    _R = 1.5e-6          # 半长
    _B = 0.75e-6         # 半宽
    _C = 0.40e-6         # 半厚

    def _mk(sdf):
        # ★ 正对照第一版在这里**错过一次**：`phi[0]` 的"外部值"取了 `1e-6`（米）——
        #   而 `1e-6 m = 1000 nm`，于是任何 `sdf < 1000 nm` 的胞都被判成变体
        #   ⇒ 长方体边长被抬高 6 胞/边（实测 L 报 4834 nm，而盒子只有 3000 nm）、`fill=1.162`。
        #   ⇒ 正确写法与 `seed_plate`（`windowB_surface.py:1532-1535`）一致：`phi[0] = −sdf`。
        phi = np.full((2, _N, _N, _N), 1e3)
        phi[1] = sdf
        phi[0] = -sdf
        return _Stub(phi)

    _cases = []
    # (1) 长方体：解析 fill = 1.0；A(x) 恒 1.00；|n·a|>0.9 面积占比 = 2·(2B·2C)/(2·(2A·2B)+2·(2A·2C)+2·(2B·2C))
    _box = np.maximum(np.maximum(np.abs(_ea) - _R, np.abs(_ew) - _B), np.abs(_en) - _C)
    _aA = 4 * _B * _C
    _aW = 4 * _R * _C
    _aN = 4 * _R * _B
    _cases.append(('长方体 3000×1500×800 nm', _mk(_box), 1.0,
                   {'fa': _aA / (_aA + _aW + _aN), 'fw': _aW / (_aA + _aW + _aN),
                    'fn': _aN / (_aA + _aW + _aN), 'flat': True, 'ncomp': 1}))
    # (2) 椭球：(4/3)πabc / (8abc) = π/6 = 0.5236
    _r = np.sqrt((_ea / _R) ** 2 + (_ew / _B) ** 2 + (_en / _C) ** 2)
    _ell = (_r - 1.0) * min(_R, _B, _C)      # 近似 SDF（尺度化，够正对照用）
    _cases.append(('椭球 3000×1500×800 nm', _mk(_ell), np.pi / 6,
                   {'flat': False, 'ncomp': 1}))
    # (3) 双锥（纺锤）：V = (2/3)πR²L（用 B 作底半径）⇒ fill = π/12 = 0.2618
    _rad = _B * np.maximum(0.0, 1.0 - np.abs(_ea) / _R)
    _spi = np.sqrt(_ew ** 2 + _en ** 2) - _rad
    _cases.append(('双锥（纺锤）半长 1500 / 底半径 750', _mk(_spi), np.pi / 12,
                   {'flat': False, 'ncomp': 1, 'taper': True}))
    # (4) 椭球 + 2 个离群单胞（沿 a 拉到 ±4800 nm）⇒ M-0 必须报 n=3 且最大分量 L << 全体 L
    _stray = _ell.copy()
    _stray[2, _N // 2, _N // 2] = -1e-9
    _stray[_N - 3, _N // 2, _N // 2] = -1e-9
    _cases.append(('椭球 + 2 离群单胞', _mk(_stray), None, {'ncomp': 3, 'stray': True}))

    print('\n' + '=' * 100)
    print('【量具正对照 `--selftest`】解析已知形状 ⇒ M-0/M-1/M-2/M-3 是否给出已知答案')
    print('  N=%d Δx=%.1f nm；设计轴取 a=[1,0,0] w=[0,1,0] n*=[0,0,1]（严格正交）'
          % (_N, a_ap.dx_nm))
    print('=' * 100)
    _fail = []
    for _nm, _st, _fill_ex, _exp in _cases:
        print('\n--- 形状：%s（解析 `fill` = %s）'
              % (_nm, ('%.4f' % _fill_ex) if _fill_ex else '—'))
        report(_st, 1, _a, _w, _n, _D, _nm, None, ed_all=None, bh=0.0, bw=0.0)
    print('\n（正对照的**解析期望值**：长方体 `fill_n→1.000`、`A(x)` 全 1.00；'
          '椭球 `fill_n→0.5236`（=π/6）且 `A(x)` 中间高两端低；双锥 `fill_n→0.2618`（=π/12）'
          '且 `A(x)` 单调三角；离群件 M-0 必须报 n=3 且"全体 L ≫ 最大分量 L"。')
    print('  ⚠ 同时注意 `fill`（不含 dx 的 `R3` 口径）**对长方体给 1.37 而不是 1.00** ——'
          '这不是 bug，是"跨度为胞中心之差"的必然偏差；**体积比必须用 `fill_n`**。')
    print('  ★★ **已标定的离散参考值（N=64 / Δx=166.7 nm，本对照实测）** —— 引用 `fill_n` 时必须用这些，'
          '不得用连续值：')
    print('       长方体(24×12×6 胞)  → `fill_n` **1.000**（连续 1.000）')
    print('       椭球(18×9×4.8 胞)   → `fill_n` **0.667**（连续 π/6 = 0.5236；'
          '**薄板向只有 4.8 胞 ⇒ 离散椭球丢掉了两极 ⇒ 参考值被抬高 27%**）')
    print('       双锥(15×7×7 胞)     → `fill_n` **0.367**（连续 π/12 = 0.2618）')
    print('       ⇒ **`fill_n` 的"紧凑"判据必须与同分辨率的离散参考比，不能与连续值比。**')
    print('=' * 100)
    sys.exit(0)

for arm in a_ap.arms.split(','):
    if arm not in ARMS:
        print('!! 未知臂 %r' % arm)
        continue
    bh, bw, ns, el, fe = ARMS[arm]
    if a_ap.norm_smooth >= 0:
        ns = a_ap.norm_smooth
    if a_ap.elong is not None:
        el = a_ap.elong
    if a_ap.flat_end:
        fe = True
    g = W.LevelSetMulti(a_ap.N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0, reinit_dt=6.0e-7)
    K = a_ap.kv
    n_hab, w_ax, a_ax = axes_of(g, K)
    g.seed_plate(K, np.array([L / 2] * 3), n_hab, a_ap.r_nm * 1e-9, a_ap.t_nm * 1e-9,
                 elong=el, along=(a_ax if el > 1.0 else None),
                 flat_end=bool(fe))
    g.init_parent()
    reg0 = g.region()
    s0 = (span(reg0, a_ax, dx), span(reg0, w_ax, dx), span(reg0, n_hab, dx))
    print('\n%s\n【臂 %s】β_h=%.2f β_w=%.2f norm_smooth=%d elong=%.1f flat_end=%s'
          '（设计速率比 1 : e^{−β_w}=%.3f : e^{−β_h}=%.3f）'
          % ('-' * 100, arm, bh, bw, ns, el, fe, np.exp(-bw), np.exp(-bh)))
    print('   种子实测 L=%.1f W=%.1f T=%.1f nm  胞=%d'
          % (s0[0][0] * 1e9 if np.isfinite(s0[0][0]) else float('nan'),
             s0[1][0] * 1e9 if np.isfinite(s0[1][0]) else float('nan'),
             s0[2][0] * 1e9 if np.isfinite(s0[2][0]) else float('nan'),
             int((reg0 == K).sum())))
    dt = 0.15 * dx / (MOB * DF)
    t0 = time.time()
    prev = None
    for it in range(1, a_ap.steps + 1):
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                  mob_beta=bh, mob_beta_w=bw, adv_grad=a_ap.adv,
                  norm_smooth=ns)
        if it % a_ap.every == 0 or it == a_ap.steps:
            _ed = None
            try:
                _ed = g.elastic_driving()
            except Exception as _e:
                print('           （弹性能调用失败：%s）' % _e, flush=True)
            prev = report(g, K, a_ax, w_ax, n_hab, dx, 'step %d' % it, prev,
                          ed_all=_ed, bh=bh, bw=bw)
            print('           （步时 %.2f s）' % ((time.time() - t0) / it), flush=True)
print('\n' + '=' * 100)
print('_probe_shape 结束')
print('=' * 100)
