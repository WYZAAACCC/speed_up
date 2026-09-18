---
name: d-version-stall-debug
description: D 版（2a+2b）不收敛排查——根因是 ACInterface 缺 coupled_variables（已修）；2a 已数值验证物理正确；现卡在预条件子
metadata:
  node_type: memory
  type: project
  originSessionId: b6decc92-d1df-4297-b052-ad15b31c0547
  modified: 2026-09-17T15:09:39.702Z
---

`stage1_meltpool_d.i` = C 版（柱状基体+溶质，已验证收敛）+ 2a + 2b。
**D 版仍未收敛。但 2a 的物理已被数值验证正确。**

## 已确认为 bug 并修复

### 1. ACInterface 的 coupled_variables 缺序参量（根因，已修）
`ACInterface` 的雅可比只对 `coupled_variables`（args）求材料属性导数。原来写
`coupled_variables = 'T'`（C 版正确，因 L 只依赖 T），但 D 版 κ 和 L 都依赖
`gr0..gr7` → **所有跨序参量雅可比项丢失**。MOOSE 日志一直在警告
`Missing coupled variables {gr1..gr7}`，之前漏看了。
修法：在 `splice_aniso.py` 里显式生成 8 组核，每个核的 `coupled_variables`
列出除自己外的全部序参量 + T。**不能用 GrainGrowth 动作**（它把同一个列表发给
全部 8 个核，报"kernel variable should not be in coupled_variables"）。
参数名是 `coupled_variables` 不是 `args`。修复后告警 8 条 → 0 条。

### 2. gen_aniso.py 里的变量遮蔽（已修）
`main()` 里曾写 `MU_QP = compute_mu_qp(...)`，**遮蔽了同名全局常量**，
导致脚本静默用 763136 而不是 900000，自检随之"不符"。已删掉该行。

## 2a 物理正确性：已数值验证 ✓

工具 `check_gb_energy.py`：解 1D 平衡晶界，量**真实**界面能 vs Read-Shockley 目标。

理论：对 γ=1.5，两序参量约化下 `η_m+η_n=1` 是精确解（两式相减得
`η(3-2γ)(1-η)=0`），约化为 φ⁴ kink，`σ = √(2κμ)/3`。
各向同性验算 `√(2·1.8e-6·9e5)/3 = 0.6 = σ_H` ✓

**结果：用 μ=9e5，全部 28 对 |σ真实/σ目标 − 1| ≤ 8.96e-05 ✓**
（κ* 范围 1.247e-6~1.8e-6，γ* 范围 1.027~1.500，与 MOOSE 实测逐位吻合）

### mu_qp 必须是熔化开关的 9e5，不是 GBAnisotropy 的 763136
Moelans 不动点的 (a*,γ*) 是**针对特定 μ 解出来的**，必须用算例真正用的 μ。
本算例 μ 被熔化开关锁死在 `6σ_H/w = 9e5`，改不得。GBAnisotropy 能用
`6·sigma_init/w`（本算例 = 763136，因 Read-Shockley 使 σ_min=0.4175）是因为
它自己声明并写入 `mu`（所以本算例不能用该材料）。
数值判定：换成 763136 后第 1 对就松弛不到平衡，**γ* 冲到 1.926** —— 不自洽。
`compute_mu_qp()` 保留在 gen_aniso.py 里作"反例存档"。
**改 barrier_mu 的 mu0 时必须同步改 MU_QP 并重新生成 aniso_block.i。**

## 2b 的形式是干净的（排除）

`(P,Q)/G`（P=gx²−gy², Q=2gxgy, G=gx²+gy²）是**单位向量**（因 P²+Q²=G²），所以
```
align4 = Σ η_i²·cos²(2(φ−θ_i)) / (Ση_i² + δ)      δ=1e-3
```
**G² 在分子分母精确抵消** ⇒ align4 只依赖梯度的**方向**，与**大小**无关。
- 值域 [0,1]，对 η 的导数 O(1) 且不含 G
- 所以「按参考量级归一化梯度」是**彻底的 no-op**，别再试
- 「G² 跨 14 个量级导致条件数恶化」的怀疑**不成立**
- 数值上也无溢出/相消损失（分子分母同为 ~1e35，比值 O(1)）

## 当前症状与已排除的方向

失败模式演进（每步都变得"更容易解决"）：
| 阶段 | 症状 |
|---|---|
| 修 coupled_variables 前 | 牛顿残差停非零地板 4.29e-07 + DIVERGED_ITS |
| 修后 | 告警 0 条；变成 `SUBPC_ERROR` |
| + `-sub_pc_factor_shift_type nonzero -sub_pc_factor_shift_amount 1e-8` | SUBPC_ERROR 消失 → `DIVERGED_ITS 30` |
| + `l_max_its=300` | `DIVERGED_BREAKDOWN iterations 31`（正好在 gmres restart=31 处） |

**最有说服力的一条**：首步 dt 从 1e-6 一路砍到 **6.25e-8 全部失败**。
缩小 dt 不能改善 ⇒ 问题不在非线性/时间积分刚性，而在**初始状态的雅可比本身**。
配合 `DIVERGED_LOCAL_MIN at iteration 0`（第一次线性求解就废，牛顿无法起步）。

逐变量残差（`show_var_residual_norms`，t=1e-6 首步）：
```
gr0:1.24e-05 gr1:1.99e-05 gr2:6.47e-06 gr3:4.91e-06 gr4:2.52e-05
gr5:7.32e-34 gr6:4.59e-43 gr7:1.07e-42     c:7.39e-11  w:0
```
各 dt 下残差**逐位不变**（3.537483e-05）⇒ 初值残差无时间导数项贡献（首步正常现象），
所以残差**大小**不是判据、**分布**才是。

已实测排除（有实验证据）：
- `material_property_names` 二阶链式求导（v4 内联后仍卡）
- AuxVariable 耦合进二阶 DerivativeParsedMaterial（最小实验 A/B 雅可比误差同为 4.58552e-10）
- 纯输出 MaterialRealAux 扰动求解（W1 残差序列与 v0 逐位相同）
- 2b 挪到 `mu`（ACGrGrPoly 用 mu 时不取任何导数，W3 更差 2.08e-05）
- L / κ 本身病态：**不是**。L 与 Arrhenius+冷远场一致（1.786e6 ~ 5.3e-40），
  κ 反解 σ 与目标吻合

## 顺带发现的两个真问题（非卡住原因，但要修）

1. **`grad_align` 在 initial 阶段全域 NaN** —— CSV 里 `align_max=-1.798e308`
   /`align_min=+1.798e308`（ElementExtremeValue 的初值哨兵，从未更新）、
   `align_mean=nan`。原因：initial 阶段 FunctionAux 尚未填充 `grad_Tx/grad_Ty`
   时材料已被求值 → `G=0` → `align4 = 0/0`。但首步残差是有限值，说明求解时
   L 并未 NaN，**所以这是输出诊断的 bug，不是卡住的原因**。
   修法：分母的 `G²` 加下限（如 `max(G,eps)²` 或 `(G²+tiny)`）。
2. **只有 5 个序参量真正被使用**：`coloring_algorithm = bt` 对 11 个柱状种子
   求得的邻接图色数只有 5 ≤ op_num=8，所以 gr5/gr6/gr7 恒等于零。
   后果：11 个晶粒压在 5 个序参量上 → **实际只有 5 个不同取向，不是 8 个**；
   共用一个序参量的晶粒在 2b 里被当作**同一取向**，extract.py 反解出的 θ 也会重复。
   这是数据质量问题，写论文前要处理（改 IC 强制 8 色 / 或按晶粒而非序参量定取向）。

## 下一步

`ab_variants.sh` 正在跑消融 A/B（C 基线 + v0 D原样 + v1 关2b + v2 L各向同性
+ v3 κ/γ常数），全部带逐变量残差、统一 end_time=1e-6、统一求解器，5 进程并行。
判据：哪个变体首步能收敛 → 锁定 2a/2b 的哪一半。
若 C 与 v3 收敛、v1/v2 不收敛 → 问题在 L 的取向依赖路径。

另待跑：`test_jac_real.sh`（D 版 `-snes_test_jacobian`，缩网格 20×8）。
**注意该脚本含 `pkill -9 -f phase_field-opt`，会杀掉其他 MOOSE 任务，不能在
有并行任务时跑。** 基线参照：no2b 的 `||J−Jfd||/||J|| = 1.2e-3`。

求解器候补（`try_solvers.sh` 已并行测）：hypre boomeramg / hypre+ASM 混合 /
MUMPS 直接解 / ASM+ILU 多重叠。理由是正确雅可比比缺项雅可比更稠密更刚，
ILU/ASM 扛不住是常见工程问题。

相关：[[moose-api-gotchas]]、[[physics-gaps-for-reviewers]]
