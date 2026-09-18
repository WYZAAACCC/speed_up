#!/usr/bin/env python3
"""
Phase 0a 分析脚本：溶质总量守恒性 + 晶粒消失事件

这是整个课题的第一个关键实验。要回答的问题：
  1. 浓度场 c 在 GrainTracker 重映射（swapSolutionValues）之后还正确吗？
  2. 每次晶粒消失，溶质总量跳变多少？
  3. 跳变随步长减小是收敛的（数值问题），还是不收敛的（结构性问题）？

输入：MOOSE 输出的 CSV（含 postprocessor 列）
输出：
  - 控制台摘要（每次事件的跳变量）
  - phase0a_mass.png（上：溶质总量 vs 时间；下：晶粒数 vs 时间）

用法：
  python3 analyze.py <结果目录>            # 默认读该目录下的 *.csv
  python3 analyze.py <结果目录> --col total_solute --grain-col ngrains
"""

import argparse
import glob
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_csv(run_dir):
    """读 MOOSE 输出的 CSV。可能按处理器分片，也可能只有一个。"""
    files = sorted(glob.glob(os.path.join(run_dir, "*.csv")))
    # 排除 MOOSE 自带的几个非结果文件
    files = [f for f in files if not os.path.basename(f).startswith(("_", "perf"))]
    if not files:
        sys.exit(f"错误：在 {run_dir} 下没找到 CSV 文件")

    frames = []
    for f in files:
        try:
            df = pd.read_csv(f)
        except Exception as e:
            print(f"  跳过 {os.path.basename(f)}: {e}")
            continue
        if "time" in df.columns:
            frames.append(df)

    if not frames:
        sys.exit("错误：没有含 time 列的 CSV")

    # 多片的话按时间拼接去重
    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values("time").drop_duplicates(subset="time", keep="first")
    return df.reset_index(drop=True)


def pick_column(df, candidates, what):
    """从候选列名里挑一个存在的。找不到就报错并列出所有可用列。"""
    for c in candidates:
        if c in df.columns:
            return c
    print(f"错误：找不到{what}列。尝试过: {candidates}")
    print(f"CSV 实际可用的列：{list(df.columns)}")
    sys.exit(1)


def detect_events(df, grain_col):
    """检测晶粒消失事件：晶粒数下降的时刻。"""
    n = df[grain_col].values.astype(float)
    t = df["time"].values.astype(float)
    events = []
    for i in range(1, len(n)):
        if n[i] < n[i - 1] - 1e-9:
            events.append({
                "index": i,
                "time": t[i],
                "n_before": n[i - 1],
                "n_after": n[i],
                "n_lost": n[i - 1] - n[i],
            })
    return events


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", nargs="?", default=".")
    ap.add_argument("--col", default=None, help="溶质总量列名（默认自动识别）")
    ap.add_argument("--grain-col", default=None, help="晶粒数列名（默认自动识别）")
    ap.add_argument("--out", default="phase0a_mass.png")
    args = ap.parse_args()

    df = load_csv(args.run_dir)
    print(f"读入 {len(df)} 行，时间范围 {df['time'].min():.4g} → {df['time'].max():.4g}")

    mass_col = args.col or pick_column(
        df,
        ["total_solute", "solute_total", "c_total", "total_c",
         "mass", "total_mass", "ElementIntegralVariable_c"],
        "溶质总量",
    )
    # 晶粒数优先用 grain_tracker 列：
    # GrainTracker 本身作为 Postprocessor 时直接输出晶粒数，最可靠。
    # 自定义的 FeatureFloodCount 后处理器容易配错阈值，只作后备。
    grain_col = args.grain_col or pick_column(
        df,
        ["grain_tracker", "ngrains", "grain_count", "num_grains", "grains"],
        "晶粒数",
    )

    t = df["time"].values
    M = df[mass_col].values.astype(float)
    n = df[grain_col].values.astype(float)

    M0 = M[0]
    drift = (M - M0) / abs(M0) if M0 != 0 else M - M0

    events = detect_events(df, grain_col)

    # ---- 控制台摘要 ----
    print()
    print("=" * 68)
    print(f"溶质总量：初始 {M0:.10g}，最终 {M[-1]:.10g}")
    print(f"总漂移  ：{M[-1] - M0:+.6e}  （相对 {drift[-1]:+.3e}）")
    print(f"最大漂移：{drift[np.argmax(np.abs(drift))]:+.3e}  @ t={t[np.argmax(np.abs(drift))]:.4g}")
    print("=" * 68)
    print(f"晶粒消失事件：{len(events)} 次")
    print()

    if events:
        print(f"{'#':>4} {'时间':>12} {'晶粒数':>10} {'消失':>6} {'该步ΔM':>16} {'相对跳变':>12}")
        print("-" * 68)
        for k, e in enumerate(events, 1):
            i = e["index"]
            dM = M[i] - M[i - 1]
            rel = dM / abs(M0) if M0 != 0 else dM
            print(f"{k:>4} {e['time']:>12.5g} {e['n_before']:>4.0f}"
                  f"→{e['n_after']:<4.0f} {e['n_lost']:>5.0f} {dM:>+16.6e} {rel:>+12.3e}")
        print("-" * 68)

        jumps = np.array([M[e["index"]] - M[e["index"] - 1] for e in events])
        print(f"跳变统计：均值 {jumps.mean():+.3e}，"
              f"绝对值最大 {np.abs(jumps).max():.3e}，"
              f"RMS {np.sqrt((jumps ** 2).mean()):.3e}")
        print()
        print("解读：")
        print("  · 若跳变 ~1e-15 量级  → 现有机制已经守恒，问题不存在（要换方向）")
        print("  · 若跳变显著且随步长减小而收敛 → 数值问题，可通过控制步长解决")
        print("  · 若跳变显著且不随步长收敛   → 结构性问题，正是本课题要解决的")
    else:
        print("没有检测到晶粒消失事件。")
        print("提示：把仿真时间加长，或增加初始晶粒数，让晶粒真正开始消失。")

    # ---- 画图 ----
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10, 7), sharex=True,
        gridspec_kw={"height_ratios": [2, 1]},
    )

    ax1.plot(t, drift, lw=1.6, color="#0A6767")
    if events:
        ax1.scatter([e["time"] for e in events],
                    [drift[e["index"]] for e in events],
                    s=26, color="#982C2C", zorder=5,
                    label=f"晶粒消失（{len(events)} 次）")
        ax1.legend(loc="best", frameon=False)
    ax1.axhline(0, color="gray", lw=0.8, ls="--")
    ax1.set_ylabel("溶质总量相对漂移  $(M-M_0)/M_0$")
    ax1.set_title("Phase 0a：晶粒消失时溶质是否守恒？", fontsize=13, pad=12)
    ax1.grid(alpha=0.25)
    ax1.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))

    ax2.plot(t, n, lw=1.6, color="#84520F")
    ax2.set_ylabel("晶粒数")
    ax2.set_xlabel("时间")
    ax2.grid(alpha=0.25)

    fig.tight_layout()
    out = os.path.join(args.run_dir, args.out)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"\n图已保存：{out}")


if __name__ == "__main__":
    main()
