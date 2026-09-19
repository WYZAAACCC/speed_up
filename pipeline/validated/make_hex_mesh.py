#!/usr/bin/env python3
"""
生成一个**正六边形**网格（GMSH v2 ASCII），供 T9 三叉晶界用。

## 为什么需要它（T9 的病灶）

审计 T9 判据：「三叉角误差 ≤ 5°」。而 120°（Herring 力平衡）要求
**域与网格都与 3 重对称兼容**。现有的 T9 算例用**有界方形域** ——
4 重对称与 3 重不兼容，体系必然破掉 3 重，落到一个由域/网格 4 重对称
决定的平衡态（实测三档都收敛到 ~103/106/150°，与 120° 差 20~30°）。

**正六边形有 6 重对称（含 3 重）**，所以「三条晶界从中心成 120° 射出、
指向交替的三个顶点」这个构型在对称性上是自洽的。

## 为什么手写 GMSH

MOOSE 的 `GeneratedMesh` 只能造矩形；`TransformGenerator` 只能平移/旋转/缩放。
`PhaseFieldApp` 里也没有多边形生成器。而 `FileMesh` **支持 GMSH**
（`--dump-search FileMesh` 明确要求 GMSH 要给 `dim`）。
所以直接写一个 GMSH v2 ASCII 文件最省事、最可控。

## 网格构造

- 正六边形，外接圆半径 R，中心在原点，顶点 `V_i = R·(cos60i°, sin60i°)`
- 分成 **3 个菱形**：`(C,V0,V1,V2)`、`(C,V2,V3,V4)`、`(C,V4,V5,V0)`
- 每个菱形用**双线性映射**铺 N×N 个四边形
  （参数化 `P(s,t) = (1-s)(1-t)C + s(1-t)A + st·D + (1-s)t·B`，
    取 `A=V_2k, D=V_2k+1, B=V_2k+2`，四条边正好是 C–A、A–D、D–B、B–C）
- 节点按**坐标去重**，所以三个菱形共享的辐条边自动合并
- 外边界 6 条边各自一个 physical group（`side0`…`side5`），供周期边界或自由边界使用

## 用法

    python3 make_hex_mesh.py --out hex.msh --n 24 --r 5e-6
"""

import argparse
import math


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=24, help="每个菱形每边的单元数")
    ap.add_argument("--r", type=float, default=5e-6, help="外接圆半径（米）")
    a = ap.parse_args()

    N, R = a.n, a.r
    V = [(R * math.cos(math.radians(60 * i)), R * math.sin(math.radians(60 * i)))
         for i in range(6)]
    C = (0.0, 0.0)

    nodes = {}          # 坐标(去重键) -> id
    coords = []         # id -> (x,y)

    def nid(p):
        k = (round(p[0], 14), round(p[1], 14))
        if k not in nodes:
            nodes[k] = len(coords) + 1     # GMSH 从 1 开始
            coords.append(k)
        return nodes[k]

    quads = []          # (n1,n2,n3,n4)
    edges = {}          # 边界名 -> [(n1,n2), ...]

    for k in range(3):
        A, D, B = V[(2 * k) % 6], V[(2 * k + 1) % 6], V[(2 * k + 2) % 6]
        grid = [[nid(((1 - s) * (1 - t) * C[0] + s * (1 - t) * A[0] + s * t * D[0] + (1 - s) * t * B[0],
                      (1 - s) * (1 - t) * C[1] + s * (1 - t) * A[1] + s * t * D[1] + (1 - s) * t * B[1]))
                 for j in range(N + 1) for s, t in [(i / N, j / N)]]
                for i in range(N + 1)]
        for i in range(N):
            for j in range(N):
                quads.append((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
        # 外边界：这个菱形贡献两条六边形边。
        # ⚠ 参数化的四条边是 C–A、A–D、D–B、B–C —— 其中 **C–A 与 B–C 是辐条**
        #   （内部边，两个菱形共享），**A–D 与 D–B 才是外边**。
        #   第一版把 `grid[i][0]`（= C–A，辐条）当成了外边，结果 side0 拿到 16 段
        #   （两个菱形各贡献 8 段）、side1 只有 8 段 —— 总数对但分配错。
        #   正确对应：A–D = V_2k → V_2k+1 = `grid[N][i]`；D–B = V_2k+1 → V_2k+2 = `grid[i][N]`。
        for name, get in ((f"side{(2*k) % 6}", lambda i: (grid[N][i], grid[N][i + 1])),
                          (f"side{(2*k+1) % 6}", lambda i: (grid[i][N], grid[i + 1][N]))):
            edges.setdefault(name, []).extend(get(i) for i in range(N))

    # --- 一致性自检 ---
    assert len(edges) == 6, f"外边界应该有 6 条，得到 {len(edges)}"
    for name, es in edges.items():
        assert len(es) == N, f"{name} 有 {len(es)} 段，期望 {N}"

    # --- 写 GMSH v2 ASCII ---
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("$MeshFormat\n2.2 0 8\n$EndMeshFormat\n")
        f.write("$PhysicalNames\n%d\n" % len(edges))
        for idx, name in enumerate(sorted(edges), start=1):
            f.write('1 %d "%s"\n' % (idx, name))
        f.write("$EndPhysicalNames\n")

        f.write("$Nodes\n%d\n" % len(coords))
        for i, (x, y) in enumerate(coords, start=1):
            f.write("%d %.16g %.16g 0\n" % (i, x, y))
        f.write("$EndNodes\n")

        eid = 0
        lines = []
        for name in sorted(edges):
            for (n1, n2) in edges[name]:
                eid += 1
                lines.append("%d 1 2 %d 1 %d %d\n" % (eid, sorted(edges).index(name) + 1, n1, n2))
        nline = eid
        for q in quads:
            eid += 1
            lines.append("%d 3 0 %d %d %d %d\n" % (eid, q[0], q[1], q[2], q[3]))
        f.write("$Elements\n%d\n" % len(lines))
        f.writelines(lines)
        f.write("$EndElements\n")

    print(f"写入 {a.out}")
    print(f"  节点 {len(coords)}，单元 {len(quads)} 四边形 + {nline} 边界线")
    print(f"  外接圆半径 R = {R:g} m，六边形边长 = R，面积 = {3*math.sqrt(3)/2*R*R:.6g} m²")
    print(f"  边界名：{', '.join(sorted(edges))}")
    print()
    print("周期边界的配对（对面的两条边）：")
    print("  side0 <-> side3   side1 <-> side4   side2 <-> side5")


if __name__ == "__main__":
    main()
