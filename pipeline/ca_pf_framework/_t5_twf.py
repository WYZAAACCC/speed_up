#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_twf.py --- ★★★★★ 判据② 的**厚度量具**：从快照带内 φ 离线重算 `wide_face_thickness`

## 为什么不能用现成列
`series.csv` 的 `ths`/`n_lath` 是**包围盒跨度**，`_bk_measure.py:156` **代码自己警告**「不是板条厚度」。
**正解 = `wide_face_thickness`（`t_wf`）**，且它有**恒定 +1Δx 偏差**（我实测 125/250/500 nm 三档都 +62.5 nm）
⇒ **用前必须减 Δx 并记账**。

## 数据来源（探针已确认，§30.1）
快照键：`band_idx`(int32 线性索引) / `band_val`(float32 φ, ±6Δx) / `band_fld`(int16 场号)
/ `band_cells`(=6) / `n_hab`(3,) / `region` / `N` / `L`。
**⚠ 带内 φ 只在 `--phi-band-every` 的倍数步有（本跑 = 200 步）。**

## 用法
  python _t5_twf.py <snap.npz> [场号…]
"""
import sys

import numpy as np

sys.path.insert(0, '.')
import _bk_measure as BM                                     # noqa: E402


def rebuild(z, k):
    """按场 k 重建 φ（带内填真值、带外填 1e3 —— 与 `np.full(...,1e3)` 的语义一致）。"""
    N = int(np.asarray(z['N']).item())
    phi = np.full(N ** 3, 1e3, np.float64)
    idx = np.asarray(z['band_idx'])
    val = np.asarray(z['band_val'], np.float64)
    fld = np.asarray(z['band_fld'])
    m = (fld == k)
    phi[idx[m]] = val[m]
    return phi.reshape(N, N, N)


def main():
    p = sys.argv[1]
    with np.load(p, allow_pickle=False) as z:
        N = int(np.asarray(z['N']).item())
        L = float(np.asarray(z['L']).item())
        dx = L / N
        n_hab = np.asarray(z['n_hab'], float)
        flds = sorted(set(np.asarray(z['band_fld']).tolist()))
        want = [int(x) for x in sys.argv[2:]] or flds
        print('=' * 96)
        print('t_wf 离线重算：%s' % p)
        print('  N=%d  dx=%.4g m = %.1f nm   场 = %s   n_hab = %s'
              % (N, dx, dx * 1e9, flds, np.round(n_hab, 4)))
        print('  ⚠ `t_wf` 有**恒定 +1Δx = %.1f nm** 偏差 ⇒ 下表同时给"原始"与"减 Δx"'
              % (dx * 1e9))
        print('=' * 96)
        print('  %-5s %14s %14s %10s' % ('场', 't_wf 原始(nm)', 't_wf − Δx(nm)', '备注'))
        print('  ' + '-' * 62)
        for k in want:
            phi = rebuild(z, k)
            try:
                r = BM.wide_face_thickness(phi, dx, n_hab, k)
                d = r if isinstance(r, dict) else {'?': r}
                # 从 dict 里找厚度
                got = None
                for kk in ('t_wf', 't_wf_m', 't', 'thickness'):
                    if kk in d:
                        got = float(np.asarray(d[kk]).ravel()[0]); break
                if got is None:
                    print('  %-5d  ⚠ 返回 dict 没有厚度键 ⇒ 键 = %s' % (k, sorted(d)[:8]))
                    continue
                print('  %-5d %14.1f %14.1f %10s'
                      % (k, got * 1e9, (got - dx) * 1e9, '已减 Δx ✓'))
            except Exception as e:
                print('  %-5d  ❌ %s: %s' % (k, type(e).__name__, str(e)[:56]))
        print('=' * 96)


if __name__ == '__main__':
    main()
