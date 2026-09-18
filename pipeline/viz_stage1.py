#!/usr/bin/env python3
"""
阶段一可视化：熔池扫过后，尾部凝固出的晶粒是柱状还是等轴？

=== 为什么必须看图 ===
固相占比只能说明"有没有凝固"，说明不了"凝成什么样"。
LPBF 的关键特征是**柱状晶**（沿最大温度梯度方向、即大致垂直于熔池边界生长）。
这个只能从晶粒形貌图上判断。

=== 画什么 ===
  1. unique_grains 的晶粒编号图（每个晶粒一种颜色）
  2. 叠加熔池位置（由激光运动学算出）
  3. 若干时间点并排，看组织如何演化

=== ⚠️ 记得遍历所有单元块 ===
  Exodus 里固态 block 0 和液态 block 1 分开存放（connect1/connect2），
  只读一块会漏掉熔池。见 analyze_stage1.py 的注释。

用法：
    python3 viz_stage1.py <exodus> [--n 6] [--out stage1_viz.png]
"""

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from netCDF4 import Dataset

V_SCAN = 0.6
X_LASER0 = -1.2e-4
T_MID = 1903.0


def decode_names(ds, key):
    if key not in ds.variables:
        return []
    out = []
    for row in ds.variables[key][:]:
        s = b"".join(row).decode("utf-8", "replace")
        out.append(s.replace("\x00", "").strip())
    return out


def read_var_all_blocks(ds, name, kind="elem"):
    """读变量（单元或节点）的所有块并拼接。返回 (conn, values, cx, cy)。"""
    if kind == "elem":
        ev = decode_names(ds, "name_elem_var")
        if name not in ev:
            return None
        j = ev.index(name) + 1
    else:
        nv = decode_names(ds, "name_nod_var")
        if name not in nv:
            return None
        j = nv.index(name) + 1

    conns, vals = [], []
    k = 1
    while f"connect{k}" in ds.variables:
        conns.append(np.asarray(ds.variables[f"connect{k}"][:], dtype=np.int64) - 1)
        pre = "vals_elem_var" if kind == "elem" else "vals_nod_var"
        for key in (f"{pre}{j}eb{k}", f"{pre}{j}"):
            if key in ds.variables:
                vals.append(np.asarray(ds.variables[key][:]))
                break
        k += 1
    if not conns:
        return None
    conn = np.concatenate(conns)
    v = np.concatenate(vals, axis=-1) if kind == "elem" else np.concatenate(vals, axis=-1)
    coords = [np.asarray(ds.variables[f"coord{a}"][:], dtype=float)
              for a in "xy" if f"coord{a}" in ds.variables]
    cc = np.column_stack([c[conn].mean(axis=1) for c in coords])
    return conn, v, cc[:, 0], cc[:, 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exodus")
    ap.add_argument("--n", type=int, default=6, help="画几个时间点")
    ap.add_argument("--out", default="stage1_viz.png")
    args = ap.parse_args()

    ds = Dataset(args.exodus, "r")
    times = np.asarray(ds.variables["time_whole"][:], dtype=float)

    res = read_var_all_blocks(ds, "unique_grains", "elem")
    if res is None:
        raise SystemExit("找不到 unique_grains")
    _, ug, cx, cy = res

    # 液相 = unique_grains < 0（0 是合法晶粒 ID）
    nt = ug.shape[0]
    pick = np.unique(np.linspace(0, nt - 1, min(args.n, nt)).astype(int))

    fig, axes = plt.subplots(len(pick), 1,
                             figsize=(12, 2.0 * len(pick)),
                             sharex=True)
    if len(pick) == 1:
        axes = [axes]

    cmap = plt.get_cmap("tab20")
    for ax, k in zip(axes, pick):
        g = ug[k].astype(float)
        # 液相 = unique_grains < 0（-1 表示不属于任何晶粒）。
        # 注意不能用 "<= 0"：晶粒 ID 0 是合法晶粒，会被误判成液相。
        liq = g < 0
        xl = (X_LASER0 + V_SCAN * times[k]) * 1e6

        # 晶粒：按 ID 上色
        gg = np.where(liq, np.nan, g)
        ax.scatter(cx * 1e6, cy * 1e6, c=gg, cmap=cmap, s=1.2,
                   vmin=1, vmax=20, marker="s", linewidths=0)
        # 液相：灰
        if liq.any():
            ax.scatter(cx[liq] * 1e6, cy[liq] * 1e6, c="0.88", s=1.2,
                       marker="s", linewidths=0)
        ax.axvline(xl, color="r", lw=1.2, ls="--")
        n = len(np.unique(np.rint(g[~liq]).astype(np.int64))) if (~liq).any() else 0
        ax.set_title(f"t = {times[k]*1e3:.3f} ms   laser x = {xl:.0f} um   "
                     f"grains {n}   liquid {liq.mean()*100:.0f}%",
                     fontsize=9)
        ax.set_ylabel("y (um)", fontsize=8)
        ax.set_ylim(cy.min() * 1e6 - 2, cy.max() * 1e6 + 2)
        ax.tick_params(labelsize=7)

    axes[-1].set_xlabel("x (um)   [scan direction ->]", fontsize=9)
    fig.suptitle("LPBF single melt pool: grey = liquid pool, "
                 "colored = grains, red dashed = laser",
                 fontsize=10)
    plt.tight_layout()
    plt.savefig(args.out, dpi=110)
    print(f"图已存: {args.out}")

    # 柱状程度定量：晶粒的 y 向跨度 / x 向跨度
    print()
    print("--- 柱状程度 (每个晶粒的 y跨度 / x跨度，>1 表示沿深度拉长=柱状) ---")
    g_last = ug[-1].astype(float)
    for gid in np.unique(g_last[g_last >= 0]):
        m = g_last == gid
        if m.sum() < 20:
            continue
        sx = cx[m].max() - cx[m].min()
        sy = cy[m].max() - cy[m].min()
        r = sy / sx if sx > 0 else float("inf")
        print(f"  晶粒 {int(gid):>2d}: {m.sum():>5d} 单元  "
              f"x跨度 {sx*1e6:>6.1f} um  y跨度 {sy*1e6:>6.1f} um  "
              f"比 {r:>5.2f}  {'<- 柱状' if r > 1.5 else ''}")


if __name__ == "__main__":
    main()
