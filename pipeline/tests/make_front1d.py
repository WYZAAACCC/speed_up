#!/usr/bin/env python3
# =============================================================================
# Gate 1 · 步骤 3 的算例生成器：按 s = W/(D/V) 生成 1D 前沿基准算例
# =============================================================================
#
# 【核心设计：固定 δ_c，扫 W】
#
#   模型只有一个长度尺度 W，却要同时解析**界面**(W) 与**溶质边界层**(δ_c=D/V)。
#   若"固定 W 扫 V"，则 s ≳ 5 之后 δ_c 细到网格解析不了，测到的是数值垃圾。
#   所以反过来：**固定 δ_c（即固定 V），扫 W = s·δ_c**。
#
#       δ_c = D/V            全扫描不变
#       W   = s·δ_c
#       dx  = min(W, δ_c)/8  两个尺度恒被解析
#       域长 = 20·max(W, δ_c)
#       单元 = 160·max(s, 1/s)
#
# 【关键关系（已数值验证，见 tests/front1d.i 文件头）】
#   双势阱 f = Wg·η²(1−η)²/4 + dG·h(η)
#       ξ  = sqrt(8κ/Wg)                （界面宽）
#       σ  = sqrt(κWg)/(3√8)            （界面能）
#       v  = 3·ξ·L·|dG|                 （前沿速度 ← **不是** L·|dG|）
#   保持 σ = 0.6 不变 ⇒ κWg = (3√8·σ)² = 常数 ⇒ κ ∝ ξ, Wg ∝ 1/ξ
#   取 dG = −0.05·Wg（5% 倾斜，保双势阱完整）⇒ ξ·|dG| = 常数 ⇒ **L 与 s 无关**
#
# 用法：
#   python3 make_front1d.py --s 10 --out case_s10.i
# =============================================================================

import argparse
import io
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "front1d.i")

# --- 固定不变量（与 tests/front1d.i 一致）---
SIGMA = 0.6            # J/m^2，界面能（不随 s 变）
K_C, A_PART, C0 = 0.9, 0.264, 0.036
M_MOB = 2.8e-9         # 溶质迁移率

# ⚠⚠ kappa_c 必须让「c 的界面宽」远小于「η 的界面宽」，否则溶质剖面跟不上 η、
#     分凝被抹平。实测（静止界面控制实验，2026-09-18）：
#         kappa_c = 1.125e-11 (生产值) -> w_c = 3.54 um >> xi  -> k_eff 漂到 0.6947 ✗
#         kappa_c = 1e-14              -> w_c = 0.105 um ~ xi   -> k_eff = 0.6303 ✓
#         kappa_c = 1e-16              -> w_c = 0.0105 um << xi -> k_eff = 0.6303 ✓
#     判据：  w_c = sqrt(kappa_c/k_c)  <<  xi = s*delta_c
#     **生产配置的 kappa_c = 1.125e-11 给出 w_c = 3.54 um，比晶界宽 d = 2 um 还大**
#     —— 即生产的分配系数从未在其自身的 kappa_c 下被验证过。见 GATE1_PLAN.md。
KAPPA_C = 1.0e-14   # 与生产同步（2026-09-18 Gate 1 修正；1e-16 结果相同，已收敛）
D_L = M_MOB * K_C      # = 2.52e-9 m^2/s
DELTA_C = 2.0e-6       # m，溶质边界层厚度（全扫描固定 ⇒ V 固定）
V_FRONT = D_L / DELTA_C


def params_for(s):
    """给定 s = W/(D/V)，返回该档的全部参数。"""
    xi = s * DELTA_C                      # 界面宽 W = ξ
    kWg = (3.0 * math.sqrt(8.0) * SIGMA) ** 2
    kappa = math.sqrt(kWg * xi ** 2 / 8.0)
    Wg = math.sqrt(kWg / (xi ** 2 / 8.0))
    dG = -0.05 * Wg
    L = V_FRONT / (3.0 * xi * abs(dG))
    dx = min(xi, DELTA_C) / 8.0
    Ldom = 20.0 * max(xi, DELTA_C)
    n = int(round(Ldom / dx))
    return dict(s=s, xi=xi, kappa=kappa, Wg=Wg, dG=dG, L=L,
                dx=dx, Ldom=Ldom, n=n, x0=Ldom * 0.125,
                t_end=12.0 * DELTA_C / V_FRONT)


def build(s, template=TEMPLATE):
    p = params_for(s)
    t = io.open(template, encoding="utf-8").read()
    reps = [
        ("  nx = 160", "  nx = %d" % p["n"]),
        ("  xmax = 4.0e-5", "  xmax = %.6e" % p["Ldom"]),
        ("    prop_values = '5.833e-4   3.6e-6    1.125e-11 2.8e-9'",
         "    prop_values = '%.6e   %.6e    %.6e 2.8e-9'" % (p["L"], p["kappa"], KAPPA_C)),
        ("    constant_expressions = '7.2e6 -3.6e5 0.9 0.036 0.264'",
         "    constant_expressions = '%.6e %.6e 0.9 0.036 0.264'" % (p["Wg"], p["dG"])),
        ("expression = '0.5*(1-tanh((x-5.0e-6)/2.0e-6))'",
         "expression = '0.5*(1-tanh((x-%.6e)/%.6e))'" % (p["x0"], p["xi"])),
        ("    elementid = 4", "    elementid = %d" % max(2, int(p["x0"] / p["dx"] / 4))),
        ("    elementid = 155", "    elementid = %d" % (p["n"] - 4)),
        ("  end_time = 8.0e-3", "  end_time = %.6e" % p["t_end"]),
    ]
    for a, b in reps:
        if a not in t:
            sys.exit("模板里找不到：%r（front1d.i 改过？）" % a[:50])
        t = t.replace(a, b, 1)

    # 解析溶质初值里的 V 与 x0 也要跟着变（多行表达式，单独处理）
    old_c = ("expression = 'if(x<5.0e-6, 0.036,\n"
             "                    0.036*(1 + (1-0.6303)/0.6303*exp(-1.26e-3*(x-5.0e-6)/2.52e-9)))'")
    new_c = ("expression = 'if(x<%.6e, 0.036,\n"
             "                    0.036*(1 + (1-0.6303)/0.6303*exp(-%.6e*(x-%.6e)/%.6e)))'"
             % (p["x0"], V_FRONT, p["x0"], D_L))
    if old_c not in t:
        sys.exit("模板里找不到解析初值表达式（front1d.i 改过？）")
    t = t.replace(old_c, new_c, 1)
    return t, p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--s", type=float, required=True, help="W/(D/V)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    txt, p = build(a.s)
    out = a.out or ("case_s%g.i" % a.s)
    io.open(out, "w", encoding="utf-8", newline="").write(txt)
    print(f"s = {a.s:g}")
    print(f"  W=xi   = {p['xi']*1e6:.5f} um      dx = {p['dx']*1e6:.5f} um      "
          f"单元/界面 = {p['xi']/p['dx']:.1f}")
    print(f"  delta_c= {DELTA_C*1e6:.3f} um        V  = {V_FRONT:.4e} m/s")
    print(f"  kappa  = {p['kappa']:.4e}   Wg = {p['Wg']:.4e}   dG = {p['dG']:.4e}   L = {p['L']:.4e}")
    print(f"  域长   = {p['Ldom']*1e6:.1f} um    单元 = {p['n']}      end_time = {p['t_end']:.4e} s")
    print(f"  已写 {out}")


if __name__ == "__main__":
    main()
