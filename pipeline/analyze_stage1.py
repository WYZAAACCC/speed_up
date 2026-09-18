#!/usr/bin/env python3
"""
阶段一结果分析：熔池扫过后，尾部到底有没有外延凝固出晶粒？

=== 为什么需要这个 ===
`liquid_frac` 稳定不变是**正常**的（熔池随激光准稳态移动），
所以它**不能**用来判断凝固有没有发生。必须直接看固相场。

=== 判据 ===
  unique_grains  （GrainTracker 经 FeatureFloodCountAux 输出的晶粒编号）
      >= 0 -> 该单元属于某个晶粒（固相）—— 注意 **0 是合法晶粒 ID**
      <  0 -> 不属于任何晶粒（液相 / 熔池），实测取值为 -1

=== ⚠️ 踩过的坑：Exodus 有多个单元块 ===
  本算例的网格是两个 subdomain（固态 block 0 / 液态 block 1），
  Exodus 里对应 connect1（25313 单元）和 connect2（4787 单元）。
  **只读 connect1 会把熔池整个漏掉**，得出"熔池占比 5%"这种错误结论。
  单元变量也分块存放：vals_elem_var{j}eb{k}。
  所以必须遍历所有块再拼接。

用法：
    python3 analyze_stage1.py <exodus 文件>
"""

import argparse
import sys

import numpy as np
from netCDF4 import Dataset

# 与 stage1_meltpool.i 保持一致（SI 单位）
V_SCAN = 0.6
X_LASER0 = -1.2e-4


def decode_names(ds, key):
    if key not in ds.variables:
        return []
    out = []
    for row in ds.variables[key][:]:
        try:
            s = b"".join(row).decode("utf-8", "replace")
        except Exception:
            s = str(row)
        out.append(s.replace("\x00", "").strip())
    return out


def read_all_blocks(ds, var_index):
    """
    读单元变量 var_index（1-based）的所有块并拼接。
    每个块的连接表和值都单独存放。
    """
    conns, vals, blocks = [], [], []
    k = 1
    while f"connect{k}" in ds.variables:
        conn = np.asarray(ds.variables[f"connect{k}"][:], dtype=np.int64) - 1
        key_a, key_b = f"vals_elem_var{var_index}eb{k}", f"vals_elem_var{var_index}"
        if key_a in ds.variables:
            v = np.asarray(ds.variables[key_a][:])
        elif key_b in ds.variables:
            v = np.asarray(ds.variables[key_b][:])
        else:
            k += 1
            continue
        conns.append(conn)
        vals.append(v)
        blocks.append(k - 1)
        k += 1
    if not conns:
        return None, None, None
    return np.concatenate(conns), np.concatenate(vals, axis=1), blocks


def elem_centers(ds, conn):
    coords = [np.asarray(ds.variables[f"coord{a}"][:], dtype=float)
              for a in "xy" if f"coord{a}" in ds.variables]
    return np.column_stack([c[conn].mean(axis=1) for c in coords])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exodus")
    args = ap.parse_args()

    ds = Dataset(args.exodus, "r")
    times = np.asarray(ds.variables["time_whole"][:], dtype=float)

    ev = decode_names(ds, "name_elem_var")
    if "unique_grains" not in ev:
        sys.exit(f"找不到 unique_grains，可用: {ev}")
    idx = ev.index("unique_grains") + 1

    conn, ug, blocks = read_all_blocks(ds, idx)
    if conn is None:
        sys.exit("读不到单元数据")
    cxy = elem_centers(ds, conn)
    cx, cy = cxy[:, 0], cxy[:, 1]

    print("=" * 70)
    print(f" 文件 {args.exodus}")
    print(f" 单元块 {len(blocks)} 个，合计 {len(cx)} 单元")
    print(f" 时间点 {len(times)}，t = {times[0]:.3g} .. {times[-1]:.3g} s")
    print("=" * 70)

    # 【判据】unique_grains 的取值：-1 = 不属于任何晶粒（液相），
    # >=0 = 属于某晶粒。**晶粒 ID 0 是合法晶粒**，不能用 "> 0"（会把它误判成液相）。
    solid = ug >= 0

    print()
    print("--- 固相占比随时间（全网格）---")
    print(f"{'t (s)':>11} {'固相占比':>10} {'晶粒数':>8}")
    step = max(1, len(times) // 16)
    for k in list(range(0, len(times), step)) + [len(times) - 1]:
        # 必须先取整再 unique —— 晶粒 ID 以浮点存储，
        # 直接 unique 会把同一个 ID 的轻微浮点差异当成不同晶粒，计数翻倍。
        # （extract.py 里也有同样的处理，见 np.rint(grains_ts[it])）
        ids = np.rint(ug[k][solid[k]]).astype(np.int64)
        n = len(np.unique(ids)) if ids.size else 0
        print(f"{times[k]:>11.4g} {solid[k].mean():>10.4f} {n:>8d}")

    s_last = solid[-1]
    t_end = times[-1]
    x_laser = X_LASER0 + V_SCAN * t_end

    print()
    print("--- 末态：沿扫描方向 (x) 的固相占比 ---")
    edges = np.linspace(cx.min(), cx.max(), 23)
    for i in range(len(edges) - 1):
        m = (cx >= edges[i]) & (cx < edges[i + 1])
        if not m.any():
            continue
        xc = (edges[i] + edges[i + 1]) / 2 * 1e6
        f = s_last[m].mean()
        mark = "  <- 激光在此" if abs(xc * 1e-6 - x_laser) < (edges[1] - edges[0]) else ""
        print(f"{xc:>8.0f} um  {f:>6.3f}  {'#' * int(round(f * 40))}{mark}")

    print()
    print(f"末态激光位置 x = {x_laser*1e6:.0f} um "
          f"(域 x ∈ [{cx.min()*1e6:.0f}, {cx.max()*1e6:.0f}] um)")
    print()
    for gap in (40, 60, 80):
        m = cx < x_laser - gap * 1e-6
        if m.any():
            f = s_last[m].mean()
            tag = "尾部已凝固" if f > 0.5 else "**仍是液态**"
            print(f"  激光后方 >{gap:>3d} um : 固相占比 {f:.4f}   <- {tag}")

    print()
    print("--- 初始 vs 末态 ---")
    n0 = len(np.unique(np.rint(ug[0][solid[0]]).astype(np.int64))) if solid[0].any() else 0
    nl = len(np.unique(np.rint(ug[-1][s_last]).astype(np.int64))) if s_last.any() else 0
    print(f"  固相占比 {solid[0].mean():.4f} -> {s_last.mean():.4f}")
    print(f"  晶粒数   {n0} -> {nl}")


if __name__ == "__main__":
    main()
