# Ti-6Al-4V LPBF 相场—神经算子项目：专家审核与执行路线

## 结论先行

这项工作目前可以被评价为“数值工程基础较强、物理闭合尚未完成”。ASM/MUMPS 对照、核等价性、Read–Shockley 晶界能实现、Newton 收敛诊断和成本剖析是可信的；但当前模型不能宣称已经给出真实 Ti64 的凝固偏析或晶界扩散，因为：

1. 4 µm 弥散界面远大于 V/Al 的物理扩散边界层（nm 量级），当前 CH 结果只能解释为模型尺度结果。
2. `f_solute` 没有进入序参量方程，体系不是单一自由能的变分模型，因此没有溶质拖曳。
3. `M0=232`、`A_ani=0.7`、`sigma_H=0.6 J/m²` 尚未形成可追溯的实验/计算标定链。
4. 训练数据若来自当前粗界面模型，神经算子只会加速“错误模型”，不能满足“接近真实物理”的硬约束。

因此，**不要立即开始大规模 NN 训练**。先完成一个可证伪的物理基准层，再决定是否训练算子。

## 对现有判断的逐项审核

### 正确且应保留

- 采用隐式 BDF2、Newton、ASM/ILU，并用相同容差比较 MUMPS，是合理的工程选择。全尺寸 fill-in 导致 MUMPS 失去优势，不能由缩小网格外推。
- 把 `nl_abs_tol` 与解误差做单变量对照是正确的；生产算例应使用 `1e-9` 级别，并报告守恒误差、自由能变化和网格/时间步收敛，而不只报告残差。
- 手写 `ACInterface`/`ACGrGrPoly` 以排除自身耦合变量，在当前 MOOSE 版本下是可接受的实现策略。
- Read–Shockley 取向差和梯度方向各向异性应保留，但必须把 `A_ani` 标为标定参数，而不是物性常数。
- “Ti64 LPBF 主要柱状外延、形核弱”作为默认基线合理；形核应作为独立敏感性分支，而不是无证据硬塞进主模型。

### 必须修正或降级表述

1. **把当前 CH 结果降级为“数值/等效模型结果”**。除非完成薄界面渐近验证或 GP 基准验证，不能称为定量偏析。
2. **恢复变分一致性**：定义一个总泛函
   `F = ∫[f_phase(η,T)+f_chem(c,η,T)+κ_c|∇c|²/2+Σκ_η|∇η|²/2]dV`，使 `η` 方程包含 `∂f_chem/∂η`。这是 solute drag 的最小正确修复；不能再用只在 CH 方程出现的分凝项。
3. **GP 不能直接被假定为“任意 W 都定量”**。Plapp (2011) 的结论是通过 grand-potential 变量构造可定量合金模型并展示界面厚度扫描；Aagesen et al. (2018) 强调界面厚度与界面能可解耦，但两者都不等于“W/(D/V)=480 在所有动力学下无误差”。必须做 1D travelling-front 校验。
4. **溶质拖曳与晶界偏析不是同一问题**。先验证移动平面界面上的拖曳，再做晶界 Gibbs 过剩；不要用一个 `A_part` 同时代表液固分配和晶界偏析。
5. **“三重积恒等式”目前不能用于本项目时窗**。Fisher/Whipple/Suzuoka 的 B 型近似需要体扩散长度显著大于晶界宽度；你给出的 `1.3 µm < 4 µm` 已直接否定该前提。因此不能仅靠 `s·w·D_GB` 重标定来宣称动力学等价。

## 推荐的科学路线（按闸门执行）

### Gate 0：冻结可重复性（1–2 天）

- 固化非 AD 生成器、输入文件哈希、MOOSE/PETSc 版本、MPI 进程数和随机种子。
- 将生产值同步进源文件：`nl_abs_tol=1e-9`；初始 `dt=1e-7`；`dtmax=2e-6`（除非新的能量稳定性实验支持放宽）。
- 每个算例自动输出：总溶质质量相对误差、序参量最大值、自由能、Newton/线性迭代、 wall time、峰值内存。

### Gate 1：物理单元测试（先于二维熔池）

1. 纯晶粒长大：无温度梯度、无溶质，验证圆/柱晶长大与 `R²∝t`。
2. 平面液固界面：扫描 `W/(D/V)={1,2,4,8,16,32,64,128,256,480}`；输出 `k_eff`、界面速度、液相/固相浓度、总质量。
3. 每个 W 同时测试：普通浓度模型、GP 模型、含/不含 anti-trapping。判据建议：`|k_eff-k_ref|<2%`，速度误差 `<2%`，守恒 `<1e-8`。若 480 不达标，不能用 GP 作为“真实粗网格真值”。
4. 变分耦合测试：固定移动晶界，改变 `c0`、扩散系数和偏析能，确认迁移速度随溶质改变且与 Cahn solute-drag 趋势一致。

### Gate 2：热力学输入分层

- 液固分配 `k_V(T,v)` 不应固定为 0.630；至少给出温度/速度区间和不确定度。优先用 PanTi/Thermo-Calc 在实际液相线温度计算；若只能用文献值，报告 `0.55–0.75` 的敏感性区间。
- `M0` 不要伪装成文献常数。以 Semiatin 1996 的晶粒长大数据反演，给出后验区间；建议先扫 `M0={50,100,232,500,1000}` m⁴/(J·s)。
- `sigma_H` 先使用 `0.4–0.8 J/m²` 敏感性带，直到获得直接测量/MD/DFT 支撑；0.6 只能是 baseline。
- `A_ani` 只作为校准参数，建议 `{0,0.3,0.7,1.0}`，目标是晶粒长宽比、织构强度和柱状/等轴比例，而不是任意选择 0.7。
- 对 β 晶界 V 偏析方向保持双分支：`E_seg>0`（富集）与 `E_seg<0`（反偏析），直到获得 β-Ti 特定证据。不要把 α/α APT 结果直接迁移到 β/β。

### Gate 3：二维熔池与数据

- 先用传统求解器完成“低维、可解释”的 reference set：至少 30–50 条轨迹；参数采用 Latin hypercube，覆盖激光速度、功率/热源尺度、初始晶粒取向、`k_V`、`M0`、`sigma_H`。
- 数据划分按物理参数分层，不要随机切相邻时间帧：train/validation/test 必须包含未见过的速度、温度梯度和晶粒取向。
- NN 先只学“单步增量/残差”或溶质子问题，不替代完整拓扑演化。每 1–5 个 NN 步插入一次传统校正，并用守恒投影修正 `c`。
- 评价不只用 L2：质量守恒、最大/最小浓度、界面速度、晶粒面积分数、拓扑事件、长时间 rollout 稳定性都必须通过。
- RTX4060 8 GB 适合小型 U-Net/FNO/DeepONet 的 patch 或低分辨率 latent 模型；不要把 430×150×多变量全场直接堆进大型 Transformer。优先 FP32、batch 1–4、梯度累积和混合精度；CPU/MOOSE 仍是主要瓶颈。

## 关于神经算子“真值”的最终建议

推荐采用双层参考，而不是把粗网格 CH 当真值：

1. **Reference A（可验证）**：1D/2D GP 或薄界面高分辨率算例，给出界面速度、`k_eff` 和守恒基准。
2. **Reference B（工程）**：430×150 µm 的完整熔池算例，用于训练/加速。

只有当 B 在 Gate 1 中相对 A 通过误差门槛时，才可称为“物理近似真值”。否则 NN 的任务应改写为“加速等效模型”，论文中必须明确限制。

## 建议的最小论文级结果包

- 网格收敛：`dx={0.5,1,2} µm`（至少在 1D/局部二维）。
- 时间步收敛：`dtmax={0.5,1,2,4} µs`，能量/守恒/形貌三者同时报告。
- GP 扫描表：每个 W 给 `k_eff`、速度、守恒误差和计算时间。
- 溶质拖曳 A/B：同一界面、同一速度，仅改变溶质耦合。
- 参数不确定性：`k_V, M0, sigma_H, A_ani` 的 Sobol 或 LHS 敏感性。
- NN rollout：至少 10× 目标时间窗，报告误差是否随时间爆炸。

## 可核实的核心文献与 DOI

1. Plapp, “Unified derivation of phase-field models for alloy solidification from a grand-potential functional,” *Phys. Rev. E* 84, 031601 (2011). DOI: **10.1103/PhysRevE.84.031601**.
2. Aagesen, Gao, Schwen, Ahmed, “Grand-potential-based phase-field model for multiple phases, grains, and chemical components,” *Phys. Rev. E* 98, 023309 (2018). DOI: **10.1103/PhysRevE.98.023309**.
3. Echebarria, Folch, Karma, Plapp, “Quantitative phase-field model of alloy solidification,” *Phys. Rev. E* 70, 061604 (2004). DOI: **10.1103/PhysRevE.70.061604**.
4. Kim, Lee, Lee, “Thermodynamic properties of phase-field models for grain boundary segregation,” *Acta Materialia* 112, 150–161 (2016). DOI: **10.1016/j.actamat.2016.04.028**.
5. Kim, Park, “Grain boundary segregation, solute drag and abnormal grain growth,” *Acta Materialia* 56, 3739–3753 (2008). DOI: **10.1016/j.actamat.2008.04.007**.
6. Mishin, “Solute drag and dynamic phase transformations in moving grain boundaries,” *Acta Materialia* 179, 383–395 (2019). DOI: **10.1016/j.actamat.2019.08.046**.
7. Gornakova & Prokofjev, “Energetics of intergranular and interphase boundaries in Ti–6Al–4V alloy,” *J. Mater. Sci.* 55 (2020). DOI: **10.1007/s10853-020-04432-w**. Use as a source to inspect, not as proof that 0.6 J/m² is validated.
8. Lee, Taguchi & Iijima, “Interdiffusion in β-Ti alloys,” *Materials Transactions* 51 (2010). DOI: **10.2320/matertrans.M2010225**.
9. Liu et al., “First-principles screening of transition-metal segregation at bcc grain boundaries,” *J. Alloys Compd.* (2025). DOI: **10.1016/j.jallcom.2025.173646**. Treat the β-Ti applicability as a hypothesis requiring direct inspection.
10. Breen et al., “Quantifying changes to solute segregation behaviour at interfaces in additively manufactured Ti-6Al-4V,” *Acta Materialia* 306, 121904 (2026). DOI: **10.1016/j.actamat.2026.121904**. Extract numerical Gibbs excess values from the full text before calibration.
11. Guin et al., “First-principles-informed phase-field modelling of solute drag…” *Modelling Simul. Mater. Sci. Eng.* 32, 065009 (2024). DOI: **10.1088/1361-651X/ad585d**.
12. Moelans, Blanpain, Wollants, “Quantitative analysis of grain boundary properties in a phase-field model for grain growth,” *Phys. Rev. B* 78, 024113 (2008). DOI: **10.1103/PhysRevB.78.024113**.

## 可直接采用的参数表（仅作起始扫描，不是最终物性）

| 参数 | baseline | 建议扫描/报告 |
|---|---:|---:|
| `W` | 4 µm | 0.5, 1, 2, 4, 8 µm（单元测试） |
| `k_V` | 0.63 | 0.55–0.75；随 T/v 的 CALPHAD 曲线优先 |
| `sigma_H` | 0.6 J/m² | 0.4–0.8 J/m² |
| `M0` | 232 m⁴/(J·s) | 50, 100, 232, 500, 1000 |
| `Q` | 312 kJ/mol | 固定为文献基线，明确适用温区 |
| `A_ani` | 0.7 | 0, 0.3, 0.7, 1.0 |
| `dtmax` | 2 µs | 0.5, 1, 2, 4 µs，仅在能量稳定性通过后放宽 |
| `nl_abs_tol` | 1e-9 | 与 1e-8、1e-10 做敏感性对照 |

## 最终判断

当前工作最适合定位为：**“面向 Ti64 LPBF 的可验证相场数值框架与神经算子加速预研”**，还不适合定位为“已实现真实晶界偏析的定量预测”。只要按 Gate 0–3 推进，保留双分支（GP 成功/失败）和参数不确定性，这个项目仍然可以形成一篇方法学上严谨、工程上可运行的工作；若跳过 Gate 1，NN 会把未验证的尺度误差固化并放大。
