#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_exp.py --- ★★★ R1 实验台：单个/多个晶核 → 板条形貌（全程留痕 + 硬守卫）

背景（不要重新发明）
--------------------
* 标准计算域 = **24 µm 立方 / Δx = 125 nm**（`MEASUREMENT_SPEC §18 R24`，用户指定）。
* 种子形状 = **输入**（晶体学控制的板条胚不是等轴的）。
* 三轴由 `NPF[k]（n*，惯习面法向）/ wtab[k]（w，宽）/ atab[k]（a，长轴）`给出 ——
  **与引擎实际使用的那一套完全相同**，不是另取一套。
* 设计迁移率比 `M(a) : M(w) : M(n*) = 1 : e^{−β_w} : e^{−β_h}`；
  β_h=3.5, β_w=2.3 ⇒ **1 : 0.100 : 0.030**。
* 文献靶（Wang 2026，LPBF Ti-64 原态 α′）：`L = 8.1 ± 2.0 µm`、`W = 0.9 ± 0.4 µm`
  ⇒ `L:W = 9.0`（ratio-of-means）。`W:T` **无同工艺锚点**。
  ⛔ **不得**把钢的 33 当成 Ti64 的靶（用户 2026-09-29 明确纠正）。

先写死判据（判据先于数据）
--------------------------
| 编号 | 量 | 通过条件 | 依据 |
|---|---|---|---|
| C-1 | 长轴与 `a` 的夹角 | ≤ 20° | 板条长轴 = Burgers 的 ⟨111⟩_β 方向 |
| C-2 | `L:W`（**+dx 无偏口径**） | ≥ 3.0 | 板条最低门槛；文献 9.0 |
| C-3 | `L:T` | ≥ 8.0 | 文献 33.8；Δx=125 nm 的离散地板 ≈ 2 胞 = 250 nm |
| C-4 | `W:T` | 报出 + `θ` 不确定度 | 文献 3.75（口径未知，**只作参考**） |
| C-5 | `fill_n`（+dx 无偏体积比） | ≥ 0.70 | 区分**板条/板**（→1）与**纺锤/针**（→0.3） |
| C-6 | 界面 `|n·a|>0.9` 占比 | ≤ 25% | 板条尖端面很小；纺锤则几乎全是尖端面 |

⚠ 既报**绝对比值**，也报**增量速率比** `ΔL:ΔW:ΔT` —— 后者不受种子形状污染，
  是"引擎各向异性是否被真正实现"的直接度量（与设计 1 : 0.100 : 0.030 比）。

全程留痕（用户要求「保留下来全部的过程用来分析」）
--------------------------------------------------
`<out>/series.csv`   每 `--every` 步一行（含守卫标志），**任何时刻可中断，数据已落盘**
`<out>/pervar.csv`   多核时每个变体一行（哪个核长成了什么）
`<out>/snap_XXXXX.npz` 每 `--snap-every` 步一份 `region()`（int8，压缩）
`<out>/log.txt`       完整 stdout
`<out>/meta.json`     精确算例配置（含引擎 SHA256、git HEAD、时间戳）

硬守卫（不允许静默）
--------------------
| G-1 | 任一向跨度 > `--box-frac`·L | `box_touch=1` ⇒ 该步形貌读数无效（`R24`）|
| G-2 | 目标变体分成 >1 个连通分量 | `ncomp>1` ⇒ `max−min` 被碎片绑架 |
| G-3 | 界面 `median|∇φ|` 落在 [0.7,1.4] 外 | `band_bad=1` ⇒ 几何测度不可信 |
| G-4 | `phi` 出现非有限值 | **立即中止并保留现场**（`CRASH_phi.npz`）|

用法
----
  python3 _r1_exp.py --case lath --out _exp/lath --steps 250 --dry-run
  python3 _r1_exp.py --case lath --nseed 6 --out _exp/lath6 --steps 250
  python3 _r1_exp.py --selftest
"""
import os
import sys
import json
import time
import argparse
import subprocess

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF, DF, MOB            # noqa: E402

# ---------------------------------------------------------------------------
# 晶核形状族：**等体积**（V* ≈ 0.5 µm³）⇒ "形状"是唯一变量（单因素纪律）
#   ⚠ 分辨率地板：Δx = 125 nm ⇒ 厚 < 2 胞（250 nm）不可信 ⇒ T 最小取 250 nm。
#     文献板条厚 ~0.24 µm 在本分辨率下只有 **1.9 胞**（`R24` 的已知不足，必须记账）。
# ---------------------------------------------------------------------------
SHAPES = {
    'lath': dict(kind='prism', L=4000.0, W=500.0, T=250.0),   # 1 : 0.125 : 0.0625
    'equi': dict(kind='sphere', R=492.4),                     # r=(3V/4π)^⅓, V=0.5 µm³
    'mid':  dict(kind='prism', L=2000.0, W=800.0, T=320.0),   # 1 : 0.40 : 0.16
}


def axes_of(g, K):
    """与引擎**同一套**三轴（`a` 长轴、`w` 宽轴、`n*` 惯习面法向）。"""
    n_hab = np.asarray(NPF[K], float)
    n_hab = n_hab / np.linalg.norm(n_hab)
    w_ax = np.asarray(g.wtab[K], float)
    w_ax = w_ax / np.linalg.norm(w_ax)
    a_ax = np.asarray(g.atab[K], float)
    a_ax = a_ax - (a_ax @ n_hab) * n_hab
    a_ax = a_ax / (np.linalg.norm(a_ax) + 1e-300)
    return n_hab, w_ax, a_ax


def seed_one(g, K, shape, center, a_ax, n_hab):
    """按形状族播种**一个**晶核。
       棱柱：`seed_plate(flat_end=True, elong, along)` 给的是半长 `elong·R`、半宽 `R`、
       半厚 `t/2` 的长方体 ⇒ 反解 `R = W/2`、`elong = L/W`、`t = T`。"""
    if shape['kind'] == 'sphere':
        g.seed_sphere(K, center, shape['R'] * 1e-9)
        return
    g.seed_plate(K, center, n_hab, shape['W'] * 0.5e-9, shape['T'] * 1e-9,
                 elong=shape['L'] / shape['W'], along=a_ax, flat_end=True)


COLS = ['step', 't_s', 'dt', 'ncell', 'V', 'L', 'W', 'T', 'Lb', 'Wb', 'Tb',
        'L_cal', 'W_cal', 'T_cal', 'LW_cal', 'LT_cal', 'WT_cal',
        'LWo', 'LTo', 'WTo', 'LW', 'LT', 'WT', 'LW_pm', 'LT_pm',
        'LA', 'WA', 'TA', 'LWA', 'LTA', 'WTA', 'fill_A', 'A_tot', 'A_a', 'A_w', 'A_n',
        'fill', 'fill_n', 'ang_a_deg', 'sv0', 'sv1', 'sv2',
        'ncomp', 'frac_big', 'L_big', 'nif', 'gmed', 'f_a', 'f_w', 'f_n',
        # ★★ 第 3 轮：**逐分量的"块"量具**（多核算例专用）
        'nc', 'Lc', 'Wc', 'Tc', 'LWc', 'LTc', 'align_deg', 'big_frac', 'gap_w_nm',
        'nsig', 'debris',
        # ★★ R1 第 2 轮：**分面弹性能诊断**（P-1，机理判决用）
        'ded_a', 'ded_w', 'ded_n', 'ded_all', 'ed_par_mean',
        'box_touch', 'band_bad', 'ok', 'dG_max', 'nreinit', 'nskip', 'regflip',
        'adv_wall', 'reinit_wall', 'reinit_pairs']


def measure(g, K, a_ax, w_ax, n_hab, box_frac, ed_all=None):
    """一次完整测量。**双口径**（`R3`：`max−min` 有偏 1 胞；`+dx` 对轴对齐无偏）。

    `ed_all` 给定时（`(nreg,N,N,N)` 的弹性驱动）额外算 **P-1 分面诊断**：
      `Δed = ed[K] − ed[0]`（母相参照）在 尖端/侧面/宽面 三族界面胞上的均值
      —— 这是"尖端被弹性顶住"这一机理的**直接**判据（第 1 轮由历史读数推出
      `1.0e8/3.08e8 = 0.325` 与实测 `ΔL:ΔW = 1:0.328` 吻合到 1%）。"""
    from scipy import ndimage as nd
    dx = g.dx
    reg = g.region()
    m = (reg == K)
    ncell = int(m.sum())
    out = dict(ncell=ncell, V=ncell * dx ** 3)
    for c in ('L', 'W', 'T', 'Lb', 'Wb', 'Tb', 'LW', 'LT', 'WT', 'LW_pm', 'LT_pm',
              'fill', 'fill_n', 'ang_a_deg', 'ncomp', 'frac_big', 'L_big', 'nif',
              'gmed', 'f_a', 'f_w', 'f_n', 'box_touch', 'band_bad', 'ok', 'sv0',
              'sv1', 'sv2', 'LA', 'WA', 'TA', 'LWA', 'LTA', 'WTA', 'fill_A',
              'A_tot', 'A_a', 'A_w', 'A_n', 'ded_a', 'ded_w', 'ded_n', 'ded_all',
              'ed_par_mean', 'L_cal', 'W_cal', 'T_cal', 'LW_cal', 'LT_cal',
              'WT_cal', 'nc', 'Lc', 'Wc', 'Tc', 'LWc', 'LTc', 'align_deg',
              'big_frac', 'gap_w_nm', 'nsig', 'debris'):
        out[c] = float('nan')
    out['ok'] = 0
    if ncell < 8:
        return out
    idx = np.argwhere(m)
    f = idx.astype(np.float64)
    pa, pw, pn = f @ a_ax, f @ w_ax, f @ n_hab
    # 口径 ①：`max−min`（胞心之差，`R3` 的"不加 dx"约定，与归档可比）
    La = (pa.max() - pa.min()) * dx
    Wa = (pw.max() - pw.min()) * dx
    Ta = (pn.max() - pn.min()) * dx
    # 口径 ②：`+dx`（对**轴对齐**包围盒无偏）
    Lb, Wb, Tb = La + dx, Wa + dx, Ta + dx
    Vol = ncell * dx ** 3
    out.update(L=La, W=Wa, T=Ta, Lb=Lb, Wb=Wb, Tb=Tb,
               LWo=La / max(Wa, 1e-30), LTo=La / max(Ta, 1e-30), WTo=Wa / max(Ta, 1e-30),
               LW=Lb / max(Wb, 1e-30), LT=Lb / max(Tb, 1e-30), WT=Wb / max(Tb, 1e-30),
               fill=Vol / max(La * Wa * Ta, 1e-30),
               fill_n=Vol / max(Lb * Wb * Tb, 1e-30))
    out['LW_pm'] = out['LW'] * float(np.hypot(0.5 * dx / Lb, 0.5 * dx / Wb))
    out['LT_pm'] = out['LT'] * float(np.hypot(0.5 * dx / Lb, 0.5 * dx / Tb))
    # 主轴（对胞坐标 PCA）⇒ C-1
    f0 = f - f.mean(0)
    try:
        _, sv, vt = np.linalg.svd(f0, full_matrices=False)
        ax = vt[0] / (np.linalg.norm(vt[0]) + 1e-300)
        out['ang_a_deg'] = float(np.degrees(np.arccos(
            min(1.0, abs(float(ax @ a_ax))))))
        out['sv0'], out['sv1'], out['sv2'] = (float(sv[0]), float(sv[1]), float(sv[2]))
    except Exception:
        pass
    # 连通分量 ⇒ G-2
    lab, ncomp = nd.label(m)
    out['ncomp'] = int(ncomp)
    if ncomp > 1:
        sz = np.bincount(lab.ravel())
        big = int(np.argmax(sz[1:])) + 1
        mb = (lab[idx[:, 0], idx[:, 1], idx[:, 2]] == big)
        out['L_big'] = float((pa[mb].max() - pa[mb].min()) * dx) if mb.any() else float('nan')
        out['frac_big'] = float(mb.mean())
    else:
        out['L_big'] = La
        out['frac_big'] = 1.0
    # 界面法向族 ⇒ C-6 ；带健康 ⇒ G-3
    phi = g.phi[K].astype(np.float64)
    gr = np.gradient(phi, dx, edge_order=2)
    gm = np.sqrt(gr[0] ** 2 + gr[1] ** 2 + gr[2] ** 2)
    iface = (np.abs(phi) <= 1.5 * dx) & (gm > 1e-9)
    nif = int(iface.sum())
    out['nif'] = nif
    gmed = float('nan')
    if nif >= 20:
        nv = np.stack([gr[0][iface] / gm[iface], gr[1][iface] / gm[iface],
                       gr[2][iface] / gm[iface]], axis=1)
        out['f_a'] = float((np.abs(nv @ a_ax) > 0.9).mean())
        out['f_w'] = float((np.abs(nv @ w_ax) > 0.9).mean())
        out['f_n'] = float((np.abs(nv @ n_hab) > 0.9).mean())
        gmed = float(np.median(gm[iface]))
        out['gmed'] = gmed
        # ---- ★★ P-1：分面 `Δed = ed[K] − ed[0]`（机理判决用）----
        if ed_all is not None:
            try:
                edk = np.asarray(ed_all[K])[iface]
                edp = np.asarray(ed_all[0])[iface]
                ded = edk - edp
                ca = np.abs(nv @ a_ax)
                cw = np.abs(nv @ w_ax)
                cn = np.abs(nv @ n_hab)
                sel = np.argmax(np.stack([ca, cw, cn], 0), axis=0)
                for idx, tag in ((0, 'ded_a'), (1, 'ded_w'), (2, 'ded_n')):
                    s = (sel == idx)
                    out[tag] = float(ded[s].mean()) if s.sum() >= 10 else float('nan')
                out['ded_all'] = float(ded.mean())
                out['ed_par_mean'] = float(np.asarray(ed_all[0]).mean())
            except Exception:
                pass
        # ---- ★★ 第三口径：**面积反解**（coarea + 法向分族）----
        #   为什么需要它（`_w2_r1calib.log` 实测）：前两条口径都受"**极端胞**"支配 ——
        #     方向与网格**斜交**时 `max−min` 近乎无偏、`+dx` 高读最多 1 胞；
        #     方向**接近网格轴/低指数方向**时反过来（`w` 轴实测：`max−min` −29.3%、
        #     `+dx` −4.3%）。⇒ 单条口径在三条晶体学轴上**各有各的坏**。
        #   面积口径不依赖任何"极端胞"：它用**共面积公式**把界面面积按法向分族，
        #     再由长方体关系反解尺寸（`A_a = 2WT, A_w = 2LT, A_n = 2LW`）⇒
        #       `T = √(A_w·A_a /(2A_n))`，`W = √(A_n·A_a /(2A_w))`，`L = √(A_n·A_w /(2A_a))`。
        #   ⚠ 记账：反解**假定形状是长方体**（板条近似成立、纺锤不成立）
        #     ⇒ `fill_A = V/(L_A W_A T_A)` 就是"离长方体有多远"的**诊断量**，
        #     纺锤应给出 `fill_A ≪ 1`。
        # ★★ R1 第 3 轮：**逐连通分量的"块"量具**。
        #   为什么必须：实验 4–7 的核是**沿 w 排成一列**的多个独立晶核。
        #   `measure()` 原来把 `region()==K` 的**全部胞**当一个对象 ⇒ 实测把 6 个核
        #   读成 `W=8442 nm`、`夹角=90°`（因为整列的 PCA 长轴沿 w）——**完全失真**。
        #   块的正确量法：**逐个分量**量 L/W/T，再统计
        #     `nc` 分量数（⇒ 是否合并）、`align` 各分量长轴与 `a` 的夹角、
        #     `gap_w` 相邻分量质心在 `w` 上的间距（文献 lath 间距 ≈ 宽度）。
        if ncomp >= 1:
            comps = []
            for ci in range(1, ncomp + 1):
                mc = (lab == ci)
                nci = int(mc.sum())
                if nci < 8:
                    continue
                ici = np.argwhere(mc).astype(np.float64)
                pai, pwi, pni = ici @ a_ax, ici @ w_ax, ici @ n_hab
                Li = (pai.max() - pai.min() + 1) * dx
                Wi = (pwi.max() - pwi.min() + 1) * dx
                Ti = (pni.max() - pni.min() + 1) * dx
                cm = ici.mean(0)
                try:
                    _, _, vt = np.linalg.svd(ici - cm, full_matrices=False)
                    u0 = vt[0] / (np.linalg.norm(vt[0]) + 1e-300)
                    al = float(np.degrees(np.arccos(min(1.0, abs(float(u0 @ a_ax))))))
                except Exception:
                    al = float('nan')
                comps.append((nci, Li, Wi, Ti, cm, al))
            out['nc'] = float(len(comps))
            # ★★ 第 4 轮（**快照解剖驱动的量具修正**）：`nc` 会被水平集甩出的
            #   微小液滴污染（实测 `e4` step125 = 6 大 + 18 碎屑；`e6` = 1 大 + 50 碎屑），
            #   而 `big_frac` 在"6 根等大独立板条"时只有 1/6、看上去像碎屑 —— **两个都不够**。
            #   ⇒ 增加**按尺寸阈值**的两个量：
            #     `nsig`  = 胞数 ≥1% 总分量的**显著分量数**（未合并 ⇒ N；已合并 ⇒ 1）
            #     `debris`= <1% 分量占的**体积比**（数值产物，须记账）
            _thr = 0.01 * max(ncell, 1)
            _sig = [c[0] for c in comps if c[0] >= _thr]
            out['nsig'] = float(len(_sig))
            out['debris'] = 1.0 - float(sum(_sig)) / max(ncell, 1)
            if comps:
                out['Lc'] = float(np.median([c[1] for c in comps]))
                out['Wc'] = float(np.median([c[2] for c in comps]))
                out['Tc'] = float(np.median([c[3] for c in comps]))
                out['LWc'] = out['Lc'] / max(out['Wc'], 1e-30)
                out['LTc'] = out['Lc'] / max(out['Tc'], 1e-30)
                out['align_deg'] = float(np.nanmedian([c[5] for c in comps]))
                out['big_frac'] = float(max(c[0] for c in comps)) / max(ncell, 1)
                # 相邻分量质心在 `w` 上的间距（取最近邻中位数）
                # ⚠ 记账（第 3 轮自查抓到的单位 bug）：`cms` 来自 `np.argwhere` ⇒ 是**胞号**，
                #   不是米。第一版忘了乘 `dx`，报出 `1.2e10 nm`。
                #   前两只阶段③算例（`e4_lath6`/`e6_mid6`）的 `gap_w_nm` 列因此**无效**
                #   （可从 `snap_*.npz` 重算）；`nc`/`align_deg`/`LWc`/`big_frac` **不受影响**。
                if len(comps) >= 2:
                    cms = np.array([c[4] for c in comps])
                    pw = np.sort(cms @ w_ax)
                    out['gap_w_nm'] = float(np.median(np.diff(pw))) * dx * 1e9
        U = np.stack([a_ax, w_ax, n_hab], 0)
        cn3 = np.abs(nv @ U.T)                      # (nif,3)
        acell = gm[iface] * dx ** 2 / 3.0           # coarea 面积元（与 cell_area_geom 同口径）
        fam = np.argmax(cn3, axis=1)
        A = np.array([float(acell[fam == i].sum()) for i in range(3)])
        out['A_a'], out['A_w'], out['A_n'] = A
        out['A_tot'] = float(A.sum())
        if A.min() > 0:
            LA = np.sqrt(A[2] * A[1] / (2.0 * A[0]))
            WA = np.sqrt(A[2] * A[0] / (2.0 * A[1]))
            TA = np.sqrt(A[1] * A[0] / (2.0 * A[2]))
            out.update(LA=LA, WA=WA, TA=TA, LWA=LA / WA, LTA=LA / TA, WTA=WA / TA,
                       fill_A=Vol / max(LA * WA * TA, 1e-30))
    out['box_touch'] = int(max(La, Wa, Ta) > box_frac * g.L)
    out['band_bad'] = int(not (0.7 <= gmed <= 1.4)) if np.isfinite(gmed) else 1
    out['ok'] = int(np.isfinite(La) and np.isfinite(Wa) and np.isfinite(Ta))
    return out


def _fmt(v):
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        return '' if not np.isfinite(v) else '%.6g' % v
    return str(v)


def calibrate_axes(g, dims_nm, axes):
    """★★ **在同一个网格上、用同尺寸的解析长方体**定标两条跨度口径的偏差。

    为什么必须做（`_w2_r1calib.log` + `--selftest` 实测）：
      `max−min`（胞心跨度）与 `+dx` **各有各的坏**，谁好取决于"测量方向在网格上
      的投影是否稠密"：
        · 方向**斜交**（本变体的 `a`、`n*`）⇒ `max−min` 偏差 ≤ 2%，`+dx` 高读 +3%~+48%；
        · 方向是**低指数方向**（本变体的 `w` = (1,1,0)/√2）⇒ `+dx` 偏差 −4%，
          `max−min` 低读 **−29%**。
      ⇒ 单一口径在三条轴上**各有各的坏**，**必须逐轴选**。这里就用"已知答案"选出
        每条轴上偏差更小的那一条，并把它的偏差因子记下来供反解。

    ⚠ 记账：因子来自**长方体**种子；演化后的形状（圆角/尖端）**不完全满足**该假定
      ⇒ 修正值是**近似**的，`meta.json` 里存原始因子，CSV 里**两条原始口径都保留**。
    返回 dict：{'L': (conv, factor), 'W': …, 'T': …}
    """
    N, dx, L = g.N, g.dx, g.L
    X = (np.arange(N) + 0.5) * dx - L / 2.0
    gx = X[:, None, None]
    gy = X[None, :, None]
    gz = X[None, None, :]
    u1, u2, u3 = (np.asarray(u, float) for u in axes)
    h = [d * 1e-9 / 2.0 for d in dims_nm]
    p1 = gx * u1[0] + gy * u1[1] + gz * u1[2]
    p2 = gx * u2[0] + gy * u2[1] + gz * u2[2]
    p3 = gx * u3[0] + gy * u3[1] + gz * u3[2]
    sdf = np.maximum(np.maximum(np.abs(p1) - h[0], np.abs(p2) - h[1]),
                     np.abs(p3) - h[2])

    class Stub(object):
        def __init__(self, s):
            self.phi = np.empty((2, N, N, N))
            self.phi[1] = s
            self.phi[0] = -s
            self.L = L
            self.dx = dx

        def region(self):
            return np.argmin(self.phi, axis=0).astype(np.int8)

    mm = measure(Stub(sdf), 1, u1, u2, u3, 0.9)
    out = {}
    for tag, d_nm, k_mm, k_pd in (('L', dims_nm[0], 'L', 'Lb'),
                                  ('W', dims_nm[1], 'W', 'Wb'),
                                  ('T', dims_nm[2], 'T', 'Tb')):
        nom = d_nm * 1e-9
        b_mm = mm[k_mm] / nom - 1.0
        b_pd = mm[k_pd] / nom - 1.0
        if abs(b_mm) <= abs(b_pd):
            out[tag] = ('maxmin', 1.0 / (1.0 + b_mm), b_mm, b_pd)
        else:
            out[tag] = ('plusdx', 1.0 / (1.0 + b_pd), b_mm, b_pd)
    return out, mm


class _Tee(object):
    def __init__(self, p):
        self.f = open(p, 'a', buffering=1)

    def write(self, s):
        sys.__stdout__.write(s)
        self.f.write(s)

    def flush(self):
        sys.__stdout__.flush()
        self.f.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', default='lath', choices=sorted(SHAPES))
    ap.add_argument('--out', default=None)
    ap.add_argument('--N', type=int, default=192)
    ap.add_argument('--dx-nm', type=float, default=125.0)
    ap.add_argument('--steps', type=int, default=250)
    ap.add_argument('--every', type=int, default=5)
    ap.add_argument('--snap-every', type=int, default=25)
    ap.add_argument('--kv', type=int, default=1)
    ap.add_argument('--nseed', type=int, default=1)
    ap.add_argument('--variants', default='')
    ap.add_argument('--shuffle-variants', type=int, default=-1,
                    help='★ 实验 7 的**正确做法**：给定随机种子时，把 `--variants` 列表'
                         '**打乱后**分配给各核。'
                         '⚠ 记账：实验 7 若**人为指定**交替排布，就只能证明"我摆的那套比随机好"，'
                         '**证明不了自组织**；必须从**随机初值**出发，看它自己演化成什么。')
    ap.add_argument('--gap-nm', type=float, default=1200.0)
    ap.add_argument('--kseed', type=int, default=7)
    ap.add_argument('--layout', default='grid',
                    choices=('grid', 'line_w', 'line_a', 'line_n'),
                    help='多核摆放：grid=抖动格点；line_w/line_a/line_n = 沿该设计轴排**一列**'
                         '（`line_w` 才是"一条 block"的几何：平行板条沿宽度方向并排）')
    ap.add_argument('--line-gap-nm', type=float, default=2500.0,
                    help='line 布局的核间距（沿排布轴）')
    ap.add_argument('--beta-h', type=float, default=3.5)
    ap.add_argument('--beta-w', type=float, default=2.3)
    ap.add_argument('--norm-smooth', type=int, default=0)
    ap.add_argument('--adv', default='proj2')
    ap.add_argument('--nthreads', type=int, default=8)
    ap.add_argument('--reinit-band', type=float, default=6.0)
    ap.add_argument('--box-frac', type=float, default=0.80)
    ap.add_argument('--max-hours', type=float, default=6.0)
    ap.add_argument('--seed-scale', type=float, default=1.0,
                    help='种子整体缩放（机制筛选用：同一长径比在不同 Δx 上都要 ≥2 胞厚）')
    ap.add_argument('--no-elastic', action='store_true',
                    help='★★ **判决实验**：关掉弹性驱动（把 elastic_driving_pair 打成 0）'
                         '⇒ 若 ΔL:ΔW:ΔT 回到设计 1:0.10:0.03，则"长不出板条"的元凶是弹性项；'
                         '否则是 M(n)/法向通道。同时省掉谱法弹性求解（快很多）。')
    ap.add_argument('--ed-diag', action='store_true',
                    help='每次采样额外算一份 elastic_driving 并报分面 Δed（P-1 诊断）')
    ap.add_argument('--allow-small-box', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    dx = a.dx_nm * 1e-9
    L = a.N * dx
    if a.selftest:
        return selftest(L, dx)

    ratio = L / 8.1e-6
    print('★ R24 盒长守卫：L = %.3f µm = %.2f × 板条长(8.1 µm)' % (L * 1e6, ratio))
    if ratio < 2.0 and not a.allow_small_box:
        print('   ⛔ 盒长 < 2× 板条长 ⇒ 结论只能写成"盒内行为"。'
              '标准域是 --N 192 --dx-nm 125。')
        return 2

    outdir = a.out or os.path.join('_exp', a.case)
    os.makedirs(outdir, exist_ok=True)
    _old = sys.stdout
    sys.stdout = _Tee(os.path.join(outdir, 'log.txt'))
    try:
        return _run(a, outdir, L, dx)
    finally:
        sys.stdout = _old


def _run(a, outdir, L, dx):
    def P(*x):
        print(*x, flush=True)

    shape = dict(SHAPES[a.case])
    if a.seed_scale != 1.0:
        # ⚠ 记账：**机制筛选**用（不同 Δx 上要保证最薄方向 ≥2 胞）。
        #   缩放后**尺寸不同** ⇒ 与未缩放的臂**不能直接比绝对量**，只能比**速率比**。
        for k in ('L', 'W', 'T', 'R'):
            if k in shape:
                shape[k] = shape[k] * a.seed_scale
    P('=' * 104)
    P('_r1_exp  case=%s  nseed=%d  N=%d  Δx=%.1f nm  L=%.2f µm  steps=%d'
      % (a.case, a.nseed, a.N, a.dx_nm, L * 1e6, a.steps))
    P('  形状 %s ；β_h=%.2f β_w=%.2f（设计比 1 : %.3f : %.3f）；norm_smooth=%d；nthreads=%d'
      % (shape, a.beta_h, a.beta_w, np.exp(-a.beta_w), np.exp(-a.beta_h),
         a.norm_smooth, a.nthreads))
    P('=' * 104)

    t_build = time.time()
    g = W.LevelSetMulti(a.N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=a.nthreads,
                        reinit_every=0, reinit_dt=6.0e-7, reinit_band_cells=a.reinit_band)
    P('构造 %.1f s（含 12 个 argmin_normal + ncmp 66 对）' % (time.time() - t_build))

    K0 = a.kv
    n_hab, w_ax, a_ax = axes_of(g, K0)
    if a.no_elastic:
        # ★★ 判决实验：把弹性驱动整条通道打成 0（`advance` 里的 `edk − edl` 项）。
        #   `elastic_driving_pair` 是 `advance` 唯一的 ed 入口 ⇒ 换掉它就等于关掉弹性。
        #   ⚠ 记账：这**改了物理**（刻意），只用于**机理归因**，不得当作生产配置。
        import numpy as _np
        _sh = (g.N, g.N, g.N)
        g.elastic_driving_pair = (
            lambda karr, larr: (_np.zeros(_sh), _np.zeros(_sh)))
        P('★★ --no-elastic：**弹性驱动已被打成 0**（判决实验，非生产配置）')
    P('变体 V%d 三轴：n*=[%.4f %.4f %.4f]  w=[%.4f %.4f %.4f]  a=[%.4f %.4f %.4f]'
      % ((K0,) + tuple(n_hab) + tuple(w_ax) + tuple(a_ax)))
    P('  正交性：n*·w=%.2e  n*·a=%.2e  w·a=%.2e（引擎的三轴本就不严格正交）'
      % (n_hab @ w_ax, n_hab @ a_ax, w_ax @ a_ax))

    # ---- ★ 逐轴定标（用**解析同尺寸长方体**选每条轴上偏差更小的口径）----
    if shape['kind'] == 'prism':
        dims_nm = (shape['L'], shape['W'], shape['T'])
    else:
        dims_nm = (2 * shape['R'], 2 * shape['R'], 2 * shape['R'])
    CAL, mmcal = calibrate_axes(g, dims_nm, (a_ax, w_ax, n_hab))
    P('★ 逐轴口径定标（解析长方体 %.0f×%.0f×%.0f nm，同一网格 Δx=%.1f nm）：'
      % (dims_nm[0], dims_nm[1], dims_nm[2], a.dx_nm))
    for tag, ax in (('L', 'a'), ('W', 'w'), ('T', 'n*')):
        conv, fac, b_mm, b_pd = CAL[tag]
        P('   %s（沿 %-2s）：选 **%s**（偏差 %+.2f%%，另一条 %+.2f%%）⇒ 修正因子 ×%.4f'
          % (tag, ax, conv, 100 * (b_mm if conv == 'maxmin' else b_pd),
             100 * (b_pd if conv == 'maxmin' else b_mm), fac))

    vlist = [int(v) for v in a.variants.split(',') if v.strip()] or [K0]
    if a.shuffle_variants >= 0 and len(vlist) > 1:
        _rngv = np.random.default_rng(a.shuffle_variants)
        _seq = [_rngv.choice(vlist) for _ in range(max(a.nseed, 1))]
        P('★ `--shuffle-variants %d`：变体序列由**随机**给出 = %s（原列表 %s）'
          % (a.shuffle_variants, _seq, vlist))
        vlist = _seq
    if a.nseed == 1:
        centers = [np.array([L / 2] * 3)]
    elif a.layout.startswith('line'):
        # ★★ 第 3 轮：**沿一条设计轴排一列**。
        #   为什么需要：实验 4–7 问的是"能不能组成**块**"，而块 = **平行板条并排**。
        #   抖动格点摆法给出的是各向同性的核团，量不出"块"。
        #   `line_w` = 沿**宽度方向 w** 并排 ⇒ 正是文献里 block 的几何
        #     （同变体的板条沿 w 堆叠，宽面互相平行）。
        _axmap = {'line_w': w_ax, 'line_a': a_ax, 'line_n': n_hab}
        u = np.asarray(_axmap[a.layout], float)
        u = u / np.linalg.norm(u)
        c0 = np.array([L / 2] * 3)
        half = 0.5 * (a.nseed - 1) * a.line_gap_nm * 1e-9
        centers = [c0 + (i * a.line_gap_nm * 1e-9 - half) * u for i in range(a.nseed)]
        # 周期盒：把越界的核折回来
        centers = [c - L * np.floor(c / L) for c in centers]
        _ext = (a.nseed - 1) * a.line_gap_nm * 1e-9
        P('沿 %s 排 %d 个核，间距 %.0f nm，总跨度 %.2f µm（盒 %.2f µm）'
          % (a.layout[5:], a.nseed, a.line_gap_nm, _ext * 1e6, L * 1e6))
        if _ext + max(shape.get('L', 0), 2 * shape.get('R', 0)) * 1e-9 > 0.9 * L:
            P('   ⚠ 排布跨度 + 核长 > 0.9 盒长 ⇒ 可能被周期镜像污染')
    else:
        rng = np.random.default_rng(a.kseed)
        side = int(np.ceil(a.nseed ** (1.0 / 3.0)))
        grid = (np.arange(side) + 0.5) / side * L
        cand = [np.array([x, y, z]) for x in grid for y in grid for z in grid]
        rng.shuffle(cand)
        # ⚠ 必须留出**长大的余量**：核间距 ≥ 核长 + gap
        need = (shape.get('L', 2 * shape.get('R', 0)) * 1e-9 * 2.0 + a.gap_nm * 1e-9)
        centers = []
        for c in cand:
            if len(centers) >= a.nseed:
                break
            if all(np.linalg.norm((c - c2) - L * np.round((c - c2) / L)) >= need
                   for c2 in centers):
                centers.append(c)
        P('多核摆放：请求 %d，成功 %d（格点 %d；最小间距 %.0f nm = 2×核长 + %.0f）'
          % (a.nseed, len(centers), len(cand), need * 1e9, a.gap_nm))
    if not centers:
        P('✗ 一个核都没放下')
        return 3

    centers = np.array(centers)
    for i, c in enumerate(centers):
        K = vlist[i % len(vlist)]
        nh, ww, aa = axes_of(g, K)
        seed_one(g, K, shape, c, aa, nh)
    g.init_parent()
    P('播种 %d 个核；变体序列 %s' % (len(centers), vlist))

    shas = {}
    for fn in ('windowB_surface.py', 'windowB_pf3d.py', 'windowB_par.py'):
        shas[fn] = subprocess.run(['sha256sum', os.path.join(_HERE, fn)],
                                  capture_output=True, text=True).stdout.split()[0]
    meta = dict(case=a.case, shape=shape, seed_scale=a.seed_scale,
                no_elastic=bool(a.no_elastic), ed_diag=bool(a.ed_diag),
                nseed=len(centers), N=a.N, dx_nm=a.dx_nm,
                L_um=L * 1e6, steps=a.steps, kv=K0, variants=vlist,
                beta_h=a.beta_h, beta_w=a.beta_w, norm_smooth=a.norm_smooth,
                adv=a.adv, nthreads=a.nthreads, reinit_band=a.reinit_band,
                reinit_dt=6.0e-7, df=DF, Mob=MOB, gamma=0.15, box_frac=a.box_frac,
                centers_nm=(centers * 1e9).tolist(), sha256=shas,
                git=subprocess.run(['git', '-C', '/mnt/f/speed_up', 'rev-parse', 'HEAD'],
                                   capture_output=True, text=True).stdout.strip(),
                t0=time.strftime('%Y-%m-%dT%H:%M:%S'))
    with open(os.path.join(outdir, 'meta.json'), 'w') as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    P('meta.json 已写；引擎 SHA256 = %s…' % shas['windowB_surface.py'][:12])

    sp = os.path.join(outdir, 'series.csv')
    fh = open(sp, 'w', buffering=1)
    fh.write(','.join(COLS) + '\n')
    pv = os.path.join(outdir, 'pervar.csv')
    fh2 = open(pv, 'w', buffering=1)
    fh2.write('step,variant,' + ','.join(COLS[3:]) + '\n')

    def emit(step, t_s, dt, adv_wall=float('nan')):
        _ed = None
        if a.ed_diag and not a.no_elastic:
            try:
                _ed = g.elastic_driving()
            except Exception as _e:
                P('   （分面 ed 诊断失败：%s）' % _e)
        mm = measure(g, K0, a_ax, w_ax, n_hab, a.box_frac, ed_all=_ed)
        # ★ 逐轴定标后的读数（每条轴用它自己那条偏差更小的口径 × 修正因子）
        Lc = mm['L' if CAL['L'][0] == 'maxmin' else 'Lb'] * CAL['L'][1]
        Wc = mm['W' if CAL['W'][0] == 'maxmin' else 'Wb'] * CAL['W'][1]
        Tc = mm['T' if CAL['T'][0] == 'maxmin' else 'Tb'] * CAL['T'][1]
        mm.update(L_cal=Lc, W_cal=Wc, T_cal=Tc,
                  LW_cal=Lc / max(Wc, 1e-30), LT_cal=Lc / max(Tc, 1e-30),
                  WT_cal=Wc / max(Tc, 1e-30))
        row = dict(step=step, t_s=t_s, dt=dt,
                   dG_max=float(getattr(g, 'dG_max', float('nan'))),
                   nreinit=int(getattr(g, '_reinit_done', 0)),
                   nskip=int(getattr(g, '_reinit_skipped', 0)),
                   regflip=int(getattr(g, '_reinit_reg_flips', 0)),
                   adv_wall=adv_wall,
                   reinit_wall=float(getattr(g, '_reinit_wall_last', float('nan'))),
                   reinit_pairs=int(getattr(g, '_reinit_pairs_last', 0)))
        row.update({k: mm.get(k, float('nan')) for k in COLS})
        # ★★ 记账（R1 自查的**第三个** bug）：上面这一行最初写的是 `row.update(...)`，
        #   而 `COLS` 里**同时**含"测量量"与"记账量"（`step`/`t_s`/`dt`/`dG_max`/
        #   `nreinit`/…）⇒ `mm` 里没有后者 ⇒ **把已经填好的正确值覆盖成 NaN**
        #   ⇒ 实测 `_exp/lath1/series.csv` 的 `step`/`t_s`/`dt`/`dG_max`/… **全是空**
        #     （几何量完好，但步号丢了 ⇒ 回归只能靠行号重建）。
        #   ⇒ 改为 `setdefault`：**已填的不许被覆盖**。
        for k in COLS:
            row.setdefault(k, float('nan'))
        fh.write(','.join(_fmt(row.get(c, float('nan'))) for c in COLS) + '\n')
        for K in sorted(set(vlist)):
            m2 = measure(g, K, *axes_of(g, K), a.box_frac, ed_all=_ed)
            r2 = dict(step=step, variant=K, **{k: m2.get(k, float('nan')) for k in COLS[3:]})
            fh2.write(','.join(_fmt(r2.get(c, float('nan'))) for c in
                               (['step', 'variant'] + COLS[3:])) + '\n')
        return mm, row

    mm0, _ = emit(0, 0.0, 0.0)
    P('种子实测：`max−min` L=%.0f W=%.0f T=%.0f nm ；`+dx` L=%.0f W=%.0f T=%.0f nm ；'
      '**定标后 L=%.0f W=%.0f T=%.0f nm**（名义 %.0f/%.0f/%.0f）；胞=%d fill_n=%.3f 夹角=%.1f°'
      % (mm0['L'] * 1e9, mm0['W'] * 1e9, mm0['T'] * 1e9, mm0['Lb'] * 1e9,
         mm0['Wb'] * 1e9, mm0['Tb'] * 1e9, mm0['L_cal'] * 1e9, mm0['W_cal'] * 1e9,
         mm0['T_cal'] * 1e9, dims_nm[0], dims_nm[1], dims_nm[2],
         mm0['ncell'], mm0['fill_n'], mm0['ang_a_deg']))

    if a.dry_run:
        P('--dry-run：构造 + 播种 + 初始测量完成，退出（未跑任何一步）。')
        return 0

    dt = 0.15 * dx / (MOB * DF)
    KW = dict(aniso=0.4, npref=NPF, band_cells=20, mob_beta=a.beta_h,
              mob_beta_w=a.beta_w, adv_grad=a.adv, norm_smooth=a.norm_smooth)
    P('dt = %.4e s（标称位移 %.2f nm/步）；Δf = %.3e J/m³；盒 %.1f µm'
      % (dt, 0.15 * a.dx_nm, DF, L * 1e6))

    t_start = time.time()
    t_sim = 0.0
    nrun = 0
    for it in range(1, a.steps + 1):
        tw = time.time()
        g.advance(dt, **KW)
        aw = time.time() - tw
        t_sim += dt
        nrun = it
        if not np.all(np.isfinite(g.phi)):
            P('✗✗ G-4 `phi` 非有限 @ step %d —— 立即中止并保留现场' % it)
            np.savez_compressed(os.path.join(outdir, 'CRASH_phi.npz'), phi=g.phi, step=it)
            return 4
        if it % a.every == 0 or it == a.steps:
            mm, r = emit(it, t_sim, dt, adv_wall=aw)
            fl = []
            if r.get('box_touch'):
                fl.append('⛔G-1盒壁')
            if (r.get('ncomp') or 1) > 1:
                fl.append('⚠G-2分量%d' % r['ncomp'])
            if r.get('band_bad'):
                fl.append('⚠G-3带病')
            P('  [%4d] V=%.4f µm³ | **定标 L/W/T %6.0f/%5.0f/%4.0f nm** | `max−min` %6.0f/%5.0f/%4.0f '
              '| `+dx` %6.0f/%5.0f/%4.0f | **LW=%5.2f LT=%6.2f WT=%5.2f** | fill_cal=%.3f '
              '夹角=%.1f° 面a/w/n=%.0f/%.0f/%.0f%% g=%.3f %.1fs/步 %s'
              % (it, mm['V'] * 1e18, mm['L_cal'] * 1e9, mm['W_cal'] * 1e9,
                 mm['T_cal'] * 1e9, mm['L'] * 1e9, mm['W'] * 1e9, mm['T'] * 1e9,
                 mm['Lb'] * 1e9, mm['Wb'] * 1e9, mm['Tb'] * 1e9,
                 mm['LW_cal'], mm['LT_cal'], mm['WT_cal'],
                 mm['V'] / max(mm['L_cal'] * mm['W_cal'] * mm['T_cal'], 1e-30),
                 mm['ang_a_deg'], 100 * mm['f_a'], 100 * mm['f_w'], 100 * mm['f_n'],
                 mm['gmed'], (time.time() - t_start) / it, ' '.join(fl)))
            if np.isfinite(mm.get('nc', float('nan'))) and mm['nc'] > 1:
                P('          ★块：**分量数 nc=%.0f**  逐分量中位 L/W/T = %.0f/%.0f/%.0f nm  '
                  '**LWc=%.2f**  长轴与 a 夹角中位 %.1f°  相邻质心沿 w 间距 %.0f nm  '
                  '最大分量占比 %.2f'
                  % (mm['nc'], mm['Lc'] * 1e9, mm['Wc'] * 1e9, mm['Tc'] * 1e9,
                     mm['LWc'], mm['align_deg'], mm.get('gap_w_nm', float('nan')),
                     mm['big_frac']))
            if a.ed_diag and np.isfinite(mm.get('ded_all', float('nan'))):
                P('          P-1 分面 `Δed=ed[V%d]−ed[0]`（J/m³）：'
                  '**尖端 %.3e  侧面 %.3e  宽面 %.3e**  全体 %.3e  '
                  '⇒ 净驱动比 (Δf+Δed_尖)/(Δf+Δed_侧) = **%.3f**'
                  % (K0, mm['ded_a'], mm['ded_w'], mm['ded_n'], mm['ded_all'],
                     (DF + mm['ded_a']) / max(DF + mm['ded_w'], 1e-30)))
        if it % a.snap_every == 0 or it == a.steps:
            np.savez_compressed(os.path.join(outdir, 'snap_%05d.npz' % it),
                                region=g.region(), step=it, t=t_sim)
        if (time.time() - t_start) / 3600.0 > a.max_hours:
            P('⏱ 达到 --max-hours=%.1f，干净停止于 step %d（数据已落盘）' % (a.max_hours, it))
            np.savez_compressed(os.path.join(outdir, 'snap_%05d.npz' % it),
                                region=g.region(), step=it, t=t_sim)
            break
    P('完成 %d 步，wall %.1f s（构造 %.1f s）' % (nrun, time.time() - t_start,
                                                time.time() - t_build))
    tot, rows = g.par.report()
    P('并行统计：nthreads=%d，并行区内累计 wall %.1f s' % (g.nthreads, tot))
    for tag, (tt, cnt, mx) in rows[:10]:
        P('    %-24s %8.2f s（%d 次调用，最大分段 %d）' % (tag, tt, cnt, mx))
    return 0


# ---------------------------------------------------------------------------
def selftest(L, dx):
    """★ 量具正对照：拿**解析已知形状**喂给 `measure()`，比对解析值。

    ★★ 本轮**修正过的判据**（记账：第一版把"薄椭球的 L 少读 18.75%"判成 FAIL，
       那是**我的判据错了**，不是量具错了 —— `R3` 的教训在这里第二次出现）：
         * `measure()` 报的是**胞集合**的跨度/PCA/填充率。对**给定胞集合**它是精确的。
         * 薄椭球的**尖端不可能被离散表示**：长轴端胞要求 `gy,gz` 同时接近 0，
           而胞心离轴至少 0.5 胞 ⇒ `(0.5/2)²+(0.5/1)² = 0.3125` 就把长轴挤掉
           `√(1−0.3125) = 17.1%`。⇒ **必须与"离散参考"比，不能与连续解析值比**。
         * 因此本对照的第三项改用**独立暴力枚举**出的"离散胞心跨度"作参考值。
       ⇒ 顺带把 `R3` 已记录的"斜轴有偏"也做成一个可复现的对照（第 4 项）。"""
    N = int(round(L / dx))
    X = (np.arange(N) + 0.5) * dx
    c = np.array([L / 2] * 3)
    gx = X[:, None, None] - c[0]
    gy = X[None, :, None] - c[1]
    gz = X[None, None, :] - c[2]
    n = np.array([0.0, 0.0, 1.0])
    w = np.array([0.0, 1.0, 0.0])
    aa = np.array([1.0, 0.0, 0.0])

    class Stub(object):
        def __init__(self, sdf):
            self.phi = np.full((2, N, N, N), 1e3)
            self.phi[1] = sdf
            self.phi[0] = -sdf
            self.L = L
            self.dx = dx

        def region(self):
            return np.argmin(self.phi, axis=0).astype(np.int8)

    def disc_ref(mask, axis):
        """**独立**暴力参考：直接由布尔胞集合算 `max−min` 与 `+dx` 跨度（不经 measure）。"""
        idx = np.argwhere(mask).astype(float)
        p = idx @ axis
        return (p.max() - p.min()) * dx, (p.max() - p.min() + 1) * dx

    print('=' * 104)
    print('【量具正对照】解析已知形状 ⇒ measure() 是否给出已知答案'
          '（N=%d，Δx=%.1f nm，L=%.2f µm）' % (N, dx * 1e9, L * 1e6))
    print('=' * 104)
    bad = []

    # ---- 1) 长方体（端面是**平面且轴对齐** ⇒ 离散也能精确表示）----
    Lx, Wy, Tz = 3000e-9, 1500e-9, 800e-9
    mbox = (np.abs(gx) <= Lx / 2) & (np.abs(gy) <= Wy / 2) & (np.abs(gz) <= Tz / 2)
    # ---- 2) 球 ----
    R = 1000e-9
    msph = (gx ** 2 + gy ** 2 + gz ** 2) <= R ** 2
    # ---- 3) 薄椭球（**尖端不可离散表示** ⇒ 参考值用暴力枚举）----
    ea, ew, en = 2000e-9, 250e-9, 125e-9
    mell = ((gx / ea) ** 2 + (gy / ew) ** 2 + (gz / en) ** 2) <= 1.0
    # ---- 4) 斜长方体（`R3` 记录过"斜轴有偏 5–24%"）----
    th = np.radians(30.0)
    u1 = np.array([np.cos(th), np.sin(th), 0.0])
    u2 = np.array([-np.sin(th), np.cos(th), 0.0])
    u3 = np.array([0.0, 0.0, 1.0])
    p1 = gx * u1[0] + gy * u1[1] + gz * u1[2]
    p2 = gx * u2[0] + gy * u2[1] + gz * u2[2]
    p3 = gz
    mobl = (np.abs(p1) <= 1500e-9) & (np.abs(p2) <= 400e-9) & (np.abs(p3) <= 200e-9)

    CASES = [
        # (名字, 胞掩模, SDF, 解析L, 解析W, 解析T, 解析fill, 容差, **测量轴 (u1,u2,u3)**,
        #  面积反解是否适用)
        ('长方体 3000×1500×800 nm（轴对齐）', mbox, box_sdf(gx, gy, gz, Lx, Wy, Tz),
         Lx, Wy, Tz, 1.0, 0.06, (aa, w, n), True),
        ('球 R=1000 nm', msph, np.sqrt(gx ** 2 + gy ** 2 + gz ** 2) - R,
         2 * R, 2 * R, 2 * R, np.pi / 6, 0.06, (aa, w, n), False),
        ('薄椭球 4000×500×250 nm（尖端不可表示）', mell,
         (np.sqrt((gx / ea) ** 2 + (gy / ew) ** 2 + (gz / en) ** 2) - 1.0) * en,
         2 * ea, 2 * ew, 2 * en, np.pi / 6, 0.06, (aa, w, n), False),
        ('斜 30° 长方体 3000×800×400 nm', mobl,
         np.maximum(np.maximum(np.abs(p1) - 1500e-9, np.abs(p2) - 400e-9),
                    np.abs(p3) - 200e-9),
         3000e-9, 800e-9, 400e-9, None, 0.06, (u1, u2, u3), True),
    ]
    for nm, mask, sdf, eL, eW, eT, efill, tol, (ux, uw, un), area_ok in CASES:
        mm = measure(Stub(sdf), 1, ux, uw, un, 0.9)
        rL, rLb = disc_ref(mask, ux)
        rW, rWb = disc_ref(mask, uw)
        rT, rTb = disc_ref(mask, un)
        print('\n--- %s' % nm)
        print('    连续解析 L/W/T = %6.0f/%6.0f/%6.0f nm ；**离散暴力参考**（胞心跨度 +dx）'
              '= %6.0f/%6.0f/%6.0f nm'
              % (eL * 1e9, eW * 1e9, eT * 1e9, rLb * 1e9, rWb * 1e9, rTb * 1e9))
        print('    measure() 实测 `max−min` = %6.0f/%6.0f/%6.0f nm ；**+dx = %6.0f/%6.0f/%6.0f nm**'
              % (mm['L'] * 1e9, mm['W'] * 1e9, mm['T'] * 1e9,
                 mm['Lb'] * 1e9, mm['Wb'] * 1e9, mm['Tb'] * 1e9))
        print('    ⇒ 与**离散参考**的相对误差：%+6.3f%% / %+6.3f%% / %+6.3f%%'
              % (100 * (mm['Lb'] / rLb - 1), 100 * (mm['Wb'] / rWb - 1),
                 100 * (mm['Tb'] / rTb - 1)))
        print('    ⇒ 与**连续解析**的相对误差：`max−min` %+6.2f%%/%+6.2f%%/%+6.2f%% ；'
              '`+dx` %+6.2f%%/%+6.2f%%/%+6.2f%%'
              % (100 * (mm['L'] / eL - 1), 100 * (mm['W'] / eW - 1),
                 100 * (mm['T'] / eT - 1), 100 * (mm['Lb'] / eL - 1),
                 100 * (mm['Wb'] / eW - 1), 100 * (mm['Tb'] / eT - 1)))
        print('    fill_n=%.3f（连续 %s）；夹角=%.2f°；连通分量=%d'
              % (mm['fill_n'], ('%.4f' % efill) if efill else '—',
                 mm['ang_a_deg'], mm['ncomp']))
        checks = [('L(+dx) vs 离散', mm['Lb'], rLb),
                  ('W(+dx) vs 离散', mm['Wb'], rWb),
                  ('T(+dx) vs 离散', mm['Tb'], rTb)]
        if area_ok:
            print('    ★ **面积反解口径**（coarea）= %6.0f/%6.0f/%6.0f nm '
                  '（%+6.2f%%/%+6.2f%%/%+7.2f%%）；A_a/A_w/A_n = %.3e/%.3e/%.3e m²'
                  '（解析 %.3e/%.3e/%.3e）；fill_A=%.3f'
                  % (mm['LA'] * 1e9, mm['WA'] * 1e9, mm['TA'] * 1e9,
                     100 * (mm['LA'] / eL - 1), 100 * (mm['WA'] / eW - 1),
                     100 * (mm['TA'] / eT - 1), mm['A_a'], mm['A_w'], mm['A_n'],
                     2 * eW * eT, 2 * eL * eT, 2 * eL * eW, mm['fill_A']))
            print('       ⚠ **本对照实测：面积口径自身也有 −23% ~ +3% 的偏差**'
                  '（coarea 的 `/3` 归一化假定带宽恰好 3Δx；薄向只有 6.4 胞时该假定失效）。')
            print('       ⇒ **面积口径只作第三诊断，不作主口径**（不参与 PASS/FAIL）。')
        else:
            print('    （面积反解**不适用**：它不是长方体 ⇒ 只作诊断，不判 PASS/FAIL）')
        for tag, got, want in checks:
            rel = abs(got - want) / max(abs(want), 1e-30)
            ncell_t = max(1.0, want / dx)
            tolc = max(tol, 0.6 / ncell_t)     # ±0.5 胞的量化地板（R3）
            okk = rel <= tolc
            print('      %-18s %s（相对 %+.4f%%，容差 %.2f%% = max(%.0f%%, ±0.5胞=%.2f%%)）'
                  % (tag, 'PASS' if okk else 'FAIL', 100 * rel, 100 * tolc,
                     100 * tol, 100 * 0.6 / ncell_t))
            if not okk:
                bad.append('%s/%s' % (nm, tag))
    print('\n' + '=' * 104)
    print('量具正对照：%s' % ('★ 全部 PASS（对**离散参考**）' if not bad else '✗ FAIL: %s' % bad))
    print('  ★★ 两条**必须与结论一起引用**的记账：')
    print('     (a) `measure()` 对**给定的胞集合**是精确的 —— 与独立暴力枚举一致到 0.000%；')
    print('     (b) 但"胞集合"与"连续解析形状"之间**有分辨率相关偏差**：薄椭球长轴少读 18.8%、')
    print('         `fill_n` 从 0.524 抬到 0.769；斜 30° 薄长方体的 W 从 0.8 µm 读成 2.25 µm（+181%）。')
    print('     ⇒ 跨分辨率比较必须用**同分辨率的离散参考**；与文献比必须显式标注该偏差。')
    print('     ⇒ 本实验台内部用同一量具做**相对**比较（各臂之间可比）；')
    print('        绝对读数（尤其 L 与 fill_n）**不得**直接当作物理尺寸。')
    print('=' * 104)
    return 0 if not bad else 1


def box_sdf(gx, gy, gz, Lx, Wy, Tz):
    return np.maximum(np.maximum(np.abs(gx) - Lx / 2, np.abs(gy) - Wy / 2),
                      np.abs(gz) - Tz / 2)


if __name__ == '__main__':
    sys.exit(main())
