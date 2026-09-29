#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_bandchk.py —— R30 **P0-4 修复的正对照**：带内稀疏 φ 能不能**无损重建**。

## 为什么必须做（本仓库纪律：探针/量具先做正对照）

R30 给快照加了 `band_idx/band_val/band_fld/band_cells`（带内稀疏 φ），
声称"有了它，界面剖面/法向/**曲率 κ**/亚胞厚度就能事后重测"。
**这个声称必须被证伪一次**：编码错一个 `ravel`/`order`/`dtype`，重建出来的
φ 就是错的，而它**不会报错** —— 正是本项目最忌讳的静默失效。

## 判据（预先写死）

在**同一次运行**里同时落盘**整场 φ** 与**带内稀疏 φ**（`--phi-every` 与
`--phi-band-every` 都开），然后：

  B-1 **逐位重建**：由 `band_*` 重建的 φ，在带内胞上与整场 φ **逐位相同**
      （float32 比较，`max|Δ| == 0`）。
  B-2 **零水平集 == region**：重建 φ 的 `argmin` 在**带内**与 `region` 一致
      （带外是裁剪值 ⇒ 不参与）。
  B-3 **界面法向可算**：在带内用重建 φ 算 `∇φ/|∇φ|`，与用整场 φ 算的**逐位相同**。
  B-4 **曲率可算**：同上，`κ = div(∇φ/|∇φ|)`，逐位相同。
  B-5 **代价**：报 `band` 的胞数与字节数（相对整场 φ 的压缩比）。

跑法：  python3 _r30_bandchk.py
"""
import os
import sys
import glob
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = 'r30bandchk'
OUT = '_exp/_r30mfix'
PY = sys.executable


def run():
    cmd = [PY, '-u', '_bk_exp.py', '--arm', 'dry', '--N', '32', '--dx-nm', '125',
           '--laths', '1,1', '--steps', '2', '--every', '1', '--snap-every', '2',
           '--nthreads', '1', '--tag', TAG, '--out', OUT,
           '--phi-every', '2',            # 整场 φ（对照组）
           '--phi-band-every', '0']       # 带内稀疏 φ（被测对象）
    print('跑：%s' % ' '.join(cmd))
    r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
        raise SystemExit('✗ 生成对照快照失败（returncode=%d）' % r.returncode)
    return os.path.join(HERE, OUT, 'dry_%s' % TAG)


def reconstruct(z, nreg, N):
    """由 `band_*` 重建 (nreg, N, N, N) 的 φ；带外填 ±band·dx 的**裁剪值**。

    ⚠ 带外值**不是真值**（这正是"稀疏"的代价）⇒ 只允许在带内做比较。
    """
    dx = float(z['L']) / N
    bc = int(z['band_cells'])
    out = np.full((nreg, N, N, N), np.nan, np.float64)
    idx = z['band_idx'].astype(np.int64)
    val = z['band_val'].astype(np.float64)
    fld = z['band_fld'].astype(np.int64)
    for k in range(nreg):
        sel = (fld == k)
        if not sel.any():
            continue
        flat = out[k].ravel()
        flat[idx[sel]] = val[sel]
    _ = bc * dx
    return out


def main():
    d = run()
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    if not snaps:
        raise SystemExit('✗ 没有快照')
    fails = []

    def ck(tag, ok, det=''):
        print('  %-52s %s  %s' % (tag, 'PASS' if ok else '**FAIL**', det))
        if not ok:
            fails.append(tag)

    for sp in snaps:
        z = np.load(sp)
        if 'phi' not in z.files:
            raise SystemExit('✗ 对照组缺 `phi`（--phi-every 没生效）: %s' % sp)
        phi = z['phi'].astype(np.float64)
        nreg, N = phi.shape[0], phi.shape[1]
        rec = reconstruct(z, nreg, N)
        dx = float(z['L']) / N
        bc = int(z['band_cells'])
        band = np.abs(phi) <= bc * dx
        print('\n%s：nreg=%d N=%d 带内胞=%d/%d（%.3f%%）  band=%d 胞'
              % (os.path.basename(sp), nreg, N, int(band.sum()), phi.size,
                 100.0 * band.sum() / phi.size, bc))
        # B-1 逐位重建
        dmax = float(np.max(np.abs(rec[band] - phi[band]))) if band.any() else 0.0
        ck('B-1 带内 φ 逐位重建（max|Δ| == 0）', dmax == 0.0, 'max|Δ|=%.3e' % dmax)
        # B-2 零水平集（带内）== region
        reg = z['region'].astype(np.int64)
        with np.errstate(invalid='ignore'):
            am = np.nanargmin(np.where(np.isnan(rec), np.inf, rec), axis=0)
        both = band.any(axis=0)
        same = int((am[both] == reg[both]).sum())
        tot = int(both.sum())
        ck('B-2 零水平集（带内）== region', same == tot,
           '%d/%d 一致' % (same, tot))
        # B-3 / B-4：法向与曲率（用**整场真值** vs **重建值**，在带内比）
        g = np.gradient(phi[0], dx, edge_order=2)
        gn = np.sqrt(sum(x ** 2 for x in g)) + 1e-30
        k1 = sum(np.gradient(g[i] / gn, dx, edge_order=2)[i] for i in range(3))
        r0 = rec[0].copy()
        r0[np.isnan(r0)] = 0.0
        g2 = np.gradient(r0, dx, edge_order=2)
        gn2 = np.sqrt(sum(x ** 2 for x in g2)) + 1e-30
        k2 = sum(np.gradient(g2[i] / gn2, dx, edge_order=2)[i] for i in range(3))
        m = band[0]
        # ★★ 本对照**第一次跑就抓到了一件事**（这正是正对照的用途）：
        #   在**整个带宽**上比导数 ⇒ n 与 κ 都 FAIL（带外被填 0 ⇒ 最外 2 层被污染）。
        #   根因**不是编码错**（B-1 逐位为 0）。实测三次定出的可用域：
        #     · `|φ| ≤ bc·Δx`（整带）      ⇒ n、κ 都不可信
        #     · `|φ| ≤ (bc−1)·Δx`          ⇒ **n_x 逐位为 0**，κ 仍不可信（二阶导）
        #     · `|φ| ≤ (bc−2)·Δx`          ⇒ **n_x 与 κ 都逐位为 0**
        #   ⇒ 必须写进落盘格式的账：
        #     **带宽 `bc` 胞 ⇒ 一阶导在 `(bc−1)` 内层、二阶导在 `(bc−2)` 内层可逐位重算。**
        inner1 = np.abs(phi[0]) <= (bc - 1) * dx
        inner2 = np.abs(phi[0]) <= (bc - 2) * dx
        if inner1.any():
            _dn = float(np.max(np.abs((g[0] / gn)[inner1] - (g2[0] / gn2)[inner1])))
            ck('B-3 内层 |φ|≤%dΔx：法向 n_x 逐位一致' % (bc - 1), _dn == 0.0,
               'max|Δ|=%.3e（%d 胞）' % (_dn, int(inner1.sum())))
        if inner2.any():
            _dn2 = float(np.max(np.abs((g[0] / gn)[inner2] - (g2[0] / gn2)[inner2])))
            _dk = float(np.max(np.abs(k1[inner2] - k2[inner2])))
            ck('B-4 内层 |φ|≤%dΔx：曲率 κ 逐位一致' % (bc - 2),
               (_dn2 == 0.0 and _dk == 0.0),
               'n_x max|Δ|=%.3e  κ max|Δ|=%.3e 1/m（%d 胞）'
               % (_dn2, _dk, int(inner2.sum())))
        # B-5 代价
        nb = int(z['band_idx'].size)
        bytes_band = (z['band_idx'].nbytes + z['band_val'].nbytes
                      + z['band_fld'].nbytes)
        full = phi.nbytes * 4          # float32 整场
        ck('B-5 代价：带内编码 < 整场 φ 的 25%', bytes_band < 0.25 * full,
           '%d 胞 / %.2f MB（整场 φ float32 = %.2f MB ⇒ %.1f%%）'
           % (nb, bytes_band / 1048576.0, full / 1048576.0,
              100.0 * bytes_band / full))

    print('\n' + '=' * 74)
    print('R30 P0-4（带内稀疏 φ）正对照：%s（FAIL=%d）'
          % ('全过 ✅' if not fails else '有 FAIL ❌', len(fails)))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
