# 文献检索任务书：Ti-6Al-4V 激光粉末床熔融（LPBF）组织仿真所需参数与尺度

> 版本：2026-09-22 ｜ 用途：交给检索人员独立执行
> 交付物：§7 的填写表（每条必须带 DOI + 图表号 + 原文句子）

---

## 0. 这份文件怎么用

- 第 1 节是**背景**：读一次就够，目的是让你能判断"哪篇文献算相关"。
- 第 3 节是**任务分块 A–G**：每块给出"要回答的问题 / 需要的量（带单位）/ 英文关键词 / 优先来源 / 判据"。
- 第 4 节是 **P0 清单**：这 6 项决定整个模型能不能成立，**先做这 6 项**。
- 第 5 节是**必须避免的陷阱**：本项目历史上多次因为"同一个词指不同东西"而得出错误结论，请**逐条读完再开始搜**。
- 第 7 节是**填写模板**：直接复制填。

**最重要的一条要求**：每条数据必须能追溯到 **DOI + 具体图/表/页码 + 原文句子**。
如果只找到二手转述（"某文说约 100 µm"），必须标注**"二手"**并尽量找到原始出处。

---

## 1. 背景（为什么需要这些数）

### 1.1 项目一句话
我们要为 **Ti-6Al-4V 的 LPBF** 建立一个"从熔池凝固到冷却到室温"的**多尺度组织仿真**，
用来预测 **prior-β 晶粒形貌 + 晶内 α′ 马氏体组织 + V 的偏析**，最终服务于力学/化学性能。

### 1.2 我们要建的仿真是什么（决定你需要找哪些量）
- **空间 1**：熔池/晶粒尺度（**几十～几百 µm**）——prior-β 晶粒的形貌、竞争生长、织构、晶界偏析。
- **空间 2**：晶内尺度（**0.1～1 µm**）——α′ 板条 / 变体群 / α+β 分解 / β 纳米薄膜。
- **时间**：熔池寿命 **0.1～1 ms**；凝固后热循环 **秒～小时**。
- 方法：**相场（含 Gibbs 面表示）+ 从热场提取的 (G, R, 冷却速率) + CALPHAD 热力学**。

### 1.3 为什么必须查文献，不能拍参数
本项目已经吃过亏：**两个关键参数是"自己标定出来的"，不是文献值**——
固液分配系数 `k`、晶界扩散系数 `D_GB`、晶界偏析 `Γ0/ΔH_seg/ΔS_seg` 全部是**标定值**。
而**参数的错会直接改变结论**（例如若 `k` 实际接近 1，则"溶质被排斥→边界层→晶界富集"这条主线会大幅弱化）。
所以**这次检索的核心目的就是把"标定值"换成"有出处的值"**。

---

## 2. 交付要求

### 2.1 每条必须给的字段（模板见 §7）
1. **量名 + 符号 + 单位**
2. **数值**（若是范围，给范围 + 典型值）
3. **适用条件**：合金牌号（Ti-6Al-4V / Ti64 / TC4 / Grade 5）、氧含量、工艺（**LPBF 优先**，其次 EBM / DED / 激光熔覆 / 常规铸造）、温度区间、取向（若适用）
4. **出处**：作者 + 年 + 期刊 + **DOI** + **图号/表号/页码** + **原文句子（英文原句）**
5. **测量/计算方法**：EBSD / TEM / APT / OM / 原位 XRD / CALPHAD / MD-DFT / 仿真拟合
6. **可信度自评**：① 直接测量 ② 由多个来源一致外推 ③ 单一来源 ④ 二手转述
7. **冲突记录**：若找到不同值，**并列列出**并说明条件差异（不要自行取平均）

### 2.2 什么算"找到了"
- ✅ 有**原文句子 + DOI + 图表号**，且**条件清楚**。
- ✅ 多个独立来源一致（列出全部）。
- ❌ 只有综述里的一句"typically ~X"而**找不到原始出处** ⇒ 记为"二手/待追原始"。
- ❌ 从别的合金（钢、铝、镍基）搬来的值 ⇒ 可以给，但**必须标"类比，非同材料"**。

### 2.3 质量要求
- **不要做平滑或取舍**：给范围就给范围，给冲突就给冲突。
- **区分"测量值"与"拟合/仿真反推值"**，后者要注明用了什么模型。
- **凡涉及温度依赖**，要给出 **Arrhenius 形式**（`X = X0·exp(−Q/RT)`）的 `X0` 与 `Q`，而不是单个温度点的值。
- 若某量**在 Ti-6Al-4V 上确实不存在**，请明确写 **"未找到，可能不存在于公开文献"** —— 这也是有用的结论。

---

## 3. 检索任务分块

### A. 热物性与相变基础参数

**要回答**：Ti64 在 LPBF 温度区间（300–3200 K）的热物性、相变温度与潜热。

| 要查的量 | 单位 | 条件 | 备注 |
|---|---|---|---|
| 固相线 / 液相线温度 | K 或 °C | 含 O 的影响 | 模型现在用 1923 K 作熔点 |
| **熔化潜热 L**（固→液） | kJ/kg | LPBF | 已有一处 286 kJ/kg，**需要第二、第三来源** |
| 热导率 k(T) | W/(m·K) | 300–2000 K | 已有 `1.25+0.015T` / `3.15+0.012T` |
| 比热 Cp(T) | J/(kg·K) | 300–2000 K | 已有 `483+0.215T` / `412.7+0.18T` |
| 密度 ρ(T) | kg/m³ | 300–2000 K | 已有 `4512−0.154T` |
| **热扩散率 α(T)=k/(ρCp)** | m²/s | 300–2000 K | 已有推导 7.2e-6（1500 K 附近） |
| **β 转变温度 T_β（β transus）** | K 或 °C | 含 O 的影响 | 常见值 ~995–1010 °C |
| **Ms（马氏体开始温度）** | K 或 °C | 含 Al/V/O 的依赖 | 已有一处 575 °C，**需要成分依赖式** |
| Mf（马氏体结束温度） | K 或 °C | — | — |
| **临界冷却速率（α′ 形成阈值）** | K/s | LPBF | 已有一处 >410 K/s |

**英文关键词**
`Ti-6Al-4V thermal properties temperature dependent`；`Ti64 latent heat of fusion`；
`thermal diffusivity titanium alloy temperature`；`beta transus Ti-6Al-4V oxygen`；
`martensite start temperature Ti-6Al-4V Ms`；`critical cooling rate alpha prime titanium`

**优先来源**：Thermo-Calc/JMatPro 数据库说明、CALPHAD 文献、热物性手册、原位 XRD 工作。

---

### B. 固液分配与凝固微观偏析 ← **P0**

**要回答**：Ti64 凝固时 V、Al 到底怎么分配？微观偏析有多强？

| 要查的量 | 单位 | 条件 | 备注 |
|---|---|---|---|
| **固液分配系数 k_V** | — | β 凝固 | ⚠ **模型现在用 0.63（未核实）**；若实际≈1，主链条要改 |
| **固液分配系数 k_Al** | — | β 凝固 | 同上 |
| k 的温度/成分依赖 | — | — | 给 Arrhenius 或多项式？ |
| 凝固界面温度 / 凝固区间 ΔT_f | K | — | — |
| **一次枝晶/胞间距 λ₁ 与冷却速率的关系** | µm | `λ₁=A·(dT/dt)^(−n)` | **要 A 与 n**，以及适用区间 |
| 二次臂间距 λ₂ 同上 | µm | — | — |
| **最后凝固区 V 的富集倍数** | — 或 wt% | — | APT / STEM-EDS 数据优先 |
| Scheil 与杠杆律的适用性判据 | — | — | 有无实测 k_eff |

**英文关键词**
`partition coefficient vanadium titanium Ti-6Al-4V solidification`；
`solute partitioning Al V beta titanium alloy dendrite`；`microsegregation laser powder bed fusion Ti-6Al-4V`；
`primary dendrite arm spacing cooling rate titanium`；`Scheil solidification Ti-6Al-4V`

**优先来源**：凝固理论（Kurz & Fisher 体系）、CALPHAD-Scheil 计算、APT/STEM-EDS 实测、原位 X 射线。

---

### C. 组织特征尺寸（分尺度）← **含 P0**

**要回答**：各层级组织的尺寸，以及它们与工艺/热条件的定量关系。

| 层级 | 要查的量 | 单位 | 备注 |
|---|---|---|---|
| 凝固晶粒 | prior-β 柱状晶**宽** | µm | 已有 124–168 µm；**需要更多来源 + 与道宽的关系** |
| | prior-β 柱状晶**长/长径比** | µm / — | 已有 >1 mm、长径比 4.5–17.4 |
| | **等轴 prior-β 晶粒尺寸** | µm | 已有 100–200 µm；**需要纯 LPBF（非超声/非添加）的统计** |
| 凝固亚结构 | **β 胞 / 枝晶臂间距** | µm | **未核实**，需要 LPBF 实测 |
| 相变单元 | **α′ 集束 / 变体群尺寸** | µm | 用户文档给 5–50 µm；**需要原始出处** |
| | **α′/α 板条宽 λ_lath** | µm | 已有 0.51–0.88 / 0.24–0.30 µm 两组 |
| | **α′/α 板条长** | µm | 已有 ~5 µm 一组 |
| | **λ_lath 与冷却速率的定量关系 A、n** | — | ⚠ **P0：这是"能否不逐条仿真板条"的关键** |
| | **α′ 变体数（实际形成几个 Burgers 变体）** | — | 12 个可能，实际常只形成数个～十几个 |
| 分解产物 | **β 纳米薄膜 / 颗粒厚度** | nm | 已有 5–100 nm（用户文档）；**需要 TEM/APT 原始出处** |
| | β 薄膜间距 | nm | — |
| | **晶界 α（GB-α）厚度** | µm | **未核实** |
| | 位错密度（沉积态） | 1/m² | — |

**英文关键词**
`prior beta grain width laser powder bed fusion Ti-6Al-4V EBSD`；
`equiaxed prior beta grain size LPBF titanium`；`alpha prime lath width cooling rate Ti-6Al-4V`；
`martensite lath width relationship cooling rate`；`alpha colony size variant selection titanium`;
`beta phase nano film lath interface TEM Ti-6Al-4V`；`grain boundary alpha thickness Ti-6Al-4V`;
`cell spacing beta solidification Ti-6Al-4V`

**优先来源**：EBSD/TEM/APT 实测论文、原位 XRD（同步辐射）。

---

### D. 界面性质与动力学 ← **P0（项目里全是标定值）**

**要回答**：晶界/相界的偏析、扩散与迁移率的**真实值**。

| 要查的量 | 单位 | 条件 | 备注 |
|---|---|---|---|
| **Γ0 单层饱和（Gibbs 过剩上限）** | mol/m² | Ti64 晶界 | 项目用 2.14e-5（标定值） |
| **ΔH_seg（偏析焓）** | J/mol | V 在 β 晶界 | 项目用 −11931（**反解值**） |
| **ΔS_seg（偏析熵）** | J/(mol·K) | 同上 | 项目设 0（**文献缺失**）→ 请核实是否真的不存在 |
| **晶界富集因子（APT 实测）** | — | V、Al、O、Fe | APT 数据优先 |
| **D_GB(T)：晶界扩散** | m²/s | 含 Arrhenius `D0, Q` | 项目用指派值 4e-10；**区分 β/β 晶界 vs α/β 相界** |
| D_α(T)、D_β(T)：体扩散（V、Al） | m²/s | 含 Arrhenius | — |
| 晶界迁移率 M_GB(T) | m⁴/(J·s) | 含 Arrhenius | 已有 `GBmob0=232, Q=3.234 eV`，需核实 |
| α/β 界面迁移率 | m⁴/(J·s) | — | 分解阶段用 |
| 界面能：β/β 晶界能 σ_GB（与错配角的关系） | J/m² | — | 项目用 0.6 |
| α/β 界面能 | J/m² | — | — |
| Gibbs 吸附对 σ 的影响（`dσ/dΓ`） | J/m² per mol/m² | V 在晶界 | — |
| **12 个 Burgers 变体的相变形状应变张量** | —（3×3） | Ti64 | 做变体选择必需 |
| 弹性常数 C_ij(T) 各相 | GPa | β、α、α′ | 已有 E(T) 表（PMC11766489），需完整张量 |
| 异质形核：氧化物的润湿角/形核势垒 | — | — | 用于等轴晶形核 |

**英文关键词**
`grain boundary segregation enthalpy titanium vanadium`；`APT grain boundary segregation Ti-6Al-4V`；
`grain boundary diffusion titanium alloy Arrhenius`；`self diffusion vanadium titanium beta`；
`grain boundary mobility titanium beta`；`Gibbs adsorption grain boundary energy solute`；
`Burgers orientation relationship variant strain Ti-6Al-4V`；`elastic constants beta alpha titanium temperature`

**优先来源**：APT/STEM-EDS 实验、DFT/MD 计算、CALPHAD 界面数据库、扩散手册（Landolt-Börnstein）。

---

### E. 热历史与工艺条件

**要回答**：LPBF 里真实的温度-时间轨迹是什么样。

| 要查的量 | 单位 | 备注 |
|---|---|---|
| **冷却速率范围（分位置）** | K/s | 已有 ≥1e5；需要分布（熔池底/顶/尾部） |
| **熔池寿命** | ms | 已有 0.1–1 ms（用户文档） |
| 熔池尺寸（宽/深/长）与 P、v、光斑的关系 | µm | 已有 80–180 / 40–120 / 200–800 µm |
| **G（温度梯度）与 R（界面速度）的范围与 (G,R) 图** | K/m, m/s | 已有 1e5–1e7 K/m、0.01–1 m/s |
| **CET 判据（柱状→等轴）** | — | `G^n/R` 形式的系数与指数 |
| **多层热循环**：峰值温度、超过 400/600/700 °C 的时间、循环次数 | K, s, — | **α′ 分解的关键** |
| 基板预热温度对组织的影响 | K | — |
| **CCT / TTT 图（α′→α+β）** | — | 时间-温度-相组成 |

**英文关键词**
`cooling rate laser powder bed fusion Ti-6Al-4V in situ measurement`；
`melt pool lifetime cooling rate LPBF`；`columnar to equiaxed transition criterion additive manufacturing`；
`solidification map G R additive manufacturing`；`thermal cycling number of cycles LPBF Ti-6Al-4V`；
`CCT diagram Ti-6Al-4V martensite decomposition`；`preheating substrate temperature LPBF microstructure`

**优先来源**：同步辐射原位（X 射线成像/衍射）、高速红外测温、FE 热模型论文。

---

### F. 现有仿真方法的"设置参数"（用于选型与对标）

**要回答**：别人做同类仿真时用了什么分辨率/域/算力。

| 要查的量 | 备注 |
|---|---|
| 相场**微观弹性**做马氏体的标准设置：界面宽 δ、网格 Δx、域尺寸、变体数 | 目标：知道"要做 0.1–1 µm 域需要多少资源" |
| Ti64 上 **β→α 变体选择**的 3D 定量相场（2014 OSU 博士论文 `osu1397655766`）的具体设置 | **唯一一篇 Ti64 同类工作**，重点 |
| Ti64 的 **α′→α+β 分解**相场（Mater. Des. 2024, `10.1016/j.matdes.2024.112949`）的设置 | 是否有开源代码 |
| LPBF 里 **元胞自动机（CA）**做晶粒竞争的标准设置 | 是否有开源代码/参数 |
| **均质化相分数模型**（Nitzler 2021, `10.1186/s40323-021-00201-9`）的演化方程与参数 | 想要它的方程形式 |
| 有没有**开源代码**（MICRESS / OpenPhase / PRISMS-PF / MOOSE 模块 / 自研） | 开源最重要 |

**英文关键词**
`phase-field microelasticity martensite grid spacing domain size`；
`phase field variant selection titanium beta alpha 3D`；`lath martensite phase field 24 variants simulation setup`；
`cellular automaton grain growth LPBF open source`；`MICRESS OpenPhase PRISMS-PF additive manufacturing`

---

### G. 必须澄清的"定义陷阱"（**请把这部分当成独立任务**）

同一篇文献里，下面这些词**可能指完全不同的物理量**。请对每个词收集 **2–3 篇文献的明确定义**，并指出常见分歧。

| 词 | 常见歧义 | 你需要写清 |
|---|---|---|
| **grain size / 晶粒尺寸** | prior-β 的**宽** / **长** / 等效圆直径 / 截线长度 | 定义与统计方法（EBSD 阈值？OM？） |
| **α′ lath width** vs **α colony size** vs **α lath** | 是"单条板条宽"还是"板条群尺寸" | 二者比值关系 |
| **k（分配系数）** | ⚠ **固液分配 k** 与 **α/β 固态分配 k** 是**两个不同的数** | 必须**分别**给出，不能混用 |
| **melt pool depth** | 是否含匙孔/是否含飞溅 | 测量方法 |
| **cooling rate** | 局部瞬时 `dT/dt` / 平均 GR / 通过某温度区间的时间 | 定义式 |
| **grain boundary segregation** | 界面**过剩量 Γ** / 界面**浓度** / **富集因子** | 单位与换算 |
| **Ms** | 是开始转变温度还是某分数对应的温度 | 定义 |
| **"细晶"** | 在 LPBF 里等轴 prior-β 其实 **100–200 µm**（并不细）；真正细的是 α′ 板条（0.25–0.9 µm） | 请给出具体数值 |
| **孔隙率/未熔合** | 与组织尺度的关系 | — |

---

## 4. 最高优先级（P0）—— 先做这 6 项

| # | 要查的量 | 为什么是 P0 |
|---|---|---|
| **P0-1** | **固液分配系数 k_V、k_Al**（Ti64，β 凝固） | 模型现在用 0.63（自标定）。若实际≈1，"溶质排斥→边界层→晶界富集"这条主线会大幅弱化；**所有偏析结论都依赖它** |
| **P0-2** | **λ_lath = A·(dT/dt)^(−n)** 的 A、n（Ti64 或其最近类比） | 决定"能不能不逐条仿真板条、改成用冷却速率映射"——这是省算力的关键 |
| **P0-3** | **D_GB(T) 的 Arrhenius（D0, Q）**，并区分 β/β 晶界与 α/β 相界 | 项目现在用**指派值** 4e-10 m²/s；晶界扩散正是项目的核心机制 |
| **P0-4** | **Γ0、ΔH_seg、ΔS_seg**（V 在 Ti64 晶界的偏析） | 项目用反解值、ΔS 设 0；**请核实是否真的没有文献值** |
| **P0-5** | **β 纳米薄膜的厚度与间距**（TEM/APT） | 决定"面超额量"路线的参数；也是"板条尺度不可网格分辨"的直接依据 |
| **P0-6** | **Ms 及其对 Al/V/O 的依赖式** | 决定 α′ 是否形成、形成多少 |

---

## 5. 检索工具与来源建议

- **数据库**：Web of Science、Scopus、Google Scholar、**OpenAlex**（免费 API）、**Europe PMC**（有全文 XML）、**J-Stage**（日文期刊，HTML 全文可读）、ScienceDirect、Springer。
- **优先期刊**：Acta Materialia、Materials & Design、Additive Manufacturing、Journal of Materials Science & Technology、Metallurgical and Materials Transactions A、Computational Materials Science、npj Computational Materials、Materials Science & Engineering A、Scripta Materialia、International Journal of Plasticity。
- **实验数据优先于仿真数据**；**原位（in-situ）数据优先于事后（ex-situ）**。
- **优先 LPBF（SLM/PBF-LB）**；EBM、DED、WLAM、常规铸造/锻造的数值**必须单独标注工艺**，不能混用。
- 若某值只在**热处理后**的样品上测得，请注明（本项目关注的是**沉积态 + 单次热历史**）。

---

## 6. 提交格式

1. **一份主表**（按 §3 的 A–G 分块，用 §7 的字段）。
2. **一份 P0 摘要**（6 条，每条 3–5 行：值 + 条件 + 出处 + 可信度 + 有没有冲突）。
3. **一份"未找到"清单**（明确写哪些量在公开文献里查不到 —— 同样重要）。
4. **一份"定义分歧"说明**（§3G 的结果）。

---

## 7. 填写模板（直接复制）

| 编号 | 量名/符号 | 单位 | 数值（范围/典型） | 适用条件（合金/工艺/温度/取向） | 出处（作者+年+期刊） | DOI | 图/表/页 | 原文句子 | 测量或计算方法 | 可信度(1-4) | 冲突记录 | "未找到"标记 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A-01 | 熔化潜热 L | kJ/kg |  | Ti-6Al-4V, LPBF 温区 |  |  |  |  | CALPHAD / DSC |  |  |  |
| B-01 | 固液分配系数 k_V | — |  | β 凝固 |  |  |  |  |  |  |  |  |
| C-01 | prior-β 柱状晶宽 | µm |  | LPBF, 沉积态 |  |  |  |  | EBSD |  |  |  |
| C-02 | λ_lath 幂律 A, n | — |  | α′ 板条 vs 冷却速率 |  |  |  |  |  |  |  |  |
| D-01 | D_GB(T) 的 D0, Q | m²/s, kJ/mol |  | β/β 晶界 |  |  |  |  |  |  |  |  |
| D-02 | ΔH_seg, ΔS_seg | J/mol, J/(mol·K) |  | V 在 β 晶界 |  |  |  |  | APT/DFT |  |  |  |
| E-01 | 冷却速率分布 | K/s |  | LPBF, 熔池内位置 |  |  |  |  | 原位 X 射线 |  |  |  |
| F-01 | 马氏体相场设置（δ, Δx, 域, 变体数） | — |  | 3D 相场微观弹性 |  |  |  |  | 仿真论文 |  |  |  |