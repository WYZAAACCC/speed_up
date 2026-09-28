#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_reinit_iters.py --- R1 reinit 审计（第 2 步）：**Q-A 迭代次数扫描**。

★ 只读引擎；**不改任何引擎代码**。调用路径与引擎**逐字一致**：
    `g.sussman_reinit(d2, iters=n)` ←→ `reinitialize()` 内的 `dn = self.sussman_reinit(d2)`
    （`LevelSetMulti.sussman_reinit` 把 iters/dtau/grad/band_cells 原样透传给模块级
      `sussman_reinit`）
  **正对照**：对"每胞只属一个配对"的状态（C1，8 个分离的核），
  把 `reinitialize()` 的结果逐胞还原成该配对的 d2，与单独调用逐位比较（须 bit-identical）。

输入 `_r1_reinit_states.npz`；输出 `_r1_reinit_iters.npz` + stdout 表（边算边打印，
  ⇒ 被 timeout 杀掉也有可用数据）。

每个状态对若干条配对场 `d2 = 0.5(φ_k − φ_l)` 扫 iters ∈ LADDER，**从同一份 d2 副本出发**：
  (a) wall 时间
  (b) 带内 `median|∇d2|`（引擎同款中心差分 `np.gradient(..., edge_order=2)`），目标 1.0
  (c) 零等值面位移：`Δ#{d2<0}`（整数胞，直接无偏）与 `Δmedian(d2[near])/dx`（亚胞统计量）
  (d) 该配对场的区域指派翻转胞数（`d2<0 → 0`，否则 `→1`）
  (e) 幂等性：对 iters=100 连做两次，第二次的 (b)(c)(d) = **噪声地板**
  (f) 与 iters=REF(=200) 在带内的最大逐胞偏差（胞）
"""
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic                                # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
MOB, DF = 1e-9, 3.5e8
HERE = os.path.dirname(os.path.abspath(__file__))
BAND = 6.0
REF = 200
LAD1 = [5, 10, 20, 30, 36, 50, 75, 100, 150]
LAD2 = [5, 20, 36, 100]
T_BUDGET = float(os.environ.get('R1_BUDGET', '1500'))     # 超过就只在日志里留痕
# ★ 记账：生成器把 L/dx 放在 `meta` 里但**没有写进 npz**（只写了 phi 帧）
#   ⇒ 这里用硬编码表兜底，并**断言**它与帧的形状自洽（N*dx == L）。
TAGCFG = {'C1': (96 * 250e-9, 250e-9), 'C2': (96 * 125e-9, 125e-9)}


def cfg_of(z, tag, N):
    if ('%s_L' % tag) in z.files:
        return float(z['%s_L' % tag]), float(z['%s_dx' % tag])
    L, dx = TAGCFG[tag]
    assert abs(N * dx - L) < 1e-18, (tag, N, dx, L)
    return L, dx


def gm(f, dx):
    g = np.gradient(f, dx, edge_order=2)
    return np.sqrt(g[0] ** 2 + g[1] ** 2 + g[2] ** 2)


def metrics(d2e, d2, near, dx):
    m = {}
    m['med_in'] = float(np.median(gm(d2, dx)[near]))
    m['med_out'] = float(np.median(gm(d2e, dx)[near]))
    m['dV'] = int((d2e < 0).sum()) - int((d2 < 0).sum())
    m['dmed'] = float((np.median(d2e[near]) - np.median(d2[near])) / dx)
    m['dmax'] = float(np.max(np.abs(d2e[near] - d2[near])) / dx)
    m['flip'] = int((np.where(d2 < 0, 0, 1) != np.where(d2e < 0, 0, 1)).sum())
    return m


def active_pairs(reg):
    pairs = set()
    for ax in range(3):
        a = reg
        b = np.roll(reg, -1, axis=ax)
        sel = a != b
        if sel.any():
            for x, y in zip(a[sel].ravel(), b[sel].ravel()):
                if x != y:
                    pairs.add((int(min(x, y)), int(max(x, y))))
    return sorted(pairs)


def main():
    z = np.load(os.path.join(HERE, '_r1_reinit_states.npz'))
    print('=' * 116)
    print('R1 reinit 审计 / Q-A：Sussman 迭代次数扫描   band_cells=%.1f  参考 iters=%d'
          % (BAND, REF))
    print('=' * 116)
    res = {}
    t_start = time.time()
    for tag in ('C1', 'C2'):
        keys = [k for k in sorted(z.files) if k.startswith(tag + '_')]
        if not keys:
            print('\n######## 配置 %s 无帧（生成器未完成）⇒ 跳过' % tag, flush=True)
            continue
        N = z[keys[0]].shape[1]
        L, dx = cfg_of(z, tag, N)
        t0 = time.time()
        g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                            df=[0.0] + [DF] * NV, workers=1, reinit_every=0,
                            reinit_dt=None, reinit_band_cells=BAND)
        print('\n######## 配置 %s : N=%d Δx=%.1f nm L=%.3f µm  （建表 %.1f s）'
              % (tag, N, dx * 1e9, N * dx * 1e6, time.time() - t0), flush=True)
        for key in keys:
            phi0 = z[key]
            reg = np.argmin(phi0, axis=0).astype(np.int8)
            pairs = active_pairs(reg)
            cand = []
            for (k, l) in pairs:
                d2 = 0.5 * (phi0[k] - phi0[l])
                cand.append((int((np.abs(d2) <= BAND * dx).sum()), k, l))
            cand.sort(reverse=True)
            print('\n  #### %s  活跃配对=%d %s' % (key, len(pairs), pairs), flush=True)
            for ip, (nb, k, l) in enumerate(cand[:2]):
                if nb == 0:
                    continue
                d2_in = 0.5 * (phi0[k] - phi0[l])
                near = np.abs(d2_in) <= BAND * dx
                lad = LAD1 if ip == 0 else LAD2
                # ---- 参考解 ----
                t0 = time.time()
                ref = g.sussman_reinit(d2_in.copy(), iters=REF)
                t_ref = time.time() - t0
                print('  ---- 配对 (k=%d,l=%d) 带胞=%d (%.3f%% of N³)  REF(%d) %.1f s ----'
                      % (k, l, nb, 100 * nb / d2_in.size, REF, t_ref), flush=True)
                print('  %6s %8s %8s %8s %8s %11s %11s %8s %11s %9s'
                      % ('iters', 'time_s', 'med_in', 'med_out', 'dV(胞)',
                         'dmed(胞)', 'dmax(胞)', 'flips', 'max|Δ−REF|', 'idem_dV'))
                # 参考解自身的幂等（= 噪声地板）
                ref2 = g.sussman_reinit(ref.copy(), iters=REF)
                mref2 = metrics(ref2, ref, near, dx)
                print('  %6s %8.2f %8.4f %8.4f %8d %+11.5f %11.5f %8d %11s %9d'
                      % ('REF2', time.time() - t0 - t_ref, mref2['med_in'],
                         mref2['med_out'], mref2['dV'], mref2['dmed'],
                         mref2['dmax'], mref2['flip'], '0.0', 0), flush=True)
                for n in lad:
                    if time.time() - t_start > T_BUDGET:
                        print('     ⚠ 时间预算 %.0f s 用尽 ⇒ 跳过 iters=%d 及其后'
                              % (T_BUDGET, n), flush=True)
                        break
                    d2 = d2_in.copy()
                    t0 = time.time()
                    d2e = g.sussman_reinit(d2, iters=n)
                    el = time.time() - t0
                    m = metrics(d2e, d2_in, near, dx)
                    dev = float(np.max(np.abs(d2e[near] - ref[near])) / dx)
                    if n in (36, 100):          # ★ 幂等只在这两档做（省 ~40% 机时）
                        d2e2 = g.sussman_reinit(d2e.copy(), iters=n)
                        m2 = metrics(d2e2, d2e, near, dx)
                    else:
                        m2 = dict(dV=0, dmed=np.nan, flip=0, med_out=np.nan)
                    print('  %6d %8.3f %8.4f %8.4f %8d %+11.5f %11.5f %8d %11.5f %9d'
                          % (n, el, m['med_in'], m['med_out'], m['dV'], m['dmed'],
                             m['dmax'], m['flip'], dev, m2['dV']), flush=True)
                    res['%s_%d_%d_i%d' % (key, k, l, n)] = np.array(
                        [el, m['med_in'], m['med_out'], m['dV'], m['dmed'],
                         m['dmax'], m['flip'], dev, m2['dV'], m2['dmed'],
                         m2['flip'], m2['med_out'], nb, nb / d2_in.size])
                del ref, ref2
        # ---- 正对照：单对路径 == 引擎 reinitialize() 路径 ----
        if tag == 'C1':
            key = keys[0]
            phiX = z[key].copy()
            g.phi = phiX.copy()
            g.reinit_iters = 100
            g.reinitialize()
            regchk = np.argmin(phiX, axis=0).astype(np.int8)
            nb0, k0, l0 = (lambda c: c[0])(sorted(
                [(int((np.abs(0.5 * (phiX[k] - phiX[l])) <= BAND * dx).sum()), k, l)
                 for (k, l) in active_pairs(regchk)], reverse=True))
            d2a = 0.5 * (g.phi[k0] - g.phi[l0])
            near0 = np.abs(0.5 * (phiX[k0] - phiX[l0])) <= BAND * dx
            d2b = g.sussman_reinit(0.5 * (phiX[k0] - phiX[l0]).copy(), iters=100)
            # 只在"该胞的 (k,l) 就是这一对"的地方比
            karr = np.argmin(phiX, axis=0)
            order = np.argsort(phiX, axis=0)
            is_kl = ((order[0] == k0) & (order[1] == l0)) | \
                    ((order[0] == l0) & (order[1] == k0))
            d = np.abs(d2a - d2b)[near0 & is_kl]
            print('\n  [正对照] 单对 g.sussman_reinit  vs  引擎 g.reinitialize()：'
                  ' 配对(k=%d,l=%d) 比较胞=%d  max|Δ|/dx=%.3e  逐位相同=%s'
                  % (k0, l0, d.size, (np.max(d) / dx if d.size else np.nan),
                     'YES' if (d.size and np.max(d) == 0.0) else 'NO'), flush=True)
        del g
    np.savez(os.path.join(HERE, '_r1_reinit_iters.npz'), **res)
    print('\n  写出 _r1_reinit_iters.npz (%d 条)  总用时 %.1f s'
          % (len(res), time.time() - t_start))
    print('=' * 116)
    return 0


if __name__ == '__main__':
    sys.exit(main())
