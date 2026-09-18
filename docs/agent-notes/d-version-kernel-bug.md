---
name: d-version-kernel-bug
description: D 版不收敛的真根因——splice_aniso.py 删掉 GrainGrowth 动作后手写的核漏了三处，解的根本不是同一个方程
metadata:
  node_type: memory
  type: project
  originSessionId: b6decc92-d1df-4297-b052-ad15b31c0547
  modified: 2026-09-17T15:34:56.197Z
---

**这是 D 版不收敛的真根因**（2026-09-18 找到）。属于"低级问题"一类，
正是最初该先排查的那一类。相关：[[d-version-stall-debug]]

## 背景
C 版的晶粒生长核来自 `[Modules/PhaseField/GrainGrowth]` 动作，`.i` 里只写了
```ini
[GrainGrowth]
  variable_mobility = true
  coupled_variables = 'T'
  mobility = L
  kappa = kappa_op
[]
```
`splice_aniso.py` 为了能逐核设置 `coupled_variables`（动作做不到：它把同一份列表
发给所有核，而每个核不该含自己的变量），**把整个 [Modules] 块删掉，手写了
8×(ACGrGrPoly + ACInterface)**。但 `GrainGrowthAction::act()`（第 118-175 行）
实际建的是 **三个**核，我漏了一处、写错两处：

| # | 动作建的 | 我写的 | 后果 |
|---|---|---|---|
| 1 | `TimeDerivative(variable)` | **完全没有** | 方程退化成**稳态** Allen-Cahn！晶粒内部 `0=0`、雅可比行为零 → 结构性奇异 |
| 2 | `ACGrGrPoly(v, **除自己外**的序参量)` | `v` = **含自己**的全部 8 个 | 晶粒内部多出 `2*gamma*mu ≠ 0` 的虚假驱动力 |
| 3 | `ACInterface(variable_L = variable_mobility)` | 没设，默认 **false** | 弱形式少掉 `gradL` 项（`nabla(L*psi)` 乘积法则那一半）→ 又一个不同的 PDE |

文档方程（`ACGrGrPoly.md`）：`mu*(eta_i^3 - eta_i + 2*gamma*eta_i*sum_{j!=i} eta_j^2)`
—— **求和排除自己**，与动作的 `v` 一致。

## 这一条把最强的那个线索解释干净了
日志里**首步残差在所有 dt 下逐位不变（3.537483e-05）**，从 1e-6 一路砍到
6.25e-8 全是同一个数。我先前解释为"首步 eta=eta_old 所以时间项为零" ——
**真相是方程里压根没有 dt。** 这也解释了：
* 砍 dt 完全无效
* `SUBPC_ERROR`（稳态下晶粒内部对角为零 → ILU 零主元）
* **所有材料侧的修改（align4 改写成有界形式、加显式 coupled_variables）全部无效** ——
  因为坏的从来不是材料，是核

## 方法论教训
我在**手写核**这件事上连错三次，所以最终的做法是：**先做自证单元测试**
（`verify_kernels.py` + `verify_kernels.sh`）—— 拿 **C 版**（材料不动）把它的
`[Modules]` 换成我手写的核，与未改动的 C 版逐位对比首步逐变量残差。
**只有逐位一致，才允许拿它去改 D 版。** 不要再靠"看起来对"。

## 修法（已实施，验证中）
`splice_aniso.py` 的核 emit 改成逐字复刻动作：
```ini
[gr0_dt]   type = TimeDerivative   variable = gr0 []
[gr0_poly] type = ACGrGrPoly  variable = gr0  v = 'gr1 ... gr7'  mob_name = L []
[gr0_int]  type = ACInterface variable = gr0  mob_name = L  kappa_name = kappa_op
           variable_L = true
           coupled_variables = 'T gr1 gr2 gr3 gr4 gr5 gr6 gr7' []
```
`coupled_variables` 多列其他序参量是必须的（L、kappa 都依赖它们，而 ACInterface
的雅可比只对 coupled_variables 求材料属性的导数）。

## 同时确认的两件事（非本 bug，但都是真问题）
1. **`L2b` / `L_aniso` 必须显式声明 `coupled_variables`**。
   `DerivativeParsedMaterialHelper::recurseMatProps` 的链式法则按**材料自己声明的
   符号表**展开：`if (!parent_mpd.dependsOn(derivative_symbol)) continue;`
   没声明 gr/T 就**不可能**生成 `dL/dgr_i`、`dL/dT`。
   已给 `L2b` 加 `coupled_variables='gr0..gr7'`、`L_aniso` 加 `'T gr0..gr7'`。
   **注意**：不必（也不应）声明 `grad_Tx/grad_Ty` —— 梯度方向经非导数
   `ParsedMaterial`（gdir_p/gdir_q）以数据身份进来，`1/G^2` 那类病态导数就不生成。
2. **`align4` 不要耦合 AuxVariable**（见 [[d-version-stall-debug]] 的梯度那节）。

## 验证结果（2026-09-18）

### 1. 核序列化自证：逐位通过 ✓
`verify_kernels.sh`：CR（未改动 C 版）vs CK（C 版 + 我手写的核），
材料完全相同（各向同性，故多列的 gr 导数为零、无害）。
**首步 10 个变量的残差逐位相同**（`4.414763e-05`），最大相对差 `0.000e+00`，
两边都在 1 步内收敛。牛顿序列仅第 3-4 位有浮点级差异。
**边界说明**：该测试验证的是**核结构**（TimeDerivative / v 排除自己 / variable_L，
以及"多列 gr 在导数为零时无害"）；各向异性下 gr 导数非零的那部分它没覆盖。

### 2. 修好核之后 D 版首步行为**彻底改变** ✓
| 牛顿迭代 | 修前 | 修后 |
|---|---|---|
| 0 | 3.537e-05 | 3.737e-05 |
| 1 | — | 3.316e-05 |
| 2 | — | 1.267e-05 |
| 3 | — | 1.141e-05 |
| 4 | — | 6.992e-06 |
| 结局 | `DIVERGED_LOCAL_MIN iterations 0`（牛顿**一步都动不了**） | 走 5 步、残差降 5.3 倍，停在 `DIVERGED_ITS 30` |

首步残差由 3.537e-05 变为 3.737e-05，**说明方程本身变了**（现在才是有时间导数、
正确 v、含 gradL 的那一个）。

**失败模式从"雅可比结构性奇异、牛顿无法起步"变成"线性迭代数不够"** ——
后者是可靠调求解器解决的。`sweep_fixed.sh` 正在扫 5 种配置
（asm/ilu 原样、l_max_its=300、非零主元平移、hypre boomeramg、ILU 二级填充）。

**关键教训：在这个核 bug 修好之前，所有求解器调参都是在**错误的方程**上做的，
全部无效。排查顺序必须是"先确认解的是不是同一个方程"，再谈求解器。**
