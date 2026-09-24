#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_timewin.py --- 实测滑动窗口 vs 全域 的每步耗时（构型与 demo_meltpool_growth.py 完全一致）"""
import os, sys, time, cProfile, pstats, io
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ca3d import CA3D, IRF, T_LIQ, T_SOL

DX = 3.0e-6
NX, NY, NZ = 67, 100, 67
T_PEAK, SIGMA, TAU, T_BATH = 2600.0, 90e-6, 3.0e-4, 353.0
NGX, NGY = 2, 3
DOM = NX * NY * NZ
NST = int(sys.argv[1]) if len(sys.argv) > 1 else 300


def build():
    ca = CA3D(NX, NY, NZ, DX, irf=IRF(), seed=2026)
    ca.nucleate_substrate_grid(NGX, NGY)
    T_init = ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH)
    ca.seed_solid_from_substrate(T_init, T_SOL)
    V_max = max(float(ca.irf(np.array([T_LIQ - T_SOL]))[0]), 0.2)
    dt = DX / (4.0 * V_max)
    return ca, dt


def run(mode, nst=NST, prof=False):
    ca, dt = build()
    box = [None]
    orig_ab = ca.active_box
    def rec_ab(margin=None, front=None, **kw):
        b = orig_ab(margin, front=front) if front is not None else orig_ab(margin)
        box[0] = b; return b
    ca.active_box = rec_ab
    w = None if mode == "auto" else "full"
    blocks, wfrac = [], []
    t_start = time.perf_counter()
    for s in range(nst):
        ca.t = s * dt
        T = ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH)
        t0 = time.perf_counter()
        ca.step(dt, T, window=w)
        blocks.append(time.perf_counter() - t0)
        b = box[0] if box[0] is not None else (0, NX, 0, NY, 0, NZ)
        wfrac.append(((b[1]-b[0]) * (b[3]-b[2]) * (b[5]-b[4])) / DOM)
    tot = time.perf_counter() - t_start
    bl = np.array(blocks).reshape(-1, 100)
    print("[%s] 总 %.1f s, 每步 %.1f ms; 分块 ms/步: %s" % (
        mode, tot, 1000 * np.array(blocks).mean(),
        " ".join("%.0f" % (1000 * b.mean()) for b in bl)))
    print("       窗口体积占比 分块: %s" % " ".join(
        "%.1f%%" % (100 * w.mean()) for w in np.array(wfrac).reshape(-1, 100)))
    if prof:
        ca2, dt2 = build()
        def one():
            for s in range(60, 160):
                ca2.t = s * dt2
                ca2.step(dt2, ca2.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH), window=w)
        pr = cProfile.Profile(); pr.enable(); one(); pr.disable()
        s_ = io.StringIO()
        pstats.Stats(pr, stream=s_).sort_stats("tottime").print_stats(14)
        print(s_.getvalue())
    return ca


print("=== 域 %d 胞, 步数 %d ===" % (DOM, NST))
ca_auto = run("auto")
ca_full = run("full")
same = np.array_equal(ca_auto.gid, ca_full.gid)
print("\n两种模式的 gid 是否逐位相同: %s (不同胞数 %d)" % (
    same, int((ca_auto.gid != ca_full.gid).sum())))