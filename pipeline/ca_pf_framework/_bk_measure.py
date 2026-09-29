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


def _ncomp(mask):
    """6-连通、**周期**边界下的连通分量数。"""
    if not mask.any():
        return 0
    if not _HAVE_SCIPY:
        raise RuntimeError('需要 scipy.ndimage 才能可靠地数周期连通分量')
    lab, n = ndi.label(mask, structure=ndi.generate_binary_structure(3, 1))
    if n <= 1:
        return int(n)
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
    return len({find(i) for i in range(1, n + 1)})


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


def measure_state(region, dx, n_hab, w_ax, a_ax, vmap, r_col=300e-9):
    """对一个状态做全套测量。`vmap` : {场号: 变体号}（只含板条场，不含母相 0）。"""
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
        if k in allowed:
            for nm in ('n', 'w', 'a'):
                e, eb = _linear_extent(m, axes[nm], dx)
                out['%s_%d' % (nm, k)] = e
                out['%sb_%d' % (nm, k)] = eb
    out['nreg_used'] = int(sum(1 for k in laths if out['vol_%d' % k] > 0))
    out['M'] = len(laths)

    prof, runs = column_profile(region, dx, n_hab, w_ax, a_ax, allowed, r_col)
    out['nslab_n'] = len(runs)
    out['runs'] = ','.join(str(x) for x in runs)
    out['nf3_col'] = _same_variant_adjacent(runs, vmap)

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

    for k in laths:
        mk, m0 = (region == k), (region == 0)
        c = 0
        for axx in (0, 1, 2):
            for sh in (1, -1):
                c += int((mk & np.roll(m0, sh, axis=axx)).sum())
        out['f1_faces_%d' % k] = c
    out['box_touch'] = bool(any(
        np.take(region, 0, axis=ax).max() > 0
        or np.take(region, N - 1, axis=ax).max() > 0 for ax in (0, 1, 2)))
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
