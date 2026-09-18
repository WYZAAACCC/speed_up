#!/usr/bin/env python3
# =============================================================================
# 验证「改 wGB 不改物理」—— 两个 wGB 下数值求解 1D 平衡晶界，比对真实晶界能
# =============================================================================
#
# 【要验证的论断】
#   把扩散界面宽 wGB 从 4e-6 改成 12e-6（为了满足"界面内 4~8 个单元"），
#   在 mu0 = 6σ/wGB、κ = a*·wGB·σ、L = 4/3·M0/wGB **同步变化**的前提下，
#   **真实晶界能 σ 不变**。若成立，则改 wGB 只是"换分辨率"，不是"换物理"。
#
# 【为什么必须数值验证而不是靠代数】
#   代数上 κ·μ0 = 6·a*·σ² 确实与 wGB 无关（可手推）。
#   但 a* 本身是 **Moelans Algorithm 1 的不动点**，是数值解出来的；
#   真实界面能又依赖 (a*, gamma*) 与 mu 的自洽性。
#   所以"参数对"不等于"能量对" —— 必须解出真实剖面来量。
#
# 用法（在 conda 环境 ml 或 moose 下都可）：
#     python3 check_wgb_invariance.py [--wgb 4e-6 12e-6] [--pairs all|span]
# =============================================================================

import argparse
import importlib.util
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, "gen_aniso.py")          # 调用方负责放好（复制 frozen 版）
CHK = os.path.join(HERE, "check_gb_energy.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wgb", type=float, nargs="+", default=[4.0e-6, 12.0e-6])
    ap.add_argument("--pairs", choices=("all", "span"), default="all",
                    help="all = 全部 C(8,2)=28 对；span = 只取 σ 最大/最小的 4 对")
    ap.add_argument("--op-num", type=int, default=8)
    args = ap.parse_args()

    if not os.path.exists(GEN):
        sys.exit(f"找不到 {GEN} —— 请把 frozen/gen_aniso_nonad.py 复制成 gen_aniso.py")

    # check_gb_energy 里导入名过期（MU_QP_ISO -> MU_QP），这里做个兼容补丁再加载
    G = load("gen_aniso", GEN)

    # 复用 check_gb_energy 的 solve_gb（它只依赖 gen_aniso 的几个名字）
    src = open(CHK, encoding="utf-8").read()
    src = src.replace(
        "from gen_aniso import (SIGMA_H, MOB0_H, WGB, MU_QP_ISO, THETA_M,\n"
        "                       rs_factor, mob_factor, moelans_pair, compute_mu_qp,\n"
        "                       pair_dtheta, build_orientations)",
        "")   # 去掉过期导入，后面手动注入
    src = src.replace("def main():", "def _unused_main():")
    ns = {"math": math, "np": np, "__name__": "gbmod"}
    exec(compile(src, CHK, "exec"), ns)
    solve_gb = ns["solve_gb"]

    n = args.op_num
    th = G.build_orientations(n)
    pairs = [(m, k) for m in range(n) for k in range(m + 1, n)]

    sig = {}
    for m, k in pairs:
        sig[(m, k)] = G.SIGMA_H * G.rs_factor(G.pair_dtheta(th[m], th[k]))

    if args.pairs == "span":
        srt = sorted(pairs, key=lambda p: sig[p])
        pairs = [srt[0], srt[-1], srt[len(srt) // 2], srt[len(srt) // 4]]

    print("=" * 92)
    print("改 wGB 是否改变真实晶界能？—— 1D 平衡晶界数值求解")
    print("=" * 92)
    print(f"  取向（{n} 个）: {[round(t,3) for t in th]}")
    print(f"  σ 目标范围   : {min(sig.values()):.5f} ~ {max(sig.values()):.5f} J/m²")
    print(f"  测试配对数   : {len(pairs)} / {len(pairs) if args.pairs=='all' else len(sig)}")
    print()

    summary = {}
    t0 = time.time()
    for wgb in args.wgb:
        # 【关键】必须同时设 WGB 和 MU_QP —— moelans_pair 用模块级 WGB，
        # 而 mu0 必须 = 6σ/wGB（生成器的 main() 里也是这么做的）
        G.WGB = wgb
        G.MU_QP = 6.0 * G.SIGMA_H / wgb
        kappa_iso = 0.75 * G.SIGMA_H * wgb
        w_eq = math.sqrt(kappa_iso / G.MU_QP)
        print("-" * 92)
        print(f"wGB = {wgb*1e6:.4g} µm   κ_iso = {kappa_iso:.6g}   "
              f"μ0 = {G.MU_QP:.6g}   w = √(κ/μ0) = {w_eq*1e6:.4f} µm")
        print("-" * 92)
        print(f"{'σ目标':>9} {'a*':>11} {'κ*':>12} {'γ*':>9} {'σ真实':>10} "
              f"{'相对误差':>11}")
        worst = 0.0
        for p in pairs:
            a_star, g_star, kap_star = G.moelans_pair(sig[p], G.MU_QP)
            s_real, _ = solve_gb(sig[p], kap_star, g_star, G.MU_QP)
            err = (s_real - sig[p]) / sig[p]
            worst = max(worst, abs(err))
            print(f"{sig[p]:9.5f} {a_star:11.7f} {kap_star:12.6e} "
                  f"{g_star:9.5f} {s_real:10.5f} {err:+11.2e}")
        ok = worst < 1e-3
        print(f"  → 最大相对误差 = {worst:.3e}   {'✅ OK' if ok else '❌ 不通过'}")
        print()
        summary[wgb] = dict(kappa_iso=kappa_iso, mu0=G.MU_QP, w=w_eq, worst=worst)

    print("=" * 92)
    print("结论")
    print("=" * 92)
    ws = list(summary)
    print(f"{'wGB(µm)':>9} {'κ_iso':>12} {'μ0':>12} {'w(µm)':>9} {'最大相对误差':>14}")
    for wgb in ws:
        d = summary[wgb]
        print(f"{wgb*1e6:9.4g} {d['kappa_iso']:12.6g} {d['mu0']:12.6g} "
              f"{d['w']*1e6:9.4f} {d['worst']:14.3e}")
    allok = all(d["worst"] < 1e-3 for d in summary.values())
    print()
    if allok:
        print("✅ 两个 wGB 下真实晶界能都等于目标值（误差 < 1e-3）")
        print("   ⇒ 改 wGB **只换分辨率，不换物理**。论断成立。")
    else:
        print("❌ 至少一个 wGB 下晶界能偏离目标 —— **改 wGB 会改变物理**，不能这么用。")
    print(f"（总耗时 {time.time()-t0:.0f} s）")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
