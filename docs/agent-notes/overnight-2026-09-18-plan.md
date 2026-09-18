---
name: overnight-2026-09-18-plan
description: 2026-09-18 夜间自主工作的计划与已知状态（用户授权连夜推进 D 版收敛并开始填物理缺口）
metadata:
  node_type: memory
  type: project
  originSessionId: b6decc92-d1df-4297-b052-ad15b31c0547
  modified: 2026-09-17T17:47:24.085Z
---

用户 2026-09-18 睡前授权：**先把 D 版改到收敛，然后开始填物理缺口；遇到的问题记下来，
能解决的就解决，希望早上起来已完成很多工作。**

## 已完成（有验证）

1. **手写核的三个 bug**（[[d-version-kernel-bug]]）：缺 `TimeDerivative`、`v` 含自己、
   缺 `variable_L`。用法与 `GrainGrowthAction::act()` 逐字对齐。
   **逐位自证通过**：`verify_kernels.sh`（C 版 + 我手写的核 vs 未改动的 C 版，
   首步 10 个变量残差最大相对差 `0.000e+00`）。

2. **根因二：`ACGrGrPoly::computeQpOffDiagJacobian` 覆盖了基类 `ACBulk` 的正确实现，
   丢了 `∂L/∂η_j` 项。** 这是 MOOSE 侧的 bug（基类 ACBulk.h 是对的，被遮蔽）。
   - C 版不可见（L 只依赖 T → 缺项为零）
   - 2a/2b 都把 η 依赖放进了 L → 必然触发
   - **定量确认（J4）**：只把 L 换成"只依赖 T"，小网格 `||J-Jfd||/||J||`
     从 **0.0594 → 2.11e-05**（降 2800 倍）；kappa/gamma 怎么关都是 0.0594/0.0596

3. **AD 转换已实施**：`ADDerivativeParsedMaterial` ×4 + `ADParsedMaterial` ×1，
   核换 `ADTimeDerivative`/`ADGrainGrowth`/`ADACInterface`，`grad_align` 换
   `ADMaterialRealAux`。`L` **全部内联成单表达式，零 `material_property_names`**
   （理由是"AD 材料消费 material_property_names 的链式行为"我没验证过 ——
   没验证过的机制不用）。
   - 最小验证：`||J-Jfd||/||J|| = 3.20e-08`（比 C 基线 1.05e-06 还精确 30 倍）
   - 材料值与非 AD **逐位相同**（kappa_op/gamma_asymm/L 的 max/min 全部一致）
   - 顺带修好 `align4` 的 initial NaN（实测 `align4_min = 0`）

4. **约束**：`MOOSE_AD_MAX_DOFS_PER_ELEM = 64`；本算例 11 变量 × QUAD4 4 节点 = 44 ✓
   不需要重编译。**op_num 若增到 11 则 14 变量 × 4 = 56 < 64，仍可行。**
   MOOSE 禁止同一属性既作 AD 又作非 AD 声明 → `kappa_op`/`gamma_asymm`/`mu`/`L`
   必须全 AD 且无非 AD 消费者（已核对：只有 grad_align 一处，已改）。

## 未解决 / 待办

### A. 未解疑点（必须查）
AD 版首步残差 `3.9107e-05` vs 非 AD 版 `3.7375e-05`，**差 4.6%**。
而三者**都已核实相同**：κ/γ/L 的**值逐位相同**、核残差公式**逐字等价**、
核参数（`v`/`variable_L`/`coupled_variables`）**逐项相同**。
差异形态是 gr3/gr4 偏高、gr0/gr1 偏低（非整体缩放）→ 像某项在空间上重新分配
→ 怀疑 `gradL` 那一项。**靠推理定位不了，需进一步测量**
（建议：把 `variable_L` 两边都设 false 做 A/B；或对 `dL/dgr0` 等导数属性做极值对比）。

### B. D 版收敛（阻塞项）
- AD + `l_max_its=30`：牛顿单调下降但 2 次 `DIVERGED_ITS 30`
- AD + `l_max_its=300`：牛顿到迭代 4（3.91→2.75e-05），仍有 2 次 `DIVERGED_ITS 300`
- **`solver_batch.sh` 在跑** 4 种预条件子：P1 asm+`sub_pc_type lu` ov1、
  P2 同 ov2、P3 ilu+factor_levels 3、P4 asm+lu+1000。判据：零线性失败 + 线性收敛。
- **AD 版显著更慢**（L 依赖 8 个 η + T + 梯度 → 每单元 44 维对偶数，
  内联表达式 2884 字符）。全量 6.5e-4 可能要数小时 → **收敛配置一确定就要立刻起全量跑**。

### C. 训练数据质量问题（高价值、可自主完成）
`coloring_algorithm = bt` 对 11 个柱状种子求得的邻接图**色数只有 5** ≤ op_num=8
→ **gr5/gr6/gr7 恒等于零**（C 版与 D 版的逐变量残差都是 1e-33~1e-45，一致）。
后果：**11 个晶粒压在 5 个序参量上 → 实际只有 5 个不同取向**；
共用序参量的晶粒在 2b 里被当作**同一取向**，extract.py 反解的 θ 也会重复。
**修法**：`op_num` 提到 ≥ 晶粒数（11），使每个晶粒有独立序参量与独立取向。
顺带可一并解决物理缺口 #5（真实 <100> 纤维织构）。
代价：要同步改 `feat_spec.py` / `extract.py` / 训练管线的维度。
**注意**：op_num=11 → 14 变量 × 4 = 56 dof < 64 ✓ 仍不用重编译。

### D. 七条物理缺口（[[physics-gaps-for-reviewers]]）
一条都还没动。可自主推进的：
- **#1 `A_ani=0.7` 无标定**：做灵敏度扫描（A_ani ∈ 0/0.3/0.7/1.0）给出量化依据
- **#4 Q 无取向差依赖**：需文献支撑，做检索
- **#6 Ti64 真实溶质热力学**：需文献数据，做检索
- #2 形核（无形核故无等轴晶，LPBF 标志性特征）—— 模型改动，需谨慎
- #3 溶质截留（δ_c~8nm 比网格小两个数量级）—— 需换模型

## 环境坑（今天踩过多次）
Git Bash → WSL 这条链上：
1. **内联命令里的 `$VAR` / 循环变量会被吞** → 一律写 `.sh` 文件跑
2. **`pgrep -f "phase_field-opt -i"` 会匹配到执行它的 shell 自身**
   → `kill -9` 杀掉自己（exit 9）。必须把 kill 放进 `.sh` 文件里，
   或让命令行不出现该模式串
3. `pkill -f phase_field-opt` 同理会杀自己的 shell
4. heredoc 传 Python 源码会被 `\n` 转义搞坏 → 用 Write 工具写文件
