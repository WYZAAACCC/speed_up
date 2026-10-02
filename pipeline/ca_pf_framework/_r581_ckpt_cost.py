#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_ckpt_cost.py --- ★★★★★ **实测**：把整场 φ（f64）加进快照的**真实代价**

## 为什么要实测
`_bk_exp.py:2370` 的注释写「整场 `phi`（**+164.7 MB/快照、+10.5 s @N=192**）」
—— 而 **N=192 ³ × 4 B = 28.3 MB**（f32）⇒ **与 164.7 MB 差 5.8 倍** ⇒
**这个数对不上，不许照抄**（P21：新数与前数矛盾时先怀疑量具/口径）⇒ **本脚本实测**。

## 量什么
| 量 | 怎么量 |
|---|---|
| 原始字节 | `N³ × itemsize` |
| **压缩后** | `np.savez_compressed` 到真实文件，量文件大小 |
| **写盘耗时** | `time.perf_counter()` |
| **读回耗时** | `np.load` + 取 `phi` |
| **读回是否逐位** | `np.array_equal`（**f64 必须逐位**） |
"""
import os
import sys
import time

import numpy as np

OUT = '_r581_ckpt_probe'
os.makedirs(OUT, exist_ok=True)


def main():
    Ns = [int(x) for x in (sys.argv[1:] or ['160', '192'])]
    print('=' * 100)
    print('实测：整场 φ 加进快照的代价（本机、本 numpy）')
    print('=' * 100)
    for N in Ns:
        # 造一个**像样**的 φ：一个球的有符号距离场（**平滑 ⇒ 压缩率会好**）
        x = np.arange(N) * 1.0
        X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
        c = N / 2.0
        phi64 = np.sqrt((X - c) ** 2 + (Y - c) ** 2 + (Z - c) ** 2) - N / 4.0
        # 再叠一点界面附近的细节（真实 φ 在界面附近有结构）
        phi64 = phi64 + 0.01 * np.sin(X * 0.7) * np.cos(Y * 0.9) * np.exp(
            -np.abs(phi64) / 3.0)
        phi32 = phi64.astype(np.float32)
        reg = np.zeros((N, N, N), np.int16)
        reg[phi64 < 0] = 1
        print()
        print('  ── N=%d（胞数 %.2f M）──' % (N, N ** 3 / 1e6))
        for tag, arr in (('f64', phi64), ('f32', phi32)):
            raw = arr.nbytes
            p = os.path.join(OUT, 'probe_%d_%s.npz' % (N, tag))
            t0 = time.perf_counter()
            np.savez_compressed(p, region=reg, phi=arr)
            t1 = time.perf_counter()
            size = os.path.getsize(p)
            t2 = time.perf_counter()
            z = np.load(p)
            back = z['phi']
            t3 = time.perf_counter()
            same = bool(np.array_equal(back, arr))
            print('    %s：原始 %6.1f MB ⇒ 落盘 %6.1f MB（压缩 %.2f×）'
                  '  写 %.2f s  读 %.2f s  读回逐位=%s'
                  % (tag, raw / 1e6, size / 1e6, raw / size, t1 - t0, t3 - t2,
                     '✅' if same else '❌'))
            # 只存 φ（不存 region）也量一下
            p2 = os.path.join(OUT, 'probe_%d_%s_phionly.npz' % (N, tag))
            np.savez_compressed(p2, phi=arr)
            print('        只存 φ：%6.1f MB' % (os.path.getsize(p2) / 1e6))
            os.remove(p)
            os.remove(p2)
        print('    （`region` 单独：原始 %.1f MB）' % (reg.nbytes / 1e6))
    print()
    print('  ★ 读法：**f64 的落盘大小**才是"每段检查点"的真实成本 ⇒')
    print('     用它 × 检查点个数 = 一次长跑的额外磁盘占用')
    print('=' * 100)


if __name__ == '__main__':
    main()
