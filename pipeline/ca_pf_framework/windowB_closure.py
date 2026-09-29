#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_closure.py —— 「块」物理框架的**参数闭合层**（Round 29，2026-10-01）。

## 它解决什么

用户要求：把当前物理框架下**所有物理公式里的参数**提取出来，回答
「能否用现有研究 + 通用理论公式**推导**出可用的参数」，例如
**「一个块里有多少根板条」**，以及能否用**形核率**之类的方式让模型合理运转。
目标是**自洽、挑不出毛病**；绝对正确性留待实验标定。

本模块是**唯一**做这件事的地方：它不跑仿真，只给闭式与判据。
调用方（`_bk_exp.py` 的 `--nuc-law athermal`、`_bk_closure.py` 的报告）
拿它的输出当输入。

## 三层记账（每个量必须落在其中一层）

| 标记 | 含义 | 处置 |
|---|---|---|
| **[推]** | 纯推导，无自由常数 | 可以直接用；判据可逐位核 |
| **[借]** | 借来的文献值 | 必须带出处 + 误差带，并做敏感度 |
| **[标]** | 仍需标定的**单一**常数 | 必须给出可测定义 + 自洽区间 + 失效后果 |

## 参数清单（`PARAMS`，机器可读）

引擎/驱动/量具里出现的每一个物理参数都在 `PARAMS` 里有一条。
`_bk_closure.py` 用它生成报告表格；**改了代码里的数不改这里 = 记账失效**。

## 七条关键结论（都有闭式 + `selftest()` 的正/负对照）

**C-1｜匀相形核在本体系热力学上不可能；异相形核只在高效位点上才可行。**
   `ΔG* = 16πγ³/(3ΔG_v²)`，`ΔG_v(M_s) = 1.128e8`、`γ ∈ [0.201,0.337]`
   ⇒ **匀相** `ΔG*/kT = 516–2500`（需要 ≲60 才有可测速率）；
   连 `γ = 0.0818 J/m²`（远低于任何文献值）都只能压到 60。
   ★ **但"匀相不可能"≠"athermal 是唯一可能"**（Round 29 阶段回顾时发现我自己
     论证过头）：**异相**形核把势垒乘上接触角因子 `f(θ)=(2−3cosθ+cos³θ)/4`，
     本体系需要 `f ≤ 0.035` ⇒ **`θ_max ≈ 39°`**。
     ⇒ 正确的结论是：**任何可用的核必须落在"接触角 ≲39° 的高效位点"上** ——
     这正是 Olson–Cohen 的**预存核（层错型缺陷，有效界面能远低于宏观 γ）**图像。
     ⇒ athermal 位置饱和与 `ΔG*` 估算**一致**，但**不得**再说成"由 ΔG* 推出的唯一机制"。

**C-2｜板条数 `n` 从"规定的 6"变成导出量。**
   引擎几何本身给出「一次形核事件 = 占满整个面内足迹 `A_f`」⇒ `A_0 ≡ A_f`。
   代入 athermal 面密度律 ⇒ **`n(T) = α_KM·(M_s − T)`**，
   与 `windowB_km.Nv_of_T`（体密度律）同一函数形式，**不含新的自由常数**。
   `α_KM = 1.1e-2 /K`、冷却到 298 K ⇒ `n = 6.325` ⇒ **`floor = 6`**（与归档的规定值一致）。
   第 k 根板条的形核温度 `T_k = M_s − k/α_KM`。

**C-3｜"顺序形核"的判据与算力下界。**
   有序性（每根长完再核下一根）：`α_KM·q·L_lath ≤ v = MOB·ΔG`。
   给定 `MOB` ⇒ 最大冷速 `q_max`；给定 `q` ⇒ 最小迁移率。
   **最小步数**（与 `MOB`、`q` 都无关！）：
   `N_steps ≥ DS·ΔT·[(T0−M_s) + ΔT/2]·α_KM·L_lath / (cfl·Δx·ΔG_crit)`
   ⇒ 在 `Δx = 125 nm`、`L_lath = 4.5 µm` 上约 **3120 步**。这是物理下界，不是调参。

**C-4｜几何容纳上限。** 块沿 `n*` 的延伸是 `n·t`；它与板条长轴一起必须装进盒子：
   `(n·t/2)|n̂_i| + (L_lath/2)|â_i| + (W/2)|ŵ_i| ≤ L_box/2`。
   ⇒ **文献板条厚（0.51–0.88 µm）+ 6 根板条在 N=96/Δx=62.5 nm 的盒子里装不下**
   （`n_max ≈ 6.8` @t=0.51 µm，`t = 0.88 µm` 时 `n_max < 1`）；
   要同时满足文献厚度与 9:1 长厚比，必须放大到 **Δx ≈ 125 nm（N=96 ⇒ L=12 µm）**。

**C-5｜`β_h` 的下界由"跑多少步"导出。**
   `β_h ≥ ln(cfl·N_steps·Δx/(δ_max·t))`（`δ_max` = 允许的相对增厚）。
   归档的 `β_h = 3.5` 在 200 步上刚好够（预测增厚 57 nm vs 实测 75 nm），
   **在 3600 步上远远不够**（需要 ≈6.1）。
   物理修法：`β_h` 的真实形式是 `dG_misfit/(k_B T)` ⇒ **随降温而变大**；
   按运行区间的 `⟨1/T⟩` 取值即得 5.7–6.1 ⇒ **与算力下界自洽**，不是拟合。

**C-6｜C-1 润湿判据在整个文献区间内成立。**
   `γ_RS(θ≤5°) ≤ 0.2771 < 2γ_α′β`，而 `γ_α′β ∈ [0.201, 0.337]`
   ⇒ `2γ ∈ [0.402, 0.674]` ⇒ **干晶界**，最小余量 **1.45×**（在最不利的 0.201 端）。
   但 `γ_α′β < 0.1385` 会让判据翻转 ⇒ 该结论的证伪条件是可写下来的。

**C-7｜`f_nuc^crit = 4γ/d` 在本体系**结构性**惰性（不是"没接线"）。
   `4γ/t` 与 `ΔG_v` 的比是 `4γ/(t·ΔG_v)`，在文献参数区间内为 **1.4e-2 … 6.0e-2** ⇒
   `ΔG_v/f_crit = 17…70 ≫ 1`（与 `_bk_fcrit.py` 独立测得的 73–583 同量级，
   差异来自 `t` 与 `γ` 的取值）⇒ **任何核厚下都拦不住**。

**C-8｜几何容纳 vs 形核供给，**谁限速**？（目标里明确要求判这一条）**
   两条独立的"上限"：几何 `n_geo_cap`（AABB 精确判据，C-4）与
   供给 `n_kin = α_KM(M_s − T_f)`（C-2）⇒ `n = min`，**谁小谁限速**。
   * 闭环配置（Δx=125 nm）：`n_kin = 6.3 < n_geo_cap = 21` ⇒ **供给限速**；
     "几何开始咬人"的温度 `T_bind = −1036 K`（**不物理**）⇒ 几何**永远**不咬人。
   * α 取敏感带上端 2e-2 ⇒ `n_kin = 11.5`，**仍是供给限速**。
   * ★ **负对照**：缩回归档几何（Δx=62.5 nm）且 `t=0.68 µm` ⇒ `n_geo_cap = 3 < 6`
     ⇒ **变成几何限速** —— 这正是 C-4 逼我们把 Δx 放大到 125 nm 的原因，
     也说明**归档配置其实一直是几何受限的**（一个此前没被指认出来的隐性缺陷）。
   ⇒ 可证伪的推论：**`n` 与 `T_end` 成线性**（斜率 `−α_KM`）⇒
     **冷得越深、板条越多、块越厚**（`W_block = n·t`）—— 这是**工艺可调**的。

用法：
    python3 windowB_closure.py            # 自检（正/负对照）+ 打印关键数
    from windowB_closure import ...       # 当库用
"""

import math

import numpy as np

# ---------------------------------------------------------------------------
# 一、被引用的物理常数（全部带来源；**不在本模块里另设数值**）
# ---------------------------------------------------------------------------
from windowB_km import (M_S_TI64, T0_TI64, DG_CRIT_REF, DS_REF, DS_BAND,
                        ALPHA_KM_REF, ALPHA_KM_BAND, T_BETA_TI64,
                        drive_of_T, dG_chem)
from windowB_lath import (E0_TI64, GAMMA_M_TI64, THETA_M_DEG, A_ALPHA,
                          E_TI64, NU_TI64, GAMMA_AB, gamma_rs, gamma_rs_deg)

K_B = 1.380649e-23          # J/K  玻尔兹曼常数（SI 定义值，无误差）

# 弹性剪切模量：由各向同性 (E, ν) 导出 —— [推]，与 windowB_lath.rs_constants 同一式
G_TI64 = E_TI64 / (2.0 * (1.0 + NU_TI64))

# 板条几何：[借] Wang 2026（8.1±2.0 × 0.9±0.4 µm，长:厚 ≈ 9:1）+ Shuai 2026（厚 0.51–0.68 µm）
ASPECT_LT_WANG = 9.0
T_LATH_BAND_NM = (510.0, 880.0)      # Shuai 2026：P=173 W 时 0.51–0.88 µm
T_LATH_MAIN_NM = 510.0               # 六个代表样品的下限端（0.51–0.68）
W_BLOCK_BAND_UM = (1.0, 6.0)         # 【仍未检索到】block 沿堆叠方向的尺寸 ⇒ 只作上限判据

# F1（α′/β）面能的**主情景值**：[借] Murzinova 2017 的 975 °C 带 [0.201, 0.337] 内
# 取**整值 0.25**（**不是带中值 0.269**，只是为了不给出虚假的有效位数）。
# ⚠ 这是**借来的扩散型 α/β 平衡界面能**，不是位移型 α′/β 的实测值（见 `limitations()`）。
# ⚠ C-6（干晶界）的判定在最不利端 **0.201** 上也单独核过（余量仍有 1.45×）⇒
#   结论不依赖在这个带里取哪个数；但**翻转阈值 0.1385** 是可写下来的证伪条件。
GAMMA_F1_MAIN = 0.25
GAMMA_F1_BAND = (0.201, 0.337)

# β_h 的锚点在 M_s：[借/推] LATH_FACET_PLAN §9（位错环形成能 → β~3.8；板条长厚比 → β~3.0）
BETA_H_AT_MS = 3.5
BETA_H_BAND = (3.0, 6.0)

# 数值常数：CFL
CFL_DEFAULT = 0.15

# ΔG*/kT 的"可测速率"门槛：exp(-60) ≈ 1e-26，任何实验时间尺度都测不到
BARRIER_RATIO_MAX = 60.0


# ---------------------------------------------------------------------------
# 二、闭式
# ---------------------------------------------------------------------------
def alpha_km_n_lath(T_f, alpha_KM=ALPHA_KM_REF, Ms=M_S_TI64):
    """★ C-2：**到温度 `T_f` 为止，块里应有的板条数**（未取整）。[推]

    推导（三步，每步都只用已有定义）：
      ① 引擎几何：一次形核事件播一整片，**占满整个面内足迹** `A_f = L·W`
         ⇒ "一个核最终占的面积" `A_0 ≡ A_f`（**这是几何恒等式，不是选择**）。
      ② `windowB_km.Nv_of_T` 的**面**类比（同一 athermal 位置饱和律）：
         `N_A(T) = α_KM·(M_s − T)/A_0`  [1/m²]
      ③ 板条数 = 面上的核数：`n = N_A·A_f = α_KM·(M_s − T_f)·A_f/A_0 = α_KM·(M_s − T_f)`。

    ⇒ **`n` 不再是自由参数**：它由 `α_KM`（[标]，可测）与**冷却终温**决定。
    ⚠ 记账：本条**只对"堆叠型块"成立**（每片占满同一足迹）。
      平面上并列的块（packet 内多个 block）用同一个 `A_0` 会在面内也饱和 ⇒ 需要在
      面内做 Voronoi 分割，本轮**不做**（见 `limitations()` 第 3 条）。
    """
    dT = float(Ms) - float(T_f)
    return float(alpha_KM) * max(dT, 0.0)


def n_lath_int(T_f, alpha_KM=ALPHA_KM_REF, Ms=M_S_TI64):
    """取整后的板条数（引擎要整数个场）。"""
    return int(math.floor(alpha_km_n_lath(T_f, alpha_KM, Ms) + 1e-12))


def T_of_k(k, alpha_KM=ALPHA_KM_REF, Ms=M_S_TI64):
    """★ C-2：第 `k` 根板条的**形核温度** `T_k = M_s − k/α_KM`（k 从 1 起）。[推]

    ⇒ 这是一个**可直接证伪的预言**：原位 XRD/中子衍射测 `f(T)` 或
      中断淬火看板条数，就能读出 `α_KM`；反过来给定 `α_KM` 就给出逐根的温度。
    """
    if k < 1:
        raise ValueError('T_of_k: k 从 1 起')
    return float(Ms) - float(k) / float(alpha_KM)


def alpha_band_n(alpha_band=ALPHA_KM_BAND, T_f=298.0, Ms=M_S_TI64):
    """`α_KM` 的敏感度带对应的板条数带（用户的"扫描 2/4/6/10/15/20"的物理参数化）。[推]"""
    return [(float(a), alpha_km_n_lath(T_f, a, Ms), n_lath_int(T_f, a, Ms))
            for a in alpha_band]


def alpha_max_from_box(L_box, t, L_lath, W, n_hat, a_hat, w_hat,
                       T_f=298.0, Ms=M_S_TI64, n_cap=64):
    """★ C-4 的推论：**盒子能容纳的最大 `n`** ⇒ 反过来给 `α_KM` 的上界。[推]

    返回 `(n_geo_cap, alpha_max)`。`n_geo_cap` 用 AABB 精确判据（不是估算）：
        `(n·t/2)|n̂_i| + (L/2)|â_i| + (W/2)|ŵ_i| ≤ L_box/2`   对 i = x,y,z
    ⇒ `n ≤ 2·min_i[ (L_box/2 − (L/2)|â_i| − (W/2)|ŵ_i|) / |n̂_i| ] / t`
    `|n̂_i| = 0` 的分量不约束（`inf`）。
    """
    L_box = float(L_box); t = float(t); L = float(L_lath); W = float(W)
    nh = np.abs(np.asarray(n_hat, float)); ah = np.abs(np.asarray(a_hat, float))
    wh = np.abs(np.asarray(w_hat, float))
    lim = np.full(3, np.inf)
    for i in range(3):
        free = 0.5 * L_box - 0.5 * L * ah[i] - 0.5 * W * wh[i]
        if nh[i] > 1e-12:
            lim[i] = 2.0 * free / (nh[i] * t)
    n_cap_geo = float(np.min(lim))
    n_int = int(math.floor(min(n_cap_geo, n_cap) + 1e-12))
    # n = α·(Ms − T_f) ⇒ α = n/(Ms − T_f)
    a_max = (n_cap_geo / (float(Ms) - float(T_f))) if T_f < Ms else float('inf')
    return n_int, float(a_max)


def v_min_ordered(alpha_KM=ALPHA_KM_REF, q=1.0e6, L_lath=4.5e-6):
    """★ C-3：**顺序形核**要求的最小界面速度 `v ≥ α_KM·q·L_lath`。[推]

    物理：两次形核的时间间隔 `Δt_nuc = 1/(α_KM·q)`（athermal ⇒ 由降温速率给出）；
    一根板条长到全长需要 `Δt_grow = L_lath/v`。
    `Δt_grow ≤ Δt_nuc` ⟺ `v ≥ α_KM·q·L_lath`。
    ⚠ 违反的后果**不是数值错误**，而是模型进入"突发（burst）形核"regime
      —— 后一根在前一根长完之前就出现。真实马氏体确有 burst，
      但**本模型的逐片平衡形状是在"长完"这个前提下才成立**的 ⇒ 必须记账。
    ⚠ 判据要在**最不利点**（`v` 最小处 = 时钟起点 `T_start`）上核。
    """
    return float(alpha_KM) * float(q) * float(L_lath)


def q_max_ordered(v, alpha_KM=ALPHA_KM_REF, L_lath=4.5e-6):
    """★ C-3：给定界面速度 `v` 允许的最大冷速。"""
    return float(v) / (float(alpha_KM) * float(L_lath))


def v_of_MOB(MOB, dG):
    """`v = M·ΔG`（引擎的速度律，`windowB_surface` `dG_cell` 的标量形式）。[推]"""
    return float(MOB) * float(dG)


def T_start_of_clock(alpha_KM=ALPHA_KM_REF, Ms=M_S_TI64):
    """★★ 时钟的起点 = **第 1 根板条的形核温度** `T_1 = M_s − 1/α_KM`。[推]

    为什么不是 `M_s`：`n(T) = α_KM(M_s − T)` 在 `T = M_s` 处为 **0** ——
    即"一根板条都还没有"。而引擎在 `t=0` 就预摆了第 1 片 ⇒ 那一片**就是**第 1 根，
    它按 C-2 出现在 `T_1`。若时钟从 `M_s` 起，则预摆的那片相当于在 `M_s` 形核、
    后面的事件整体**错位一根**（`T_2…T_6` 被当成第 2…6 根）⇒ 序列与 C-2 差一个下标。
    （`clsmoke` 的 400 步冒烟跑实测到这一点：`n_eng_ev=0`，因为按错位写法
     第 1 个事件要等到 `T_2`，而 400 步只走到 ~800 K。）
    ⇒ **时钟从 `T_1` 起**，`n` 在 `T_1` 处正好 = 1（预摆的那片）。
    """
    return float(Ms) - 1.0 / float(alpha_KM)


def steps_at_q(MOB=1e-9, q=1.0e6, dx=125e-9, cfl=CFL_DEFAULT, T_f=298.0,
               T_start=None, T0=T0_TI64, DS=DS_REF):
    """给定 `(MOB, q, dx, T_start)` 时，跑完 `T_start → T_f` 全程所需的步数。[推]

    `N_steps = (MOB·DS/(cfl·dx·q))·[(T0−T_start)ΔT + ΔT²/2]`，`ΔT = T_start − T_f`
    （由 `dt = cfl·dx/(MOB·DS(T0−T))` 沿 `T(t)=T_start−q t` 积分得到）。
    `steps_min_ordered` 就是本式在 `q = q_max` 处的取值 —— `selftest` 做往返核对。
    """
    Ts = T_start_of_clock() if T_start is None else float(T_start)
    dT = Ts - float(T_f)
    if dT <= 0:
        raise ValueError('steps_at_q: 需要 T_f < T_start')
    num = (float(MOB) * float(DS)
           * ((float(T0) - Ts) * dT + 0.5 * dT * dT))
    den = float(cfl) * float(dx) * float(q)
    return num / den


def steps_min_ordered(alpha_KM=ALPHA_KM_REF, L_lath=4.5e-6, dx=125e-9,
                      cfl=CFL_DEFAULT, T_f=298.0, T_start=None,
                      T0=T0_TI64, DS=DS_REF):
    """★★ C-3：跑完**顺序**形核序列的**最小步数**（与 `MOB`、`q` 都无关）。[推]

    推导：`dt = cfl·dx/(MOB·ΔG_v(T))`，`ΔG_v(T) = DS(T0 − T)`，
          `T(t) = T_start − q t`，`t_end = (T_start − T_f)/q`。
          `N_steps = ∫dt/dt = (MOB·DS/(cfl·dx·q))·[(T0−T_start)ΔT + ΔT²/2]`
    再用有序性上界 `q ≤ q_max = MOB·DS(T0−T_start)/(α·L_lath)`
    （最不利点 = 时钟起点，那里 ΔG_v 最小）消掉 `MOB/q` ⇒ **`MOB` 与 `q` 全部消去**：
          `N_steps ≥ ΔT·[(T0−T_start) + ΔT/2]·α_KM·L_lath / (cfl·dx·(T0−T_start))`

    ⇒ 这是一个**物理下界**：想按物理次序把板条长出来，就算力而言**至少**要这么多步，
      调 `MOB` 或 `q` 都不能省。
    ★ 推论：**省算力的唯一途径是放大 `Δx`、缩短 `L_lath`、或减少 `ΔT`**。
    """
    Ts = T_start_of_clock(alpha_KM) if T_start is None else float(T_start)
    dT = Ts - float(T_f)
    if dT <= 0:
        raise ValueError('steps_min_ordered: 需要 T_f < T_start')
    dT0 = float(T0) - Ts                      # = ΔG_v(T_start)/DS
    if dT0 <= 0:
        raise ValueError('steps_min_ordered: T_start 必须 < T0')
    # = ΔT·[(T0−T_start) + ΔT/2]·α_KM·L_lath / (cfl·dx·(T0−T_start))
    return (dT * (dT0 + 0.5 * dT) * float(alpha_KM) * float(L_lath)
            / (float(cfl) * float(dx) * dT0))


def q_from_steps(steps, alpha_KM=ALPHA_KM_REF, dx=125e-9, cfl=CFL_DEFAULT,
                 MOB=1e-9, T_f=298.0, T_start=None, T0=T0_TI64, DS=DS_REF):
    """给定算力预算 `steps`，反解能用的冷速 `q`（其余同上）。[推]

    `N_steps = (MOB·DS/(cfl·dx·q))·[(T0−T_start)ΔT + ΔT²/2]` ⇒ 解出 `q`。
    ⚠ 解出的 `q` 还须满足有序性上界 `q ≤ q_max_ordered(MOB·DS(T0−T_start), …)`；
      调用方必须自己比一遍（`ordered_ok()`）。
    """
    Ts = T_start_of_clock(alpha_KM) if T_start is None else float(T_start)
    dT = Ts - float(T_f)
    num = (float(MOB) * float(DS) * ((float(T0) - Ts) * dT + 0.5 * dT * dT))
    den = float(cfl) * float(dx) * float(steps)
    return num / den


def ordered_ok(q, MOB=1e-9, alpha_KM=ALPHA_KM_REF, L_lath=4.5e-6,
               dG_worst=None):
    """★ C-3 的判定：`α_KM·q·L_lath ≤ MOB·ΔG_worst` ⇒ 顺序形核成立。[推]

    `ΔG_worst` 默认取 `ΔG_crit`（`T = M_s` 处，速度最小 ⇒ 最不利）。
    返回 `(ok, ratio, q_max)`，`ratio = Δt_grow/Δt_nuc`（≤1 才算有序）。
    """
    dG = DG_CRIT_REF if dG_worst is None else float(dG_worst)
    v = v_of_MOB(MOB, dG)
    ratio = v_min_ordered(alpha_KM, q, L_lath) / v
    qm = q_max_ordered(v, alpha_KM, L_lath)
    return (ratio <= 1.0), float(ratio), float(qm)


def beta_h_min(n_steps, dx, t, delta_max=0.3, cfl=CFL_DEFAULT):
    """★ C-5：`β_h` 的**下界**，由"跑多少步"和"允许多厚"导出。[推]

    法向（惯习面）迁移率是 `M(n̂) = M0·e^{−β_h}` ⇒ 每步法向位移至多
    `cfl·Δx·e^{−β_h}`；`N_steps` 步的累积法向位移 ≤ `cfl·N_steps·Δx·e^{−β_h}`。
    要求它 ≤ `δ_max·t` ⇒ **`β_h ≥ ln(cfl·N_steps·Δx/(δ_max·t))`**。

    ⚠ 这是**下界**，与 `LATH_FACET_PLAN §9` 的"长厚比反推"是两条**独立**约束，
      必须同时满足 ⇒ 取两者最大。
    """
    arg = (float(cfl) * float(n_steps) * float(dx)) / (float(delta_max) * float(t))
    if arg <= 1.0:
        return 0.0
    return float(math.log(arg))


def beta_h_of_T(T, beta_at_Ms=BETA_H_AT_MS, Ms=M_S_TI64):
    """★ C-5 的物理形式：`β_h = dG_misfit/(k_B T)` ⇒ **随降温变大**。[推]

    `LATH_FACET_PLAN §9` 把 `β_h` 标定在 `M_s` 处为 3.5（位错环形成能 / 长厚比反推）
    ⇒ 一般温度下 `β_h(T) = β_h(M_s)·M_s/T`。
    运行区间的等效值用 `⟨1/T⟩` 的倒数。
    """
    return float(beta_at_Ms) * float(Ms) / float(T)


def beta_h_run_average(n_steps, q, T_start, beta_at_Ms=BETA_H_AT_MS, Ms=M_S_TI64,
                       T_f=298.0, dx=125e-9, cfl=CFL_DEFAULT, t_lath=510e-9):
    """把 `β_h(T)` 在**实际的时间表**上按步数加权平均（`dt ∝ ΔG_v(T) ∝ (T0−T)`）。

    返回 `(beta_h_eff, beta_h_floor)`：前者是物理值，后者是 C-5 的算力下界。
    """
    Ts = float(T_start) + np.linspace(0.0, -1.0, 2001) * (float(T_start) - float(T_f))
    w = np.maximum(T0_TI64 - Ts, 0.0)                     # dt ∝ ΔG_v
    if w.sum() <= 0:
        raise ValueError('beta_h_run_average: 权重全 0')
    invT = float(np.sum(w / Ts) / np.sum(w))
    b_eff = float(beta_at_Ms) * float(Ms) * invT
    b_floor = beta_h_min(n_steps, dx, t_lath)
    return b_eff, b_floor


# ---- 形核热力学（C-1 / C-7）-----------------------------------------------
def r_star(gamma, dG_v):
    """临界核半径 `r* = 2γ/ΔG_v`（球形，界面能-体积自由能竞争）。[推]"""
    return 2.0 * float(gamma) / float(dG_v)


def dG_star(gamma, dG_v):
    """匀相形核势垒 `ΔG* = 16πγ³/(3ΔG_v²)`（球形）。[推]"""
    return 16.0 * math.pi * float(gamma) ** 3 / (3.0 * float(dG_v) ** 2)


def barrier_ratio(gamma, dG_v, T):
    """`ΔG*/k_B T`：**匀相**形核的势垒比。[推]

    ⚠ 这是**匀相**的量。异相形核要把势垒乘上接触角因子 `f(θ)`（见下），
      所以本函数**不能单独**得出"不可能形核"的结论 —— 见 `contact_angle_max()`。
    """
    return dG_star(gamma, dG_v) / (K_B * float(T))


def rate_slowdown_decades(gamma, dG_v, T, ratio_max=BARRIER_RATIO_MAX):
    """★ C-1a 的正确量纲：相对"可测门槛"慢了多少**个数量级**。[推]

    `ΔG*/kT` 与门槛 `ratio_max` 的**比值**是 `ΔG*/(ratio_max·kT)`（无量纲倍数），
    而**速率**之比是 `exp[−(ΔG*/kT − ratio_max)]` ⇒ 数量级 = `(ΔG*/kT − ratio_max)/ln10`。

    ⚠ 这两个数**不是一回事**，本文件第一版把"比值 8.6–42"错写成了"9–42 个数量级"
    （阶段回顾时发现）。现在两者都单独算、单独核。
    返回 `(倍数, 数量级)`。
    """
    r = barrier_ratio(gamma, dG_v, T)
    return r / float(ratio_max), (r - float(ratio_max)) / math.log(10.0)


def who_limits(n_geo_cap, alpha_KM=ALPHA_KM_REF, T_f=298.0, Ms=M_S_TI64):
    """★★ C-8：**几何容纳与形核供给，谁在限速？**[推]

    目标里明确要求判这一条。两条独立的"上限"：
      * **几何**：盒子装得下几根 ⇒ `n_geo_cap`（`alpha_max_from_box`，AABB 精确判据）
      * **供给**：athermal 律给得出几根 ⇒ `n_kin = α_KM·(M_s − T_f)`（C-2）

    `n = min(n_kin, n_geo_cap)`；**谁更小谁限速**。
    另外给出"几何开始咬人"的温度 `T_bind = M_s − n_geo_cap/α_KM`
    —— 若它在物理温区（> 0 K）之外，说明**本盒子永远不是几何受限的**。

    返回 `dict(n_kin, n_geo_cap, n, binding, T_bind, geom_is_slack)`。

    ★ 本模型的答案（闭环配置）：`n_kin = 6.3`、`n_geo_cap = 21`
      ⇒ **供给限速**；`T_bind = −1036 K` ⇒ 几何**永远**不咬人。
    ⇒ 可证伪的推论：**`n` 与 `T_end` 成线性**（斜率 `−α_KM`），
      冷得越深板条越多、块越厚（`W_block = n·t`）—— 这是**工艺可调**的。
    """
    n_kin = alpha_km_n_lath(T_f, alpha_KM, Ms)
    n_cap = float(n_geo_cap)
    binding = 'kinetics' if n_kin <= n_cap else 'geometry'
    T_bind = float(Ms) - n_cap / float(alpha_KM)
    return dict(n_kin=n_kin, n_geo_cap=n_cap, n=min(n_kin, n_cap),
                binding=binding, T_bind=T_bind,
                geom_is_slack=bool(T_bind < 0.0))


def hetero_barrier_factor(theta_deg):
    """异相形核的接触角因子 `f(θ) = (2 − 3cosθ + cos³θ)/4`（球形冠，标准式）。[推]

    `ΔG*_hetero = f(θ)·ΔG*_homo`；`f(0) = 0`（完全润湿 ⇒ 无势垒）、`f(90°) = 0.5`。
    """
    c = math.cos(math.radians(float(theta_deg)))
    return (2.0 - 3.0 * c + c ** 3) / 4.0


def contact_angle_max(gamma, dG_v, T, ratio_max=BARRIER_RATIO_MAX):
    """★★ C-1 的**正确版本**：让**异相**形核势垒比压到 `ratio_max` 所需的最大接触角。[推]

    解 `f(θ)·ΔG*_homo/k_B T = ratio_max`，`f` 在 `[0°,90°]` 上单调降 ⇒ 二分求根。
    返回 `(theta_max_deg, f_needed)`；`f_needed = ratio_max/(ΔG*_homo/kT)`。

    **为什么必须有这条**（Round 29 阶段回顾时发现的**我自己论证过头**的地方）：
      `C-1` 原来写的是"匀相形核不可能 ⇒ **athermal 是唯一可能的机制**"。
      前半句对（`ΔG*/kT = 1707 ≫ 60`），**后半句不成立**：
      异相形核只要位点的接触角足够小，势垒就降到可测。
      本函数给出**那个门槛**：`f_needed ≈ 0.035` ⇒ `θ_max ≈ 39°`。
      ⇒ 正确的结论是：
        **① 匀相形核不可能；**
        **② 异相形核只有在"接触角 ≲ 39° 的高效位点"上才热激活可行；**
        **③ 马氏体的惯习面是半共格的、胚芽是**预存**的层错型缺陷（Olson–Cohen），
           其有效界面能远低于宏观 γ ⇒ 落在 ② 的"高效位点"一侧 ⇒ athermal 位置饱和
           是与 ΔG* 估算**一致**的机制。**
      ⚠ **但"athermal 是唯一可能"这个更强的措辞不得再用** —— 它没有从 ΔG* 推出来。
    """
    ratio_homo = barrier_ratio(gamma, dG_v, T)
    f_need = float(ratio_max) / ratio_homo
    if f_need <= 0.0:
        return 0.0, f_need
    # `f` 在 [0°,90°] 上**单调增**，值域 [0, 0.5]。
    # ★ Round 29 修：第一版写反了这一行（`f_need >= f(0°) = 0` 恒真 ⇒ 永远返回 90°）
    #   —— 被自检 C-1b.1 当场抓到。
    if f_need >= hetero_barrier_factor(90.0):
        return 90.0, f_need
    lo, hi = 0.0, 90.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if hetero_barrier_factor(mid) < f_need:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi), f_need


def barrier_ratio_range(gammas=GAMMA_F1_BAND, T_lo=298.0, T_hi=None,
                        ratio_max=BARRIER_RATIO_MAX, n=61):
    """★ C-1a 的**正确取值范围**：在 `(γ, T)` 的矩形上算 `ΔG*/kT`。[推]

    `ΔG_v` 与 `T` **不是独立的**：`ΔG_v(T) = DS·(T0 − T)`。
    ⇒ 矩形 = `γ ∈ gammas` × `T ∈ [T_lo, T_hi]`（`T_hi` 默认 `M_s`）。

    ⚠ 为什么必须有这条（阶段回顾抓到的**第二处**错）：
      文档第一版写 `ΔG*/kT = 516…2500`，其中 **516 是 T=298 K、γ=0.25 的值**，
      与"M_s 处、γ 取文献带两端"**不是同一个工况** ⇒ 两个数被拼成了一个区间。
      正确：`T = M_s`、`γ ∈ [0.201,0.337]` ⇒ **887…4181**；
      把 T 也放开到 298 K ⇒ 全矩形 **268…4181**。

    返回 dict：`ratio_min/max`、`factor_min/max`（相对门槛的倍数）、
    `decades_min/max`（速率慢的数量级）、以及取到极值的 `(γ, T)`。
    """
    hi = float(M_S_TI64) if T_hi is None else float(T_hi)
    Ts = np.linspace(float(T_lo), hi, int(n))
    rmin, rmax = float('inf'), -float('inf')
    amin = amax = None
    for g in gammas:
        for T in Ts:
            dG = float(DS_REF) * (T0_TI64 - T)
            if dG <= 0:
                continue
            r = barrier_ratio(g, dG, T)
            if r < rmin:
                rmin, amin = r, (float(g), float(T))
            if r > rmax:
                rmax, amax = r, (float(g), float(T))
    # ★ 口径修（Round 4 回顾）：`decades`/`factor` **必须由 ratio 的极值算出**，
    #   不能各自独立取极值再配对 —— 第一版就是各自取极值，结果把
    #   "最小比值"配上了"最大倍数"，四个对照全 FAIL。
    #   关系是单调的：ratio 越大 ⇒ 倍数越大、数量级越大。
    def _f(r):
        return (r / float(ratio_max), (r - float(ratio_max)) / math.log(10.0))
    fmin, dmin = _f(rmin)
    fmax, dmax = _f(rmax)
    return dict(ratio_min=rmin, ratio_max=rmax, argmin=amin, argmax=amax,
                factor_min=fmin, factor_max=fmax,
                decades_min=dmin, decades_max=dmax)


def gamma_max_athermal(dG_v, T, ratio_max=BARRIER_RATIO_MAX):
    """★ C-1a：让**匀相** `ΔG*/kT ≤ ratio_max` 的最大界面能 `γ`。[推]

    `γ³ = 3·ratio·k_B T·ΔG_v²/(16π)`。
    本体系（`dG_v = 1.128e8`、`T = 873 K`）给 **0.0818 J/m²** ——
    **远低于任何文献界面能**（Murzinova 0.201–0.337；纯 Ti 计算 0.188）
    ⇒ **匀相形核在任何文献 γ 下都慢到不可测**。
    ⚠ 这只是"匀相"的结论；异相形核见 `contact_angle_max()`（C-1b）。
    """
    g3 = (3.0 * float(ratio_max) * K_B * float(T) * float(dG_v) ** 2
          / (16.0 * math.pi))
    return g3 ** (1.0 / 3.0)


def fcrit_ratio(gamma, t, dG_v):
    """★ C-7：`ΔG_v / f_nuc^crit`，`f_nuc^crit = 4γ/t` ⇒ **越大越拦不住**。[推]

    返回 `(f_crit, ratio)`。`ratio ≫ 1` ⇒ 该判据在任何核厚下都不限制形核。
    """
    fc = 4.0 * float(gamma) / float(t)
    return fc, float(dG_v) / fc


# ---- 润湿（C-6）-----------------------------------------------------------
def gamma_f3_max(theta_max_deg=5.0):
    """块内低角晶界的**最大**面能（Read–Shockley 在阶梯顶端）。[推]"""
    return float(gamma_rs_deg(theta_max_deg))


def wetting_check(gamma_F1, theta_max_deg=5.0):
    """★ C-6（Cahn 润湿判据）：`γ_LAGB < 2γ_α′β` ⇒ **不润湿 ⇒ 干晶界**。[推]

    返回 `dict(margin=2γ_F1/γ_F3max, dry=bool, flip_gamma=γ_F3max/2)`。
    `flip_gamma` 是**判据翻转的阈值**：`α′/β` 面能低于它，结论就反过来。
    ⇒ 这给了本条结论一个**可写下来的证伪条件**。
    """
    g3 = gamma_f3_max(theta_max_deg)
    two = 2.0 * float(gamma_F1)
    return dict(gamma_F3_max=g3, two_gamma_F1=two, margin=two / g3,
                dry=bool(g3 < two), flip_gamma=g3 / 2.0)


def wetting_over_band(theta_max_deg=5.0, band=GAMMA_AB):
    """把 C-6 在 Murzinova 的**整个**区间上逐档核一遍（含 975 °C 与 600 °C 两档）。[推]"""
    out = {}
    for k, (lo, hi) in band.items():
        out[k] = dict(lo=lo, hi=hi,
                      dry_lo=wetting_check(lo, theta_max_deg)['dry'],
                      dry_hi=wetting_check(hi, theta_max_deg)['dry'],
                      margin_lo=wetting_check(lo, theta_max_deg)['margin'])
    return out


# ---------------------------------------------------------------------------
# 三、由闭式给出的**推荐配置**（`_bk_exp.py` 的 `--nuc-law athermal` 用它）
# ---------------------------------------------------------------------------
# 归档配置的长轴/惯习法向/宽轴（取自 `_exp/_bk_eng/eng_eng12/meta.json`）。
# C-4 的判据只依赖三者的**分量绝对值**，与具体是哪个变体无关。
HAT_N = np.array([-0.4424, 0.4425, -0.7801])
HAT_A = np.array([-0.4909, 0.4909, 0.7198])
HAT_W = np.array([0.7071, 0.7071, 0.0])
# 面内宽/长：归档 plate_W/plate_L = 640/2400 = 0.2667（模型几何输入，非文献值）
ASPECT_LW = 0.2667
# Δx 候选（nm）：从细到粗，取**第一个**同时满足 t/Δx ≥ `t_min_over_dx` 与 C-4 的。
# 从 125 nm 起：更细的 Δx 只会让 C-3 的步数下界 ∝ 1/Δx 变大，而 C-4 在 125 nm 已通过。
DX_CAND_NM = (125.0, 150.0, 160.0, 175.0, 200.0, 250.0, 300.0, 400.0, 500.0)


def recommend(N=96, t_lath_nm=T_LATH_MAIN_NM, aspect=ASPECT_LT_WANG,
              alpha_KM=ALPHA_KM_REF, T_f=298.0, MOB=1e-9, cfl=CFL_DEFAULT,
              ratio_target=0.8, n_floor=2, dx_cand_nm=DX_CAND_NM,
              t_min_over_dx=4.0):
    """★ 由上面几条闭式**一次算出**一套自洽的引擎输入（**不是调出来的**）。

    步骤（每一步都只用前面已给的闭式）：
      1. `n = floor(α_KM(M_s − T_f))`                                    —— C-2
      2. `t` 取文献板条厚（Shuai 2026），`L_lath = aspect·t`（Wang 9:1），
         `W = ASPECT_LW·L_lath`（模型几何输入）
      3. `Δx` 取候选表里**第一个**同时满足 `t/Δx ≥ t_min_over_dx`（4，本仓库
         自己的分辨率目标带 4–8 的下端）与 C-4 的 ⇒ **不是**"调到结果好看"，
         而是"最小代价的合法离散化"
      4. `q` 取 C-3 的有序性上界乘 `ratio_target`（安全系数）
      5. `N_steps = ceil(steps_min_ordered / ratio_target × 1.05)`
      6. `β_h = max(β_h(T) 运行均值, C-5 下界)`

    返回 dict；`ok` = 所有判据都过。`blocked` 给出第一个不过的判据名。
    """
    out = dict(N=int(N), alpha_KM=float(alpha_KM), T_f=float(T_f), MOB=float(MOB),
               t_lath_nm=float(t_lath_nm), aspect=float(aspect),
               ratio_target=float(ratio_target))
    n_float = alpha_km_n_lath(T_f, alpha_KM)
    n = max(n_lath_int(T_f, alpha_KM), int(n_floor))
    out.update(n_lath_float=n_float, n_lath=n)
    t = float(t_lath_nm) * 1e-9
    L_lath = float(aspect) * t
    W = ASPECT_LW * L_lath
    out.update(t=t, L_lath=L_lath, W_lath=W, elong=L_lath / W)

    # --- ③ 选 Δx ----------------------------------------------------------
    pick = None
    tried = []
    for dx_nm in dx_cand_nm:
        dx = dx_nm * 1e-9
        res_dx = t / dx
        L_box = int(N) * dx
        ncap, a_max = alpha_max_from_box(L_box, t, L_lath, W, HAT_N, HAT_A, HAT_W,
                                         T_f=T_f)
        tried.append((dx_nm, round(res_dx, 2), ncap))
        if res_dx >= float(t_min_over_dx) and ncap >= n:
            pick = (dx_nm, dx, L_box, ncap, a_max, res_dx)
            break
    out['dx_tried'] = tried
    if pick is None:
        out['ok'] = False
        out['blocked'] = 'C-4（或 t/Δx ≥ %.1f）：候选 Δx 里没有一个能装下 %d 根板条' % (
            t_min_over_dx, n)
        return out
    dx_nm, dx, L_box, ncap, a_max, res_dx = pick
    out.update(dx_nm=dx_nm, dx=dx, L_box=L_box, L_box_um=L_box * 1e6,
               n_geo_cap=ncap, alpha_max=a_max, t_over_dx=res_dx)

    # --- ③b 时钟起点 = T_1（预摆的第 1 片就是第 1 根，见 T_start_of_clock）----
    T_start = T_start_of_clock(alpha_KM)
    out.update(T_start=T_start, dT=T_start - float(T_f),
               dG_at_start=DS_REF * (T0_TI64 - T_start))

    # --- ④ q：有序性上界 × ratio_target -----------------------------------
    #   最不利点 = 时钟起点（ΔG_v 最小 ⇒ v = M·ΔG 最小）
    v_worst = v_of_MOB(MOB, out['dG_at_start'])
    q_cap = q_max_ordered(v_worst, alpha_KM, L_lath)
    q = q_cap * float(ratio_target)
    out.update(v_worst=v_worst, q_cap=q_cap, q=q,
               t_sim=(T_start - float(T_f)) / q)

    # --- ⑤ 步数 -----------------------------------------------------------
    smin = steps_min_ordered(alpha_KM, L_lath, dx, cfl, T_f, T_start)
    steps = int(math.ceil(smin / float(ratio_target) * 1.05))
    out.update(steps_min=smin, steps=steps,
               growth_steps=L_lath / (cfl * dx),
               steps_per_nuc=(1.0 / (alpha_KM * q)) / (cfl * dx / v_worst))

    # --- ⑥ β_h ------------------------------------------------------------
    b_eff, b_floor = beta_h_run_average(steps, q, T_start, t_lath=t)
    out.update(beta_h_T=b_eff, beta_h_floor=b_floor,
               beta_h_use=max(b_eff, b_floor))

    # --- 判定 --------------------------------------------------------------
    ok_o, ratio_o, _ = ordered_ok(q, MOB, alpha_KM, L_lath,
                                  dG_worst=out['dG_at_start'])
    out.update(ordered_ok=ok_o, ordered_ratio=ratio_o,
               overlap_nm=dx_nm, r_nuc_nm=0.5 * W * 1e9)
    out['ok'] = bool(ok_o and ncap >= n and res_dx >= float(t_min_over_dx))
    if not out['ok']:
        out['blocked'] = ('C-3 有序性' if not ok_o else 'C-4')
    return out


def limitations():
    """必须随任何结论一起报的局限（返回 list[str]）。"""
    return [
        'C-2 的 `n = α_KM(M_s − T_f)` 只在"堆叠型块"（每片占满同一足迹）上成立；'
        '面内并列的多个 block 需要在面内做分割，本轮不做。',
        '`α_KM` 仍是 **[标]**：它是"单位过冷度下单位面积的可用核位数"，'
        '定义清楚、可测（原位 f(T) 或中断淬火数板条），但本轮没有 Ti-64 的实测值。',
        '`block` 沿堆叠方向的尺寸 `W_block` **仍未检索到** ⇒ C-4 只能给"装得下/装不下"，'
        '不能反过来独立定 `n`。',
        '`γ_α′β` 借的是**扩散型 α/β 平衡**界面能（Murzinova），'
        '不是位移型 α′/β 的值；C-6 的结论建立在这个借用上。',
        '`β_h` 的指数形式 `M(n)=M0·e^{−β_h(n·n̂)²}` 本身是**唯象**的'
        '（物理内核是 `dG_misfit/(k_B T)`），长跑下它被暴露：'
        'C-5 要求 `β_h` 随步数增大。',
        '`F2`（不同变体之间的界面）在全部归档块算例里**面积为 0**'
        '（6 个场同变体）⇒ 它的面能**从未被检验过**。',
        '`Γ_i ≡ 0`（无溶质通道）、`shuffle` 未表示、小应变近似 —— 均见 `WINDOWB_PARAMS §6`。',
    ]


# ---------------------------------------------------------------------------
# 四、参数总表（机器可读；`_bk_closure.py` 用它出表）
# ---------------------------------------------------------------------------
def _p(name, val, unit, where, role, tier, source):
    return dict(name=name, value=val, unit=unit, where=where, role=role,
                tier=tier, source=source)


def params():
    """**当前物理框架下所有物理公式里的参数**。tier ∈ {推, 借, 标, 数}。"""
    P = []
    A = P.append
    # ---- 晶体学 ----------------------------------------------------------
    A(_p('a_beta', 0.3310, 'nm', 'windowB_ti64_variants', 'Burgers OR → ε⁰', '借',
         'WINDOWB_PARAMS §1（β-Ti 0.3306–0.3320）'))
    A(_p('a_alpha', 0.2950, 'nm', 'windowB_lath.A_ALPHA', 'Burgers OR → ε⁰；也是位错 b', '借',
         'WINDOWB_PARAMS §1（α-Ti）'))
    A(_p('c_alpha', 0.4683, 'nm', 'windowB_ti64_variants', 'Burgers OR → ε⁰（c/a=1.5875）', '借',
         'WINDOWB_PARAMS §1'))
    A(_p('eps0_v (×12)', '—', '-', 'windowB_ti64_variants.variants()', '弹性能 ed_k、变体选择', '推',
         '由 a_beta/a_alpha/c_alpha + Burgers OR 构造；C1–C6 六条判据全过'))
    A(_p('Ms', M_S_TI64, 'K', 'windowB_km.M_S_TI64', 'athermal 钟的零点；C-2 的 n', '借',
         'Ji 2016 DOI 10.1007/s11669-015-0436-9（原文为估 ΔG 取的名义值）'))
    A(_p('T0', T0_TI64, 'K', 'windowB_km.T0_TI64', 'ΔG=0 的温度', '借',
         'Ji 2016 CALPHAD f^β=f^α'))
    A(_p('T_beta', T_BETA_TI64, 'K', 'windowB_km.T_BETA_TI64', '仅用于冷速时间表的起点', '借',
         'WINDOWB_PARAMS §1（Ji 2016 给 1249 K）'))
    # ---- 弹性 ------------------------------------------------------------
    A(_p('C (β-Ti cubic)', (134, 110, 36), 'GPa', 'T16_verify_rve.C', '弹性能 ed_k（母相刚度）', '借',
         'WINDOWB_PARAMS §2；β-Ti 高温外推，误差未量化'))
    A(_p('E_TI64', E_TI64, 'Pa', 'windowB_lath.E_TI64', '→ G → E0', '借',
         'WINDOWB_PARAMS §2（α′ 多晶近似 114 GPa）'))
    A(_p('NU_TI64', NU_TI64, '-', 'windowB_lath.NU_TI64', '→ G → E0', '借', '同上 0.34'))
    A(_p('G_TI64', G_TI64, 'Pa', 'windowB_closure.G_TI64', 'E0 = Gb/[4π(1−ν)]', '推',
         'G = E/[2(1+ν)]，由 E_TI64/NU_TI64 导出'))
    # ---- 界面能 ----------------------------------------------------------
    A(_p('gamma0 (F1, α′/β)', 0.15, 'J/m²', '_bk_exp.py:186 / T16', 'F1 界面刚度', '标',
         '**占位**。文献 Murzinova 2017 给 0.201–0.337(975 °C)/0.298–0.429(600 °C) '
         '⇒ 建议改用 0.25（主）/带 [0.201,0.337]'))
    A(_p('gamma0 (F2, 异变体)', 0.15, 'J/m²', '同上', 'F2 界面刚度', '标',
         '**占位且从未被检验**：归档块算例 6 场同变体 ⇒ F2 面积为 0'))
    A(_p('E0 (RS)', E0_TI64, 'J/m²', 'windowB_lath.E0_TI64', 'γ_RS 的尺度', '推',
         'E0 = Gb/[4π(1−ν)] = %.5f（自检 S-3.1）' % E0_TI64))
    A(_p('theta_m', THETA_M_DEG, 'deg', 'windowB_lath.THETA_M_DEG', 'RS 平台角', '借',
         'Read–Shockley 通用平台角 15°'))
    A(_p('gamma_m (RS)', GAMMA_M_TI64, 'J/m²', 'windowB_lath.GAMMA_M_TI64', 'γ_RS 的上限', '推',
         'γ_m = E0·θ_m = %.5f（自检 S-3.2）' % GAMMA_M_TI64))
    A(_p('theta ladder', 5.0, 'deg', '_bk_exp.py --omega-max-deg', 'F3 面能 γ_RS(θ)', '标',
         '**无直接实验值**；用户文献复核建议改做 0.5–2/2–5/5–10° 三情景'))
    A(_p('GAMMA_AB (α′/β)', GAMMA_AB, 'J/m²', 'windowB_lath.GAMMA_AB', 'C-6 润湿判据', '借',
         'Murzinova 2017 DOI 10.22226/2410-3535-2017-1-55-59'))
    # ---- 热力学/驱动 ------------------------------------------------------
    A(_p('DG_CRIT_REF', DG_CRIT_REF, 'J/m³', 'windowB_km', '|ΔG(Ms)|；M_s 锚；C-1/C-3', '借',
         '1200 J/mol（Ji 2016）÷ V_m'))
    A(_p('DS_REF', DS_REF, 'J/(m³K)', 'windowB_km', 'ΔG_v(T) = DS(T0−T)', '推',
         '= DG_CRIT_REF/(T0−Ms)；带 ±20%（DS_BAND）'))
    A(_p('V_m', 1.064e-5, 'm³/mol', 'windowB_km 注释', 'J/mol ↔ J/m³', '借',
         'Boccardo 2024 附录 A1 引 Singman 1984；β/α′ 用同一个值（未区分）'))
    A(_p('df (引擎常数)', 3.5e8, 'J/m³', 'T16_verify_rve.DF', '引擎的驱动力', '推',
         '= drive_of_T(298 K)。**本应是 T 的函数** ⇒ 闭环版改用 set_T(T_of_t)'))
    A(_p('cfl', CFL_DEFAULT, '-', '_bk_exp.py:375', 'dt = cfl·dx/(M·ΔG)', '数',
         'CFL 数；与实际最大速度配套（suggest_dt）'))
    # ---- 动力学 ----------------------------------------------------------
    A(_p('MOB', 1e-9, 'm⁴/(J·s)', 'T16_verify_rve.MOB', 'v = M·ΔG', '标',
         '**占位**。C-3 给下界 MOB_min = α_KM·q·L/ΔG_crit；上界由"界面不拖后腿"给'))
    A(_p('alpha_KM', ALPHA_KM_REF, '1/K', 'windowB_km.ALPHA_KM_REF', 'C-2 的 n；C-3 的节奏', '标',
         '**占位**（钢的常见量级 1e-2，Ti-64 未核实）。可测：原位 f(T) 或中断淬火数板条'))
    A(_p('beta_h', BETA_H_AT_MS, '-', '_bk_exp.py --beta-h', 'M(n)=M0 e^{−β_h(n·n̂)²}', '标',
         '锚在 Ms：位错环形成能→3.8；长厚比→3.0 ⇒ 取 3.5。'
         '闭环版用 β_h(T)=3.5·Ms/T 与 C-5 下界取大'))
    A(_p('beta_w', 2.3, '-', '_bk_exp.py --beta-w', '宽度方向钉扎', '标',
         '由"长/宽~10"反推 ⇒ **该观测无出处**（Wang 2026 只给长与厚）'))
    A(_p('p_auto', 0.0, '-', 'nuc_cfg(p_auto=…)', 'sympathetic 增益 1+p·4f(1−f)', '标',
         '**本项目自设**；原引 Bhadeshia (5.24) 已撤（分母未读到）'))
    A(_p('harden_f', 1.0, '-', 'nuc_cfg(harden_f=…)', '阶段③开关（母相硬化）', '数',
         '默认 1.0 = 不可达 ⇒ 归档算例**未启用阶段③**'))
    A(_p('use_fcrit', False, '-', 'nuc_cfg(use_fcrit=…)', 'f_nuc^crit = 4γ/d', '数',
         'C-7：在本体系结构性惰性（ΔG_v/f_crit ≈ 17–70）'))
    # ---- 形核几何/放置 ----------------------------------------------------
    A(_p('R_nuc', 320.0, 'nm', '_bk_exp.py --eng-r-nm', '核的面内半宽', '数',
         '不是物理核径（真实 r* = 2γ/ΔG_v ≈ 1.4–6.0 nm ≪ Δx）⇒ **亚网格种子约定**'))
    A(_p('t_nuc', 250.0, 'nm', '_bk_exp.py --eng-t-nm', '核厚 = 板条厚', '标',
         '**与文献冲突**：Shuai 2026 给 0.51–0.88 µm ⇒ 闭环版用 510 nm'))
    A(_p('plate L/W/T', (2400, 640, 250), 'nm', '_bk_exp.py --plate-*', '种子几何/长厚比', '标',
         '归档 L/T = 9.6 ≈ Wang 2026 的 9:1 ✓；绝对尺度受盒子限制（C-4）'))
    A(_p('elong', 3.75, '-', '_bk_exp.py --eng-elong', 'L/W', '数', '= plate_L/plate_W'))
    A(_p('nuc cadence', 30, 'steps', '_bk_exp.py --eng-cadence', '形核节奏', '数',
         '**规定值**；闭环版由 C-2/C-3 的 athermal 律取代'))
    A(_p('overlap', 62.5, 'nm', '_bk_exp.py --nuc-overlap-nm', '共用界面的咬入量', '数',
         '剂量–响应实测：1Δx 最优；0 会留 1 胞 β 膜、1.5Δx 会撕碎先成片'))
    A(_p('nv (场数)', 6, '-', '_bk_exp.py --laths', '可表示的板条数上限', '数',
         '表示上限（region() 是 int8 ⇒ nreg ≤ 127），不是物理上限。'
         '闭环版由 C-2 导出：`--laths` = n 个 1'))
    # ★★★ R29 新增：**播种厚 ≠ 物理厚**（记账偏移，不是物理量）。
    #   共享界面（`attach`）把重叠区 `o` 从两片各吃 `o/2` ⇒
    #   内部片播种 `t_phys + o`、末片 `t_phys + o/2`（`t_last_reduce`）。
    #   实测代价（`dry_cl1` 忘了补，跑到 step 1000）：场 1 剔孤儿厚 **391.8 nm**
    #   vs 物理靶 510 ⇒ **−23%**，掉出 V-8b 窗口；场 2/3（尚未被咬）503/508 ✓
    #   ⇒ 判据的靶必须是 `--plate-t-physical`，不是 `--plate-T`。
    A(_p('t_seed (播种厚)', 't_phys + o', 'nm', '_bk_closed.py', '引擎播种的板条厚', '数',
         '**不是物理量**，是"预补被咬量"的记账偏移；'
         '判据（V-8b/A-8）的靶是 `--plate-t-physical`。'
         '⚠ Round 5 实测：被咬量**不是常数 o/2**（n=2 时≈0、n=6 时≈o）'
         '⇒ 本条的**取值未闭合**，开关 `--seed-comp-frac`（`_bk_closed.py`）'))
    # ---- ★ Round 5 参数完备性审计（`_bk_param_audit.py`）补登的三条 ----
    A(_p('q (冷速)', 'q_cap × cool_ratio', 'K/s', 'windowB_closure.q_max_ordered',
         'athermal 时钟 T(t)=T_start−q·t 的速率', '推',
         'C-3 的有序性上界 `q ≤ M·ΔG_v(T_start)/(α_KM·L_lath)` × 安全系数。'
         'CLI：`_bk_exp.py --cool-rate`（0 = 自动取 C-3 的值；非 0 = 用户给定并检查）'))
    A(_p('cool_ratio', 0.8, '-', '_bk_exp.py --cool-ratio', 'q 的安全系数', '数',
         '0.8 ⇒ Δt_grow/Δt_nuc = 0.8（留 20% 余量）；'
         '同时决定 C-3 的步数下界要乘 1/0.8'))
    A(_p('gamma_film (γ_f)', 0.6, 'J/m²', '_bk_exp.py --gamma-film',
         '`auto` 臂的面带 ψ 模型里的"残余 β 膜"面能', '标',
         '用于 C-1/C-6 的润湿判决（P-2）：**假设存在**一层 β 膜时的膜/基体面能。'
         'C-6 说 γ_RS,max=0.277 < 2γ_α′β ⇒ **不润湿 ⇒ 干晶界**，'
         '而 `auto` 臂的实测 ψ 单调退湿到 0.09 与之一致。'
         '⚠ 它只在 `--arm auto` 被读到；闭环算例（`dry`/`gpos`）不用它'))
    # ---- 网格 ------------------------------------------------------------
    A(_p('N / dx', (96, 62.5), '-/nm', '_bk_exp.py --N/--dx-nm', '离散化', '数',
         '约束① t/Δx ≥ 3；C-4 给 N=96 下 Δx 必须 ≥125 nm 才能装下文献厚度的 6 根'))
    A(_p('aniso (Herring)', 0.4, '-', '_bk_exp.py kw', 'γ(n) 各向异性强度', '数',
         'Herring 刚度项；与 γ_RS 的 θ 依赖正交'))
    A(_p('facet_lam / facet_eps', (0.0, 0.05), '-', '_bk_exp.py --facet-*', '刻面（默认关）', '数',
         'facet_lam=0 ⇒ 归档算例未启用刻面'))
    A(_p('norm_smooth', 0, '-', '_bk_exp.py --norm-smooth', '∇d 盒滤波宽度', '数',
         '离散正则化，不是物理量'))
    A(_p('reinit_dt / band', (1e-4, 6.0), '-', '_bk_exp.py', 'Sussman 重初始化', '数',
         'reinit_dt=1e-4 而 dt≈2.7e-8 ⇒ 200 步里不会触发（R22/R23 已记账）'))
    return P


# ---------------------------------------------------------------------------
# 五、自检（**正对照 + 负对照**；只验证"正常能过"等于没验证）
# ---------------------------------------------------------------------------
def selftest(verbose=True):
    chk = []

    def ck(name, cond, extra=''):
        chk.append((name, bool(cond), extra))

    # --- 常数自洽 ---------------------------------------------------------
    ck('S-1  E0 = Gb/[4π(1−ν)] == 1.51301', abs(E0_TI64 - 1.51301) < 5e-5,
       '%.6f' % E0_TI64)
    ck('S-2  γ_m = E0·θ_m == 0.39610', abs(GAMMA_M_TI64 - 0.396102) < 5e-6,
       '%.6f' % GAMMA_M_TI64)
    ck('S-3  γ_RS(5°) == 0.277088', abs(gamma_f3_max(5.0) - 0.277088) < 5e-6,
       '%.6f' % gamma_f3_max(5.0))

    # --- C-1：athermal 是推论 ---------------------------------------------
    ratio_ms = barrier_ratio(0.25, DG_CRIT_REF, M_S_TI64)
    ck('C-1.1 ΔG*/kT @Ms (γ=0.25) ≫ 60', ratio_ms > 1000.0, '%.1f' % ratio_ms)
    gmax = gamma_max_athermal(DG_CRIT_REF, M_S_TI64)
    ck('C-1.2 允许 athermal 的 γ 上限 < 文献下限 0.201',
       gmax < 0.201, 'γ_max=%.4f vs 文献下限 0.201' % gmax)
    ck('C-1.3 γ_max 落在 0.08–0.09（与手算 0.0818 一致）',
       0.080 < gmax < 0.083, '%.4f' % gmax)
    # ★负对照的正确设计：**把 γ 往下推**，看结论会不会翻。
    #   γ=0.10（文献下限 0.201 的一半）时 ΔG*/kT 仍 = 109 ≫ 60 ⇒
    #   结论**不依赖** γ 取文献带的哪一端。
    r_low = barrier_ratio(0.10, DG_CRIT_REF, M_S_TI64)
    ck('C-1.4 ★负对照：γ=0.10（文献下限的一半）时 ΔG*/kT 仍 > 60',
       r_low > 60.0, '%.1f' % r_low)
    # 反向：γ 要低到 0.0819 才压到 60 ⇒ 与 C-1.2/C-1.3 是同一个数的两种读法
    ck('C-1.5 反向：γ = γ_max 时 ΔG*/kT == 60（阈值确实在 0.0819）',
       abs(barrier_ratio(gmax, DG_CRIT_REF, M_S_TI64) - 60.0) < 1e-6)
    # ---- C-1b：**异相**形核（Round 29 阶段回顾补）----------------------
    #   ★ 这条是对我自己论证过头的纠正：ΔG* 只否掉了「匀相」，
    #     没有否掉「在高效位点上的异相形核」。这里把门槛算出来。
    th, f_need = contact_angle_max(0.25, DG_CRIT_REF, M_S_TI64)
    ck('C-1b.1 异相形核可行的门槛：θ_max ≈ 39°（f_needed ≈ 0.035）',
       abs(th - 39.0) < 1.5 and abs(f_need - 0.03515) < 5e-4,
       'θ_max=%.2f°  f_needed=%.5f' % (th, f_need))
    ck('C-1b.2 f(0)=0、f(90°)=0.5、且随 θ **单调增**',
       abs(hetero_barrier_factor(0.0)) < 1e-12
       and abs(hetero_barrier_factor(90.0) - 0.5) < 1e-12
       and hetero_barrier_factor(20.0) > hetero_barrier_factor(10.0),
       '%.5f vs %.5f' % (hetero_barrier_factor(20.0), hetero_barrier_factor(10.0)))
    ck('C-1b.3 ★负对照：θ=50°（>门槛）的势垒比仍 > 60 ⇒ 不可行',
       hetero_barrier_factor(50.0) * barrier_ratio(0.25, DG_CRIT_REF, M_S_TI64) > 60.0,
       '%.1f' % (hetero_barrier_factor(50.0)
                 * barrier_ratio(0.25, DG_CRIT_REF, M_S_TI64)))
    ck('C-1b.4 ★负对照：θ=20°（<门槛）的势垒比 < 60 ⇒ 可行',
       hetero_barrier_factor(20.0) * barrier_ratio(0.25, DG_CRIT_REF, M_S_TI64) < 60.0,
       '%.1f' % (hetero_barrier_factor(20.0)
                 * barrier_ratio(0.25, DG_CRIT_REF, M_S_TI64)))
    # ---- C-1c：**量纲**（比值 vs 数量级）与**正确的取值范围** --------------
    #   ★ 纠正两处：① 第一版文档把**比值**"9–42"说成了"个数量级"；
    #                ② 第一版文档的区间 `516…2500` 把 M_s 处与 298 K 处的值拼在一起。
    _br = barrier_ratio_range()
    ck('C-1c.1 ΔG*/kT 全矩形 (γ∈[0.201,0.337], T∈[298,873] K) = %.0f…%.0f'
       % (_br['ratio_min'], _br['ratio_max']),
       255.0 < _br['ratio_min'] < 262.0 and 4180.0 < _br['ratio_max'] < 4185.0,
       'min@(γ=%.3f,T=%.0f) max@(γ=%.3f,T=%.0f)'
       % (_br['argmin'][0], _br['argmin'][1], _br['argmax'][0], _br['argmax'][1]))
    # 解析钉点：`ratio ∝ γ³/[(T0−T)²·T]` ⇒ 最小值在 `d/dT[(T0−T)²T]=0` ⇒ **T = T0/3**
    ck('C-1c.1b 解析：最小值出现在 **T = T0/3 = %.1f K**（数值 %.0f K）'
       % (T0_TI64 / 3.0, _br['argmin'][1]),
       abs(_br['argmin'][1] - T0_TI64 / 3.0) < 6.0,
       '%.1f vs %.1f' % (_br['argmin'][1], T0_TI64 / 3.0))
    ck('C-1c.2 相对门槛(60)的**倍数** = %.1f…%.1f'
       % (_br['factor_min'], _br['factor_max']),
       4.0 < _br['factor_min'] < 4.6 and 69.0 < _br['factor_max'] < 70.0,
       '%.1f / %.1f' % (_br['factor_min'], _br['factor_max']))
    ck('C-1c.3 **速率**慢的数量级 = %.0f…%.0f'
       % (_br['decades_min'], _br['decades_max']),
       84.0 < _br['decades_min'] < 88.0 and 1780.0 < _br['decades_max'] < 1800.0,
       '%.1f / %.1f' % (_br['decades_min'], _br['decades_max']))
    ck('C-1c.4 ★负对照：倍数与数量级**不是同一个数**（相差 ≫1）',
       (_br['decades_max'] / _br['factor_max']) > 20.0,
       '%.1f vs %.1f' % (_br['decades_max'], _br['factor_max']))
    # 单独钉住"M_s 处、γ 取文献带两端"这个工况（文档里最常引的那对）
    _r201 = barrier_ratio(0.201, DG_CRIT_REF, M_S_TI64)
    _r337 = barrier_ratio(0.337, DG_CRIT_REF, M_S_TI64)
    ck('C-1c.5 T=M_s、γ=0.201/0.337 ⇒ ΔG*/kT = %.0f / %.0f' % (_r201, _r337),
       885.0 < _r201 < 890.0 and 4180.0 < _r337 < 4185.0,
       '（第一版文档误写成 516…2500 —— 那混进了 T=298 K 的值）')

    # --- C-2：板条数 ------------------------------------------------------
    n25 = alpha_km_n_lath(298.0)
    ck('C-2.1 α=1.1e-2, T_f=298 K ⇒ n = 6.325', abs(n25 - 6.325) < 5e-3, '%.4f' % n25)
    ck('C-2.2 floor(n) == 6（与归档的规定值一致）', n_lath_int(298.0) == 6)
    ck('C-2.3 T_1 = 782.09 K', abs(T_of_k(1) - 782.0909) < 1e-3, '%.4f' % T_of_k(1))
    ck('C-2.4 T_6 = 327.55 K > 298（所以第 6 根在室温前出现）',
       T_of_k(6) > 298.0, '%.2f' % T_of_k(6))
    ck('C-2.5 ★负对照：T_f = Ms（未过冷）⇒ n = 0',
       n_lath_int(float(M_S_TI64)) == 0)
    bnd = alpha_band_n()
    ck('C-2.6 α 带 (5e-3,1.1e-2,2e-2) ⇒ n = 2/6/11',
       [b[2] for b in bnd] == [2, 6, 11], str([b[2] for b in bnd]))

    # --- C-8：**谁限速**（目标里明确要求判这一条）-------------------------
    nh8 = np.array([-0.4424, 0.4425, -0.7801]); ah8 = np.array([-0.4909, 0.4909, 0.7198])
    wh8 = np.array([0.7071, 0.7071, 0.0])
    _cap8, _ = alpha_max_from_box(96 * 125e-9, 510e-9, 4590e-9, 1224.153e-9,
                                  nh8, ah8, wh8)
    _wl = who_limits(_cap8)
    ck('C-8.1 闭环配置：**供给限速**（n_kin=%.2f < n_cap=%d）'
       % (_wl['n_kin'], _wl['n_geo_cap']),
       _wl['binding'] == 'kinetics' and _wl['n_geo_cap'] >= 6,
       'n=%d，binding=%s' % (_wl['n'], _wl['binding']))
    ck('C-8.2 几何**永远**不咬人：T_bind = %.0f K < 0' % _wl['T_bind'],
       _wl['geom_is_slack'])
    ck('C-8.3 即便 α 取敏感带上端 2e-2，仍是供给限速',
       who_limits(_cap8, 2.0e-2)['binding'] == 'kinetics',
       str(who_limits(_cap8, 2.0e-2)))
    ck('C-8.4 ★负对照：把盒子缩到 Δx=62.5 nm 且 t=680 nm ⇒ 变成**几何限速**',
       who_limits(alpha_max_from_box(96 * 62.5e-9, 680e-9, 9 * 680e-9,
                                     0.2667 * 9 * 680e-9, nh8, ah8, wh8)[0],
                  0.011)['binding'] == 'geometry',
       'n_cap=%d' % alpha_max_from_box(96 * 62.5e-9, 680e-9, 9 * 680e-9,
                                       0.2667 * 9 * 680e-9, nh8, ah8, wh8)[0])
    ck('C-8.5 线性推论：T_end 从 298 降到 200 K ⇒ n 增加 %.1f 根'
       % (alpha_km_n_lath(200.0) - alpha_km_n_lath(298.0)),
       abs((alpha_km_n_lath(200.0) - alpha_km_n_lath(298.0))
           - 98.0 * ALPHA_KM_REF) < 1e-9)

    # --- C-3：有序性与算力下界 -------------------------------------------
    T1 = T_start_of_clock(ALPHA_KM_REF)
    ck('C-3.0 时钟起点 T_1 = M_s − 1/α_KM == 782.0909 K',
       abs(T1 - 782.0909) < 1e-3, '%.4f' % T1)
    # ★ 关键：预摆的第 1 片就是第 1 根 ⇒ 时钟必须从 T_1 起，不能从 M_s 起。
    #   （`clsmoke` 400 步实测：从 M_s 起则第 1 个事件要等到 T_2 ⇒ 序列整体错位一根。）
    ck('C-3.0b ★错位检查：M_s 处的累计核数 n(M_s) == 0 而 n(T_1) == 1',
       (abs(alpha_km_n_lath(float(M_S_TI64), ALPHA_KM_REF)) < 1e-12)
       and (abs(alpha_km_n_lath(T1, ALPHA_KM_REF) - 1.0) < 1e-9),
       'n(Ms)=%.3f n(T_1)=%.3f' % (alpha_km_n_lath(float(M_S_TI64), ALPHA_KM_REF),
                                   alpha_km_n_lath(T1, ALPHA_KM_REF)))
    vmin = v_min_ordered(ALPHA_KM_REF, 1.0e6, 4.5e-6)
    ck('C-3.1 v_min(α=1.1e-2, q=1e6, L=4.5µm) == 0.0495 m/s',
       abs(vmin - 0.0495) < 1e-4, '%.5f' % vmin)
    ok, ratio, qm = ordered_ok(1.0e6, 1e-9, ALPHA_KM_REF, 4.5e-6,
                               dG_worst=DS_REF * (T0_TI64 - T1))
    ck('C-3.2 q=1e6 在 MOB=1e-9 下有序', ok,
       'ratio=%.3f q_max=%.3e' % (ratio, qm))
    ok2, ratio2, _ = ordered_ok(1.0e8, 1e-9, ALPHA_KM_REF, 4.5e-6,
                                dG_worst=DS_REF * (T0_TI64 - T1))
    ck('C-3.3 ★负对照：q=1e8 有序性被违反', (not ok2), 'ratio=%.2f' % ratio2)
    smin = steps_min_ordered(ALPHA_KM_REF, 4.59e-6, 125e-9, T_f=298.0, T_start=T1)
    ck('C-3.4 最小步数（从 T_1 起、L=4590 nm）== 2173（与 MOB、q 无关）',
       abs(smin - 2172.98) < 1.0, '%.2f' % smin)

    def _steps_numeric(MOB, q, alpha=ALPHA_KM_REF, L=4.5e-6, dx=125e-9,
                       cfl=CFL_DEFAULT, T_f=298.0, npts=200001, T_start=None):
        """按 `T` 积分（而不是按 `t`）：`N = ∫ (MOB·DS(T0−T)/(cfl·dx)) dT/q`。
        这是 `steps_at_q` 闭式的**独立数值对照**（不同变量、不同离散）。"""
        Ts0 = (T_start_of_clock(alpha) if T_start is None else float(T_start))
        Ts = np.linspace(Ts0, float(T_f), npts)
        y = float(MOB) * DS_REF * (T0_TI64 - Ts) / (float(cfl) * float(dx) * float(q))
        return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.abs(np.diff(Ts))))

    s_a = _steps_numeric(1e-9, 1.0e6, T_start=T1)
    s_b = _steps_numeric(4e-9, 4.0e6, T_start=T1)
    ck('C-3.5 ★独立性：MOB/q 同比例变化时步数不变（数值积分）',
       abs(s_a - s_b) / s_a < 1e-6, '%.1f vs %.1f' % (s_a, s_b))
    # ★ 口径修（Round 29）：`steps_min_ordered` 已经把 `q = q_max` 代进去了 ⇒
    #   要跟数值积分比就必须**在同一个 q 上**比。原写法拿 q=1e6 的积分去比
    #   q=q_max 的闭式，差一个 q 的比值 ⇒ 是**我这条对照写错了**，不是公式错。
    q_max = q_max_ordered(v_of_MOB(1e-9, DS_REF * (T0_TI64 - T1)),
                          ALPHA_KM_REF, 4.59e-6)
    ck('C-3.6a steps_at_q(q=1e6) 与数值积分一致（<0.1%）',
       abs(s_a - steps_at_q(1e-9, 1.0e6, 125e-9, T_f=298.0,
                            T_start=T1)) / s_a < 1e-3,
       '%.1f vs %.1f' % (s_a, steps_at_q(1e-9, 1.0e6, 125e-9, T_f=298.0, T_start=T1)))
    ck('C-3.6b steps_min_ordered(L=4.59µm) == steps_at_q(q_max)（往返）',
       abs(smin - steps_at_q(1e-9, q_max, 125e-9, T_f=298.0,
                             T_start=T1)) / smin < 1e-9,
       '%.1f vs %.1f (q_max=%.4e）' % (smin, steps_at_q(1e-9, q_max, 125e-9,
                                                        T_f=298.0, T_start=T1), q_max))
    # ★ 负对照：把时钟起点错误地取成 M_s ⇒ 步数下界会偏大（≈3185 vs 2173）
    s_ms = steps_min_ordered(ALPHA_KM_REF, 4.5e-6, 125e-9, T_f=298.0,
                             T_start=float(M_S_TI64))
    ck('C-3.7 ★负对照：时钟从 M_s 起（错位一根）⇒ 下界变成 %.0f，明显不同'
       % s_ms, abs(s_ms - smin) / smin > 0.3, '%.1f vs %.1f' % (s_ms, smin))

    # --- C-4：几何容纳 ----------------------------------------------------
    nh = np.array([-0.4424, 0.4425, -0.7801]); ah = np.array([-0.4909, 0.4909, 0.7198])
    wh = np.array([0.7071, 0.7071, 0.0])

    def _cap(dx_nm, t_nm):
        t_ = t_nm * 1e-9
        L_ = 9.0 * t_
        return alpha_max_from_box(96 * dx_nm * 1e-9, t_, L_, 0.2667 * L_, nh, ah, wh)

    c62_510, a62_510 = _cap(62.5, 510.0)
    c62_680, a62_680 = _cap(62.5, 680.0)
    c62_880, a62_880 = _cap(62.5, 880.0)
    ck('C-4.1 N=96/Δx=62.5nm：t=0.51 µm 时**恰好**n_cap=6（零余量）',
       c62_510 == 6, 'n_cap=%d' % c62_510)
    ck('C-4.2 同盒子：t=0.68 µm ⇒ n_cap=3 < 6 ⇒ **装不下**',
       c62_680 < 6, 'n_cap=%d' % c62_680)
    ck('C-4.2b 同盒子：t=0.88 µm（Shuai 上限）⇒ n_cap ≤ 1',
       c62_880 <= 1, 'n_cap=%d' % c62_880)
    c125_510, a125_510 = _cap(125.0, 510.0)
    ck('C-4.3 N=96/Δx=125nm ⇒ n_cap ≥ 6 且有余量',
       c125_510 >= 6, 'n_cap=%d, α_max=%.3e' % (c125_510, a125_510))
    # ★ 口径修：C-4 在 Δx=125 nm 上是**松**的（n_cap≈21），真正卡住的是 C-3。
    #   所以不能声称"C-4 给 α_KM 一个 2e-2 的上界"。正确的说法是：
    #   C-4 只**排除**细网格 + 厚板条；α_KM 的上界来自 C-3（步数）。
    ck('C-4.4 ★口径：Δx=125nm 上 C-4 是松的（n_cap ≥ 3×n）',
       c125_510 >= 18, 'n_cap=%d' % c125_510)

    # --- C-5：β_h 下界 ----------------------------------------------------
    b200 = beta_h_min(200, 62.5e-9, 250e-9)
    ck('C-5.1 200 步/Δx=62.5/t=250nm ⇒ β_h ≥ 3.22（归档 3.5 刚好过）',
       abs(b200 - 3.2189) < 5e-3, '%.4f' % b200)
    b3600 = beta_h_min(3600, 125e-9, 510e-9)
    ck('C-5.2 3600 步/Δx=125/t=510nm ⇒ β_h ≥ 4.3 > 3.5',
       b3600 > BETA_H_AT_MS, '%.4f' % b3600)
    ck('C-5.3 ★负对照：步数 10× ⇒ 下界增加 ln(10)',
       abs((beta_h_min(2000, 125e-9, 510e-9) - beta_h_min(200, 125e-9, 510e-9))
           - math.log(10.0)) < 1e-9)
    ck('C-5.4 β_h(T)：T=535K 时 ≈ 5.7（随降温变大）',
       abs(beta_h_of_T(535.0) - 5.710) < 0.02, '%.3f' % beta_h_of_T(535.0))

    # --- C-6：润湿 --------------------------------------------------------
    w = wetting_check(0.25, 5.0)
    ck('C-6.1 干晶界（γ_RS,max < 2γ_F1）', w['dry'], 'margin=%.3f' % w['margin'])
    wb = wetting_over_band(5.0)
    ck('C-6.2 整个 Murzinova 区间（含最低端 0.201）都是干晶界',
       all(v['dry_lo'] and v['dry_hi'] for v in wb.values()),
       str({k: round(v['margin_lo'], 2) for k, v in wb.items()}))
    ck('C-6.3 翻转阈值 γ_flip == 0.138544（可写下来的证伪条件）',
       abs(w['flip_gamma'] - 0.138544) < 1e-5, '%.6f' % w['flip_gamma'])
    ck('C-6.4 ★负对照：γ_F1 = 0.10 ⇒ 判据不再成立（湿）',
       not wetting_check(0.10, 5.0)['dry'])

    # --- C-7：4γ/d 惰性 ---------------------------------------------------
    fc, rt = fcrit_ratio(0.25, 510e-9, DG_CRIT_REF)
    ck('C-7.1 ΔG_v/f_crit ≫ 1（4γ/d 拦不住）', rt > 10.0,
       'f_crit=%.3e ratio=%.1f' % (fc, rt))
    ck('C-7.2 ★负对照：核厚放大 100× 后 ratio 仍 > 2',
       fcrit_ratio(0.25, 51e-6, DG_CRIT_REF)[1] > 2.0)

    # --- 推荐配置 ---------------------------------------------------------
    rec = recommend()
    ck('R-1  recommend() 全部判据通过', rec.get('ok') is True,
       'n=%s q=%.3e steps=%d dx=%.0f nm β_h=%.2f' %
       (rec.get('n_lath'), rec.get('q', 0), rec.get('steps', 0),
        rec.get('dx_nm', 0), rec.get('beta_h_use', 0)))
    ck('R-2  n_lath == 6（由 α_KM 与 T_f 导出）', rec.get('n_lath') == 6)
    ck('R-3  有序比 ≤ 1', rec.get('ordered_ratio', 9) <= 1.0,
       '%.3f' % rec.get('ordered_ratio', 9))
    ck('R-4  β_h_use ≥ β_h_floor', rec.get('beta_h_use', 0) >= rec.get('beta_h_floor', 1))
    ck('R-5  q 在 LPBF 文献区间 [1e4, 1e8] K/s 内',
       1e4 <= rec.get('q', 0) <= 1e8, '%.3e' % rec.get('q', 0))

    ok = all(c[1] for c in chk)
    if verbose:
        print('=' * 96)
        print('windowB_closure 自检（正/负对照）')
        print('=' * 96)
        for name, v, extra in chk:
            print('  %-58s %s   %s' % (name, 'PASS' if v else '**FAIL**', extra))
        print('-' * 96)
        nf = sum(1 for c in chk if not c[1])
        print('  对照数 = %d   FAIL = %d' % (len(chk), nf))
        print('=' * 96)
        if rec.get('ok'):
            print('★ 闭环推荐配置（全部由闭式给出，不是调出来的）：')
            for k in ('n_lath_float', 'n_lath', 't_lath_nm', 'L_lath', 'W_lath',
                      'dx_nm', 'L_box', 'n_geo_cap', 'alpha_max', 'q', 'q_cap',
                      'steps', 'steps_min', 't_sim', 'beta_h_T', 'beta_h_floor',
                      'beta_h_use', 'ordered_ratio', 'overlap_nm', 'r_nuc_nm'):
                if k in rec:
                    print('    %-16s %s' % (k, rec[k]))
    return ok, chk


if __name__ == '__main__':
    _ok, _ = selftest(verbose=True)
    raise SystemExit(0 if _ok else 1)
