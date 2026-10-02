#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_proj.py --- ★★★★ 判据②：用**投影法**量单根板条的三维几何量（**独立于 `t_wf`**）

## 为什么需要它（两条独立路径才算数）
`blk_alen_nm`/`blk_wlen_nm` 依赖 `axes_var`（要 `_bk_exp.py` 的 `EPS0`/`NPF`）⇒ **离线拿不到**（§39.2）。
**替代**：快照**自带三个轴** `n_hab`（厚度方向）/ `w_ax` / `a_ax`；
**单变体时（`n_var_sig=1`）它们就是该变体的三轴** ⇒ 把 `region` 的体素**投影**上去算跨度。

## ★ 关键对照（**判据先写死**）
* **投影法厚度**（沿 `n_hab` 的跨度）**vs** `t_wf − Δx`
* **判据**：两者相对差 **≤ 30%** ⇒ 两条独立路径互证；
  差 > 30% ⇒ **必须先解释差异，不得采信任一条**（这正是我在 §36–38 反复吃过的教训）。

## 用法
  python _t5_proj.py <snap.npz>
"""
import sys

import numpy as np

sys.path.insert(0, '.')
import _bk_measure as BM                                     # noqa: E402
from _t5_twf import rebuild_full                             # noqa: E402

P = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_t5/dry_t5G3/snap_00200.npz'
with np.load(P, allow_pickle=False) as z:
    N = int(np.asarray(z['N']).item())
    dx = float(np.asarray(z['L']).item()) / N
    n_hab = np.asarray(z['n_hab'], float)
    w_ax = np.asarray(z['w_ax'], float)
    a_ax = np.asarray(z['a_ax'], float)
    reg = np.asarray(z['region']).astype(np.int32)
    band_flds = sorted(set(np.asarray(z['band_fld']).tolist()))
    phiF = rebuild_full(z) if len(band_flds) > 1 else None


def pick(res):
    if isinstance(res, dict):
        for kk in ('t_wf', 't_wf_m', 't', 'thickness'):
            if kk in res:
                return float(np.asarray(res[kk]).ravel()[0])
        return None
    try:
        return float(np.asarray(res).ravel()[0])
    except Exception:
        return None


ax3 = (a_ax / np.linalg.norm(a_ax), w_ax / np.linalg.norm(w_ax), n_hab / np.linalg.norm(n_hab))
print('=' * 100)
print('投影法（独立于 t_wf）：%s' % P)
print('  N=%d dx=%.1f nm  盒=%.2f µm' % (N, dx * 1e9, N * dx * 1e6))
print('  轴：a_ax=%s  w_ax=%s  n_hab=%s' % tuple(np.round(v, 3) for v in ax3))
print('=' * 100)
print('  %-4s %8s %10s %10s %10s %12s %10s %8s'
      % ('场', '胞数', 'a 跨(nm)', 'w 跨(nm)', 'n 跨(nm)', 't_wf−Δx', '相对差', '判定'))
print('  ' + '-' * 84)
ok = bad = 0
for k in [int(x) for x in np.unique(reg)]:
    if k == 0:
        continue
    idx = np.argwhere(reg == k)                      # (m,3) 体素索引
    if idx.size == 0:
        continue
    ctr = (idx + 0.5) * dx                           # 物理坐标
    # 逐轴投影跨度（跨度 = max − min；周期盒这里先不做最小镜像，见下）
    sp = []
    for ax in ax3:
        pr = ctr @ ax
        sp.append((pr.max() - pr.min()))
    twf = None
    if phiF is not None:
        try:
            v = pick(BM.wide_face_thickness(phiF, dx, n_hab, k))
            twf = (v - dx) if v else None
        except Exception:
            pass
    rel = ''
    verdict = ''
    if twf:
        rel = '%+.1f%%' % ((sp[2] - twf) / twf * 100)
        verdict = '✅' if abs(sp[2] - twf) / twf <= 0.30 else '❌ 差>30%'
        ok += (verdict == '✅')
        bad += (verdict != '✅')
    print('  %-4d %8d %10.1f %10.1f %10.1f %12s %10s %8s'
          % (k, idx.shape[0], sp[0] * 1e9, sp[1] * 1e9, sp[2] * 1e9,
             ('%.1f' % (twf * 1e9)) if twf else '—', rel, verdict))
print()
print('  ── 判据（预先写死）──')
print('  互证通过 %d 个场，未过 %d 个场' % (ok, bad))
if bad:
    print('  ⚠ **必须先解释差异**，不得只采信其中一条路径（§36–38 的教训）')
print('  ⚠ 口径提醒：投影跨度是**包围盒跨度**（会被碎片/凸起撑大），')
print('     而 `t_wf` 是**两宽面之间的距离** ⇒ 两者**本来就不该完全相等**；')
print('     这条对照的用途是**发现量级错误**，不是判逐位相同。')
print('=' * 100)
