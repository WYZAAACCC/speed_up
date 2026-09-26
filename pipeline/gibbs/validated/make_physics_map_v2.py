#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「物理正确且精细的晶界溶质仿真」层级图 —— 2026-09-21 状态版。

与 2026-09-20 版的区别（全部为本 session 实测）：
  · G2/G3「面在数值上挂在哪」这条生死线 已破（3D 低维块 + mortar 跑通）
  · K3「面↔体相交换」从"没有"变成 已有并在 3D 上工作（kex 的静默 bug 已修）
  · G4「3D」从"没有"变成 已有（3D 生产副本跑起来）
  · 新增两块：本轮进展 / 仍未解决（尤其 S9 棋盘振荡、G5 面跟随 η）
颜色：绿=已实现 / 橙=部分 / 红=未实现
⚠ 本文件里不要用 Markdown 的 ** 强调（matplotlib 会原样画出来）；
   微软雅黑缺的码位统一过 _SUBS 替换。
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch

for cand in ("/mnt/c/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyh.ttc"):
    if os.path.exists(cand):
        fm.fontManager.addfont(cand)
        break
plt.rcParams["font.family"] = "Microsoft YaHei"
plt.rcParams["axes.unicode_minus"] = False

# 微软雅黑缺这些码位（实测会渲染成空框）
_SUBS = {"⇒": "→", "↔": "→", "⚠": "※", "∇_s": "grad_s", "∇": "grad",
         "≪": "远小于", "≤": "<=", "≥": ">="}


def fx(s):
    for k, v in _SUBS.items():
        s = s.replace(k, v)
    return s


OK, PART, NO = "#2e7d32", "#e65100", "#c62828"
BG = {"OK": "#e8f5e9", "PART": "#fff3e0", "NO": "#ffebee"}
COL = {"OK": OK, "PART": PART, "NO": NO}

fig, ax = plt.subplots(figsize=(20.0, 14.0))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")
fig.subplots_adjust(left=0.004, right=0.996, top=0.996, bottom=0.004)


def box(x, y, w, h, text, status=None, fs=10.0, bold=False, fc="white",
        ec="#546e7a", lw=1.6):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.3,rounding_size=1.0",
                                linewidth=lw, edgecolor=ec, facecolor=fc, zorder=2))
    if status:
        ax.add_patch(FancyBboxPatch((x, y), 0.9, h,
                                    boxstyle="round,pad=0.2,rounding_size=0.5",
                                    linewidth=0, facecolor=COL[status], zorder=3))
    tx = x + 1.9 if status else x + 1.3
    ax.text(tx, y + h / 2, fx(text), fontsize=fs, va="center", ha="left", zorder=4,
            weight="bold" if bold else "normal", linespacing=1.30)


# ============================== 标题 ==============================
box(17.0, 93.0, 66.0, 6.4,
    "物理正确且精细的晶界溶质仿真：需要什么 · 已经有什么      （状态：2026-09-21）",
    fs=14.0, bold=True, fc="#eceff1", ec="#263238", lw=2.2)

# ============================== 三大支柱 ==============================
heads = [
    (1.8, 31.6, "热力学  —  平衡态是什么", "#1565c0"),
    (34.2, 31.6, "动力学  —  以多快趋近平衡", "#6a1b9a"),
    (66.6, 31.6, "几何 / 拓扑  —  界面在哪、怎么动", "#00695c"),
]
for x, w, t, c in heads:
    box(x, 86.8, w, 4.6, t, fs=12.0, bold=True, fc=c, ec=c)
    ax.texts[-1].set_color("white")

THERMO = [
    ("T1  体相自由能 f(c,T)", "OK", "理想溶液(物理量纲) + 液固分配\n带 T 依赖（生产没有 T 依赖）"),
    ("T2  液固分配 k(T)", "OK", "k = 0.63\nLee 2025 / PanTi CALPHAD"),
    ("T3  晶界偏析等温线 Γ_eq(c,T)", "OK", "McLean 等温线 · 3D 面上跑通\nGam→c，弛豫时标对上"),
    ("T4  偏析焓 / 熵  ΔH_seg、ΔS_seg", "PART", "ΔH = −11.93 kJ/mol 已从锚点反解\nΔS 缺 → 设 0（显式记账）"),
    ("T5  晶界能 σ_GB(Γ,T)  吸附 dσ/dμ = −Γ", "PART", "框架有\n未接回拓扑（C4 仍未通）"),
    ("T6  β/α 多相 + 三元 Ti-Al-V 热力学", "NO", "没有\nC3（相变）依赖它"),
]
KINET = [
    ("K1  体相扩散 D_L / D_S(T)", "OK", "已有 · 分层\nM = D_eff/f_cc 精确保证（审计 P0-4 已消）"),
    ("K2  沿晶界的面内扩散 δ·D_GB(T)", "OK", "已实现：MatDiffusion(DGBeff)\n机制验证：阶跃初值铺平到均值（A/B 干净）"),
    ("K3  面 ↔ 体相 交换速率 k_att（非平衡）", "OK", "k_att = 1e6\n本 session 修好两个静默 bug 并 3D 跑通"),
    ("K4  溶质拖曳 F_drag(Γ,T,v)", "PART", "机制已落地：L_eff = L/(1+β·A_s·Γ_GB·h_gb)\n⚠ 系数 β 无文献值 ⇒ 默认关，待你定"),
    ("K5  晶界迁移率 L_GB(Δθ,T)", "OK", "已有（Arrhenius）\n各向异性 2a/2b 未接"),
    ("K6  界面附着 / 溶质截留", "PART", "抗截留项已有（ALPHA=2）\n截留部分标定（残差 ≤6.6%）"),
]
GEOM = [
    ("G1  晶粒序参量 + 拓扑事件(GrainTracker)", "OK", "已有：8 序参量、Landau 熔化开关\n柱状晶种子（与生产同源）"),
    ("G2  晶界面 = 真正的低维面，Γ 挂在面上", "OK", "生死线已破：低维块 + mortar\n每条晶界一个独立 Γ（逐面算子的「面」）"),
    ("G3  面的离散化（共形/提取/嵌入）", "OK", "已实现：两侧各一个低维块 + mortar\n※ AMR + mortar 是坏的（见下方进展）"),
    ("G4  3D", "OK", "已有：3D 生产副本\n5247 单元、~20 s/步、5 步全收敛"),
    ("G5  面跟随 η 场移动", "NO", "面还钉在网格面上\n↑ 下一个最关键的工程（缺口③）"),
    ("G6  拓扑事件处 Γ 的守恒重映射", "NO", "晶粒合并 / 消失时面块怎么办\nP1 的核心选题"),
]

for (x, w, _, _), items in zip(heads, [THERMO, KINET, GEOM]):
    for i, (t, st, note) in enumerate(items):
        y0 = 76.6 - i * 9.4
        box(x, y0, w, 8.4, t + "\n" + note, status=st, fs=9.2, fc=BG[st])

# ============================== 底部左：耦合清单 ==============================
ax.add_patch(FancyBboxPatch((1.8, 15.0), 96.4, 13.4,
                            boxstyle="round,pad=0.4,rounding_size=1.0",
                            linewidth=1.4, edgecolor="#b0bec5", facecolor="#fafafa", zorder=1))
ax.text(3.2, 27.4, "耦合（跨支柱 —— 「真实反馈」的落点，也是逐面算子的接口）",
        fontsize=11.0, weight="bold", va="center")
coup = [
    ("C1", "溶质 → 拓扑：溶质拖曳（Γ 的反作用）", "未实现", "NO", "★ 最关键；当前 = 0（依赖 K4）"),
    ("C2", "拓扑 → 溶质：面跟随 η（晶界移动改变输运几何）", "未实现", "NO", "面已建起来，但不跟随（G5）"),
    ("C3", "晶界成分 → 相变：α 在 β 晶界形核", "未实现", "NO", "依赖 T6 三元热力学"),
    ("C4", "偏析 → 界面能 → 长大驱动力", "部分", "PART", "Gibbs 吸附框架有，未接入拓扑（T5）"),
    ("C5", "温度 T 贯穿所有 Arrhenius / 温度相关项", "已实现", "OK", "三支柱共用同一个 T 场"),
]
for i, (cid, desc, st, stc, note) in enumerate(coup):
    y = 25.2 - i * 2.05
    ax.text(4.2, y, cid, fontsize=10.0, va="center", weight="bold", color=COL[stc])
    ax.text(7.0, y, fx(desc), fontsize=10.0, va="center")
    ax.text(58.0, y, st, fontsize=10.0, va="center", color=COL[stc])
    ax.text(64.0, y, fx(note), fontsize=9.2, va="center", color="#546e7a")

# ============================== 底部右：本轮进展 ==============================
ax.add_patch(FancyBboxPatch((1.8, 0.6), 96.4, 13.6,
                            boxstyle="round,pad=0.4,rounding_size=1.0",
                            linewidth=1.8, edgecolor="#1565c0", facecolor="#f3f7fd", zorder=1))
ax.text(3.2, 12.9, "本轮进展（2026-09-21，全部为实测）", fontsize=11.5,
        weight="bold", va="center", color="#0d47a1")
prog = [
    ("√", "显式交错成型（本夜主线）：面与体相都在 timestep_begin 显式推一步；砍掉 mortar ⇒ 熔池 3 步全收敛", OK),
    ("√", "守恒 = 恒等式：面拿到 9.749332e-16 ／ 体相少 9.749332e-16 ⇒ 比值 1.000e+00", OK),
    ("√", "熔池 depletion 转正（0.72%）：与关掉耦合逐位相同 ⇒ 交换确实在发生", OK),
    ("√", "S10 面内扩散：机制测试下阶跃铺平到均值；关掉时精确不动（干净 A/B）", OK),
    ("√", "S11 拖曳机制落地：L_eff = L/(1+β·A_s·Γ_GB·h_gb)；β 无文献值 ⇒ 默认关（待你定）", OK),
    ("√", "A5 时间收敛判据：实测阶数 p≈1.05（一阶）⇒ 设计规则 k_att·dt ≤ 0.01 才有 1% 精度", OK),
    ("√", "B2 二维版跑通：守恒 1.0000、depletion 与三维互印（1.23e-4 vs 1.27e-4）", OK),
]
gaps = [
    ("×", "G5/C2 面跟随 η：面还钉在网格上，新凝固的晶界没被覆盖 ⇒ 下一个最关键的工程"),
    ("×", "G6 拓扑事件 Γ 重映射：晶粒合并/消失时面块怎么办（与 G5 同一套机制）"),
    ("×", "S9 前沿欠解析（体相非晶界）：D_S/V≈0.04 nm ≪ dx ⇒ 要换建模方式（A4）"),
    ("×", "A1 ΔS_seg：在一阶量级（±2R ⇒ Γ 差 2.5~7 倍）；已给补偿效应方案 −0.15R，待你确认"),
    ("×", "A3 δ·D_GB(T)：1200 K 快 1e5~1e6 倍（已算）；但 900 K 外推要先补 α 相（T6）"),
    ("×", "A2 拖曳 β：机制已就位（默认关）；β 无文献值 ⇒ 待你定"),
]
for i, (mark, head, _c) in enumerate(prog):
    x0 = 4.0
    y = 11.2 - i * 1.9
    ax.text(x0, y, mark, fontsize=11.5, va="center", weight="bold", color=c)
    ax.text(x0 + 1.7, y, fx(head), fontsize=8.4, va="center", color="#1b5e20")
ax.text(51.5, 12.9, "仍然不物理的六件事（不能因为数值干净就放过）", fontsize=11.5,
        weight="bold", va="center", color="#b71c1c")
for i, (mark, head) in enumerate(gaps):
    x0 = 51.5
    y = 11.2 - i * 1.9
    ax.text(x0, y, mark, fontsize=11.5, va="center", weight="bold", color=NO)
    ax.text(x0 + 1.7, y, fx(head), fontsize=8.4, va="center", color="#b71c1c")

out = "/mnt/f/speed_up/pipeline/gibbs/GB_PHYSICS_MAP.png"
fig.savefig(out, dpi=130, bbox_inches="tight", facecolor="white")
print("saved", out)
