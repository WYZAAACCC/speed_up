# 实施计划（v2 路线）

> 配套 `RESEARCH_INTENT.md`（v2）与 `MATH_FRAMEWORK.md`。
> 目标：把「Window A (CA) -> Window B (局部 PF) -> Window C (Gibbs 面)」推到**物理正确、可验证、能训算子**的状态。
>
> 计划原则：
> 1. 每一阶段都有**可执行的验收判据**（不是"看起来对了"）；
> 2. **关键路径最短**：先打通两级之间唯一的接口条件（§P1.1），否则后面全是白做；
> 3. **不擅自启动生产跑**；长任务先问；
> 4. **20 核并行**：互不干扰的 smoke 算例并行跑，各自独立目录（避免 CSV 同名覆盖的坑）；
> 5. 只在 F 盘工作；不动生产原件 `pipeline/stage1_meltpool_c.i`。
> 6. **要实现的仿真是三维的。2D 只能作为代码验证手段，绝不能把 2D 跑通视为仿真成功**（用户 2026-09-22 硬要求）。⇒ 每阶段验收判据里 **3D 结果必须单独列出**；2D 结果只能出现在「验证」一栏并显式标注。

---

## 0. 已有资产与复用决定

| 资产 | 复用方式 |
|---|---|
| @@pipeline/gibbs/prod3d/@@（MOOSE：弥散 PF + Gibbs 面机制 + 显式交错 + 守恒 sink + 3D 副本） | **整体转为 Window B 的 PF 引擎**；其中 Gibbs 面机制（@@GBFluxExchange@@ / @@GBSoluteSink@@ / 显式交错）**直接转为 Window C 的基础** |
| `pipeline/stage1_meltpool_c.i`（生产弥散界面熔池模型） | **只读、不动**。作为 Window B 的**热历史提供者**（T 场 / G / R / 冷却速率）与对照 |
| `thermal_layer.py`（本目录，已验证的焓式热层） | **L1-T 层参考实现**：既可作为独立热层，也可用来**验证**移入 MOOSE 后的焓方程是否等价 |
| `irf_ti64.csv`（界面响应函数 @@V(\Delta T)@@，115 点） | **Window A 的直接输入** |
| `verify_framework.py` / `thermal_layer.py` | 当作**框架 CI**：每次改动物理后重跑 |
| `CALPHAD_REQUEST.md` | 数据任务的执行件（外部依赖） |

> **结论**：不需要从零建代码库。**Window A(CA) 是唯一全新的部分**，Window B/C 主要是在既有 MOOSE 副本上扩展。

---

## 1. 阶段划分与判据

### Phase 0 —— 数学框架 ✅ **已完成（2026-09-22）**

| 交付 | 状态 |
|---|---|
| `MATH_FRAMEWORK.md`（850+ 行，四层方程 + 接口 + 守恒 + V&V） | ✅ |
| `verify_framework.py`（76 条判据：55 PASS / 7 WARN / 6 FAIL / 8 RULE） | ✅ |
| `thermal_layer.py`（焓式能量方程 + 潜热，11/11 PASS） | ✅ |
| `irf_ti64.csv`（@@V(\Delta T)@@ 表） | ✅ |
| `CALPHAD_REQUEST.md`（26 个量的数据任务书） | ✅ |

---

### Phase 1 —— 打通两级接口 + Window A 骨架（**关键路径**）

#### P1.1 ⭐ PF @@\leftrightarrow@@ LKT 薄界面渐近匹配（**最高优先级**）

**为什么最优先**：它是 CA 与 PF 两级之间**唯一的可检验接口条件**（`MATH_FRAMEWORK.md` §7.2）。
不做它，两级接不上，后面所有耦合都是假的。它同时也是仓库里反复出现的「缺口 #3 溶质截留」的真正根源。

| 项 | 内容 |
|---|---|
| 算例 | 1D 定向凝固（温度梯度 @@G@@ + 拉速 @@V@@ 给定），单相 + 一个溶质 |
| 做法 | 相场求解，固定 @@W/V@@，@@W@@ 减半三次；与 `irf_ti64.csv` 的 @@V_{\mathrm{LKT}}(\Delta T)@@ 对比 |
| 必要项 | 溶质方程里的**抗截留通量**（量级 @@\sim W\,\partial_t\varphi/|\nabla\varphi|\,(c_l^0-c_s^0)@@） |
| 判据 1 | @@V_{\mathrm{PF}}(\Delta T)@@ 收敛到 @@V_{\mathrm{LKT}}(\Delta T)@@，残差按 @@O(W)@@ 下降 |
| 判据 2 | 有效分配系数 @@k_{\mathrm{eff}}\to k_e=0.6303@@（现在是 0.877 的伪影，见仓库 P0 记录） |
| 判据 3 | 与**解析解**对照：平面前沿的稳态溶质剖面 @@c(x)=c_0[1+\frac{1-k}{k}e^{-Vx/D}]@@ |
| 代价 | 1D ⇒ 分钟级；可并行跑多档 @@W@@ |

#### P1.2 Window A：三维 CA（滑动窗口）  ✅ **已完成（2026-09-22）**

> 已实现并验证：三维 CA（`ca3d.py`）、21 项三维判据 20 PASS/1 WARN/0 FAIL、盒子 A（450x450x200 µm, dx=10 µm）0.9 s 跑完。详见 `CA3D_REPORT.md`。
> **第二轮已完成**：**液相传质子模型**（`ca3d_solute.py`，11 项判据全过） + active region margin 收敛（gid 差异 0）。
> **第三轮已完成**：两处**物理正确性修正**（IRF 严禁外推 + 初始固相区外延填充）、**CET 体形核**（三维，通过）。
> **仍余（开放项）**：倾斜梯度下的**取向选择**未复现（双晶正对照通过，多晶+倾斜+有限域需专门收敛性研究）；输运与 CA 的 dt 收敛性检验。

原始条目（保留作依据）：

| 项 | 内容 |
|---|---|
| 交付 | 一个 2D CA 求解器（Python 起步，接口按 `MATH_FRAMEWORK.md` §4） |
| 必含 | ① 界面响应函数查表（读 `irf_ti64.csv`）② decentered octahedron 捕获规则（含取向）③ 连续形核（CNT 或 Greer free-growth）④ 滑动窗口 + halo |
| 正对照 A | **双晶取向竞争**：两个取向不同的晶粒在给定 @@G@@ 下竞争，验证"取向能被正确选择"（Walton–Chalmers）+ 长大速度对取向敏感 |
| 正对照 B | 单晶定向凝固：CA 前沿位置 vs 解析的 @@x=VG^{-1}\Delta T@@ 关系 |
| 正对照 C | **halo 收敛**：@@N=L/l_D@@ 从 3 到 7，界面处成分的相对误差按 @@0.587e^{-N}@@ 下降（§4.1 的闭式判据，可直接数值验证） |
| 判据 | 三组对照全过；且与 2D 生产熔池的晶粒形貌量级一致（柱状晶宽 100~170 µm） |
| 代价 | 2D、@@10^3\sim10^4@@ 胞 ⇒ 分钟级 |

#### P1.3 CALPHAD 数据接入（等外部）

| 项 | 内容 |
|---|---|
| 交付 | `calphad_ingest.py`：读填好的表 -> 按 §5.2 闭式算 @@\Delta g_V,\Delta g_{Al},T_L,T_S,\Delta T_0,m_L@@ -> 与 CALPHAD 直接对账 |
| 判据 | 闭式与 CALPHAD 的 @@T_L,T_S@@ 偏差 @@<2@@ K；否则改用 Redlich-Kister |
| 联动 | 更新 `irf_ti64.csv`、Scheil 剖面、CET 判据 |

#### P1.4 求解能力（为 Phase 3 铺路，与 P1.1~P1.3 并行）

| 项 | 内容 |
|---|---|
| 交付 | MOOSE 上 AMG/迭代求解器（GAMG+ASM 或 fieldsplit）的**基准与选型报告** |
| 判据 | 3D、@@\Delta x=0.5@@ µm、@@20^3@@ µm 盒子（~3.2e5 自由度）能在 **22 GB 内存内**跑通 |
| 理由 | `MATH_FRAMEWORK.md` §7.5：直接解外推 ~10 GB，自由度再涨必撞墙 |

---

### Phase 2 —— Window B：局部精细 PF（2D 先行）

#### P2.1 B1 子模型：beta -> alpha-prime（位移型 / 非守恒）

| 项 | 内容 |
|---|---|
| 方程 | 非守恒序参量 + Landau 势垒 @@\propto(T-M_s)@@ + 应变耦合 |
| 关键 | **V 不分配**（@@c@@ 继承 beta 的过饱和值）；athermal 极限用 Koistinen-Marburger 交叉校验 |
| 判据 | @@f_{\alpha^\prime}(T)@@ 与 @@1-\exp[-\alpha_{KM}(M_s-T)]@@ 形状一致；@@M_s=848@@ K |
| 判据 | **变体选择**：给定单轴应力，被选中的变体满足 @@\Delta E_v=-\sigma^{\mathrm{ext}}\!:\!\varepsilon^{0,v}@@ 最小 |

#### P2.2 B2 子模型：alpha-prime -> alpha+beta（扩散型 / 守恒）

| 项 | 内容 |
|---|---|
| 方程 | 多相场 + Cahn-Hilliard（V 守恒；**三元时必须同时带 Al**，见 D2） |
| 判据 1 | 分解时间标度：@@t\sim L_{\mathrm{lath}}^2/D_V^{\alpha}@@ ⇒ 973 K 时 ~5 h 量级（与 Boccardo 2024 的原位实验同量级） |
| 判据 2 | **继承长度尺度**：alpha 板条宽度不显著粗化（文献结论：@@\alpha+\beta@@ 继承 alpha-prime 的板条长度尺度） |
| 判据 3 | V 守恒到 @@10^{-6}@@ 相对 |

#### P2.3 晶界 alpha 膜（第三类形核位置）

| 项 | 内容 |
|---|---|
| 位置 | 沿 prior-beta 晶界优先形核（界面能优势） |
| 判据 | 与 EBSD/APT 观察到的晶界 alpha 厚度量级一致 |

---

### Phase 3 —— 3D 化 + A->B 耦合

| 项 | 内容 | 判据 |
|---|---|---|
| P3.1 | A->B 的**投影算子 @@\Pi@@**（逐胞质量守恒） | @@\int_{\Omega_i}c\,\mathrm dV=\bar c_i|\Omega_i|@@ 到机器精度；直接插值会抹平偏析（要作为**反例**显式跑一次） |
| P3.2 | Halo-in / Core-out | core 尺寸加倍，输出不变（domain-size convergence） |
| P3.3 | 拖曳反馈（溶质 -> 拓扑） | 解隐式 @@v=M_{GB}[\Delta G-P_{\mathrm{drag}}(v)]@@；验证"钉扎/脱钉"两种状态都存在 |
| P3.4 | 盒子 A 3D（450x450x200 µm，@@\Delta x=10@@ µm） | 4e4 单元，分钟级 |
| P3.5 | 盒子 B 3D（@@20^3@@ µm，@@\Delta x=0.5@@ µm） | 依赖 P1.4 的求解器 |

---

### Phase 4 —— Window C：Gibbs 面

| 步 | 内容 | 判据 |
|---|---|---|
| P4.1 | 静态界面 @@\Gamma_i@@（固定几何） | 吸附方程 @@\mathrm d\gamma/\mathrm d\mu=-\Gamma@@ 数值微分对账（Langmuir 等温线） |
| P4.2 | 面内扩散 @@\nabla_s\!\cdot(D^s\nabla_s\Gamma)@@ | 1D 面上与解析解对账 |
| P4.3 | 面-体交换 + 总守恒 | @@\mathrm d/\mathrm dt[\int_\Omega c\,\mathrm dV+\int_\Sigma\Gamma\,\mathrm dA]=@@ 外部通量 |
| P4.4 | 移动曲面（界面跟着 eta 走） | 三叉线通量平衡 @@\sum_s J_s=0@@ |
| P4.5 | 参数标定 | @@\Delta H_{seg}@@ 从 Tan 2016 的 923 K APT 锚点反解（@@-12\sim-18@@ kJ/mol）；@@\Delta S_{seg}@@ 缺失 ⇒ 给不确定度带 |

---

### Phase 5 —— 神经算子

| 步 | 内容 | 判据 |
|---|---|---|
| P5.1 | 生成 Window B 的 teacher 数据（多热史 / 多取向 / 多成分） | 覆盖度报告（OOD 检测用） |
| P5.2 | Halo-in / Core-out 的 FNO / U-AFNO / DeepONet / PINO 对比 | 长时 rollout 稳定性 + 守恒 + QoI（不是单步 MSE） |
| P5.3 | 守恒约束损失（质量 / 相分数 / 非负 / 自由能耗散） | 守恒残差 @@<10^{-6}@@ |
| P5.4 | OOD 回退（不确定度门 + 主动学习） | 超训练域时自动回退 teacher |
| P5.5 | Window C 的界面算子 | 同上 |

---

## 2. 依赖关系与关键路径

@@
P1.1 (PF<->LKT 匹配) ──┐
                      ├──> P3.1 (Pi 守恒) ──> P3.3 (拖曳) ──> Phase 5
P1.2 (2D CA) ─────────┘
P1.4 (AMG/MPI) ───────────> P3.5 (3D 盒子 B)
P1.3 (CALPHAD) ───────────> 更新 irf / Scheil / CET（可随时插入）
Phase 2 (Window B) ───────> Phase 3 / Phase 5
Phase 4 (Window C) ───────> P5.5
@@

**关键路径 = P1.1 -> P1.2 -> P3.1 -> Phase 5。**
P1.3 / P1.4 / Phase 2 / Phase 4 都可**并行**。

---

## 3. 本机算力预算（实测口径）

| 配置 | 自由度 | 单次 Jacobian | 内存 |
|---|---|---|---|
| 2D CA（@@10^3\sim10^4@@ 胞） | ~1e4 | ms 级 | < 100 MB |
| 1D PF 匹配算例 | ~1e3 | ms 级 | < 100 MB |
| 2D PF（盒子 B，@@\Delta x=0.5@@ µm） | ~8e4 | ~1 s | ~1 GB |
| 3D 盒子 A（@@\Delta x=10@@ µm） | 1.2e5 | ~10 s | ~2~4 GB |
| 3D 盒子 B（@@\Delta x=0.5@@ µm） | 3.2e5 | 数十 s | ~10 GB（需 AMG） |

机器：20 逻辑核，WSL 内存上限 24 GB（规划 **22 GB**）。
**并行策略**：Phase 1/2 的 smoke 算例互相独立 ⇒ 同时跑 4~8 个，各自独立目录（避免 CSV 同名覆盖）。

---

## 4. 立即可做的下一步（按顺序）

| # | 动作 | 依赖 | 预计 |
|---|---|---|---|
| 0b | **P1.2 余项（开放）**：倾斜梯度取向选择（域放大 + 侧向周期边界 + 分离位置/取向效应）+ dt 收敛性 | 无 | 中 |
| 1 | **P1.1**：1D PF @@\leftrightarrow@@ LKT 匹配算例（含抗截留通量） | 无 | 本轮可达 |
| 2 | **P1.2**：2D CA 骨架 + 双晶取向正对照 | 无 | 本轮可达 |
| 3 | **P1.2c**：halo 收敛的数值验证（对 §4.1 闭式） | 步骤 2 | 短 |
| 4 | **P1.4**：AMG/MPI 求解器选型基准 | 无（并行） | 中 |
| 5 | **P1.3**：CALPHAD 接入脚本骨架（数据未到也可先写） | 无（并行） | 短 |
| 6 | Phase 2.1：B1 子模型最小算例（2D） | 无（并行） | 中 |

---

## 5. 风险登记

| # | 风险 | 缓解 |
|---|---|---|
| R1 | CALPHAD 数据拿不到 | 先用本框架的 17.9 K 自洽组（F1）并显式声明；同时按 §10.2 做敏感度带 |
| R2 | @@\Delta S_{seg}@@ 文献不存在 | 只做不确定度带，不假装有材料常数（`MATH_FRAMEWORK.md` §6.1） |
| R3 | PF @@\leftrightarrow@@ LKT 匹配做不出（薄界面极限不收敛） | 退路：用**表格化的** @@V(\Delta T)@@ 作为 CA 的封闭，并让 PF 只在 @@W/V@@ 足够的区制使用；把该限制写进论文 |
| R4 | 3D 内存不足 | P1.4 先做；退路：2D 精细 + 3D 粗的混合 |
| R5 | 算子学到的是 teacher 的错（而非真实物理） | 强制分开报告 @@\|\mathrm{NO-teacher}\|@@ 与 @@\|\mathrm{teacher-experiment}\|@@（`MATH_FRAMEWORK.md` §8.3） |

---

## 6. 记账要求（每个阶段结束时必须更新）

1. `MATH_FRAMEWORK.md` 的 V&V 表（哪一级从 ❌ 变 ✅）；
2. `verify_framework.py` 的判据数与 FAIL 数；
3. 所有新引入的近似：**在哪一条方程上、量级多大、为什么可接受**；
4. 所有新参数：来源标签 L / T / A。

---

## 7. 进度日志（新增）

| 轮次 | 完成 | 验证 |
|---|---|---|
| Phase 0 | 数学框架 + 自检 | 76 项（55/7/6/8） |
| D3 | 焓式能量方程 + 潜热（`thermal_layer.py`） | 11/11 |
| P1.2 | 三维 CA 骨架 + 取向 + 滑动窗口（`ca3d.py`） | 21 项（20/1/0） |
| P1.2 | 液相溶质输运（`ca3d_solute.py`） | 11/11 |
| P1.2 | 物理修正：IRF 严禁外推 + 初始固相区；CET 打开 | 14 项（13/1/0） |
| P3.1 | **投影算子 Pi**（`ca3d_project.py`） | 5/5 |

**累计 138 项判据。** 开放项：倾斜梯度下的多晶取向淘汰（定量预测）、CET 的形貌验证、
输运在 `dx < l_mix` 区制的 dt 收敛性、**P1.1（PF ↔ LKT 薄界面匹配）尚未开始**。
