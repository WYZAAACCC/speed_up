#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_ckpt_negctl.py --- ★★★★★ **造"被破坏的检查点"**（四个负对照的输入端）

## 为什么用"造副本"而不是给生产代码加破坏开关
1. **不污染生产代码**（goal：新开关一律默认关 ⇒ 越少越好）；
2. **语义更准**：破坏项 = "**那一项没被存/没被回填**"的**等价物**；
3. **可复现**：每个副本都落盘、可与原帧逐字节对比。

## 四个负对照（goal 任务(5) 逐字）
| # | 破坏 | 怎么造 | 预期 |
|---|---|---|---|
| **1** | **φ 只存带内** | 保留 `\\|φ\\| ≤ band·Δx`，其余填 `1e3`（各场自己的坐标） | **必须 FAIL** |
| **2** | **不恢复 RNG 状态** | 把 `nuc_rng_state` 清成**空数组**（引擎代码里 `if _rs:` ⇒ **静默跳过**） | **必须 FAIL** |
| **3** | **不恢复 `_cnt`/`_t_since_reinit`** | 两者都置 **0** | **必须 FAIL** |
| **4** | **不恢复 `_nuc['dbg']['ok']`** | `nuc_ok` 置 **0** | **允许 PASS，但必须解释** |
"""
import os
import sys
import tempfile

import numpy as np


def sabotage(src, dst, kind, band_cells=6):
    z = np.load(src, allow_pickle=False)
    st = {k: z[k] for k in z.files}
    note = ''
    if kind == 'phi_band_only':
        # ★ 只留 |φ| ≤ band·Δx：带外按 `np.full(..., 1e3)` 的语义填 1e3
        phi = np.array(st['phi'], copy=True)
        N = int(np.asarray(st['N']).item())
        L = float(np.asarray(st['L']).item())
        dx = L / N
        thr = band_cells * dx
        keep = np.abs(phi) <= thr
        n_keep = int(keep.sum())
        phi[~keep] = 1e3
        st['phi'] = phi
        note = ('φ 只保留 |φ| ≤ %dΔx（保留 %d / %d 个元素 = %.3f%%）'
                % (band_cells, n_keep, phi.size, 100.0 * n_keep / phi.size))
    elif kind == 'no_rng':
        st['nuc_rng_state'] = np.zeros(0, np.uint8)
        note = 'nuc_rng_state 清空（引擎里 `if _rs:` ⇒ 静默跳过恢复）'
    elif kind == 'no_reinit_clock':
        st['_cnt'] = np.int64(0)
        st['_t_since_reinit'] = np.float64(0.0)
        note = '`_cnt` 与 `_t_since_reinit` 归零（reinit 节拍错位）'
    elif kind == 'no_dbg_ok':
        st['nuc_ok'] = np.int64(0)
        note = '`_nuc[\'dbg\'][\'ok\']` 归零（attach 选端的奇偶会不同）'
    else:
        raise SystemExit('未知的破坏类型：%s' % kind)
    with open(dst, 'wb') as fh:
        np.savez_compressed(fh, **st)
    print('  [%s] ⇒ %s' % (kind, dst))
    print('      %s' % note)
    print('      体积 %.2f MB（原帧 %.2f MB）'
          % (os.path.getsize(dst) / 1048576.0, os.path.getsize(src) / 1048576.0))


if __name__ == '__main__':
    sabotage(sys.argv[1], sys.argv[2], sys.argv[3],
             int(sys.argv[4]) if len(sys.argv) > 4 else 6)
