# 最终深度审计

## 1. 审计范围

审计了仓库当前 HEAD `ec103592`，重点包括：

- `pipeline/stage1_meltpool_c.i` / `_d.i`
- `pipeline/frozen/gen_aniso_nonad.py`
- `pipeline/frozen/splice_aniso_nonad.py`
- `pipeline/tests/*`
- `pipeline/run_nonad_prod.sh`
- `pipeline/extract.py`
- `pipeline/train_operator_v3.py`
- `GATE1_PLAN.md`、`OPEN_PROBLEMS.md`、`GB_SOLUTE_GOAL.md`

## 2. 最终判定

### 可以保留

1. Landau 熔化开关修复：原液相自由能下无界的问题已被正确识别，修复形式方向正确。
2. 冻结的非 AD 生成器和哈希检查：适合保证生产输入可复现。
3. ASM/ILU 的全尺寸路线：比 MUMPS 更适合 32 GB 笔记本。
4. 1D 平面前沿、纯晶粒长大、分配系数和守恒测试框架。
5. `extract.py` 对多块 Exodus 的处理方向；它比早期只读 `eb1` 的版本可靠。

### 当前不能宣称

1. 不能宣称已经定量表示 Ti64 晶界偏析。
2. 不能宣称已经表示晶界快速扩散；当前全域基本使用同一个 `M`。
3. 不能宣称已经实现溶质拖曳；当前溶质自由能没有完整进入序参量方程。
4. 不能宣称 `kappa_c=1e-14` 已被网格解析；其对应长度约为 0.105 µm，而 `dx=1 µm`。
5. 不能宣称 `W/(D/V)≈476` 下 GP 或抗截留项一定定量；必须实测扫描。
6. 不能把 `wGB=12 µm` 直接当作欠解析修复；必须做 epsilon 收敛。

## 3. 阻断性代码问题

### P0：SplitCHParsed 缺少序参量耦合声明

`f_loc` 依赖 `c, gr0...gr7`，但 `coupled_parsed` 未声明全部 `gr`。这会使残差与雅可比不一致，导致不必要的 Newton 迭代和预条件器退化。

先修复：

```text
[coupled_parsed]
  type = SplitCHParsed
  variable = c
  f_name = f_loc
  kappa_name = kappa_c
  w = w
  coupled_variables = 'gr0 gr1 gr2 gr3 gr4 gr5 gr6 gr7'
[]
```

修复后必须做 Jacobian 检查，并比较修复前后的物理解、迭代数和守恒。

### P0：液固分配与晶界偏析混为一项

当前：

```text
f_loc = k_c/2*(c-c0)^2 + A_part*c^2*sum(gr_i^2)
```

`sum(gr_i^2)` 在液相、晶粒内部、固固晶界分别近似为 0、1、0.5。因此 `A_part` 同时改变液固分配和固固晶界化学势。当前所谓晶界富集不能解释为独立的 Ti64 晶界偏析。

必须拆成：

```text
f_solute = f_liquid_solid_partition(c, phase)
        + f_gb_segregation(c, gb_indicator)
```

第二项必须由偏析焓、McLean 等温线或实验 Gibbs 过剩量标定。

### P0：没有晶界快速扩散

当前溶质场没有独立的晶界扩散通道。必须引入连续的晶界指示函数 `h_gb` 和：

```text
D = D_bulk + h_gb*(D_GB - D_bulk)
```

或迁移率等价形式，并用 1D 晶界示踪算例验证有效 `s*δ*D_GB`。

### P0：固相扩散系数会被当前自由能推高

当前 `D=M*f_cc`，而 `f_cc=k_c+2*A_part*sum(gr_i^2)`。因此固相 `f_cc≈1.428`、液相 `f_cc=0.9`，在统一 `M` 下固相扩散反而快约 1.59 倍。必须显式区分 `D_L(T)`、`D_S(T)` 和 `D_GB(T)`。

## 4. 物理模型风险

### 温度场

Rosenthal 点源在源点附近给出约 1.5 万 K。该温度会进入 Arrhenius 迁移率和材料导数，影响刚度和晶粒速度。必须增加有限源半径或统一的 `T_eff=min(T,T_cap)`，并做截断敏感性测试。

### 变分一致性

当前 `f_loc` 只进入 `c` 方程，未进入 `η` 方程，因此没有溶质拖曳。应让同一 `f_solute(c,η)` 同时产生 `δF/δc` 和 `δF/δη`，然后用移动平面晶界做受控验证。

### 界面宽度

“4–8 个单元”不是充分条件。必须扫 `wGB` 和 `dx`，比较 `σ_eff`、平面速度、圆晶粒 `R²` 斜率、三叉角、`Γ_GB` 与 `k_eff`。只要观测量未收敛，模型就不能称为定量。

### 神经算子真值

当前模型仍有上述结构性缺陷；在修复并通过物理测试前，生产 Exodus 不可作为“真实晶界扩散”训练真值。

## 5. 笔记本可行性判定

- 当前 PETSc/ASM 路线主要使用 CPU；RTX 4060 不会自动加速 MOOSE 主求解。
- 32 GB 内存应按每条任务约 4–6 GB 预算，保留操作系统和 WSL 余量。
- 推荐 4–8 MPI 进程，不建议盲目使用全部 20 个逻辑线程。
- 必须激活包含 `mpicxx` 的 MOOSE 环境，否则 ParsedMaterial JIT 失败后会退回解释执行，结果可能相同但速度显著下降。
- 全尺寸生产跑只在 Gate 1 全部通过后进行。
