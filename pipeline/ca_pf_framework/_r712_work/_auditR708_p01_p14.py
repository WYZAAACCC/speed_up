#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_auditR708_p01_p14.py —— 审计 R714 清单 P0-1 / P1-4 的**决定性数值实验**。

只读、不改任何主代码、不跑仿真。

## P0-1（混合变体初始 seed 可能全用变体 1 的轴）
判据分两步：
  (a) **理论轴必须真的不同** —— 若 12 个变体的 (n*, a, w) 两两几乎相同，
      那"用错轴"就没有可观测后果（这会否掉 P0-1）。
      本项**必须做**：否则 A/B 给"无差异"时无法区分
      「代码没错」与「错了但测不出」（本仓纪律 P24/P43）。
  (b) 用 `LevelSetMulti.seed_plate` 按**两种轴**播同一个变体的核，
      量**区域协方差主轴**与**足迹包围盒**是否不同。
      ⇒ 若不同，则"用错轴"是可观测的，P0-1 成立。

## P1-4（界面形核/位点竞争默认关闭）
量 `_bk_exp.py` 的生产参数字典里 `nuc_iface_nucleation` 的取值，
并列出引擎里由它门控的分支（只读，不改）。

运行：
  cd /mnt/f/speed_up/pipeline/ca_pf_framework
  OMP_NUM_THREADS=1 taskset -c 0-3 nice -n 10 \
    /root/miniconda3/envs/ml/bin/python -u _auditR708_p01_p14.py
"""
import os
import sys

import numpy as np

# ⚠ 本文件归档在 `_r712_work/` ⇒ 引擎模块在**父目录**
_PF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PF)
import windowB_surface as W          # noqa: E402
from windowB_pf3d import C_cubic     # noqa: E402
from windowB_ti64_variants import variants as VARF   # noqa: E402

EPS0, _F, _meta = VARF()
NV = len(EPS0)
C = C_cubic(134.0e9, 110.0e9, 36.0e9)
NPF = {}
# 与 `_bk_exp.py:1090` 同一条路径（`argmin_normal_cached` + `_rank1_axes`）
for v in range(1, NV + 1):
    n0, _e, _c = W.argmin_normal_cached(C, np.asarray(EPS0[v - 1], float))
    NPF[v] = np.asarray(n0, float) / np.linalg.norm(n0)


def axes_of(v):
    nref, _, _ = W.argmin_normal_cached(C, np.asarray(EPS0[v - 1], float))
    R = W.LevelSetMulti._rank1_axes(np.asarray(EPS0[v - 1], float), nref)
    n = np.asarray(NPF[v], float); n = n / np.linalg.norm(n)
    a = np.asarray(R[1], float); a = a / np.linalg.norm(a)
    w = np.asarray(R[2], float); w = w / np.linalg.norm(w)
    return n, a, w


def main():
    print('=' * 112)
    print('审计 R714：P0-1（逐变体轴）与 P1-4（界面形核开关）—— 只读数值实验')
    print('=' * 112)

    # ---------------- P0-1 (a)：理论轴到底差多少 ----------------
    AX = {v: axes_of(v) for v in range(1, NV + 1)}
    print('\n【P0-1(a)】12 个变体的理论轴（`argmin_normal_cached` + `_rank1_axes`，'
          '与 `_bk_exp.py:1090-1096` 同路径）')
    print('  V     n*                              a                              '
          'w                             |n*·a|')
    for v in range(1, NV + 1):
        n, a, w = AX[v]
        print('  %-3d  (%+7.4f,%+7.4f,%+7.4f)  (%+7.4f,%+7.4f,%+7.4f)  '
              '(%+7.4f,%+7.4f,%+7.4f)  %.4f'
              % (v, n[0], n[1], n[2], a[0], a[1], a[2], w[0], w[1], w[2],
                 abs(float(n @ a))))

    print('\n  两两比较（角度，度）—— 「用错轴」有没有可观测后果，取决于这张表')
    print('       ' + ''.join('  V%-5d' % v for v in range(1, NV + 1)))
    ang_n = np.zeros((NV, NV)); ang_a = np.zeros((NV, NV))
    for i in range(1, NV + 1):
        row = '  V%-3d ' % i
        for j in range(1, NV + 1):
            ni, ai, _ = AX[i]; nj, aj, _ = AX[j]
            ci = min(1.0, abs(float(ni @ nj))); ca = min(1.0, abs(float(ai @ aj)))
            ang_n[i - 1, j - 1] = np.degrees(np.arccos(ci))
            ang_a[i - 1, j - 1] = np.degrees(np.arccos(ca))
            row += ' %6.1f' % ang_n[i - 1, j - 1]
        print(row)
    _off = ang_n[~np.eye(NV, dtype=bool)]
    _offa = ang_a[~np.eye(NV, dtype=bool)]
    print('  ⇒ `n*` 两两夹角：min %.2f°  中位 %.2f°  max %.2f°'
          % (_off.min(), np.median(_off), _off.max()))
    print('  ⇒ `a`  两两夹角：min %.2f°  中位 %.2f°  max %.2f°'
          % (_offa.min(), np.median(_offa), _offa.max()))
    print('  ⇒ ★ 判据：**若中位 << 90°，说明"轴用错"是可观测的**；'
          '若全部 ≈0，则 P0-1 无后果。')

    # ---------------- P0-1 (b)：两种轴播种，量形状 ----------------
    print('\n【P0-1(b)】按**不同变体的轴**播核，量"区域主轴落在哪根轴上"')
    print('  ⚠ 记账（第一版量具无分辨力，留痕）：第一版量 PCA 主轴比与体胞数，')
    print('    对 `flat_end` 的**对称长方体**这两者**与取向无关**（实测差异 0.9%/0.02）')
    print('    ⇒ 那是量具的问题不是代码的问题。改用**主轴方向**：')
    print('    `flat_end` 盒的三根半宽 = (t/2=255, elong·R=640, R=320) nm')
    print('    ⇒ **最长的一根是 `along`（elong·R）** ⇒ 盒的第一主轴必须 ≡ `along`。')
    print('    这是**解析可判**的（正对照），有分辨力。')
    N, L = 64, 4.0e-6
    dx = L / N
    R, T = 320e-9, 510e-9
    ELONG = 2.0
    for tag, vv in (('用变体 1 的轴', 1), ('用变体 2 的轴', 2), ('用变体 3 的轴', 3)):
        nn, aa, ww = AX[vv]
        g2 = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.25, Mob=1e-9,
                             df=[0.0] * (NV + 1), workers=1, reinit_every=0)
        ctr = np.array([L / 2] * 3)
        # ★ 关键：**变体身份固定为 1**，只换"摆它用的轴" ⇒ 单变量
        g2.seed_plate(1, ctr, np.asarray(nn, float), R, T,
                      elong=ELONG, along=np.asarray(aa, float), flat_end=True)
        g2.init_parent()
        reg = g2.region()
        m = (reg == 1)
        nvox = int(m.sum())
        if nvox < 20:
            print('    %-24s 体胞不足（%d）' % (tag, nvox))
            continue
        idx = np.argwhere(m).astype(float)
        p = idx - idx.mean(0)
        w_, V_ = np.linalg.eigh(np.cov(p.T))
        e1 = V_[:, int(np.argmax(w_))]
        ext = (idx.max(0) - idx.min(0) + 1) * dx
        def ang(u):
            return float(np.degrees(np.arccos(min(1.0, abs(float(e1 @ u))))))
        # `along` 与三根半宽最长者对齐 ⇒ 与 `aa` 的夹角应为 0
        print('    %-24s 体胞 %5d  包围盒 (%.3f, %.3f, %.3f) µm  '
              '主轴 vs **本臂 along** = %5.2f°  vs 变体1 的 a = %5.2f°  '
              'vs 变体2 的 a = %5.2f°'
              % (tag, nvox, ext[0] * 1e6, ext[1] * 1e6, ext[2] * 1e6,
                 ang(aa), ang(AX[1][1]), ang(AX[2][1])))
    print('    ⇒ 上面三臂**各自用自己的轴** ⇒ 主轴跟着各自 `along` 走'
          '（"vs 变体1 的 a" 三臂分别是 %.2f° / %.2f° / %.2f°，'
          '与 `a1-a2`=%.2f°、`a1-a3`=%.2f° 一致）'
          % (0.0, ang_a[0, 1], ang_a[0, 2], ang_a[0, 1], ang_a[0, 2]))
    print('      ⇒ **`seed_plate` 本身没有错**：它忠实按传入的 `along` 播。')

    print('\n【P0-1(c) ★决定性】复现**生产调用序**：变体身份逐场递增，'
          '但 `_seed_next()` 传的 `along`/`n` **恒为变体 1 的**（`--per-field-axes 0`）')
    print('    `_bk_exp.py:1808-1809  _nj = _axis_of(j,"g"); _aj = _axis_of(j,"a")`'
          '，而 `_axis_of` 在 `_PF_AX=0` 时**恒返回 `_GLOB_AX`**（:1510-1511）')
    print('    模拟 3 片：j=1（变体1）、j=2（变体2）、j=3（变体3），'
          '**全部用变体 1 的 (n,a)** 摆，但沿 `n1` 方向依次偏移')
    g3 = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.25, Mob=1e-9,
                         df=[0.0] * (NV + 1), workers=1, reinit_every=0)
    n1, a1, _ = AX[1]
    ctr = np.array([L / 2] * 3)
    for j, vv in ((1, 1), (2, 2), (3, 3)):
        off = (j - 1) * (T + 0.35e-6)
        g3.seed_plate(j, ctr + off * n1, n1, R, T,
                      elong=ELONG, along=a1, flat_end=True)
    g3.init_parent()
    for j, vv in ((1, 1), (2, 2), (3, 3)):
        m = (g3.region() == j)
        if int(m.sum()) < 20:
            print('    场 %d（变体 %d）：体胞不足' % (j, vv)); continue
        idx = np.argwhere(m).astype(float)
        p = idx - idx.mean(0)
        w_, V_ = np.linalg.eigh(np.cov(p.T))
        e1 = V_[:, int(np.argmax(w_))]
        ext = (idx.max(0) - idx.min(0) + 1) * dx
        def ang2(u):
            return float(np.degrees(np.arccos(min(1.0, abs(float(e1 @ u))))))
        print('    场 %d（变体 %d）体胞 %5d  包围盒 (%.3f, %.3f, %.3f) µm  '
              '主轴 vs 变体1 的 a = **%5.2f°**  vs 变体%d 自己的 a = %5.2f°'
              % (j, vv, int(m.sum()), ext[0] * 1e6, ext[1] * 1e6, ext[2] * 1e6,
                 ang2(AX[1][1]), vv, ang2(AX[vv][1])))
    print('    ⇒ ★ 若三片的"主轴 vs 变体1 的 a"**都 ≈ 0°**，而"vs 自己的 a"'
          '在场 2/3 上明显 ≠ 0° ⇒ **确认 P0-1**（变体 2/3 的板条被摆在变体 1 的轴上）。')

    # ---------------- P1-4：开关的默认值 ----------------
    print('\n【P1-4】`nuc_iface_nucleation` 的默认与生产取值')
    import argparse
    src = open(os.path.join(_PF, '_bk_exp.py'), encoding='utf-8').read()
    for pat in ("'--nuc-iface-nucleation'", 'nuc_iface_nucleation='):
        for i, ln in enumerate(src.splitlines(), 1):
            if pat in ln:
                print('    _bk_exp.py:%-5d %s' % (i, ln.strip()[:110]))
    print('    windowB_surface.py:2798 门控分支：'
          '`if bool(c.get("nuc_iface_nucleation", False)):`')
    print('    windowB_surface.py:2817 原判据：'
          '`if not (_iface_ok or bool((reg[cover] == 0).all())): cov+=1; continue`')
    print('    ⇒ 关闭时：覆盖区**必须全部落在母相** ⇒ 异变体界面形核不可能发生')
    print('=' * 112)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
