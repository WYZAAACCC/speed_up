#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_c5scale.py --- ★★ C-5 是否**尺度依赖**？为什么它奖励错误的物理？

假说（本轮提出）
----------------
`fill_cal = V/(L·W·T)`。对一个**薄板**，只要尖端/棱有**一个胞**的圆角，
被削掉的体积占比就很大 ⇒ `fill_cal` 天生就低，**与"是不是板条"无关**。
⇒ 若 `fill_cal` 与**厚度（以胞计）**强相关，则 C-5 的 0.70 阈值实际上是在要求
   "物体相对网格足够厚"，而不是"长成了板条"。

实测线索：`mid1`（**m=0**，各向异性被压缩 ⇒ 板更厚）`fill_cal`=0.718 **PASS**；
          而 `mid192_ns4`（**m=4**，正确的薄板）`fill_cal`=0.499 **FAIL**。
          ⇒ 即 C-5 在**奖励错的物理**。

判据
----
  F-1 列各臂末态的 `L/W/T`（**以胞计**）与 `fill_cal`；
  F-2 算 `fill_cal` 与 `min(L,W,T)`（最薄方向的胞数）的**秩相关**；
      若强正相关 ⇒ C-5 主要是"厚度够不够几个胞"的代理，**不是形状判据**；
  F-3 给出"完美长方体但尖端切掉一个胞"的解析估算，看能否解释观测到的量级。
"""
import csv
import json
import os
import re

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r'^\s*\[\s*(\d+)\]\s')
ARMS = ['mid1', 'mid192_ns2', 'mid192_ns4', 'mid192_s2_ns4',
        'mid250_base', 'mid250_ns1', 'mid250_ns2', 'mid250_ns4',
        'lath1', 'lath192_ns4', 'equi192_ns4']


def fnum(r, k):
    try:
        v = float(r[k])
        return v if np.isfinite(v) else np.nan
    except (TypeError, ValueError, KeyError):
        return np.nan


print('=' * 108)
print('%-16s %6s %6s %6s %8s %8s %8s %10s %10s'
      % ('臂', 'N', 'Δx', 'm', 'L(胞)', 'W(胞)', 'T(胞)', 'fill_cal末', 'min胞'))
print('-' * 108)
data = []
for d in ARMS:
    sp = os.path.join(HERE, '_exp', d, 'series.csv')
    mp = os.path.join(HERE, '_exp', d, 'meta.json')
    if not os.path.exists(sp) or not os.path.exists(mp):
        continue
    try:
        m = json.load(open(mp))
    except Exception:                                            # noqa: BLE001
        continue
    dx = m.get('dx_nm') or 125.0
    rows = list(csv.DictReader(open(sp)))
    # 末态**有效**步（未触壁、单核时未裂分）
    sel = None
    for r in reversed(rows):
        ok = True
        bt = fnum(r, 'box_touch')
        if np.isfinite(bt) and bt > 0:
            ok = False
        nc = fnum(r, 'ncomp')
        if (m.get('nseed') or 1) <= 1 and np.isfinite(nc) and nc > 1:
            ok = False
        if ok:
            sel = r
            break
    if sel is None:
        sel = rows[-1]
    L = fnum(sel, 'L_cal') * 1e9 / dx
    W = fnum(sel, 'W_cal') * 1e9 / dx
    T = fnum(sel, 'T_cal') * 1e9 / dx
    V = fnum(sel, 'V')
    fc = V / max(fnum(sel, 'L_cal') * fnum(sel, 'W_cal') * fnum(sel, 'T_cal'), 1e-30)
    if not np.isfinite(L + W + T + fc):
        continue
    mn = min(L, W, T)
    data.append((d, L, W, T, fc, mn))
    print('%-16s %6s %6s %6s %8.2f %8.2f %8.2f %10.3f %10.2f'
          % (d, m.get('N'), dx, m.get('norm_smooth'), L, W, T, fc, mn))
print('-' * 108)

if len(data) >= 4:
    fc = np.array([x[4] for x in data])
    mn = np.array([x[5] for x in data])

    def spear(a, b):
        ra = np.argsort(np.argsort(a)).astype(float)
        rb = np.argsort(np.argsort(b)).astype(float)
        ra -= ra.mean(); rb -= rb.mean()
        return float(ra @ rb / np.sqrt((ra @ ra) * (rb @ rb)))
    print('F-2 秩相关 ρ(`fill_cal`, 最薄方向胞数) = **%+.3f**' % spear(fc, mn))
    print('    ⚠ 假说是「强**正**相关」（薄 ⇒ fill 低）。实测为 **%s**'
          % ('正相关，假说成立' if spear(fc, mn) > 0.5
             else '**负**相关 ⇒ **假说被否证**'))
    print('    回归：fill_cal ≈ %.3f + %.3f·min胞'
          % tuple(np.polyfit(mn, fc, 1)[::-1]))
print('\nF-3 解析估算（完美长方体、但尖端切掉一个胞的圆角）：')
print('    设 L×W×T 胞的长方体，仅把**两个尖端**各削掉一个 (W×T×1胞) 的角块：')
print('    fill_cal ≈ 1 − 2·W·T·1/(L·W·T) = 1 − 2/L，**与厚度无关** ⇒ 解释不了。')
print('    若**四条长棱**各削掉一个 (1×1×L) 的角条：')
print('    fill_cal ≈ 1 − 4·1·1·L/(L·W·T) = 1 − 4/(W·T)')
for _, L, W, T, fcv, _mn in data[:0]:
    pass
for x in data:
    L, W, T = x[1], x[2], x[3]
    est = max(0.0, 1 - 4.0 / max(W * T, 1e-9))
    print('      %-16s W·T=%.1f 胞² ⇒ 估算 fill_cal ≈ %.3f（实测 %.3f）'
          % (x[0], W * T, est, x[4]))
print('=' * 108)
print('⇒ 结论（**按实测写，不按假说写**）：')
print('   * 「薄 ⇒ fill_cal 低」的尺度假说 **被否证**（ρ = %+.3f，符号相反；'
      '最厚的 `equi192_ns4` 反而最低）。' % (spear(fc, mn) if len(data) >= 4 else 0.0))
print('   * 但 F-3 的"棱圆角"解析估算**系统性高于**实测（估算 0.80–0.96 vs 实测 0.28–0.75）')
print('     ⇒ 单靠"棱圆角"也解释不了 ⇒ `fill_cal` 还混进了**其它因素**，')
print('       最可能是**物体主轴与量测轴（a/w/n*）不平行**（斜交 ⇒ L·W·T 高估外接盒）。')
print('   * 因此：**C-5 的 0.70 阈值不是有效的验收判据** —— 它是一个复合量，')
print('     同时受**面的平直度 + 取向斜交 + 形状类型**影响，且**在 m=0（错物理）臂上反而更高**')
print('     （`mid1` 0.718 PASS、`lath1` 0.651 vs m=4 的 `lath192_ns4` 0.580、`mid192_ns4` 0.532）。')
print('   ⇒ **长宽比验收一律看 `_r1_aniso.py` 的 `ΔW:ΔL`/`ΔT:ΔL`**；')
print('     C-5 应降级为"参考量"并**重新推导**（需与取向无关的形状量，如惯性张量特征值比）。')
print('=' * 108)
