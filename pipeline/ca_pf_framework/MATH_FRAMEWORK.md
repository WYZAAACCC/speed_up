# Ti-6Al-4V LPBF 多尺度组织仿真：完整数学框架 v1

> 版本 2026-09-22。对应研究路线 v2（Ti64_CA_PF_Gibbs_NeuralOperator_EventDriven_v2.docx）：
> **Window A = 滑动窗口 CA 做 prior-beta 生长；Window B = 局部精细 PF 做晶内组织转变；Gibbs 面最后做。**
>
> 本文件只做一件事：把这个路线写成一组**无歧义的方程 + 边界条件 + 耦合条件 + 守恒律**，
> 并给出每一条的判据与验证状态。验证由同目录的 `verify_framework.py` 自动执行，
> 结果写入 `VERIFY_REPORT.md` 与 `verify_results.json`。
>
> 记账约定（全文件有效）：
> - 参数来源三档：L = 文献值（有出处）｜T = 理论/解析推导｜A = 指派值（论文里必须标明）
> - 结论三档：[已验证] = 脚本给出数值证据｜[推导] = 解析推导未数值复核｜[未核实] = 需查
> - 本文中 @@...@@ 是数学显示分隔符。

---

## 0. 这份框架怎么组织

整个系统是一个**混合系统**：连续状态场上叠加一个由事件触发的**离散调度**。
所以必须分三层写，缺一层就不自洽：

| 层 | 名字 | 内容 | 回答 |
|---|---|---|---|
| L0 | 状态与调度 | 全局材料状态 @@\mathfrak{S}@@、活动窗口、混合自动机 | 谁在什么时候算 |
| L1 | 连续物理层 | T 层、G 层 (CA)、P 层 (PF)、C 层 (Gibbs) | 每个窗口里解什么方程 |
| L2 | 接口层 | 投影算子 @@\Pi@@、halo、一致性条件、守恒记账 | 层与层凭什么能接上 |
| L3 | 学习层 | 神经算子的算子定义与约束 | 用什么替代什么 |

**硬性要求（不可协商）**
1. 每条方程都在 `verify_framework.py` 里有量纲/极限/恒等式判据；
2. 层与层之间**只能通过显式写出的接口量**耦合，不允许隐式共享网格；
3. 所有守恒量逐项记账；任何"为了跑通"的近似必须写进 §11。

---

## 1. L0-a 全局材料状态

域 @@\Omega\subset\mathbb{R}^3@@。定义**全局材料状态场**（不是四个各自独立的模型，而是同一个场被四个窗口分区读写）：

@@
\mathfrak{S}(x,t)=\Big(\;T,\;\{\varphi_\alpha\},\;\{c_i\},\;\{\Gamma_i\},\;g,\;\mathbf{q},\;\mathcal{H}\;\Big)
@@

| 符号 | 含义 | 量纲 |
|---|---|---|
| @@T(x,t)@@ | 温度 | K |
| @@\varphi_\alpha@@ | 相/变体序参量（beta / alpha / alpha-prime / 变体 1..12） | 1 |
| @@c_i@@ | 溶质摩尔分数（@@i\in\{V,Al\}@@；准二元时只留 V） | 1 |
| @@\Gamma_i@@ | 界面 Gibbs 过剩（挂在界面上，不是体场） | mol/m^2 |
| @@g@@ | prior-beta 晶粒身份（整数标签） + 取向 @@\mathbf{q}\in SO(3)@@ | -- |
| @@\mathcal{H}@@ | 热史指针（峰值 T、冷却速率、重热次数） | -- |

**关键形式化要求**：active window 是 @@\mathfrak{S}@@ 的**限定算子**，不是独立数据结构：

@@
\mathfrak{S}_A(t):=\mathfrak{S}\big|_{\Omega_A(t)},\qquad
\mathfrak{S}_{B,j}:=\mathfrak{S}\big|_{\Omega_{B,j}},\qquad
\mathfrak{S}_{C,l}:=\mathfrak{S}\big|_{\Sigma_l}
@@

不满足这一条，就会掉进 v2 文档 §4 警告的"每个求解器各持一份材料"——这是最常见的隐性错误。

---

## 2. L0-b 事件驱动调度的形式化

写成**混合自动机** @@\mathcal{H}_{aut}=(Q,\mathfrak{S},F,Inv,E,G,R)@@：

- @@Q=@@ { LIQUID, ACTIVE_SOLIDIFICATION, SOLID_WAITING, ACTIVE_SOLID_PF, QUIESCENT, REACTIVATE_GRAIN, REMELTED }
- 每个模式 @@q@@ 对应一个向量场 @@F_q@@（即"此模式解哪些方程"）
- @@Inv_q@@：模式不变式（例如 ACTIVE_SOLID_PF 要求 @@T<T_{\beta\mathrm{tr}}@@）
- 迁移 @@E@@：由**事件函数** @@\psi(\mathfrak{S})@@ 与门限 @@\theta@@ 定义
- @@R@@：迁移时的重置映射

### 2.1 事件函数必须是热力学/动力学量，不能是经验温度

按 v2 文档 §8 的要求，最终版应写成

@@
\psi_{B\to \mathrm{ACTIVE}}=
\max\!\Big(\;\frac{|\Delta G_{\mathrm{chem}}|}{RT},\;
\frac{\Delta t_{\mathrm{avail}}}{\tau_{\mathrm{diff}}(T)},\;
\frac{\Delta t_{\mathrm{avail}}}{\tau_{\mathrm{trans}}(T)}\;\Big)
@@

其中 @@\tau_{\mathrm{diff}}=L_{\mathrm{diff}}^2/D(T)@@、@@\tau_{\mathrm{trans}}\sim 1/(M_{\mathrm{int}}|\Delta G|)@@。
Window A/B 的具体形态（可立即实现、量纲为 1）：

@@
\psi_A=\frac{f_s(1-f_s)}{f_s(1-f_s)+\varepsilon},\qquad
\psi_B=\frac{L_{\mathrm{lath}}^2}{D_V^{\alpha}(T)\,\Delta t_{\mathrm{step}}}
@@

> @@\psi_B@@ 的物理含义：**这一时间步内 V 能否扩散过一条板条**。@@\psi_B<1@@ ⇒ 打开也没用，直接留在 SOLID_WAITING。
> 这条把 v2 文档"用热力学/动力学事件触发"从口号变成了可执行判据。

### 2.2 必须排除 Zeno 行为

调度器必须**同时**满足：

1. **迟滞**：@@\theta_{\mathrm{off}}<\theta_{\mathrm{on}}@@；
2. **最短驻留**：进入模式后停留 @@\Delta t_{\min}>0@@，且 @@\Delta t_{\min}\ge@@ 该模式向量场的显式稳定极限。

[RULE] 不满足这两条的实现不算事件驱动，只算抖动。

### 2.3 迁移时的守恒

对每个守恒律 @@\mathcal{C}(\mathfrak{S})=0@@ 必须要求 @@\mathcal{C}(R(\mathfrak{S}))=\mathcal{C}(\mathfrak{S})@@。最容易出错的两次迁移：

- **Window A -> SOLID_WAITING**：@@c@@ 必须逐胞**精确**移交（见 §5.7 的 @@\Pi@@），不能清零重来；
- **REMELTED**：熔掉的固态组织必须把 @@c@@ 还回液相池，不能直接删除。

---

## 3. L1-T 热层（所有窗口共享的时钟）

### 3.1 焓式能量方程（含潜热）

@@
\frac{\partial h}{\partial t}+\mathbf{u}\cdot\nabla h=\nabla\cdot\big(k(T)\nabla T\big)+q_{\mathrm{laser}}(\mathbf x,t)
@@
@@
h(T)=\int_{T_{\mathrm{ref}}}^{T}c_p(\theta)\,\mathrm d\theta+f_lL_f,\qquad f_l=1-f_s
@@

写成温度形式时**必须**保留潜热项：

@@
\rho c_p\frac{\partial T}{\partial t}+\mathbf u\cdot\nabla h=\nabla\cdot(k\nabla T)
-\rho L_f\frac{\partial f_s}{\partial t}+q_{\mathrm{laser}}
@@

> 仓库旧版正是漏掉 @@-\rho L_f\partial_t f_s@@ 这一项。量纲已核对：@@[PASS]\ E1@@（@@\mathrm{m^{-1}kg\,s^{-3}}@@ 四项齐）。
> 热源用 Goldak 双椭球，或由外部热 FE/CFD 直接给 @@\hat T(\mathbf x,t)@@。

### 3.2 必须记账的四条判据（全部 [已验证]）

| 判据 | 数值 | 结论 |
|---|---|---|
| @@Ste=c_p\Delta T_{\mathrm{super}}/L_f@@ | **1.74**（@@\Delta T_{\mathrm{super}}=577@@ K） | 潜热**不可忽略** |
| @@L_f/(c_p\Delta T_0)@@ | **18.6** | 凝固区间内潜热是显热的 19 倍 |
| @@l_T=2\sqrt{\alpha t}@@，@@t=0.1@@ ms | **57 µm** vs 熔池深 100 µm | 同量级 ⇒ **准静态热场近似不成立** |
| @@Fo=\alpha t/L^2@@ | 0.081 | 熔池内部非等温 |

热物性取文档口径：@@k_l=3.15+0.012T@@、@@c_{p,l}=412.7+0.18T@@、@@\rho=4512-0.154T@@
⇒ @@\alpha_l(1900\,\mathrm K)=8.15\times10^{-6}\,\mathrm{m^2/s}@@。

### 3.3 与"静态熔池"设定的接口

用户已定：**不重熔**；"激光熔化后关掉，模型从熔池开始演化"。
热层的输出契约是给 @@\hat T(\mathbf x,t)@@（可用静态熔池 + 指数衰减 @@T=353+(T_0-353)e^{-t/\tau}@@），
**唯一必须保证的是 @@T@@ 确实在下降**：若 @@T@@ 被冻死，模型中唯一的凝固驱动力消失，熔池永不凝固（已实测的失败模式）。

---

## 4. L1-G Window A：滑动窗口 CA（prior-beta 晶粒）

> **术语澄清（很重要，极易混淆）**
>
> | 说法 | 是不是 Window A 的事 |
> |---|---|
> | 固液界面 @@\Sigma_{sl}@@ 推进（@@f_s@@ 从 0 到 1） | ✅ 是。CA 的捕获规则就是在推进它 |
> | 某个胞被哪个晶粒占有（grain ID） | ✅ 是。这是 Window A 的主输出 |
> | **晶粒之间的晶界位置** | ⚠️ **不是被推进的，是涌现的**：CA 里没有任何方程写晶界，晶界 = grain ID 场 @@g(\mathbf x)@@ 的间断集合 |
> | 固态晶界迁移（曲率驱动 + 溶质拖曳） | ❌ 不是。属 REACTIVATE_GRAIN 模式，见 §9 P1/P2（LPBF 建造期内位移 1.4~2.8 nm） |
> | 晶界面上的 @@\Gamma_i@@、沿晶界扩散 | ❌ 不是。属 Window C |
>
> 一句话：**Window A 里被推进的是固液界面，晶界是被它画出来的，不是被它推的。**
> 窗口跟着 @@\Sigma_{sl}(t)@@ 走，不跟着晶界走。
> 由此推出一条架构结论：**prior-beta 晶界网络是 Window A 的产物，且凝固后冻结**，
> 它适合当 Window B/C 的几何载体，但不适合被当成一个需要持续求解/加速的演化对象。

Window A 只回答两件事：**哪个 prior-beta 晶粒占哪块位置**，以及**凝固留下一份什么样的化学初值**。
它不解析 alpha-prime 板条（那是 Window B）。

### 4.1 窗口定义与 halo（本框架里唯一有闭式判据的地方）

固液界面 @@\Sigma_{sl}(t)@@，界面速度 @@V@@，液相扩散系数 @@D_L@@：

@@
\Omega_A(t)=\{\,x\in\Omega:\; d\big(x,\Sigma_{sl}(t)\big)\le \delta_A\,\},\qquad
\delta_A=\max\big(N_\perp l_D,\;N_\parallel\lambda_1,\;\delta_{\min}\big)
@@
@@
l_D=\frac{D_L}{V}=95\ \mathrm{nm}\ (V=0.1\,\mathrm{m/s}),\qquad
\lambda_1=2\pi\sqrt{\frac{2\Gamma D_L}{k\,V\,\Delta T_0}}=461\ \mathrm{nm}
@@

**halo 判据（闭式，已数值复核）**。稳态溶质边界层解析解：

@@
c(\xi)=c_0\Big[1+\frac{1-k}{k}e^{-\xi/l_D}\Big],\qquad \xi=x-\int V\mathrm dt
@@

设 @@N=L/l_D@@（halo 用扩散长度度量），则

| 量 | 闭式 | N=5 | N=7 |
|---|---|---|---|
| 漏出窗口外的溶质份额 | @@e^{-N}@@ | @@6.74\times10^{-3}@@ | @@9.12\times10^{-4}@@ |
| 出口用 Dirichlet @@c=c_0@@ 造成的 @@c_l@@ 相对误差 | @@\dfrac{1-k}{k}e^{-N}@@ | @@-0.394\%@@ | @@-5.3\times10^{-4}@@ |

@@[已验证]@@ 系数 @@(1-k)/k=0.5865@@；打靶法独立复核 5 个 N 上解析式与数值解差 @@3.9\times10^{-14}@@。

⇒ **判据**：@@N\ge\ln(1/\varepsilon)\Rightarrow@@ 泄漏 @@<\varepsilon@@；取 @@\varepsilon=1\%@@ 得 @@N\ge4.6@@。
这就是文献里 "5 @@l_D@@" 的严格版本（且给出了正确的系数 @@0.587@@，不是拍出来的）。

> [RULE] **横向截断不是指数衰减**。侧向溶质场是 Laplace 型（代数 @@1/r@@ 衰减），
> 上表只在**生长方向**严格。横向窗口必须靠 domain-size convergence 数值定，不能照搬 @@N=5@@。

### 4.2 形核（三选一，按 CET 判据切换）

**(a) 外延/基底形核**（熔池底部与侧壁，主导）
@@t=0@@ 时按已有 beta 晶粒取向布置种子；密度 @@N_{\mathrm{sub}}@@ 由 EBSD 重构的 prior-beta 统计给出。

**(b) 体形核（CET）** —— 连续形核谱

@@
\frac{\mathrm dN}{\mathrm d(\Delta T)}=\frac{N_{\max}}{\Delta T_\sigma\sqrt{2\pi}}
\exp\!\Big[-\frac{(\Delta T-\overline{\Delta T})^2}{2\Delta T_\sigma^2}\Big],\qquad
N_v(\Delta T)=\int_0^{\Delta T}\frac{\mathrm dN}{\mathrm d\Delta T^\prime}\mathrm d\Delta T^\prime
@@

每个 CA 胞每步的形核概率 @@P=N_v\,V_{\mathrm{ca}}@@（@@V_{\mathrm{ca}}=(\Delta x)^3@@）。

**(c) 自由生长形核判据**（Greer，取代接触角）

@@
\Delta T_n=\frac{4\gamma_{SL}}{\Delta S_{f,v}\,d_p},\qquad
Q=|m_L|\,c_0(1-k)=10.9\ \mathrm K
@@
其中 @@d_p@@ 是形核颗粒直径（SEM/TEM 可测）。CET 判据：成分过冷 @@\Delta T_{CS}> \Delta T_n@@。

@@[已验证]@@ @@Q=10.9@@ K。把"指派接触角"换成"可测的颗粒尺寸"，这是数据缺口的实质缩小。
@@[未核实]@@ @@N_{\max},\overline{\Delta T},\Delta T_\sigma@@ 仍缺（P0 级数据缺口）。

### 4.3 生长律：LKT 界面响应函数 @@V(\Delta T)@@

CA 的"生长"由**尖端动力学**封闭，而不是解析溶质边界层。这是 CA 能省算力的根本原因，也是它与 PF 必须一致的地方。

@@
P=\frac{RV}{2D_L},\qquad
\mathrm{Iv}(P)=P e^{P}E_1(P),\qquad
c_l^\ast=\frac{c_0}{1-(1-k)\mathrm{Iv}(P)}
@@
@@
G_c=\frac{V}{D_L}c_l^\ast(1-k),\qquad
\xi_c(P)=1-\frac{2k}{\sqrt{1+(2\pi/P)^2}-1+2k}
@@
@@
\underbrace{R=2\pi\sqrt{\frac{\Gamma}{|m_L|G_c\xi_c-G}}}_{\text{marginal stability}}
\qquad
\underbrace{\Delta T=|m_L|(c_l^\ast-c_0)+\frac{2\Gamma}{R}+\frac{V}{\mu_k}}_{\text{过冷度预算}}
@@
@@
\Gamma=\frac{\gamma_{SL}}{\Delta S_{f,v}}=3.08\times10^{-7}\ \mathrm{K\,m},\qquad
|m_L|=\frac{R_gT_m^2(1-k)}{\Delta H_f}=818\ \mathrm{K/(mol\ frac)}
@@

**已解出的结果（[已验证]，全表见 `irf_ti64.csv`）**

| 量 | 值 |
|---|---|
| 平面界面稳定极限 @@V_c=\dfrac{G\,k\,D_L}{|m_L|c_0(1-k)}@@ | @@5.5\times10^{-4}@@ m/s（LPBF 的 0.1 m/s 在其上 182 倍 ⇒ 深枝晶区） |
| LPBF 工作点 @@V=0.1@@ m/s 对应 | @@\Delta T=12.28@@ K，其中成分过冷 @@\Delta T_c=10.38@@ K（85%） |
| 尖端半径 @@R_{\mathrm{tip}}@@ | 0.34 µm（@@P=1.80@@） |
| 界面动力学过冷 | @@\Delta T_k=V/\mu_k=0.09@@ K ⇒ 可忽略（但 @@\mu_k@@ 是 A 档） |

**交付形式（重要修正）**：不要用 @@V=a_2\Delta T^2+a_3\Delta T^3@@ 当唯一封闭。
实测局部指数 @@n=\mathrm d\ln V/\mathrm d\ln\Delta T@@ 在 @@\Delta T=6.5\sim17.4@@ K 上从 **3.9 变到 6.4**，
多项式拟合全域 @@R^2=0.985@@ 但最大偏差 **210%**，只在 @@\Delta T=10.6\sim16.7@@ K 内把误差压到 5% 以内。
⇒ **Window A 的封闭应当用插值表 `irf_ti64.csv`（这也就是 ExaCA 的做法），多项式只作为快速回退。**

### 4.4 取向与捕获判据（decentered octahedron）

> ⚠ **2026-09-23 修复（见 `CA3D_AUDIT_2026-09-23.md` / `CA3D_FIX_PLAN_2026-09-23.md`）**
> 代码默认捕获已从 `decentered`（逐胞 L 预算 + 格点路径代价）换成 **`envelope`**
> （逐晶粒连续包络 ℓ_g + 外延邻接 + 逐胞 argmax(ℓ_g/sup_g)），原因：
> ① `decentered` 的格点路径代价使**径向可达距离短 25~40%**（实测 r(<100>)/ℓ=0.60~0.76，
>    正确 1.00），KD 各向异性 1.73 被压到 1.05~1.12，晶粒体积 −25%，且**不随 dx 收敛**；
> ② 旧 `thermal_capture` 的 26 邻域洪泛**依赖扫描顺序**（30% 的初始胞换主）且残留冷液相会
>    **每胞一颗**自形核（41³ 盒造 68578 个假晶粒）。
> 新实现实测：体积误差 ∝ dx（0.003%/0.07%/0.98%/2.2% @ dx=0.5/1/2/3 µm）、顺序无关、
> 无假晶粒、熔池界面单连通无孤岛且随 dt 收敛。`decentered` / `analytic` 保留可选。

晶粒 @@g@@ 的"虚拟生长前沿"是**晶体坐标系下的正八面体**（L1 球），半轴随凝固距离增长：

@@
\ell_g(t+\Delta t)=\ell_g(t)+V\big(\Delta T(\mathbf x)\big)\,\Delta t
@@

晶体学主轴 @@\{\mathbf p_1,\mathbf p_2,\mathbf p_3\}@@ 由取向 @@\mathbf q_g@@ 给出。沿方向 @@\hat{\mathbf n}@@ 的八面体半径：

@@
r_g(\hat{\mathbf n})=\frac{\ell_g}{|\mathbf p_1\!\cdot\!\hat{\mathbf n}|+|\mathbf p_2\!\cdot\!\hat{\mathbf n}|+|\mathbf p_3\!\cdot\!\hat{\mathbf n}|}
@@

**捕获规则**：邻居胞 @@j@@（胞心偏移 @@\mathbf d_{ij}@@）被 @@g@@ 捕获，当且仅当

@@
\big|\mathbf d_{ij}\big|\le r_g\big(\hat{\mathbf d}_{ij}\big)
@@

按邻居类型展开即得常用的三档判据（@@a@@ 为胞边长；【2026-09-23 更正】这里用的是
**胞心到胞心**的偏移 @@d_{ij}@@：面邻 @@|d|=a@@、棱邻 @@a\sqrt2@@、角邻 @@a\sqrt3@@，故下面三式**没有 1/2**；代码 `_thr_tables` 的 `thr=dx*Σ` 正是这个约定，与 ExaCA 一致）：

@@
\text{面邻：}\ell\ge a\sum_a|\mathbf p_a\!\cdot\!\hat{\mathbf n}|,\quad
\text{棱邻：}\ell\ge a\sqrt2\,(\dots),\quad
\text{角邻：}\ell\ge a\sqrt3\,(\dots)
@@

> [未核实] 若要与 ExaCA 逐位对上，必须核对它的 @@cx,cy,cz@@ 半对角约定（本框架给的是物理判据，等价形式）。
> **捕获规则决定"取向竞争"如何发生**：各向同性的 @@\ell@@ + 各向异性的 @@r(\hat{\mathbf n})@@ 才能产生 Walton–Chalmers 择优。
> 注意：这不是"晶界迁移率各向异性"，措辞不同会改变审稿人的提问。

### 4.5 凝固化学：为什么可以严格退化为 Scheil 方程

**这是本框架最有价值的一条简化，因为它是"算出来的"而不是"假设的"。**

局部凝固时间 @@t_f=\Delta T_0/(GR)=1.73\times10^{-4}@@ s（@@GR=10^5@@ K/s）。两个判据：

| 判据 | 表达 | 值 | 含义 |
|---|---|---|---|
| 液相充分混合 | @@Fo_L=D_Lt_f/\lambda_1^2@@ | **7.74** @@\gg1@@ | 胞尺度液相均匀 |
| 固相反扩散（Brody–Flemings） | @@\alpha_{bd}=D_St_f/(\lambda_1/2)^2@@ | @@1.63\times10^{-3}@@ @@\ll1@@ | 固相**无**反扩散 |

⇒ 微观偏析严格落在 **Scheil 极限**：

@@
c_l(f_s)=c_0(1-f_s)^{k-1},\qquad c_s=k\,c_l,\qquad
\int_0^1 k\,c_l\,\mathrm df_s=c_0
@@

@@[已验证]@@ 守恒恒等式数值误差 @@<10^{-4}@@；Scheil 预测 @@c_l(f_s=0.99)=0.198@@，
与仓库 Gibbs 版 2D 实测的 @@c_{\max}\in[0.12,0.24]@@ 同量级（互相印证）。

> **结论（对路线有直接影响）**：在 LPBF 的 @@G,R@@ 区制下，**Window A 不需要附加局部凝固 PF 就能给出可信的 @@c@@ 分布**。
> 局部 PF 只在两种情况下才必要：(i) 要解析**胞/枝晶形貌**本身；(ii) @@Fo_L@@ 或 @@\alpha_{bd}@@ 越出上表区制（例如更慢的冷却、更快的生长）。

### 4.6 从 CA 到全局状态的投影算子 @@\Pi@@

@@\Pi@@ 把"胞平均"变成"胞内分布"，是两级之间唯一的化学接口：

@@
\Pi:\;\big(\bar c_i,\;f_{s,i},\;g_i,\;\mathbf q_i\big)\;\longmapsto\;c_i(\mathbf x)\Big|_{\Omega_i}
\quad\text{s.t.}\quad
\int_{\Omega_i}c_i\,\mathrm dV=\bar c_i\,|\Omega_i|
@@

实现方式：把 §4.5 的 Scheil 剖面按"胞/枝晶几何"映射进胞内（例如以主要生长方向为轴的柱状剖面）。

[RULE] **@@\Pi@@ 必须逐胞精确守恒**。直接双线性插值会把凝固偏析抹平——仓库已经实测过这个错误（"CA -> PF 时把凝固偏析清零"）。

---

## 5. L1-P Window B：局部精细 PF（晶内组织）

### 5.1 状态与自由能泛函

相/变体集合 @@\mathcal P=\{\beta,\alpha,\alpha^\prime\}\cup\{\text{变体 }1..12\}@@，序参量 @@\{\varphi_\alpha\}@@ 满足

@@
\sum_{\alpha\in\mathcal P}\varphi_\alpha=1,\qquad 0\le\varphi_\alpha\le1
@@

自由能泛函（多相场 + 微弹性）：

@@
F=\int_\Omega\Big[\;\underbrace{f_{\mathrm{chem}}(\{\varphi\},\{c\})}_{\text{化学}}
+\underbrace{\sum_{\alpha<\beta}W_{\alpha\beta}\varphi_\alpha^2\varphi_\beta^2+\sum_\alpha\frac{\kappa_\alpha}{2}|\nabla\varphi_\alpha|^2}_{\text{界面}}
+\underbrace{f_{\mathrm{el}}(\varepsilon,\{\varphi\})}_{\text{弹性}}\;\Big]\mathrm dV
@@

化学项（置换式理想溶液，每个相有自己的标准态）：

@@
f_{\mathrm{chem}}=\sum_\alpha \varphi_\alpha\,f_\alpha(\{c\}),\qquad
f_\alpha=\sum_i c_i\,g_i^\alpha(T)+\frac{R_gT}{V_m}
\Big[\textstyle\sum_i c_i\ln c_i+\big(1-\sum_i c_i\big)\ln\big(1-\sum_i c_i\big)\Big]
@@

### 5.2 热力学输入其实只有两个独立参数（[已验证]，重要结论）

> ⚠ **适用域（2026-09-25 补）**：本节结论是 **n_solute = 1（准二元）** 的结论 ——
> 它解的是 2 个化学势等式（溶质 + 溶剂），得到**一对离散的** @@(c_s,c_l)@@。
> 三元（Al + V）必须用 **§5.9**。判据 **T-A1** 已数值验证：本节数值在 n_solute=1 时正确
> （复现 @@T_L=1911.1133@@ K vs 1911.1 K，偏 +0.013 K）。**本节不删除，只限定范围。**

理想溶液 + 两相共存的两个化学势平衡条件

@@
R_gT\ln\frac{c_s}{c_l}=-(\Delta g_B),\qquad
R_gT\ln\frac{1-c_s}{1-c_l}=-(\Delta g_A)
@@

给出两条**闭式**结论：

@@
\underbrace{\Delta g_A(T)=-\Delta H_f\Big(1-\frac{T}{T_m}\Big)}_{\text{由 } \Delta H_f, T_m \text{ 定}}\qquad
\underbrace{\Delta g_B=-R_gT_L\ln k}_{\text{由 } k \text{ 定}}
@@
@@
T_{\text{pair}}(c_l,c_s)=\frac{\Delta H_f}{\Delta H_f/T_m-R_g\ln\frac{1-c_l}{1-c_s}}
@@

数值（本项目参数，@@c_0=0.036@@、@@k=0.6303@@、@@\Delta H_f=14150@@ J/mol、@@T_m=1941@@ K）：

| 量 | 值 |
|---|---|
| 液相线 @@T_L=T_{\text{pair}}(c_0,kc_0)@@ | **1911.1 K** |
| 固相线 @@T_S=T_{\text{pair}}(c_0/k,c_0)@@ | **1893.2 K** |
| 凝固区间 @@\Delta T_0=T_L-T_S@@ | **17.93 K** |
| van t Hoff 恒等式 @@|m_L|c_0(1-k)/k@@ | 17.28 K（差 3.6%，线性化残差） |
| @@m_L=-R_gT_m^2(1-k)/\Delta H_f@@ | @@-818.4@@ K/(mol frac) = @@-7.69@@ K/wt% |
| PF 需要的溶质标准态差 | @@\Delta g_B=7334@@ J/mol |

> **结论 1（建模简化）**：@@m_L@@ **不是独立参数**，它由 @@(k,\Delta H_f,T_m)@@ 唯一决定。
> 所以"用 600 还是用 -819"这个问题在框架层面就消解了：本模型类里只能是 -818。
>
> **结论 2（数据缺口，FAIL）**：本项目现在同时用了两套不相容的口径 ——
> 自己反解出的 @@(k=0.6303,\ c_0=0.036)@@ 配上 van t Hoff，凝固区间**只有 17.9 K**；
> 而仓库文档里写的 @@T_l-T_s=45\sim50@@ K 来自另一篇论文的 @@(k=0.5,\ c_0=0.10)@@。
> 两者不能同时成立（要凑出 45 K 需 @@\Delta H_f=5434@@ J/mol，真实值 14150）。
> **必须由 CALPHAD（Thermo-Calc TCTI 或 Ti-Al-V 评估）给出一套自洽的 @@(k,m_L,\Delta T_0)@@。**
>
> **结论 3（准二元偏差）**：模型液相线 1911.1 K vs 实测 Ti64 液相线 1923 K，差 **-11.9 K**。
> 这是忽略 Al 的系统偏差。要消除它必须上三元，或显式吸收这个偏置。

### 5.3 演化方程

多相场（非守恒）与溶质（守恒）分开写：

@@
\frac{\partial\varphi_\alpha}{\partial t}
=-\frac{1}{\tilde N}\sum_{\beta\neq\alpha}M_{\alpha\beta}
\Big(\frac{\delta F}{\delta\varphi_\alpha}-\frac{\delta F}{\delta\varphi_\beta}\Big),
\qquad
\frac{\delta F}{\delta\varphi_\alpha}
=\frac{\partial f}{\partial\varphi_\alpha}-\nabla\!\cdot\!\frac{\partial f}{\partial\nabla\varphi_\alpha}
@@
@@
\frac{\partial c_i}{\partial t}
=\nabla\!\cdot\!\Big(\sum_j M^c_{ij}\,\nabla \mu_j\Big),\qquad
\mu_j=\frac{\delta F}{\delta c_j}
@@

@@\tilde N@@ 是 @@\alpha@@ 处的共存相数（保证界面不被人为拖慢）。扩散迁移率矩阵 @@M^c_{ij}@@ 必须满足

@@
M^c_{ij}=M^c_{ij}(\{\varphi\})=\sum_\alpha \varphi_\alpha\,M^{\alpha}_{ij}
\quad\text{（相平均）}
@@

热力学因子由自由能自动给出（@@M^{c}=\sum_\alpha\varphi_\alpha D_\alpha/(R_gT/V_m)\cdot\partial^2f/\partial c^2@@ 类），
**不允许**把 @@D@@ 直接当迁移率写进去（仓库旧版的 P0 之一就是这个混用）。

### 5.4 微弹性与变体选择

@@
\varepsilon=\tfrac12(\nabla\mathbf u+\nabla\mathbf u^{\mathsf T}),\qquad
\nabla\!\cdot\!\sigma=0,\qquad
\sigma=\mathbb C(\{\varphi\})\!:\!\big(\varepsilon-\varepsilon^0(\{\varphi\})\big)
@@
@@
\varepsilon^0(\{\varphi\})=\sum_\alpha\varphi_\alpha\varepsilon^0_\alpha,\qquad
E_{\mathrm{el}}=\frac12\int(\varepsilon-\varepsilon^0)\!:\!\mathbb C\!:\!(\varepsilon-\varepsilon^0)\,\mathrm dV
+\int \sigma^{\mathrm{ext}}\!:\!\varepsilon\,\mathrm dV
@@

变体选择的驱动力（哪个变体先出现）：

@@
\Delta E_v=-\sigma^{\mathrm{ext}}\!:\!\varepsilon^{0,v}\,V_v
+\underbrace{\Delta E^{\mathrm{auto}}(\text{已存在变体的取向场})}_{\text{自催化/自协调}}
@@

beta -> alpha 的 Burgers 取向关系给出 **12 个变体**（若做全量 ⇒ 12 个序参量场；可先降到变体群）。

> [未核实] @@\varepsilon^{0,v}@@ 的量级（BCC->HCP 的 Bain 型对应应变，通常 0.08~0.12）需按具体变体对算；
> 这是变体选择的**唯一物理输入**，必须从晶体学算，不能指派。

### 5.5 ⚠ 必须把"晶内转变"拆成两个物理机制不同的子模型

v2 文档把 @@\beta\to\alpha/\alpha^\prime@@ 与 @@\alpha^\prime\to\alpha+\beta@@ 与 @@V/Al@@ 重分配并列写，
但它们在数学上是**两类不同的方程**，混写会直接做错：

| | 子模型 B1：@@\beta\to\alpha^\prime@@ | 子模型 B2：@@\alpha^\prime\to\alpha+\beta@@ |
|---|---|---|
| 机制 | 无扩散、位移型（马氏体） | 扩散型 |
| 序参量 | **非守恒** @@\varphi_{\alpha^\prime}@@ | 非守恒 @@\varphi_\alpha,\varphi_\beta@@ + **守恒** @@c_V@@ |
| 方程 | 带势垒的 Landau + 应变耦合 | 多相场 + Cahn-Hilliard |
| 溶质 | **不分配**（@@c@@ 继承 beta 的过饱和值） | 分配：V 进 beta，Al 留 alpha |
| 时间标度 | 非热（athermal）：@@f_{\alpha^\prime}=1-\exp[-\alpha_{KM}(M_s-T)]@@ | @@t\sim L_{\mathrm{lath}}^2/D_V^\alpha@@ |
| 触发 | @@T<M_s=848@@ K 且冷却速率足够 | 需要 @@T\in[900,1073]@@ K 的**长时间**停留 |

@@[已验证]@@ B2 的时间标度（@@L_{\mathrm{lath}}=0.5@@ µm）：

| T | @@D_V^\alpha@@ | 跨越板条所需 t |
|---|---|---|
| 900 K | @@1.2\times10^{-18}@@ m^2/s | 59 h |
| 973 K | @@1.3\times10^{-17}@@ m^2/s | 5.3 h |
| 1073 K | @@2.1\times10^{-16}@@ m^2/s | 0.33 h |

⇒ **LPBF 建造过程中（单次热循环 ~@@10^{-3}@@ s，@@\sqrt{D_Vt}\sim10^{-10}@@ m ≪ 板条宽）B2 根本不发生**。
沉积态就是过饱和 @@\alpha^\prime@@；B2 只在**后处理热处理**或有长时高温停留时开启。
这条直接决定了 Window B 的调度：**建造期 Window B 基本处于 SOLID_WAITING**。

> 附注：晶界 @@\alpha@@（先共析 alpha 膜）是**第三类形核位置**，与 B1/B2 都不同；
> 若后续要预测晶间腐蚀/H 陷阱（v2 文档 §1 的通道 (d)），这一项必须单独建。

### 5.6 halo 与窗口尺寸（Halo-in / Core-out）

Window B 的尺寸由三项最大者控制：

@@
L_B\;\gtrsim\;\max\big(L_{\mathrm{RVE}},\;N_\lambda\lambda_{\mathrm{micro}},\;\sqrt{D_s\Delta t},\;N_W W\big),\qquad
L_B\ll L_{\mathrm{macro}}
@@

- @@\lambda_{\mathrm{micro}}@@：板条/集束尺度 0.5~5 µm ⇒ 域 20~50 µm 级
- @@W@@：PF 界面宽，@@\Delta x\le W/4@@ 起
- 输入 patch 比可信输出 core 大：**只把 core 拼回全局**，把人工边界放在感受野之外

[RULE] 边界必须做 domain-size convergence（@@L_B@@ 加倍看输出变不变），不能只用一个固定尺寸。

### 5.7 Window B 的守恒

@@
\frac{\mathrm d}{\mathrm dt}\int_{\Omega_B}c_i\,\mathrm dV
=\oint_{\partial\Omega_B}\sum_j M^c_{ij}\nabla\mu_j\cdot\mathbf n\,\mathrm dA
\;+\;\big(\text{与 }\Omega_B\text{ 外的交换项}\big)
@@

@@\Pi^{-1}@@（B -> 全局）必须与 @@\Pi@@（A -> B）配对，使 @@\int_{\Omega_B}c_i\mathrm dV@@ 在窗口开/关时**恰好**不变。

---

### 5.8 Window B′：板条界面的【Gibbs 面 / 锐界面】表示（2026-09-24 新增）

#### 5.8.1 为什么必须加这一节（实测结论，不是偏好）

弥散界面 PF 在板条尺度有一个**结构性矛盾**：@(W = 13.18\gamma/w_{90})@
把"界面宽"与"势垒"绑在一起，而"同一格点混合多个变体"的弹性收益实测
@\sim 9\times10^8\ \mathrm{J/m^3}@。要压制它需 @w_{90}\lesssim 1\text{–}2@ nm
@\Rightarrow \Delta x\lesssim0.5@ nm；而装下板条排列需要 @2\text{–}3\ \mu m@
（@5000^3\sim10^{11}@ 格）。**两者不可同时满足**。
实测（`WINDOWB_STATUS.md` §4）：12 变体随机竞争在 @\Delta x=20@ nm 与 @1@ nm
下都退化成"多变体微观混合"（纯胞 0% 与 3.3%），**板条这个概念消失**。

@\Rightarrow@ 板条界面必须按**面**（零厚度）表示；每个胞唯一属于一个变体。
这条与 §6 的晶界 Gibbs 面是**同一套表示原则**（界面量按单位面积记账），
区别只是界面上的物理量：晶界管溶质过剩 @\Gamma@（mol/m²），板条管界面能 @\gamma@（J/m²）。

#### 5.8.2 与 §5.1–5.4 的对应（自洽性的形式化）

同一套体自由能泛函，两个表示：

@@
\underbrace{E_{\rm PF}=\int\Big[f_{\rm bulk}+\sum_\alpha \tfrac{W_\alpha}{2}\varphi_\alpha^2(1-\varphi_\alpha)^2+\tfrac{\kappa_\alpha}{2}|\nabla\varphi_\alpha|^2+f_{\rm el}\Big]{\rm d}V}_{\text{弥散界面}}
\;\xrightarrow[\;w\to0\;]{}\;
\underbrace{E_{\rm Gib}=\int f_{\rm bulk}{\rm d}V+\gamma\,A[\mathcal I]+\int f_{\rm el}{\rm d}V}_{\text{锐界面 / Gibbs 面}}
@@

对应关系（逐项）：

| 量 | 弥散 PF | Gibbs 面 | 关系 |
|---|---|---|---|
| 界面位置 | @\varphi=1/2@ 等值面 | 标签跳变面 @\mathcal I@ | 同一几何 |
| 界面能 | @\gamma=\sqrt{2\kappa W}/6@ | @\gamma@ 直接给出 | **同一 @\gamma@** |
| 界面宽 | @w_{90}=4.394\sqrt{\kappa/2W}@ | @0@ | @w\to0@ 极限 |
| 体自由能 | @f_{\rm bulk}(\{\varphi\})@ | 分段常数的 @f_{\rm bulk}@ | 相同 |
| 弹性 | @\varepsilon^0=\sum_\alpha\varphi_\alpha\varepsilon^0_\alpha@ | @\varepsilon^0@ 分段常数 | 相同泛函 |
| 互斥性 | 由势垒 @W@ **近似**保证 | **由构造保证**（每胞一个标签） | Gibbs 面严格 |

**推论（关键）**：@\gamma@ 是同一根标定链的产物，所以
*"@\gamma@ 取多少"* 与 *"界面多宽"* 在 PF 里是**同一件事**，而在 Gibbs 面里**解耦**；
这正是 Gibbs 面能同时满足"物理正确"与"装得下板条尺度"的原因。

#### 5.8.3 Gibbs 面的能量与动力学（已实现：`windowB_gibbs.py`）

@@
E[\mathcal I]=E_{\rm el}[\varepsilon^0(\mathcal I)]+\gamma\,A[\mathcal I]-\Delta f\,V_{\rm trans}[\mathcal I],
\qquad
A[\mathcal I]=\Delta x^2\cdot\frac{\#\{\text{异标签近邻键}\}}{2}
@@

动力学取**非热**（马氏体）极限：界面重标号由**精确总能单调下降**接受，
局部一阶场 @-\Delta x^3(\varepsilon^0_{\rm new}-\varepsilon^0_{\rm old}):\sigma@
只用于**提议**。@\sigma@ 由 §5.4 的谱法给出（与 PF **共用同一套 @\Lambda(n)@ 实现**）。

> ⚠ **离散化的两个已知坑**（都已在代码里记账）：
> 1. 面能**不能**放进逐胞提议：单胞翻转必然长出凸包（@+2@ 个异键 @=+2\gamma\Delta x^2@），
>    界面会被永久冻结（实测接受数恒为 0）。面能必须交给精确总能（它等价于
>    Gibbs–Thomson 曲率项），提议只用体驱动力 + **按意愿排序的前缀接受**。
> 2. 面积测度 @\#@异键 @\times\Delta x^2@ 对斜面有 @\le15\%@ 的立方网格偏差；
>    对平坦界面（板条的主要界面）几乎精确。

#### 5.8.4 形核物必须"有形状"（实测）

单胞翻转的弹性代价 @\sim10^9\ \mathrm{J/m^3}@ 远大于化学驱动 @\Delta f\sim5\times10^7@，
所以**单点形核在能量上被禁止**，动力学完全不动（实测）。这与马氏体必须以
**板条/自协调集团**形核的经典图像一致 ⇒ 初始化必须是**有法向的薄板晶核**。

晶核取向的判据来自 PTMC（见 `windowB_ptmc.py` 的实测）：

@@
\text{不变平面存在}\iff \lambda_2(U)=1,\qquad U=\sqrt{F^{\rm T}F}
@@

**本项目实测**：12 个变体的贝恩应变给出

@@
\lambda_1=0.89124,\quad \boxed{\lambda_2=1.00042},\quad \lambda_3=1.09154
\qquad(|\lambda_2-1|=4.2\times10^{-4})
@@

即 @\beta\to\alpha'@ **几乎是不变平面应变**（"几乎"的来源与 §1 的
@c_\alpha/2\approx a_\beta/\sqrt2@ 是同一个偶然），对应的不变平面法向 @\approx[110]_\beta@。
@\Rightarrow@ 板条可以以极低的弹性代价在该面内长大。

> ⚠ **[未核实]** 文献里 @\alpha'@ 的惯习面常报 @\{334\}_\beta/\{344\}_\beta@ 型，
> 与"单变体 IPS"给出的 @(110)_\beta@ 不一致。两种可能：(i) 实际板条是**孪晶配对**的
> PTMC 解（孪晶面+孪晶分数+刚体转动使 @\lambda_2=1@）；(ii) 我方 @(a,c)@ 取值或
> 对应关系需要复核。**写进论文前必须查证。**

#### 5.8.5 与其它窗口的接口

> **2026-09-24 更新**：§5.8 的锐界面极限已进一步展开成完整的**混合模型**
> （**体相场 + Gibbs 面场**）规格，见 **`HYBRID_FRAMEWORK.md`**：
> 那里补齐了（i）面场状态量（面片身份/法向/面上的过剩 `Γ_i`）、
> （ii）**面上的守恒式**（Stefan + 面储存 + 沿面输运 = `ΣJ_s=0` 的完整版）、
> （iii）Gibbs–Thomson 与 McLean 面-体局部平衡、（iv）拓扑事件与离散化方案、
> （v）8 条自洽性判据（H1–H8）与文献对照清单。
> 本节的对应表（PF ↔ 锐界面）仍是其极限依据。

* **窗口尺寸（⚠ 2026-09-25 更正）**：原句写「@\Delta x@ 由**板条间距**定（@10\text{–}50@ nm），
  于是 §5.6 的 @20\text{–}50\ \mu m@ 窗口重新变得可行」——**这一句量级写错**，更正为：
  - **体相网格的 @\Delta x@ 由「体相需要解析的最粗组织层级」定**：集束/变体群 **5–50 µm** ⇒
    盒子 @L=20\text{–}50@ µm；**板条(片层)间距 ~1 µm** ⇒ 区分相邻板条需 ≥2–4 胞
    ⇒ **@\Delta x\approx0.1\text{–}0.5@ µm（建议 0.25 µm ≈ 4 胞/间距）**；
  - **nm 级的东西一律交给「面」表示**：板条界、晶界、**β 纳米膜 5–100 nm**、界面宽 1–2 nm
    ⇒ 零厚度面 + 面上的 @\Gamma/\gamma@（§5.8 的架构），**不由体相网格解析**；
  - ⚠ **@48@ nm 那条（§14.2 的 F4–F6）不是错的，但与本节无关**：它来自
    @l_D=D_L/V=95@ nm（**固液前沿溶质边界层**）⇒ 属 **Window A/凝固前沿**。
  - 【待文献复核】「@10\text{–}50@ nm」原本指哪个量（β 膜？单根片层最细层级？被误挪的 48 nm？）
    ⇒ 已加入 `docs/LIT_SEARCH_BRIEF_Ti64_THERMO.md` 的检索项（TEM vs SEM/EBSD 的板条宽/间距）。
  - 算力账（说明为何必须更正）：真取 @\Delta x=10@ nm 则 @L=20@ µm 需 @2000^3\approx8\times10^9@ 胞 ✗；
    取 @\Delta x=0.25@ µm 则 @80^3\approx5\times10^5@ 胞 ✓（@L=50@ µm 时 @200^3\approx8\times10^6@ ✓）。
* **⚠ 生产路径的权威声明（2026-09-25 依代码复核）**：
  - **生产路径 = `windowB_surface.py`（level-set 面场 + 面上的 `\Gamma` 场）** —— 每胞唯一标签、
    界面为面、面量按面积记，符合用户"禁止随机胞翻转 / 要面场+PDE"的硬约束；
  - **非生产参考（仍在仓库）**：`windowB_gibbs.py`（`GibbsLath`：胞**重标号**，接受用精确总能
    单调下降 ⇒ 非热极限语义可用，但形式上是元胞重标号，不作主路径）与
    `windowB_hybrid.py`（`advance(..., rng)` 里 `draw = rng.random(...)` ⇒ **随机胞翻转**，
    与用户约束冲突 ✗，仅作历史原型）；
  - 这两个文件只作 **G1–G3 能量判据的参考实现**；`windowB_surface.py` 模块级只 import
    numpy/scipy（弹性核与参数表在函数内延迟 import `windowB_pf3d`/`windowB_aniso_elastic`/
    `gibbs_physics`）⇒ **与那两个原型无依赖** ✓。
* **V6 必须分侧记（2026-09-25）**：**CA 侧 halo 已实现**（`ca3d.py` 的 halo + `active_box`；
  闭式判据在 `verify_framework.py` 的 W1–W4：泄漏 `e^{-N}`、Dirichlet 截断 `((1-k)/k)e^{-N}`、
  打靶法复核、横向截断 RULE）✓；**Window B 侧 halo/core 与 domain-size 收敛未做** ✗
  （全仓库 `halo` 只出现在 `ca3d.py` 与 CA 验证脚本里）。
* **惯习面 `{334}_\beta` 的证据（2026-09-25）**：**两个分析脚本已存在** ——
  `_chk_334.py`（{334} 族 24 个成员 vs 3000 个随机方向的弹性能分位；**随机对照已经做过** ✓）
  与 `_chk_nstar.py`（把 **PTMC 不变平面法向**代入 `\frac12\varepsilon:\Lambda(n):\varepsilon`）。
  ⚠ 两者都**只打印数值、没有 pass/fail 门槛** ⇒ 结论**未记账**（本会话的 HX-8b 才是带判据的版本）。
* **Window B 的 PF 引擎实况（2026-09-25）**：`windowB_pf3d.py::PF3D` 与 `windowB_pf.py::MartensitePF`
  **已经是多变体马氏体 PF 引擎**（Allen–Cahn 型非守恒序参量 + FFT 谱法微弹性 +
  `\varepsilon^0(\varphi)=\sum_v\varphi_v\varepsilon^0_v` 驱动），且 **`sigma_ext`（外应力）已接进驱动力**
  （`sext_e0[v] = \sigma_{ext}:\varepsilon^0_v` 出现在 `forces()`/`dfdphi()` 里 ✓）
  ⇒ **缺的不是引擎，而是**：T 依赖的势垒/KM 动力学（`M_s`/`Koistinen`/`Landau`/`athermal` 全库 0 命中）、
  "V 不分配"的非守恒束缚判据、以及**变体选择判据脚本**（给定 `\sigma_{ext}` ⇒ `\Delta E_v=-\sigma:\varepsilon^{0,v}` 最小）。
* **与 Window C（晶界 Gibbs 面）共用一套离散面机制**：`\Gamma_i@ 的面上输运
  与这里的 @A[\mathcal I]@、面法向、面扩散是同一套数据结构 ⇒ 可复用。
* **与学习层（§8）**：Gibbs 面版本天然给出"面上算子"的训练数据（面法向、面通量、
  面能），与逐面神经算子的目标一致。

---

### 5.9 三元闭合（Al+V 双溶质）—— 对 §5.1/§5.2/§5.3 的推广（2026-09-25 新增）

> **触发**：用户 2026-09-25 决定「**一步到位做三元**」。
> 审计与修复台账：`TERNARY_COMPAT_AUDIT.md`；
> 实现（单一参数来源）：`ternary_thermo.py`；
> 数值判据：`_chk_ternary.py`（**T-A0..T-A11，33 项 ALL PASS**）。

**§5.2 的适用范围**：§5.2 的「只有两个独立参数 @@(k,\Delta H_f,T_m)@@」是 **n_solute = 1**
（准二元）的结论。三元（@@C=3@@、@@P=2@@）相律 @@F=C-P+2=3@@，固定 @@T,P@@ 后 @@F=1@@
⇒ **系线是一条曲线（1 参数族），不是一对点**。故 §5.2 降级为准二元子集，其数值仍正确（T-A1）。

#### R0 自由能与化学势（精确式；可选正规溶液相互作用）

@@
g^{\varphi}(c)=\sum_j c_j g_j^{\varphi}+R_gT\sum_j c_j\ln c_j+E^{\varphi}(c),
\qquad E^{\varphi}=\sum_{j<k}L^{\varphi}_{jk}c_jc_k
@@

对 @@(C-1)@@ 个独立组分（求和跑遍全部 @@C@@ 个组分）：

@@
\mu_i^{\varphi}=g_i^{\varphi}+R_gT\ln c_i^{\varphi}
+\frac{\partial E^{\varphi}}{\partial c_i}-E^{\varphi}
@@

（推导：@@\mu_i=g+\partial g/\partial c_i-\sum_jc_j\partial g/\partial c_j@@，
@@\sum_jc_j\partial g/\partial c_j=(g-E)+R_gT+2E@@ ⇒ @@R_gT@@ 项抵消。）
**@@L=0@@ 时 @@\mu_i=g_i+R_gT\ln c_i@@ 是精确的（没有 @@X@@ 比）**。
> ⚠ 本仓库实现时曾把 @@-E@@ 误写成 @@-2E@@（判据 **T-A5b** 抓到）；@@L=0@@ 时两者相同，
> 故理想部分结论不受影响，但必须记账。

#### R1 系线族（逐溶质分配）

@@
c_i^{\mathrm{sol}}=k_i(T)\,c_i^{\mathrm{liq}},\qquad
k_i(T)=\exp\!\big[-\Delta g_i(T)/(R_gT)\big],\qquad
\Delta g_i\equiv g_i^{\mathrm{sol}}-g_i^{\mathrm{liq}}=\Delta H_i-T\Delta S_i
@@
@@
\text{溶剂（Ti）锚：}\quad \Delta g_{\mathrm{Ti}}(T)=-\Delta H_f\Big(1-\frac{T}{T_m}\Big)
@@

【符号约定】（本仓库推错过一次，必须写死）：@@T<T_m@@ 时 @@\Delta g_{\mathrm{Ti}}<0@@（固相更稳）、
@@k_{\mathrm{Ti}}>1@@、@@k_{\mathrm{Ti}}(T_m)=1@@ —— 判据 **T-A0**。

#### R2 ⭐ 液相线恒等式 (★) —— 把两个溶质绑在一起

固相成分必须是一个**合法成分**（分数组分和为 1，而 @@X^{\mathrm{sol}}=k_{\mathrm{Ti}}X^{\mathrm{liq}}@@）：

@@
G(T;c^{\mathrm{liq}}):=\sum_i k_i(T)\,c_i^{\mathrm{liq}}
+k_{\mathrm{Ti}}(T)\,X^{\mathrm{liq}}=1 \tag{★}
@@

一句话含义：**「按 @@k@@ 逐组分把液相成分放大后，固相的总和必须恰好是 1」**。

| 用途 | 做法 |
|---|---|
| 纯 Ti 检验 | @@c^{\mathrm{liq}}=0\Rightarrow G=k_{\mathrm{Ti}}=1@@ 只在 @@T=T_m@@ 成立 ✓（T-A4） |
| **液相线** | 把 @@c^{\mathrm{liq}}=c_0@@ 代入 (★) 解 @@T@@ |
| **固相线** | 把 @@c_i^{\mathrm{liq}}=c_i^0/k_i(T)@@ 代入 (★) 解 @@T@@ |
| **凝固区间** | @@\Delta T_0=T_L-T_S@@ 变成**预测值**（可对文献 45~50 K 检验，见 R7） |

@@[已验证]@@ **T-A2**：解析系线 = 3 个 @@\mu@@ 等式的**独立**数值解（最小二乘残差 @@7.3\times10^{-12}@@ J/mol）。
@@[已验证]@@ **T-A2b**：离开 (★) 曲线就**没有**系线（残差 51.9 J/mol）⇒ (★) 不是恒等式。

> **[RULE] (★) 是一条方程 ⇒ @@k_{\mathrm{Al}}@@ 与 @@k_V@@ 不能自由各选。**
> 这在此前任何文档里都没有，是本轮的新硬约束（见 R7 的绑定表）。

#### R3 分配**矩阵**（不是标量）

@@
k_{ij}:=\frac{\partial c_i^{\mathrm{sol}}}{\partial c_j^{\mathrm{liq}}}\Big|_T
@@

**理想置换溶液（@@L=0@@）⇒ @@k_{ij}=k_i\delta_{ij}@@（精确对角，无交叉耦合）**；
含 @@L_{jk}\neq0@@ 时出现非对角项，量级 @@O(L/R_gT)@@（T-A6：@@|k_{\mathrm{Al}V}|=0.55@@、
@@\det>0@@）。⇒ **想要非零交叉分配，必须由 CALPHAD 给 @@L_{jk}@@；不能凭空造。**

#### R4 抗截留 / 拖曳的向量化

逐溶质各带一项，@@a_t@@ 仍是**一个**标量；
溶剂项由 @@\sum_ic_i=1@@ 隐含（@@j^{\mathrm{at}}_{\mathrm{Ti}}=-\sum_ij^{\mathrm{at}}_i@@）：

@@
j^{\mathrm{at}}_i=a_t\,W\,(c_i^{l0}-c_i^{s0})\,
\frac{\partial_t\varphi}{|\nabla\varphi|}\Big/(2\sqrt2)
\quad\text{（本仓库归一化）}
@@

@@[已验证]@@ **T-A10**：@@n=1@@ 时向量式与 `alloy_pf_std` 的标量式**逐位相同**。

> ⚠ **本轮附带的一个判决（必须记账）**：在**冻结核面**（解析 @@\varphi(x,t)@@）仪器里，
> 不存在单一 @@a_t@@ 让两个溶质同时满足 @@k_{\mathrm{eff},i}=k_i^e@@，且有
> @@5.1\%/\text{倍}@@ 的 @@W@@ 依赖（T-A11d）⇒ 这与 §7.2 的 RULE 一致：
> **抗截留只在「界面自洽 + 局部平衡」下才有意义**，因此 **A1（解 @@\varphi@@：WBM/KKS）
> 是闭合 §7.2 的前提，不是可选项**。

#### R5 独立输入计数（**替代** §5.2 的「只有两个独立参数」）

| 项 | 个数 |
|---|---|
| 溶剂 Ti：@@(\Delta H_f,T_m)@@ | 2（已知：14150 J/mol、1941 K）|
| 每溶质：@@(\Delta H_i,\Delta S_i)@@ | @@2\times2=4@@（**未知**）|
| (★) 的 1 条约束（用文献 @@T_L@@ 闭合）| @@-1@@ |

@@\Rightarrow@@ **三元自由度 = 3**（不是 §5.2 的 1）；判据 **T-A9**。

#### R6 Gibbs 面（§6）的位点竞争 —— 双溶质 McLean 必须换掉

§6.1 的 McLean 等温线是**单物种**的。两个溶质**争同一批晶界位点**，正确闭合是
**Langmuir 竞争吸附**（多元 McLean）：

@@
\frac{\Gamma_i}{\Gamma_0-\sum_j\Gamma_j}}
=a_i\exp\!\Big[-\frac{\Delta G_{\mathrm{seg},i}}{R_gT}\Big]
@@

（@@a_i@@ 为体相活度，理想溶液下 @@a_i\simeq c_i@@。）单物种极限立即退化为 McLean ✓。
**忽略 @@\sum_j\Gamma_j@@ 会系统性高估偏析**（每个物种都以为自己独占全部位点），
而 @@\Gamma_0@@ 是**总**位点数。
⇒ `gibbs_physics.py` 的 [A] 档 @@\Delta H_{\mathrm{seg}}@@ 必须**每溶质一套**，
且必须声明「另一物种占了多少位点」。**判据待建（本轮只写下闭合式）。**

#### R7 数值结果（本轮的「新东西」）

**(a) 二元退化复现**（T-A1）：@@T_L=1911.1133@@ K vs §5.2 的 1911.1 K（偏 **+0.013 K**）；
@@T_S@@ 与老口径差 0.60 K（老口径只用了溶剂方程，记账）。

**(b) @@k_{\mathrm{Al}}@@–@@k_V@@ 绑定表**（@@T=1923@@ K [L]，@@x_{\mathrm{Al}}=0.102@@、
@@x_V=0.036@@ [T] 由 wt% 换算）：

| @@k_{\mathrm{Al}}@@ | 0.700 | 0.719 | 0.733 | 0.750 | 0.800 | 0.850 | 0.900 | 0.950 |
|---|---|---|---|---|---|---|---|---|
| @@k_V@@ | 1.653 | 1.599 | 1.559 | 1.511 | 1.369 | 1.228 | 1.086 | 0.944 |

⇒ @@k_V>1@@（V 是 @@\beta@@ 稳定元素，物理必然）**要求 @@k_{\mathrm{Al}}<0.9304@@**。

**(c) 用文献 @@\Delta T_0@@ 反解（F1/F2 的结构性关闭）**：

| 文献 @@\Delta T_0@@ [L] | @@k_{\mathrm{Al}}@@ | @@k_V@@ | 推出 @@T_S@@ |
|---|---|---|---|
| 45 K | 0.7333 | 1.5582 | 1878.0 K |
| **47.5 K** | **0.7271** | **1.5758** | 1875.5 K |
| 50 K | 0.7211 | 1.5928 | 1873.0 K |

两种温度依赖约定（@@\Delta S_i=0@@ 与 @@\Delta H_i=0@@）只差 **1–2 K**（T-A8b）⇒ 结论**鲁棒**。
与已授权的 A2 扫描区间 @@\\{1.1,1.37,1.6\\}@@ 自洽（@@k_V=1.6\iff k_{\mathrm{Al}}=0.7186@@）。
⚠ **CALPHAD 到手前，这组数是 [T]+[L] 级，不是 [L] 级**（依赖文献 @@T_L=1923@@ K 与
@@\Delta T_0=45\text{–}50@@ K 的准确值，二者出处**【未核实】**）。

#### R8 本轮**未做**（不许说成已解决）

| # | 项 | 阻塞 |
|---|---|---|
| N1 | `ca3d.py` / `ca3d_solute.py` 双溶质向量化 | Window A 化学初值 |
| N2 | `windowB_surface.py` 的 @@\Gamma_i@@ / @@D^s_{ij}@@ 向量化 | Window C |
| N3 | R6 的 Langmuir 竞争与每溶质 @@\Delta G_{\mathrm{seg},i}@@ | Window C 定量 |
| N4 | 标量 `alloy_pf_std.StdFront` 的**抗截留符号判决**（本轮只判了三元版）| A1/A2 |
| N5 | 文献 @@T_L=1923@@ K 与 @@\Delta T_0=45\text{–}50@@ K 的**出处与不确定度** | R7(c) 的定标 |
| N6 | 摩尔体积两个口径（@@1.1345\times10^{-5}@@ vs @@9.873\times10^{-6}@@，差 15%）| 面-体守恒 |
| N7 | @@L_{jk}@@ 与 @@D_{ij}@@ 非对角项 | 等 CALPHAD |


---

## 6. L1-C Window C：Gibbs 面（按用户要求最后做，但接口现在就定死）

Window C 不是独立相态，而是**挂在活跃界面上的二维求解区**。定义界面状态

@@
u_\Gamma=\{\Gamma_i,\;T,\;\mu_i^\pm,\;\kappa,\;\mathbf n,\;v_n,\;\text{misorientation},\;\gamma\}
@@

### 6.1 吸附方程与规范（gauge）问题

Gibbs 吸附方程：

@@
\mathrm d\gamma=-\sum_i\Gamma_i\,\mathrm d\mu_i-S^\sigma\,\mathrm dT
@@

@@\Gamma_i@@ 依赖**分界面的取法**（gauge）。平移分界面 @@\Delta x@@ 时

@@
\Gamma_i(x_0+\Delta x)=\Gamma_i(x_0)+\Delta x\,\big(c_i^{\beta}-c_i^{\alpha}\big)
@@

@@[已验证]@@ 真正的规范不变量是 @@\gamma@@ 本身，以及组合 @@\sum_i\Gamma_i\mathrm d\mu_i+S^\sigma\mathrm dT@@：
平移 3 nm 后组合量漂移 @@3.7\times10^{-16}@@（机器精度），
抵消来自两相各自的 Gibbs-Duhem 关系 @@\sum_i c_i^{\varphi}\mathrm d\mu_i+\bar s^{\varphi}\mathrm dT=0@@ 相减。

[RULE] **论文里给 @@\Gamma_i@@ 必须同时声明分界面定义**（等摩尔面 / 零溶剂吸附面），否则不可复现。
[RULE] 只有 @@\sum_i\Gamma_i\mathrm d\mu_i+S^\sigma\mathrm dT@@ 或 @@\gamma@@ 才有物理意义；单独一个 @@\Gamma_i@@ 没有。

### 6.2 沿界面的守恒与输运

@@
\frac{\partial\Gamma_i}{\partial t}
+\nabla_s\!\cdot\!(\Gamma_i\mathbf v_s)
=\nabla_s\!\cdot\!\Big(\sum_j D^{s}_{ij}\nabla_s\Gamma_j\Big)+J_i^{\mathrm{bulk}}
@@
@@
J_i^{\mathrm{bulk}}=-\Big(D_i^{\alpha}\frac{\partial c_i}{\partial n}\Big|_{\alpha}
+D_i^{\beta}\frac{\partial c_i}{\partial n}\Big|_{\beta}\Big),
\qquad
\mu_i^{\alpha}=\mu_i^{\beta}=\mu_i^{\sigma}(\{\Gamma\})
@@

最后一行是**局部平衡闭合**；若要允许有限吸附动力学，换成 @@J_i^{\mathrm{bulk}}=k_i\big[\mu_i^{\sigma}-\mu_i^{\mathrm{bulk}}\big]@@。

### 6.3 溶质拖曳必须写成隐式自洽方程

拖曳的**精确泛函**（对任意势能 @@E(x)@@）：

@@
P_{\mathrm{drag}}=-\frac{1}{V_m}\int_{-\infty}^{\infty}\big(c(x)-c_\infty\big)\,E^\prime(x)\,\mathrm dx
@@

由双盒质量平衡（界面 + 相邻 @@\ell@@ 厚体层，界面扫掠率 @@v@@）可得

@@
P_{\mathrm{drag}}(v)=\frac{P_0}{1+v/v^\ast},\qquad v^\ast=\frac{D_{GB}}{\ell}
@@

⇒ **速度律是隐式方程**：

@@
v=M_{GB}\Big[\Delta G-P_{\mathrm{drag}}(v)\Big]
@@

@@[已验证]@@ 线性闭式 @@P\approx P_0(1-v/v^\ast)@@ 只在 @@v\lesssim0.1v^\ast@@ 时误差 @@<2\%@@；
@@v=v^\ast@@ 时误差 100%，@@v=2v^\ast@@ 时误差 400%（且给出**负压强**，非物理）。
并且隐式方程在 @@\Delta G<P_0@@ 时可以**无解（钉扎）**，线性闭式却凭空给出速度。

[RULE] 禁止 @@v=M_{GB}\Delta G(1-a v)@@ 之类的线性修正写法。这条直接对应仓库已实测的"线性 Cahn 拖曳在本区制不成立"。

### 6.4 面-体总守恒

@@
\frac{\mathrm d}{\mathrm dt}\Big[\int_\Omega c_i\,\mathrm dV+\int_\Sigma\Gamma_i\,\mathrm dA\Big]
=\oint_{\partial\Omega}\mathbf J_i\cdot\mathbf n\,\mathrm dA
@@

[RULE] 面-体交换项 @@J_i^{\mathrm{bulk}}@@ 在体和面两个方程里必须**成对出现、符号相反**（仓库的 `GBSoluteSink` 就是这个角色）。

---

## 7. L2 层间一致性：整个框架里最关键的一节

四个窗口各自自洽 ≠ 框架自洽。**层与层之间只有下面 6 个接口量**，每一个都必须有可检验条件：

### 7.1 接口量清单（冻结，改动即架构改动）

| # | 接口 | 方向 | 量 | 一致性判据 |
|---|---|---|---|---|
| I1 | T 层 -> 所有 | -> | @@\hat T(\mathbf x,t),\ G,\ R,\ \dot T@@ | 需与 CA 的 @@V(\Delta T)@@ 相容 |
| I2 | G 层 -> L0 | -> | @@g,\mathbf q,t_s,\bar c_i,f_{s,i}@@ | 逐胞守恒（@@\Pi@@） |
| I3 | G 层 -> P 层 | -> | 同上 + 界面位置 | @@\Pi@@ 守恒 + 界面几何一致 |
| I4 | P 层 -> G 层 | <- | 拖曳后的有效迁移率 / 界面能 | 拖曳隐式方程（§6.3） |
| I5 | P 层 -> C 层 | <-> | @@\mu_i^\pm,c_i^\pm,\mathbf n,\kappa,v_n@@ | 局部平衡或有限动力学 |
| I6 | C 层 -> P 层 | -> | @@\Gamma_i,J_i^s,\gamma@@ | 面-体守恒成对 |

### 7.2 ⭐ 核心一致性条件：PF 必须复现 CA 的 @@V(\Delta T)@@

这两级描述的是**同一个物理**：CA 用的是锐界面/LKT 极限，PF 用的是弥散界面。
它们必须在重合区给出同一个答案：

@@
\lim_{\substack{W\to0\ W/V=\text{const}}}\;V_{\mathrm{PF}}(\Delta T;W)\;=\;V_{\mathrm{LKT}}(\Delta T)
@@

- 极限必须取 @@W\to0@@ 且 @@W/V@@ 固定（**Karma–Rappel 薄界面极限**），否则 PF 会给出错误的 @@k@@；
- 为让该极限存在，必须在溶质方程里加**抗截留通量（anti-trapping current）**，其量级为 @@\sim W\,\partial_t\varphi/|\nabla\varphi|\cdot(c_l^0-c_s^0)@@；
- @@c_l^0,c_s^0@@ 分别是界面两侧的平衡浓度。

> **这条正好解释了仓库里反复出现的"缺口 #3 溶质截留"**：它不是数值 bug，而是**两级模型之间的匹配条件没写出来**。
> 换了 CA+PF 的新路线之后，这个条件从"可选项"变成**强制项** —— 因为 CA 层给了你必须匹配的靶子。

> **三元补注（2026-09-25）**：@@(c_l^0-c_s^0)@@ 变成**逐溶质的向量**
> @@(c_i^{l0}-c_i^{s0})@@，而 @@a_t@@ 仍是**一个**标量（判据 T-A10：@@n=1@@ 时逐位退化）。
> ⚠ 但本轮判据 **T-A11d** 给出一个 no-go：**冻结核面**（解析 @@\varphi@@）下不存在单一 @@a_t@@
> 让两个溶质同时满足 @@k_{\mathrm{eff},i}=k_i^e@@，且有 5.1%/倍 @@W@@ 依赖
> ⇒ **本 RULE 的闭合前提是「解 @@\varphi@@（WBM/KKS）」，即 `IMPLEMENTATION_PLAN` §7.6 的 A1。**
> 完整推导与数值见 `TERNARY_COMPAT_AUDIT.md` §3.1 与 `_chk_ternary.py`。

[RULE] 验收判据：固定 @@W/V@@，把 @@W@@ 减半三次，@@V_{\mathrm{PF}}@@ 应单调收敛到 @@V_{\mathrm{LKT}}@@，且残差按 @@O(W)@@ 下降。

### 7.3 时间上的多尺度耦合

CA 的时间步由胞尺度定（@@\Delta t_A\sim\Delta x_A/V@@），PF 的时间步由界面/扩散定（@@\Delta t_P\sim\min(W^2/M\sigma,\ \Delta x_P^2/D)@@），
两者可差 2~4 个数量级。两种可接受做法：

**(a) 子步（sub-stepping）**：每个 CA 步内，用 CA 提供的 @@T(t)@@ 把 PF 推进 @@n@@ 步。
误差 @@O(\Delta t_A)@@，需要做 @@\Delta t_A@@ 收敛性检验。

**(b) 交错（staggered，仓库旧版用的）**：CA 与 PF 各自走一整步再交换。
必须显式记账：每步交换引入 @@O(\Delta t)@@ 的算子分裂误差。

[RULE] 无论哪种，都必须报告 @@\Delta t@@ 收敛阶（仓库已实测交错耦合是**一阶**，@@p\approx1.05@@）。

### 7.4 全局守恒记账（每步都要检查的 5 个量）

1. 溶质总量 @@M_i=\int_\Omega c_i\mathrm dV+\int_\Sigma\Gamma_i\mathrm dA@@
2. 相分数约束 @@\sum_\alpha\varphi_\alpha=1@@
3. 浓度非负 @@c_i\ge0@@（仓库旧版实测出现过 @@c<0@@ 到 @@-0.031@@）
4. 序参量界 @@0\le\eta\le1@@（仓库旧版实测 @@\eta_{\max}>1@@ 到 1.30）
5. 等温松弛问题的自由能单调不增

> 3 与 4 是**硬判据**：越界就是模型/离散错误，不能用"数值噪声"解释。

### 7.5 求解能力约束（会在 3D 上变成硬墙）

| 配置 | 单元 | 自由度 | 直接解内存 |
|---|---|---|---|
| 盒子 A（CA，450x450x200 µm，@@\Delta x=10@@ µm） | 4.05e4 | ~1.2e5 | 可 |
| 盒子 B（PF，@@20^3@@ µm，@@\Delta x=0.5@@ µm） | 6.4e4 | ~3.2e5 | ~10 GB（MUMPS 外推，[推导]） |

⇒ 盒子 B 必须用 AMG/迭代求解器 + MPI；这条要在实现 Window B 之前先解决，否则自由度一涨就撞墙。

---

## 8. L3 学习层：神经算子的数学定义

### 8.1 算子定义（严格）

@@
\mathcal G_{\mathrm{PF},\Delta t}:\;
u_\Omega(t)\big|_{B_r}\;\longrightarrow\;u_\Omega(t+\Delta t)\big|_{B_{r_0}},\qquad r>r_0
@@
@@
\mathcal G_{\Gamma,\Delta t}:\;u_\Gamma(t)\;\longrightarrow\;u_\Gamma(t+\Delta t)
@@

- @@B_r@@ 是输入 patch，@@B_{r_0}\subset B_r@@ 是**可信输出 core**（Halo-in / Core-out）；
- 训练数据必须是**同一 teacher 的多条轨迹**，不是单点快照；
- 损失不是纯 field MSE，必须含：PDE 残差、质量守恒、相分数/非负约束、自由能耗散、边界条件、关键 QoI。

### 8.2 ⚠ 按本框架，"Window A 的化学"不是算子该学的对象

本框架已经**证明**（§4.5）：在 LPBF 区制下，Window A 的微观偏析 = Scheil 解析式，误差可忽略。
学习一个已知的解析式是同义反复，没有科学价值。

**同理，v2 文档里 "NO-Solidification（学 Window A 局部 PF 的 phi/C 场）" 这个算子定位需要修正**：
- 若只是要 @@c(x)@@ —— **不需要算子**，Scheil 直接给；
- 若目标是**胞/枝晶形貌**本身 —— 那是另一个研究问题（本文档不覆盖）。

**算子真正有价值的目标（按价值排序）**：
1. **Window B 的 PF 时间推进 @@\mathcal G_{\mathrm{PF},\Delta t}@@** —— 贵、局部、有明确 teacher；
2. **Window B 的拓扑事件**（alpha-prime 分解时的板条合并/消失）—— 这部分即使不用算子也要靠规则处理；
3. **Window C 的界面算子 @@\mathcal G_{\Gamma,\Delta t}@@** —— 目前文献里没有 Ti64 先例，是潜在原创点；
4. **DtN / 亚网格闭合**（把 halo 外部的影响压成一个边界到通量的映射）—— 这是真正能省算力且非平凡的目标。

### 8.3 误差分解（必须分开报告）

@@
\big\|\mathcal G_{\mathrm{NO}}-\text{experiment}\big\|
\;\le\;
\underbrace{\big\|\mathcal G_{\mathrm{NO}}-\mathcal G_{\mathrm{teacher}}\big\|}_{\text{可以用更好的 ML 降低}}
\;+\;
\underbrace{\big\|\mathcal G_{\mathrm{teacher}}-\text{experiment}\big\|}_{\text{ML 无法降低}}
@@

⇒ **第二项由 teacher 的物理正确性决定，与本框架 §5.2/§4.5 的数据缺口直接挂钩**。
"拟合 PF 很准"不能当成"预测真实材料很准"。

---

## 9. 验证与确认（V&V）层级

| 级 | 内容 | 状态 |
|---|---|---|
| V1 | **量纲齐次性**（逐项，全部方程） | ✅ 已做（13 组） |
| V2 | **热力学恒等式**（van t Hoff、Gibbs-Duhem、理想溶液反演、共存线） | ✅ 已做 |
| V3 | **闭式极限**（Scheil 守恒、窗口截断、Gibbs 吸附、规范不变性） | ✅ 已做 |
| V4 | **渐近匹配**（PF @@\leftrightarrow@@ LKT 薄界面极限） | ❌ **未做，强制项** |
| V5 | 制造解（MMS） | ❌ 未做 |
| V6 | 窗口/halo 的 domain-size convergence | ❌ 未做（横向必须做） |
| V7 | 参数可辨识性（哪些参数能从实验反解） | ⬜ 部分 |
| V8 | 跨模型一致性（CA 与 PF 在重合区给同一 @@V(\Delta T)@@） | ❌ 未做 |
| V9 | 实验对标（EBSD 取向、板条宽、APT 偏析剖面） | ❌ 未做 |

---

## 10. 本框架的自检结果（`verify_framework.py` 输出）

**76 项判据：PASS 55 / WARN 7 / FAIL 6 / RULE 8**（RULE = 设计禁令，不是缺陷）

判定含义：PASS = 已验证成立；WARN = 有前提或数据缺口；FAIL = **当前框架或参数不一致/不足，必须处理**；RULE = 必须遵守的写法。

### 10.1 六条 FAIL（必须处理）

| # | 内容 | 定量 |
|---|---|---|
| F1 | ~~凝固区间参数不自洽~~ ⇒ **降级为「准二元模型的适用域声明」**（2026-09-25 重写） | 17.9 K 是**准二元（只留 1 个溶质）**的预测；单溶质模型本来就没有第二个自由度去同时满足液相线与凝固区间。**三元（§5.9）下 @@\Delta T_0@@ 是 @@(k_{\mathrm{Al}},k_V)@@ 的预测值**，文献 45–50 K 反过来把 @@k_V@@ 钉在 **1.56–1.60**（T-A8）。**这不是物理矛盾，是模型维度不够。** |
| F2 | 同上（另一种表述）| 「要凑 45 K 需 @@\Delta H_f=5434@@ J/mol」只在**单溶质**下成立。三元下 @@\Delta H_f=14150@@ J/mol **保持真值**，凝固区间由 @@(k_{\mathrm{Al}},k_V)@@ 与各自 @@\Delta H_i@@ 给出（T-A8）。|
| F3 | **潜热不可忽略** | @@Ste=1.74@@；凝固区间内 @@L_f/(c_p\Delta T_0)=18.6@@ |
| F4 | **生产网格欠解析溶质边界层** | @@\Delta x=2@@ µm 时 @@d_c/\Delta x=0.095@@（判据 @@\ge4@@），欠解析 **42 倍** |
| F5 | 同上 | @@\Delta x=0.2@@ µm 时 @@0.95@@（欠解析 4.2 倍） |
| F6 | 同上 | @@\Delta x=50@@ nm 时 @@3.8@@（刚够/不够），需 @@\le48@@ nm |

> F4–F6 是**新路线最有力的论据**：整个全域 PF 做到可信所需的分辨率（@@\lesssim@@50 nm）在熔池尺度上是不可能的，
> 所以"局部精细 PF"不是权宜之计，而是**唯一可行解**。这条同时把"为什么 CA 不需要这个分辨率"讲清楚了：
> CA 用 LKT 解析解**内置**了边界层，不靠网格解析它。

### 10.2 七条 WARN（有前提）

- 界面能口径不一致：本项目 @@\Gamma=3.08\times10^{-7}@@ K m；JOM 给 @@1.88\times10^{-7}@@ ⇒ 隐含 @@\gamma=0.121@@ J/m²，而 MD 给 0.198 ⇒ **@@\Gamma@@ 与 @@\gamma@@ 必须同源**
- 准二元液相线偏低 11.9 K（忽略 Al）
- @@\Delta g_B=7334@@ J/mol 需独立标定（不能反解 @@k@@ 得到）
- KGT 多项式只在 @@\Delta T=10.6\sim16.7@@ K 内误差 <5%
- 低 @@\Delta T@@ 端有 marginal-stability 回折（@@V<0.01@@ m/s），拟合必须避开
- @@l_T(0.1\,\mathrm{ms})=57@@ µm 与熔池尺寸同量级 ⇒ 准静态热场近似不成立
- 盒子 B 的 3D 直接解需 ~10 GB

### 10.3 八条 RULE（设计禁令）

横向 halo 需数值收敛｜拖曳必须隐式｜@@\Gamma_i@@ 必须声明 gauge｜面-体守恒成对｜超转熔点退火必须重新激活晶粒模型｜@@\Pi@@ 必须逐胞守恒｜PF 必须复现 @@V(\Delta T)@@｜Zeno 必须排除

---

## 11. 必须由用户拍板（其余我按推荐执行）

> **本节的 7 条已于 2026-09-22 全部拍板，结论见 §14。本节保留为决策依据与备选方案的记录，不再代表开放问题。**

| # | 决策 | 影响 | 我的建议 |
|---|---|---|---|
| D1 | **凝固区间用哪一套 @@(k,m_L,\Delta T_0)@@** | 决定 CA 的 @@V(\Delta T)@@、Scheil 剖面、CET 判据全部数值 | 走 CALPHAD 拿一套自洽值；在拿到之前，**以本框架的 17.9 K 为准**，并在论文中显式标注 |
| D2 | 是否把 Al 纳入（做三元） | 消除 11.9 K 液相线偏差；代价是自由度 +1 | 第一阶段准二元 + 显式偏置声明；第二阶段上三元 |
| D3 | 是否现在就补**能量方程 + 潜热** | 潜热占比 19 倍，不补则 @@T@@ 与 @@f_s@@ 的耦合是假的 | 建议补（代价小，且不额外限制 @@\Delta t@@） |
| D4 | 盒子 B 的尺度：@@20^3@@ µm（@@\Delta x=0.5@@ µm）是否可接受 | 决定能否在 3D 上做 | 若接受，先按此做；否则改为 2D 精细 + 3D 粗 |
| D5 | 算子目标按 §8.2 重新定位（学 Window B/C，不学 Window A 的 Scheil） | 决定整个学习层的科学价值 | 建议接受，并据此改写 `RESEARCH_INTENT.md` |
| D6 | @@\mu_k@@（界面动力学系数）与 @@d_p@@（颗粒尺寸）取值 | @@\Delta T_k@@ 与形核判据 | 按文献；拿不到就标 A 档并做敏感度 |
| D7 | 是否保留 v2 文档的 "NO-Solidification" | 与 §8.2 冲突 | 建议删掉或重新定义为"胞/枝晶形貌"，与本框架分开 |

---

## 12. 与旧路线（`RESEARCH_INTENT.md`）的差异——需要您确认后才改那份文件

| 项 | 旧（RESEARCH_INTENT） | 新（本框架 / v2 文档） |
|---|---|---|
| 晶粒拓扑 | 传统相场 | **CA（滑动窗口）** |
| 界面表示 | 弥散界面 @@w_{GB}=4@@ µm | **CA 锐界面包络** + 未来 Gibbs 面 |
| 算子对象 | 逐面学**晶界元素扩散** | **Window B 的 PF 时间推进 / Window C 界面算子**（§8.2） |
| 学习目标 | 2x2 网格（拓扑/溶质 x 两阶段） | **事件驱动的 Window A/B/C** + 统一材料状态 |
| 时间推进 | 连续同域 | **异步多速率 + 混合自动机** |

**我没有改动 `RESEARCH_INTENT.md`**（按仓库规则，改它必须经您确认）。上面 D5 通过后我再改。

---

## 13. 交付物

| 文件 | 内容 |
|---|---|
| `MATH_FRAMEWORK.md` | 本文件 |
| `verify_framework.py` | 自动验证脚本（10 个模块） |
| `VERIFY_REPORT.md` | 完整验证输出（逐条判据） |
| `verify_results.json` | 结构化判定表 |
| `irf_ti64.csv` | Window A 的界面响应函数表 @@V(\Delta T)@@（115 点，可直接喂给 CA） |

复跑：

`
/root/miniconda3/envs/ml/bin/python verify_framework.py
`


---

## 14. 决策记录（2026-09-22 用户已定）

| # | 决策 | 用户答复 | 本框架的落地动作 | 影响到的章节 |
|---|---|---|---|---|
| D1 | 凝固区间用哪套热力学值 | **CALPHAD** | 已出任务书 `CALPHAD_REQUEST.md`（A/B/C/D 四组、26 个量、含填表模板与验收判据）。拿到后按 §5.2 闭式重算 @@T_L,T_S,\Delta T_0,k,\Delta g_{V/Al}@@ | §5.2、§10.1 F1/F2 |
| **D2** | 是否把 Al 纳入 | **2026-09-25 用户改判：一步到位三元（Al+V）** | **全窗口三元**（Window A 与 B 都用 @@(c_{\mathrm{Al}},c_V)@@）；准二元只作**退化对照**（判据 T-A1）。落地：§5.9 + `ternary_thermo.py` + `_chk_ternary.py`（33 项 ALL PASS）+ `TERNARY_COMPAT_AUDIT.md`。原「Window A 准二元 + 显式声明 11.9 K 偏置」**作废**（三元下该偏置自动消除，见 §5.9 R2）| §5.1、§5.5、**§5.9** |
| D3 | 是否现在补能量方程 + 潜热 | **补上，按数学框架** | ✅ **已完成并验证**：`thermal_layer.py` 实现 §3.1 的焓式方程，11 项判据全过（见 §14.1） | §3.1 |
| D4 | 盒子 B 的尺度 | **可接受** | 固定为 @@20^3@@ µm、@@\Delta x=0.5@@ µm、~6.4e4 单元 / ~3.2e5 自由度。**前提**：先解决 AMG/迭代求解器（§7.5） | §5.6、§7.5 |
| D5 | 算子目标重定位 | **重定位** | 算子对象改为 **Window B 的 PF 时间推进 + Window C 的界面算子 + DtN/亚网格闭合**；Window A 的化学不学（它是解析的）。第 12 节列出的 RESEARCH_INTENT.md 差异清单待您点头后再改 | §8.2 |
| D6 | @@\mu_k@@ 与 @@d_p@@ | **文献优先，无则理论推导** | 已按此执行：@@\mu_k@@ 先取 1 m/(s K) 并做敏感度（实测 @@\Delta T_k=0.09@@ K，可忽略）；@@d_p@@ 改为 Greer 判据 @@\Delta T_n=4\gamma_{SL}/(\Delta S_{f,v}d_p)@@，把"指派接触角"换成"可测颗粒尺寸" | §4.2 |
| D7 | v2 的 NO-Solidification 算子 | **保留但不用** | 保留为**预留槽位**并重新定义作用域：只有当目标不是化学而是**胞/枝晶形貌本身**（或退化为 DtN 边界→通量映射）时才有意义。**不在关键路径上，记录在案、本轮不实现** | §8.2 |

### 14.1 D3 的交付与证据（`thermal_layer.py`，11/11 PASS）

按 §3.1 实现焓式方程 @@\dfrac{\partial h}{\partial t}=\nabla\cdot(k\nabla T)@@，
@@h(T)=\rho\int c_p\mathrm dT+\rho L_f f_l@@，支持纯物质（尖界面）与合金（冻结区间线性释放潜热）两种焓反演。

| 判据 | 结果 |
|---|---|
| 焓反演 @@T(h(T))=T@@（2001 点，跨熔点跳跃） | 误差 **0.00e+00** K（两个模型都是闭式精确） |
| 纯导热（@@L_f=0@@）对 erf 解析解 | @@L_2@@ 误差 5.7e-4 → 8.7e-6，**收敛阶 2.02 / 2.00 / 2.00**（二阶，符合预期） |
| 1D Stefan 前沿 vs Neumann 相似解 @@x_f=2\lambda\sqrt{\alpha t}@@ | @@Ste=0.1556,\ \lambda=0.2721@@；网格加密 200→1600 时相对误差 **2.42% → 0.32%** |
| 潜热的作用（物理量级） | Stefan 前沿 14.9 µm vs 热扩散长度 54.6 µm ⇒ **只走到 27%**，潜热把凝固显著拖慢 |
| 绝热域总焓守恒 | 相对漂移 **2.15e-16**（3000 步）⇒ 焓形式离散通量严格守恒 |
| 单边 Dirichlet 域 总焓变化 = 面通量积分 | 偏差 **0.00%** |
| 2D 静态熔池（高斯热斑，激光关掉） | 末态液相分数 **0.0000**（初值 0.055）⇒ 潜热路径是活的，熔池能凝固 |

> 这与框架 §3.2 的判据一致：@@Ste=1.74@@、凝固区间内潜热是显热的 18.6 倍，**潜热必须进方程**（FAIL F3 已由此关闭）。

### 14.2 仍未关闭的项

- **F4~F6（网格欠解析 42 倍）**：这是"为什么要局部 PF"的论据本身，不是要修的 bug；但实现 Window B 时必须落实 @@\Delta x\le48@@ nm。
- **F1/F2**：等 CALPHAD 数据。
- **V4（PF @@\leftrightarrow@@ LKT 渐近匹配）**：强制项，未做。它是两级之间唯一的可检验接口条件（§7.2）。
- **V6（横向 halo 的 domain-size convergence）**：未做（§4.1 的 RULE）。
