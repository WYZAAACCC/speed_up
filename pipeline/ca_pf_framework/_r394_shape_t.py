#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r394_shape_t.py —— 用**已验证的形状度量**（`§183` 的等效盒尺寸）跑时间序列：
长度是**持续增长**还是**饱和**？⇒ 直接回答"长宽比不足是不是时间不够"。

## 口径（与 `_r393` 同一套，`t=0` 已自证到 1–5%）
每场体素集合的协方差特征值 @@\\lambda_i@@ ⇒ **等效盒尺寸 = √(12λ_i)**（均匀长方体）。
按大小排序记 `(L, W, T)` = (长, 宽, 厚)。

## 判据（**先写死**）
* **T-1**：`L(step)` 若**线性**（分段斜率大致恒定）⇒ **时间不够**是主因；
* **T-2**：`L(step)` 若**斜率单调下降** ⇒ 有**饱和机制**（Gibbs–Thomson 尖端 / 基体耗尽 / 碰撞），
  单纯延长时间**不够**；
* **T-3**：`T(step)`（厚度）应基本恒定（否则是另一回事）。
"""
from __future__ import annotations

import glob
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
DX_NM = 62.5


def shapes(tag):
    d = os.path.join(MB, 'dry_' + tag)
    fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                key=lambda q: int(re.search(r'_(\d+)\.npz$', q).group(1)))
    out = []
    for f in fs:
        z = np.load(f, allow_pickle=True)
        reg = np.asarray(z['region'], np.int64)
        st = int(z['step'])
        Ls, Ws, Ts = [], [], []
        for k in range(1, int(reg.max()) + 1):
            idx = np.argwhere(reg == k).astype(float)
            if idx.shape[0] < 50:
                continue
            idx -= idx.mean(0)
            C = (idx.T @ idx) / idx.shape[0] * DX_NM ** 2
            ev = np.sort(np.linalg.eigvalsh(C))[::-1]
            box = np.sqrt(np.maximum(ev, 0) * 12.0)
            Ls.append(box[0]); Ws.append(box[1]); Ts.append(box[2])
        if Ls:
            out.append((st, float(np.median(Ls)), float(np.median(Ws)),
                        float(np.median(Ts))))
    return np.asarray(out, float)


def main():
    for tag in (sys.argv[1:] or ['saSet2']):
        A = shapes(tag)
        if A.size == 0:
            print('%-14s ⚠ 无数据' % tag); continue
        print('=' * 92)
        print('### %s  形状时间序列（12 场的中位；等效盒尺寸 nm）' % tag)
        print('  %-6s %10s %10s %10s %10s' %
              ('step', '长 L', '宽 W', '厚 T', 'L/T'))
        for r in A[::max(len(A) // 10, 1)]:
            print('  %-6.0f %10.0f %10.0f %10.0f %10.2f'
                  % (r[0], r[1], r[2], r[3], r[1] / r[3]))
        r = A[-1]
        print('  %-6.0f %10.0f %10.0f %10.0f %10.2f'
              % (r[0], r[1], r[2], r[3], r[1] / r[3]))
        print()
        print('  ## T-1/T-2：`L` 的分段斜率（nm/步）')
        n = len(A)
        for lo, hi, lab in ((0.0, 0.25, '前 1/4'), (0.25, 0.5, '1/4–1/2'),
                            (0.5, 0.75, '1/2–3/4'), (0.75, 1.0, '后 1/4')):
            i0 = int(lo * (n - 1)); i1 = int(hi * (n - 1))
            if i1 <= i0:
                continue
            ds = A[i1, 0] - A[i0, 0]
            print('    %-8s dL/dstep = %+7.3f ；dW/dstep = %+7.3f ；dT/dstep = %+7.3f'
                  % (lab, (A[i1, 1] - A[i0, 1]) / ds,
                     (A[i1, 2] - A[i0, 2]) / ds,
                     (A[i1, 3] - A[i0, 3]) / ds))
        s = [(A[i + 1, 1] - A[i, 1]) / (A[i + 1, 0] - A[i, 0])
             for i in range(n - 1)]
        s = np.asarray(s)
        mono = float((np.diff(s) < 0).mean())
        print()
        print('  ## 判读')
        print('    末段 dL/dstep = **%+.3f nm/步**；全程相邻斜率**下降**的占比 = %.2f'
              % (s[-1], mono))
        if mono > 0.6:
            print('    ⇒ ⚠ **斜率在单调下降 ⇒ 有饱和机制**（不是单纯时间不够）')
        else:
            print('    ⇒ ✅ **斜率大致恒定 ⇒ 主要是时间不够**（继续跑会长）')
        print('    `T` 全程范围 = %.0f … %.0f nm（极差 %.1f%%）'
              % (A[:, 3].min(), A[:, 3].max(),
                 100 * (A[:, 3].max() - A[:, 3].min()) / A[:, 3].mean()))


if __name__ == '__main__':
    sys.exit(main())
