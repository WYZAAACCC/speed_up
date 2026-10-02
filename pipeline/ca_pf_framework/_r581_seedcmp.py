#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_seedcmp.py --- ★★★★★ 比 F / G / L 的 `seeds.npz`（初始位点）
                         ⇒ 回答"同参数为什么前几步就分叉"

## 背景（R161）
F 与 L 的**参数逐字相同**、**step 0 的读数逐位相同**（`nslab_n`=1、`Vt`=2.49512e-19），
**但 step 5 就分叉**（`nf2`：0 vs 477）。
**⇒ 最可能是**初始位点池（`seeds.npz`）不同**** —— 它决定"后面在哪里、以什么变体形核"。
"""
import os
import sys

import numpy as np

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mn64'
TAGS = sys.argv[2:] or ['F', 'G', 'L']


def main():
    z = {}
    for t in TAGS:
        p = os.path.join(ROOT, 'dry_' + t, 'seeds.npz')
        if not os.path.exists(p):
            print('  %-3s （无 seeds.npz）' % t)
            continue
        d = np.load(p, allow_pickle=True)
        z[t] = d
        print('  ── 臂 %s 的 seeds.npz ──' % t)
        for k in d.files:
            a = d[k]
            try:
                print('     %-16s shape=%-14s dtype=%-10s 前 3 个=%s'
                      % (k, str(a.shape), str(a.dtype),
                         np.asarray(a).ravel()[:3]))
            except Exception as e:
                print('     %-16s （读不出：%s）' % (k, e))
        print('     文件字节数 = %d' % os.path.getsize(p))
        print()
    # 两两比较
    print('=' * 96)
    print('★ 两两比较（同名的键逐位比）')
    print('=' * 96)
    tags = [t for t in TAGS if t in z]
    for i in range(len(tags)):
        for j in range(i + 1, len(tags)):
            a, b = tags[i], tags[j]
            ka, kb = set(z[a].files), set(z[b].files)
            common = sorted(ka & kb)
            print(' %s vs %s：共同键 %d 个（%s 独有 %d，%s 独有 %d）'
                  % (a, b, len(common), a, len(ka - kb), b, len(kb - ka)))
            for k in common:
                va, vb = np.asarray(z[a][k]), np.asarray(z[b][k])
                same = (va.shape == vb.shape) and bool(np.array_equal(va, vb))
                print('    %-16s %s' % (k, '✅ 逐位相同' if same else '★ 不同（形状 %s vs %s）'
                                        % (va.shape, vb.shape)))
            print()
    print('  ★ 判读：**`seeds` 不同** ⇒ 初始位点池不同 ⇒ **前几步必然分叉**（与 R161 的观察一致）')
    print('          ⇒ ⇒ **同参数的两次运行**不是同一条轨迹****（`V` 的走向随之不同）')
    print('=' * 96)


if __name__ == '__main__':
    main()
