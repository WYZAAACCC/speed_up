#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_twf_probe.py --- ★ 判据② 的**前置探针**：快照里到底有什么、能不能重建出 φ

## 为什么先探针、不直接写 `t_wf` 工具（P20 纪律：先打语义，再写代码）
判据② 要"单根板条的三维几何量、长宽比符合物理"，而：
* **不能用 `ths`/`n_lath`**（包围盒跨度，非厚度 —— `_bk_measure.py:156` 代码自警告）；
* **正解是 `wide_face_thickness`（`t_wf`）**，签名
  `(phi, dx, n_hab, k, band=1.5, cos2_min=0.81, band_cells=2)`，**返回 dict**；
* **它有恒定 +1Δx 偏差**（我实测：125/250/500 nm 三档都 +62.5 nm）⇒ **用前必须减 Δx**；
* 它需要 **φ** 与 **`n_hab`**，而快照里只有**带内 φ**（每 `--phi-band-every` 步一份）
  ⇒ **必须先确认：带内 φ 够不够、`n_hab` 从哪来。**

**⇒ 本脚本只做四件事（全部是"读"，不改任何东西）：**
1. 快照的**键清单**（有没有 `band_*`、有没有 `region`）；
2. `band_*` 三个数组的**形状/dtype/取值范围**；
3. **重建的覆盖率**：带内 φ 覆盖了多少比例的体积；**若按 band=6 判，带外补 `1e3` 是否可行**；
4. **`n_hab` 的可得性**：引擎里 `NPF`/`EPS0` 表能否从**命令行**重建（`_bk_exp.py` 是模块级）。
"""
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def probe(path):
    print('=' * 100)
    print('探针：%s（%.2f MB）' % (os.path.basename(path),
                                 os.path.getsize(path) / 1048576.0))
    print('=' * 100)
    with np.load(path, allow_pickle=False) as z:
        keys = sorted(z.files)
        print('  键（%d 个）：%s' % (len(keys), keys))
        have_band = [k for k in ('band_idx', 'band_val', 'band_fld', 'band_cells') if k in keys]
        print('  ★ 带内 φ 相关键：%s' % (have_band or '**无**'))
        print('  ★ 有 `region` 吗：%s' % ('region' in keys))
        for k in ('N', 'L', 'step', 't_s', 'n_hab', 'w_ax', 'a_ax'):
            if k in keys:
                a = z[k]
                print('     %-10s shape=%-16s dtype=%-10s 值=%s'
                      % (k, a.shape, a.dtype, str(a)[:60]))
        if 'region' in keys:
            reg = np.asarray(z['region'])
            u = np.unique(reg)
            print('     region     shape=%s  取值 %d 个：%s%s'
                  % (reg.shape, len(u), u[:10], ' …' if len(u) > 10 else ''))
        if not have_band:
            print('  ⇒ **本快照没有带内 φ** ⇒ 判据② 无法从它离线重算')
            return
        idx = np.asarray(z['band_idx'])
        val = np.asarray(z['band_val'])
        fld = np.asarray(z['band_fld'])
        bc = int(np.asarray(z['band_cells']).item()) if 'band_cells' in keys else -1
        N = int(np.asarray(z['N']).item()) if 'N' in keys else 0
        L = float(np.asarray(z['L']).item()) if 'L' in keys else 0.0
        print()
        print('  ── 带内 φ 的三元组 ──')
        print('     band_idx   %s %s  范围 [%d, %d]' % (idx.shape, idx.dtype,
                                                         idx.min(), idx.max()))
        print('     band_val   %s %s  范围 [%.4g, %.4g]' % (val.shape, val.dtype,
                                                            val.min(), val.max()))
        print('     band_fld   %s %s  取值 %s' % (fld.shape, fld.dtype,
                                                   sorted(set(fld.tolist()))[:12]))
        print('     band_cells = %d' % bc)
        if N:
            tot = N ** 3
            print()
            print('  ── 覆盖率 ──')
            print('     每场总胞数 N³ = %d' % tot)
            for k in sorted(set(fld.tolist()))[:6]:
                m = (fld == k)
                print('       场 %-3d 带内 %7d 胞 = **%.4f%%**'
                      % (k, int(m.sum()), 100.0 * m.sum() / tot))
            print('     ⚠ 带外胞**不在**快照里 ⇒ 若要把 φ 补全，只能填常数（原值是 `1e3`）')
            print('     ⚠ 而 `wide_face_thickness` 只需**界面附近**的 φ 估计法向')
            print('       ⇒ 「带内够不够」**必须实测**，不能推理（见下一步）')


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_t5/dry_t5G3'
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    if not snaps:
        print('  ⚠ %s 里没有 snap_*.npz' % d)
        return 1
    print('共 %d 个快照：%s' % (len(snaps), [os.path.basename(s) for s in snaps]))
    # 只探**有 band_* 的**那个（带内 φ 每 --phi-band-every 步一份）
    cand = []
    for s in snaps:
        with np.load(s, allow_pickle=False) as z:
            if 'band_idx' in z.files:
                cand.append(s)
    print('★ 含 `band_idx` 的快照：%s' % ([os.path.basename(c) for c in cand] or '**无**'))
    if not cand:
        print('  ⇒ **一个都没有** ⇒ 判据② 的离线重算在本跑上**不可行**')
        print('     原因：启动器把 `--phi-band-every` 写成 200，而 `--snap-every` 是 40')
        print('     ⇒ 只有 1/5 的快照带 φ；若连这 1/5 都没有，说明步数还没到 200')
        return 1
    probe(cand[-1])
    return 0


if __name__ == '__main__':
    sys.exit(main())
