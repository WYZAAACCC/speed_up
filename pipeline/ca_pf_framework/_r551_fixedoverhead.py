#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r551_fixedoverhead.py —— **审计"固定开销 311.8 B/胞"到底是什么**。

## 为什么
`R550_MEMORY_ENVELOPE.md` 实测出（留一法误差 0.13%）：
    数组合计(MB) = **9.01**·nv·N³/2²⁰  +  **311.8**·N³/2²⁰
* `9.01 B/胞` 是每个 `nv` 的边际成本（`phi` 本身 8 B/胞 ⇒ **每场只多 1 B，很省**）
* **`311.8 B/胞` 与 `nv` 完全无关** —— 是 `phi` 单场成本的 **39 倍**
  ⇒ `N=160` 时 **1218 MB**，占 22 GB 预算的 **5.4%**，而它**不随 `nv` 变化**
  ⇒ 只要它砍得下来，10 µm 盒的可行性结论**会直接改变**（现判 `nv_max ≈ 605`，需 1176）。

## 本量具做什么
把 `LevelSetMulti` 的**每个数组**按 `nbytes` 排序，标出**归属属性名**与**形状**，
并把它们**按"是否 ∝ N³"分类**：
* **A 类**：形状含 `N³` 的三维场（每胞固定成本的主要来源）⇒ 逐个列
* **B 类**：与 `nv` 成正比的（`(nreg,N,N,N)` 的那些）—— 已知 9.01 B/胞，不是重点
* **C 类**：小表（`(nv,nv)`、`(3,3,3,3)` 等）⇒ 与 N 无关

## 判据（先写死）
* **F1 记账闭合**：A 类字节数之和 / `N³` **必须接近 311.8 B/胞**（±20%）
  ⇒ 否则说明固定开销还有别的来源，**不得就此下"砍谁"的结论**。
* **F2 列出前 12 大数组**（名字 + 形状 + 字节数 + 占比）。
* **F3 可省性标注**：对每个 A 类数组，报它**是不是可以现算/复用**（人工判断写在报告里，
  本量具只负责把它们摊开，**不自动下结论**）。
"""
import gc
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                    # noqa: E402
from T16_verify_rve import C, EPS0                             # noqa: E402

TARGET_C = 311.8        # `_r550` 拟合出来的固定项（B/胞）


def _walk(o, path, seen, depth=0):
    """产出 `(path, ndarray)`，按 `id` 去重。"""
    if depth > 5 or id(o) in seen:
        return
    seen.add(id(o))
    if isinstance(o, np.ndarray):
        yield path, o
        return
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _walk(v, '%s[%r]' % (path, k), seen, depth + 1)
        return
    if isinstance(o, (list, tuple)):
        for i, v in enumerate(o[:8]):
            yield from _walk(v, '%s[%d]' % (path, i), seen, depth + 1)
        return
    d = getattr(o, '__dict__', None)
    if isinstance(d, dict):
        for k, v in d.items():
            yield from _walk(v, '%s.%s' % (path, k), seen, depth + 1)


def main():
    N, nv = 64, 24
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(nv)]
    g = W.LevelSetMulti(N, N * 0.0625, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        df=[0.0] * (nv + 1), nv=nv)
    items = []
    seen = set()
    for p, a in _walk(g, 'g', seen):
        items.append((a.nbytes, p, a.shape, str(a.dtype)))
    items.sort(reverse=True)
    tot = sum(x[0] for x in items)
    N3 = N ** 3

    L = ['=' * 100,
         'R551 —— 固定开销审计（N=%d, nv=%d, N³=%d）' % (N, nv, N3), '=' * 100,
         '  数组合计 = **%.2f MB**（%d 个数组）' % (tot / 2**20, len(items)), '']
    L.append('  ── 前 14 大数组 ──')
    L.append('  %-9s %-7s %-26s %s' % ('MB', '占比', '形状', '属性路径'))
    for b, p, shp, dt in items[:14]:
        L.append('  %-9.3f %-6.1f%% %-26s %s  [%s]'
                 % (b / 2**20, 100.0 * b / tot, str(shp), p[:62], dt))
    del g
    gc.collect()

    # ---- F1：A 类（含 N³ 的 3D 场）字节和 / N³ 是否接近 311.8 ----
    #   ⚠ 恒等 null：`nv=0` 时 `tot/(N³)` 就是纯固定项
    eps0 = [np.asarray(EPS0[0], float)]
    g0 = W.LevelSetMulti(N, N * 0.0625, C=C, eps0=eps0, gamma=0.25, Mob=1e-9,
                         df=[0.0, 0.0], nv=1)
    i0 = []
    seen0 = set()
    for p, a in _walk(g0, 'g', seen0):
        i0.append((a.nbytes, p, a.shape, str(a.dtype)))
    i0.sort(reverse=True)
    tot0 = sum(x[0] for x in i0)
    per_cell = tot0 / N3
    del g0
    gc.collect()
    L.append('')
    L.append('  ── F1：把 `nv` 压到 1（≈纯固定项）后重测 ──')
    L.append('     数组合计 = **%.2f MB** ⇒ **%.1f B/胞**（对照 `_r550` 拟合的 %.1f）'
             % (tot0 / 2**20, per_cell, TARGET_C))
    dev = abs(per_cell - TARGET_C) / TARGET_C
    L.append('     F1 相对偏差 = **%.1f%%**（判据 ≤20%%）⇒ %s'
             % (100 * dev, '✅ PASS（记账闭合）' if dev <= 0.20 else
                '❌ FAIL ⇒ **固定开销还有别的来源，不得就此下结论**'))
    L.append('     （`nv=1` 时仍含 1 个 `phi` = 8 B/胞 ⇒ 纯固定项约 %.1f B/胞）'
             % (per_cell - 8))
    L.append('')
    L.append('  ── `nv=1` 时的前 12 大数组（这就是固定开销的面孔） ──')
    for b, p, shp, dt in i0[:12]:
        L.append('     %-9.3f MB  %-5.1f%%  %-24s %s'
                 % (b / 2**20, 100.0 * b / tot0, str(shp), p[:56]))

    # ---- 外推：砍掉最大的 k 个之后，10 µm 盒能不能装下 1176 ----
    L.append('')
    L.append('  ── 外推：若能把某些固定项砍掉，10 µm 盒（N=160）能装多少 `nv`？ ──')
    a_marg = 9.01
    N160 = 160 ** 3
    for cut_mb, lbl in ((0.0, '现状'), (0.25 * tot0 / 2**20, '砍 25% 固定项'),
                        (0.50 * tot0 / 2**20, '砍 50% 固定项'),
                        (0.75 * tot0 / 2**20, '砍 75% 固定项')):
        fix160 = (per_cell * N160 / 2**20) * (1.0 - cut_mb / max(tot0 / 2**20, 1e-9))
        per = a_marg * N160 / 2**20
        nv_max = max(int((22 * 1024 - fix160) / per), 0)
        L.append('     %-16s ⇒ 固定 %.0f MB + 每 nv %.2f MB ⇒ `nv_max` ≈ **%d** %s'
                 % (lbl, fix160, per, nv_max,
                    '✅ 够 1176' if nv_max >= 1176 else '❌ 仍不够 1176'))

    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r551_fixedoverhead.log'), 'w') as fh:
        fh.write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
