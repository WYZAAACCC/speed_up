#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""画一张「物理正确且精细的晶界溶质仿真」的层级关系图。
绿色=已实现 / 橙色=部分实现 / 红色=未实现"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fm.fontManager.addfont("/mnt/c/Windows/Fonts/msyh.ttc")
plt.rcParams["font.family"] = "Microsoft YaHei"
plt.rcParams["axes.unicode_minus"] = False

OK, PART, NO = "#2e7d32", "#e65100", "#c62828"
BG = {"OK": "#e8f5e9", "PART": "#fff3e0", "NO": "#ffebee"}
COL = {"OK": OK, "PART": PART, "NO": NO}

fig, ax = plt.subplots(figsize=(19.5, 13.2))
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")


def box(x, y, w, h, text, status=None, fs=11, bold=False, fc="white",
        ec="#546e7a", lw=1.6, ha="left"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.35,rounding_size=1.2",
                                linewidth=lw, edgecolor=ec, facecolor=fc, zorder=2))
    if status:
        ax.add_patch(FancyBboxPatch((x, y), 1.4, h, boxstyle="round,pad=0.35,rounding_size=0.6",
                                    linewidth=0, facecolor=COL[status], zorder=3))
    tx = x + 2.4 if status else x + 1.4
    ax.text(tx, y + h / 2, text, fontsize=fs, va="center", ha="left",
            zorder=4, weight="bold" if bold else "normal", linespacing=1.35)


def arrow(p1, p2, label, color="#37474f", ls="-", rad=0.0, fs=9.5, lw=1.6, lx=0, ly=0):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=17,
                                 linewidth=lw, color=color, linestyle=ls, zorder=5,
                                 connectionstyle="arc3,rad=%.2f" % rad))
    mx, my = (p1[0] + p2[0]) / 2 + lx, (p1[1] + p2[1]) / 2 + ly
    ax.text(mx, my, label, fontsize=fs, color=color, ha="center", va="center",
            zorder=6, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.92))


# ---------------- 标题 ----------------
box(24, 91.5, 52, 7,
    "物理正确且精细的晶界溶质仿真：需要什么、已经有什么",
    fs=15, bold=True, fc="#eceff1", ec="#263238", lw=2.2)

# ---------------- 三大支柱 ----------------
heads = [
    (2.0,  29.0, "热力学  —  平衡态是什么", "#1565c0"),
    (35.5, 29.0, "动力学  —  以多快趋近平衡", "#6a1b9a"),
    (69.0, 29.0, "几何 / 拓扑  —  界面在哪、怎么动", "#00695c"),
]
for x, w, t, c in heads:
    box(x, 83.5, w, 5.6, t, fs=12.5, bold=True, fc=c, ec=c)
    ax.texts[-1].set_color("white")

THERMO = [
    ("T1  体相自由能 f(c,T)\n(理想溶液 + 正则项)", "OK",   "  已有 · 物理量纲"),
    ("T2  液固分配 k(T)", "OK", "  已有  k=0.63"),
    ("T3  晶界偏析等温线 Γ_eq(c,T)\n(McLean / Langmuir)", "OK", "  已有 · 1D 验证过"),
    ("T4  偏析焓 / 熵  ΔH_seg、ΔS_seg", "PART", "  ΔH 已反解  ΔS 缺"),
    ("T5  晶界能 σ_GB(Γ,T)\n(Gibbs 吸附 dσ/dμ = −Γ)", "PART", "  框架有 · 未接拓扑"),
    ("T6  β/α 多相 + 三元 Ti-Al-V 热力学", "NO", "没有"),
]
KINET = [
    ("K1  体相扩散 D_L / D_S(T)", "OK", "  已有 · 分层"),
    ("K2  沿晶界扩散 δ·D_GB(T)", "PART", "  能量出 · 参数缺/各向异性未做"),
    ("K3  晶界与体相交换速率 k_att\n(非平衡)", "NO", "没有(我取了局域平衡→=0)"),
    ("K4  溶质拖曳 F_drag(Γ,T,v)", "NO", "没有  ← ★最关键"),
    ("K5  晶界迁移率 L_GB(Δθ,T)", "OK", "  已有"),
    ("K6  界面附着 / 溶质截留", "PART", "  抗截留项已有 · 截留部分"),
]
GEOM = [
    ("G1  晶粒序参量 + 拓扑事件\n(GrainTracker)", "OK", "  已有"),
    ("G2  晶界面的低维表示\n(Γ 挂在面上)", "NO", "生死线"),
    ("G3  面的离散化\n(共形 / 提取 / 嵌入)", "NO", "方案未定"),
    ("G4  3D", "NO", "没有"),
    ("", "OK", ""),
    ("", "OK", ""),
]

for (x, w, _, _), items in zip(heads, [THERMO, KINET, GEOM]):
    for i, (t, st, note) in enumerate(items):
        if not t:
            continue
        y0 = 74.0 - i * 10.4
        box(x, y0, w, 8.2, t + "\n" + note, status=st, fs=10.2, fc=BG[st])

# ---------------- 耦合箭头 ----------------
# C4: T5 -> G1 (偏析改界面能 -> 长大驱动力)
arrow((31.0, 30.4), (69.0, 80.0), "C4", color="#1565c0",
      ls="--", rad=-0.22, fs=9.2, ly=1.2)
# C2: G1 -> K2 (拓扑改扩散几何)
arrow((69.0, 76.0), (64.5, 58.0), "C2", color="#00695c",
      ls="--", rad=0.25, fs=9.2, lx=1.5, ly=1.0)
# C1: K4 -> G1 (拖曳)  ★核心
arrow((64.5, 37.5), (69.0, 72.2), "C1", color="#c62828",
      ls="-", rad=0.30, fs=10.2, lw=2.4, lx=-1.0, ly=-1.0)
# C3: T6/G2 -> 相变耦合
arrow((31.0, 23.0), (69.0, 43.0), "C3", color="#6a1b9a",
      ls="--", rad=-0.18, fs=9.2, ly=-1.4)
# C5 温度贯穿
ax.text(50, 88.5, "C5   温度 T 进入所有 Arrhenius / 温度相关项（贯穿三条支柱）",
        fontsize=9.6, ha="center", va="center", color="#455a64",
        bbox=dict(boxstyle="round,pad=0.4", fc="#eceff1", ec="#90a4ae"))

# ---------------- 图例 ----------------
ax.add_patch(FancyBboxPatch((2, 1.0), 96, 20.5, boxstyle="round,pad=0.5,rounding_size=1.2",
                            linewidth=1.4, edgecolor="#b0bec5", facecolor="#fafafa", zorder=1))
ax.text(3.5, 19.2, "图例 / 读数 / 耦合清单", fontsize=12.5, weight="bold", va="center")
for i, (st, t) in enumerate([("OK", "已实现"), ("PART", "部分实现"), ("NO", "未实现")]):
    ax.add_patch(FancyBboxPatch((5 + i * 22, 15.2), 3.2, 2.6, boxstyle="round,pad=0.3,rounding_size=0.6",
                                linewidth=0, facecolor=COL[st]))
    ax.text(9.2 + i * 22, 16.5, t, fontsize=10.5, va="center")

ax.text(3.5, 12.2, "耦合（跨支柱，是「真实反馈」的落点）", fontsize=10.8, weight="bold", va="center")
coup = [
    ("C1", "溶质 → 拓扑：溶质拖曳（Γ 的反作用）", "未实现", "NO",   "★ 五条通道里最关键；当前 = 0"),
    ("C2", "拓扑 → 溶质：晶界移动改变扩散几何", "部分", "PART", "几何变了但面没建起来"),
    ("C3", "晶界成分 → 相变：α 在 β 晶界形核", "未实现", "NO",   "依赖 T6 三元热力学"),
    ("C4", "偏析 → 界面能 → 长大驱动力", "部分", "PART", "Gibbs 吸附框架有，未接入拓扑"),
    ("C5", "温度 T：贯穿所有 Arrhenius / 温度相关项", "已实现", "OK", "三支柱共用同一个 T 场"),
]
for i, (cid, desc, st, stc, note) in enumerate(coup):
    y = 9.3 - i * 1.85
    ax.text(4.5, y, cid, fontsize=10.2, va="center", weight="bold", color=COL[stc])
    ax.text(7.5, y, desc, fontsize=10.2, va="center")
    ax.text(45.0, y, st, fontsize=10.2, va="center", color=COL[stc])
    ax.text(52.0, y, note, fontsize=9.6, va="center", color="#546e7a")

ax.text(3.5, 0.0, "真障碍只有两个：  ① G2/G3「面在数值上挂在哪」    ② K3/K4「非平衡动力学 + 它带来的刚度」",
        fontsize=11.0, va="center", color="#263238", weight="bold")
plt.tight_layout()
out = "/mnt/f/speed_up/pipeline/gibbs/GB_PHYSICS_MAP.png"
fig.savefig(out, dpi=118, bbox_inches="tight", facecolor="white")
print("saved", out)