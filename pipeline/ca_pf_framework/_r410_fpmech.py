#!/usr/bin/env python3
"""_r410_fpmech.py —— ★ **`--facet-proj` 抹掉块内 F3 的机理直测**（离线、可证伪）。

## 为什么要写这个
`§185` 实测（单变量、干净）：
  * `--facet-proj 10`：`blk_nprof` 由 `2/2/2/2/2/2` → step 20 变成 **10 块（8 个单板条）**，
    `nf3` 由 **1169 → 2**；
  * `--facet-proj 0`：`blk_nprof` 全程 `2/2/2/2/2/2`，`nf3` 只由 1169 → 1049。
⇒ 投影**把块内低角界面（F3）打断了**。这是**物理图像本身是否成立**的问题（goal 第 (2) 项）。

## 代码里读出来的疑点（**待本脚本证实/证伪**）
`windowB_surface.facet_project()`（`:2631`）为每个场构造**排除掩码**
`excl` = "与**同变体的另一个场**相邻的胞"膨胀 `pad=2` 层，交给
`_r68_facet_op.facet_project_one(..., excl=excl)`。
而后者（`:40-50`）：
    `_pts_mask = body & (~excl)`          # ← 只影响**取跨度的点云**
    `tgt      = v0 = body.sum()`          # ← 体积靶仍是**整个体**
    `s = (tgt / vp) ** (1/3)`             # ← 于是**必须放大**
**推理**：沿 F3 法向被内缩 `2Δx`，而体积靶没跟着减 ⇒ `s > 1` ⇒ 盒子**绕中心各向同性放大**
⇒ 沿 F3 法向净**内缩**（因为那是唯一被内缩的轴），而沿 `a`/`w` **外扩**
⇒ 同变体相邻两场的盒子之间**张开一条缝** ⇒ 缝里的胞不属于任何场 ⇒ `region = 0`（**β 膜**）
⇒ F3 被打断、每根板条各自成一个块。**这正是 `§185` 观测到的形态。**

## 本脚本做什么（**全部离线，不跑仿真**）
1. 读 `snap_00000.npz` 的 `region`（= 播种后、未推进的构型）；
2. 按**与驱动逐字相同**的方式重建逐场轴表 `npref_tab / atab / wtab`；
3. 对每个场**原样调用** `facet_project_one`（含 `excl`）——`phi` 用
   `∓1·Δx` 的二值场代替：**算子只从 `phi` 取 `(phi<0)` 这一个信息**
   （`_r68_facet_op.py:33`），所以二值替代对 `body` 是**精确**的，不是近似；
4. 量：投影前后的 F3/F2/F1 面数、以及"原先属于某场、投影后不属于任何场"的胞数
   （= **β 膜**，直接可证伪的量）；
5. **正对照**：解析长方体上算子幂等（`_r68_facet_op.selftest` 同款）；
6. **负对照**：`excl=None`（R73 之前的行为）跑同一构型，看 F3 是否保住。

⚠ 本脚本**只读**快照、**只调用**算子，不写任何归档产物。
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import windowB_surface as W                                    # noqa: E402
import windowB_lath as WL                                      # noqa: E402
from T16_verify_rve import C, EPS0, NPF                        # noqa: E402
from _r68_facet_op import facet_project_one                    # noqa: E402

RUN = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mb/dry_saSet2'
STEP = int(sys.argv[2]) if len(sys.argv) > 2 else 0

PAD = 2          # 与 `facet_project` 的 `pad` 逐字一致


def P(s):
    print(s, flush=True)


# ---------------------------------------------------------------- 面计数
def face_counts(reg, vmap, skip_zero_empty=True):
    """按**变体**分类的界面 COUNT（周期性）。返回 (n_f1, n_f2, n_f3, n_face_all).

    分类依据 `vmap`（场→变体）：
      * 0  <-> >0  ⇒ **F1**（母相-析出相）
      * >0 <-> >0，变体**不同** ⇒ **F2**
      * >0 <-> >0，变体**相同** ⇒ **F3**（低角晶界）
    """
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


def connected_blocks(reg, vmap):
    """同变体的 6-连通块计数（`_bk_measure.blocks` 的同口径简化版）。

    返回 (n_block, sorted sizes desc, per-block variant)。
    只用 `scipy.ndimage.label`（周期性用 3×3×3 拼接技巧）。
    """
    from scipy import ndimage
    out = []
    seen = np.zeros(reg.shape, bool)
    # 逐个场号做连通标记即可：同变体的不同场在 `region` 里**本来就是不同标号**，
    # 所以"同变体块"= 相邻场号的并集，必须先按变体合并。
    for v in sorted(set(vmap.values())):
        ks = [k for k, vv in vmap.items() if vv == v]
        m = np.isin(reg, ks)
        if not m.any():
            continue
        # 周期性连通：把场在 3 个方向各平移一次与自身相交（`np.roll` 语义）
        lab, n = ndimage.label(m, structure=ndimage.generate_binary_structure(3, 1))
        # 合并周期性接壤的标号（简单做法：用 roll 找跨边界的邻居对）
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
            out.append((v, s))
    out.sort(key=lambda t: -t[1])
    return len(out), out


def axes_tables(laths, vmap):
    """**与驱动逐字相同**地重建逐场轴表。

    `_bk_exp.py:539`：`eps0 = [EPS0[v-1] for v in laths_eff]`
    ⇒ 引擎的 `self.atab[k]` / `self.wtab[k]`（在 `windowB_surface.__init__` 里
      由传入的 `eps0` 逐行算得）**就是逐场（不是逐变体）**的。
    `npref_tab[k]` = `NPF[v]`（`LathTable.npref[i+1] = npref_var[v]`，**未做 ladder 旋转**）。
    """
    M = len(laths)
    npref = {}
    atab = {}
    wtab = {}
    for i, v in enumerate(laths):
        k = i + 1
        E = np.asarray(EPS0[v - 1], float)
        nref, _, _ = W.argmin_normal_cached(C, E)
        R = W.LevelSetMulti._rank1_axes(E, nref)
        npref[k] = np.asarray(NPF[v], float) / np.linalg.norm(np.asarray(NPF[v], float))
        atab[k] = np.asarray(R[1], float) / np.linalg.norm(np.asarray(R[1], float))
        wtab[k] = np.asarray(R[2], float) / np.linalg.norm(np.asarray(R[2], float))
    return npref, atab, wtab


# ---------------------------------------------------------------- 正对照
def selftest_box():
    """**正对照**：算子在**解析长方体**上必须幂等（体积逐位不变）。"""
    P('-' * 78)
    P('[P-1] 正对照：算子在解析长方体上幂等？')
    N, dx = 48, 62.5e-9
    ii = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(ii, ii, ii, indexing='ij')
    c = np.array([0.5, 0.5, 0.5]) * N * dx
    h = np.array([10.0, 6.0, 4.0]) * dx            # 半宽（胞数）
    u = np.eye(3)
    pr = np.stack([X - c[0], Y - c[1], Z - c[2]], -1)
    phi = np.max(np.abs(pr) - h[None, None, None, :], -1)
    v0 = int((phi < 0).sum())
    ph2, info = facet_project_one(phi, dx, (u[2], u[0], u[1]))
    v1 = int((ph2 < 0).sum())
    ok = (v1 == v0)
    P('    体积 v0=%d  v1=%d  s=%.6f  rel=%.3e  ⇒ %s'
      % (v0, v1, info.get('s', float('nan')), info.get('rel', float('nan')),
         '✅ 幂等（PASS）' if ok else '❌ 不幂等（FAIL）'))
    # 二阶：再投影一次仍不变
    ph3, _ = facet_project_one(ph2, dx, (u[2], u[0], u[1]))
    v2 = int((ph3 < 0).sum())
    P('    再投影一次：v2=%d ⇒ %s' % (v2, '✅' if v2 == v0 else '❌'))
    return ok


# ---------------------------------------------------------------- 主测
def main():
    P('=' * 78)
    P('_r410 —— `--facet-proj` 抹掉块内 F3 的**机理直测**')
    P('  快照：%s  step=%d' % (RUN, STEP))
    P('=' * 78)
    ok_pos = selftest_box()

    snap = os.path.join(RUN, 'snap_%05d.npz' % STEP)
    if not os.path.exists(snap):
        snap = os.path.join(RUN, 'seeds.npz')
        P('  （用 seeds.npz）')
    d = np.load(snap)
    # ★ 快照**不含** `laths`/`vmap`（只有 `seeds.npz` 有）⇒ 缺了就回退读 `seeds.npz`。
    #   `laths`/`vmap` 是**构型常量**，来自 `meta.json`，与 step 无关 ⇒ 回退是安全的。
    _sd = np.load(os.path.join(RUN, 'seeds.npz'))
    reg = np.asarray(d['region'], np.int64)
    N = int(d['N'])
    L = float(d['L'])
    dx = L / N
    _lt = d['laths'] if 'laths' in d.files else _sd['laths']
    _vk = d['vmap_keys'] if 'vmap_keys' in d.files else _sd['vmap_keys']
    _vv = d['vmap_vals'] if 'vmap_vals' in d.files else _sd['vmap_vals']
    laths = [int(x) for x in np.asarray(_lt).ravel()]
    vmap = {int(k): int(v) for k, v in
            zip(np.asarray(_vk).ravel(), np.asarray(_vv).ravel())}
    P('\n[0] 构型：N=%d  Δx=%.2f nm  L=%.3f µm  场数=%d' % (N, dx * 1e9, L * 1e6, len(laths)))
    P('    laths = %s' % laths)
    P('    vmap  = %s' % vmap)

    npref, atab, wtab = axes_tables(laths, vmap)
    P('    轴表已按驱动同款方式重建（逐**场**）')

    # ---- 基线
    P('\n[1] 基线（未投影）')
    f1, f2, f3 = face_counts(reg, vmap)
    nb, blks = connected_blocks(reg, vmap)
    P('    F1(母相-析出)=%d  F2(异变体)=%d  F3(同变体)=%d' % (f1, f2, f3))
    P('    同变体 6-连通块数 = %d；各块(变体,体积胞数) 前 14 个：' % nb)
    P('      %s' % (blks[:14],))
    n_tot = int((reg > 0).sum())
    P('    已转变胞数 = %d' % n_tot)

    # ---- 两个对照：excl 开 / 关
    for label, use_excl in (('excl=None（R73 之前）', False),
                            ('excl=同变体邻域（现行）', True)):
        P('\n' + '-' * 78)
        P('[2] 投影：%s' % label)
        bodies_new = {}
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
                    try:
                        import scipy.ndimage as _ndi
                        excl = _ndi.binary_dilation(other, iterations=PAD)
                    except Exception:
                        excl = other
            ph, info = facet_project_one(phi_k, dx, (npref[k], atab[k], wtab[k]),
                                         excl=excl)
            if info.get('ok'):
                bodies_new[k] = (ph < 0)
        # 合成新 region：被任何场占据 ⇒ 取"最负"的那个（argmin φ 的等价物）；
        # 都不占据 ⇒ 0（母相）。**这是 β 膜的判据。**
        phi_stack = np.full((len(bodies_new) + 1,) + reg.shape, np.inf, np.float32)
        ks = sorted(bodies_new)
        for i, k in enumerate(ks):
            phi_stack[i + 1] = np.where(bodies_new[k], -1.0 * dx, 1.0 * dx)
        reg_new = np.argmin(phi_stack, axis=0).astype(np.int64)
        reg_new = np.where(phi_stack.min(0) < 0, reg_new, 0)

        g1, g2, g3 = face_counts(reg_new, vmap)
        nb2, blks2 = connected_blocks(reg_new, vmap)
        vac = int(((reg > 0) & (reg_new == 0)).sum())
        P('    F1=%d  F2=%d  F3=%d   （基线 F1=%d F2=%d F3=%d）' % (g1, g2, g3, f1, f2, f3))
        P('    ⇒ ΔF3 = %+d（%.1f%% 保留）' % (g3 - f3, 100.0 * g3 / max(f3, 1)))
        P('    同变体 6-连通块数 = %d（基线 %d）；单板条块数 = %d'
          % (nb2, nb, sum(1 for _, s in blks2 if s < 0.5 * n_tot / max(nb, 1))))
        P('    各块(变体,体积胞数) 前 14：%s' % (blks2[:14],))
        P('    ★ **β 膜**（原先已转变、投影后不属于任何场的胞）= **%d**'
          '（占原转变体积 %.2f%%）' % (vac, 100.0 * vac / max(n_tot, 1)))
    P('\n' + '=' * 78)
    P('判读口径：若「excl=同变体邻域」的 β 膜胞数 **远大于** 「excl=None」，')
    P('则机理成立：**排除掩码内缩了跨度、而体积靶没减 ⇒ 盒子被放大 ⇒ 沿 F3 法向张开缝**。')
    P('=' * 78)


if __name__ == '__main__':
    main()
