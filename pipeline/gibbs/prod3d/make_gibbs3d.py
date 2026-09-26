#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生产 2D 熔池输入 -> **3D + Gibbs 面** 副本（只读生产原件，绝不改动）。

输入： pipeline/stage1_meltpool_c.i                       （只读）
      pipeline/columnar_seeds.csv                         （柱状晶种子，生产同款）
输出： pipeline/gibbs/prod3d/stage1_meltpool_gibbs3d.i

做什么
------
1. **三维化**：2D 域 -> 3D 域；Rosenthal 温度场补上 z 项（3D 点源形式）；
   熔池子域判据同样补 z 项。
2. **把晶界变成真正的面**（Gibbs）：
   · 柱状晶的晶界位置由 columnar_seeds.csv 的**中点**给出（生产的晶粒就长这样）；
   · 按这些中点把网格切成 M+1 个**块**（每块 = 一个柱状晶），
     块之间的内界面 = 晶界 -> 建 sideset -> LowerDBlockFromSideset 做成**低维块**；
   · 每条晶界一个独立的低维状态量 `Gam{k}`（= Γ/A_s，Γ 是 Gibbs 过剩量）。
     => 「逐面算子」的「面」就是它。
3. **晶界溶质那一层从弥散场换成 Gibbs 面**：
   · 生产自由能里的晶界偏析项（`A_part*c^2*min(1,2S)` 与 `Omega0/wgb` 项）**删除**；
   · 偏析改由面上的 McLean 等温线承担：`dΓ/dt = k_att·(Γ_eq − Γ)`，
     `Γ_eq = Γ0·K(T)·c`，`K(T) = exp(−ΔG_seg/(RT))` —— **温度相关**（生产没有）。
   · 体相 <-> 面 的守恒交换用已验证过的 mortar 约束 `GBFluxExchange`，
     系数 `kex = A_s·k_att/ρ_mol`，随位置/时间的 T 变（`A_s = Γ0·K(T)`）。
4. **所有体相对象加 block 限制**：实测（probe_lowdim.i）证明**不加限制的变量/核/材料
   会跑到低维块上去**，会静默污染界面节点的方程。
5. **关掉 AMR**：max_h_level = 0（mortar 约束 + AMR 未验证，单独一堵墙）。

已知简化（全部显式记账）
------------------------
  S1. 晶界面**静止**：面块挂在网格面上，不随 η 场移动（缺口③）。
      初始固相区内的晶界面积是对的；**新凝固出来的那一段晶界没有被面块覆盖**。
  S2. `Gam ≡ Γ/A_s(T)`，而 A_s 随 T 变 => 守恒式漏掉一项 `(Gam/ρ_mol)·dA_s/dt`。
      量级 (ΔH/(R T^2))·(dT/dt)/k_att ≈ 0.4%（1950 K、dT/dt~1e7 K/s）。
  S3. 关 AMR（见 5）。

用法（在 WSL 里跑，避免 Windows python3 把行尾写成 CRLF）：
  python3 make_gibbs3d.py
"""
import csv
import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.join(REPO, "pipeline", "stage1_meltpool_c.i")
SEEDS = os.path.join(REPO, "pipeline", "columnar_seeds.csv")
_ONAME = "stage1_meltpool_nogb3d.i" if os.environ.get("NO_GIBBS", "0") == "1" \
    else ("stage1_meltpool_gibbs3d_iso.i" if os.environ.get("TISO", "")
          else "stage1_meltpool_gibbs3d.i")
if os.environ.get("GAMIC", "") and float(os.environ["GAMIC"]) != 0.036:
    _ONAME = _ONAME.replace(".i", "_neq.i")
if os.environ.get("DROP", ""):
    _ONAME = _ONAME.replace(".i", "_drop" + os.environ["DROP"].replace(",", "_") + ".i")
if os.environ.get("OUTSUF", ""):
    _ONAME = _ONAME.replace(".i", "%s.i" % os.environ["OUTSUF"])
OUT = os.path.join(HERE, _ONAME)

# ---------------------------------------------------------------- 几何 / 分辨率
# 窗口选法（有实测依据，不是拍的）：
#   · 柱状晶种子在 x = -258.5 / -215.2 / -176.7 / ... µm（间距 ~40 µm）
#     => 晶界（中点）在 x = -236.87 / -195.96 µm，两条都落在窗口里
#   · Rosenthal 的池深（T>1628 K 判据，z=0）：x=-262 -> 31.7 µm，x=-176 -> 46.4 µm
#     => 域深必须 >= ~47 µm，否则窗口里**一点固相都没有**（没有晶粒、没有晶界）
XMIN, XMAX = -262e-6, -176e-6      # 86 µm
YMIN, YMAX = 0.0, 48e-6            # 深度：y=0 是上表面
ZMIN, ZMAX = 0.0, 10e-6            # 横向（三维化新加的）
# 单元尺寸 + 数值界面宽（wGB）**必须成对选**：
#   判据 A：wGB/dx ≈ 4（生产就是 4 µm / 1 µm）。
#   判据 B：wGB / 晶粒宽 要小（官方 3D 示例 ~20%，本项目 phase1_3d.i 用到 23%）。
#   ⚠ 关键：Gibbs 把**偏析**从弥散带上搬到了面上 ⇒ 放大 wGB **只动数值界面**，
#     不再污染偏析物理（这是 Gibbs 表示带来的"红利"；弥散表示下放大 wGB 会直接改 Γ）。
#   放大 wGB 必须**同步重标定** mu0 = 6σ/wGB、κ = 0.75·σ·wGB、L = 4/3·M0/wGB，
#   否则改的就是**真实晶界能**（见 AGENTS.md §3.5，本项目最容易踩的坑）。
DX = float(os.environ.get("DX", "1.0e-6"))
WGB = float(os.environ.get("WGB", "4.0e-6"))
# 【2026-09-21】初始熔池（= eta 初值置零的区域）的判据温度。
#   生产原值是 **1628 K**（注释里没给依据），而同一个文件里：
#     · `liquid_flag = if(T>1903, 1, 0)`      ← 另一个"液相"定义用 1903 K
#     · Landau 熔化 T_mid = 1903 K（dT = 60） ← 模型真正的熔点
#   ⇒ 1628 K 比模型熔点低 275 K：那一圈"被当成液相、eta 置 0"的材料，
#     按模型自己的自由能其实是**固相**（Landau 会把 eta 拉回 1）。
#   本开关用来做**单因素 A/B**：把判据对齐到模型熔点，看停滞是否随它消失。
TPOOL = float(os.environ.get("TPOOL", "1628.0"))
# 【2026-09-21 用户决定 (1)】把温度场**冻结成一张静态的三维温度图**。
#   原理：`laser_T` 里唯一的含时项是点源位置 `x_s(t) = -120 µm + 0.6*t`
#         （表达式里写作 `0.6*t`）。把 `t` 换成一个常数 ⇒ 场变成 T(x,y,z)，
#         之后整个仿真就在这张**固定的**温度场里演化。
#   取值 = 冻结的那个时刻 [s]：
#       TSNAP=0        ⇒ 源停在 -120 µm（当前设置的 t=0 快照）
#       TSNAP<0        ⇒ 源更靠 -x（例如 TSNAP=-1.583e-4 ⇒ 源在 -215 µm，熔池压住晶界）
#       TSNAP>0        ⇒ 源更靠 +x（熔池更远、窗口更冷）
#   ⚠ 物理后果（必须知道）：静态场下**熔池永远不凝固**——
#     区域 {T > 熔点} 恒为液态、{T < 熔点} 凝固。这正是"稳态焊池"的理想化，
#     凝固只发生一次（初始瞬变），之后是粗化 + 晶界偏析/扩散。
#     若要让熔池也最终消失，需要给幅值加时间衰减（另一件事，未做）。
TSNAP = os.environ.get("TSNAP", "")
# 【2026-09-21 用户澄清】"激光把金属熔化之后就关闭了" —— 关闭热源**不等于**温度场冻结：
#   热源停供后，熔池的热量向周围固体传导散走 ⇒ 温度**必须下降**，材料才会凝固。
#   而模型里**唯一**的凝固驱动力是 Landau 项 mu_T(T) ⇒ T 若完全不动，
#   {T > 熔点} 那 60% 的域**永远不会凝固**。
#   ⇒ 物理正确的"关激光"= **形状给定 + 过热度随时间衰减**：
#        T(x,y,z,t) = 353 + ( T0(x,y,z) - 353 ) * exp(-t/tau)
#      熔池因此由外向内**收缩**，在 t ≈ 0.60*tau 时完全消失，之后全固态演化。
#   tau 的量级依据（两条独立估算，同一量级）：
#     · 传导估算：tau ~ L^2/alpha，L~20~40 µm、Ti64 的 alpha = k/(rho*cp)
#       = 7/(4430*560) ≈ 2.8e-6 m²/s ⇒ tau ≈ 1.4e-4 ~ 5.7e-4 s
#     · LPBF 实测冷却速率 1e6~1e7 K/s，过热度 ~1280 K ⇒ tau ≈ 1.3e-4 ~ 1.3e-3 s
#   ⇒ 默认建议 tau = 1e-4 ~ 3e-4 s（由命令行给）。空 = 不衰减（= 完全静态，(a) 方案）。
TDECAY = os.environ.get("TDECAY", "")
# 点源快照位置带来的判据平移：判据里写的是 (x + XOFF) = x - x_s
XOFF = 1.2e-4 - (0.6 * float(TSNAP) if TSNAP != "" else 0.0)
# 【2026-09-21】抗截留电流 [at_susc] 的 ALPHA 与 W。
#   ⚠ 生产的 W = 2e-6 m 是**硬编码**的界面宽度，而本模型的 eta 界面宽是 wGB
#     （生产 4 µm、本 2D 副本 8 µm）⇒ W 与 wGB **不一致**（差 2~4 倍）。
#   Karma–Rappel 抗截留电流的幅度必须是 sqrt(...)*W*(∂φ/∂t)，W 就是界面宽度
#   ⇒ 用错 W 会让"被界面吞掉/吐出的溶质"补偿不完整。
#   本开关用来做单因素 A/B。
# 【2026-09-23 物理正确化】抗截留系数 a（不再叫 ALPHA：语义已变）
#   F = a * W * [ c_l(mu) - c_s(mu) ]
#   Plapp, PRE 84, 031601 (2011) 式(102); Echebarria/Folch/Karma/Plapp,
#   PRE 70, 061604 (2004) 式 (j_at = -a W (1-k) c_l^0 e^u (dphi/dt) n)
#   Echebarria 对其插值对给出 a = 1/(2 sqrt2) = 0.35355；
#   在本模型形式下的 1D 同构标定值见 ca_pf_framework/P11_SPEC.md §22
#   （W=200 nm 给出 a* ≈ 2.04；W 无关性待确认）。
AT_A = float(os.environ.get("AT_A", os.environ.get("AT_ALPHA", "1.90")))
# 【2026-09-22 修正】抗截留幅值必须用【本模型真实的界面宽】, 即 WGB。
# 原来默认 2.0e-6 是生产里硬编码的值; 在 wGB=8um 的副本里它小了 4 倍,
# 导致"被界面吞掉/吐出的溶质"补偿不完整 —— 这很可能就是之前记录的
# "抗截留机制通、但效应为零" 的原因。仍可用 AT_W 环境变量覆盖。
AT_W = float(os.environ.get("AT_W", "%.10g" % WGB))
# 【2026-09-21】把 eta 的晶粒着色初值**也铺到液相块**上（默认只铺固相块）。
#   默认做法会在液相块边界留下一个**逐单元跳变**（eta: 1 -> 0）。
ICALL = os.environ.get("ICALL", "0") == "1"
SIGMA_GB = 0.6                     # J/m^2（Gornakova & Prokofjev 2020）
NX = int(round((XMAX - XMIN) / DX))
NY = int(round((YMAX - YMIN) / DX))
NZ = int(round((ZMAX - ZMIN) / DX))

# ---------------------------------------------------------------- 物理常数
FREF = 1.6423e9        # R*T_ref/v_m  [J/m^3]
TREF = 1950.0
C0 = 0.036
# 【A/B 诊断用】KPART_V=1 等价于关掉固液分配项（log(KPART) = 0）
KPART = float(os.environ.get("KPART_V", "0.63"))
DH_SEG = -11931.1      # gibbs_physics.py 由 Tan 2016 锚点 + delta_GB=0.5nm 反解
DS_SEG = 0.0           # 缺失，显式设 0（本项目「甲类空白」）
GAMMA_MONO = 2.1421e-5  # mol/m^2 单层饱和
RHOMOL = 101292.8831   # mol/m^3
K_ATT = 1.0e6          # 1/s 附着速率（[A] 标定值）

# 预条件子：生产用 asm/ilu（快），但**mortar 约束从来没在 asm/ilu 下测过**
# （3D 原型 p3c 一直是 lu+mumps）。用环境变量切换，便于做单因素对照。
PRECOND = os.environ.get("PRECOND", "asm")
NO_GIBBS = os.environ.get("NO_GIBBS", "0") == "1"   # 对照组：只做 3D 化，不加 Gibbs 面
# 非线性绝对容差。生产是 1e-9。3D 粗网格下 **实测存在 3.5e-9 的残差地板**
# （见报告「地板诊断」：c 方程、过渡区节点、与 dt 完全无关、Gam 的残差只有 1e-30），
# 所以 3D 算例要把 atol 设在实测地板之上，否则每步都会报 DIVERGED_LOCAL_MIN。
# ⚠ 这**不是**放宽到生产禁止的 1e-6 —— 1e-8 仍比它严 100 倍，且有实测依据。
NL_ABS_TOL = os.environ.get("NLATOL", "")     # 空 = 保持生产值
DTMAX = os.environ.get("DTMAX", "")           # 空 = 保持生产值 2e-6
# 【已废弃 2026-09-21】原来的做法是给 c 加下限 max(c,CFLOOR)，CFLOOR = 1e-6。
#   动机（当时）：理想溶液的 f = c·ln c 在 c→0 发散，粗网格下固液前沿会把 c
#   冲到负值（实测 c_min = -0.0135）⇒ log 变 NaN ⇒ 整步发散。
#   **但截断本身制造了更严重的问题**（f_cc→0、M 跳变 10^6 倍），
#   已由下面的 C1/C2 抛物线正则化取代。CFLOOR 只留作历史记录，不再使用。
# ===========================================================================
# 【2026-09-21 根因修复】自由能的正则化 —— 取代 max(c,CFLOOR) 截断
# ===========================================================================
# 理想溶液的摩尔自由能只有 0<c<1 的定义域：
#   g(c) = c*ln c + (1-c)*ln(1-c),   g''(c) = 1/c + 1/(1-c)
#   · c->0+ 时 g'' -> +∞（稀溶液极硬，物理正确）
#   · c<0  时 g'' < 0  ⇒ M = D_eff/g'' < 0（负迁移率 = 反扩散 = 爆炸）
# 原代码把它截断成 max(c,CFLOOR)（CFLOOR=1e-6）。本轮**实测**该截断的两个后果：
#   (1) f_cc 在 c<CFLOOR 处掉到 0              ⇒ c 方程的行退化；
#   (2) M ∝ max(c,CFLOOR) 在 c=CFLOOR 处**跳变 10^6 倍**；
#   而集合 {c<CFLOOR} 是**子网格尺度、随时间乱动**的 ⇒ 离散通量在上面
#   不可微 ⇒ 牛顿残差**冻结在非零地板上**（实测 2D 熔池 t=1.27e-7 之后
#   |R| = 2.375117e-05 逐位冻结，dt 砍到 1e-12 也无效）。
# ---------------------------------------------------------------------------
# 修法（**纯数值**）：在 c=C1 处用匹配 g, g', g'' 的**抛物线外推**。
#   · c >= C1 时表达式与理想溶液**逐字相同**（只是把 max 换成 if）
#     ⇒ 物理区间（c0=0.036、实测 c 落在 [0.01,0.13]）**逐位不变**。
#   · C^1+C^2 连续 ⇒ 无拐点、无跳变、雅可比完整。
#   · g''(c<C1) = GPP1 > 0 由构造保证 ⇒ f_cc>0、M>0。
#   · c>C2 侧同样外推（防 c 越界时 log(1-c) 变 NaN）。
# `if()` 的导数行为**已实测**：取活跃分支的导数，且非活跃分支的 NaN 不会
#   污染结果（对照实验 _test_if.i / _test_minmax.i）；
#   而 `max()` 在夹紧处把导数置 0 —— 这正是本条要绕开的。
# 【默认值 = 1e-2，有实测依据】
#   ε 收敛性（三档 C1 = 1e-4 / 1e-3 / 1e-2，2D 熔池，15 个共同时间点）：
#     · t <= 1.075e-7 上三档**逐位相同**（c_max/c_min/depletion/gr*/Γ 全部 14 位一致）
#     · 越过旧停滞点 t*=1.268e-7 后，物理量（c_max、depletion、gr0_max、Γ）在
#       C1=1e-3 与 1e-2 之间一致到 ~1e-5 相对
#     · 唯一在 C1 上有 1~2% 敏感的是 **c_min 本身**（即"undershoot 的深度"，
#       它本来就是非物理量）
#     · 稳健性：t=1.275e-7 那一步的牛顿迭代数 = **35 (1e-4) / 17 (1e-3) / 5 (1e-2)**
#   ⇒ 更大的 C1 明显更稳健，而物理结果不变 ⇒ **默认取 1e-2**。
#   ⚠ 使用前提：C1 要明显低于**物理最低浓度**。本例物理最低浓度 ≈ c_s,eq ≈ 0.027
#     （k·c_l，c_l≈0.043）⇒ C1 = 1e-2 有 **2.7 倍**余量。
#     若将来工况（低温、强偏析）把 c 压到接近 1e-2，**必须重新核这个余量**。
C1 = float(os.environ.get("C1", "1.0e-2"))
C2 = float(os.environ.get("C2", "0.9"))
KAPC = float(os.environ.get("KAPC", "1.0e-14"))
G1 = C1 * math.log(C1) + (1.0 - C1) * math.log(1.0 - C1)
GP1 = math.log(C1) - math.log(1.0 - C1)
GPP1 = 1.0 / C1 + 1.0 / (1.0 - C1)
G2 = C2 * math.log(C2) + (1.0 - C2) * math.log(1.0 - C2)
GP2 = math.log(C2) - math.log(1.0 - C2)
GPP2 = 1.0 / C2 + 1.0 / (1.0 - C2)
# 无量纲自由能 g(c)：理想溶液 + 两侧 C^2 抛物线外推
G_EXPR = ("if(c<C1, G1+GP1*(c-C1)+0.5*GPP1*(c-C1)^2, "
          "if(c>C2, G2+GP2*(c-C2)+0.5*GPP2*(c-C2)^2, "
          "c*log(c)+(1-c)*log(1-c)))")
# g''(c)：[solute_mobility] 的 M = D_eff/(FREF*(T/TREF)*gpp) 必须用它，
#   才能保证 D = M*f_cc **逐点精确**（审计 P0-4 的修复不被破坏）
GPP_EXPR = "if(c<C1, GPP1, if(c>C2, GPP2, 1/c+1/(1-c)))"
# 【已废弃】CFLOOR 仍保留定义，但**不再出现在任何表达式里**（改用 C1/C2）。
C_FLOOR = 1.0e-6
# 低维变量 Gam 的**方程缩放**（MOOSE 的 `[Variables] scaling`）。
#   为什么必须动它：面上方程的节点残差量级只有 ~1e-16，而体相是 ~1e-6
#   ⇒ SNES 用**一个标量范数**判收敛，面上方程被完全淹没，
#     每一步都在"0 次牛顿迭代"下被判收敛 ⇒ Γ 永远停在初值上（实测）。
#   给它一个 >1 的 scaling 把这一行抬到与体相可比。
#   ★ 实测（2026-09-20）：**必须给**，否则 Γ 一步都不动。
#     不加时：面上的节点残差 ~1e-16，体相 ~1e-6，SNES 用一个标量范数判收敛
#     ⇒ 面上方程被淹没 ⇒ 每步"0 次牛顿迭代"就判收敛 ⇒ Γ 永远停在初值。
#     加 scaling = 1e9 之后：19 步全收敛，Gam_avg 从 0 正常爬到 0.0306（朝 McLean 的 c 收敛）。
GAM_SCALE = os.environ.get("GAMSCALE", "1e9")
# 是否加一套**零位移**的位移系统（`[Mesh] displacements = ...`）。
#   p3c 原型里有；我最初把它删了。有位移网格时 MOOSE 的 mortar 装配走**另一条分支**
#   （`_displaced`），而实测症状正是"体相侧残差根本没算"（只有 type=0/Lower 的调用）。
DISP = os.environ.get("DISP", "1") == "1"
# MOOSE 的**自动缩放**：按雅可比对角把各变量的行残差拉到同一量级。
#   为什么必须有：约束给体相的汇只有 ~1e-17/节点，而体相自己的残差 ~1e-7
#   ⇒ 体相方程"看不见"这个汇 ⇒ 面在拿溶质、体相不丢 ⇒ **不守恒**（实测差 1.8e5 倍）。
#   行缩放不改变解（R_i = 0 乘常数还是 R_i = 0），只改收敛判据的加权。
# ⚠ 默认**关**（0）。2026-09-21 踩过：我为了试它把它设成默认开，忘了改回来，
#   结果熔池算例第 1 步 |R| = 1.92e1（看起来像"耦合打开后发散"）——
#   真相是 automatic_scaling 自己造成的（对比：关掉时第 1 步残差仅 3.5e-6）。
AUTOSC = os.environ.get("AUTOSC", "0") == "1"
# 交错耦合的显式扣账（GBSoluteSink）：把面拿走的溶质按构造成比例地从体相扣掉。
#   为什么必须有：mortar 给体相的那条 primal 残差只有 ~1e-17/节点，而体相自己 ~1e-12
#   ⇒ 容差从 1e-7 扫到 1e-16，体相积分浓度**逐位不变**（实测）。
#   ⇒ 无法靠"同一个牛顿解出来"，只能按构造成立。
SINK = os.environ.get("SINK", "1") == "1"
# ★★ 推荐方案（默认）：**双向显式交错**，砍掉 mortar 约束。
#   理由（实测）：mortar 的强耦合里，给体相的那一项只有 ~1e-17/节点（体相自身 ~1e-12），
#   任何绝对容差都约束不住；而把 kex 修对之后熔池第 1 步就 |R| = 1.92e1。
#   ⇒ 面（Γ）与体相（c）都改成"用上一步已知量"推一步，不做隐式联立。
#   这与 RESEARCH_INTENT.md §3.2「耦合方式：离散、交错」完全一致。
#   守恒 = 恒等式（同一个对象里同时扣两边）。
STAGGER = os.environ.get("STAGGER", "1") == "1"
# 【S10】沿晶界的**面内扩散** ∇_s·(D_GB ∇_s Γ)：把晶界从"存储"变成"快速通道"。
#   这是晶界在 900–1200 K（T/T_m < 0.5）的**主导角色**，也是「逐面算子」要学的一部分。
#   可在交错与 mortar 两种模式下都开。
INPLANE = os.environ.get("INPLANE", "1") == "1"
# 【S11】溶质拖曳（P1 的落点：溶质 → 拓扑 的真实反馈）
#   机制：移动的晶界要拖着偏析云走 ⇒ 有效迁移率下降
#         L_eff = L / (1 + β·A_s(T)·Γ_GB·h_gb)， Γ_GB = 面上的 Γ/A_s 投影到体相节点
#   ⚠ **β 没有文献值**（甲类空白）⇒ 默认关闭（DRAG=0，β=0）：
#     开启后 L_eff ≡ L，与不做的结果**逐位相同**（这也是"管线无害"的正对照）。
#     β 的具体取值需要用户决定（见报告「待你拍板」）。
DRAG = os.environ.get("DRAG", "0") == "1"
# 【T5→C4】Gibbs 吸附：偏析降低晶界能 ⇒ 长大驱动力变小（**这条没有未知系数**）
#   Langmuir/Gibbs 积分形式：  σ(Γ) = σ0 − R·T·Γ0·ln(1 + K(T)·c_GB)
#   在 ACGrGrPoly 里晶界能只通过势垒 mu = 6σ/wGB 进入 ⇒ 做法是把 `mu` 这个**属性**
#   换成随 Γ 变的版本（名字仍叫 mu，所以 GrainGrowth action 与 f_grain 自动跟着变）。
#   实测量级（用我们的 ΔG_seg 与 c=0.036）：Δσ/σ = 4.2% @1950 K、4.3% @923 K。
T5 = os.environ.get("T5", "1") == "1"
# 【正对照】把 Gibbs 吸附的修正放大 T5_MULT 倍（只用于验证"这个材料到底进没进核"）
T5_MULT = float(os.environ.get("T5_MULT", "1.0"))
# 【μ 探针】把材料属性 `mu` 直接导出（MaterialRealAux —— 项目教训 19：这版可靠，
#   后处理器版有"构造顺序伪影"）。用途：判断 T5 的 Γ-依赖到底有没有进到"场"里。
MU_PROBE = os.environ.get("MU_PROBE", "0") == "1"
# 【B2】二维版：同物理、快 ~50×（低维面 → 1D 线元）。用途：
#   · 长时标（ms 量级）物理 —— 三维跑 ms 不可行（~20 s/步 × 1e4 步）
#   · 参数扫描（κ_c / D_GB / β）
#   · G5「面跟随 η」的开发
#   ⚠ 2D 下：z 方向不能有；DISP 自动关；低维单元是 2 节点线元（UO 已用 volume() 统一处理）。
DIM2 = os.environ.get("DIM2", "0") == "1"
# 【数值 1】AMR：mortar 砍掉之后重试（production-sanctioned 的"把前沿解析得更好"的手段）
#   ⚠ 与低维块 + 交错 UO 一起用会改网格 ⇒ UO 必须每步重建节点表（已加 always_rebuild）
AMR = os.environ.get("AMR", "0") == "1"
AMR_LEVEL = int(os.environ.get("AMR_LEVEL", "1"))
AMR_INTERVAL = int(os.environ.get("AMR_INTERVAL", "2"))
BETA_DRAG = float(os.environ.get("BETA", "1.0e4"))   # 占位值 [m^2/mol]，**无文献依据**
# 晶界扩散系数 D_GB —— ⚠ **指派值**（Ti64 无定量数据，甲类空白），沿用生产标定值。
D_GB = float(os.environ.get("DGB", "4.0e-10"))
# 每条晶界**两侧各一个**低维块（MOOSE 文档里"两侧界面"的写法）。
#   ⚠ 2026-09-21 实测：**等温算例**在两侧版下正常（守恒闭合，见 §5.1d），
#     但**真熔池算例**在两侧版下第 1 步就 |R| = 1.92e1（单侧版正常）。
#     熔池的晶界面是**阶梯状**（被 initial pool 切过），两侧 sideset 可能配不上 ⇒
#     留一个开关，默认两侧（等温用），熔池可切回单侧。
TWOSIDE = os.environ.get("TWOSIDE", "1") == "1"
# 等温对照（环境变量 TISO，单位 K）：
#   把 Rosenthal 温度场换成常数 + 把「初始熔池」子域判据换成恒假
#   => 全域等温固相（T < 1882.2 K 熔点），没有糊状区、没有熔化开关的陡变。
#   用途：**受控地**验证「体相 <-> Gibbs 面」这一层的收敛性与守恒，
#   把「糊状区/熔池边界欠解析」这个**与 Gibbs 无关**的干扰项排除掉。
TISO = os.environ.get("TISO", "")
# Γ 的初值（Gam ≡ Γ/A_s 的无量纲值）。默认 = c0（= 局域平衡，t=0 通量为 0）。
# 设成 0 就是一个**非平衡初值**：面从体相里把溶质吸进去，用来验证
#   (a) 它是否**收敛到 McLean 等温线** Gam -> c，
#   (b) 体相贫化量是否等于解析杠杆规则，
#   (c) 总溶质是否守恒。
GAMIC = os.environ.get("GAMIC", "")
# 【S10 验证用】沿晶界方向的 Γ **阶跃**初值：半个面 0.036、半个面 0。
#   ⇒ 开面内扩散时 gam_max 应下降、gam_min 应上升（沿晶界铺平）；
#     关掉时两者都不动。配合 k_att=0 可把"体相交换"隔离掉，只看面内输运。
GAMSTEP = os.environ.get("GAMSTEP", "0") == "1"
# 试验开关：把体相浓度 c 的**变量 block 列表**也扩到低维块上（kernels/materials 不动）。
#   动机：ADMortarConstraint 的 secondary/primary **subdomain 就是低维块**，
#   若 c 未定义在那里，约束可能整块静默失效（实测 Gam 残差恒为 0）。
CVAR_ON_LD = os.environ.get("CVAR_ON_LD", "0") == "1"
# 诊断开关：整段删掉某些段（逗号分隔），用来定位「
# mortar 交换在生产副本里是死的」到底由哪一块引入。
DROP = [s for s in os.environ.get("DROP", "").split(",") if s]


# ===========================================================================
# 解析：**必须按方括号深度**找块的结尾
# ===========================================================================
# ⚠ 2026-09-20 踩到的坑：第一版用 `(^[ \t]*\[Mesh\](?:.*?))\n[ \t]*\[\]` 找块结尾，
#   而 `.*?` 非贪婪 ⇒ 遇到**第一个内层 `[]`** 就截断。
#   后果：[Mesh] 只替换了一半、[Kernels]/[Materials] 只处理了第一个子对象，
#   **而脚本照样打印 OK**。生成出来的文件大段是生产原文（静默出错）。
#   教训与 AGENTS.md §3.1 同类：**块匹配必须按深度，不能按"第一个 []"**。


class Span:
    """模拟 re.Match 的 .start()/.end()/.group(1)，便于复用原有代码。"""

    def __init__(self, text, a, b):
        self._t, _a, _b = text, a, b
        self._a, self._b = a, b

    def start(self):
        return self._a

    def end(self):
        return self._b

    def group(self, i=1):
        return self._t[self._a:self._b]


def _seg(line):
    """去掉行内注释后的可解析部分（注释里的方括号不算数）。"""
    h = line.find("#")
    return line if h < 0 else line[:h]


def _scan(seg, depth):
    """在 seg 里走一遍括号，返回 (新 depth, 触发闭合的列号 or -1)。"""
    j = 0
    while j < len(seg):
        if seg[j] == "[":
            if j + 1 < len(seg) and seg[j + 1] == "]":
                depth -= 1
                if depth == 0:
                    return depth, j
                j += 2
                continue
            depth += 1
        j += 1
    return depth, -1


def block_of(text, name):
    """按**方括号深度**取 [name] 块的完整 span（含头尾）。"""
    pat = re.compile(r"^[ \t]*\[" + re.escape(name) + r"\]", re.M)
    m = pat.search(text)
    if not m:
        return None
    start = m.start()
    off = text.rfind("\n", 0, start) + 1
    depth = 0
    while off < len(text):
        nl = text.find("\n", off)
        if nl < 0:
            nl = len(text)
        seg = _seg(text[off:nl])
        depth, hit = _scan(seg, depth)
        if hit >= 0:
            return Span(text, start, off + hit + 2)
        off = nl + 1
    return None


def direct_children(section_text, indent=2):
    """返回 section_text 里**直接子对象**的 (名字, 起始行, 结束行)。"""
    lines = section_text.split("\n")
    out = []
    prefix = " " * indent + "["
    i = 1
    while i < len(lines):
        ln = lines[i]
        st = ln.strip()
        if ln.startswith(prefix) and st.endswith("]") and not st.startswith("[."):
            name = st[1:-1].strip()
            depth = 0
            j = i
            done = False
            while j < len(lines) and not done:
                seg = _seg(lines[j])
                depth, hit = _scan(seg, depth)
                if hit >= 0:
                    out.append((name, i, j))
                    done = True
                j += 1
            i = j
            continue
        i += 1
    return out


def restrict_section(section_text, bulk, indent=2, skip=()):
    """给 section 里每个直接子对象插入 block = <bulk>（已有 block 行的跳过）。"""
    lines = section_text.split("\n")
    kids = direct_children(section_text, indent)
    for name, start, end in reversed(kids):
        if name in skip:
            continue
        body = "\n".join(lines[start + 1:end])
        if re.search(r"^\s*block\s*=", body, re.M):
            continue
        lines.insert(start + 1, " " * (indent + 2) + "block = '%s'" % bulk)
    return "\n".join(lines)


def sub_block(txt, name, new_block):
    m = block_of(txt, name)
    if not m:
        return txt, False
    return txt[:m.start()] + new_block.rstrip("\n") + txt[m.end():], True


def add_line_into(txt, sp, line):
    """把一行插进某个块的**内部**（紧挨着它的收尾 [] 之前）。

    ⚠ 第一版是直接 `sp.group(1) + "\\n" + line`，那等于插到块**外面**去了
      ⇒ MOOSE 报 `parameter 'Variables/block' supplied multiple times`。
    """
    lines = sp.group(1).split("\n")
    for k in range(len(lines) - 1, -1, -1):
        if lines[k].strip() == "[]":
            lines.insert(k, line)
            break
    else:
        raise SystemExit("块里找不到收尾 []：" + lines[0])
    return txt[:sp.start()] + "\n".join(lines) + txt[sp.end():]


def set_param(body, name, value):
    """改块里**非注释行**的某个参数（注释里也会出现同样的字样，不能一律 replace）。"""
    lines = body.split("\n")
    pat = re.compile(r"^(\s*)" + re.escape(name) + r"\s*=")
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("#"):
            continue
        m = pat.match(ln)
        if m:
            lines[i] = "%s%s = %s" % (m.group(1), name, value)
            return "\n".join(lines), True
    return body, False


S_ETA2 = "(gr0^2+gr1^2+gr2^2+gr3^2+gr4^2+gr5^2+gr6^2+gr7^2)"
Q_ETA4 = "(gr0^4+gr1^4+gr2^4+gr3^4+gr4^4+gr5^4+gr6^4+gr7^4)"
H_SOLID = "min(1, 2*%s)" % S_ETA2
H_GB = "8*(%s^2 - %s)" % (S_ETA2, Q_ETA4)
ALLETA = "gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7"


def load_gb_x():
    xs = []
    with open(SEEDS, newline="") as f:
        for row in csv.DictReader(f):
            xs.append(float(row["x"]))
    xs.sort()
    mid = [0.5 * (xs[i] + xs[i + 1]) for i in range(len(xs) - 1)]
    return [x for x in mid if XMIN < x < XMAX]


def mesh_block(gb_x):
    nslab = len(gb_x) + 1
    pool_block = nslab
    L = []
    a = L.append
    a("[Mesh]")
    a("  # =========================================================")
    a("  # 【Gibbs3D】3D 域 + 柱状晶块 + 每条晶界一个低维块")
    a("  #   晶界位置 = columnar_seeds.csv 相邻种子的中点（= 生产的 Voronoi 胞界）")
    for k, x in enumerate(gb_x):
        a("  #     晶界 %d : x = %.4f um" % (k, x * 1e6))
    a("  #   块号：slab k = block k（k=0..%d）；熔池 = block %d" % (nslab - 1, pool_block))
    a("  #   块只在**初始固相**里切（先切块、后切熔池）=> 面块自动避开液相")
    a("  # =========================================================")
    a("  [gen]")
    a("    type = GeneratedMeshGenerator")
    a("    dim = %d" % (2 if DIM2 else 3))
    a("    nx = %d" % NX)
    a("    ny = %d" % NY)
    if not DIM2:
        a("    nz = %d" % NZ)
    a("    xmin = %.10g" % XMIN)
    a("    xmax = %.10g" % XMAX)
    a("    ymin = %.10g" % YMIN)
    a("    ymax = %.10g" % YMAX)
    if not DIM2:
        a("    zmin = %.10g" % ZMIN)
        a("    zmax = %.10g" % ZMAX)
    a("    elem_type = %s" % ("QUAD4" if DIM2 else "HEX8"))
    a("  []")
    if DISP and not DIM2:
        a("  # 零位移的位移系统（p3c 原型里有）—— 见文件头 DISP 说明")
        a("  displacements = 'disp_x disp_y disp_z'")
    prev = "gen"
    for k in range(1, nslab):
        lo = gb_x[k - 1]
        hi = gb_x[k] if k < len(gb_x) else XMAX
        a("  [slab%d]" % k)
        a("    type = SubdomainBoundingBoxGenerator")
        a("    input = %s" % prev)
        a("    block_id = %d" % k)
        a("    block_name = slab%d" % k)
        # ⚠ libMesh 的 VectorValue 参数**永远要 3 个分量**（2D 也要给 z=0）
        a("    bottom_left = '%.10g %.10g %.10g'" % (lo, YMIN, ZMIN))
        a("    top_right   = '%.10g %.10g %.10g'" % (hi, YMAX, ZMAX))
        a("  []")
        prev = "slab%d" % k
    a("  # 初始熔池（t=0 时 T>%.6g K 的区域，见 TPOOL）—— 只用于把 eta 初值置零" % TPOOL)
    a("  [liquid_pool]")
    a("    type = ParsedSubdomainMeshGenerator")
    a("    input = %s" % prev)
    if DIM2:
        a("    combinatorial_geometry = '0.222817/sqrt((x+%.8g)^2+y^2+1e-10)"
          "*exp(-50000*(sqrt((x+%.8g)^2+y^2+1e-10)+x+%.8g)) > %.6g'"
          % (XOFF, XOFF, XOFF, TPOOL))
    else:
        a("    combinatorial_geometry = '0.222817/sqrt((x+%.8g)^2+y^2+z^2+1e-10)"
          "*exp(-50000*(sqrt((x+%.8g)^2+y^2+z^2+1e-10)+x+%.8g)) > %.6g'"
          % (XOFF, XOFF, XOFF, TPOOL))
    a("    block_id = %d" % pool_block)
    a("    block_name = liquid")
    a("  []")
    prev = "liquid_pool"
    # 对照组（NO_GIBBS）不建晶界 sideset / 低维块：
    #   没有 Gam 变量时，低维块上没有任何核 -> MOOSE 直接报
    #   "Each subdomain must contain at least one Kernel"。
    for k in range(len(gb_x) if not NO_GIBBS else 0):
        a("  [gb%d_ss]" % k)
        a("    type = SideSetsBetweenSubdomainsGenerator")
        a("    input = %s" % prev)
        a("    primary_block = %d" % k)
        a("    paired_block = %d" % (k + 1))
        a("    new_boundary = gb%d" % k)
        a("  []")
        prev = "gb%d_ss" % k
    for k in range(len(gb_x) if not NO_GIBBS else 0):
        a("  [gb%d_ld]" % k)
        a("    type = LowerDBlockFromSidesetGenerator")
        a("    input = %s" % prev)
        a("    sidesets = 'gb%d'" % k)
        a("    new_block_id = %d" % (100 + k))
        a("    new_block_name = gbb%d" % k)
        a("  []")
        prev = "gb%d_ld" % k
    # ★ 2026-09-20：【两侧各一个低维块】—— MOOSE 对"两侧界面"的标准写法。
    #   只用**一个**低维块时（secondary_subdomain == primary_subdomain == gbb）实测：
    #   约束只算出了 Lower（面）那一侧，Secondary/Primary（体相）那一侧
    #   `test_space_size == 0`（体相变量在那个"二次侧单元"上没有自由度）
    #   ⇒ 面在拿溶质、体相没丢 ⇒ **不守恒**（实测差 1.8e5 倍）。
    # 只有 mortar 方案才需要"一次侧"的低维块；STAGGER 方案不需要它
    # （实测：留着会让那些块"没有核" ⇒ MOOSE 直接报错）
    if not NO_GIBBS and TWOSIDE and not STAGGER:
        for k in range(len(gb_x)):
            a("  [gb%d_ssb]" % k)
            a("    type = SideSetsBetweenSubdomainsGenerator")
            a("    input = %s" % prev)
            a("    primary_block = %d" % (k + 1))
            a("    paired_block = %d" % k)
            a("    new_boundary = gb%db" % k)
            a("  []")
            prev = "gb%d_ssb" % k
        for k in range(len(gb_x)):
            a("  [gb%d_ldb]" % k)
            a("    type = LowerDBlockFromSidesetGenerator")
            a("    input = %s" % prev)
            a("    sidesets = 'gb%db'" % k)
            a("    new_block_id = %d" % (110 + k))
            a("    new_block_name = gbb%db" % k)
            a("  []")
            prev = "gb%d_ldb" % k
    a("[]")
    return "\n".join(L), nslab, pool_block


def main():
    with open(SRC, encoding="utf-8", newline="") as f:
        txt = f.read()
    orig_lines = txt.count("\n")
    report = []

    gb_x = load_gb_x()
    if not gb_x:
        raise SystemExit("窗口里一条晶界都没有，检查 XMIN/XMAX")
    ngb = len(gb_x)

    mesh, nslab, pool_block = mesh_block(gb_x)
    slab_blocks = list(range(nslab))
    # TISO 时熔池判据被关掉 => block 3 在网格上不存在，不能写进 block 列表
    bulk = " ".join(str(b) for b in slab_blocks) + ("" if TISO else " %d" % pool_block)
    gb_blocks = ["gbb%d" % k for k in range(ngb)]
    txt, ok = sub_block(txt, "Mesh", mesh)
    report.append(("Mesh -> 3D+Gibbs", ok))

    # ---- 温度场 -> 3D ----
    if DISP:
        # 零位移函数 + 三个位移 AuxVariable/AuxKernel（照抄 p3c 的写法）
        m = block_of(txt, "Functions")
        txt = add_line_into(txt, m, "\n".join([
            "  [zero_fn]",
            "    type = ParsedFunction",
            "    expression = '0'",
            "  []"]))
        m = block_of(txt, "AuxVariables")
        txt = add_line_into(txt, m, "\n".join([
            "  [disp_x]", "  []", "  [disp_y]", "  []", "  [disp_z]", "  []"]))
        m = block_of(txt, "AuxKernels")
        txt = add_line_into(txt, m, "\n".join([
            "  [disp_x_k]", "    type = FunctionAux", "    variable = disp_x",
            "    function = zero_fn", "    use_displaced_mesh = false",
            "    execute_on = 'initial timestep_end'", "  []",
            "  [disp_y_k]", "    type = FunctionAux", "    variable = disp_y",
            "    function = zero_fn", "    use_displaced_mesh = false",
            "    execute_on = 'initial timestep_end'", "  []",
            "  [disp_z_k]", "    type = FunctionAux", "    variable = disp_z",
            "    function = zero_fn", "    use_displaced_mesh = false",
            "    execute_on = 'initial timestep_end'", "  []"]))
        report.append(("零位移系统（p3c 同款）", True))
    m = block_of(txt, "Functions")
    if m:
        body = m.group(1)
        body2 = body.replace("(x+1.2e-4-0.6*t)^2+y^2", "(x+1.2e-4-0.6*t)^2+y^2+z^2")
        if DIM2:   # 2D：不加 z
            body2 = body
        txt = txt[:m.start()] + body2 + txt[m.end():]
        report.append(("laser_T -> 3D", body2 != body))
    if TSNAP != "":
        m = block_of(txt, "laser_T")
        # 把 `1.2e-4-0.6*t` **整体**换成一个常数（= XOFF = x - x_s），
        # 不要只换 `0.6*t`（那会写出 `1.2e-4--9.5e-05` 这种双重减号）
        body2 = m.group(1).replace("1.2e-4-0.6*t", "%.10g" % XOFF)
        ok = (body2 != m.group(1))
        if not ok:
            raise SystemExit("TSNAP：laser_T 里没找到 '1.2e-4-0.6*t'，无法冻结温度场")
        txt = txt[:m.start()] + body2 + txt[m.end():]
        report.append(("TSNAP=%s s：温度场冻结为静态 3D 场（点源固定在 x_s=%.6g m）"
                       % (TSNAP, 1.2e-4 - XOFF), True))
    if TDECAY != "":
        tau = float(TDECAY)
        m = block_of(txt, "laser_T")
        body = m.group(1)
        body2, n = re.subn(
            r"(expression = ')([^']*)(')",
            lambda mm: mm.group(1)
            + ("353 + ( %s - 353 )*exp(-t/%.10g)" % (mm.group(2), tau))
            + mm.group(3), body, count=1)
        if n != 1:
            raise SystemExit("TDECAY：没能包裹 laser_T 的 expression")
        txt = txt[:m.start()] + body2 + txt[m.end():]
        report.append(("TDECAY=%s s：过热度按 exp(-t/tau) 衰减"
                       "（熔池将在 t≈%.3g s 消失，之后全固态）" % (TDECAY, 0.60 * tau), True))
    if TISO:
        m = block_of(txt, "laser_T")
        body2, ok = set_param(m.group(1), "expression", "'%s'" % TISO)
        if not ok:
            raise SystemExit("TISO：没能把 laser_T 换成常数")
        txt = txt[:m.start()] + body2 + txt[m.end():]
        # 熔池子域判据 -> 恒假（否则会在等温固相里凭空挖出一个"液相"块）
        m = block_of(txt, "liquid_pool")
        body2, ok = set_param(m.group(1), "combinatorial_geometry", "'1 > 2'")
        if not ok:
            raise SystemExit("TISO：没能关掉 liquid_pool 判据")
        txt = txt[:m.start()] + body2 + txt[m.end():]
        report.append(("TISO = %s K（等温固相对照，无熔池）" % TISO, True))

    # ---- 体相对象的 block 限制 ----
    for sec in ("Kernels", "Materials", "AuxKernels"):
        m = block_of(txt, sec)
        if not m:
            report.append(("block: " + sec, False))
            continue
        skip = ("T_field",) if sec == "AuxKernels" else ()
        if sec == "Materials":
            # kex **故意**不加 block（mortar 积分点不在 gbb 上，加了会静默取 0）
            skip = ("kex",)
        body2 = restrict_section(m.group(1), bulk, indent=2, skip=skip)
        txt = txt[:m.start()] + body2 + txt[m.end():]
        report.append(("block: " + sec, True))

    # ---- 变量 / 初值 / action ----
    for name in ("PolycrystalVariables", "c", "w"):
        m = block_of(txt, name)
        if not m:
            report.append(("var " + name, False))
            continue
        if name == "c" and CVAR_ON_LD:
            body2, ok = set_param(m.group(1), "block",
                                  "'%s' " % bulk + " ".join(gb_blocks))
            if not ok:   # 生产里 [c] 本来没有 block 行 -> 直接插一行
                body2 = add_line_into(txt, m, "    block = '%s %s'"
                                      % (bulk, " ".join(gb_blocks)))
                txt = body2
                report.append(("var c 也定义在低维块上（试验）", True))
                continue
            txt = txt[:m.start()] + body2 + txt[m.end():]
            report.append(("var c 也定义在低维块上（试验）", True))
            continue
        if re.search(r"^\s*block\s*=", m.group(1), re.M):
            report.append(("var " + name, "已有限制"))
            continue
        txt = add_line_into(txt, m, "    block = '%s'" % bulk)
        report.append(("var " + name, True))

    m = block_of(txt, "GrainGrowth")
    if m:
        txt = add_line_into(txt, m, "      block = '%s'" % bulk)
        report.append(("GrainGrowth block", True))

    m = block_of(txt, "PolycrystalColoringIC")
    if m:
        _icb = bulk if ICALL else " ".join(str(b) for b in slab_blocks)
        body = m.group(1).replace("block = 0", "block = '%s'" % _icb)
        txt = txt[:m.start()] + body + txt[m.end():]
        report.append(("PolycrystalColoringIC block = '%s'" % _icb, True))
    for name in ("c_init", "w_init"):
        m = block_of(txt, name)
        if m:
            txt = add_line_into(txt, m, "    block = '%s'" % bulk)
            report.append(("IC " + name, True))

    # ---- 溶质那一层：换成 Gibbs 版 ----
    fe = [
        "  [free_energy]",
        "    # =====================================================================",
        "    # 【Gibbs 版】体相自由能 —— 物理量纲、理想溶液、**没有晶界偏析项**",
        "    #   f = FREF*{ (T/TREF)*[c*ln c+(1-c)*ln(1-c)] - (-ln k)*c*(1-h_solid) }",
        "    #   生产原式: k_c/2*(c-c0)^2 + A_part*c^2*min(1,2S) + (Omega0/wgb)*(c-c0)*h_gb",
        "    #   => 后两项是「弥散晶界偏析」，已被面上的 Gamma 取代（删掉，避免双计）",
        "    #   与生产的第二处差别：**本式依赖 T**（生产完全不依赖 T）",
        "    # ---------------------------------------------------------------",
        "    # 【2026-09-21 根因修复】max(c,CFLOOR) 截断 -> C^2 抛物线正则化",
        "    #   截断的两个**实测**后果：",
        "    #     (1) f_cc 在 c<CFLOOR 处掉到 0         -> c 方程的行退化",
        "    #     (2) M ∝ max(c,CFLOOR) 在 c=CFLOOR 处**跳变 10^6 倍**",
        "    #   而 {c<CFLOOR} 是**子网格尺度、随时间乱动**的集合",
        "    #     -> 离散通量在那里不可微 -> 牛顿残差冻在非零地板",
        "    #     （实测：2D 熔池 t=1.27e-7 后 |R| = 2.375117e-05 逐位冻结；",
        "    #       去掉 Gibbs 面的对照 k1ng 同样在 t=1.27e-7 停）",
        "    #   修法是**纯数值**的：c>=C1 与理想溶液逐字相同，只在 c<C1 与",
        "    #   c>C2 用匹配 g,g',g'' 的抛物线外推 -> C^1+C^2、无跳变、",
        "    #   雅可比完整、g''>0 由构造保证。ε 收敛性见报告 §12。",
        "    #   `if()` 导数行为已实测（取活跃分支；非活跃分支的 NaN 不污染）；",
        "    #   `max()` 在夹紧处把导数置 0 —— 这正是本条要绕开的。",
        "    # =====================================================================",
        "    type = DerivativeParsedMaterial",
        "    property_name = f_loc",
        "    block = '%s'" % bulk,
        "    coupled_variables = 'c T %s'" % ALLETA,
        "    constant_names = 'FREF TREF KPART C1 C2 G1 GP1 GPP1 G2 GP2 GPP2'",
        "    constant_expressions = '%.6e %.6e %.6g %.6e %.6g %.10e %.10e %.10e %.10e %.10e %.10e'"
        % (FREF, TREF, KPART, C1, C2, G1, GP1, GPP1, G2, GP2, GPP2),
        "    expression = 'FREF*( (T/TREF)*(%s) - (-log(KPART))*c*(1-%s) )'"
        % (G_EXPR, H_SOLID),
        "    derivative_order = 2",
        "  []",
    ]
    txt, ok = sub_block(txt, "free_energy", "\n".join(fe))
    report.append(("free_energy(Gibbs)", ok))

    mo = [
        "  [solute_mobility]",
        "    # =====================================================================",
        "    # 【Gibbs 版】M = D_eff / f_cc  => D = M*f_cc **逐点精确**",
        "    #   f_cc = FREF*(T/TREF)*g''(c)              （J/m^3；g'' 见 [free_energy]）",
        "    #   D_eff = D_L + (D_S-D_L)*h_solid + (D_GB-D_S)*h_gb",
        "    # => 审计 P0-4（固相扩散反比液相快 1.59 倍）由构造消除",
        "    # ⚠ g'' 与 [free_energy] 用的是**同一套** C1/C2/GPP1/GPP2 常数，",
        "    #   所以 D = M*f_cc 仍是恒等式，f_cc>0 / M>0 由构造保证 ——",
        "    #   不再需要 max(c,CFLOOR) 那种会**跳变 10^6 倍**的截断。",
        "    # =====================================================================",
        "    type = DerivativeParsedMaterial",
        "    property_name = M",
        "    block = '%s'" % bulk,
        "    coupled_variables = 'c T %s'" % ALLETA,
        "    constant_names = 'D_L D_S D_GB FREF TREF C1 C2 GPP1 GPP2'",
        "    constant_expressions = '1.2e-06 4e-13 4e-10 %.6e %.6e %.10e %.10e %.10e %.10e'"
        % (FREF, TREF, C1, C2, GPP1, GPP2),
        "    expression = '(D_L + (D_S-D_L)*(%s) + (D_GB-D_S)*(%s))"
        " / (FREF*(T/TREF)*(%s))'" % (H_SOLID, H_GB, GPP_EXPR),
        "    derivative_order = 2",
        "  []",
    ]
    txt, ok = sub_block(txt, "solute_mobility", "\n".join(mo))
    report.append(("solute_mobility(Gibbs)", ok))

    # ---- κ_c 单因素可调（判断停滞是否来自固液前沿欠解析）----
    if abs(KAPC - 1.0e-14) > 1e-30:
        m = block_of(txt, "ch_kappa")
        if m:
            body2, ok = set_param(m.group(1), "prop_values", "'%.6e'" % KAPC)
            if ok:
                txt = txt[:m.start()] + body2 + txt[m.end():]
            report.append(("kappa_c -> %.3e" % KAPC, ok))

    # 【2026-09-23 物理正确化】抗截留电流 susceptibility（替换掉旧式）
    #   Plapp PRE 84 031601 (2011) 式(102):
    #       j_at = -a W (c_l - c_s) (dphi/dt) grad(phi)/|grad(phi)|
    #   MOOSE 的 AntitrappingCurrent 实现的是  j_at = F (grad v/|grad v|) dv/dt
    #   =>  F = a W [ c_l(mu) - c_s(mu) ]                       （a > 0）
    #   【旧式两处错】
    #     (1) 用 (1-k_eq)*c 当 Delta c 的替身。Delta c 必须由**局部 mu** 解出两相
    #         平衡成分之差：
    #         本分支 f = FREF[(T/TREF) g(c) - (-ln KPART) c (1-h_solid)], g' = ln(c/(1-c))
    #         => mu/FREF = (T/TREF) ln(c/(1-c)) + ln(KPART)(1-h_solid)
    #         => a_s = (c/(1-c)) exp( ln(KPART)(1-h_solid) TREF/T ),  c_s = a_s/(1+a_s)
    #            a_l = a_s exp( -ln(KPART) TREF/T ),                 c_l = a_l/(1+a_l)
    #            Delta c = c_l - c_s
    #         校核：T=TREF 时 a_l/a_s = 1/KPART => c_s/c_l = KPART ✓
    #     (2) W 用了冻结的 2e-6。W 必须是**本模型真实的界面宽** = wGB（见 AT_W）。
    #   门 (1-h_gb)：固液前沿 h_gb = 0 -> 门 = 1（保留）；
    #                固-固晶界 h_gb = 1 -> 门 = 0。
    #     物理理由：Karma-Rappel 电流的前提是"界面两侧存在分配系数"；
    #     固-固晶界 k = 1，该电流在此处无定义（且 h_gb 项对 mu 的贡献会被双重计入）。
    _as_ = "((c/(1-c))*exp(log(KPART)*(1-" + H_SOLID + ")*(TREF/T)))"
    _al_ = "(" + _as_ + "*exp(-log(KPART)*(TREF/T)))"
    _dc_ = "((" + _al_ + "/(1+" + _al_ + "))-(" + _as_ + "/(1+" + _as_ + ")))"
    at = [
        "  [at_susc]",
        "    type = DerivativeParsedMaterial",
        "    property_name = F_at",
        "    block = '%s'" % bulk,
        "    coupled_variables = 'c w T %s'" % ALLETA,
        "    constant_names = 'A_AT W KPART TREF'",
        "    constant_expressions = '%.6g %.6e %.6g %.6e'" % (AT_A, AT_W, KPART, TREF),
        "    expression = 'A_AT*W*" + _dc_ + "*(1-(" + H_GB + ")) + 0*w'",
        "    derivative_order = 2",
        "  []",
    ]
    txt, ok = sub_block(txt, "at_susc", "\n".join(at))
    report.append(("at_susc(物理正确 aW Delta c)", ok))

    # 8 个抗截留核的 coupled_variables 必须与新 [at_susc] 逐字一致（新增 T）
    for _i in range(8):
        _m = block_of(txt, "gr%d_antitrap" % _i)
        if _m:
            _b, _ok = set_param(_m.group(1), "coupled_variables", "'c T %s'" % ALLETA)
            if _ok:
                txt = txt[:_m.start()] + _b + txt[_m.end():]
            report.append(("at kernel gr%d cv+T" % _i, _ok))

    # ---- 5b. 雅可比缺项修复 ----------------
    # Gibbs 版把 M 和 f_loc 的依赖扩到了 **c 与 T**（生产里 M 不依赖 c、f_loc 不依赖 T）。
    # MOOSE 的 SplitCHParsed / SplitCHWRes 都是
    #     cvar = mapJvarToCvar(jvar);  (*_dXdarg[cvar])[_qp]
    # 而 _dXdarg 是按**材料** coupled_variables 的顺序索引的
    #   （SplitCHWResBase.h: `_dmobdarg[i] = getMaterialPropertyDerivative(_mob_name, i)`）。
    # ⇒ **核的 coupled_variables 顺序必须与材料逐字一致**，否则 ∂M/∂c 整块静默丢失
    #   （就是审计 P0-1 / 本项目教训 1 的同一类缺陷）。
    # 实测证据：地板残差集中在 c 方程（3.48e-9），且与 dt 完全无关（纯空间不一致）。
    args_full = "c T %s" % ALLETA
    for kern in ("coupled_res", "coupled_parsed"):
        m = block_of(txt, kern)
        if not m:
            report.append(("雅可比: " + kern, False))
            continue
        body2, ok = set_param(m.group(1), "coupled_variables", "'%s'" % args_full)
        if not ok:
            report.append(("雅可比: " + kern, False))
            continue
        txt = txt[:m.start()] + body2 + txt[m.end():]
        report.append(("雅可比: %s <- '%s'" % (kern, args_full), True))

    # ---- 5c. wGB 重标定（只有 WGB != 4 µm 时才动）----
    # 判据：σ = 0.6 J/m^2 必须**逐位不变**。三条关系（生产 gen/check 工具用的同一组）：
    #   mu0   = 6*σ/wGB
    #   κ_op  = 0.75*σ*wGB          （a* = 0.75 是与 gamma_asymm 配套的不动点）
    #   L     = 4/3*M_GB/wGB        （[L_mobility] 里的常数 wGB）
    #   还有 Voronoi 的 int_width 必须跟着 wGB（它决定 η 初值的界面宽度）
    if abs(WGB - 4.0e-6) > 1e-12:
        mu0 = 6.0 * SIGMA_GB / WGB
        kap = 0.75 * SIGMA_GB * WGB
        rep_wgb = []
        for name, val in (("mu_barrier_const", None), ("consts", None),
                          ("L_mobility", None), ("voronoi", None)):
            mm = block_of(txt, name)
            if not mm:
                rep_wgb.append((name, False))
                continue
            body = mm.group(1)
            if name == "mu_barrier_const":
                body2, ok = set_param(body, "prop_values", "'%.6g'" % mu0)
            elif name == "consts":
                body2, ok = set_param(body, "prop_values", "'%.6g    1.5'" % kap)
            elif name == "L_mobility":
                body2, ok = set_param(body, "constant_expressions",
                                      "'232 3.234 8.617e-5 %.6g'" % WGB)
            else:
                body2, ok = set_param(body, "int_width", "%.6g" % WGB)
            if ok:
                txt = txt[:mm.start()] + body2 + txt[mm.end():]
            rep_wgb.append((name, ok))
        report.append(("wGB %.4g -> %.4g (mu0=%.6g, kappa=%.6g, sigma=%.3g)"
                       % (4.0e-6, WGB, mu0, kap, SIGMA_GB),
                       all(ok for _, ok in rep_wgb)))
        for nm, ok in rep_wgb:
            if not ok:
                report.append(("   重标定失败: " + nm, False))

    # ---- 预条件子切换 + 对照组提前返回 ----
    m = block_of(txt, "Executioner")
    ex = m.group(1)
    if AUTOSC:
        ex2, ok = set_param(ex, "automatic_scaling", "true")
        if ok:
            ex = ex2
            report.append(("automatic_scaling = true（平衡各行残差）", True))
        else:
            # [Executioner] 里没有这一行 -> 插在 solve_type 之后
            ex = re.sub(r"(\n(\s*)solve_type\s*=\s*\w+)",
                        r"\1\n\2automatic_scaling = true", ex, count=1)
            report.append(("automatic_scaling = true（插入）",
                           "automatic_scaling" in ex))
    if PRECOND == "mumps":
        ex2 = re.sub(r"petsc_options_iname = '[^']*'",
                     "petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'", ex)
        ex2 = re.sub(r"petsc_options_value = '[^']*'",
                     "petsc_options_value = 'lu       mumps'", ex2)
        if ex2 == ex:
            raise SystemExit("没能把 Executioner 的 petsc options 换成 mumps —— 检查正则")
        ex = ex2
        report.append(("预条件子 lu+mumps", True))
    else:
        report.append(("预条件子 asm/ilu（生产）", True))
    if NL_ABS_TOL:
        ex2, n = re.subn(r"\n(\s*)(nl_abs_tol\s*=\s*)[0-9.eE+-]+",
                         "\n\\g<1>\\g<2>%s" % NL_ABS_TOL, ex)
        if n != 1:
            raise SystemExit("没能改 nl_abs_tol —— 检查正则")
        ex = ex2
        report.append(("nl_abs_tol -> %s（实测地板 3.5e-9 之上）" % NL_ABS_TOL, True))
    if DTMAX:
        ex2, n = re.subn(r"\n(\s*)(dtmax\s*=\s*)[0-9.eE+-]+",
                         "\n\\g<1>\\g<2>%s" % DTMAX, ex)
        if n != 1:
            raise SystemExit("没能改 dtmax —— 检查正则")
        ex = ex2
        report.append(("dtmax -> %s（按 dx 缩下来）" % DTMAX, True))
    txt = txt[:m.start()] + ex + txt[m.end():]

    # ---- 低维 Gamma：变量 / 方程 / mortar 交换 / 材料 ----
    # ⚠ 对照组（NO_GIBBS=1）要走到**最后**才对：它仍然需要后面那些
    #   "生产后处理器加 block" 的修补，否则连启动都过不了。
    m = block_of(txt, "Variables")
    gv = ["  # =====================================================================",
          "  # 【Gibbs 面】每条晶界一个独立的低维状态量 Gam_k = Gamma_k / A_s",
          "  #   初值 = c0 => 面上恰好处于局域平衡 => t=0 交换通量为 0（避免启动冲击）",
          "  # ====================================================================="]
    for k in range(ngb):
        gv += ["  [Gam%d]" % k, "    block = '%s'" % gb_blocks[k],
               ]
        if not GAMSTEP:
            gv += ["    initial_condition = %.6g" % (float(GAMIC) if GAMIC else C0)]
        if GAM_SCALE:
            gv += ["    scaling = %s" % GAM_SCALE]
        gv += ["  []"]
    if not NO_GIBBS:
        txt = add_line_into(txt, m, "\n".join(gv))
        report.append(("Variables +Gam", True))
    # 【S11 拖曳 / T5 吸附】都要把面 Γ 投影到体相节点
    if (DRAG or T5) and not NO_GIBBS:
        mv = block_of(txt, "AuxVariables")
        txt = add_line_into(txt, mv, "\n".join([
            "  # 【S11 拖曳 / T5 吸附】面上的 Γ/A_s 投影到体相节点（由 GBStaggeredUpdate 填）",
            "  [gamgb]", "    order = FIRST", "    family = LAGRANGE",
            "    block = '%s'" % bulk, "  []"]))
        # 把投影名告诉 UO
        m_uo = block_of(txt, "gb_stagger") or block_of(txt, "gb_sink")
        if m_uo and not DRAG:      # DRAG 分支里已经加过一次，避免重复
            txt = add_line_into(txt, m_uo, "    gamgb_name = gamgb")
        report.append(("【T5/拖曳】投影变量 gamgb 就绪", True))
    if DRAG and not NO_GIBBS:
        # 把 AllenCahn / GrainGrowth 的迁移率从 L 换成 L_eff（语法级替换，逐处可见）
        n1 = txt.count("mob_name = L\n") + txt.count("mob_name = L ")
        txt = re.sub(r"(mob_name\s*=\s*)L(\s*(?:\n|$))", r"\1L_eff\2", txt)
        txt2, k2 = re.subn(r"(mobility\s*=\s*)L(\s*(?:\n|$))", r"\1L_eff\2", txt)
        txt = txt2
        # ⚠ UO 是在**后面**才生成的（顺序！），所以 `gamgb_name` 不能在这里插，
        #   而是在生成 UO 时直接带上（见下面的 DRAG 分支）。
        report.append(("【S11 拖曳】投影变量 gamgb + L→L_eff（β=%.3g，占位值）" % BETA_DRAG,
                       txt.count("L_eff") > 0))
    # ⚠ GAMSTEP 的插入必须放在**所有用过的 span 之后**：span 是过期就会插错位置
    #   （实测踩过：把 [Functions]/[ICs] 的插入放在 [Variables] 插入之前，
    #    导致 m 这个旧 span 失效 ⇒ 生成出 `[g[Variables]` 这种坏文件）
    if GAMSTEP and not NO_GIBBS:
        gi = ["  [gamstep_fn]", "    type = ParsedFunction",
              "    expression = '0.018*(1-tanh((y-24e-6)/1e-6))'", "  []"]
        txt = add_line_into(txt, block_of(txt, "Functions"), "\n".join(gi))
        for k in range(ngb):
            gi = ["  [gam%d_step]" % k, "    type = FunctionIC",
                  "    variable = Gam%d" % k, "    function = gamstep_fn",
                  "    block = '%s'" % gb_blocks[k], "  []"]
            txt = add_line_into(txt, block_of(txt, "ICs"), "\n".join(gi))
        report.append(("GAMSTEP：沿晶界的 Γ 阶跃初值（S10 验证用）", True))

    m = block_of(txt, "Kernels")
    gk = ["  # =====================================================================",
          "  # 【Gibbs 面】面方程的时间导数项：(A_s/ρ_mol)*dGam/dt",
          "  #   面方程的其余部分（与体相的交换）由 mortar 约束 GBFluxExchange 提供",
          "  # ====================================================================="]
    for k in range(ngb):
        gk += ["  [gam%d_dt]" % k, "    type = ScaledTimeDerivative",
               "    variable = Gam%d" % k, "    block = '%s'" % gb_blocks[k],
               "    scale = AsRho", "  []"]
        if INPLANE:
            # 【S10】面内扩散：∇_s·(DGBeff·∇_s Gam)，DGBeff = A_s·D_GB/ρ_mol
            #   ⇒ 等效方程 ∂Gam/∂t = ∇_s·(D_GB ∇_s Gam)（面内，2D 单元上）
            gk += ["  [gam%d_inplane]" % k, "    type = MatDiffusion",
                   "    variable = Gam%d" % k, "    block = '%s'" % gb_blocks[k],
                   "    diffusivity = DGBeff", "  []"]
    if not NO_GIBBS:
        txt = add_line_into(txt, m, "\n".join(gk))
        report.append(("Kernels +gam_dt", True))

    m = block_of(txt, "Constraints")
    if m:
        m2 = re.compile(r"^\[\]", re.M).search(txt, m.end())
        at_pos = m2.start()
    else:
        # 生产输入里**没有** [Constraints] 段 —— 插在 [Preconditioning] 之前
        mp = re.search(r"^\[Preconditioning\]", txt, re.M)
        if not mp:
            raise SystemExit("既没有 [Constraints] 也没有 [Preconditioning]")
        at_pos = mp.start()
    gc = ["  # =====================================================================",
          "  # 【Gibbs 面】体相 <-> 面 的守恒通量交换（mortar，已在 3D 原型验证）",
          "  #   面侧:  -(K/2)[(c_sec-Gam)+(c_pri-Gam)]",
          "  #   体侧:  +(K/2)(c-Gam)   两侧各半 => 总量守恒",
          "  #   K = A_s*k_att/ρ_mol，随位置/时间的 T 变",
          "  # ====================================================================="]
    for k in range(ngb):
        if TWOSIDE:
            gc += ["  [gb%d_exchange]" % k, "    type = GBFluxExchange",
               "    variable = Gam%d" % k, "    secondary_variable = c",
               "    primary_variable = c", "    secondary_boundary = gb%d" % k,
               "    primary_boundary = gb%db" % k,
               # ★ 两侧各一个低维块（见 [Mesh] 里的说明）：
               #   二次侧 = 块 k 的面；一次侧 = 块 k+1 的面
               "    secondary_subdomain = %s" % gb_blocks[k],
               "    primary_subdomain = %sb" % gb_blocks[k],
               "    kex = kex"]
        else:
            gc += ["  [gb%d_exchange]" % k, "    type = GBFluxExchange",
               "    variable = Gam%d" % k, "    secondary_variable = c",
               "    primary_variable = c", "    secondary_boundary = gb%d" % k,
               "    primary_boundary = gb%d" % k,
               "    secondary_subdomain = %s" % gb_blocks[k],
               "    primary_subdomain = %s" % gb_blocks[k],
               "    kex = kex"]
        # ⚠ 不要设 `compute_primal_residuals = false`！实测：一设就**段错误**
        #   （ComputeMortarFunctor 后面仍会 cacheResidual/cacheResidualNeighbor，
        #    而没人填那两个局部向量 ⇒ 缓存到未初始化内存）。
        #   而且**留着也没关系**：它只有 ~1e-17/节点，比 GBSoluteSink 那一步的贡献
        #   （~6.6e-7 的 dc）小 11 个数量级 ⇒ 双计完全可忽略。
        gc += ["  []"]
    if STAGGER:
        # 交错方案：**不建 mortar 约束**，面↔体相的两条腿都在 GBStaggeredUpdate 里
        report.append(("Constraints：STAGGER=1 ⇒ 不建 mortar（避免强耦合）", True))
    elif not NO_GIBBS:
        if m:
            txt = txt[:at_pos] + "\n".join(gc) + "\n" + txt[at_pos:]
        else:
            txt = txt[:at_pos] + "[Constraints]\n" + "\n".join(gc) + "\n[]\n\n" + txt[at_pos:]
        report.append(("Constraints +exchange", True))

    # ---- 交错耦合的显式扣账对象 ----
    if not NO_GIBBS and (SINK or STAGGER):
        m = block_of(txt, "UserObjects")
        if STAGGER:
            gu = ["  # =================================================================",
                  "  # 【交错耦合】GBStaggeredUpdate：面推一步 + 体相按构造成比例扣账（双向，同一对象）",
                  "  #   面：Γ ← Γ_eq + (Γ_old − Γ_eq)·exp(−k_att·dt)，  Γ_eq = A_s(T)·c（McLean）",
                  "  #   体：Δc = −ΔM/(ρ_mol·V_int)，ΔM = Σ A_s·ΔΓ·w（界面节点的面积份额）",
                  "  #   ⇒ ρ_mol·Δ∫c dV + ΔM ≡ 0 **恒成立**，与非线性容差完全无关",
                  "  # =================================================================",
                  "  [gb_stagger]", "    type = GBStaggeredUpdate"]
        else:
            gu = ["  # =================================================================",
                  "  # 【交错耦合】GBSoluteSink：只把体相那一侧显式扣账（面侧仍走 mortar）",
                  "  # =================================================================",
                  "  [gb_sink]", "    type = GBSoluteSink"]
        gu += [
              "    gam_names = '%s'" % " ".join("Gam%d" % k for k in range(ngb)),
              "    gb_blocks = '%s'" % " ".join(gb_blocks),
              "    c_name = c", "    T_name = T",
              "    rho_mol = %.6f" % RHOMOL,
              "    gamma_mono = %.6e" % GAMMA_MONO,
              "    dh_seg = %.6e" % DH_SEG, "    ds_seg = %.6e" % DS_SEG,
              "    r_gas = 8.314462618"]
        if STAGGER:
            gu += ["    k_att = %.6e" % K_ATT]
        if DRAG or T5:
            # ⚠ UO 是**后面**才生成的 ⇒ 投影名必须在这里带（不能在前面按 span 插）
            gu += ["    # 【S11 拖曳 / T5 吸附】面上的 Γ 投影到这个体相 AuxVariable（由本对象填）",
                   "    gamgb_name = gamgb"]
        if AMR:
            gu += ["    # 【AMR】网格会变 ⇒ 每步重建界面节点表与 V_int",
                   "    always_rebuild = true"]
        gu += ["    execute_on = timestep_begin", "  []"]
        txt = add_line_into(txt, m, "\n".join(gu))
        report.append(("UserObjects +%s（交错耦合）"
                       % ("GBStaggeredUpdate" if STAGGER else "GBSoluteSink"), True))

    m = block_of(txt, "Materials")
    gm = ["  # =====================================================================",
          "  # 【Gibbs 面】面上的材料（只在低维块上）",
          "  #   A_s(T) = Γ0*K(T)，K(T)=exp(-ΔG_seg/(RT))，ΔG_seg = ΔH_seg - T*ΔS_seg",
          "  #   kex = A_s*k_att/ρ_mol  [m/s]",
          "  #   ΔS_seg = 0 是**缺口**（文献不存在），显式记账",
          "  # ====================================================================="]
    for k in range(ngb):
        gm += ["  [AsRho%d]" % k, "    type = DerivativeParsedMaterial",
               "    property_name = AsRho", "    block = '%s'" % gb_blocks[k],
               "    coupled_variables = 'T'",
               "    constant_names = 'GAM0 DHSEG DSSEG RGAS RHOMOL'",
               "    constant_expressions = '%.6e %.6e %.6e 8.314462618 %.6e'"
               % (GAMMA_MONO, DH_SEG, DS_SEG, RHOMOL),
               "    expression = 'GAM0*exp(-(DHSEG-DSSEG*T)/(RGAS*T))/RHOMOL'",
               "    derivative_order = 1", "  []",
               ]
        # 【S10】沿晶界的**面内扩散**用的等效扩散系数
        #   面方程（已乘 A_s/ρ_mol 缩放）：(A_s/ρ_mol)·∂Gam/∂t = ... + (A_s/ρ_mol)·∇_s·(D_GB ∇_s Gam)
        #   ⇒ MOOSE 侧的 diffusivity = AsRho·D_GB（单位 m·m²/s = m³/s，无单位检查）
        #   物理式：∂Γ/∂t = ∇_s·(D_GB ∇_s Γ)，Γ = δ·c_GB ⇒ 与 δ 无关（δ 均匀时）
        #   ⚠ D_GB 本身就是**指派值**（Ti64 无定量数据，见 §6 S7/参数缺口）——
        #     这里沿用生产 `[solute_mobility]` 里的 4e-10 m²/s，并显式记账。
        if INPLANE:
            gm += ["  [DGBeff%d]" % k, "    type = DerivativeParsedMaterial",
                   "    property_name = DGBeff",
                   "    block = '%s'" % gb_blocks[k],
                   "    coupled_variables = 'T'",
                   "    constant_names = 'GAM0 DHSEG DSSEG RGAS RHOMOL DGB'",
                   "    constant_expressions = '%.6e %.6e %.6e 8.314462618 %.6e %.6e'"
                   % (GAMMA_MONO, DH_SEG, DS_SEG, RHOMOL, D_GB),
                   "    expression = 'GAM0*exp(-(DHSEG-DSSEG*T)/(RGAS*T))*DGB/RHOMOL'",
                   "    derivative_order = 1", "  []"]
    if DRAG:
        gm += ["  [L_drag]", "    type = DerivativeParsedMaterial",
               "    property_name = L_eff",
               "    block = '%s'" % bulk,
               "    coupled_variables = 'T gamgb %s'" % ALLETA,
               "    material_property_names = 'L'",
               "    constant_names = 'BETA GAM0 DHSEG DSSEG RGAS'",
               "    constant_expressions = '%.6e %.6e %.6e %.6e 8.314462618'"
               % (BETA_DRAG, GAMMA_MONO, DH_SEG, DS_SEG),
               "    expression = 'L/(1 + BETA*GAM0*exp(-(DHSEG-DSSEG*T)/(RGAS*T))*gamgb*(%s))'"
               % H_GB,
               "    derivative_order = 2", "  []"]
    # ⚠ kex **只能有一个**（无 block 限制）：MortarNodal 的积分点在 mortar segment 网格上，
    #   限制到 gbb 上会静默取 0；而不限制时两个同名材料会在所有块上冲突（实测报错
    #   "declared on block 0 by multiple materials"）⇒ 只能共用一份。
    gm += ["  [kex]", "    type = DerivativeParsedMaterial",
               "    property_name = kex",
               # =============================================================
               # 【2026-09-20 关键修复】**绝不能**给 kex 加 block 限制！
               #   实测（GBFluxExchange 里加诊断打印）：
               #       sec=0.036 pri=0.036 lam=0  kex=0   <- 体相值对，kex 是 0
               #   原因：mortar 约束的积分点在**另一套 mortar segment 网格**上，
               #   它不属于 `gbb0` 这个子域 ⇒ 带 block 限制的材料在那里**求不出值，
               #   MOOSE 静默返回 0** ⇒ 交换通量恒为 0 ⇒ Γ 永远不动。
               #   p3c 原型用的是**无 block 限制**的 GenericConstantMaterial，所以它一直好。
               #   反例：AsRho 带 block 限制是**没问题**的，因为读它的是
               #   ScaledTimeDerivative（就装在同名低维块上）。
               # =============================================================
               "    # （故意不加 block：mortar 积分点不在 gbb%d 上，加了会静默取 0）" % k,
               "    coupled_variables = 'T'",
               "    constant_names = 'GAM0 DHSEG DSSEG RGAS RHOMOL KATT'",
               "    constant_expressions = '%.6e %.6e %.6e 8.314462618 %.6e %.6e'"
               % (GAMMA_MONO, DH_SEG, DS_SEG, RHOMOL, K_ATT),
               "    expression = 'GAM0*exp(-(DHSEG-DSSEG*T)/(RGAS*T))*KATT/RHOMOL'",
               "    derivative_order = 1", "  []"]
    if not NO_GIBBS:
        txt = add_line_into(txt, m, "\n".join(gm))
        report.append(("Materials +AsRho/kex", True))

    # ---- 【T5→C4】Gibbs 吸附：把 `mu` 属性换成随 Γ 变的版本 ----
    #   σ(Γ) = σ0 − R·T·Γ0·ln(1 + K(T)·c_GB)（Langmuir/Gibbs 积分形式）
    #   ⇒ mu = 6σ/wGB = mu0·(1 − h_gb·(R T Γ0/σ0)·ln(1+K·gamgb))
    #   ⚠ 属性名仍叫 `mu`：GrainGrowth action 的 ACGrGrPoly 与 f_grain 都**硬编码**这个名。
    #   ⚠⚠ 必须放在 `add_line_into(...gm)` **之后**：那个 `m` 是更早取的 span，
    #       先改文本再按旧 span 插入 ⇒ 新块被覆盖掉（本项目已在 span 上栽过三次）。
    if T5 and not NO_GIBBS:
        mmu = block_of(txt, "mu_barrier_const")
        new_mu = ["  [mu_barrier_gibbs]",
                  "    # 【T5→C4】Gibbs 吸附：偏析降低晶界能 ⇒ 长大驱动力变小（无未知系数）",
                  "    #   σ(Γ) = σ0 − R T Γ0 ln(1 + K(T)·c_GB) ⇒ mu = 6σ/wGB",
                  "    type = DerivativeParsedMaterial",
                  "    property_name = mu",
                  "    block = '%s'" % bulk,
                  "    coupled_variables = 'T gamgb %s'" % ALLETA,
                  "    constant_names = 'mu0 RGAS GAM0 SIGMA0 DHSEG DSSEG'",
                  "    constant_expressions = '%.6g 8.314462618 %.6e %.6g %.6e %.6e'"
                  % (6.0 * SIGMA_GB / WGB, GAMMA_MONO, SIGMA_GB, DH_SEG, DS_SEG),
                  "    expression = 'mu0*(1 - %.6g*(%s)*(RGAS*T*GAM0/SIGMA0)"
                  "*log(1 + exp(-(DHSEG-DSSEG*T)/(RGAS*T))*gamgb))'" % (T5_MULT, H_GB),
                  "    derivative_order = 2", "  []"]
        if mmu:
            txt = txt[:mmu.start()] + "\n".join(new_mu) + txt[mmu.end():]
            report.append(("【T5→C4】Gibbs 吸附：mu 随 Γ 变（Δσ/σ = 4.2%）", True))
        else:
            report.append(("【T5→C4】**没找到 mu_barrier_const**", False))

    # ---- 后处理：守恒 + 逐面 Gamma ----
    # ---- 【μ 探针】把 mu 属性导成场 + 极值（只用于诊断）----
    if MU_PROBE:
        mv = block_of(txt, "AuxVariables")
        txt = add_line_into(txt, mv, "\n".join([
            "  # 【μ 探针】mu 属性的场（MaterialRealAux，教训 19 认可的可靠版）",
            "  [mu_probe]", "    order = CONSTANT", "    family = MONOMIAL",
            "    block = '%s'" % bulk, "  []"]))
        ka = block_of(txt, "AuxKernels")
        txt = add_line_into(txt, ka, "\n".join([
            "  [mu_probe_k]", "    type = MaterialRealAux",
            "    variable = mu_probe", "    property = mu",
            "    block = '%s'" % bulk, "    execute_on = 'initial timestep_end'", "  []"]))
        mp = block_of(txt, "Postprocessors")
        txt = add_line_into(txt, mp, "\n".join([
            "  # 全场的极值：min 应出现在晶界（h_gb 最大处）、max 在晶粒内（=mu0）",
            "  [mu_min]", "    type = ElementExtremeValue",
            "    variable = mu_probe", "    block = '%s'" % bulk,
            "    value_type = min", "    execute_on = 'initial timestep_end'", "  []",
            "  [mu_max]", "    type = ElementExtremeValue",
            "    variable = mu_probe", "    block = '%s'" % bulk,
            "    value_type = max", "    execute_on = 'initial timestep_end'", "  []"]))
        report.append(("【μ 探针】ElementExtremeValue(mu_probe) min/max", True))
    # ⚠ 生产的 [Postprocessors] 全都没有 block 限制 ⇒ 会试图在低维块上求值，
    #   MOOSE 直接报 "The 'block' parameter of the object 'total_solute' must be a
    #   subset of the 'block' parameter of the variable 'c'"。
    #   先给生产已有的那些加上体相限制（少数几个不吃 block 的要跳过），再追加 Gibbs 的。
    m = block_of(txt, "Postprocessors")
    skip_pp = ("T_max", "dt", "n_elem", "n_nonlin", "n_lin")
    txt = txt[:m.start()] + restrict_section(m.group(1), bulk, indent=2, skip=skip_pp) + \
        txt[m.end():]
    m = block_of(txt, "Postprocessors")
    gp = ["  # =====================================================================",
          "  # 【Gibbs 面】守恒与逐面诊断",
          "  #   守恒量 = ρ_mol*∫c dV + A_s*Σ_k ∫Gam_k dA   [mol]",
          "  # =====================================================================",
          "  [c_int_pp]",
          "    type = ElementIntegralVariablePostprocessor",
          "    variable = c",
          "    block = '%s'" % bulk,
          "    execute_on = 'initial timestep_end'",
          "  []"]
    for k in range(ngb):
        gp += ["  [gam%d_int]" % k,
               "    type = ElementIntegralVariablePostprocessor",
               "    variable = Gam%d" % k, "    block = '%s'" % gb_blocks[k],
               "    execute_on = 'initial timestep_end'", "  []",
               "  [gam%d_max]" % k, "    type = NodalExtremeValue",
               "    variable = Gam%d" % k, "    block = '%s'" % gb_blocks[k],
               "    value_type = max", "    execute_on = 'timestep_end'", "  []",
               "  [gam%d_min]" % k, "    type = NodalExtremeValue",
               "    variable = Gam%d" % k, "    block = '%s'" % gb_blocks[k],
               "    value_type = min", "    execute_on = 'timestep_end'", "  []",
               "  [gb%d_area]" % k, "    type = AreaPostprocessor",
               "    boundary = 'gb%d'" % k,
               "    execute_on = 'initial timestep_end'", "  []"]
        # ★ 直接量面上的材料值 —— 用来判断「交换是不是死的」
        #   （p3c 里 kex/AsRho 是 GenericConstantMaterial；这里是 parsed 材料，
        #    必须确认它们在**低维块**上真的求出了非零值）
        gp += ["  [kex%d_int]" % k,
               "    type = ElementIntegralMaterialProperty",
               "    mat_prop = kex",
               "    block = '%s'" % gb_blocks[k],
               "    execute_on = 'initial timestep_end'", "  []",
               "  [AsRho%d_int]" % k,
               "    type = ElementIntegralMaterialProperty",
               "    mat_prop = AsRho",
               "    block = '%s'" % gb_blocks[k],
               "    execute_on = 'initial timestep_end'", "  []"]
    expr = "%.6f*c_int_pp" % RHOMOL
    names = "c_int_pp"
    for k in range(ngb):
        expr += " + %.6e*gam%d_int" % (GAMMA_MONO, k)
        names += " gam%d_int" % k
    gp += ["  # 总溶质量 [mol]：体相 + 所有晶界面",
           "  [solute_total]", "    type = ParsedPostprocessor",
           "    expression = '%s'" % expr, "    pp_names = '%s'" % names,
           "    execute_on = 'initial timestep_end'", "  []"]
    if not NO_GIBBS:
        txt = add_line_into(txt, m, "\n".join(gp))
        report.append(("Postprocessors +Gibbs", True))
    else:
        report.append(("NO_GIBBS 对照：跳过全部 Gibbs 面对象", True))

    # ---- 局部诊断：跨晶界的剖面 + 界面/远场贫化率 ----
    # ⚠ 为什么必须补：全局守恒量只有 ~10 ppm 的变化，**看不见**界面附近那层贫化
    #   （算例条件下该层 ~1 nm、贫化 ~40%）。判据不能只看全局积分。
    #   ⚠ LineValueSampler 每个时间步写一个 CSV（AGENTS.md 教训 25）⇒ 分析脚本必须
    #     按文件名里的时间步序号排序，不能用 os.listdir(...)[0]。
    gm2 = ["  # =====================================================================",
           "  # 【局部诊断】跨晶界的浓度剖面（全局积分看不到界面贫化层）",
           "  #   取样线：垂直于晶界、穿过它 ±10 µm；y/z 取在**固相**里",
           "  # ====================================================================="]
    for k, x in enumerate(gb_x):
        gm2 += ["  [profile_gb%d]" % k, "    type = LineValueSampler",
                "    variable = 'c T'",
                "    start_point = '%.10g %.10g %.10g'"
                % (x - 10e-6, 42e-6, 0.0 if DIM2 else 5e-6),
                "    end_point   = '%.10g %.10g %.10g'"
                % (x + 10e-6, 42e-6, 0.0 if DIM2 else 5e-6),
                "    num_points = 41", "    sort_by = x",
                "    execute_on = 'timestep_end'", "    outputs = csv", "  []"]
    if not NO_GIBBS:
        mp = re.search(r"^\[Preconditioning\]", txt, re.M)
        at_pos = mp.start() if mp else len(txt)
        txt = txt[:at_pos] + "[VectorPostprocessors]\n" + "\n".join(gm2) + "\n[]\n\n" + txt[at_pos:]
        report.append(("VectorPostprocessors +跨晶界剖面", True))

        # 界面处 vs 远场的贫化率（直接量"晶界抽走了多少"）
        m = block_of(txt, "Postprocessors")
        gd = ["  # =====================================================================",
              "  # 【局部诊断】晶界**处**的浓度 vs 体相平均浓度 ⇒ 贫化率",
              "  # ====================================================================="]
        for k in range(ngb):
            gd += ["  [c_at_gb%d]" % k, "    type = SideAverageValue",
                   "    variable = c", "    boundary = 'gb%d'" % k,
                   "    execute_on = 'initial timestep_end'", "  []",
                   "  [T_at_gb%d]" % k, "    type = SideAverageValue",
                   "    variable = T", "    boundary = 'gb%d'" % k,
                   "    execute_on = 'initial timestep_end'", "  []"]
        expr = " + ".join("c_at_gb%d" % k for k in range(ngb))
        gd += ["  [c_gb_mean]", "    type = ParsedPostprocessor",
               "    expression = '(%s)/%d'" % (expr, ngb),
               "    pp_names = '%s'" % " ".join("c_at_gb%d" % k for k in range(ngb)),
               "    execute_on = 'initial timestep_end'", "  []",
               "  # 贫化率 = 1 - c(界面)/c(体相平均)。晶界真的在抽溶质时它应显著 > 0",
               "  [depletion]", "    type = ParsedPostprocessor",
               "    expression = '1 - c_gb_mean/c_solid_avg'",
               "    pp_names = 'c_gb_mean c_solid_avg'",
               "    execute_on = 'initial timestep_end'", "  []"]
        txt = add_line_into(txt, m, "\n".join(gd))
        report.append(("Postprocessors +界面贫化率", True))

    # ---- 整段删掉 AMR ----
    # ⚠ 2026-09-20 实测教训：**`max_h_level = 0` 并**没有**关掉 AMR**。
    #   日志里每 2 步照样 "Adapting Mesh"，内存 921 MB -> 3162 -> 8484 MB，
    #   最后 **段错误**；而且每次适配之后都留下一份与 dt 无关的
    #   `|R| = 7.200000e-02`（糊状区节点）—— **mortar 约束 + AMR 是未验证组合**。
    #   ⇒ 3D Gibbs 版本**整段删除 [Adaptivity]**。要开 AMR 必须单独做一堵墙去验证。
    m = block_of(txt, "Adaptivity")
    if m and AMR:
        body = m.group(1).replace("max_h_level = 1", "max_h_level = %d" % AMR_LEVEL)
        body = body.replace("interval = 2", "interval = %d" % AMR_INTERVAL)
        txt = txt[:m.start()] + body + txt[m.end():]
        report.append(("【AMR】保留 Adaptivity（max_h_level=%d、interval=%d）—— mortar 已砍掉，可能可用"
                       % (AMR_LEVEL, AMR_INTERVAL), True))
    elif m:
        note = ("# =============================================================================\n"
                "# 【2026-09-20 实测删除】AMR 整段删掉，不是设 max_h_level = 0。\n"
                "#   实测：设 0 之后 MOOSE 照样每 2 步细化网格（内存 921->3162->8484 MB）\n"
                "#   并最终段错误；每次适配后留下与 dt 无关的 |R| = 7.2e-2。\n"
                "#   mortar 约束 + AMR 是**未验证组合**，必须单独验证后才能开。\n"
                "# =============================================================================\n")
        txt = txt[:m.start()] + note + txt[m.end():]
        report.append(("Adaptivity 整段删除（max_h_level=0 不管用，实测）", True))

    # ---- 诊断：整段删掉指定段 ----
    for sec in DROP:
        m = block_of(txt, sec)
        if not m:
            report.append(("DROP %s" % sec, False))
            continue
        txt = txt[:m.start()] + "# 【诊断】整段删除 [%s]\n" % sec + txt[m.end():]
        report.append(("DROP 段 [%s]" % sec, True))

    # ---- c_solid_avg 的块号 ----
    txt = txt.replace("  [c_solid_avg]\n    type = ElementAverageValue\n    variable = c\n    block = 0",
                      "  [c_solid_avg]\n    type = ElementAverageValue\n    variable = c\n"
                      "    block = '%s'" % " ".join(str(b) for b in slab_blocks))

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(txt)
    print("输入 %s" % SRC)
    print("输出 %s" % OUT)
    print("行数 %d -> %d" % (orig_lines, txt.count("\n")))
    print("晶界 %d 条：%s" % (ngb, ", ".join("%.4f um" % (x * 1e6) for x in gb_x)))
    print("体相块 '0..%d' + 熔池块 %d；面块 %s" % (nslab - 1, pool_block, gb_blocks))
    print()
    for name, ok in report:
        print("  %-28s %s" % (name, "OK" if ok is True else ("**未命中**" if ok is False else ok)))
    print()
    verify(ngb, bulk)


def verify(ngb, bulk):
    """**回读生成出来的文件**做自检 —— 不许只看"脚本打印了 OK"。"""
    with open(OUT, encoding="utf-8", newline="") as f:
        t = f.read()
    bad = []
    print("----- 回读自检 -----")
    # 1) 段必须齐全
    need = ["Mesh", "Functions", "Variables", "ICs", "UserObjects", "AuxVariables",
                "AuxKernels", "Kernels", "Modules", "Materials", "Postprocessors",
                "Preconditioning", "Executioner", "Outputs"]
    if not NO_GIBBS and not STAGGER:
        need.append("Constraints")
    for sec in need:
        sp = block_of(t, sec)
        print("  段 %-16s %s" % (sec, "有" if sp else "**缺**"))
        if not sp:
            bad.append("缺段 " + sec)
    # 2) 体相对象是否都加了 block
    for sec in ("Kernels", "Materials", "AuxKernels"):
        sp = block_of(t, sec)
        kids = direct_children(sp.group(1), 2)
        skip = ("T_field",) if sec == "AuxKernels" else ()
        if sec == "Materials":
            # kex 是**故意**不加 block 的（mortar 积分点不在 gbb 上，加了会静默取 0）
            skip = ("kex",)
        miss = [n for n, a, b in kids if n not in skip
                if not re.search(r"^\s*block\s*=", "\n".join(sp.group(1).split("\n")[a + 1:b]),
                                 re.M)]
        print("  %-10s 子对象 %2d 个，缺 block: %s（故意跳过 %s）"
              % (sec, len(kids), miss if miss else "无", list(skip) or "无"))
        if miss:
            bad.append("%s 缺 block: %s" % (sec, miss))
    # 3) Mesh 的关键内容
    mesh = block_of(t, "Mesh").group(1)
    for key in ("LowerDBlockFromSidesetGenerator", "SideSetsBetweenSubdomainsGenerator",
                "GeneratedMeshGenerator", "dim = 3"):
        print("  Mesh 里有 %-32s %s" % (key, "是" if key in mesh else "**否**"))
        if key not in mesh:
            bad.append("Mesh 缺 " + key)
    n_ld = mesh.count("LowerDBlockFromSidesetGenerator")
    # 每条晶界**两侧各一个**低维块（仅 mortar 方案）=> 2*ngb；交错方案只需一侧 => ngb
    want = 0 if NO_GIBBS else (2 * ngb if (TWOSIDE and not STAGGER) else ngb)
    print("  Mesh 里 LowerDBlock 个数 = %d（应 = %d）" % (n_ld, want))
    if n_ld != want:
        bad.append("LowerDBlock 个数 = %d" % n_ld)
    # 4) Gibbs 的件数
    if NO_GIBBS:
        print("  （NO_GIBBS=1 对照算例：不检查 Gibbs 件数）")
        print()
        print("自检通过（对照组）。" if not bad else "！！ 自检不通过：%s" % bad)
        return
    cnt = {
        "Gam 变量": len(re.findall(r"^\s*\[Gam\d+\]", t, re.M)),
        "GBFluxExchange": t.count("type = GBFluxExchange"),
        "ScaledTimeDerivative": t.count("type = ScaledTimeDerivative"),
        "kex 材料": t.count("property_name = kex"),          # 只应有 1 个（无 block）
        "AsRho 材料": t.count("property_name = AsRho"),      # 每个晶界一个
    }
    want = {"Gam 变量": ngb, "ScaledTimeDerivative": ngb,
            "kex 材料": 1, "AsRho 材料": ngb,
            "GBFluxExchange": 0 if STAGGER else ngb}
    for k, v in cnt.items():
        print("  %-22s %d（应 = %d）" % (k, v, want[k]))
        if v != want[k]:
            bad.append("%s = %d" % (k, v))
    # 5) 生产的晶界偏析项必须没了（只查**代码行**，注释里出现没问题）
    code = "\n".join(_seg(x) for x in t.split("\n"))
    for key in ("A_part", "Omega0"):
        n = code.count(key)
        print("  生产偏析项 %-10s 在**代码**里出现 %d 次（应为 0）" % (key, n))
        if n:
            bad.append("旧的晶界偏析项 %s 仍在代码里" % key)
    print()
    if bad:
        print("！！ 自检不通过：")
        for b in bad:
            print("   -", b)
        raise SystemExit(2)
    print("自检通过。")


if __name__ == "__main__":
    main()
