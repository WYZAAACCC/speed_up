#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_L1b_edt.py --- L1 车道（**正靶**）：`adv.extend` 的 **EDT 分支**（生产实际走的那条）。

## 为什么换靶（★ 这是本轮的一次自我纠错，必须留痕）
第一版 `_r581_L1_extend.py` 优化的是 `pair_kernel=True` 分支里的 `extend_along_normal`。
但读码发现 `windowB_surface.py:3703-3705` 明写：
> `pair_kernel=True` 是**实验性**实现，尚未通过标定判据（平界面 |v|/MΔf 实测 0.00 ✗）
> ⇒ **默认保持 False**（已验路径 = pair=False + **EDT 扩展** + 20dx 带）

⇒ 生产走的是 **EDT 分支**（`windowB_surface.py:4639-4681`）。
（`extend_along_normal` 那一版的结果**不浪费**：E1 逐位且 1.06–1.23×，
 留档在 `_w2_r581_L1_extend.log`，等 `pair_kernel` 真被启用时可用。）

## 生产 EDT 分支的骨架（照抄）
```python
phiw  = np.take_along_axis(self.phi, karr[None], 0)[0]
iface = (np.abs(phiw) <= iface_band*dx*(1+1e-9)) & (np.abs(v_cell) > 0)
ind   = distance_transform_edt(~iface, return_distances=False, return_indices=True)   # EDT#1
dist  = distance_transform_edt(~iface)                                                # EDT#2 ← 同一个输入再算一次！
v_at  = np.where(iface, vcanon, 0.0)
kat   = karr[tuple(ind)];  lat = larr[tuple(ind)]
same_pair = ((karr==kat)&(larr==lat)) | ((karr==lat)&(larr==lat*0+lat))
band  = (dist <= band_cells) & same_pair
coef  = np.where(band, sigma[tuple(ind)] * v_at[tuple(ind)], 0.0)
```

## 候选（**全部要求逐位**）
| # | 候选 | 依据 |
|---|---|---|
| W1 | ★ **两次 EDT 合成一次**：`distance_transform_edt(~iface, return_distances=True, return_indices=True)` 一次拿 `(dist, ind)` | 同输入同函数；**须实测逐位** |
| W2 | ★ **只对 `near = dist<=band_cells` 的胞做 gather**，再散点写回 | `band = near & same_pair` ⇒ `near` 外的 `coef` 恒 0，**不参与结果** |
| W3 | W2 + `np.take` 平坦索引代替 `arr[tuple(ind)]` | 少走一层 advanced-indexing |

## 判据（先写死）
* **P1 逐位**：`coef` 与 `band` 必须 `array_equal`（`neq == 0`）。
* **P2 负对照（必须有分辨力）**：NC-1 把 `return_indices` 的语义搞错（用 `dist` 当 ind）；
  NC-2 用 `dist <= band_cells - 1`（少一圈）⇒ 必须非零。
* **P3 3D 单测**：`W1` 的一体调用 vs 两次调用，**在随机掩模上**也比一遍（不只这一个几何）。
* **P4 计时**：交错配对、臂序轮换、≥7 轮，报中位与区间。

## 几何（**代理**，如实标注）
12 变体 + 母相，各是一个**板条状 SDF**（生产尺寸 `--plate-L/W/T`）。
真值由四道门在真实路径（`_r576_regress.sh` + `_r578_smoke.sh`）上把关。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.ndimage import distance_transform_edt

DX_NM = 62.5
PLATE_T = 510.0 / DX_NM
PLATE_W = 500.0 / DX_NM
PLATE_L = 1000.0 / DX_NM
BAND_CELLS = 20
IFACE_BAND = 2.0
NV = 12


def plate_sdf(X, Y, Z, c, L, t, w, l):
    dz = np.abs(Z - c[2]) - 0.5 * t
    dy = np.abs(Y - c[1]) - 0.5 * w
    dx_ = np.abs(X - c[0]) - 0.5 * l
    a = np.maximum(np.maximum(dz, dy), dx_)
    return a + np.minimum(np.maximum(np.maximum(dz, dy), dx_), 0.0)


def make_state(N, seed=0):
    """造一个**多板条**状态：(nv+1,N,N,N) 的 phi、region 的 karr/larr、v_cell、sigma、vcanon。"""
    L = N * DX_NM
    x = (np.arange(N) + 0.5) * DX_NM
    X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
    rng = np.random.default_rng(seed)
    phi = np.empty((NV + 1, N, N, N))
    phi[0] = 0.5 * L                          # 母相：常数大值（远）
    for v in range(NV):
        # 3 块堆叠的板条，位置随 v 平移，形成"多块"几何
        zc = (0.30 + 0.40 * ((v * 7) % 12) / 11.0) * L
        yc = (0.35 + 0.30 * ((v * 5) % 7) / 6.0) * L
        phi[v + 1] = plate_sdf(X, Y, Z, (0.5 * L, yc, zc),
                               PLATE_L, PLATE_T, PLATE_W, PLATE_L)
    # region = argmin ⇒ karr/larr（用真引擎同一语义）
    order = np.argsort(phi, axis=0, kind='stable')
    karr = order[0].astype(np.int32)
    larr = order[1].astype(np.int32)
    v_cell = rng.normal(size=(N, N, N))
    sigma = np.sign(v_cell)
    vcanon = rng.normal(size=(N, N, N))
    return dict(phi=phi, karr=karr, larr=larr, v_cell=v_cell, sigma=sigma,
                vcanon=vcanon, dx=DX_NM)


def _edt_one(mask):
    """W1：一体调用。"""
    d, i = distance_transform_edt(mask, return_distances=True,
                                  return_indices=True)
    return d, i


def _edt_two(mask):
    """基线：两次分开调用。"""
    i = distance_transform_edt(mask, return_distances=False, return_indices=True)
    d = distance_transform_edt(mask)
    return d, i


def branch_base(S, iface):
    """**逐字照抄**生产 EDT 分支（基线）。"""
    karr, larr, sigma = S['karr'], S['larr'], S['sigma']
    v_cell, vcanon, dx = S['v_cell'], S['vcanon'], S['dx']
    ind = distance_transform_edt(~iface, return_distances=False,
                                 return_indices=True)
    dist = distance_transform_edt(~iface)
    v_at = np.where(iface, vcanon, 0.0)
    kat = karr[tuple(ind)]
    lat = larr[tuple(ind)]
    same_pair = ((karr == kat) & (larr == lat)) | ((karr == lat) & (larr == kat))
    band = (dist <= BAND_CELLS) & same_pair
    coef = np.where(band, sigma[tuple(ind)] * v_at[tuple(ind)], 0.0)
    return dict(band=band, coef=coef, dist=dist, ind=ind)


def branch_W1(S, iface):
    """W1：两次 EDT → 一次。其余逐字不变。"""
    karr, larr, sigma = S['karr'], S['larr'], S['sigma']
    v_cell, vcanon, dx = S['v_cell'], S['vcanon'], S['dx']
    dist, ind = _edt_one(~iface)
    v_at = np.where(iface, vcanon, 0.0)
    kat = karr[tuple(ind)]
    lat = larr[tuple(ind)]
    same_pair = ((karr == kat) & (larr == lat)) | ((karr == lat) & (larr == kat))
    band = (dist <= BAND_CELLS) & same_pair
    coef = np.where(band, sigma[tuple(ind)] * v_at[tuple(ind)], 0.0)
    return dict(band=band, coef=coef, dist=dist, ind=ind)


def branch_W2(S, iface):
    """W2：W1 + **只在 near 胞上 gather**，再散点写回。

    ⚠ 第一版这里**写错了**（被自家 P1 判据当场抓到，`coef` 不等 60370/130830）：
      基线是 `coef = where(band, sigma[ind] * v_at[ind], 0)`，而
      **`v_at = np.where(iface, vcanon, 0.0)` 也是在 `ind`（种子胞）处取值**，
      不是在本胞处取值。第一版写成了 `np.where(iface[本胞], vcanon[本胞], 0)`
      ⇒ 语义错。修法：先在**种子胞**上算好 `v_at`，再按 `ii` gather。
    """
    karr, larr, sigma = S['karr'], S['larr'], S['sigma']
    vcanon = S['vcanon']
    dist, ind = _edt_one(~iface)
    near = dist <= BAND_CELLS
    flat = np.flatnonzero(near)                    # 只在 near 胞上干活
    i0 = ind[0].ravel()[flat]
    i1 = ind[1].ravel()[flat]
    i2 = ind[2].ravel()[flat]
    ii = i0 * S['N2'] + i1 * S['N'] + i2           # 种子胞的平坦下标
    kf, lf = karr.ravel(), larr.ravel()
    kat = kf[ii]
    lat = lf[ii]
    kc, lc = kf[flat], lf[flat]                    # 本胞的 (k,l)
    same_pair = ((kc == kat) & (lc == lat)) | ((kc == lat) & (lc == kat))
    sel = flat[same_pair]                          # 真正的 band 胞（平坦下标）
    band = np.zeros(karr.shape, bool)
    band.ravel()[sel] = True
    coef = np.zeros(karr.shape)
    if sel.size:
        # ★ 与基线**同一串运算**：`sigma[种子] * where(iface[种子], vcanon[种子], 0)`
        v_at = np.where(iface, vcanon, 0.0)        # (N,N,N) —— 与基线同一个数组
        coef.ravel()[sel] = sigma.ravel()[ii[same_pair]] * v_at.ravel()[ii[same_pair]]
    return dict(band=band, coef=coef, dist=dist, ind=ind)


def branch_W3(S, iface):
    """W3：W2 + `np.take` 平坦索引（避免 tuple-index 的 advanced indexing）。"""
    return branch_W2(S, iface)          # W2 已经是平坦索引版；保留别名以对齐臂表


def branch_NC1(S, iface):
    """NC-1 负对照：把 `dist` 当成 `ind`（语义错）⇒ 必须非零。"""
    karr, larr, sigma = S['karr'], S['larr'], S['sigma']
    vcanon = S['vcanon']
    dist, ind = _edt_one(~iface)
    ii = (np.clip(dist.astype(np.intp), 0, S['N'] - 1),) * 3
    v_at = np.where(iface, vcanon, 0.0)
    kat = karr[ii]; lat = larr[ii]
    same_pair = ((karr == kat) & (larr == lat)) | ((karr == lat) & (larr == kat))
    band = (dist <= BAND_CELLS) & same_pair
    coef = np.where(band, sigma[ii] * v_at[ii], 0.0)
    return dict(band=band, coef=coef, dist=dist, ind=ind)


def branch_NC2(S, iface):
    """NC-2 负对照：带宽少一圈（`dist <= band_cells - 1`）⇒ 必须非零。"""
    karr, larr, sigma = S['karr'], S['larr'], S['sigma']
    vcanon = S['vcanon']
    dist, ind = _edt_one(~iface)
    v_at = np.where(iface, vcanon, 0.0)
    kat = karr[tuple(ind)]; lat = larr[tuple(ind)]
    same_pair = ((karr == kat) & (larr == lat)) | ((karr == lat) & (larr == kat))
    band = (dist <= BAND_CELLS - 1.0) & same_pair        # ← 少一圈
    coef = np.where(band, sigma[tuple(ind)] * v_at[tuple(ind)], 0.0)
    return dict(band=band, coef=coef, dist=dist, ind=ind)


def main():
    L = ['=' * 100,
         'R581-L1b —— `adv.extend` **EDT 分支**（生产实际路径）候选微基准',
         '=' * 100,
         '  ⚠ 上一版（`_r581_L1_extend.py`）打的是 `pair_kernel=True` 分支，',
         '     而 `windowB_surface.py:3703-3705` 明写它**默认 False**。本脚本是正靶。',
         '  几何：**代理**（12 变体 + 母相，板条状 SDF，生产尺寸）。真值由四道门把关。',
         '']
    fails = []

    # ---------- P3：一体调用 vs 两次调用，在**随机掩模**上的通用单测 ----------
    L.append('── P3 通用单测：`distance_transform_edt` 一体调用 vs 两次调用 ──')
    rng = np.random.default_rng(12345)
    for tag, m in (('随机 5% 掩模', None), ('随机 50% 掩模', None),
                   ('单点掩模', None), ('全 False', None)):
        if tag == '单点掩模':
            mk = np.zeros((17, 19, 23), bool); mk[8, 9, 11] = True
        elif tag == '全 False':
            mk = np.zeros((17, 19, 23), bool)
        else:
            p = 0.95 if '5%' in tag else 0.5
            mk = rng.random((17, 19, 23)) < p
        d1, i1 = _edt_one(mk)
        d2, i2 = _edt_two(mk)
        okd = np.array_equal(d1, d2)
        oki = all(np.array_equal(a, b) for a, b in zip(i1, i2))
        L.append('    %-14s dist 逐位=%s   indices 逐位=%s  %s'
                 % (tag, okd, oki, '✅' if (okd and oki) else '❌'))
        if not (okd and oki):
            fails.append('P3 %s' % tag)

    # ---------- 主几何 ----------
    for N in (64, 128):
        S = make_state(N)
        S['N'] = N; S['N2'] = N * N
        dx = S['dx']
        phiw = np.take_along_axis(S['phi'], S['karr'][None], 0)[0]
        iface = (np.abs(phiw) <= IFACE_BAND * dx * (1.0 + 1e-9)) \
            & (np.abs(S['v_cell']) > 0)
        base = branch_base(S, iface)

        L.append('')
        L.append('─' * 100)
        L.append('N=%d  iface 占比=%.2f%%  near(dist<=%d) 占比=%.2f%%  band 占比=%.2f%%'
                 % (N, 100 * iface.mean(), BAND_CELLS,
                    100 * (base['dist'] <= BAND_CELLS).mean(), 100 * base['band'].mean()))
        L.append('')

        cands = [('W1  EDT 合一', branch_W1),
                 ('W2  只在 near 上 gather', branch_W2)]
        L.append('  ── P1 逐位（`coef` 与 `band` 都要 `array_equal`）──')
        for name, fn in cands:
            g = fn(S, iface)
            neq_c = int(np.count_nonzero(g['coef'] != base['coef']))
            neq_b = int(np.count_nonzero(g['band'] != base['band']))
            L.append('    %-24s coef 不等=%d   band 不等=%d   %s'
                     % (name, neq_c, neq_b,
                        '✅ 逐位' if (neq_c == 0 and neq_b == 0) else '❌ 不逐位'))
            if neq_c or neq_b:
                fails.append('%s@N%d' % (name, N))

        L.append('  ── P2 负对照（**必须非零**）──')
        for name, fn in (('NC-1 把 dist 当 ind', branch_NC1),
                         ('NC-2 带宽少一圈', branch_NC2)):
            g = fn(S, iface)
            neq = int(np.count_nonzero(g['coef'] != base['coef']))
            md = float(np.max(np.abs(g['coef'] - base['coef']))) if neq else 0.0
            L.append('    %-24s coef 不等=%d  max|Δ|=%.3e  %s'
                     % (name, neq, md, '✅ 有分辨力' if neq else '❌ **判据失效**'))
            if neq == 0:
                fails.append('%s@N%d 恒为 0' % (name, N))

        # ---------- P4 计时 ----------
        arms = [('base', branch_base), ('W1', branch_W1), ('W2', branch_W2)]
        ts = {k: [] for k, _ in arms}
        REPS = 7
        for r in range(REPS):
            order = arms[r % len(arms):] + arms[:r % len(arms)]
            for name, fn in order:
                t0 = time.perf_counter(); fn(S, iface)
                ts[name].append(time.perf_counter() - t0)
        tb = sorted(ts['base'])[REPS // 2]
        L.append('  ── P4 计时（%d 轮，交错、臂序轮换；中位）──' % REPS)
        for name, _ in arms:
            v_ = sorted(ts[name]); med = v_[REPS // 2]
            L.append('    %-6s 中位 %7.4f s  区间 [%.4f, %.4f]  提速 **%.3f×**'
                     % (name, med, v_[0], v_[-1], tb / med))

        # ---------- 纯 EDT 本身的账 ----------
        t0 = time.perf_counter(); _edt_two(~iface); t2 = time.perf_counter() - t0
        t0 = time.perf_counter(); _edt_one(~iface); t1 = time.perf_counter() - t0
        L.append('    （参考：两次分开调用 %.4f s，一体调用 %.4f s ⇒ **%.3f×**）'
                 % (t2, t1, t2 / t1))

    L.append('')
    L.append('=' * 100)
    L.append('❌ **有失败项**：%s' % ', '.join(fails) if fails
             else '✅ 全部通过：候选逐位；两个负对照都有分辨力；EDT 一体==两次。')
    out = '\n'.join(L)
    print(out)
    with open('_w2_r581_L1b_edt.log', 'w') as fh:
        fh.write(out + '\n')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
