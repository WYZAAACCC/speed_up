#!/usr/bin/env python3
# =============================================================================
# T9 生成器：三晶粒静态三叉晶界
# =============================================================================
# 审计原文：
#   「2.2 ... 必须测：平面界面、圆晶粒、三叉晶界、移动溶质前沿。」
#   「T9 | 三叉晶界 | 三晶粒静态 | 三叉角误差 ≤ 5°；无伪第三相增长」
#
# 【被测的物理】
#   三条晶界能相等时，三叉晶界处的**力平衡**要求三个夹角都是 **120°**。
#   这是一条纯几何的、与迁移率无关的结论（Herring 关系在三重对称下的特例）。
#   ⇒ 平衡角与 M 无关，只与 γ 有关。所以这个测试**不依赖**任何动力学参数。
#
# 【⚠ 一个漂亮的巧合：Voronoi 的三叉角 = 三角形的内角】
#   三个种子的 Voronoi 图，三条边是三角形三边的**垂直平分线**，
#   交于**外心**。垂直平分线 AB 与 AC 的夹角
#   = 直线 AB 与 AC 的夹角 = 三角形的内角 A。
#   ⇒ **初始三叉角恰好等于种子三角形的三个内角。**
#   这让我们可以**精确控制初始偏离**：选一个远离 120° 的三角形，
#   初始角就是那些角；跑到位后应该收敛到 120/120/120。
#
#   本脚本默认用直角三角形（一个角 90°），初始就有 30° 的偏离。
#
# 【时间尺度】t_r = L²/(M·σ)，L≈10 µm、M=2.87e-7、σ=0.6 ⇒ ≈5.8e-4 s。
#   与圆晶粒算例同量级，所以是跑得动的。
#   **注意**：改 M 不改变平衡角（力平衡与 M 无关），只改变到达平衡的快慢。
#
# 【⚠ 关于"静态性"—— 这一条是实测才搞清楚的，很关键】
#   Herring 的 120° 条件要求晶界**是直的**（没有曲率驱动力）。
#   有界域里的三个任意晶粒**根本没有静态平衡**：
#   它们会粗化、晶界弯曲、三叉点迁移，角度随之漂移。
#
#   实测（构型 "s1"，初始 110/145/105）：
#       t=0        104.8  110.1  145.2
#       t=5.2e-5   108.9  116.9  134.1   ← 朝 120 走
#       t=1.1e-4   107.3  126.0  126.7   ← 最接近
#       t=1.7e-4   105.7  119.2  135.1   ← 开始离开
#       t=7.5e-4   103.3  105.3  151.4   ← 越走越远
#   ⇒ **对非静态构型，"平衡角"这个判据不适用。**
#
#   ⇒ 真正可测的是**等边三角形**构型（三个扇区都是 120°，对称、无驱动力）：
#       * 初始角 = 120/120/120
#       * 模型若无各向异性，角度应**保持** 120
#       * **必须相对网格旋转一个角度**（`eq17` / `eq41`），
#         否则晶界与网格轴平行，各向异性被对称性掩盖、测不出来
#     这测的是**数值各向异性**，正是"三叉角误差 ≤ 5°"这条判据的实际内容。
#
# 用法：
#   python3 make_t9.py --out t9.i [--tri s1|s2|eq0|eq17|eq41] [--nx 60]
# =============================================================================

import argparse
import math
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

HERE_SRC = "/mnt/f/speed_up/pipeline/tests/grain_growth_circle.i"
# Windows 侧跑时用相对路径
import os
if not os.path.exists(HERE_SRC):
    HERE_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "tests", "grain_growth_circle.i")

# --- 三个种子（µm）。外心在原点，方便放进取景框。---
#
# 【⚠ 必须用**锐角**三角形 —— 直角三角形/钝角三角形是退化的】
#   Voronoi 的三叉点 = 种子三角形的**外心**。
#   * 直角三角形的外心落在**斜边上** ⇒ 三叉点退化，
#     三个角会变成 (A, C, 360−B) 这种，实测得到 35°/55°/**270°**（踩过）。
#   * 钝角三角形的外心在三角形**外面**，同样不是我们要的构型。
#   * **锐角三角形**的外心严格在内部，三个扇区都是 180° 以内。
#
# 【初始三叉角 = 180° − 三角形的对应内角】
#   外心 O，顶点 A。射线 O→mid(AB) 平分 ∠AOB = 2C，O→mid(AC) 平分 ∠AOC = 2B。
#   夹在两条射线之间的扇区（含射线 OA）= C + B = 180° − A。
#   ⇒ 三个初始三叉角 = (180−A, 180−B, 180−C)，**加起来 = 360°** ✔
#
# 【取值】三角形内角 70°/35°/75°（都 < 90，锐角 ✔）
#   ⇒ 初始三叉角 110°/145°/105°，与 120° 的偏离 10°/25°/15°。
#   （三个角平均必然是 120°，所以不可能三个都离 120° 很远 ——
#     这是几何约束，不是选得不好。）
TRIANGLES = {
    # 锐角、不等边；外心在原点，R = 9 µm
    # ⚠ **实测发现这个构型没有静态平衡**（见文件头"关于静态性"）：
    #   角度先朝 120° 走，然后随晶粒粗化又离开。保留它作为"非静态"的对照。
    "s1": [(9.0, 0.0), (-7.794, 4.5), (3.078, -8.457)],
    # 更瘦的锐角三角形（内角 50/60/70 ⇒ 三叉角 130/120/110）
    "s2": [(9.0, 0.0), (-4.5, 7.794), (-2.0, -8.775)],
    # **等边三角形**（外心在原点，R = 9 µm）⇒ 初始三叉角恰好 120/120/120。
    #   这就是审计要的"三晶粒静态"构型：三个扇区都是 120°，对称，无驱动力。
    # ⚠ 但要**相对网格旋转一个角度**，否则测不到网格各向异性
    #   （旋转 0° 时晶界与网格轴平行，各向异性被对称性掩盖）。
    "eq0": [(9.0, 0.0), (-4.5, 7.7942286), (-4.5, -7.7942286)],
    "eq17": [(9.0 * math.cos(math.radians(17 + 120 * k)),
              9.0 * math.sin(math.radians(17 + 120 * k))) for k in range(3)],
    "eq41": [(9.0 * math.cos(math.radians(41 + 120 * k)),
              9.0 * math.sin(math.radians(41 + 120 * k))) for k in range(3)],
    # ⚠ 不要试图用"缩小种子半径"来等效放大域 —— **它不改变任何几何**。
    #   三点 Voronoi 的三个胞都是以**外心**为顶点的楔形，
    #   楔形顶角 = 180° − 对应内角，**只取决于三角形的形状与朝向，与半径无关**。
    #   （我一度加了个 R=4.5 的变体，意识到这点后撤掉了。）
    #   ⇒ 想改边界相对距离，**只能改域本身**（见 t9big / t9fine 两个对照）。
}


def tri_angles(P):
    """三角形三个内角（度）。"""
    A, B, C = P

    def ang(O, X, Y):
        v1 = (X[0] - O[0], X[1] - O[1])
        v2 = (Y[0] - O[0], Y[1] - O[1])
        d = v1[0] * v2[0] + v1[1] * v2[1]
        n = math.hypot(*v1) * math.hypot(*v2)
        return math.degrees(math.acos(max(-1, min(1, d / n))))

    return [ang(A, B, C), ang(B, A, C), ang(C, A, B)]


def circumcenter(P):
    A, B, C = P
    ax, ay = A
    bx, by = B
    cx, cy = C
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay)
          + (cx**2 + cy**2) * (ay - by)) / d
    uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx)
          + (cx**2 + cy**2) * (bx - ax)) / d
    return (ux, uy)


def initial_junction_angles(P):
    """真实初始三叉角 = 180° − 三角形内角（顺序按外心发出的射线排）。"""
    return [180.0 - a for a in tri_angles(P)]


IC_BLOCK = """[ICs]
  # 三个种子 -> Voronoi 三晶粒。初始三叉角 = 180° - 三角形内角（见文件头）。
  [PolycrystalICs]
    [PolycrystalColoringIC]
      polycrystal_ic_uo = voronoi
      block = 0
    []
  []
[]
"""

UO_BLOCK = """[UserObjects]
  [voronoi]
    type = PolycrystalVoronoi
    file_name = seeds3.csv
    # ⚠ file_name 时必须显式给染色算法：默认算法会退化，
    #   把所有种子染成同一个颜色（生产输入里踩过，见其注释）。
    coloring_algorithm = bt
    int_width = 2.0e-6
  []
[]
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--tri", choices=sorted(TRIANGLES), default="s1")
    ap.add_argument("--nx", type=int, default=60)
    ap.add_argument("--ny", type=int, default=60)
    ap.add_argument("--half", type=float, default=1.5e-5,
                    help="域的半边长 m（默认 15 µm）")
    ap.add_argument("--t-end", type=float, default=3.0e-3)
    ap.add_argument("--seeds-out", default=None, help="种子 CSV 路径")
    ap.add_argument("--hex-mesh", default=None,
                    help="用六边形网格文件（由 make_hex_mesh.py 生成）替代方形域。"
                         "⚠ 这是 T9 的关键：方形域是 4 重对称，与 120° 要求的 3 重对称"
                         "不兼容，体系必然破掉 3 重（实测三档都落到 ~103/106/150°）。"
                         "正六边形有 6 重对称（含 3 重），才可能与 120° 自洽。")
    ap.add_argument("--seed-scale", type=float, default=1.0,
                    help="种子半径的缩放。⚠ 三角形形状与朝向决定楔角大小，"
                         "**与半径无关**（见 TRIANGLES 里的注释），"
                         "所以缩放种子不改变物理，只是让种子落进域内"
                         "（六边形域半径只有 5 µm，而默认种子在 9 µm）。")
    ap.add_argument("--hex-file-name", default="hex.msh",
                    help="写进 .i 里的网格文件名（相对算例目录）")
    args = ap.parse_args()

    P = TRIANGLES[args.tri]
    ang = tri_angles(P)
    jang = initial_junction_angles(P)
    cc = circumcenter(P)

    t = open(HERE_SRC, encoding="utf-8").read()

    def rep(old, new, cnt=1):
        nonlocal t
        c = t.count(old)
        if c != cnt:
            sys.exit("错误：%r 匹配 %d 次，期望 %d" % (old[:60], c, cnt))
        t = t.replace(old, new)

    # --- 网格 ---
    h = args.half          # 六边形路径不用它，但后面打印要用，先绑定
    if args.hex_mesh:
        # 六边形域：整块替换 [Mesh]，不走 nx/ny 那套改写
        import re as _re2
        m = _re2.search(r"\[Mesh\][\s\S]*?\n\[\]\n", t)
        if not m:
            sys.exit("错误：模板里找不到 [Mesh] 块")
        t = t[:m.start()] + (
            "[Mesh]\n"
            "  [hex]\n"
            "    type = FileMeshGenerator\n"
            "    file = %s\n" % args.hex_file_name +
            "  []\n"
            "[]\n") + t[m.end():]
        print("  网格：六边形（%s）" % args.hex_file_name)
    else:
        rep("  nx = 120", "  nx = %d" % args.nx)
        rep("  ny = 120", "  ny = %d" % args.ny)
        h = args.half
        rep("  xmin = -3.0e-5", "  xmin = %.6e" % (-h,))
        rep("  xmax =  3.0e-5", "  xmax =  %.6e" % (h,))
        rep("  ymin = -3.0e-5", "  ymin = %.6e" % (-h,))
        rep("  ymax =  3.0e-5", "  ymax =  %.6e" % (h,))

    # --- 序参量个数 ---
    rep("  op_num = 2", "  op_num = 3")

    # --- IC：用 Voronoi 替换两个 SmoothCircleIC ---
    i0 = t.index("[ICs]")
    i1 = t.index("\n[]", i0) + len("\n[]\n")
    ic = IC_BLOCK
    if args.hex_mesh:
        # ⚠ GMSH 的 physical id 从 **1** 开始，而 GeneratedMesh 的子域是 **0**。
        #   不换会报「blocks (ids) do not exist on the mesh: 0」。
        ic = ic.replace("block = 0", "block = 1")
    t = t[:i0] + ic + t[i1:]

    # --- 插入 UserObjects（放在 [ICs] 之前）---
    t = t.replace("[ICs]", UO_BLOCK + "[ICs]", 1)

    # --- 自由能要覆盖 gr2 ---
    rep("    coupled_variables = 'gr0 gr1'",
        "    coupled_variables = 'gr0 gr1 gr2'")
    rep("""    expression = 'mu*((gr0^4/4-gr0^2/2)+(gr1^4/4-gr1^2/2)
                   +gamma_asymm*(gr0^2*gr1^2))'""",
        """    expression = 'mu*((gr0^4/4-gr0^2/2)+(gr1^4/4-gr1^2/2)+(gr2^4/4-gr2^2/2)
                   +gamma_asymm*(gr0^2*gr1^2+gr0^2*gr2^2+gr1^2*gr2^2))'""")

    # --- 去掉周期边界 ---
    # ⚠ 这是必须的。`grain_growth_circle.i` 用周期边界（孤立晶粒在无限基体中的等效），
    #   但对三晶粒来说，周期边界会把 3 个种子**复制成晶格**，
    #   产生**很多个**三叉点 —— 分析器会随机找到其中一个
    #   （实测找到 (13.5, 6.0) µm，而不是设计的原点）。
    #   三叉晶界测试要的是**单个**三叉点，所以用自然边界。
    import re as _re
    m = _re.search(r"\[BCs\][\s\S]*?\n\[\]\n", t)
    if m:
        t = t[:m.start()] + t[m.end():]

    # --- 时间 ---
    rep("  end_time = 6.0e-4", "  end_time = %.6e" % args.t_end)

    # --- Exodus 输出密一点，方便看三叉角随时间的演化 ---
    rep("    time_step_interval = 50", "    time_step_interval = 10")

    # --- 加「伪第三相」判据：Ση² 的极值 ---
    # 审计 T9 判据之二：「无伪第三相增长」。
    # 判据：三叉晶界处 Ση² 的理论值是 0.4286（三个 η 各 1/√6.86...，
    # 见 GATE1_PLAN.md），**绝不应超过 1**。超过 1 = 伪影。
    rep("""[AuxVariables]
  [inside]
    order = CONSTANT
    family = MONOMIAL
  []
[]""",
        """[AuxVariables]
  [inside]
    order = CONSTANT
    family = MONOMIAL
  []
  [sum_eta2]
    order = CONSTANT
    family = MONOMIAL
  []
[]""")
    rep("""  [inside]
    type = ParsedAux
    variable = inside
    coupled_variables = 'gr0'
    expression = 'if(gr0>0.5,1,0)'
    execute_on = 'initial timestep_end'
  []
[]""",
        """  [inside]
    type = ParsedAux
    variable = inside
    coupled_variables = 'gr0'
    expression = 'if(gr0>0.5,1,0)'
    execute_on = 'initial timestep_end'
  []
  [sum_eta2]
    type = ParsedAux
    variable = sum_eta2
    coupled_variables = 'gr0 gr1 gr2'
    expression = 'gr0^2+gr1^2+gr2^2'
    execute_on = 'initial timestep_end'
  []
[]""")
    rep("""  [dt]
    type = TimestepSize
  []
[]""",
        """  [dt]
    type = TimestepSize
  []
  # --- T9 判据：无伪第三相 ---
  # ⚠ 名字不能叫 sum_eta2_max —— 模板 grain_growth_circle.i 里已经有一个
  #   同名后处理器（用的是 inside 变量），重名会报 "supplied multiple times"。
  [sumEta2_max]
    type = ElementExtremeValue
    variable = sum_eta2
    value_type = max
    execute_on = 'initial timestep_end'
  []
  [sumEta2_min]
    type = ElementExtremeValue
    variable = sum_eta2
    value_type = min
    execute_on = 'initial timestep_end'
  []
  [gr2_max]
    type = NodalExtremeValue
    variable = gr2
    value_type = max
    execute_on = 'timestep_end'
  []
[]""")

    open(args.out, "w", encoding="utf-8", newline="").write(t)

    # --- 种子文件 ---
    sp = args.seeds_out or (os.path.dirname(os.path.abspath(args.out))
                            + "/seeds3.csv")
    with open(sp, "w", encoding="utf-8") as f:
        f.write("x,y\n")
        for (x, y) in P:
            f.write("%.10g,%.10g\n" % (x * args.seed_scale * 1e-6,
                                       y * args.seed_scale * 1e-6))

    print("写出 %s" % args.out)
    print("  种子 (%s): %s" % (args.tri, ["(%.2f, %.2f)" % p for p in P]))
    print("  外心（= Voronoi 三叉点）= (%.3f, %.3f) µm" % cc)
    print("  三角形内角 = %s   （锐角 ⇒ 外心在内部，构型非退化）"
          % ["%.2f°" % a for a in ang])
    print("  **初始三叉角 = 180° − 三角形内角 = %s**"
          % ["%.2f°" % a for a in jang])
    print("  平衡目标 120° × 3 ⇒ 初始偏离 %s（三个角平均必然是 120°）"
          % ["%.2f°" % (120 - a) for a in jang])
    if args.hex_mesh:
        print("  网格：六边形（%s），t_end=%.3g s" % (args.hex_file_name, args.t_end))
    else:
        print("  网格 %dx%d, 域 ±%.1f µm, dx=%.3f µm, t_end=%.3g s"
              % (args.nx, args.ny, h * 1e6, 2 * h / args.nx * 1e6, args.t_end))
    print("  种子文件 %s" % sp)


if __name__ == "__main__":
    main()
