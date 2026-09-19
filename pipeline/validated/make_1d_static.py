#!/usr/bin/env python3
# =============================================================================
# 1D 静止界面算例生成器（T1 / T2 / T4 / T5 + Phase 1.3 的守恒与化学势平衡）
# =============================================================================
#
# 【为什么是「静止」】
#   审计对 Phase 1.3 的要求原话：
#       「先在 1D 静态相界面上验证守恒和化学势平衡，再验证移动前沿。」
#   静止界面把「传质动力学」从问题里拿掉，只留**热力学平衡**——
#   于是任何偏离都能直接归因到自由能/分配关系，而不是时间步或速度。
#
# 【静界面平衡的解析解（本算例的判据来源）】
#   取 dG = 0（无反驱动力），则 η 不动，只有 c 松弛。平衡条件 μ = ∂F/∂c = 常数：
#       ∂F/∂c = k_c(c−c0) + 2A·c·η² = 常数
#   远端液相 (η=0) 给出常数 = k_c(c_l − c0)，代入并令 c=c_s (η=1)：
#       c_s = c0·k_c/(k_c + 2A)              ⇒  k_eff = k_c/(k_c + 2A)
#   把 k_c=0.9, A=0.264 代入：k_eff = 0.6302521...
#   ⇒ **这就是 T4 的判据**（k_eff 与理论值误差 ≤ 1%），
#     它同时就是「化学势平衡」的检验：算出来的剖面若不满足上式，说明没到平衡。
#
#   ⚠ 注意 k_eff 是**热力学量**，与迁移率 M 无关。
#     这正是 Phase 1.3 的关键验证手段（见下面分层模式）。
#
# 【两种模式】
#   常数模式（--dl 不给）：M = 2.8e-9 常数。复现 tests/make_partition_sweep.py 的基准。
#   分层模式（--dl --ds 给出）：
#        S      = η²                       （单序参量，Ση² = η²）
#        h_gb   = 8(S² − Q) = 8(η⁴ − η⁴) = **恒等于 0**   ← 单 η 没有固固晶界，正确
#        D(η)   = D_L + (D_S − D_L)·η²
#        M      = D(η) / f_cc,   f_cc = k_c + 2A·η² = ∂²F/∂c²（已核对）
#   ⚠ h_gb ≡ 0 是**要的**：固液界面不该有晶界快速通道。
#     （第一版草稿用 h_gb = 4S(1−S)，在界面中点 η=0.5 处给出 1，
#       会把晶界扩散错误地加到固液界面上。见 validated/check_D_layering.py。）
#
# 【分层模式下要验什么】
#   **平衡剖面必须与常数模式逐点相同** —— 因为平衡与 M 无关。
#   若不同，说明分层实现错了（例如 M 的雅可比缺项、或 f_cc 写错）。
#   这是 T6 的「动力学版」补充：T6 只核对了 D 的**定义**，这里核对它的**后果**。
#
# ⚠ M 依赖 η ⇒ `[coupled_res]`（SplitCHWRes）**必须**声明 coupled_variables='eta'，
#   否则 ∂M/∂η 整块不进雅可比 —— 与审计 P0-1 完全同类（JvarMapInterface 静默早退）。
#   本脚本在分层模式下自动打上这个补丁。
#
# 用法：
#   python3 make_1d_static.py --out A.i                          # 常数 M 基准
#   python3 make_1d_static.py --out B.i --dl 2.52e-9 --ds 4.0e-13 # 分层
#   python3 make_1d_static.py --out C.i --dx 0.25e-6             # 换 dx（T5 要求两种 dx）
# =============================================================================

import argparse
import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "tests", "front1d.i")

# --- 与 tests/ 里的基准保持一致（改这里必须同步改注释里的推导）---
SIGMA = 0.6                 # J/m^2
K_C, A_PART, C0 = 0.9, 0.264, 0.036
K_EFF_THEORY = K_C / (K_C + 2.0 * A_PART)      # = 0.6302521008403361
M_CONST = 2.8e-9

D_IFACE_DEFAULT = 2.0e-6    # m，生产界面宽 d = sqrt(2*kappa_op/mu0)
DX_DEFAULT = 0.5e-6         # m，4 单元/界面
LDOM_DEFAULT = 40.0e-6      # m


def double_well(d_iface, sigma=SIGMA):
    """由界面宽 d 与界面能 sigma 反解双势阱的 kappa 与 Wg（保持 sigma 不变）。"""
    kWg = (3.0 * math.sqrt(8.0) * sigma) ** 2
    kappa = math.sqrt(kWg * d_iface ** 2 / 8.0)
    Wg = math.sqrt(kWg / (d_iface ** 2 / 8.0))
    return kappa, Wg


def sub_once(text, old, new, what):
    n = text.count(old)
    if n != 1:
        sys.exit(f"错误：{what} 匹配到 {n} 次，期望 1 次。模板 front1d.i 改过？\n"
                 f"      找的是：{old[:90]!r}")
    return text.replace(old, new, 1)


LAYERED_MATERIAL = """  # ===== 【Phase 1.3】分层溶质迁移率（单序参量：无固固晶界）=====
  #   S = eta^2, Q = eta^4  =>  h_gb = 8(S^2 - Q) = 8(eta^4 - eta^4) = 0
  #   固液界面**不该**有晶界快速通道 —— 这里 h_gb 恒为 0 正是要的。
  [solute_M]
    type = DerivativeParsedMaterial
    property_name = M
    coupled_variables = 'eta'
    constant_names = 'D_L D_S k_c A_part'
    constant_expressions = '@DL@ @DS@ 0.9 0.264'
    expression = '(D_L + (D_S-D_L)*eta^2) / (k_c + 2*A_part*eta^2)'
    derivative_order = 2
  []
"""


def build(args):
    t = open(TEMPLATE, encoding="utf-8").read()
    notes = []

    dx = args.dx
    d = args.d_iface
    ldom = args.ldom
    n = int(round(ldom / dx))
    x0 = ldom * 0.25
    kappa, Wg = double_well(d)

    # --- [Mesh] ---
    t = sub_once(t, "  nx = 160", f"  nx = {n}", "网格单元数")
    t = sub_once(t, "  xmax = 4.0e-5", f"  xmax = {ldom:.6e}", "域长")
    notes.append(f"网格 nx={n}, xmax={ldom:.3e} m, dx={dx:.3e} m "
                 f"({d/dx:.1f} 单元/界面)")

    # --- 界面初值位置与宽度 ---
    t = sub_once(t, "expression = '0.5*(1-tanh((x-5.0e-6)/2.0e-6))'",
                 f"expression = '0.5*(1-tanh((x-{x0:.6e})/{d:.6e}))'",
                 "eta 初值表达式")

    # --- 双势阱 + 溶质常数；dG=0（静止界面）---
    t = sub_once(t, "    constant_expressions = '7.2e6 -3.6e5 0.9 0.036 0.264'",
                 f"    constant_expressions = '{Wg:.6e} 0 0.9 0.036 0.264'",
                 "F 的常数（Wg / dG=0）")
    notes.append(f"双势阱 kappa={kappa:.4e}, Wg={Wg:.4e}, dG=0（静止）")
    notes.append(f"界面能 sigma={SIGMA}（不随 d 变，按 front1d.i 的不变量约定）")

    # --- 溶质初值：精确平衡剖面（T4 的解析解）---
    old_c = ("expression = 'if(x<5.0e-6, 0.036,\n"
             "                    0.036*(1 + (1-0.6303)/0.6303*exp(-1.26e-3*(x-5.0e-6)/2.52e-9)))'")
    new_c = (f"expression = '0.036*0.9/(0.9 + 2*0.264*pow(0.5*(1-tanh((x-{x0:.6e})/{d:.6e})),2))'")
    t = sub_once(t, old_c, new_c, "c 的平衡初值表达式")
    notes.append("c 初值 = 精确平衡剖面 c0*k_c/(k_c+2A*eta^2)")

    # --- 材料：常数 M 或 分层 M ---
    if args.dl is None:
        t = sub_once(t, "    prop_names  = 'L          kappa_op  kappa_c   M'",
                     "    prop_names  = 'L          kappa_op  kappa_c   M'",
                     "材料 prop_names（常数模式，保持原样）")
        t = sub_once(t, "    prop_values = '5.833e-4   3.6e-6    1.125e-11 2.8e-9'",
                     f"    prop_values = '5.833333e-04   {kappa:.6e}    {args.kc:.6e} {M_CONST:g}'",
                     "材料 prop_values")
        notes.append(f"常数迁移率 M = {M_CONST:g}（未分层）")
    else:
        t = sub_once(t, "    prop_names  = 'L          kappa_op  kappa_c   M'",
                     "    prop_names  = 'L          kappa_op  kappa_c'",
                     "材料 prop_names（去掉 M）")
        t = sub_once(t, "    prop_values = '5.833e-4   3.6e-6    1.125e-11 2.8e-9'",
                     f"    prop_values = '5.833333e-04   {kappa:.6e}    {args.kc:.6e}'",
                     "材料 prop_values（去掉 M）")
        mat = (LAYERED_MATERIAL
               .replace("@DL@", f"{args.dl:g}")
               .replace("@DS@", f"{args.ds:g}"))
        # 插在 [F] 之前（那个注释行在模板里唯一），而不是找 "[]\n" —— 后者满文件都是
        anchor = "  # 【唯一的自由能】η 与 c 共用 ⇒ 变分耦合"
        t = sub_once(t, anchor, mat + anchor, "在 [F] 前插入 solute_M")
        # ⚠ M 依赖 eta ⇒ SplitCHWRes 必须声明，否则 ∂M/∂η 静默不进雅可比
        t = sub_once(t, "    variable = w\n    mob_name = M\n",
                     "    variable = w\n    mob_name = M\n"
                     "    # 【必须】M 依赖 eta，不声明则 ∂M/∂η 不进雅可比（同审计 P0-1）\n"
                     "    coupled_variables = 'eta'\n",
                     "[coupled_res] 的 coupled_variables")
        notes.append(f"分层迁移率 D_L={args.dl:g}, D_S={args.ds:g}")
        notes.append("已同步给 [coupled_res] 加 coupled_variables='eta'（同 P0-1）")

    # --- 采样点 ---
    t = sub_once(t, "    elementid = 4", f"    elementid = {max(2, int(x0 / dx / 4))}",
                 "固相取样单元")
    t = sub_once(t, "    elementid = 155", f"    elementid = {n - 4}", "液相取样单元")

    # --- 时间：静止界面只需松弛到平衡 ---
    t = sub_once(t, "  end_time = 8.0e-3", f"  end_time = {args.t_end:g}", "结束时间")

    # --- 让 CSV 记录守恒量（T2）---
    if "total_c" not in t:
        sys.exit("错误：模板里没有 total_c 后处理，T2 无法核对")

    # --- 沿 x 采样完整剖面：Phase 1.3 要「逐点」比较平衡剖面，
    #     只看后处理量（k_eff）不够 —— 剖面对不上而 k_eff 恰好相同是可能的。
    vpp = f"""
[VectorPostprocessors]
  [profile]
    type = LineValueSampler
    variable = 'c eta'
    start_point = '0 0 0'
    end_point = '{ldom:.6e} 0 0'
    num_points = {n + 1}
    sort_by = x
    execute_on = 'initial final'
  []
[]
"""
    t = t.rstrip() + "\n" + vpp

    return t, notes, dict(n=n, dx=dx, d=d, kappa=kappa, Wg=Wg, x0=x0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--kc", type=float, default=1.0e-14,
                    help="kappa_c（默认 1e-14，即收敛值）")
    ap.add_argument("--dx", type=float, default=DX_DEFAULT, help="网格间距 m")
    ap.add_argument("--d-iface", type=float, default=D_IFACE_DEFAULT,
                    help="界面宽 d = sqrt(2*kappa_op/mu0)，m")
    ap.add_argument("--ldom", type=float, default=LDOM_DEFAULT, help="域长 m")
    ap.add_argument("--t-end", type=float, default=2.0e-2, help="结束时间 s")
    ap.add_argument("--dl", type=float, default=None, help="给 D_L 则启用分层模式")
    ap.add_argument("--ds", type=float, default=None, help="D_S（分层模式必给）")
    args = ap.parse_args()

    if (args.dl is None) != (args.ds is None):
        sys.exit("错误：--dl 与 --ds 必须同时给或同时不给")

    txt, notes, p = build(args)
    open(args.out, "w", encoding="utf-8", newline="").write(txt)

    print(f"写出 {args.out}")
    for x in notes:
        print("  - " + x)
    print()
    print(f"  理论 k_eff = k_c/(k_c+2A) = {K_EFF_THEORY:.10f}")
    print(f"  单元数 {p['n']}，界面 {p['d']/p['dx']:.1f} 单元")
    print()
    if args.dl is not None:
        print("  ⚠ 分层模式：平衡剖面应与常数模式**逐点相同**（平衡与 M 无关）。")
        print("     不同 => 分层实现有错。")


if __name__ == "__main__":
    main()
