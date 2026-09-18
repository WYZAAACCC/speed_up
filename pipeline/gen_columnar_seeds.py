#!/usr/bin/env python3
"""
生成柱状晶种子文件，供 PolycrystalVoronoi 的 file_name 使用。

=== 为什么要柱状基体 ===
真实 LPBF 的基体**不是等轴多晶**，而是上一道/上一层留下的**柱状晶**。
新熔池是外延生长在这些柱状晶上的 —— 它们本来就又长又取向一致，
所以能继续向熔池内延伸。给等轴 Voronoi 基体，再怎么外延也长不出柱状。

=== Voronoi 怎么得到柱状 ===
  晶粒形状 = 种子的 Voronoi 胞。
  想让胞在 y 方向拉长，就要让**同列内没有别的种子**（y 方向无邻居），
  同时 x 方向邻居靠近。
  所以：每列放 1 个种子，列间距 = 目标晶粒宽度。

=== 文件格式 ===
  MooseUtils::DelimitedFileReader 读的带表头分隔文件：
      第 1 行表头，之后每行一个种子
      列: x, y[, z]
（源码见 modules/phase_field/src/userobjects/PolycrystalVoronoi.C 的
 precomputeGrainStructure：data[0]=x, data[1]=y, data[2]=z 可选）

用法：
    python3 gen_columnar_seeds.py [--out seeds.csv] [--width 40] [--depth 150]
"""

import argparse

import numpy as np

# 与 stage1_meltpool.i 的域保持一致（SI，米）
XMIN, XMAX = -2.8e-4, 1.5e-4
YMIN, YMAX = 0.0, 1.5e-4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="columnar_seeds.csv")
    ap.add_argument("--width", type=float, default=40.0,
                    help="目标柱状晶宽度 (um)")
    ap.add_argument("--depth", type=float, default=150.0,
                    help="域深 (um)，仅用于校验")
    ap.add_argument("--per-column", type=int, default=1,
                    help="每列放几个种子。1 = 贯穿全深的柱状晶；"
                         ">1 会在柱内引入横向晶界（真实 LPBF 因逐层重熔也有）")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    w = args.width * 1e-6
    n_col = int(round((XMAX - XMIN) / w))

    rows = []
    for i in range(n_col):
        xc = XMIN + w * (i + 0.5)
        if args.per_column == 1:
            ys = [YMIN + (YMAX - YMIN) * 0.5]
        else:
            # 在深度方向随机撒点，留出边距避免贴边
            pad = (YMAX - YMIN) * 0.15
            ys = rng.uniform(YMIN + pad, YMAX - pad, args.per_column)
            ys.sort()
        for yc in ys:
            # x 上加一点抖动，避免完全规则的栅格
            jitter = rng.uniform(-0.15, 0.15) * w
            rows.append((xc + jitter, yc))

    with open(args.out, "w") as f:
        f.write("x,y\n")
        for x, y in rows:
            f.write(f"{x:.10g},{y:.10g}\n")

    print(f"写入 {args.out}")
    print(f"  列数 {n_col}，每列 {args.per_column} 个种子，"
          f"共 {len(rows)} 个晶粒")
    print(f"  目标晶粒宽度 {args.width:.0f} um，域深 {args.depth:.0f} um")
    if args.per_column == 1:
        print(f"  -> 预期长宽比 ~{args.depth/args.width:.1f}（柱状）")


if __name__ == "__main__":
    main()
