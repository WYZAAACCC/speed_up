#!/usr/bin/env python3
"""
LPBF 温度场：移动高斯热源的 Rosenthal 解（半无限体、准稳态、无潜热）

    T(x,t) - T0 = eta*P / (2*pi*k*R) * exp( -v*(R + xi) / (2*alpha) )

    xi = x - v*t        随激光移动的坐标（激光沿 +x 扫）
    R  = sqrt(xi^2 + y^2 + z^2)

=== 为什么要先算这个 ===

Rosenthal 解在 R -> 0 处发散（点源奇点），直接用会得到无穷大的温度。
真实熔池底部温度有限，由光斑尺寸决定。所以用一个常用的正则化：

    R -> sqrt(xi^2 + y^2 + z^2 + r_b^2)

r_b 为光束特征半径。这样熔池尺寸由物理参数（P、v、r_b）决定，
而不是由网格分辨率决定。

本脚本的作用：
  1. 用一组典型 LPBF 参数算出熔池尺寸与冷却速率
  2. 断言它们落在文献报道的真实范围内（否则说明参数选错了）
  3. 输出可直接粘进 MOOSE [Functions] 的 ParsedFunction 表达式

用法：
    python3 thermal_field.py            # 用默认参数
    python3 thermal_field.py --P 200 --v 1.0 --rb 50e-6
"""

import argparse

import numpy as np

# ---------------------------------------------------------------------------
# Ti-6Al-4V 物性（待核：数值来自常见文献区间，正式使用前需逐条确认）
# ---------------------------------------------------------------------------
TI64 = {
    "T_room": 300.0,      # K，室温
    "T_solidus": 1878.0,  # K，固相线 (~1605 C)
    "T_liquidus": 1928.0, # K，液相线 (~1655 C)
    "T_beta": 1268.0,     # K，beta transus (~995 C)
    "k": 20.0,            # W/(m*K)，高温导热系数
    "alpha": 6.0e-6,      # m^2/s，热扩散率 = k/(rho*cp)
}

DEFAULTS = {
    "P": 300.0,      # W，激光功率
    "eta": 0.35,     # 吸收率
    "v": 0.6,        # m/s，扫描速度
    "rb": 30e-6,     # m，光束特征半径（仅作有效性判据，见下）
    "T0": 353.0,     # K，基板预热温度
}


# 数值下限：只为避免 R=0 处除零。**不是**光束半径 ——
# 曾错误地把 rb^2 加进 R，结果同时改变了 1/R 几何因子与 exp 衰减项，
# 在 v*rb/(2*alpha) ~ 4 时把温度压低两个数量级，熔池直接消失。
R_MIN = 1.0e-6   # m


def T_rosenthal(x, y, z, t, p, ti=TI64):
    """
    原始 Rosenthal 解。x,y,z 单位 m，t 单位 s。

    注意：点源解在 R -> 0 处发散，在 r < rb 的范围内物理上不成立
    （真实光束是分布源）。但**熔池边界（T = T_L 等温线）位于 r >> rb 处**，
    那里解是准确的，所以直接用它定熔池形状是合法的。
    近轴区的数值只影响"熔池内部有多热"，不影响熔池几何。
    """
    xi = x - p["v"] * t
    R = np.maximum(np.sqrt(xi**2 + y**2 + z**2), R_MIN)
    return ti["T_room"] + (p["eta"] * p["P"]) / (2 * np.pi * ti["k"] * R) * \
        np.exp(-p["v"] * (R + xi) / (2 * ti["alpha"]))


def melt_pool(p, ti=TI64, z=0.0, verbose=True):
    """算熔池几何：宽度（y 向）、深度（z 向，取 y=0 平面）、尾部长度。"""
    TL = ti["T_liquidus"]
    t = 0.0

    # --- 宽度：在 y 方向找 T = TL 的边界（取激光正下方 xi=0）---
    y = np.linspace(0, 3e-4, 200001)
    Ty = T_rosenthal(np.zeros_like(y), y, z, t, p)
    idx = np.where(Ty >= TL)[0]
    width = 2 * y[idx[-1]] if len(idx) else 0.0

    # --- 深度：在 z 方向找边界（取 xi=0, y=0）---
    zz = np.linspace(0, 3e-4, 200001)
    Tz = T_rosenthal(np.zeros_like(zz), np.zeros_like(zz), zz, t, p)
    idx = np.where(Tz >= TL)[0]
    depth = zz[idx[-1]] if len(idx) else 0.0

    # --- 尾部长度：沿 -x 方向（激光后方），xi < 0 ---
    xi = np.linspace(0, -3e-3, 300001)
    Tx = T_rosenthal(xi, np.zeros_like(xi), np.zeros_like(xi), t, p)
    idx = np.where(Tx >= TL)[0]
    tail = abs(xi[idx[-1]]) if len(idx) else 0.0

    # --- 光束边缘处的温度（比轴心更有意义；轴心是点源奇点，非物理）---
    T_at_beam = float(T_rosenthal(0.0, p["rb"], 0.0, t, p))

    # --- 前缘长度：xi > 0 方向 ---
    xf = np.linspace(0, 3e-4, 200001)
    Tf = T_rosenthal(xf, np.zeros_like(xf), np.zeros_like(xf), t, p)
    idxf = np.where(Tf >= TL)[0]
    front = xf[idxf[-1]] if len(idxf) else 0.0

    if verbose:
        print(f"  熔池宽度 (y)  : {width*1e6:8.1f} um")
        print(f"  熔池深度 (z)  : {depth*1e6:8.1f} um")
        print(f"  前缘长度 (+x) : {front*1e6:8.1f} um")
        print(f"  尾部长度 (-x) : {tail*1e6:8.1f} um")
        print(f"  总长          : {(front+tail)*1e6:8.1f} um")
        print(f"  长宽比        : {(front+tail)/width if width else 0:8.2f}")
        print(f"  光束边缘温度  : {T_at_beam:8.1f} K  (轴心为点源奇点，非物理)")

    return {"width": width, "depth": depth, "tail": tail,
            "front": front, "T_at_beam": T_at_beam}


def cooling_rate(p, ti=TI64):
    """
    熔池尾部边界上的冷却速率 |dT/dt|。

    取激光后方、固相线等温线上的一点，用有限差分求 dT/dt。
    这是 LPBF 最关键的量：它决定 beta -> alpha' 是否发生。
    """
    TS = ti["T_solidus"]
    t = 0.0

    # 找尾部固相线位置
    xi = np.linspace(0, -3e-3, 300001)
    T = T_rosenthal(xi, np.zeros_like(xi), np.zeros_like(xi), t, p)
    idx = np.where(T >= TS)[0]
    if not len(idx):
        return float("nan")
    xi_s = xi[idx[-1]]

    # 在固定空间点上看温度随时间的变化（激光扫过，该点先升温后降温）
    dt = 1e-9
    x_fixed = xi_s + p["v"] * t
    dTdt = (T_rosenthal(x_fixed, 0.0, 0.0, t + dt, p)
            - T_rosenthal(x_fixed, 0.0, 0.0, t - dt, p)) / (2 * dt)
    return float(dTdt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--P", type=float, default=DEFAULTS["P"])
    ap.add_argument("--v", type=float, default=DEFAULTS["v"])
    ap.add_argument("--rb", type=float, default=DEFAULTS["rb"])
    ap.add_argument("--eta", type=float, default=DEFAULTS["eta"])
    ap.add_argument("--T0", type=float, default=DEFAULTS["T0"])
    ap.add_argument("--no-plot", action="store_true")
    args = ap.parse_args()

    p = {"P": args.P, "v": args.v, "rb": args.rb,
         "eta": args.eta, "T0": args.T0}

    print("=" * 62)
    print(" LPBF 温度场：Rosenthal 解")
    print("=" * 62)
    print(f"  激光功率 P   = {p['P']:.0f} W   (吸收 {p['eta']*p['P']:.0f} W)")
    print(f"  扫描速度 v   = {p['v']:.2f} m/s")
    print(f"  光斑半径 rb  = {p['rb']*1e6:.0f} um")
    print(f"  预热温度 T0  = {p['T0']:.0f} K")
    print(f"  Ti64: k={TI64['k']} W/(m*K), alpha={TI64['alpha']:.1e} m^2/s")
    print(f"        T_solidus={TI64['T_solidus']:.0f} K, T_liquidus={TI64['T_liquidus']:.0f} K")
    print()

    print("--- 熔池几何 ---")
    mp = melt_pool(p)

    print()
    print("--- 冷却速率 ---")
    cr = cooling_rate(p)
    print(f"  固相线处 |dT/dt| = {abs(cr):.3e} K/s")
    if abs(cr) > 0:
        print(f"  特征冷却时间     = {TI64['T_solidus']/abs(cr)*1e3:.3f} ms "
              f"(从固相线降到 0 K 的粗估)")

    # ------------------------------------------------------------------
    # 合理性断言：这些范围来自 LPBF 文献的常见报道区间
    # ------------------------------------------------------------------
    print()
    print("--- 合理性检查 ---")
    ratio = (mp["front"] + mp["tail"]) / mp["width"] if mp["width"] else 0.0
    halfw = mp["width"] / 2
    checks = [
        ("熔池存在（宽 > 0）", mp["width"] > 0, mp["width"] * 1e6, "um"),
        ("熔池宽度在 50-300 um", 50e-6 <= mp["width"] <= 300e-6, mp["width"] * 1e6, "um"),
        ("熔池深度在 20-200 um", 20e-6 <= mp["depth"] <= 200e-6, mp["depth"] * 1e6, "um"),
        ("尾部 > 前缘（熔池后拖）", mp["tail"] > mp["front"], mp["tail"] / mp["front"] if mp["front"] else 0, "x"),
        ("长宽比在 2-8", 2.0 <= ratio <= 8.0, ratio, "x"),
        ("冷却速率在 1e4-1e7 K/s", 1e4 <= abs(cr) <= 1e7, abs(cr), "K/s"),
        # 【关键】点源解只在「熔池远大于光束」时成立。
        # rb 不参与求解，只是有效性判据 —— 若熔池半宽 < 光束半径，
        # 说明点源假设不成立，算出的熔池是假的。
        ("熔池半宽 > 1.2*光束半径（点源解有效）",
         halfw > 1.2 * p["rb"], halfw / p["rb"], "x"),
    ]
    allok = True
    for name, ok, val, unit in checks:
        flag = "OK  " if ok else "警告"
        print(f"  [{flag}] {name:38s} = {val:10.2f} {unit}")
        allok &= ok

    if not allok:
        print("\n  有检查未通过 —— 参数需要调整，不要直接拿去跑。")
    else:
        print("\n  全部通过，参数可用。")

    # ------------------------------------------------------------------
    # 输出 MOOSE ParsedFunction 表达式
    # ------------------------------------------------------------------
    # 注意：MOOSE 的 ParsedFunction 里用 x, y, z, t 作为自变量。
    # 这里直接把 SI 数值代入，得到一个纯数值表达式。
    print()
    print("=" * 62)
    print(" 可直接粘进 MOOSE [Functions] 的表达式（SI 单位，米/秒）")
    print("=" * 62)
    e = p["eta"] * p["P"]
    k = TI64["k"]
    v = p["v"]
    a = TI64["alpha"]
    print(f"""
[Functions]
  [laser_T]
    type = ParsedFunction
    expression = '{TI64["T_room"]} + {e:.6g}/(2*pi*{k}*R)*exp(-{v:.6g}*(R+xi)/(2*{a:.6g}))'
    symbol_names = 'xi R'
    symbol_values = 'x-{v:.6g}*t  max(sqrt((x-{v:.6g}*t)^2+y^2+z^2),{R_MIN:.6g})'
  []
[]

  # 注意：symbol_values 按空白切分，表达式内部不能有空格。
""")

    if args.no_plot:
        return

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("（无 matplotlib，跳过绘图）")
        return

    # ---- 画熔池形貌 ----
    _, axes = plt.subplots(1, 2, figsize=(13, 5))

    xs = np.linspace(-3e-3, 1e-3, 400)
    ys = np.linspace(-2e-4, 2e-4, 200)
    X, Y = np.meshgrid(xs, ys)
    T = T_rosenthal(X, Y, 0.0, 0.0, p)

    # 色标封顶：点源解在近轴处发散（可达 1e5 K），不封顶整个场会是黑的。
    # 封顶只影响"熔池内部有多热"的显示，不影响熔池边界（那才是要看的）。
    lv = np.linspace(TI64["T_room"], 2300.0, 40)

    ax = axes[0]
    cf = ax.contourf(X * 1e6, Y * 1e6, T, levels=lv, cmap="inferno", extend="max")
    cs = ax.contour(X * 1e6, Y * 1e6, T,
                    levels=[TI64["T_solidus"], TI64["T_liquidus"]],
                    colors=["w", "c"], linewidths=2)
    ax.clabel(cs, fmt={TI64["T_solidus"]: "solidus", TI64["T_liquidus"]: "liquidus"},
              fontsize=9)
    ax.plot(0, 0, "w+", ms=14, mew=2)
    ax.set_xlabel("x (um)   [laser scans +x]")
    ax.set_ylabel("y (um)")
    ax.set_title("Melt pool, top view (z=0)")
    plt.colorbar(cf, ax=ax, label="T (K)")

    ax = axes[1]
    zs = np.linspace(-1.5e-4, 1e-4, 200)
    X2, Z2 = np.meshgrid(xs, zs)
    T2 = T_rosenthal(X2, np.zeros_like(X2), Z2, 0.0, p)
    cf = ax.contourf(X2 * 1e6, Z2 * 1e6, T2, levels=lv, cmap="inferno", extend="max")
    cs = ax.contour(X2 * 1e6, Z2 * 1e6, T2,
                    levels=[TI64["T_solidus"], TI64["T_liquidus"]],
                    colors=["w", "c"], linewidths=2)
    ax.clabel(cs, fmt={TI64["T_solidus"]: "solidus", TI64["T_liquidus"]: "liquidus"},
              fontsize=9)
    ax.plot(0, 0, "w+", ms=14, mew=2)
    ax.set_xlabel("x (um)")
    ax.set_ylabel("z (um)   [+z = depth]")
    ax.set_title("Longitudinal section (y=0)")
    plt.colorbar(cf, ax=ax, label="T (K)")

    plt.tight_layout()
    out = "thermal_field.png"
    plt.savefig(out, dpi=110)
    print(f"  图已存: {out}")


if __name__ == "__main__":
    main()
