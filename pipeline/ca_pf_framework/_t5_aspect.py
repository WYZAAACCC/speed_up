#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_aspect.py --- ★★★★ 判据② 的**量化读数**：板条长宽比（离线，从快照）

## 口径（**先写死**）
* **厚度** = `wide_face_thickness(φ, dx, n_hab, k) − Δx`
  * 偏差 **+1Δx** 已在 13 个解析读数上验证（3 档厚度 + 9 档长宽比 + 1 档截断）
  * **只对变体场取**（母相场数值无意义 —— §38 实测：场 0 = 1582 nm vs 变体 243–324 nm）
  * **只在形核后的快照取**（椭球种子无平坦宽面）
* **面内长/宽** = `blk_alen_nm` / `blk_wlen_nm`（`_bk_measure.blocks()` 的逐块长轴/宽度跨度）
* **长宽比** = `alen / (t_wf − Δx)`   ← **厚度做分母**

## 判据（**预先写死**，供下一轮复核）
| 量 | 期望（文献） |
|---|---|
| 板条厚度 | **数百 nm**（LPBF Ti64 二次 α′；`gla_thesis.txt:3009-3016`）|
| 板条长度 | **µm 量级** |
| **长宽比** | **> 1**（板条应是拉长的）；若 ≤1 ⇒ **可疑**，必须查 |
"""
import sys

import numpy as np

sys.path.insert(0, '.')
import _bk_measure as BM                                     # noqa: E402
from _t5_twf import rebuild_full                             # noqa: E402


def pick(res):
    """从 `wide_face_thickness` 的返回值（**dict**）里取厚度。"""
    if isinstance(res, dict):
        for kk in ('t_wf', 't_wf_m', 't', 'thickness'):
            if kk in res:
                return float(np.asarray(res[kk]).ravel()[0])
        return None
    try:
        return float(np.asarray(res).ravel()[0])
    except Exception:
        return None


def main():
    p = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_t5/dry_t5G3/snap_00200.npz'
    with np.load(p, allow_pickle=False) as z:
        N = int(np.asarray(z['N']).item())
        dx = float(np.asarray(z['L']).item()) / N
        n_hab = np.asarray(z['n_hab'], float)
        reg = np.asarray(z['region']).astype(np.int32)
        vk = np.asarray(z['vmap_keys']).ravel()
        vv = np.asarray(z['vmap_vals']).ravel()
        vmap = {int(a): int(b) for a, b in zip(vk, vv)}
        band_flds = sorted(set(np.asarray(z['band_fld']).tolist()))
        phiF = rebuild_full(z) if len(band_flds) > 1 else None

    print('=' * 96)
    print('判据② 量化读数：%s' % p)
    print('  N=%d  dx=%.1f nm  盒=%.2f µm  变体场=%s'
          % (N, dx * 1e9, N * dx * 1e6, band_flds))
    print('=' * 96)

    # ── 面内长/宽（逐块）──
    b = BM.blocks(reg, dx, vmap)
    print('  ── 块表（离线）──')
    for k in ('nblk', 'nblk_sig', 'n_var_sig', 'n_habit', 'blk_laths',
              'blk_nlath', 'blk_span_nm', 'blk_alen_nm', 'blk_wlen_nm',
              'blk_nprof', 'blk_nruns'):
        if k in b:
            print('     %-14s = %s' % (k, str(b[k])[:60]))
    alen = b.get('blk_alen_nm')
    wlen = b.get('blk_wlen_nm')

    # ── 厚度（逐场）──
    print()
    print('  ── 厚度（`t_wf − Δx`，只列变体场）──')
    thick = {}
    if phiF is not None:
        for k in band_flds:
            if k == 0:
                continue                                  # ★ 母相场排除
            try:
                v = pick(BM.wide_face_thickness(phiF, dx, n_hab, k))
                if v:
                    thick[k] = v - dx
            except Exception as e:
                print('     场 %-3d ❌ %s' % (k, str(e)[:40]))
        for k in sorted(thick):
            print('     场 %-3d t_wf−Δx = **%.1f nm**' % (k, thick[k] * 1e9))

    # ── 长宽比 ──
    print()
    print('  ── ★ 长宽比 = alen / (t_wf − Δx) ──')
    if not thick:
        print('     ⚠ 没有厚度读数 ⇒ 无法算')
    else:
        tmed = float(np.median(list(thick.values())))
        print('     厚度中位 = **%.1f nm**' % (tmed * 1e9))
        for nm, val in (('blk_alen_nm', alen), ('blk_wlen_nm', wlen)):
            if val is None:
                continue
            try:
                arr = np.atleast_1d(np.asarray(val, float))
                arr = arr[np.isfinite(arr) & (arr > 0)]
                if arr.size:
                    print('     %-14s 中位 = %.0f nm ⇒ 长宽比 = **%.2f**'
                          % (nm, np.median(arr) * 1e9 if np.median(arr) < 1e-3
                             else np.median(arr), (np.median(arr) * 1e-9) / tmed
                             if np.median(arr) > 1e-3 else np.median(arr) / tmed))
            except Exception as e:
                print('     %-14s ⚠ %s' % (nm, str(e)[:40]))
    print('=' * 96)


if __name__ == '__main__':
    main()
