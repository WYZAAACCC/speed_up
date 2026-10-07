#!/usr/bin/env python3
"""R52/R53: **第四口径 —— 直接读 φ=0 等值面的位置**（最接近"定义"的量）。

## 为什么还需要第四个
前三个口径互相矛盾（`R30_AUDIT_LEDGER.md` §34/§35）：
  ① `tip_sep_nm` 面簇**中位位置**之差 —— 尖端变钝时会停住（且末态给 nan）
  ② `a_lath` 该场**包围跨度** —— 同场碎屑/长指会撑大
  ③ `core3` 最大连通分量在自己 (n,w,a) 基上的跨度 —— 孤儿免疫，但仍是**跨度**
⇒ 本口径不用任何"簇"或"跨度"的定义，而是**直接解 φ_k(x)=0**：
   在网格上找 φ 的**变号**相邻对（x/y/z 三轴各一次），线性插值出零交叉点，
   再把交叉点投影到该场的 `a` 轴取 min/max。
   * 不受"尖端变钝"影响（变钝只会增加交叉点，不会让极值内移）；
   * 不受碎屑影响（碎屑属于同一个场时会额外给出交叉点 ⇒ **仍可能撑大**）
     ⇒ 所以**只取最大连通分量的场**参与（复用 ③ 的思路）。

## 数据来源
`snap_*.npz` 的 `band_idx`/`band_val`/`band_fld`（带内稀疏 φ，**米**）。
⚠ 带外无值 ⇒ 只能重建 |φ| ≤ band_cells·Δx 的胞；但**变号必然发生在带内**，
  所以零交叉点是完整的。
"""
import glob
import os
import sys

import numpy as np

sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
import _bk_measure as BM  # noqa: E402


def phi_band(z, N):
    """把带内稀疏 φ 还原成 (nreg,N,N,N) 的数组，带外 = NaN。"""
    vm = {int(a): int(b) for a, b in zip(z['vmap_keys'], z['vmap_vals'])}
    nreg = max(vm) + 1 if vm else 1
    out = np.full((nreg, N, N, N), np.nan, np.float32)
    if 'band_idx' not in z.files:
        return out, vm
    idx = z['band_idx']
    val = z['band_val']
    fld = z['band_fld']
    for k in np.unique(fld):
        sel = (fld == k)
        kk = int(k)
        if 0 <= kk < nreg:
            out[kk].ravel()[idx[sel]] = val[sel]
    return out, vm


def crossings_along(phi_k, dx, axis):
    """沿 `axis` 找 φ=0 的零交叉点，返回 (坐标数组, 交叉点三维位置 Nx3)。"""
    N = phi_k.shape[0]
    pts = []
    a = np.moveaxis(phi_k, axis, 0)
    for i in range(N - 1):
        p0, p1 = a[i], a[i + 1]
        m = np.isfinite(p0) & np.isfinite(p1) & (p0 * p1 < 0)
        if not m.any():
            continue
        w = p0[m] / (p0[m] - p1[m])                       # ∈ (0,1)
        sub = np.argwhere(m)                              # 在其余两轴上的索引
        coord = (i + w) * dx
        full = np.zeros((sub.shape[0], 3))
        oth = [j for j in range(3) if j != axis]
        full[:, axis] = coord
        full[:, oth[0]] = (sub[:, 0] + 0.5) * dx
        full[:, oth[1]] = (sub[:, 1] + 0.5) * dx
        pts.append(full)
    if not pts:
        return np.zeros(0)
    return np.vstack(pts)


def main():
    D = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mb/dry_mb1s62'
    snaps = sorted(glob.glob(os.path.join(D, 'snap_*.npz')))
    print('臂 %s  快照 %d 个' % (D, len(snaps)))
    print()
    print('  %-6s %-10s %-10s %-10s %-10s %s'
          % ('step', 'iso a (nm)', 'iso w (nm)', 'iso n (nm)', '交叉点数', '场数'))
    rec = []
    for s in snaps:
        z = np.load(s)
        if 'band_idx' not in z.files:
            print('  %-6s ⚠ 该快照**没有带内 φ**（`band_idx` 缺）' % z['step'])
            continue
        N = int(z['N'])
        L = float(z['L'])
        dx = L / N
        aa = np.asarray(z['a_ax'], float)
        ww = np.asarray(z['w_ax'], float)
        nn = np.asarray(z['n_hab'], float)
        phi, vm = phi_band(z, N)
        # 只保留**最大连通分量**所属的场（碎屑免疫）
        reg = z['region']
        mask = (reg > 0)
        keep = None
        if mask.any():
            lab, n = BM._label_periodic(mask)
            if lab is not None and n > 0:
                sz = np.bincount(lab.ravel(), minlength=n + 1)
                big = int(np.argmax(sz[1:])) + 1
                keep = set(int(x) for x in np.unique(reg[lab == big]) if x > 0)
        allp = []
        for k in range(phi.shape[0]):
            if k == 0 or (keep is not None and k not in keep):
                continue
            pk = phi[k]
            if not np.isfinite(pk).any():
                continue
            for ax in (0, 1, 2):
                p = crossings_along(pk, dx, ax)
                if p.size:
                    allp.append(p)
        if not allp:
            print('  %-6s （无交叉点）' % z['step'])
            continue
        P = np.vstack(allp)
        ext = {}
        for nm, u in (('a', aa), ('w', ww), ('n', nn)):
            pr = P @ u
            ext[nm] = (pr.max() - pr.min()) * 1e9
        rec.append((int(z['step']), ext['a'], ext['w'], ext['n'], len(P)))
        print('  %-6d %-10.0f %-10.0f %-10.0f %-10d %d'
              % (z['step'], ext['a'], ext['w'], ext['n'], len(P),
                 len(keep) if keep else 0))
    if len(rec) < 3:
        print('\n⚠ 有效点不足，无法给速率')
        return
    print()
    print('=== 分段速率（**φ=0 等值面**口径，nm/步）')
    print('  %-14s %-12s %-12s %-12s %s'
          % ('窗口', 'd(iso a)', 'd(iso w)', 'd(iso n)', '判词'))
    for lo, hi in ((0, 500), (500, 1000), (1000, 1500), (0, 10 ** 9)):
        seg = [r for r in rec if lo <= r[0] <= hi]
        if len(seg) < 3:
            continue
        xs = np.array([r[0] for r in seg], float)
        out = [float(np.polyfit(xs, np.array([r[c] for r in seg], float), 1)[0])
               for c in (1, 2, 3)]
        lab = ('全程' if hi > 10 ** 8 else '%d–%d' % (lo, hi))
        print('  %-14s %+-12.3f %+-12.3f %+-12.3f %s'
              % (lab, out[0], out[1], out[2],
                 ('**a 快**（拉长）' if out[0] > out[1] else
                  '**w 快**（肥化）' if out[1] > out[0] else '相等')))


if __name__ == '__main__':
    main()
