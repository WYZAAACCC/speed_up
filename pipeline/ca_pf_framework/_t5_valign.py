#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_valign.py --- ★★★★★ 同步对齐的 `Vt` 比较（两臂同一 step）—— 最快的对齐读数

## 为什么
`t5B6np`（--B 6）的 `Vt` 在 step 20/40/60 为 3.1726 → 3.0154 → **2.9006**（**单调降**）
⇒ **溶解仍在发生**。但**必须与 A 臂在同一 step 比**才能判"是否减轻"（第九次口径纪律）。

## 判据（**预先写死**）
在同一 step 上比较两臂的 `Vt` 与"相对峰值的跌幅"：
* **`--B 6` 的跌幅显著小于 `--B 3`** ⇒ **变体数↑ ⇒ 溶解减轻** ⇒ **设计级根因确认** ✓
* **两者相近** ⇒ 变体数不是关键 ⇒ 需回到其它候选
"""
import csv
import os
import sys


def load(tag):
    P = '_exp/_bk_t5/dry_%s/series.csv' % tag
    if not os.path.exists(P):
        return {}
    d = {}
    for r in csv.DictReader(open(P, newline='')):
        try:
            d[int(r['step'])] = float(r['Vt'])
        except Exception:
            pass
    return d


A = load('t5N276F')      # --B 3
B = load('t5B6np')       # --B 6
print('=' * 92)
print('★ 同步对齐的 `Vt` 比较（`--B 3` vs `--B 6`；同 step）')
print('=' * 92)
a0 = A.get(0); b0 = B.get(0)
print('  step 0：A(B=3) Vt=%.4f ｜ B(B=6) Vt=%.4f  （应相同：同一 t=0 种子）'
      % ((a0 or 0) * 1e18, (b0 or 0) * 1e18))
print()
common = sorted(set(A) & set(B))[:14]
if not common:
    print('  ⚠ 两臂没有共同的 step（B 臂还太早或 A 臂缺该段）')
    print('  B 臂已有 step：%s' % sorted(B)[:12])
    print('  A 臂已有 step：%s' % sorted(A)[:12])
    sys.exit(0)
print('  %-7s | %-14s %-14s | %s' % ('step', 'A: --B 3', 'B: --B 6', '差（B−A, µm³）'))
for st in common:
    print('  %-7d | %-14.4f %-14.4f | **%+.4f**' % (st, A[st] * 1e18, B[st] * 1e18,
                                                   (B[st] - A[st]) * 1e18))
print()
# 峰值与跌幅
for tag, d, lab in (('t5N276F', A, '--B 3'), ('t5B6np', B, '--B 6')):
    ks = sorted(d)
    if not ks:
        continue
    pk = max(d[k] for k in ks)
    kp = max(ks, key=lambda k: d[k])
    last = ks[-1]
    print('  %-9s 峰值 Vt=%.4f µm³ @step %-5d ｜ 末 Vt=%.4f @step %-5d ｜ 自峰值跌幅 **%.1f%%**'
          % (lab, pk * 1e18, kp, d[last] * 1e18, last,
             100.0 * (pk - d[last]) / max(pk, 1e-30)))
print()
print('  ── 判据（**预先写死**）──')
print('  * 在**相同 step 范围**内比较"自峰值跌幅"：')
print('    **B 臂跌幅显著小于 A 臂** ⇒ **变体数↑ ⇒ 溶解减轻** ⇒ **设计级根因确认** ✓')
print('    **两者相近** ⇒ 变体数不是关键 ⇒ 需回到其它候选')
print('  ⚠ 注意：两臂的 step 覆盖范围不同（A 臂到 2266，B 臂才 60）')
print('    ⇒ 必须**截到共同范围**才有意义；上面的逐 step 差列已给出可比窗口。')
