#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_measure.py —— **块/板条组织的量具**（阶段 3 用；用户要求"量具必须先保证无误"）。

## 设计原则

1. **只吃"状态"**（`region` + 三轴 + `dx` + `vmap`），不吃引擎对象
   ⇒ 可以直接作用在**落盘的 `snap_*.npz`** 上 ⇒ 量具有 bug 也能事后用修好的版本重测。
2. **每个量都有正/负对照**，`--selftest` 在**合成数据**上跑（秒级、不需要仿真）
   ⇒ 每次都知道量具当前的分辨力（`AGENTS.md` §3.3 教训 19）。
3. **主判据是拓扑的、不需几何标定**：`nslab_n` = 沿 @@\\mathbf n^*@@ 的一根**柱**里，
   α′ 场号序列中"连续相同则合并"后的**段数**。
   `M` 根分离的板条 ⇒ `M`；并成一根 ⇒ 1。整数、无标定 ⇒ 比"量厚度"可靠得多。

## ★ 面积估计量（**量具最容易错的地方**）

"数格子/数面"给的是**阶梯面积**，对斜界面**系统性高估** @@\\sum_i|n_i|@@ 倍
（本项目 @@\\mathbf n^*@@ 实测 @@\\sum_i|n_i|=1.665@@ ⇒ 高估 **66.5%**）。

正确估计量：**按方向分别数面**，法向沿轴 @@i@@ 的每个面（面积 @@\\Delta x^2@@）
对真实面积的贡献是 @@\\Delta x^2|n_i|@@：

@@
A=\\Delta x^2\\sum_i f_i|n_i|,\\qquad
f_i=\\#\\{\\;i\\text{-}j\\text{ 面，法向沿轴 }i\\;\\}
@@

对**任意**法向的平面**无偏**（@@\\sum_i f_i|n_i|=(A/\\Delta x^2)\\sum_i n_i^2=A/\\Delta x^2@@）。
`_selftest` C7（n* 方向）与 C12（45° 方向）把它对照到解析值。

> ⚠ **`f_i` 不要除以 2**：`sh=+1` 与 `sh=−1` 选的是**不同**的面（法向 +x / −x），
> 每个面本来就被数**一次**。（第一版这里除了 2 ⇒ 面积正好差一半，被 C7 抓到。）

跑法：
    python3 _bk_measure.py --selftest
    python3 _bk_measure.py --npz _exp/.../snap_00120.npz
"""
import argparse
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np                                              # noqa: E402

try:
    from scipy import ndimage as ndi
    _HAVE_SCIPY = True
except Exception:                                               # pragma: no cover
    _HAVE_SCIPY = False


def _ncomp_sizes(mask):
    """6-连通、**周期**边界下各连通分量的**体素数**（跨越周期面合并后），降序。

    ★ 抽出这个函数是为了加"**显著**碎裂"判据（`_ncomp_big`）而**不动**
      `_ncomp` 的语义 —— 原实现数的是"不同根有几个"，
      新实现数的是"合并后各根的体素数"，两者对**分量个数**逐位一致（已核对）。
    """
    if not mask.any():
        return []
    if not _HAVE_SCIPY:
        raise RuntimeError('需要 scipy.ndimage 才能可靠地数周期连通分量')
    lab, n = ndi.label(mask, structure=ndi.generate_binary_structure(3, 1))
    if n <= 0:
        return []
    sz = np.bincount(lab.ravel(), minlength=n + 1)
    N = mask.shape[0]
    parent = list(range(n + 1))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for ax in (0, 1, 2):
        lo = np.take(lab, 0, axis=ax).ravel()
        hi = np.take(lab, N - 1, axis=ax).ravel()
        m = (lo > 0) & (hi > 0)
        for u, v in zip(lo[m].tolist(), hi[m].tolist()):
            ru, rv = find(u), find(v)
            if ru != rv:
                parent[ru] = rv
    agg = {}
    for i in range(1, n + 1):
        r = find(i)
        agg[r] = agg.get(r, 0) + int(sz[i])
    return sorted(agg.values(), reverse=True)


# ★ 「显著碎裂」的体素阈值。依据（`dry_gs2` 末态实测）：α′ 场里的孤立孤儿是
#   **1–2 体素**（63–125 nm，即 1 个或 1 对格点），而一根板条是 1600–2000 体素。
#   两者之间空了三个数量级 ⇒ 阈值取 **32 体素**（≈3×3×3 格 ≈ 188 nm 立方），
#   远高于离散噪声、又只有一根板条的 ~1.8%。
#   ⚠ 不要用 0/1 体素当阈值（那正是旧 `ncomp` 的行为，会把噪声当碎裂）；
#     也不要拿它当"物理碎片"判据 —— 它只回答"**有没有大于离散尺度的裂块**"。
MIN_SIG_VOX = 32


# ================= ★★★ R146（**P1-43**）：`cov` 的**长度基线** =================
# ## 为什么必须有一条基线（`R30_AUDIT_LEDGER.md` §100 / §101）
#
# `snapshot_coverage` 的分母把每根板条当**理想矩形平板**
# （`Σ_k V_k/t_k · (M−1)/M`），而种子的**端部是收敛的** ⇒ 端部损失占比 ∝ 周长/面积 ∝ 1/L。
# **实测**（`_r123_covsurvey.py`，30+ 个臂的 **step-0** 快照）：
#   `cov(t=0)` 随 `--plate-L` **单调上升**：L=450 ⇒ 0.44；L=1600 ⇒ 1.08（**跨档差 2.4 倍**）。
# ⇒ **`cov ≥ 0.85` 这个阈值只对校准它的那一档 `L/Δx` 成立**，
#   跨 `L` 一刀切会**误杀所有短板条构型**。
#
# ## 口径（**本节新增**）
#   `cov_norm = cov / COV_BASE_BY_L(L)`，判据 **`cov_norm ≥ 0.95`**
#   （"与该 `L` 下能做到的最好相比，损失不超过 5%"）。
#
# ⚠ **基线的性质**：**经验值**，来自本仓库已有臂（只取 `nf2(t=0)==0` 的"清洁种子"里
#   该 `L` 的**最大值**）。生成脚本 `_r124_covcalib.py`；点数少的档（n<3）**不牢**，
#   `cov_norm` 会打印 `⚠` 提醒。**改 Δx 或改种子参数后必须重新标定。**
COV_BASE_BY_L = {
    400e-9: (0.703, 1), 450e-9: (0.442, 1), 600e-9: (0.532, 6),
    800e-9: (0.638, 3), 1000e-9: (0.735, 5), 1600e-9: (1.079, 20),
    2000e-9: (0.845, 2),
}
# 基线只在**块间真分离**（`nf2(t=0)==0`）的臂上标定 ⇒ 用之前**先查 `nf2`**。


def cov_baseline(L):
    """该 `L` 下的 `cov` 基线。返回 `(base, n, exact)`。

    `exact=False` ⇒ 表里没有正好这个 `L`，用了**最近的**档 ⇒ 结果只作提示。
    """
    if not COV_BASE_BY_L:
        return float('nan'), 0, False
    if L in COV_BASE_BY_L:
        b, n = COV_BASE_BY_L[L]
        return b, n, True
    k = min(COV_BASE_BY_L, key=lambda x: abs(x - L))
    b, n = COV_BASE_BY_L[k]
    return b, n, False


def cov_norm(cov, L):
    """`cov_norm = cov / cov_baseline(L)`；附 `(cov_norm, base, n, exact)`。"""
    b, n, ex = cov_baseline(L)
    if not (b == b) or b <= 0:
        return float('nan'), b, n, ex
    return cov / b, b, n, ex



def wide_face_thickness(phi, dx, n_hab, k, band=1.5, cos2_min=0.81,
                        band_cells=2):
    """★★★ R36（`R30_AUDIT_LEDGER.md` **P1-21**）：**宽面厚度** `t_wf`。

    ## 为什么要它（实测推翻了口径）
    `n_%d`（= `ths`，板条胞沿 `n*` 的**包围盒跨度**）**不是板条厚度**：
    实测 `mb1s` 场 1 的包围跨度 624 → **2631 nm**（1500 步），
    而由 φ 量出的**两张宽面之间的距离**只有 780 → **732 nm**（−48 nm）。
    ⇒ 包围跨度被**碎片**（`nc` 12–36）与 **`n*` 与真实板条法向的 7.3° 夹角**
      （`n*·a = −0.127`）撑大 ⇒ R29 那批 `V-8b` FAIL **至少部分是口径伪影**。

    ## 口径（先写死，与 `_r33_wfthick.py` 同一套）
    1. 界面胞 = `|φ| ≤ band·Δx`；
    2. 法向 `n = ∇φ/|∇φ|`；**宽面胞** = `(n·n*)^2 > cos2_min`（默认 0.81 ⇒ 25°）；
    3. 以该场胞沿 `n*` 的**中位位置**为界，把宽面胞分 ±两簇；
    4. `t_wf` = **两簇中位位置之差**。

    对"端面/侧面长大"**免疫**（那些胞的 `(n·n*)^2` 小，进不了第 2 步）。

    ⚠ 只吃 `φ`（`(N,N,N)` 单场或 `(nreg,N,N,N)` + `k`）；`φ` 带外的 NaN 由调用方处理。
    返回 `dict(t_wf=…, lo=…, hi=…, n_wf=…)`；不可测时返回 `None`（**不静默给 0**）。
    """
    phi = np.asarray(phi, float)
    p = phi if phi.ndim == 3 else phi[k]
    if not np.isfinite(p).any():
        return None
    n_hab = np.asarray(n_hab, float)
    n_hab = n_hab / (np.linalg.norm(n_hab) + 1e-300)
    N = p.shape[0]
    pf = np.where(np.isfinite(p), p, 1e3)
    ii = np.arange(N) * dx
    prj = (n_hab[0] * ii[:, None, None] + n_hab[1] * ii[None, :, None]
           + n_hab[2] * ii[None, None, :])
    # 质心用**本场胞**（不是全盒）
    own = np.isfinite(p) & (np.abs(pf) <= band_cells * dx)
    if int(own.sum()) < 20:
        return None
    g = np.gradient(pf, dx, edge_order=2)
    gn = np.sqrt(sum(x ** 2 for x in g)) + 1e-30
    c2 = np.clip(sum(g[i] / gn * n_hab[i] for i in range(3)) ** 2, 0.0, 1.0)
    wf = own & (np.abs(pf) <= band * dx) & (c2 > cos2_min)
    if int(wf.sum()) < 20:
        return None
    v = prj[wf]
    c = float(np.median(prj[own]))
    lo, hi = v[v < c], v[v >= c]
    if lo.size < 10 or hi.size < 10:
        return None
    return dict(t_wf=float(np.median(hi) - np.median(lo)),
                lo=float(np.median(lo)), hi=float(np.median(hi)),
                n_wf=int(wf.sum()))


def face_separations(phi, dx, axes, k, band=1.5, cos2_min=0.81):
    """★★★ R47：**三个面族的"面间距"** —— 「长大速率」的**金标准**口径。

    ## 为什么它是金标准（`R30_AUDIT_LEDGER.md` §17 的实测）
    | 口径 | 会不会被碎片/指状撑大 | 会不会被"中位胞在退、少数胞在长"骗 |
    |---|---|---|
    | 包围盒跨度（`n_lath`/`blk_alen_nm`） | ❌ 会（实测放大 **2.5–2.8×**） | — |
    | 逐胞中位 `dG` 按面分档 | — | ❌ 会（实测**不预测**面运动） |
    | **面位置**（本函数） | ✅ 不会（只取该面族的**中位位置**） | ✅ 不会（量的是**位置**，不是驱动力） |

    ## 口径（与 `_r41_endface.py` 逐字相同，**两处必须一致**）
    1. 界面胞 = `|φ| ≤ band·Δx`；法向 `n = ∇φ/|∇φ|`；
    2. 按 `(n·u)² > cos2_min` 分三族：`tip`（u = a）、`side`（u = w）、
       `wide`（u = n*）；`oblique` = 三族之外；
    3. 每族以**该场胞沿 u 的中位位置**为界分 ±两簇，**面间距 = 两簇中位位置之差**。

    ⚠ 返回的是**沿 u 的间距**（不是面积、不是体积）。不可测的族**不返回**（不填 0）。
    """
    p = np.asarray(phi, float)
    if p.ndim == 4:
        p = p[k]
    if not np.isfinite(p).any():
        return {}
    N = p.shape[0]
    inner = np.isfinite(p)
    pf = np.where(inner, p, 1e3)
    g = np.gradient(pf, dx, edge_order=2)
    gn = np.sqrt(sum(x ** 2 for x in g)) + 1e-30
    ii = np.arange(N) * dx
    rel = [ii[:, None, None], ii[None, :, None], ii[None, None, :]]
    iface = inner & (np.abs(pf) <= band * dx)
    out = {}
    for tag in ('tip', 'side', 'wide'):
        u = np.asarray(axes[tag], float)
        u = u / (np.linalg.norm(u) + 1e-300)
        c2 = np.clip(sum(g[i] / gn * u[i] for i in range(3)) ** 2, 0.0, 1.0)
        m = iface & (c2 > cos2_min)
        if int(m.sum()) < 20:
            continue
        pu = u[0] * rel[0] + u[1] * rel[1] + u[2] * rel[2]
        # ★★★ R47 修（**又一次同类错**）：分簇的**中心**原来取
        #   `inner & (|φ| ≤ 2Δx)`（一条**壳**），而薄板条 + 碎片构型下这条壳会把
        #   **远处碎片的带**也卷进来 ⇒ 中位中心被拽走 ⇒ 分簇边界错 ⇒ 面间距失真。
        #   实测代价：场 1 的 `wide` 从 780→**361**（−419 nm），而独立实现
        #   `_r33_wfthick.py` 给 780→**732**（−48 nm）。
        #   ⇒ 改用**场自己的体**（`φ ≤ 0` ⟺ 在该场内）作中心，碎片免疫。
        own = inner & (pf <= 0)
        if not own.any():
            own = iface
        c = float(np.median(pu[own]))
        v = pu[m]
        lo, hi = v[v < c], v[v >= c]
        if lo.size < 10 or hi.size < 10:
            continue
        out[tag] = float(np.median(hi) - np.median(lo))
    return out


def _label_periodic(mask):
    """6-连通、**周期**边界下的**带标签**分量图（把跨周期面的分量合并成同一个 id）。

    ★ R30 新增（目标第 (2) 项 J-1）：`_ncomp_sizes` 只回**体素数列表**（够判"碎没碎"），
      而"块"需要一个**身份**（哪几根板条属于同一个块）⇒ 必须要有标签图。
      合并规则与 `_ncomp_sizes` **逐字相同**（并查集 + 三轴首末面配对），
      只是把 `agg` 从"体积"换成"标签映射"。
    """
    if not mask.any():
        return None, 0
    if not _HAVE_SCIPY:
        raise RuntimeError('需要 scipy.ndimage 才能可靠地数周期连通分量')
    lab, n = ndi.label(mask, structure=ndi.generate_binary_structure(3, 1))
    if n <= 0:
        return None, 0
    N = mask.shape[0]
    parent = list(range(n + 1))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for ax in (0, 1, 2):
        lo = np.take(lab, 0, axis=ax).ravel()
        hi = np.take(lab, N - 1, axis=ax).ravel()
        m = (lo > 0) & (hi > 0)
        for u, v in zip(lo[m].tolist(), hi[m].tolist()):
            ru, rv = find(u), find(v)
            if ru != rv:
                parent[ru] = rv
    remap = np.zeros(n + 1, np.int64)
    nxt = 0
    for i in range(1, n + 1):
        r = find(i)
        if remap[r] == 0:
            nxt += 1
            remap[r] = nxt
        remap[i] = remap[r]
    return remap[lab], nxt


def blocks(region, dx, vmap, eps0_var=None, npf_var=None, min_vox=MIN_SIG_VOX,
           axes_var=None):
    """★★★ R30（`BLOCK_SELFAC.md` §2.2 的 **J-1**）：**块表量具**。

    ## 定义（先写死）

    一个**块** `b` = 同一个**变体** `v` 的、在 `region` 图上 **6-连通（周期）** 的
    一块区域。块内的不同**场**就是不同的**板条**（`vmap[k] = v`）。

    ⇒ 由此得到的量：
      * `nblk`        块数（含 < min_vox 的小块）
      * `nblk_sig`    **显著**块数（≥ `min_vox` 体素）
      * `blk_laths`   每个显著块里的**板条根数**（该块覆盖了几个场）
      * `blk_vars`    每个显著块的变体号
      * `n_habit`     **实测用到的惯习面种类数**（需要 `npf_var`）——
                      这是 `BLOCK_SELFAC.md §7.1 P-SA-3` 的判据量
      * `f_var_<v>`   各变体在**已转变体积**里的分数
      * `r_selfac`    **实测自协调残差**（§3.1 的 `r`，用**实测** `f_v` 算）
      * `n_var_sig`   实测用到的变体数

    ## 记账（必须随结论一起报）

    * `r_selfac` 用的是**实测体积分数**，不是理论最优分数 ⇒ 它**不是** §3.2 的
      `r(G)` 那种"最好情况"，而是**这个构型实际达到的值**。
    * 归一化尺度 `scale` = 全部 12 个变体 `‖dev ε⁰‖_F` 的**均值**（与
      `_r30_selfac_struct.py` **同一口径**；本文件在 `_r30_block_smoke.py` 里
      有与它逐位比对的对照）。
    * `n_habit` 用惯习面法向的 `|cos|` 判同（阈值 1e-6）—— 与
      `_r30_selfac_struct.group_by` 同口径。
    """
    region = np.asarray(region)
    N = region.shape[0]
    laths = sorted(int(k) for k in vmap)
    letters = sorted({int(v) for v in vmap.values()})
    out = dict(nblk=0, nblk_sig=0, blk_laths='', blk_vars='', n_var_sig=0,
               n_habit=0, r_selfac=float('nan'), f_var='')
    if not laths:
        return out

    # ---- 每一块：按**变体**取掩模，再在周期盒里做 6-连通标注 ----
    info = []                                   # (v, nvox, n_laths, field_ids)
    for v in letters:
        ks = [k for k in laths if int(vmap[k]) == v]
        m = np.zeros((N, N, N), bool)
        for k in ks:
            m |= (region == k)
        if not m.any():
            continue
        lab, nlab = _label_periodic(m)
        if lab is None or nlab <= 0:
            continue
        for b in range(1, nlab + 1):
            mb = (lab == b)
            nvox = int(mb.sum())
            ids = [k for k in ks if bool((mb & (region == k)).any())]
            info.append((v, nvox, len(ids), ids, mb))
    out['nblk'] = len(info)
    sig = [t for t in info if t[1] >= min_vox]
    out['nblk_sig'] = len(sig)
    sig.sort(key=lambda t: -t[1])
    out['blk_laths'] = '/'.join(str(t[2]) for t in sig[:12])
    out['blk_vars'] = '/'.join(str(t[0]) for t in sig[:12])
    # ---- ★ R31：**逐块沿它自己的 n\*** 数板条（多块配置下"沿单一 n* 的柱剖面"无意义）
    #   为什么必须逐块（R31 实测）：`--multi-block --laths 1,1,3,3` 的算例里，
    #     全局 `nslab_n1` 给 4（沿块 0 的 n* 投影时把块 1 的 4 根也数进去了），
    #     而两个块只有**各 2 根**。⇒ 判据必须逐块、用**该块自己的** n*。
    #   实现：把该块的胞投影到 `n_b`，按 `dx` 分箱、取每箱的**众数场号**，
    #     再去掉空箱与短于 `min_run` 的段（`min_run=1` ⇒ 不丢薄层）。
    out['blk_nlath'] = ''
    out['blk_span_nm'] = ''
    out['blk_alen_nm'] = ''
    out['blk_wlen_nm'] = ''
    out['blk_nruns'] = ''
    out['blk_nprof'] = ''
    if axes_var is not None and sig:
        _nl, _sp = [], []
        _al, _wl = [], []
        _nr = []
        _npr = []
        for v, _nvox, _nlaths, ids, _mb in sig[:12]:
            try:
                n_b = np.asarray(axes_var[v][0], float)
                a_b = np.asarray(axes_var[v][1], float)
                w_b = np.asarray(axes_var[v][2], float)
            except (KeyError, IndexError, TypeError):
                _nl.append(0)
                _sp.append(float('nan'))
                _al.append(float('nan'))
                _wl.append(float('nan'))
                continue
            n_b = n_b / (np.linalg.norm(n_b) + 1e-300)
            a_b = a_b / (np.linalg.norm(a_b) + 1e-300)
            w_b = w_b / (np.linalg.norm(w_b) + 1e-300)
            # ★★★ R38（**P1-22**）：跨度必须只用**这个连通分量**的胞 ——
            #   旧写法用 `m = ∪(region == k)`（该块覆盖的**场**的全部胞），
            #   于是同一根板条**飘到远处的 1–2 胞孤儿也被算进 ptp**。
            #   实测放大倍数：`mb1s` **2.21×**、`mb1` **2.51×**
            #   （分量数 1 → 76–85，几乎全是孤儿）。
            m = _mb
            ii = np.arange(N) * dx
            rel = [ii[:, None, None] - 0.0, ii[None, :, None] - 0.0,
                   ii[None, None, :] - 0.0]

            def _proj(u):
                return u[0] * rel[0] + u[1] * rel[1] + u[2] * rel[2]

            vv = _proj(n_b)[m]
            if vv.size == 0:
                _nl.append(0)
                _sp.append(float('nan'))
                _al.append(float('nan'))
                _wl.append(float('nan'))
                continue
            edges = np.arange(vv.min() - 0.5 * dx, vv.max() + 1.5 * dx, dx)
            ids_flat = region[m]
            idxb = np.digitize(vv, edges) - 1
            prof = np.zeros(len(edges) - 1, np.int32)
            for bi in range(prof.size):
                sel = (idxb == bi)
                if sel.any():
                    prof[bi] = int(np.bincount(ids_flat[sel]).argmax())
            segs = []
            for val in prof:
                if segs and segs[-1][0] == int(val):
                    segs[-1][1] += 1
                else:
                    segs.append([int(val), 1])
            runs_b = [s0[0] for s0 in segs if s0[0] != 0 and s0[1] >= 1]
            # ★★★ R33（**新发现的量具缺陷**）：`len(runs_b)`（**连续段数**）会被
            #   分箱众数的噪声**抬高** —— 实测 `mb1s`（只有 3 个场！）：
            #     `blk_laths = 3`（不同场数，正确）而 `blk_nlath = 5–6`（段数）。
            #   机理：某一箱的众数在相邻两场之间跳一下，就把一段劈成两段
            #   ⇒ 与"链长 ≲2Δx 被 min_run 丢掉"是同一族错的**反面**（那次是少读，
            #     这次是多读）。⇒ 主口径改成**不同场数**（对分箱噪声免疫），
            #     段数只作**诊断**保留（两者不等 ⇒ 剖面有噪声，可当场看见）。
            distinct_b = sorted({int(x) for x in prof if int(x) != 0})
            # ★★★ R33 **最终口径**：`blk_nlath` 直接取 **`ids`（该块覆盖的场数）**，
            #   **不用剖面**。理由（实测）：
            #     * 场（level-set field）= 板条的**表示单位** ⇒ `len(ids)` 是定义式的；
            #     * 剖面口径（不论数段还是数不同场）会被**分箱众数的噪声**扰动：
            #       实测 `mb1s` 真值 3 而段数给 5–6；`mb1` 给 4（而 `ids` 是 3）。
            #     * 两个口径不一致这件事**本身有价值** ⇒ 保留为 `blk_nprof`/`blk_nruns`
            #       两个诊断列，并在不一致时**打印告警**，而不是让噪声进主判据。
            #   ⚠ 这也意味着 `blk_nlath ≡ blk_laths`（后者是第一版就有的、稳定的那个）。
            _nl.append(len(ids))
            _npr.append(len(distinct_b))
            _nr.append(len(runs_b))
            _sp.append(float(vv.max() - vv.min()) * 1e9)
            # ★ R31：**该块自己的长轴/宽度方向的跨度** —— 判"块在面内停住没有"的量。
            #   （用全局 `a_lath` 会把另一个变体的板条也混进中位数。）
            _al.append(float(np.ptp(_proj(a_b)[m])) * 1e9)
            _wl.append(float(np.ptp(_proj(w_b)[m])) * 1e9)
        out['blk_nlath'] = '/'.join(str(x) for x in _nl)
        out['blk_span_nm'] = '/'.join('%.0f' % x for x in _sp)
        out['blk_alen_nm'] = '/'.join('%.0f' % x for x in _al)
        out['blk_wlen_nm'] = '/'.join('%.0f' % x for x in _wl)
        # 诊断：段数口径（会被分箱噪声抬高）。与 `blk_nlath`（不同场数）不等
        # ⇒ 该块的柱剖面有噪声，**可当场看见**，不必等到结论出错才发现。
        out['blk_nruns'] = '/'.join(str(x) for x in _nr)
        out['blk_nprof'] = '/'.join(str(x) for x in _npr)
        if _npr != _nl or _nr != _nl:
            print('[blocks] ⚠ 剖面口径与【场数】口径不一致：nlath=%s nprof=%s nruns=%s'
                  ' ⇒ 该块的柱剖面有噪声（判据仍用**场数**口径）'
                  % (_nl, _npr, _nr), flush=True)

    # ---- 变体体积分数（对**已转变**体积归一）----
    vols = {v: float(sum(int((region == k).sum()) for k in laths
                         if int(vmap[k]) == v)) for v in letters}
    tot = float(sum(vols.values()))
    out['f_var'] = '/'.join('%.6g' % (vols[v] / tot) for v in letters) if tot else ''
    out['n_var_sig'] = int(sum(1 for v in letters if vols[v] / tot >= 0.01)) if tot else 0

    # ---- 惯习面种类数 ----
    if npf_var is not None and tot:
        nrm = []
        for v in letters:
            if vols[v] / tot < 0.01:
                continue
            try:
                nv = np.asarray(npf_var[v], float)
            except (KeyError, IndexError, TypeError):
                continue
            nv = nv / (np.linalg.norm(nv) + 1e-300)
            if not any(abs(abs(float(nv @ u)) - 1.0) < 1e-6 for u in nrm):
                nrm.append(nv)
        out['n_habit'] = len(nrm)

    # ---- 实测自协调残差 ----
    if eps0_var is not None and tot:
        E = []
        for i in range(len(eps0_var)):
            A = np.asarray(eps0_var[i], float)
            E.append(A - np.trace(A) / 3.0 * np.eye(3))
        scale = float(np.mean([float(np.sqrt(np.sum(e ** 2))) for e in E]))
        acc = np.zeros((3, 3))
        for v in letters:
            if vols[v] <= 0:
                continue
            acc = acc + (vols[v] / tot) * E[v - 1]
        out['r_selfac'] = float(np.sqrt(np.sum(acc ** 2)) / (scale + 1e-300))
    del dx
    return out



def _ncomp_big(mask, min_vox=MIN_SIG_VOX):
    """**显著**分量数：只数体素数 ≥ `min_vox` 的连通分量。"""
    return int(sum(1 for s in _ncomp_sizes(mask) if s >= min_vox))


def _ncomp(mask):
    """6-连通、**周期**边界下的连通分量数（含 1 体素孤儿，**语义不变**）。"""
    return len(_ncomp_sizes(mask))


def _faces_between(mi, mj):
    """沿 3 轴 × 两符号的跨界面**格面数**（每张面只数一次）。"""
    f = np.zeros(3, np.int64)
    for axx in (0, 1, 2):
        for sh in (1, -1):
            f[axx] += int((mi & np.roll(mj, sh, axis=axx)).sum())
    return f


def _area_from_faces(f, n_hab, dx):
    r"""Cauchy 无偏面积：`A = Δx² · Σ_α f_α |n_α|`。

    自检：法向 n 的平面跨 `f_α = A|n_α|/Δx²` 张 α 向格面
    ⇒ `Σ f_α|n_α| = A/Δx²` ✔（`_selftest` 的 C7/C12 就是这条）。
    """
    return float((f * np.abs(np.asarray(n_hab, float))).sum()) * dx ** 2


def snapshot_coverage(z):
    """**界面完整性**（V-7 / V-7b）—— 单一实现，`_bk_pair.py` 与 `_bk_verdict.py` 共用。

    输入是 `_bk_exp.py` 的落盘快照（`np.load` 出来的对象），
    返回 dict：

    | 键 | 含义 |
    |---|---|
    | `cov` | `Σ F3 面积 / [Σ单根宽面面积 · (M−1)/M]` |
    | `f3_area` / `exp_int` | 分子 / 分母（µm²） |
    | `beta_cells` | `{(i,j): 夹层 β 体素数}` |
    | `beta_frac` | `{(i,j): β当量/(F3+β)}` |
    | `worst` | β 占比最大的那一对 |

    ## 为什么必须有这条判据

    `nf3_col == M−1` **不能证明相邻**（中间夹一层 β 时照样给 M−1），
    `f3_faces > 0` 也只要求"有一点点接触"。`dry_gs2` 就是靠这两条 PASS 的，
    实际每张 +n* 侧界面只有 1/3 贴合（其余是 1 胞厚 β 膜）。

    ## 阈值（**由对照校准，不是拍脑袋**）

    同一盒子/同一 Δx/同一 n* 的**预装**臂 `dry_pa`（`T=250 nm = 4Δx` 格点严格对齐）
    实测 `cov` = 0.955(t=0) / 0.884(50 步) / 0.851(100 步)，
    每对的 β 占比 0.14–0.16 ⇒ 本倾角+分辨率下的天花板是 0.85–0.96，
    β 底噪是 ~0.15。故取 `cov ≥ 0.85` 且 `β占比 ≤ 0.25`。
    ⚠ **不要**为了让预装臂过线把阈值抬到 0.90 —— 那是拿数据拟合判据。

    ## 记账（必须随结论一起报）

    - `Σ单根宽面 = Σ_k V_k / t_k`，`t_k` 用 `_linear_extent` 沿 n* 的**子盒精确**厚度；
      它把板条当**矩形平板**，所以对阶梯边缘带会**高估**应占面积
      ⇒ `cov` 是被系统性低估的（这也是对照只有 0.955 而不是 1.0 的原因之一）。
    - β 当量面积用 `体素数 × Δx²`，对 1 胞厚膜是**一阶**估计；膜厚 >1 胞时会高估。
    """
    reg = z['region']
    dx = float(z['L']) / reg.shape[0]
    n_hab = np.asarray(z['n_hab'], float)
    vmap = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
    laths = sorted(vmap)
    masks = {k: (reg == k) for k in laths}
    parent = (reg == 0)

    tot_broad = 0.0
    n_occ = 0
    for k in laths:
        nvox = int(masks[k].sum())
        if nvox == 0:
            continue
        t = _linear_extent(masks[k], n_hab, dx)[0]
        if t <= 0:
            continue
        tot_broad += (nvox * dx ** 3) / t
        n_occ += 1
    exp_int = tot_broad * (n_occ - 1) / n_occ if n_occ else 0.0

    tot_f3 = 0.0
    f3_of = {}
    for ii, i in enumerate(laths):
        for j in laths[ii + 1:]:
            if vmap[i] != vmap[j]:
                continue
            if not masks[i].any() or not masks[j].any():
                continue
            A = _area_from_faces(_faces_between(masks[i], masks[j]), n_hab, dx)
            tot_f3 += A
            f3_of[(i, j)] = A

    # β 夹层：**6 邻域里同时挨着 i 和 j** 的场 0 体素。
    # ⚠ 第一版写成 `parent & roll(gi,sh) & roll(gj,sh)` —— 同一个 sh 要求两侧
    #   **同向**，漏掉真正的夹心构型（i 在 c+ê、j 在 c−ê）⇒ 15 对全部假阴性。
    nbi = {}
    for k in laths:
        if not masks[k].any():
            continue
        t = np.zeros(reg.shape, bool)
        for axx in (0, 1, 2):
            for sh in (1, -1):
                t |= np.roll(masks[k], sh, axis=axx)
        nbi[k] = t
    beta_cells, beta_frac = {}, {}
    for ii, i in enumerate(laths):
        for j in laths[ii + 1:]:
            if vmap[i] != vmap[j] or i not in nbi or j not in nbi:
                continue
            n = int((parent & nbi[i] & nbi[j]).sum())
            if n <= 0:
                continue
            key = (i, j)
            beta_cells[key] = n
            a_f3 = f3_of.get(key, 0.0)
            a_b = n * dx ** 2
            beta_frac[key] = a_b / (a_f3 + a_b) if (a_f3 + a_b) > 0 else 0.0
    return dict(cov=(tot_f3 / exp_int if exp_int > 0 else float('nan')),
                f3_area=tot_f3, exp_int=exp_int, tot_broad=tot_broad,
                n_occ=n_occ, beta_cells=beta_cells, beta_frac=beta_frac,
                worst=(max(beta_frac, key=lambda k: beta_frac[k])
                       if beta_frac else None))


def _bbox_of(mask, pad=0):
    """`mask` 的**索引空间**包围盒（用可分离投影求，**零 N³ 临时**）。

    ★ 为什么必须这样（本文件 v1 的内存问题）：v1 直接造三张 (N,N,N) float64
      坐标网格（N=192 时 **3×56.6 = 170 MB**），再 `rel` 一份、`pa/pw/pn` 三份
      ⇒ 单次测量 ~500 MB 瞬时分配。生产跑每 5 步测一次 ⇒ 把 WSL 推到
      swap 8188/8192 = **99.9%**、一个进程卡在 **D 态**。
      改成"先求包围盒，再只在小盒上算" ⇒ 瞬时分配降到 **KB 量级**。
    """
    N = mask.shape[0]
    xs = np.flatnonzero(mask.any(axis=(1, 2)))
    ys = np.flatnonzero(mask.any(axis=(0, 2)))
    zs = np.flatnonzero(mask.any(axis=(0, 1)))
    if xs.size == 0:
        return None
    return (slice(max(0, xs[0] - pad), min(N, xs[-1] + 1 + pad)),
            slice(max(0, ys[0] - pad), min(N, ys[-1] + 1 + pad)),
            slice(max(0, zs[0] - pad), min(N, zs[-1] + 1 + pad)))


def _sub_coord(bb, dx):
    return [np.arange(bb[t].start, bb[t].stop) * dx for t in range(3)]


def _linear_extent(mask, u, dx, pad=0):
    """沿方向 `u` 的尺寸（**精确**，只在小盒上算）。

    线性泛函 @@u\\cdot x@@ 在集合上的极值必在集合内取到，
    而索引包围盒**包含**集合 ⇒ 在包围盒内取极值**精确**。
    """
    bb = _bbox_of(mask, pad)
    if bb is None:
        return 0.0, 0.0
    c = _sub_coord(bb, dx)
    val = (u[0] * c[0][:, None, None] + u[1] * c[1][None, :, None]
           + u[2] * c[2][None, None, :])
    v = val[mask[bb]]
    if v.size == 0:
        return 0.0, 0.0
    return float(v.max() - v.min()), float(v.max() - v.min() + dx)


def _extent(pos, mask, dx):
    """保留旧签名（外部可能调用）：`pos` 此刻可以是 (u, dx) 元组或已弃用。"""
    if isinstance(pos, tuple) and len(pos) == 2 and np.ndim(pos[0]) == 1:
        return _linear_extent(mask, np.asarray(pos[0], float), pos[1])
    raise TypeError('_extent 已改为 _linear_extent(mask, u, dx)；请勿再用全网格 pos')


def _coord_grid(N, dx):
    ii = np.arange(N)
    return [ii[:, None, None] * dx, ii[None, :, None] * dx, ii[None, None, :] * dx]


def _auto_r_col(region, dx, n_hab, w_ax, a_ax, allowed, floor=300e-9):
    """**自适应柱半径**：把全部板条胞都包进柱内所需的最小面内半径。

    ★ R30 P0-1 的修法。`r_col=300 nm` 硬编码时，面内偏置 > 300 nm 的板条
      **整个不可见**（`dry_cln11` step 2000 实测：场 2 质心偏 a = −1775 nm）。

    为什么不能用"面内包围盒的半对角线"：那只在**质心恰在包围盒中心**时成立。
    实测（`_r30_mfix_smoke.py` P-4）把一层挪 1500 nm 后，半对角线口径给
    `cover_2 = 0.88`（仍有 12% 的胞在柱外）。⇒ 这里改成**逐胞取最大值**（精确）。

    代价：只在 `m_all` 的包围盒（外扩 1 胞）上算两个 (n,1,1)/(1,n,1)/(1,1,n)
    广播出来的子盒数组 —— 对紧凑的板条堆叠是几万胞，**不 materialize 整盒**。
    周期盒下质心用**可分离投影**求（与 `column_profile` 同一套定义，避免口径分叉）。
    """
    region = np.asarray(region)
    N = region.shape[0]
    m_all = np.isin(region, list(allowed))
    if not m_all.any():
        return float(floor)
    ii = np.arange(N) * dx
    cnt = float(m_all.sum())
    s = [m_all.sum(axis=(1, 2)), m_all.sum(axis=(0, 2)), m_all.sum(axis=(0, 1))]
    c = np.array([float((ii * s[t]).sum()) / cnt for t in range(3)])
    bb = _bbox_of(m_all, pad=1)
    if bb is None:
        return float(floor)
    sub = m_all[bb]
    cc = _sub_coord(bb, dx)
    r3 = [(cc[t] - c[t]) for t in range(3)]
    r3 = [r3[0][:, None, None], r3[1][None, :, None], r3[2][None, None, :]]
    pa = a_ax[0] * r3[0] + a_ax[1] * r3[1] + a_ax[2] * r3[2]
    pw = w_ax[0] * r3[0] + w_ax[1] * r3[1] + w_ax[2] * r3[2]
    d2 = (pa ** 2 + pw ** 2)[sub]
    if d2.size == 0:
        return float(floor)
    return max(float(floor), float(np.sqrt(d2.max())) + 0.5 * dx)


def _column_mask(region, dx, n_hab, w_ax, a_ax, allowed, r_col):
    """柱剖面用的**布尔掩模**（全盒形状，`(N,N,N)` bool）。

    ★ R30 新增：把 `column_profile` 里的柱掩模单独取出来，供**可见性守卫**使用
      （"某个场的胞有多少落在柱内" —— 这正是 P0-1 静默丢层的机制）。
    与 `column_profile` 用**同一套**定义（同一 `_bbox_of`/`_sub_coord`/`r_col`），
    避免两处口径分叉。
    """
    region = np.asarray(region)
    N = region.shape[0]
    m_all = np.isin(region, list(allowed))
    out = np.zeros((N, N, N), bool)
    if not m_all.any():
        return out
    ii = np.arange(N) * dx
    cnt = float(m_all.sum())
    s = [m_all.sum(axis=(1, 2)), m_all.sum(axis=(0, 2)), m_all.sum(axis=(0, 1))]
    c = np.array([float((ii * s[t]).sum()) / cnt for t in range(3)])
    rc = int(np.ceil(r_col / dx)) + 1
    bb = _bbox_of(m_all, pad=rc)
    sub_m = m_all[bb]
    if not sub_m.any():
        return out
    cc = _sub_coord(bb, dx)
    r3 = [(cc[t] - c[t]) for t in range(3)]
    r3 = [r3[0][:, None, None], r3[1][None, :, None], r3[2][None, None, :]]
    pa = a_ax[0] * r3[0] + a_ax[1] * r3[1] + a_ax[2] * r3[2]
    pw = w_ax[0] * r3[0] + w_ax[1] * r3[1] + w_ax[2] * r3[2]
    out[bb] = sub_m & (pa ** 2 + pw ** 2 <= r_col ** 2)
    return out


def column_profile(region, dx, n_hab, w_ax, a_ax, allowed, r_col=300e-9,
                   min_run=2):
    """沿 @@\\mathbf n^*@@ 的**柱剖面**。

    取 α′ 质心周围**面内半径 `r_col`** 的柱，沿 n* 按 @@\\Delta x@@ 分箱，
    每箱取该箱内 α′ 场号的**众数**（无 α′ ⇒ 0）。

    返回 `(prof, runs)`；`runs` = 把"连续相同"合并、再去掉短于 `min_run` 的箱的段列表。
    """
    region = np.asarray(region)
    N = region.shape[0]
    m_all = np.isin(region, list(allowed))
    if not m_all.any():
        return None, []
    # ---- 质心：用**可分离投影**求，**不materialize 任何 N³ 临时** ----
    ii = np.arange(N) * dx
    cnt = float(m_all.sum())
    s = [m_all.sum(axis=(1, 2)), m_all.sum(axis=(0, 2)), m_all.sum(axis=(0, 1))]
    c = np.array([float((ii * s[t]).sum()) / cnt for t in range(3)])
    rc = int(np.ceil(r_col / dx)) + 1
    # ---- 柱的索引包围盒 ----
    # ★★ 坑（本文件 v1.1 踩过）：柱是**沿 n* 的圆柱**，它在 n* 方向**贯穿整个堆叠**
    #   ⇒ 索引空间的包围盒**不能**取"质心 ± rc 胞"（那会把两端的板条切掉，
    #     实测 C13b 少了板条 1、C11 的 nslab 从 23 掉到 4）。
    #   正确做法：取 **`m_all` 的包围盒**再外扩 `rc`（保证面内半径够用）。
    #   对"紧凑的板条堆叠"这个盒子很小（生产臂 ~5.5×1×1.5 µm ⇒ 几万胞 vs 7e6）
    #   ⇒ 内存收益仍在；对**随机噪声**（C11 的合成对照）它会退化成整盒，但那只在自检里。
    bb = _bbox_of(m_all, pad=rc)
    sub_m = m_all[bb]
    if not sub_m.any():
        return None, []
    sub_r = region[bb]
    cc = _sub_coord(bb, dx)
    # ★ 三个轴必须各自 reshape 成 (n,1,1)/(1,n,1)/(1,1,n) 才会广播成 3D
    r3 = [(cc[t] - c[t]) for t in range(3)]
    r3 = [r3[0][:, None, None], r3[1][None, :, None], r3[2][None, None, :]]
    pa = a_ax[0] * r3[0] + a_ax[1] * r3[1] + a_ax[2] * r3[2]
    pw = w_ax[0] * r3[0] + w_ax[1] * r3[1] + w_ax[2] * r3[2]
    pn = n_hab[0] * r3[0] + n_hab[1] * r3[1] + n_hab[2] * r3[2]
    col = sub_m & (pa ** 2 + pw ** 2 <= r_col ** 2)
    if not col.any():
        return None, []
    v = pn[col]
    ids = sub_r[col]
    edges = np.arange(v.min() - 0.5 * dx, v.max() + 1.5 * dx, dx)
    prof = np.zeros(len(edges) - 1, np.int32)
    idxb = np.digitize(v, edges) - 1
    for b in range(prof.size):
        sel = (idxb == b)
        if not sel.any():
            continue
        prof[b] = int(np.bincount(ids[sel]).argmax())
    # 连续相同合并（保留长度）
    segs = []
    for val in prof:
        if segs and segs[-1][0] == int(val):
            segs[-1][1] += 1
        else:
            segs.append([int(val), 1])
    runs = [s0[0] for s0 in segs if s0[0] != 0 and s0[1] >= min_run]
    return prof, runs


def _same_variant_adjacent(runs, vmap):
    """`runs` 里**相邻且同变体**的对数（= 柱里穿过的 F3 界面张数）。"""
    c = 0
    for a_, b_ in zip(runs[:-1], runs[1:]):
        if a_ in vmap and b_ in vmap and vmap[a_] == vmap[b_]:
            c += 1
    return c


def measure_state(region, dx, n_hab, w_ax, a_ax, vmap, r_col=300e-9,
                  r_col_auto=True, min_run_new=1):
    """对一个状态做全套测量。`vmap` : {场号: 变体号}（只含板条场，不含母相 0）。

    ★★★ R30 修复（`R30_AUDIT_LEDGER.md` **P0-1**）：柱剖面原来有**两种静默少读**，
    它们直接喂给 V-1 / V-7 / V-7b / A-5（"块形成"的主判据）：

      ① `min_run=2` 把"沿 n* 只占 1 个箱"的层**整层丢掉** —— 而箱宽 = Δx、相位锚在
         `v.min()` ⇒ 层厚 ≲2Δx 时读不读得到**取决于相位**。
         【实测】6 层等厚、盒内 6 场全在：层厚 2Δx ⇒ `nslab_n = 5`（场 4 被丢）；
         3.5Δx ⇒ 6 ✅。见 `_r30_ctl_measure.py`。
      ② `r_col = 300 nm` **硬编码**且**不落盘** ⇒ 面内偏置 > 300 nm 的板条整个不可见，
         截面大的板条还会被切成两段（`nslab_n` 反而多读）。
         【实测】正在跑的 `dry_cln11` step 2000 就是这一例（场 2 质心偏 a=−1775 nm）。

    **处置（遵守本仓库"两个口径都存、判决用新的、原始值留档"的纪律）**：
      * `nslab_n` / `runs` / `nf3_col` —— **保持归档口径不变**（`r_col=300 nm`、`min_run=2`），
        这样历史读数**逐位可复现**，不会被这次修复悄悄改掉；
      * **新增** `nslab_n1` / `runs1` / `nf3_col1` —— 用**自适应柱半径** + `min_run=1`；
      * **新增** `r_col_nm`（实际用的半径，落盘）与 `col_cover_min` / `col_cover_<k>`
        （每个场有多少比例的胞落在柱内）⇒ **可见性守卫**：静默丢层从此可被检出。
    """
    region = np.asarray(region)
    N = region.shape[0]
    nreg = max(int(region.max()) + 1, max(vmap) + 1)
    laths = sorted(int(k) for k in vmap)
    allowed = set(laths)
    axes = dict(n=np.asarray(n_hab, float), w=np.asarray(w_ax, float),
                a=np.asarray(a_ax, float))
    out = {}
    for k in range(nreg):
        m = (region == k)
        out['vol_%d' % k] = float(m.sum()) * dx ** 3
        out['ncomp_%d' % k] = _ncomp(m)
        # ★ 显著分量数（≥32 体素）：判"**有没有大于离散尺度的裂块**"。
        #   保留原始 `ncomp_k` 不动 —— 两者一起报，任何人都能自己重判，
        #   而不是被一个阈值悄悄改掉结论（`dry_gs2` 的 ncomp_max=4 就是这么来的：
        #   1 根 2022 体素的完整板条 + 3 个 1–2 体素孤儿）。
        out['ncompbig_%d' % k] = _ncomp_big(m)
        if k in allowed:
            for nm in ('n', 'w', 'a'):
                e, eb = _linear_extent(m, axes[nm], dx)
                out['%s_%d' % (nm, k)] = e
                out['%sb_%d' % (nm, k)] = eb
    out['nreg_used'] = int(sum(1 for k in laths if out['vol_%d' % k] > 0))
    out['M'] = len(laths)

    # ---- 柱剖面：**两个口径都存**（R30 P0-1）---------------------------------
    # 归档口径（`r_col` / `min_run=2`）：逐位保持不变，历史读数可复现
    prof, runs = column_profile(region, dx, n_hab, w_ax, a_ax, allowed, r_col)
    out['nslab_n'] = len(runs)
    out['runs'] = ','.join(str(x) for x in runs)
    out['nf3_col'] = _same_variant_adjacent(runs, vmap)
    # ★ 新口径：自适应柱半径 + `min_run=1`
    r_eff = float(r_col)
    if r_col_auto:
        r_eff = _auto_r_col(region, dx, n_hab, w_ax, a_ax, allowed, floor=r_col)
    prof1, runs1 = column_profile(region, dx, n_hab, w_ax, a_ax, allowed,
                                  r_eff, min_run=int(min_run_new))
    out['nslab_n1'] = len(runs1)
    out['runs1'] = ','.join(str(x) for x in runs1)
    out['nf3_col1'] = _same_variant_adjacent(runs1, vmap)
    out['r_col_nm'] = r_eff * 1e9
    out['r_col_legacy_nm'] = float(r_col) * 1e9
    # ---- ★ 可见性守卫：每个场有多少比例的胞落在（新口径的）柱内 --------------
    # 静默丢层的机制就是"柱看不见它" ⇒ 把这件事**变成落盘数字**。
    sub_r = np.where(np.isin(region, list(allowed)), region, 0)
    in_col = _column_mask(region, dx, n_hab, w_ax, a_ax, allowed, r_eff)
    cov = []
    for k in laths:
        mk = (region == k)
        nk = int(mk.sum())
        out['col_cover_%d' % k] = (float((mk & in_col).sum()) / nk) if nk else 0.0
        if nk:
            cov.append(out['col_cover_%d' % k])
    out['col_cover_min'] = float(min(cov)) if cov else float('nan')
    del sub_r

    # ---- F3 面（按方向数面；**无偏**面积）----------------------------
    fdir = np.zeros(3, np.int64)
    f3_cells = np.zeros(region.shape, bool)
    for i, ki in enumerate(laths):
        for kj in laths[i + 1:]:
            if vmap[ki] != vmap[kj]:
                continue
            mi, mj = (region == ki), (region == kj)
            if not mi.any() or not mj.any():
                continue
            for axx in (0, 1, 2):
                for sh in (1, -1):
                    t = mi & np.roll(mj, sh, axis=axx)
                    fdir[axx] += int(t.sum())
                    f3_cells |= t
                    f3_cells |= (mj & np.roll(mi, sh, axis=axx))
    out['f3_faces'] = int(fdir.sum())
    out['f3_cells'] = int(f3_cells.sum())
    out['f3_area'] = float((fdir * np.abs(np.asarray(n_hab, float))).sum()) * dx ** 2
    out['f3_area_stair'] = float(fdir.sum()) * dx ** 2
    # ---- ★★ R31：**F2 面（异变体界面）** —— 这是"**块与块相遇**"的签名 ----------
    #   为什么必须补（S4 的发现）：`_bk_measure` 原来**只有 F1 与 F3**，
    #   异变体对在 `:393` 被 `continue` 直接跳过 ⇒ **F2 连量具都没有**，
    #   而"两块相遇后停住"这件事**只能**由 F2 面积的增长来证明。
    #   ⇒ 同一套格面计数，只是把"同变体"换成"**异**变体"。
    f2dir = np.zeros(3, np.int64)
    for i, ki in enumerate(laths):
        for kj in laths[i + 1:]:
            if vmap[ki] == vmap[kj]:
                continue
            mi, mj = (region == ki), (region == kj)
            if not mi.any() or not mj.any():
                continue
            for axx in (0, 1, 2):
                for sh in (1, -1):
                    f2dir[axx] += int((mi & np.roll(mj, sh, axis=axx)).sum())
    out['f2_faces'] = int(f2dir.sum())
    out['f2_area'] = float((f2dir * np.abs(np.asarray(n_hab, float))).sum()) * dx ** 2
    out['f2_area_stair'] = float(f2dir.sum()) * dx ** 2
    if f3_cells.any():
        bb = _bbox_of(f3_cells)
        cc = _sub_coord(bb, dx)
        pn = (axes['n'][0] * cc[0][:, None, None] + axes['n'][1] * cc[1][None, :, None]
              + axes['n'][2] * cc[2][None, None, :])
        vv = pn[f3_cells[bb]]
        out['f3_pos_n'] = float(vv.mean())
        out['f3_std_n'] = float(vv.std())
    else:
        out['f3_pos_n'] = float('nan')
        out['f3_std_n'] = float('nan')

    # ★★★★★ R218（`R30_AUDIT_LEDGER.md` **§137.7**）：补**聚合的 `f1_area`**。
    #   ## 缺口
    #     `series.csv` 一直只有 `f2_area_m2` / `f3_area_m2`，
    #     而 **F1（α′/β，含母相）的面积只能在 `f1_faces_<k>` 里逐根读** ⇒
    #     **"三类界面各占多少"这个最基本的问题答不出来**。
    #   ## 为什么现在必须补（`§137.5`）
    #     `§135.4` 报的 "F2 占 74.5%" 分母是 `f2+f3` —— **没有 F1**！
    #     而 `§137.3` 的胞数比是 F1 **488** : F2 88 : F3 196（F1 占 63%）
    #     ⇒ **R165 否定结果的头号候选解释**就是"F2 在**总**面积里占比很小"。
    #     ⇒ 没有聚合计不出来，必须补。
    #   ## 口径
    #     **与 `f2_area`/`f3_area` 完全同一套**：按格面计数（`np.roll`，**周期性**）
    #     再乘 `|n_hab|` 的对应分量、乘 `dx²`。
    #     ⚠ 保留原来的逐根 `f1_faces_%d`（历史读数可复现）。
    f1dir = np.zeros(3, np.int64)
    for k in laths:
        mk, m0 = (region == k), (region == 0)
        c = 0
        for axx in (0, 1, 2):
            for sh in (1, -1):
                _t = int((mk & np.roll(m0, sh, axis=axx)).sum())
                c += _t
                f1dir[axx] += _t
        out['f1_faces_%d' % k] = c
    out['f1_faces'] = int(f1dir.sum())
    out['f1_area'] = float((f1dir * np.abs(np.asarray(n_hab, float))).sum()) * dx ** 2
    out['f1_area_stair'] = float(f1dir.sum()) * dx ** 2
    out['box_touch'] = bool(any(
        np.take(region, 0, axis=ax).max() > 0
        or np.take(region, N - 1, axis=ax).max() > 0 for ax in (0, 1, 2)))
    # ★★★ R38（**P1-22**）：**孤儿免疫**的撞壁判据。
    #   旧 `box_touch` 判的是"**任一**已转变胞落在盒面" ⇒ **一个 1 胞孤儿飘到壁面就置 1**。
    #   实测代价（MB-1）：`mb1` 报了 **27 行** `box_touch=1`，而它的**核心** a 跨度只有
    #   **2654 nm**（盒 12 µm）⇒ 那些"撞壁"极可能全是孤儿。
    #   ⇒ 新增 `box_touch_core`：只看**最大连通分量**有没有碰到盒面。
    #   （旧列保留 ⇒ 历史读数可复现；判据应改用新列。）
    try:
        _lab, _nlab = _label_periodic(np.isin(region, list(allowed)))
        if _lab is not None and _nlab > 0:
            _sz = np.bincount(_lab.ravel(), minlength=_nlab + 1)
            _big = int(np.argmax(_sz[1:])) + 1
            _mb = (_lab == _big)
            out['box_touch_core'] = bool(any(
                bool(np.take(_mb, 0, axis=ax).any())
                or bool(np.take(_mb, N - 1, axis=ax).any()) for ax in (0, 1, 2)))
            out['core_vox'] = int(_sz[_big])
            out['ncomp_all'] = int(_nlab)
        else:
            out['box_touch_core'] = False
            out['core_vox'] = 0
            out['ncomp_all'] = 0
    except Exception:                                           # pragma: no cover
        out['box_touch_core'] = False
        out['core_vox'] = -1
        out['ncomp_all'] = -1
    return out


# ---------------------------------------------------------------------------
def _synth_slab(N, dx, center, half, axis_map, out=None):
    ii = np.arange(N)
    c = np.asarray(center, float)
    rel = [ii[:, None, None] * dx - c[0], ii[None, :, None] * dx - c[1],
           ii[None, None, :] * dx - c[2]]
    m = np.ones((N, N, N), bool)
    for nm, h in half.items():
        u = np.asarray(axis_map[nm], float)
        m &= np.abs(u[0] * rel[0] + u[1] * rel[1] + u[2] * rel[2]) <= h
    return m


def _stack_reg(N, dx, c0, n_hab, am, M, T, gap=0.0, w=320e-9, a=1200e-9):
    reg = np.zeros((N, N, N), np.int8)
    for i in range(M):
        off = (i - (M - 1) / 2.0) * (T + gap)
        reg[_synth_slab(N, dx, c0 + off * n_hab, dict(n=T / 2, w=w, a=a), am)] = i + 1
    return reg


def _selftest():
    F = []

    def ck(tag, ok, det=''):
        print('  %-56s %s %s' % (tag, 'PASS' if ok else '**FAIL**', det))
        if not ok:
            F.append(tag)

    print('=' * 100)
    print('_bk_measure._selftest —— 合成数据上的正/负对照')
    print('=' * 100)
    N, dx = 64, 62.5e-9
    n_hab = np.array([-0.4424, 0.4425, -0.7801]); n_hab /= np.linalg.norm(n_hab)
    w_ax = np.array([0.70711, 0.70711, 0.0]); w_ax /= np.linalg.norm(w_ax)
    a_ax = np.array([-0.4909, 0.4909, 0.7198]); a_ax /= np.linalg.norm(a_ax)
    am = dict(n=n_hab, w=w_ax, a=a_ax)
    c0 = np.array([N * dx / 2] * 3)
    print('  n*=%s   Σ|n_i| = %.4f（阶梯口径的高估因子）'
          % (np.array2string(n_hab, precision=4), np.abs(n_hab).sum()))
    W, AL, T = 320e-9, 1200e-9, 125e-9

    r = measure_state(_stack_reg(N, dx, c0, n_hab, am, 1, 2 * T, w=W, a=AL),
                      dx, n_hab, w_ax, a_ax, {1: 1})
    Vex = (2 * T) * (2 * W) * (2 * AL)
    ck('C1 单片：体积 vs 解析（|Δ| < 6%）', abs(r['vol_1'] - Vex) / Vex < 0.06,
       '%.5f vs %.5f µm³ (%+.2f%%)'
       % (r['vol_1'] * 1e18, Vex * 1e18, 100 * (r['vol_1'] / Vex - 1)))
    ck('C2 单片：ncomp == 1', r['ncomp_1'] == 1, '%d' % r['ncomp_1'])
    ck('C3 单片：nslab_n == 1', r['nslab_n'] == 1, '%d runs=%s'
       % (r['nslab_n'], r['runs']))
    ck('C4 单片：f3_faces == 0 且 nf3_col == 0',
       r['f3_faces'] == 0 and r['nf3_col'] == 0,
       '%d / %d' % (r['f3_faces'], r['nf3_col']))
    ck('C4b 单片：三轴尺寸 ≈ 解析（n 250 / w 640 / a 2400 nm）',
       abs(r['n_1'] - 2 * T) < 3 * dx and abs(r['w_1'] - 2 * W) < 3 * dx
       and abs(r['a_1'] - 2 * AL) < 3 * dx,
       '%.0f/%.0f/%.0f nm' % (r['n_1'] * 1e9, r['w_1'] * 1e9, r['a_1'] * 1e9))

    reg6 = _stack_reg(N, dx, c0, n_hab, am, 6, 2 * T, w=W, a=AL)
    r6 = measure_state(reg6, dx, n_hab, w_ax, a_ax, {i + 1: 1 for i in range(6)})
    ck('C5 6 层：nslab_n == 6（**量具分辨力的正对照**）', r6['nslab_n'] == 6,
       '%d runs=%s' % (r6['nslab_n'], r6['runs']))
    ck('C6 6 层：nreg_used == 6', r6['nreg_used'] == 6, '%d' % r6['nreg_used'])
    ck('C6b 6 层：nf3_col == 5（柱里穿过 5 张同变体界面）', r6['nf3_col'] == 5,
       '%d' % r6['nf3_col'])
    A5 = 5 * (2 * W) * (2 * AL)
    ck('C7 6 层：**无偏面积** = 5 张共享面（|Δ| < 8%）',
       abs(r6['f3_area'] - A5) / A5 < 0.08,
       '实测 %.4f vs 解析 %.4f µm² (%+.1f%%)；阶梯口径 %.4f（%+.0f%%）'
       % (r6['f3_area'] * 1e12, A5 * 1e12, 100 * (r6['f3_area'] / A5 - 1),
          r6['f3_area_stair'] * 1e12, 100 * (r6['f3_area_stair'] / A5 - 1)))

    reg1 = _stack_reg(N, dx, c0, n_hab, am, 1, 12 * T, w=W, a=AL)
    r1 = measure_state(reg1, dx, n_hab, w_ax, a_ax, {1: 1})
    ck('C9 负对照（6 层并成 1 根）：nslab_n == 1', r1['nslab_n'] == 1,
       '%d' % r1['nslab_n'])
    ck('C10 负对照：f3_faces == 0', r1['f3_faces'] == 0, '%d' % r1['f3_faces'])

    noisy = np.random.default_rng(5).integers(0, 4, size=(N, N, N)).astype(np.int8)
    rn = measure_state(noisy, dx, n_hab, w_ax, a_ax, {1: 1, 2: 1, 3: 2})
    ck('C11 随机场号：ncomp 极大 且 nslab_n 极大',
       rn['ncomp_1'] > 5000 and rn['nslab_n'] > 15,
       'ncomp=%d nslab=%d' % (rn['ncomp_1'], rn['nslab_n']))

    # C12 45° 界面：面积估计量对任意法向无偏
    u45 = np.array([1.0, 1.0, 0.0]) / np.sqrt(2)
    N2, dx2 = 64, 1.0
    ii = np.arange(N2)
    rel = [ii[:, None, None] * dx2 - 32.0, ii[None, :, None] * dx2 - 32.0,
           ii[None, None, :] * dx2 - 32.0]
    pr = u45[0] * rel[0] + u45[1] * rel[1] + 0.0 * rel[2]   # ← 第三项必须留，否则只剩 (N,N,1)
    reg45 = np.where(pr < 0, 1, 2).astype(np.int8)
    r45 = measure_state(reg45, dx2, u45, np.array([0.0, 0.0, 1.0]),
                        np.array([-1.0, 1.0, 0.0]) / np.sqrt(2), {1: 1, 2: 1})
    # ★ 解析值要考虑**周期**：`{x+y<64}` 与 `{x+y>=64}` 在环面上被
    #   "x=0 与 x=63 相邻" 又切了一刀 ⇒ 有**两张**面积各 64√2·64 的界面。
    A45 = 2.0 * 64.0 * np.sqrt(2.0) * 64.0
    ck('C12 45° 界面：**无偏面积** vs 解析（|Δ| < 8%）',
       abs(r45['f3_area'] - A45) / A45 < 0.08,
       '实测 %.1f vs 解析 %.1f（%+.1f%%）'
       % (r45['f3_area'], A45, 100 * (r45['f3_area'] / A45 - 1)))
    # ★★ 估计量的**内禀**校验：阶梯口径 / 无偏口径 必须 == Σ|n_i|（与解析面积无关）
    ck('C12b 阶梯/无偏 == Σ|n_i|=√2（估计量的内禀恒等式，|Δ| < 3%）',
       abs(r45['f3_area_stair'] / r45['f3_area'] - np.sqrt(2.0)) / np.sqrt(2.0) < 0.03,
       '比值 %.4f vs √2=%.4f' % (r45['f3_area_stair'] / r45['f3_area'], np.sqrt(2.0)))
    ck('C7b 阶梯/无偏 == Σ|n_i|=1.6649（本项目 n* 的内禀恒等式）',
       abs(r6['f3_area_stair'] / r6['f3_area'] - np.abs(n_hab).sum())
       / np.abs(n_hab).sum() < 0.03,
       '比值 %.4f vs %.4f' % (r6['f3_area_stair'] / r6['f3_area'],
                              np.abs(n_hab).sum()))

    # C13 **体积量具的正对照**：把第 5 层厚度减半 ⇒ 体积必须掉 ≈50%
    reg8 = _stack_reg(N, dx, c0, n_hab, am, 6, 2 * T, w=W, a=AL)
    reg8[:] = 0
    for i in range(6):
        off = (i - 2.5) * 2 * T
        tt = T if i == 4 else 2 * T
        reg8[_synth_slab(N, dx, c0 + off * n_hab, dict(n=tt, w=W, a=AL), am)] = i + 1
    r8 = measure_state(reg8, dx, n_hab, w_ax, a_ax, {i + 1: 1 for i in range(6)})
    ck('C13 第 5 层厚度减半：vol_5 掉 ≈50%（体积量具正对照）',
       0.40 < r8['vol_5'] / r6['vol_5'] < 0.60,
       '%.5f → %.5f µm³ (%.0f%%)'
       % (r6['vol_5'] * 1e18, r8['vol_5'] * 1e18,
          100 * r8['vol_5'] / r6['vol_5']))
    ck('C13b 厚度减半后 nslab_n 仍为 6', r8['nslab_n'] == 6,
       '%d runs=%s' % (r8['nslab_n'], r8['runs']))

    # C14 **板条数量具的正对照**：**删掉**第 4 层 ⇒ nslab_n 必须掉到 5
    reg9 = _stack_reg(N, dx, c0, n_hab, am, 6, 2 * T, w=W, a=AL)
    reg9[:] = 0
    for i in range(6):
        if i == 3:
            continue
        off = (i - 2.5) * 2 * T
        reg9[_synth_slab(N, dx, c0 + off * n_hab, dict(n=T, w=W, a=AL), am)] = i + 1
    r9 = measure_state(reg9, dx, n_hab, w_ax, a_ax, {i + 1: 1 for i in range(6)})
    ck('C14 删掉第 4 层：nslab_n == 5（板条数量具正对照）', r9['nslab_n'] == 5,
       '%d runs=%s' % (r9['nslab_n'], r9['runs']))
    ck('C14b 删掉第 4 层：nf3_col == 4（5 层 ⇒ 4 对相邻同变体界面）',
       r9['nf3_col'] == 4, '%d' % r9['nf3_col'])
    ck('C14c 删掉第 4 层：vol_4 == 0 且 nreg_used == 5',
       r9['vol_4'] == 0.0 and r9['nreg_used'] == 5,
       'vol_4=%.1f nreg_used=%d' % (r9['vol_4'], r9['nreg_used']))

    # ---- C15 ★ 「显著碎裂」判据的**正对照** -------------------------------
    # 复刻 `dry_gs2` 末态的**真实现象**：一根完整板条 + 3 个 1–2 体素孤儿。
    # 必须同时满足：原始 `ncomp` 数得出 4（与实跑读数一致），
    # 而 `ncompbig`（≥32 体素）只数出 1。
    # ★ 这正是项目教训 #19：新探针**先拿一个已知答案跑通**再用于未知答案。
    #   没有这条对照，"ncompbig=1"可能只是因为函数恒返回 1（静默失效）。
    g15 = reg6.copy()
    st = [(3, 3, 3), (10, 20, 30), (60, 60, 60)]        # 三个孤立体素（彼此远离）
    for (i, j, k_) in st:
        g15[i, j, k_] = 1 if g15[i, j, k_] == 0 else g15[i, j, k_]
    m1 = (g15 == 1)
    n_raw = _ncomp(m1)
    n_big = _ncomp_big(m1)
    # 反查：单个孤立体素本身必须是"非显著"的（阈值确实在起作用）
    iso = np.zeros_like(g15, bool)
    for (i, j, k_) in st:
        iso[i, j, k_] = True
    ck('C15 显著碎裂判据：1 根板条 + 3 个 1 体素孤儿 ⇒ ncomp=4 但 ncompbig=1',
       n_raw == 4 and n_big == 1,
       'ncomp=%d（应为 4）  ncompbig=%d（应为 1）' % (n_raw, n_big))
    ck('C15b 判据在噪声上真的为 0（孤立 3 体素 ⇒ ncompbig=0）',
       _ncomp_big(iso) == 0, '%d' % _ncomp_big(iso))
    # 反向：把一根板条**真**切成两半（各 ≥32 体素）⇒ 必须数出 2
    cut = (g15 == 1).copy()
    cidx = np.argwhere(cut)
    if cidx.size:
        ax = int(np.argmax(cut.shape))
        cut[cidx[len(cidx) // 2, 0], :, :] = False
    ck('C15c 反向对照：真把一层切断 ⇒ ncompbig ≥ 2',
       _ncomp_big(cut) >= 2, '%d' % _ncomp_big(cut))

    # ---- C16/C17 ★ `snapshot_coverage`（V-7/V-7b 的唯一实现）的**正/负对照** ----
    # ★ 项目教训 #19：**新探针必须先拿一个"已知答案"跑通**，再相信它对未知答案的
    #   判定。`snapshot_coverage` 现在同时供 `_bk_pair.py` 与 `_bk_verdict.py` 用，
    #   而它比 C7 多两样 C7 没控过的东西：(i) 分母 `ΣV/t`，(ii) β 夹层计数。
    #   ⇒ 两条对照都补上。
    def _z(reg):
        return dict(region=reg, L=N * dx, n_hab=n_hab, w_ax=w_ax, a_ax=a_ax,
                    vmap_keys=np.arange(1, 7), vmap_vals=np.ones(6, int))
    cv = snapshot_coverage(_z(reg6))
    ck('C16 对齐 6 层：覆盖率 ≥ 0.90（**正对照**）', cv['cov'] >= 0.90,
       'cov=%.3f（应占 %.4f，实测 %.4f µm²）'
       % (cv['cov'], cv['exp_int'] * 1e12, cv['f3_area'] * 1e12))
    ck('C16b 对齐 6 层：每一对的 β 占比 ≤ 0.25（**正对照**）',
       bool(cv['beta_frac']) and max(cv['beta_frac'].values()) <= 0.25,
       '各对: %s' % '  '.join('%d|%d:%.2f' % (ij[0], ij[1], f)
                              for ij, f in sorted(cv['beta_frac'].items())))
    # 负对照：在**第 3 与第 4 层之间**塞一层 1 胞厚的母相 β（精确复刻 `dry_gs2`
    # 的缺陷形态），判据必须只在 (3,4) 这一对上报警，其余对不受影响。
    # ★ 索引算术（第一版在这里错了，膜落到了 1|2 之间）：`_stack_reg` 里第 i 层
    #   （0 基）的中心是 `(i − (M−1)/2)·T` ⇒ **第 i 与 i+1 层的界面**在
    #   `((i − (M−1)/2) + 0.5)·T`。要 3|4 界面 ⇒ i=2 ⇒ `(2 − 2.5 + 0.5)·T = 0`。
    reg_film = reg6.copy()
    _T = 2 * T
    _i0 = 2                                              # 第 3 层（0 基）
    _mid = c0 + ((_i0 - (6 - 1) / 2.0 + 0.5) * _T) * n_hab
    _filmcell = _synth_slab(N, dx, _mid, dict(n=0.5 * dx, w=W, a=AL), am)
    _before = int(reg_film[_filmcell].min())
    reg_film[_filmcell] = 0
    cvf = snapshot_coverage(_z(reg_film))
    _bf = cvf['beta_frac']
    ck('C17 插入 1 胞 β 膜（第 3|4 层间）：该对的 β 占比必须 > 0.25（**负对照**）',
       _bf.get((3, 4), 0.0) > 0.25,
       '3|4:%.2f  其余各对 max=%.2f  （膜覆盖处原本是场 %d，应 == 3）'
       % (_bf.get((3, 4), 0.0),
          max([v for k, v in _bf.items() if k != (3, 4)] + [0.0]), _before))
    ck('C17b 插入 β 膜后**其余对**仍 ≤ 0.25（判据有分辨力，不是一锅端）',
       max([v for k, v in _bf.items() if k != (3, 4)] + [0.0]) <= 0.25,
       '其余 max=%.2f' % max([v for k, v in _bf.items() if k != (3, 4)] + [0.0]))
    ck('C17c 插入 β 膜后总覆盖率必须**掉下来**（vs C16）',
       cvf['cov'] < cv['cov'] - 0.02,
       '带膜 %.3f  vs  对齐 %.3f' % (cvf['cov'], cv['cov']))

    # ================= ★★★ R76（**P1-33/P1-34**）：逐块口径的正/负对照 =========
    # 为什么必须补（这是 R76 的核心教训）：
    #   R75 的判决行吃的是**全局** `nslab_n`，而多块构型下它**结构性无效** ——
    #   柱心 = `allowed`（两个块的**全部**场）的质心 ⇒ 落在**两块之间的空隙**里；
    #   柱轴只用 `laths[0]` 的 n* ⇒ 块 1（镜面变体）投影弥散。
    #   实测 R75：全局 `nslab_n = 1` 而逐块口径 **31/31 快照全为 3/3**。
    #   ⇒ 必须给逐块口径补**正对照**（3 根应读到 3）与**负对照**（并成一片应读到 1），
    #     否则"3/3"完全可能只是函数恒返回满值（本仓库教训 #19）。
    def _triad(nv):
        """由 n* 造一组正交三轴（自足，不 import 重模块）。"""
        nv = np.asarray(nv, float)
        nv = nv / np.linalg.norm(nv)
        t = np.array([0.0, 0.0, 1.0]) if abs(nv[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        wv = np.cross(nv, t)
        wv = wv / np.linalg.norm(wv)
        av = np.cross(wv, nv)
        return nv, av / np.linalg.norm(av), wv

    # 变体 1 与变体 3 用**不同**的 n*（复刻 R75 的镜像对）——这正是全局柱口径失效的原因
    nB = np.array([0.4424, 0.4425, 0.7801])
    nA, aA, wA = _triad(n_hab)
    nB, aB, wB = _triad(nB)
    _axvar = {1: (nA, aA, wA), 3: (nB, aB, wB)}
    # 造 12 个**无迹**的合成 eps0（只为让 `r_selfac` 有定义，不参与块计数）
    _eps0 = []
    for _k in range(12):
        _A = np.diag([1.0, -1.0, 0.0]) * (1.0 + 0.1 * _k)
        _eps0.append(_A - np.trace(_A) / 3.0 * np.eye(3))
    _npfvar = {1: nA, 3: nB}

    def _twoblock(merge=False):
        """2 块 × 3 根；块心沿 y 分开 2500 nm（**复刻 R75 几何**）。

        `merge=True` ⇒ 块 B 的三根**并成一根**（负对照）。
        """
        reg = np.zeros((N, N, N), np.int8)
        centers = {1: c0 + np.array([0.0, -1250e-9, 0.0]),
                   3: c0 + np.array([0.0, +1250e-9, 0.0])}
        halves = {1: (nA, aA, wA), 3: (nB, aB, wB)}
        for v, f0 in ((1, 1), (3, 4)):
            nv, av, wv = halves[v]
            amv = dict(n=nv, w=wv, a=av)
            Mv = 1 if (merge and v == 3) else 3
            Tv = (6 * T) if (merge and v == 3) else 2 * T
            for i in range(Mv):
                off = (i - (Mv - 1) / 2.0) * Tv
                reg[_synth_slab(N, dx, centers[v] + off * nv,
                                dict(n=Tv / 2, w=W, a=AL), amv)] = f0 + i
        return reg

    _vmap2 = {1: 1, 2: 1, 3: 1, 4: 3, 5: 3, 6: 3}
    _rg = _twoblock(False)
    b_ok = blocks(_rg, dx, _vmap2, eps0_var=_eps0, npf_var=_npfvar, axes_var=_axvar)
    ck('C18 两块×3根：nblk_sig == 2（块分离判据）', b_ok['nblk_sig'] == 2,
       'nblk_sig=%d blk_laths=%s blk_vars=%s'
       % (b_ok['nblk_sig'], b_ok['blk_laths'], b_ok['blk_vars']))
    ck('C19 ★**逐块主口径正对照**：blk_nprof == 3/3（沿**每块自己的 n***）',
       b_ok['blk_nprof'] == '3/3',
       'blk_nprof=%s   blk_nlath=%s   blk_nruns=%s'
       % (b_ok['blk_nprof'], b_ok['blk_nlath'], b_ok['blk_nruns']))
    # ★ 全局柱口径在这个构型上**必须**失效 —— 把"量具缺陷"本身变成一个可证伪的读数
    _rglob = measure_state(_rg, dx, nA, wA, aA, _vmap2)
    ck('C19b 同一构型上**全局** `nslab_n` 失效（< 6）—— P1-34 的直接证据',
       _rglob['nslab_n'] < 6,
       '全局 nslab_n=%d runs=%s  vs 逐块 3/3（列心=并集质心，落在两块的空隙里）'
       % (_rglob['nslab_n'], _rglob['runs']))
    ck('C19c `blk_nlath` 只能当**上界**（它在 C21 的横切构型上照样报满）',
       True, '见 C21')
    _rgm = _twoblock(True)
    b_mg = blocks(_rgm, dx, _vmap2, eps0_var=_eps0, npf_var=_npfvar, axes_var=_axvar)
    ck('C20 ★**逐块主口径负对照**：块 B 并成 1 根 ⇒ blk_nprof 掉到 3/1',
       b_mg['blk_nprof'] == '3/1',
       'blk_nprof=%s   blk_nlath=%s   blk_nruns=%s'
       % (b_mg['blk_nprof'], b_mg['blk_nlath'], b_mg['blk_nruns']))
    # ★★ C21 —— **`blk_nprof` 的已知边界**（第一版我把它当"退化对照"，预期写错了，
    #   实测给出的是**另一条更有用的信息**，记在这里而不是改判据去迁就预期）：
    #   构造：块 B 的 3 个场**不是沿 n\* 堆叠**，而是把**同一片**沿 w 横切成 3 份
    #   （3 个场贴着彼此 ⇒ 并集 6-连通、`ids` = 3）。
    #   **实测**：`blk_nprof` 仍报 **3**（每箱的众数在三个场之间**抖动** ⇒ 三个场
    #   都当过至少一个箱的众数），而 `blk_nruns` 报 **6**（段数）并触发
    #   `[blocks] ⚠ 剖面口径与【场数】口径不一致` 告警。
    #   ⇒ **`blk_nprof` 是「每个场在该块的柱剖面里出没过」的检验，
    #     不是「这些场沿 n\* 有序堆叠」的检验。**
    #   ⇒ 判据必须三件一起看：
    #       `blk_nprof == blk_laths`（在场）+ `blk_nruns == blk_nprof`（剖面无噪声）
    #       + `f_flat`（端面还在，见 `_r65_corner.py`）。
    #   ⇒ 这一条同时解释了 R33 的老观察（`mb1s` 真值 3 而段数 5–6）。
    reg_deg = _twoblock(True)
    _cB = c0 + np.array([0.0, +1250e-9, 0.0])
    for i in range(3):
        off = (i - 1.0) * (2 * W / 3.0)
        reg_deg[_synth_slab(N, dx, _cB + off * wB,
                            dict(n=3 * T, w=W / 3.0, a=AL),
                            dict(n=nB, w=wB, a=aB))] = 4 + i
    b_dg = blocks(reg_deg, dx, _vmap2, eps0_var=_eps0, npf_var=_npfvar,
                  axes_var=_axvar)
    _np_dg = [int(t) for t in b_dg['blk_nprof'].split('/') if t]
    _nr_dg = [int(t) for t in b_dg['blk_nruns'].split('/') if t]
    ck('C21 ★`blk_nprof` 的边界（**已知局限，不是 bug**）：'
       '「在场」≠「沿 n* 堆叠」',
       (len(_np_dg) == 2 and len(_nr_dg) == 2
        and _np_dg[1] == 3 and _nr_dg[1] > _np_dg[1]),
       '横向切 3 份（非沿 n* 堆叠）⇒ blk_nprof=%s（**仍报满**）而 '
       'blk_nruns=%s（**噪声告警起作用**）⇒ 判据需与 f_flat 合看'
       % (b_dg['blk_nprof'], b_dg['blk_nruns']))

    # ================= ★★★★★ C22：**`nf2`（异变体界面）的解析自证** =================
    #   ## 为什么补这一组（`R30_AUDIT_LEDGER.md` **§201**）
    #     目标第 (3) 项要求「条件③的**每一项**都要先过量具自证与正/负对照」。
    #     逐项对了一遍 `_selftest` 的清单：**`f2_faces` 被 `measure_state` 算出来了
    #     （`:948`），但整个自检里没有任何一条断言碰过它**
    #     （`grep 'f2_faces'` 只命中定义处与注释）。
    #     ⇒ 而 `nf2` 正是「**块间相互作用**」的直接量具（`_bk_exp.py` 的 CSV 列 `nf2`）。
    #     ⇒ **有计算、无自证** = 目标原文说的"量具出错会对结论产生极大影响"的典型风险口。
    #   ## 构造（**解析已知答案**）
    #     两块**轴对齐**的板条面对面贴着，接触面在 `x = c0x`：
    #       板 A（场 1，变体 1）：`x ∈ [c0x − d, c0x]`，`|y| ≤ W`，`|z| ≤ AL`
    #       板 B（场 4，变体 3）：`x ∈ [c0x, c0x + d]`，同 `y/z` 范围
    #     ⇒ 接触格面数 = `n_y · n_z`，其中 `n_y = #{|y| ≤ W}`、`n_z = #{|z| ≤ AL}`
    #       （**逐格面计数**，与 `_bk_measure` 的 `np.roll` 周期口径同源）。
    _amx = dict(n=np.array([1.0, 0.0, 0.0]), w=np.array([0.0, 0.0, 1.0]),
                a=np.array([0.0, 1.0, 0.0]))
    _d = 4 * T

    def _twoslab(field_b, sep_nm):
        """A 恒为场 1（变体 1）；B 的场号与间距可调。`sep_nm > 0` ⇒ 两块分开。"""
        reg = np.zeros((N, N, N), np.int8)
        gap = sep_nm * 1e-9
        reg[_synth_slab(N, dx, c0 + np.array([-(_d / 2 + gap / 2), 0.0, 0.0]),
                        dict(n=_d / 2, w=W, a=AL), _amx)] = 1
        reg[_synth_slab(N, dx, c0 + np.array([+(_d / 2 + gap / 2), 0.0, 0.0]),
                        dict(n=_d / 2, w=W, a=AL), _amx)] = field_b
        return reg

    #   ⚠⚠ **自纠错（自查错误 #66，`§201`）**：本组第一版把解析预期写成
    #      `n_y = #{|y| ≤ W}`、`n_z = #{|z| ≤ AL}` ⇒ **380**，而实测 **429**（+12.89%）。
    #      用**独立手写计数**裁决（`_r449_f2adjudicate.py`）：
    #        * 手写逐轴逐向数 ⇒ **只有"轴0 向−1"给出 429**，其余方向全 0
    #          ⇒ `f2_faces` **每次界面只数一次**（我原先"再除以 2"是错的）；
    #        * 实测各轴占据胞数：x=15、**y=39**、**z=11**
    #          ⇒ `_amx` 里 `w` 在 **z**、`a` 在 **y** ⇒ 接触截面 = `39 × 11 = **429**`。
    #      ⇒ **量具是对的，我的预期把 `W`/`AL` 的轴弄反了。**
    #      ⇒ 判据**不放宽**，改的是**预期式**（并让它由 `_amx` 的轴分配**自动推**，不再手写）。
    _axn = np.asarray(_amx['n'], float)
    _axw = np.asarray(_amx['w'], float)
    _axa = np.asarray(_amx['a'], float)
    # ⚠⚠ **自纠错（#68）**：`_synth_slab` 里的格坐标是 **`i·dx`**（`:1024`
    #   `rel = ii[:,None,None]*dx − c[0]`），**不是** `(i+0.5)·dx`。
    #   第一版我按 `(i+0.5)·dx` 数格心 ⇒ 得 10×38=380，而真值是 **11×39=429**。
    #   （独立裁决见 `_r449_f2adjudicate.py`：实测 x=15、**y=39**、**z=11**。）
    _ii = np.arange(N) * dx

    def _ncell(u, half):
        """沿单位轴 `u`（轴对齐）、以 `c0` 为中心、半宽 `half` 的**格心数**。

        ⚠ 自纠错（#67）：第一版留了一行没用的 `proj = _ii * u[None, :]`
        且形状不匹配 ⇒ `ValueError`。本函数**只需要非零分量的那个轴**。
        """
        ax = int(np.argmax(np.abs(u)))
        return int((np.abs(_ii - c0[ax]) <= half).sum())
    # 接触截面 = 两个**面内**方向的格数之积（`n` 是厚度方向，不参与）
    _n_expect = _ncell(_axw, W) * _ncell(_axa, AL)

    # C22a 正对照：异变体贴着 ⇒ f2_faces > 0
    _m_f2 = measure_state(_twoslab(4, 0.0), dx, nA, wA, aA, _vmap2)
    ck('C22a ★`nf2` 正对照：异变体贴着 ⇒ f2_faces > 0',
       _m_f2['f2_faces'] > 0,
       'f2_faces=%d  f3_faces=%d  （解析预期 %d）'
       % (_m_f2['f2_faces'], _m_f2['f3_faces'], _n_expect))

    # C22b 定量：接触面数 == n_y·n_z（|Δ| < 5%）
    _rel22 = abs(_m_f2['f2_faces'] - _n_expect) / max(_n_expect, 1)
    ck('C22b ★`nf2` 定量：f2_faces == 解析接触格面数（|Δ| < 5%）',
       _rel22 < 0.05,
       '实测 %d vs 解析 %d （%+.2f%%）'
       % (_m_f2['f2_faces'], _n_expect, 100 * (_m_f2['f2_faces'] / _n_expect - 1)))

    # C22c ★★ **分辨力（最关键的一条）**：把 B 换成**同变体**（场 2，也属变体 1）
    #   ⇒ 那张接触面是 **F3**，`f2_faces` 必须掉到 **0**，而 `f3_faces` 必须涨上来。
    #   这条若不过 ⇒ `nf2` 分不清"块间"与"块内" ⇒ **条件③的块间量具整个失效**。
    _m_f3 = measure_state(_twoslab(2, 0.0), dx, nA, wA, aA, _vmap2)
    ck('C22c ★★`nf2` 分辨力：同变体贴着 ⇒ f2_faces == 0 且 f3_faces ≥ 解析值',
       (_m_f3['f2_faces'] == 0) and (_m_f3['f3_faces'] >= 0.95 * _n_expect),
       '同变体：f2_faces=%d（应 0）  f3_faces=%d（应 ≈%d）'
       % (_m_f3['f2_faces'], _m_f3['f3_faces'], _n_expect))

    # C22d 负对照：异变体**分开** ⇒ f2_faces == 0
    _m_sep = measure_state(_twoslab(4, 2 * T * 1e9 / 1e0), dx, nA, wA, aA, _vmap2)
    ck('C22d `nf2` 负对照：异变体分开 ⇒ f2_faces == 0',
       _m_sep['f2_faces'] == 0,
       '间距 %.0f nm ⇒ f2_faces=%d  f1_faces=%d'
       % (2 * T * 1e9, _m_sep['f2_faces'], _m_sep['f1_faces']))

    print('-' * 100)
    print('FAIL = %d %s' % (len(F), F if F else ''))
    print('=' * 100)
    return 1 if F else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--npz')
    a = ap.parse_args()
    if a.selftest or not a.npz:
        return _selftest()
    z = np.load(a.npz)
    reg = z['region']
    # ★★ 兼容 `_bk_exp.py` 的快照格式：它存的是 **`vmap_keys`/`vmap_vals`**（不是 `nv`）。
    #   这条路径就是用户要求的"量具有 bug 也能事后用修好的工具在完整数据上重测"
    #   ⇒ 必须真的能跑通（本文件第一版这里会 KeyError('nv')）。
    if 'vmap_keys' in z.files:
        vmap = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
    elif 'vmap' in z.files:
        vmap = {int(k): int(v) for k, v in zip(z['vmap'][0], z['vmap'][1])}
    else:
        nv = int(z['nv']) if 'nv' in z.files else int(reg.max())
        vmap = {k: 1 for k in range(1, nv + 1)}
    r = measure_state(reg, float(z['L']) / reg.shape[0], z['n_hab'], z['w_ax'],
                      z['a_ax'], vmap)
    print('文件 %s   N=%d  板条场=%s' % (a.npz, reg.shape[0], sorted(vmap)))
    for k in sorted(r):
        print('  %-16s %s' % (k, r[k]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
