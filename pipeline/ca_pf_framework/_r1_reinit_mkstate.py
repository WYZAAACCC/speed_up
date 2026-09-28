#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_reinit_mkstate.py --- R1 reinit 审计（第 1 步）：生成**冻结的代表性状态**。

★ 本脚本**只读**引擎（import windowB_surface），**不改任何引擎代码**。

产物 `_r1_reinit_states.npz`：每个配置两帧快照（phi, 形状 (nreg,N,N,N), float64）
  `C1_s06` / `C1_s40`   配置 1 = "R24 口径"（大盒、等轴盘核、核间距大 ⇒ 配对少）
  `C2_s06` / `C2_s40`   配置 2 = "薄板条口径"（小盒、elong=3 的薄片核 ⇒ 会碰撞 ⇒ 变体-变体界面对多）

两帧的含义
  `s06` = 撒核后推进 **6 步**（**reinit 全程关闭**）
        ⇒ 这正是生产里"第一次定时 reinit"看到的态（生产 reinit_dt=6e-7，N=96/Δx=250 时
          间隔 = 6e-7/1.071e-7 = 5.60 步）。
  `s40` = 推进 **40 步**（**reinit 全程关闭**）⇒ 界面带 |∇d2| 退化到 ~40 步的量级，
        是**比生产更苛刻**的输入（保守方向）。

⚠ 记账（必须随读数一起引用）
  * C2 的盒长 L=12 µm **违反 R24 的"L ≥ 2×板条长(8.1µm)"守卫**。本文件产出的状态
    **只用于 reinit 数值学**（迭代次数/窄带占比/包围盒），**不得**用于任何形貌（L:W:T、
    分组）读数。C1 的 L=24 µm 满足 R24。
  * 两帧都在 **reinit 关闭**下推进 ⇒ 不是生产轨迹上的真实态，而是"若不定时 reinit
    会退化到什么程度"的**上界**输入。
"""
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic                                # noqa: E402
from windowB_pf3d import argmin_normal as _argmin_normal        # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
MOB, DF = 1e-9, 3.5e8
NPF = {v + 1: _argmin_normal(C, np.asarray(EPS0[v], float))[0] for v in range(NV)}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   '_r1_reinit_states.npz')

CFG = [
    dict(tag='C1', N=96, dx=250e-9, nseed=8, R=1.5e-6, t=0.9e-6, elong=1.0,
         jit=0.25),
    # ★ 修（首跑崩在这）：`seed_plate` 的硬检查 `elong*R <= margin`，
    #   首版 R=0.8µm/elong=3 ⇒ 2.4µm > margin 2.258µm ⇒ ValueError。
    #   现在 R=0.6µm（elong*R=1.8µm）、抖动降到 0.10*step（margin ≥ 2.4µm）。
    dict(tag='C2', N=96, dx=125e-9, nseed=8, R=0.6e-6, t=0.30e-6, elong=3.0,
         jit=0.10),
]
NSTEP = 40


def build(cfg):
    N, dx = cfg['N'], cfg['dx']
    L = N * dx
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=1, reinit_every=0,
                        reinit_dt=None,            # ★ 本脚本全程不做 reinit
                        reinit_band_cells=6.0)
    rng = np.random.default_rng(7)
    R, t, el = cfg['R'], cfg['t'], cfg['elong']
    # 抖动格子布点：确保种子不重叠、不被盒面截断
    n1 = int(np.ceil(cfg['nseed'] ** (1 / 3.0)))
    step = L / n1
    ns = 0
    for i in range(n1):
        for j in range(n1):
            for k in range(n1):
                if ns >= cfg['nseed']:
                    break
                c = np.array([(i + 0.5) * step, (j + 0.5) * step,
                              (k + 0.5) * step])
                c = c + (rng.random(3) - 0.5) * cfg['jit'] * step
                kk = ns + 1                       # 8 个核用 8 个**不同**变体
                nrm = np.asarray(NPF[kk], float)
                nrm = nrm / np.linalg.norm(nrm)
                al = None
                if el > 1.0:
                    al = np.asarray(g.atab[kk], float)
                    al = al / np.linalg.norm(al)
                g.seed_plate(kk, c, nrm, R, t, elong=el, along=al)
                ns += 1
    g.init_parent()
    return g, ns


def step_stats(g, tag):
    reg = g.region()
    f = 1.0 - float((reg == 0).sum()) / g.N ** 3
    nb = 0
    for ax in range(3):
        nb += int((reg != np.roll(reg, -1, axis=ax)).sum())
    nvar = int(sum(1 for k in range(1, g.nreg)
                   if float((reg == k).sum()) / g.N ** 3 > 0.002))
    # 活跃配对数（与 reinitialize() 内的算法一致）
    pairs = set()
    for ax in range(3):
        a = reg
        b = np.roll(reg, -1, axis=ax)
        sel = a != b
        if sel.any():
            for x, y in zip(a[sel].ravel(), b[sel].ravel()):
                if x != y:
                    pairs.add((int(min(x, y)), int(max(x, y))))
    print('     [%s] f=%.4f  界面键=%-7d  非零变体=%d  活跃配对=%d'
          % (tag, f, nb, nvar, len(pairs)), flush=True)
    return f, nb, len(pairs)


def main():
    print('=' * 100)
    print('R1 reinit 审计 / 第 1 步：生成冻结状态')
    print('  机器：nproc=%d' % (os.cpu_count() or 0))
    print('=' * 100)
    store = {}
    meta = {}
    for cfg in CFG:
        tag = cfg['tag']
        t0 = time.time()
        try:
            g, ns = build(cfg)
        except Exception as e:                       # noqa: BLE001
            print('  ⚠ %s 建态失败（%s: %s）⇒ 跳过，已完成的配置照常写出'
                  % (tag, type(e).__name__, e), flush=True)
            continue
        t_build = time.time() - t0
        dt = 0.15 * cfg['dx'] / (MOB * DF)
        print('  --- %s  N=%d Δx=%.1f nm  L=%.3f µm  种子=%d (R=%.2f µm t=%.2f µm elong=%.1f) ---'
              % (tag, cfg['N'], cfg['dx'] * 1e9, cfg['N'] * cfg['dx'] * 1e6, ns,
                 cfg['R'] * 1e6, cfg['t'] * 1e6, cfg['elong']), flush=True)
        print('     构造用时 %.1f s（含 argmin_normal 建表）；dt=%.4e s' % (t_build, dt),
              flush=True)
        step_stats(g, tag + '@s00')
        t1 = time.time()
        for it in range(1, NSTEP + 1):
            g.elastic_driving()
            g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                      mob_beta=3.5, mob_beta_w=2.3, adv_grad='proj2')
            if it in (6, NSTEP):
                store['%s_s%02d' % (tag, it)] = g.phi.copy()
                step_stats(g, '%s@s%02d' % (tag, it))
                print('       累计 %.1f s（%.2f s/步）'
                      % (time.time() - t1, (time.time() - t1) / it), flush=True)
        meta['%s_dt' % tag] = dt
        meta['%s_L' % tag] = cfg['N'] * cfg['dx']
        meta['%s_dx' % tag] = cfg['dx']
        np.savez(OUT, **store)          # ★ 每个配置存一次：后一个崩了不丢前面的
        print('     （已增量写出 %s，%d 帧）'
              % (OUT, len([k for k in store if k.startswith(tag)])), flush=True)
    np.savez(OUT, **store)
    print()
    print('  写出 %s' % OUT)
    for k, v in sorted(store.items()):
        nz = int((v < 1e2).sum())          # 非空区域胞数（母相初值 1e3）
        print('    %-10s shape=%s  已占用胞=%d (%.3f%%)'
              % (k, v.shape, nz, 100.0 * nz / v[0].size))
    sz = os.path.getsize(OUT) / 1e6
    print('  文件大小 %.1f MB' % sz)
    print('=' * 100)
    return 0


if __name__ == '__main__':
    sys.exit(main())
