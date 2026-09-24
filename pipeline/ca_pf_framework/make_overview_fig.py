# -*- coding: utf-8 -*-
"""总工作图 v2: 修正版面溢出"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.font_manager import FontProperties
import matplotlib.gridspec as gridspec

CJK = "/mnt/c/Windows/Fonts/simhei.ttf"
fp  = FontProperties(fname=CJK, size=10)
fpb = FontProperties(fname=CJK, size=11.5)
fpt = FontProperties(fname=CJK, size=15)
fps = FontProperties(fname=CJK, size=8.5)
SW = "black"
GREEN, YELLOW, RED, ORANGE, BLUE, GREY = "#2e8b57", "#d4a017", "#c0392b", "#e07b39", "#2b6cb0", "#7f8c8d"

fig = plt.figure(figsize=(18.5, 13.0), facecolor="white")
gs = gridspec.GridSpec(3, 2, height_ratios=[2.7, 3.0, 2.9], width_ratios=[1.0, 1.5],
                       hspace=0.30, wspace=0.10)

def box(ax, x, y, w, h, text, color, fs=fps, lw=1.9, alpha=0.15):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.018",
                                linewidth=lw, edgecolor=color, facecolor=color, alpha=alpha))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontproperties=fs, color="black")

def arrow(ax, p, q, color=GREY, lw=1.8):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=16, linewidth=lw, color=color))

# ============================== Panel A ==============================
axA = fig.add_subplot(gs[0, :]); axA.set_xlim(0, 1); axA.set_ylim(0, 1); axA.axis("off")
axA.text(0.005, 0.965, "①  总体路线与当前状态（三个活动窗口 + 事件驱动调度 + 全局材料状态）",
         fontproperties=fpb, color=SW)
labels = [
 ("热层（共享时钟）\nT(x,t) / G / R / 冷却速率\n\n[完成] thermal_layer.py\n11/11 通过\n焓式方程 + 潜热", GREEN),
 ("Window A：滑动窗口 CA\n推进的是【固液界面】\n晶界是涌现的\n产出：冻结 prior-β 骨架\n+ 晶界网络 + 凝固化学\n\n[OK] ca3d.py  21 项 20/1/0\n形核·CET·V(ΔT)查表\n26 邻居捕获·Scheil\n液相输运·滑动窗口", GREEN),
 ("Window B：局部精细 PF\n晶内 α′ / 板条 / 变体\n+ 晶界 α 膜\n（B1 位移型 / B2 扩散型）\n\n[  ] 未开始\n引擎已定：\nMOOSE 生产副本 prod3d", RED),
 ("Window C：Gibbs 面\n界面过剩 Γi 演化\n面内扩散 · 溶质拖曳\n\n[  ] 未开始\n（v1「逐面算子」\n的正确落点）", RED),
 ("神经算子层\n只学 B / C\n不学 A\n（A 是解析的）\n\n[  ] 未开始", GREY),
]
x0, w, gap = 0.008, 0.190, 0.010
for i, (t, c) in enumerate(labels):
    x = x0 + i * (w + gap)
    box(axA, x, 0.575, w, 0.325, t, c)
    if i < len(labels) - 1:
        arrow(axA, (x + w + 0.001, 0.737), (x + w + gap - 0.001, 0.737))
box(axA, 0.008, 0.285, 0.984, 0.145,
    "两级接口（框架 §7.2 的强制项）\n"
    "[OK] Π 投影算子：胞平均 -> 胞内分布，逐胞守恒 1.27e-16，5/5 判据通过\n"
    "[部分] PF <-> LKT 薄界面匹配（P1.1）：进行中 —— 见 ③", ORANGE)
box(axA, 0.008, 0.045, 0.984, 0.185,
    "L0 状态与调度：全局材料状态 S + 混合自动机（7 个模式）　设计已完成，实现未开始　[  ]\n"
    "量化依据：prior-β 骨架在 LPBF 中冻结（单道 1.4 nm / 100 层 2.8 nm）\n"
    "=> Window B 的「固定骨架」假设成立，这使 Window B 可以只在局部窗口里演化", GREY)

# ==================== Panel B ====================
axB = fig.add_subplot(gs[1, 0]); axB.axis("off"); axB.set_xlim(0, 1); axB.set_ylim(0, 1)
axB.text(0.0, 0.985, "②  验证账本：累计 142 项判据", fontproperties=fpb, color=SW, transform=axB.transAxes)
rows = [("数学框架自检", 76, 55, 7, 6, 8), ("热层（潜热）", 11, 11, 0, 0, 0),
        ("三维 CA", 21, 20, 1, 0, 0), ("液相溶质输运", 11, 11, 0, 0, 0),
        ("物理正确性", 15, 14, 1, 0, 0), ("Π 投影算子", 5, 5, 0, 0, 0),
        ("P1.1 界面匹配", 3, 3, 0, 0, 0)]
y = 0.875
for name, tot, p, w_, f_, r_ in rows:
    axB.text(0.015, y, name, fontproperties=fps, va="center")
    xx = 0.40; sc = 0.50 / 76.0
    for cnt, col in ((p, GREEN), (w_, YELLOW), (f_, RED), (r_, GREY)):
        if cnt:
            axB.add_patch(plt.Rectangle((xx, y - 0.030), cnt * sc, 0.060, color=col, alpha=0.85))
            xx += cnt * sc
    axB.text(0.975, y, str(tot), fontproperties=fps, va="center", ha="right")
    y -= 0.108
axB.text(0.015, 0.085, "绿 = PASS　黄 = WARN　红 = FAIL（必须处理）　灰 = RULE（设计禁令）",
         fontproperties=fps, color=GREY)
axB.text(0.015, 0.010, "FAIL 明细：凝固区间参数不自洽（17.9 vs 45 K）/ 潜热不可忽略（18.6 倍）/ 网格欠解析 42 倍",
         fontproperties=fps, color=RED)

# ==================== Panel C ====================
axC = fig.add_subplot(gs[1, 1]); axC.set_xlim(0, 1); axC.set_ylim(0, 1); axC.axis("off")
axC.text(0.0, 0.985, "③  P1.1 关键路径：现在走到哪一步", fontproperties=fpb, color=SW)
steps = [
 ("P1-a\n冻结 φ + 均匀 T\n共存分配系数", "[OK] 通过\nc_s/c_l = 0.63228\nvs k_e 0.6303\n(+0.31%)", GREEN),
 ("抗截留「效应为零」\n的根因（源码+文档）", "[OK] 已钉死\n残差严格正比 dv/dt\n（φ 曾是 AuxVariable\n=> dv/dt 被当成 0）", GREEN),
 ("修好根因后\n抗截留的非零效应", "[OK] 已实现\n1.9% ~ 4.0%\n（修前 ALPHA=0 与 2\n逐位相同）", GREEN),
 ("ALPHA 的可调性", "[OK] 已实现\n固相探针单调\n+8.9%（ALPHA 0 -> 3）", GREEN),
 ("定出 ALPHA* 的数值", "[X] 未完成\n卡在 W/dc = 0.16\n伪影只占 0.2~1%\n=> 参数不可辨识", RED),
]
x0, w, gap = 0.008, 0.186, 0.017
for i, (t1, t2, c) in enumerate(steps):
    x = x0 + i * (w + gap)
    box(axC, x, 0.605, w, 0.225, t1, BLUE, lw=1.5, alpha=0.10)
    box(axC, x, 0.325, w, 0.265, t2, c, lw=1.7)
    if i < len(steps) - 1:
        arrow(axC, (x + w + 0.002, 0.72), (x + w + gap - 0.002, 0.72))
box(axC, 0.008, 0.155, 0.984, 0.135,
    "下一步（不需要用户决策）：把 1D 算例的 W 放大到 200 / 400 nm（W/dc = 1.05 / 2.1），\n"
    "让界面拉伸伪影升到 O(10%) => 判据有分辨力 => 在那个 W 上定出 ALPHA*，再验证它与 W 无关", ORANGE)
box(axC, 0.008, 0.012, 0.984, 0.125,
    "[!] 已查出但尚未确认约定：生产 F_at 取 ALPHA = +2（正值）；我的 1D 对照显示需要【负】前置因子\n"
    "=> 生产可能把它用在了符号错的一侧（但在 W/dc ~ 0.17 的区制里这个错只值 ~0.2%，所以此前没人发现）",
    ORANGE)

# ==================== Panel D ====================
axD = fig.add_subplot(gs[2, :]); axD.set_xlim(0, 1); axD.set_ylim(0, 1); axD.axis("off")
axD.text(0.005, 0.970, "④  本轮查出的问题与状态", fontproperties=fpb, color=SW)
items = [
 ("初始固相区\n被当成过冷液体", "熔池外 353 K 区域按 ΔT≈1558 K 生长　=>　现按热力学约束：与固相邻则外延并入，隔离则自发形核", "已修", GREEN),
 ("IRF 在 ΔT>17.97 K\n外推为常数", "LKT 尖端过冷度饱和值 = 凝固区间（比值 1.004）　=>　改为截断 + 计数，越界 0.45% 已记账", "已修", GREEN),
 ("抗截留 F_at 的 W\n小 2~4 倍", "生产 W = 2 um vs 界面宽 4 / 8 um　=>　生成器默认已改为跟随 WGB", "已修", GREEN),
 ("抗截留核恒为零", "φ 是 AuxVariable => dφ/dt 被当成 0　=>　源码 + 文档钉死；φ 改真变量后效应出现", "已定位", GREEN),
 ("生产 ALPHA = +2\n可能符号错", "MOOSE 核是 +F(grad v/|grad v|)dv/dt；我的对照显示需要负因子", "待确认", ORANGE),
 ("倾斜梯度下\n取向淘汰已修复", "根因=包络支撑律用错(L*max vs L/Sum)+格点路径偏差；修法=周期侧边界+analytic 捕获", "已修", GREEN),
 ("CALPHAD 数据未到", "凝固区间 17.9 K vs 文档 45 K 不自洽　=>　任务书已出，等外部数据", "阻塞", RED),
]
y = 0.845
for t, d, s, col in items:
    box(axD, 0.010, y - 0.045, 0.135, 0.085, t, col, lw=1.4)
    axD.text(0.155, y - 0.002, d, fontproperties=fps, va="center")
    axD.text(0.985, y - 0.002, s, fontproperties=fps, va="center", ha="right", color=col)
    y -= 0.113

fig.suptitle("Ti-6Al-4V LPBF 多尺度组织仿真与神经算子加速 —— 总工作图（2026-09-23）",
             fontproperties=fpt, y=0.985)
plt.savefig("FIG_OVERALL_STATUS.png", dpi=115, bbox_inches="tight", facecolor="white")
print("saved")
