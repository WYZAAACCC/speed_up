#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""当前工作全景（一页对齐）—— Ti64 LPBF 晶界 Gibbs 面支线。

本图每一条数字都与代码 / 结果文件逐项核对过，来源：
  pipeline/RESEARCH_INTENT.md                 研究意图 / 路线 / 硬约束（唯一权威）
  pipeline/gibbs/README.md                    §3 1D 验证 / §4 2D 副本 / §6 待办 / §7 修法A
  pipeline/gibbs/gibbs_physics.py             ΔH_seg / s(T) / Γ(923K) / w_GB 反解
  pipeline/gibbs/results_p3c/g_out.csv        3D 体相↔面守恒耦合
  pipeline/gibbs/results_p3d/*_out.csv        3D 面自由度 + 面测度
  pipeline/gibbs/results_p3mv/*_out.csv       面随网格迁移
  pipeline/gibbs/results_probeB/df1e3/*.csv   驱动晶界速率
  pipeline/gibbs/results_pf3g/run.log         3 晶粒相场 dtmin 中止（实测）
  pipeline/gibbs/stage1_meltpool_gibbs.i      2D 副本（含 Gam 块）

版面按「1 y 单位 = 10 pt、1 x 单位 = 14.3 pt」排的，卡片高度都留了余量。
输出： pipeline/gibbs/WORK_STATE_MAP.png / .svg
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch

for cand in ("C:/Windows/Fonts/msyh.ttc", "/mnt/c/Windows/Fonts/msyh.ttc"):
    if os.path.exists(cand):
        fm.fontManager.addfont(cand)
        break
plt.rcParams["font.family"] = "Microsoft YaHei"
plt.rcParams["axes.unicode_minus"] = False

OK, PART, NO, INFO = "#2e7d32", "#e65100", "#c62828", "#1565c0"
GREY = "#9e9e9e"
FILL = {"ok": "#e8f5e9", "part": "#fff3e0", "no": "#ffebee",
        "info": "#e3f2fd", "none": "#ffffff", "todo": "#f5f5f5"}
EDGE = {"ok": OK, "part": PART, "no": NO, "info": INFO,
        "none": "#90a4ae", "todo": GREY}

# 微软雅黑（msyh.ttc）缺这几个码位，渲染出来是空框 —— 统一换成它有的字形。
# 可用性用 fontTools 查过 cmap：→(0x2192)/※(0x203B)/×(0x00D7)/√(0x221A)/★(0x2605) 都在。
_SUBS = {"⇒": "→", "↔": "→", "⚠": "※", "🔒": "", "❌": "×", "✅": "√", "₀": "0"}


def _fix(s):
    for k, v in _SUBS.items():
        s = s.replace(k, v)
    return s


fig, ax = plt.subplots(figsize=(20, 14))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")
fig.subplots_adjust(left=0.004, right=0.996, top=0.996, bottom=0.004)


def rect(x, y, w, h, fc="white", ec="#90a4ae", lw=1.4, r=1.0, z=2):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0,rounding_size=%s" % r,
                                linewidth=lw, edgecolor=ec, facecolor=fc, zorder=z))


def text(x, y, s, fs=10, color="#212121", ha="left", va="center",
         bold=False, z=6, ls=1.38):
    ax.text(x, y, _fix(s), fontsize=fs, color=color, ha=ha, va=va, zorder=z,
            weight="bold" if bold else "normal", linespacing=ls)


def band(y0, h, tag, fc="#fafafa", ec="#b0bec5", tag_color="#37474f", fs=12.5):
    rect(0.6, y0, 98.8, h, fc=fc, ec=ec, lw=1.3, r=1.2, z=1)
    text(2.2, y0 + h - 1.5, tag, fs=fs, bold=True, color=tag_color)


def card(x, y, w, h, head, body, status="none", fs_head=9.8, fs_body=8.3,
         head_color=None, gap=1.5):
    rect(x, y, w, h, fc=FILL[status], ec=EDGE[status], lw=1.7, r=0.9, z=2)
    rect(x, y, 0.7, h, fc=EDGE[status], ec=EDGE[status], lw=0, r=0.3, z=3)
    if head:
        text(x + 2.0, y + h - 1.4, head, fs=fs_head, bold=True,
             color=head_color or EDGE[status])
    if body:
        text(x + 2.0, y + h - 1.4 - gap, body, fs=fs_body, color="#263238",
             va="top")


# ============================== 标题 ==============================
rect(0.6, 93.6, 98.8, 6.0, fc="#eceff1", ec="#263238", lw=2.2, r=1.2, z=1)
text(2.4, 97.6, "Ti64 LPBF 晶界精细仿真 —— 当前工作全景（一页对齐）",
     fs=17, bold=True, color="#1a237e")
text(2.4, 94.9, "本支线 = 生产模型的隔离副本（生产 stage1_meltpool_c.i 一个字未动，SHA256 冻结）"
                "   ·   2026-09-20", fs=10.0, color="#37474f")
for i, (c, lab) in enumerate([(OK, "已验证（实测）"),
                              (PART, "部分 / 能跑但不物理"),
                              (NO, "未做"),
                              (GREY, "未开始")]):
    bx = 62.8 + i * 8.6
    rect(bx, 95.2, 1.4, 1.4, fc=c, ec=c, lw=0, r=0.3, z=4)
    text(bx + 1.8, 95.9, lab, fs=8.1, color="#37474f")

# ============================== ① 为什么做 ==============================
band(80.5, 12.0, "① 为什么做这个仿真 —— 两条前提（项目成立的地基）")
cw, cgap = 31.73, 1.2
card(1.6, 81.3, cw, 8.6, "要做什么（架构权威：RESEARCH_INTENT）",
     "为「逐面神经算子」造训练用参考解\n"
     "算子只学【晶界上的溶质扩散与分配】\n"
     "晶粒拓扑演化仍走传统求解器\n"
     "2×2 = 拓扑T/溶质C × 阶段1/阶段2，交错耦合", "info", fs_body=9.0)
card(1.6 + cw + cgap, 81.3, cw, 8.6, "前提 P1（已用实测落地）",
     "晶界「精细 + 物理正确」的仿真\n"
     "→ 对最终组织与物化性能很重要\n"
     "→ 硬指标：不能用「如实声明局限」绕过\n"
     "→ 训练真值里晶界怎么表示 = 前提中的前提", "ok", fs_body=9.0)
card(1.6 + 2 * (cw + cgap), 81.3, cw, 8.6, "前提 P2（至今还没实测）",
     "这种精细仿真 → 很贵\n"
     "→ 才值得交给神经算子去加速\n"
     "※ 但「贵」这件事没被实测过\n"
     "（现有反证：弥散板下溶质只占总成本 13%）", "no", fs_body=9.0)

# ============================== ② 两代表示 ==============================
band(61.3, 18.2, "② 晶界用什么表示 —— 两代对照（这是整个项目的枢轴）")
cw2 = 48.1
card(1.6, 62.1, cw2, 15.0, "① 生产模型：弥散晶界（4 µm 厚板）   冻结未动",
     "· 晶界 = 4 µm 宽的场；偏析强度由一个无量纲常数 Ω0 定\n"
     "· Γ ∝ w_GB → Γ 一旦对上文献，s 必塌到 1.0015\n"
     "   （真实值：2.89 @1950 K  /  8.08 @923 K）→ 二者不可兼得\n"
     "· 没有独立的晶界扩散通道（全域用同一个 M）\n"
     "· D_固 / D_液 = 1.59 → 物理上反了（真实液相快约 4 个量级）\n"
     "· 需要 w_GB ≈ 0.24–0.29 nm 才能同时给对 s 与 Γ\n"
     "   → 与生产用的 4 µm 差 14031 倍", "no", fs_body=9.0)
card(51.1, 62.1, cw2, 15.0, "② 本支线：Gibbs 面（零厚度面 + 面状态量 Γ）",
     "· Γ = A_s·c_GB（McLean 等温线，A_s = Γ0·K(T)）→ 面上有自己的热力学\n"
     "· dΓ/dt = k_att·(Γ_eq − Γ)；体相 → 面按归一化 shape 守恒交换\n"
     "· 真实 ~1 nm 偏析层被 Γ 吸收 → 不需要 nm 网格（8000 倍问题消解）\n"
     "· 【实测】Γ 与 w_GB 逐位无关（2/5/10/20 nm 四档完全相同）\n"
     "· 【实测】Γ ∝ K(T)，五位有效数字\n"
     "· 【隔离】生产二进制 SHA256 构建前后逐位不变\n"
     "· 载体：独立 app（GibbsApp）+ 4 个自写对象", "ok", fs_body=9.0)

# ============================== 推翻的旧判断 ==============================
rect(0.6, 54.9, 98.8, 5.4, fc="#fff8e1", ec="#f9a825", lw=1.6, r=1.2, z=1)
text(2.2, 57.6, "※ 本次长讨论\n推翻的三个旧判断", fs=10.2, bold=True,
     color="#e65100", va="center")
strip = [
    "「Gibbs 面装不进熔池（差 8000 倍）」\n"
    "× 错：8000 倍是【弥散晶界 vs 真实晶界】\n"
    "→ Gibbs 面应直接做在熔池网格上（dx = 0.5 µm）",
    "「晶界储存只占体相 0.0036% → Γ 可用代数量」\n"
    "× 错：Γ 的演化就是算子要学的东西\n"
    "→ Γ 必须是独立状态量，否则算子没东西可学",
    "「w（η 界面宽）是个麻烦」\n"
    "※ 拆开：w 有 4 个角色，只需把【晶界溶质区宽度】\n"
    "解耦到 Gibbs 面 → 不需要 nm 网格",
]
sw = 25.7
for i, s in enumerate(strip):
    sx = 20.5 + i * (sw + 0.8)
    rect(sx, 55.4, sw, 4.4, fc="#ffffff", ec="#f9a825", lw=1.2, r=0.7, z=2)
    text(sx + 1.4, 57.6, s, fs=8.4, color="#37474f", va="center")

# ============================== ③ 已经做到哪 ==============================
band(36.3, 17.6, "③ 已经做到哪（下面每一条都是实测 / 已验证，不是「我认为」）",
     fc="#f1f8f2")
done = [
    ("物理核心（纯 Python，秒级可跑）",
     "gibbs_physics.py = 单一参数来源\n"
     "ΔH_seg = −18.38 kJ/mol（从 Tan 2016 锚点反解）\n"
     "落在 DFT 常见量级 −10~−30 内 √"),
    ("偏析绝对值锚定文献",
     "Γ(923 K) = 3.75 at/nm² = 0.291 个单层\n"
     "落在 Tan 2016 锚点 2.2–5.3 at/nm² 之内\n"
     "s: 8.08 @923 K → 2.89 @1950 K（高温稀释）"),
    ("1D 弥散版：PDE 复现 McLean",
     "c_max 随 κ_c 单调收敛 → −2.11% 平台\n"
     "残余偏差有明确解释（节点极值 + 单元采样）\n"
     "温度依赖：模型 s 比 0.500 vs 解析 0.481 √"),
    ("1D Gibbs 面版（决定性判据）",
     "固定域长，只扫 w_GB = 2 / 5 / 10 / 20 nm\n"
     "Γ = 1.609661e-06（四档逐位相同）\n"
     "极差 / 均值 = 0.0000"),
    ("Γ 的温度依赖正确",
     "Γ / K(T) = 7.7115e-07\n"
     "在 1950 / 1500 / 923 K 五位有效数字相同\n"
     "→ 弥散表示在数学上做不到这件事"),
    ("3D 里的面自由度打通",
     "低维块 + 自写守恒通量约束（GBFluxExchange）\n"
     "面测度 1.28e-16 m²（与解析一致）\n"
     "面 PDE 可跑、面内守恒、非共形传递可用"),
    ("体相 → 面 守恒交换",
     "总溶质相对漂移 4.0e-12\n"
     "平衡 Gam → 0.034151 vs 解析 0.0341175（+0.10%）\n"
     "面随网格变形：面积与 ∫Γ dA 同因子 1.00813"),
    ("面「能跟着材料走」",
     "驱动晶界：v_实测 / v_解析 = 1.011；Δf = 0 → v = 0\n"
     "3 晶粒共形构型几何正确\n"
     "※ 只验证了「跟着网格位移」，还不是跟着 η 场"),
]
dw = 23.65
for i, (hd, bd) in enumerate(done):
    r_, c_ = divmod(i, 4)
    card(1.6 + c_ * (dw + 1.0), 37.1 + (1 - r_) * 7.65, dw, 6.65, hd, bd, "ok")

# ============================== ④ 还差什么 ==============================
band(17.9, 17.4, "④ 还差什么（按优先级；★ = 卡着项目主干的两个物理缺口）",
     fc="#fdf3f3")
gaps_ = [
    ("① 非平衡动力学 → 溶质拖曳 ★",
     "五条通道里最关键的一条\n"
     "现在取局域平衡 → 拖曳恒为 0\n"
     "需要 k_att 有限 + 变分一致地进 η 方程", "no"),
    ("② 拓扑事件处 Γ 的守恒重映射 ★",
     "P1 的核心选题\n"
     "晶粒合并 / 消失时，面块上的 Γ 怎么办？\n"
     "这是「溶质反过来作用拓扑」的落点", "no"),
    ("③ 面不跟随 η 场 ★",
     "搬到生产前最难的一步\n"
     "现在只验证了「跟着网格位移」\n"
     "需要让面块随 η 场重建 / 移动", "part"),
    ("④ 手写 3 晶粒相场不收敛",
     "Mercedes 构型 t = 0 几何正确\n"
     "但第 1 步就 dtmin 中止（run.log 实测）\n"
     "绕开标准 GrainGrowth action 的代价", "no"),
    ("⑤ 参数缺口（独立的一堵墙）",
     "ΔS_seg 完全缺失（现设 0，最大单点隐患）\n"
     "δ·D_GB(T) 在文献里不存在\n"
     "没有 Thermo-Calc 授权", "no"),
    ("⑥ 固液界面欠解析 476×",
     "W/(D/V) = 476 → 原理性不可修\n"
     "靠抗截留 + D_L 子网格闭合打工（残差 ≤6.6%）\n"
     "※ 这一层 Gibbs 面不管", "part"),
    ("⑦ 2D 副本的 Gam 块刚度",
     "k_att = 1e6 时第 2–3 步发散，MUMPS 直接解也救不了\n"
     "降 k_att 到 1e2 能跑完，但 τ = 10 ms 不物理\n"
     "修法 A 两个核已编入，功能正对照尚未取得", "part"),
    ("⑧ 三叉线 / β→α 相变",
     "三叉线溶质通量平衡 Σ J_s = 0 未做\n"
     "β→α 相变（用户已要求加）未做\n"
     "建议：先闭合晶界层，再加相变", "no"),
]
for i, (hd, bd, st) in enumerate(gaps_):
    r_, c_ = divmod(i, 4)
    card(1.6 + c_ * (dw + 1.0), 18.7 + (1 - r_) * 7.55, dw, 6.55, hd, bd, st)

# ============================== ⑤ 主线五步 ==============================
band(0.6, 16.3, "⑤ 主线五步 · 现在在哪（这是唯一主线，用户已同意方向）",
     fc="#f4f6f8")
yl = 12.0
ax.plot([3.5, 58.5], [yl, yl], color="#546e7a", lw=2.6, zorder=4,
        solid_capstyle="round")
steps = [
    ("① 副本上算 Γ 并输出", "只加一个材料 + 一个后处理", "未开始", GREY, 7.0),
    ("② Γ 接入为独立状态量", "面块 + 守恒交换（3D 小算例已验证）", "部分", PART, 19.0),
    ("③ 面跟随 η 场", "几何 —— 最难的一步", "未开始", GREY, 31.0),
    ("④ 非平衡动力学 + 拖曳", "★ 最关键物理", "未开始", GREY, 43.0),
    ("⑤ 拓扑事件 Γ 重映射", "P1 的核心选题", "未开始", GREY, 55.0),
]
for lab, note, st, col, x in steps:
    ax.plot([x], [yl], "o", ms=17, color=col, zorder=5,
            markeredgecolor="white", markeredgewidth=1.6)
    text(x, yl, lab[0], fs=10.5, color="white", ha="center", va="center",
         bold=True, ls=1.0)
    text(x, yl - 1.9, lab[2:], fs=8.8, color="#263238", ha="center", va="top",
         bold=True)
    text(x, yl - 3.9, note, fs=7.4, color="#546e7a", ha="center", va="top")
    text(x, yl - 5.6, st, fs=9.0, color=col, ha="center", va="top", bold=True)
text(2.4, 3.6,
     "待你拍板（唯一悬空决策）：第 1 步直接上生产副本（只加材料 + 后处理，零风险），\n"
     "还是先在小算例里把「面跟随 η」做通再搬？  →  我的倾向：两条并行。"
     "第 1 步未做时不要碰生产原件（有 SHA256 冻结门禁）。", fs=8.3, color="#c62828",
     va="top")

bw = 35.7
card(63.5, 7.3, bw, 6.3, "生死线 ① G2/G3「面在数值上挂在哪」  √ 已打通",
     "低维块 + 自写 mortar 守恒通量交换；\n"
     "实测面测度 1.28e-16 m²、体-面守恒漂移 4.0e-12；\n"
     "MultiApp 非共形传递（KDTree）亦可用。", "ok", fs_head=9.6, fs_body=8.1)
card(63.5, 0.6, bw, 6.3, "生死线 ② K3/K4「非平衡动力学 + 刚度」  × 未解决",
     "交换速率 shape·k_att ≈ 1.9e11 /s，\n"
     "比它喂给的扩散快 6 个量级 → MUMPS 直接解也崩；\n"
     "降 k_att 能跑但 τ = 10 ms 不物理 → 只作临时方案。", "no",
     fs_head=9.6, fs_body=8.1)

out = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "WORK_STATE_MAP"))
fig.savefig(out + ".png", dpi=160)
fig.savefig(out + ".svg")
print("wrote", out + ".png")
