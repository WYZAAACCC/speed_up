#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_branch.py --- ★★★ 定案工具：`n*`（板条厚向）该取哪个 rank-1 解？

要回答的问题（Round 141，用户批准"先修收敛性、选支暂沿用 nref"，本脚本为**定选支**做准备）
----------------------------------------------------------------------------------
对每个 Burgers 变体的形状应变 `eps`，rank-1 分解 `eps = ½(a nᵀ + n aᵀ)` 有**两个**精确解：
    解1：(n₊, a₊)     解2：(n₋, a₋)
两者都精确重构同一个 `eps`。代码必须二选一（`_rank1_axes` 用 `max|n·nref|` 选）。
而**能量判据对选支几乎没有分辨力**（实测两个解的弹性自能只差 8.6%）。

本脚本把三件事摆在一起，供外部晶体学数据（如 Xiang 2022 的 PTMT 结果）对照：
  Q-1 **两个 rank-1 解各自的能量与方向**（干净实现，不依赖引擎的选支）
  Q-2 **微弹性判据的极小点** `n_micro = argmin_n ½·eps:Λ(C,n):eps`（收敛版）
      与四个候选方向（n₊, n₋, a₊, a₋）的夹角
  Q-3 ⚠ **澄清一个可能的自相矛盾**：`_chk_habit2.py` 当时报「精修极小点离 `a_eng` 仅 0.04°，
      但其能量 5.869e3 **低于** `_chk_habit4.py` 给出的两个 rank-1 解的能量 6.757e3 / 7.342e3」。
      若两点真的只差 0.04°，能量不可能差 13% ⇒ **两者必有一个是错的**。
      本脚本用干净实现重算，**不预设谁对**。

判据（先定判据再看数）
--------------------
  B-1 **rank-1 重构误差**：`max|½(a nᵀ + n aᵀ) − eps| / max|eps|` 应 `< 1e-12`（两个解都必须过）。
  B-2 **rank-1 解的 `n` 是否就是微弹性极小点**：报 `<n_micro, n±>`、`<n_micro, a±>`。
      若某一个 `< 1°` **且** `E(该解) ≈ E(n_micro)`（相对差 <1%）⇒ 两判据一致，
      选支就取"更接近 `n_micro` 的那个解"（这与现行 `nref` 规则等价，但**从此有据**）。
      若夹角小**但**能量差 >1% ⇒ **存在实现/一致性错误，必须查**。
      若四个夹角都 > 20° ⇒ **微弹性判据与 rank-1 判据给出不同的法向** ⇒ 重大发现，须记账。

外部对照（可选）：`--xiang-m "x,y,z;x,y,z;..."` 传入外部 PTMT 的惯习面法向列表（β 母相系），
  脚本会把每个外部向量匹配到**最近的候选方向**并报夹角 ⇒ 一次定选支。

用法：
  python3 _chk_branch.py
  python3 _chk_branch.py --xiang-m "-0.7147,-0.4946,0.4946"
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
from windowB_pf3d import C_cubic, _lam_full, argmin_normal       # noqa: E402
from windowB_ti64_variants import variants                       # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--xiang-m', default='',
                help='外部 PTMT 惯习面法向，分号分隔，每项 "x,y,z"（β 母相系）')
ap.add_argument('--nsamp', type=int, default=20000)
a = ap.parse_args()

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, FV, _M = variants()
NV = len(EPS0)


def ang(u, v):
    u = np.asarray(u, float) / np.linalg.norm(u)
    v = np.asarray(v, float) / np.linalg.norm(v)
    return float(np.degrees(np.arccos(np.clip(abs(u @ v), -1.0, 1.0))))


def two_solutions(eps):
    """返回 [(n̂,â,n_raw,a_raw,err), (...)]。

    ⚠ 重要：`eps = ½(a nᵀ + n aᵀ)` 只对**未归一化**的 (n_raw, a_raw) 精确成立。
    引擎 `_rank1_axes` 返回的是**归一化**后的方向 ⇒ 该恒等式**只到尺度**。
    ⇒ 重构误差必须用 raw 判；归一化后的 (n̂, a_) 只携带**方向**信息。
    """
    w_, V = np.linalg.eigh(np.asarray(eps, float))
    o = np.argsort(w_)[::-1]
    w_, V = w_[o], V[:, o]
    mu1, mu3 = w_[0], w_[2]
    if mu1 <= 0 or mu3 >= 0:
        return None
    e1, e3 = V[:, 0], V[:, 2]
    r = np.sqrt(-mu3 / mu1)
    out = []
    for sgn in (+1.0, -1.0):
        n_raw = e1 + sgn * r * e3
        a_raw = mu1 * e1 - sgn * np.sqrt(-mu1 * mu3) * e3
        rec = 0.5 * (np.outer(a_raw, n_raw) + np.outer(n_raw, a_raw))
        err = float(np.max(np.abs(rec - eps)) / max(np.max(np.abs(eps)), 1e-30))
        n_hat = n_raw / np.linalg.norm(n_raw)
        a_hat = a_raw / np.linalg.norm(a_raw)
        out.append((n_hat, a_hat, n_raw, a_raw, err))
    return out


def E(eps, n):
    return 0.5 * float(np.einsum('ij,ijkl,kl->', eps, _lam_full(C, n), eps))


print('=' * 112)
print('_chk_branch —— 选支定案：两个 rank-1 解 vs 微弹性极小点')
print('=' * 112)

print('\nB-1 rank-1 重构误差（用**未归一化**向量判；应 < 1e-12）')
print('  %-4s %-14s %-14s %-14s' % ('变体', '解1 误差', '解2 误差', '归一化后误差'))
sols = {}
worst = 0.0
worst_norm = 0.0
for k in range(1, NV + 1):
    eps = np.asarray(EPS0[k - 1], float)
    ss = two_solutions(eps)
    assert ss is not None, '变体 %d 不是 rank-1 形状应变' % k
    sols[k] = (eps, ss)
    worst = max(worst, ss[0][4], ss[1][4])
    # 归一化后同一恒等式的误差（说明"只到尺度"）
    e_n = []
    for (n_hat, a_hat, _nr, _ar, _e) in ss:
        rec = 0.5 * (np.outer(a_hat, n_hat) + np.outer(n_hat, a_hat))
        e_n.append(float(np.max(np.abs(rec - eps)) / max(np.max(np.abs(eps)), 1e-30)))
    worst_norm = max(worst_norm, max(e_n))
    print('  %-4d %-14.3e %-14.3e %-14.3e' % (k, ss[0][4], ss[1][4], max(e_n)))
print('  => raw 最大重构误差 %.3e => %s' % (worst, 'PASS' if worst < 1e-12 else 'FAIL'))
print('  => 归一化后 %.3e（**必然不为 0**：归一化丢掉了剪切幅值）' % worst_norm)

print('\nB-2 逐变体：能量与方向')
print('  %-4s | %11s %11s %11s %11s | %7s %7s %7s %7s | %s' %
      ('变体', 'E(n1)', 'E(n2)', 'E(a1)', 'E(a2)',
       '<nm,n1>', '<nm,n2>', '<nm,a1>', '<nm,a2>', 'n1/n2 谁更低'))
n_conf = 0
n_contra = 0
for k in range(1, NV + 1):
    eps, ss = sols[k]
    n1, a1 = ss[0][0], ss[0][1]
    n2, a2 = ss[1][0], ss[1][1]
    En1, En2 = E(eps, n1), E(eps, n2)
    Ea1, Ea2 = E(eps, a1), E(eps, a2)
    nm, vm, cons = argmin_normal(C, eps, nsamp=a.nsamp)
    d = [ang(nm, x) for x in (n1, n2, a1, a2)]
    close = [i for i, x in enumerate(d) if x < 1.0]
    if close:
        j = close[0]
        e_of = (En1, En2, Ea1, Ea2)[j]
        if abs(e_of - vm) / max(abs(vm), 1e-30) < 0.01:
            n_conf += 1
        else:
            n_contra += 1
    print('  %-4d | %11.4e %11.4e %11.4e %11.4e | %6.2f %6.2f %6.2f %6.2f | %s (E=%.4e)'
          % (k, En1, En2, Ea1, Ea2, d[0], d[1], d[2], d[3],
             '解1' if En1 < En2 else '解2', min(En1, En2)))
    print('       n_micro E=%.6e  cons=%.4f  min-angle=%.2f deg'
          % (vm, cons, min(d)))

print('\n  => B-2 汇总：')
print('     [候选 <1 deg 且能量与 n_micro 差 <1%%] 的变体数 = %d/%d  (一致)' % (n_conf, NV))
print('     [夹角 <1 deg 但能量差 >1%%]       的变体数 = %d/%d  (自相矛盾, 须查)' % (n_contra, NV))
if n_contra:
    print('     => 存在"同一点却报出两个能量"的情形 => 必有错，见 B-4 的局部扫描。')
elif n_conf == NV:
    print('     => 微弹性判据与 rank-1 判据指向同一方向 => 选支可取"更接近 n_micro 的解"。')
else:
    print('     => 四个候选都离 n_micro >1 deg => 两判据给出不同法向，须记账 + 外部对照。')

# ---------------- B-4 局部扫描：判定"极小点是否真的那么窄" ----------------
print('\nB-4 局部扫描：在 rank-1 候选点附近 ±2 deg 内做一维细扫（判定 13%% 落差是否可能）')
print('  目的：B-2 说「离候选 0.05 deg 处能量低 13%%」——若成立，则极小点极窄；')
print('        若不成立，则 `argmin_normal` 的落点有问题，必须查。')
print('  %-4s %-10s | %-12s %-12s %-12s %-12s | %s' %
      ('变体', '参考点', 'E(参考点)', 'E(+0.05deg)', 'E(+0.5deg)', 'E(+2deg)', '判定'))
for k in (1, 2, 3):
    eps, ss = sols[k]
    nref = ss[0][0]
    e0 = E(eps, nref)
    # 在球面上沿一个切向走
    t = np.cross(nref, [0.0, 0.0, 1.0])
    if np.linalg.norm(t) < 1e-6:
        t = np.cross(nref, [0.0, 1.0, 0.0])
    t = t / np.linalg.norm(t)
    vals = []
    for dth in (0.05, 0.5, 2.0):
        th = np.deg2rad(dth)
        v = E(eps, np.cos(th) * nref + np.sin(th) * t)
        vals.append(v)
    drop = (e0 - min(vals)) / e0 * 100
    verdict = ('窄极小（可能）' if drop > 5 else '**不可能**：0.05 deg 内降不到 13%')
    print('  %-4d %-10s | %-12.5e %-12.5e %-12.5e %-12.5e | %s'
          % (k, 'n1(解1)', e0, vals[0], vals[1], vals[2],
             '%s (最大降 %.1f%%)' % (verdict, drop)))

# ---------------- 外部对照 ----------------
if a.xiang_m.strip():
    print('\nB-3 外部 PTMT 惯习面法向对照（β 母相系）')
    ext = []
    for tok in a.xiang_m.split(';'):
        tok = tok.strip()
        if tok:
            ext.append(np.array([float(x) for x in tok.split(',')]))
    cands = []
    for k in range(1, NV + 1):
        _, ss = sols[k]
        cands += [(k, 'n1', ss[0][0]), (k, 'n2', ss[1][0]),
                  (k, 'a1', ss[0][1]), (k, 'a2', ss[1][1])]
    print('  外部向量 -> 最近候选（分支按"离 n_micro 更近"判定，**不按标签**）：')
    # ⚠ 关键：`n1/n2/a1/a2` 的**标签**会随 `eigh` 特征向量的符号翻转而在变体间互换
    #   ⇒ 必须用"哪一支离微弹性极小点 `n_micro` 更近"来定义 A/B 支，标签不可跨变体比较。
    brA = {}
    for k in range(1, NV + 1):
        eps_k, ss_k = sols[k]
        nm_k, _v, _c = argmin_normal(C, eps_k, nsamp=a.nsamp)
        four = [('n1', ss_k[0][0]), ('n2', ss_k[1][0]),
                ('a1', ss_k[0][1]), ('a2', ss_k[1][1])]
        lbl = min(four, key=lambda t: ang(nm_k, t[1]))[0]
        brA[k] = {'n2', 'a1'} if lbl in ('n2', 'a1') else {'n1', 'a2'}
    tab = {1: 0, 0: 0}
    for j, m in enumerate(ext):
        best = min(cands, key=lambda c: ang(m, c[2]))
        dd = ang(m, best[2])
        kk, lbl = best[0], best[1]
        br = 'A(近 n_micro)' if lbl in brA[kk] else 'B(另一支)'
        tab[1 if lbl in brA[kk] else 0] += 1
        print('    [%2d] (%+.4f,%+.4f,%+.4f)  => 变体%2d / %-2s ，夹角 %.2f deg ，**%s**'
              % (j, m[0], m[1], m[2], kk, lbl, dd, br))
    print('    => 落在 **A 支 %d 个 / B 支 %d 个**（共 %d）'
          % (tab[1], tab[0], tab[1] + tab[0]))
    if tab[0] == 0:
        print('    => ★ 全部落在同一支 ⇒ **选支定案**。')
    elif tab[1] == 0:
        print('    => ★ 全部落在另一支 ⇒ **选支定案（取 B 支）**。')
    else:
        print('    => ⚠ 两支都有 ⇒ 要么变体配对还没对齐，要么"两支"与 PTMT 的两解不是同一个区分。')
    print('  => 若夹角普遍 <2 deg => 外部数据与我们的候选在同一坐标系、同一约定，可直接定选支；')
    print('     若普遍 >20 deg => 坐标系或符号约定不同，须先对齐（不得据此下结论）。')
print('=' * 112)
