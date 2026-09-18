# Gate 0 实施规划：冻结可重复性 + 每算例自动诊断

> 依据：`ROADMAP.md` §4.0 Gate 0（两份专家评审合并版）
> 建立：2026-09-18
> **状态：规划完成，待实施**

---

## 一、为什么做这一步

两份独立专家评审都把 Gate 0 排在最前，理由一致：

> **「若跳过 Gate 1，NN 会把未验证的尺度误差固化并放大。」**

而 Gate 0 是 Gate 1 的前提：**如果算例本身不可复现，Gate 1 的误差判据（`k_eff < 2%`、速度 `< 2%`、
守恒 `< 1e-8`）就无从谈起**——你无法区分"物理误差"与"配置漂移"。

**当前状态核对（与代码逐条核对过）**：

| 项 | 现状 | 位置 |
|---|---|---|
| `nl_abs_tol` | **1e-7**，应为 1e-9 | `stage1_meltpool_c.i:364` |
| 起始 `dt` | **1e-6**，应为 1e-7 | `stage1_meltpool_c.i:373` |
| 生成器版本 | 非 AD 版在 `/root/work/bak/`（WSL，无版本管理）；仓库里是 AD 版 | — |
| 输入文件哈希 | **完全没有** | — |
| MOOSE/PETSc 版本记录 | **完全没有** | — |
| 自由能诊断输出 | **没有** | — |
| 迭代数诊断输出 | **没有** | — |
| 机器可读诊断汇总 | **没有**（现有全是 `printf` 人读文本） | — |

⇒ **Gate 0 尚未开始。**

---

## 二、已核实的 MOOSE API 事实（本次实测，带源码行号）

这些全部在 WSL 的 `/root/moose` 源码与 `phase_field-opt` 二进制上实测过，**不是查文档得到的**。

### 2.1 纠正：参数名是 `mat_prop`，不是 `material_property`

```cpp
// framework/src/postprocessors/ElementIntegralMaterialProperty.C:22
params.addRequiredParam<MaterialPropertyName>("mat_prop", "The name of the material property");
```

**判决性验证**（`/tmp/t4.i`，常数材料 `fconst = 3.5`，域体积 `2.0`）：

```
| time | Fconst | umax | umin | vol |
| 1.00 | 7.0000 | 0.70 | 0.70 | 2.00 |
```

`7.0 = 3.5 × 2.0` ⇒ **积分器精确**。若按错误的 `material_property` 写，MOOSE 会因
未使用参数报错（除非加 `-w`，那就会被**静默忽略**——本项目已在
`-sub_pc_asm_overlap` 上踩过这个坑）。

### 2.2 迭代数有现成后处理器，**不需要解析日志**

```cpp
// framework/src/postprocessors/NumNonlinearIterations.C / NumLinearIterations.C
// NumNonlinearIterations 有 accumulate_over_step 参数
```

实测（2D 扩散+反应，`Mesh/nx` 与 `nl_rel_tol` 均用 CLI 覆盖）：

| 配置 | `NumElements` | `NumLinearIterations` | `NumNonlinearIterations` |
|---|---:|---:|---:|
| 默认 nx=10 | 100 | 27 | 2 |
| `Mesh/nx=4` | **40** | 15 | 2 |
| `Mesh/nx=4 Executioner/nl_rel_tol=1e-3` | 40 | **7** | **1** |

⇒ **直接进 `*_out.csv`，机器可读，不用剥 ANSI 色码、不用正则。**
这是对原计划（解析 `run.log`）的重要改进——日志解析在本仓库已内联重复 40+ 次，
是最大的重复造轮子来源。

### 2.3 CLI 覆盖语法**确实生效**

```bash
phase_field-opt -i in.i Mesh/nx=4 Executioner/nl_rel_tol=1e-3 Outputs/csv=false
```

已验证**不是被静默忽略**：同一算例 `nx=10 → nx=4` 时牛顿初始残差从 `9.5e-2` 变为 `1.44e-1`，
`NumElements` 100 → 40。⇒ **小域回归算例不需要再生成一份 .i 文件**，
极大简化 Gate 0 与后续 Gate 1 的扫描。

### 2.4 `ACGrGrPoly` 的体自由能**有精确解析式**

这是本次最关键的发现——**晶粒自由能可以在输入文件里精确复现**，不必自己重实现：

```cpp
// modules/phase_field/src/kernels/ACGrGrPoly.C:60  computeDFDOP(Residual)
return _mu[_qp] * (op*op*op - op + 2.0 * _gamma[_qp] * op * SumOPj);
//                                                        ^^^ SumOPj = Σ_{j≠i} η_j²
```

反推自由能（要求 `∂f/∂ηᵢ = mu·(ηᵢ³ − ηᵢ + 2γ·ηᵢ·Σ_{j≠i}ηⱼ²)`）：

```
f_grain = mu · [ Σᵢ(ηᵢ⁴/4 − ηᵢ²/2) + (γ/2)·Σ_{i≠j} ηᵢ²ηⱼ² ]
```

> **注意交叉项系数是 `γ/2` 不是 `γ`**：
> `Σ_{i≠j}ηᵢ²ηⱼ²` 对 `ηᵢ` 求导得 `4ηᵢΣ_{j≠i}ηⱼ²`，要凑出 `2γ` 必须乘 `γ/2`。
> 等价写法（更常用）：`f = mu·[Σᵢ(ηᵢ⁴/4 − ηᵢ²/2) + γ·Σ_{i<j}ηᵢ²ηⱼ²]`，因为 `Σ_{i≠j} = 2Σ_{i<j}`。

`mu` 来自 `[barrier_mu]`（含熔化开关），`gamma_asymm` 来自 `[consts]`，两者都可用
`DerivativeParsedMaterial` 的 `material_property_names` 引用——**已实测构造成功**。

⚠️ **该式子必须做数值验证**（见 §三.4）：实现后用有限差分核对
`∂f_grain/∂ηᵢ` 是否等于 MOOSE 残差里的那一项。**推导错了不会报错，只会给出错误的自由能。**

### 2.5 梯度能项系数

```cpp
// modules/phase_field/src/kernels/ACInterface.C:96,102
return _kappa[_qp] * nablaLPsi();   // nablaLPsi 含 _L[_qp] * _grad_test
return _grad_u[_qp] * kappaNablaLPsi();
```

残差形如 `L·κ·∇η·∇φ`（`L` 在 `ACBulk`/`ACInterface` 里都乘进去了），
对应 `F_grad = Σᵢ ∫ (kappa_op/2)·|∇ηᵢ|² dV`。**这一项在 Python 里用 Exodus 网格做有限差分算**，
并通过"纯晶粒长大时总自由能非增"来交叉验证系数是否取对。

### 2.6 坑：t=0 那一行后处理器**全是 0**

实测 `/tmp/t4.i` 输出：

```
| time | Fconst | umax | umin | vol |
| 0.00 | 0.0    | 0.0  | 0.0  | 0.0 |   ← 材料尚未求值
| 1.00 | 7.0    | 0.7  | 0.7  | 2.0 |   ← 正确
```

⇒ **诊断必须跳过 `time = 0` 行**，否则所有量都会被读成 0。

---

## 三、实施步骤

### 步骤 1：固化生成器与配置（无风险，先做）

按已确认的方案：**复制进仓库，两版并存**。

- 新建 `pipeline/frozen/`，放入：
  - `gen_aniso_nonad.py` ← 复制自 `/root/work/bak/gen_aniso.py`（**生产用**）
  - `splice_aniso_nonad.py` ← 复制自 `/root/work/bak/splice_aniso.py`
  - `README.md`：说明两版差异、哪个是生产版、为什么并存
- **不移动、不删除、不修改** `pipeline/gen_aniso.py`（AD 版）与 `/root/work/bak/` 原件
- 记录每个文件的 **SHA256**

**理由**：`gen_aniso_nonad.py` 与 `gen_aniso.py` 同名不同内容，产出物都叫
`stage1_meltpool_d.i`，**目前没有任何哈希能区分**。这是最危险的隐性漂移源——
本项目已经因为"选错生成器"误诊过一次（C1 验证第一版把 AD 版问题归因到 `k=0.63`）。

### 步骤 2：改源文件 `stage1_meltpool_c.i`

**2a. 生产值同步**

| 项 | 原 | 新 | 依据 |
|---|---|---|---|
| `nl_abs_tol` | 1e-7 | **1e-9** | 两份专家评审一致；已实测非 AD+MUMPS 能收敛到 4.01e-10 |
| 起始 `dt` | 1e-6 | **1e-7** | 实测：给 1e-6/4e-6 会让首步反复失败（全尺寸白烧 47 分钟） |
| `dtmax` | 2e-6 | **不动** | 源码 `:368` 注释「界面弛豫时间 ~4.7e-6 s」是这个约束的来源；两份评审都明确**不要放宽到 4e-6** |
| `l_max_its` | 30 | **按实测日志定** | 【审2】要求；先跑一次看实际分布再定 |
| `scheme` | bdf2 | 不动 | — |
| PETSc | ASM/ilu | 不动 | 全尺寸 ASM 比 MUMPS 快 4× 、内存省一半 |

**必须同时修正的过期注释**：
`pipeline/run_nonad_prod.sh` 文件头仍在说「非 AD 版有 7.3e-07 牛顿残差地板 ⇒ 把
`nl_abs_tol` 放宽到 `1e-6`」。**这个归因已被实测推翻**（地板来自 ASM/ILU 预条件子，
不是 Jacobian 不完备——非 AD + MUMPS 二次收敛到 4.01e-10）。
不改这条注释，将来一定会有人照着它把容差放宽。

**2b. 新增诊断材料**（只增不改，不动任何现有物理）

```moose
[f_grain]                       # 晶粒体自由能，供积分诊断用
  type = DerivativeParsedMaterial
  property_name = f_grain
  coupled_variables = 'gr0 gr1 ... gr7'
  material_property_names = 'mu gamma_asymm'
  expression = 'mu*( (gr0^4/4-gr0^2/2) + ... + gamma_asymm*(gr0^2*gr1^2 + ...) )'
  derivative_order = 1
[]
```

**2c. 新增后处理器**

| 后处理器 | 类型 | 参数 | 作用 |
|---|---|---|---|
| `F_loc` | `ElementIntegralMaterialProperty` | `mat_prop = f_loc` | 溶质+分配自由能 |
| `F_grain` | `ElementIntegralMaterialProperty` | `mat_prop = f_grain` | 晶粒体自由能 |
| `gr{i}_max` ×8 | `NodalExtremeValue` | `variable = gr{i}`, `value_type = max` | 序参量越界检查（应 ≤ 1） |
| `n_elem` | `NumElements` | — | 网格规模校验（防 CLI 覆盖失效） |
| `n_nonlin` | `NumNonlinearIterations` | — | 牛顿迭代数 |
| `n_lin` | `NumLinearIterations` | — | 线性迭代数 |

**全部显式设 `execute_on = timestep_end`**（避开 §2.6 的 t=0 全零行）。

### 步骤 3：诊断汇总器 `pipeline/gate0_report.py`

**输入**：一个运行目录（`run.log`、`*_out.csv`、`*.e`）
**输出**：`diagnostics.json`（机器可读）+ 人读表格

**复用现有代码**（不重写）：

| 复用对象 | 位置 | 用途 |
|---|---|---|
| Exodus 读取器 | `cmp_solution.py:21-52` | 时间序列与场 |
| **多单元块遍历** | `extract.py:152-195` | ⚠️ **必须遍历所有块**——熔池是独立 block（占 15.9% 单元），写死 `eb1` 会**静默漏掉整个凝固区** |
| 迭代数/墙钟正则 | `cost_breakdown.sh:139-151` | 日志兜底（后处理器已覆盖迭代数，日志只用于墙钟） |
| RSS 求和看门狗 | `bench_mpi_mem.sh:45-53` | 多进程峰值内存 |

**函数分解**：

```
parse_csv(dir)        -> 时间序列 + 标量后处理器（跳过 time=0）
parse_log(dir)        -> 墙钟、雅可比装配耗时、DIVERGED_* 分类计数
read_exodus(dir)      -> 场（遍历所有单元块）
conservation(dir)     -> total_solute 相对漂移
free_energy_grad(dir) -> Σᵢ∫(kappa_op/2)|∇ηᵢ|² dV（有限差分）
free_energy_check()   -> 交叉验证：F 在纯晶粒长大下应非增
write_report()        -> diagnostics.json
```

**已知坑（必须保留处理）**：
- 剥 ANSI 色码 `sed 's/\x1b\[[0-9;]*m//g'`（`time_breakdown.sh:12` 有记录）
- conda 环境：`moose` 有 netCDF4 无 torch，`ml` 有 torch 无 netCDF4 ⇒ **本脚本在 `moose` 下跑**
- 晶粒 ID 先 `np.rint` 再 `unique`（`analyze_stage1.py:116-118`）
- `unique_grains` 是整数**标号**不是物理量，**不可混入统计**

### 步骤 4：验证新材料的正确性（**不可跳过**）

`f_grain` 的推导是我从 MOOSE 源码反推的，**推导错误不会报错，只会静默给出错误的自由能**。

验证方法：1D 小算例，用有限差分核对
`[f_grain(ηᵢ+ε) − f_grain(ηᵢ−ε)] / 2ε  ==?  mu·(ηᵢ³ − ηᵢ + 2γ·ηᵢ·Σ_{j≠i}ηⱼ²)`

即**把材料属性 `f_grain` 的数值导数与 `ACGrGrPoly` 残差里的 `computeDFDOP` 对齐**。
不通过就不许用它做诊断。

### 步骤 5：两档运行与回归比对

**档 A — 小域回归**（秒级，用 CLI 覆盖）

```bash
phase_field-opt -i <生成的生产 .i> \
  Mesh/nx=86 Mesh/ny=30 \
  Executioner/end_time=2e-5 \
  Outputs/file_base=<tag>
```

**档 B — 全尺寸短跑**（**10 步，约 30 分钟**，已确认预算）

```bash
mpiexec -n 8 phase_field-opt -i <生产 .i> Executioner/end_time=<10步对应时间>
```

用已实测的 ASM 全尺寸 499 s / 3 步估算。

**回归判据**：同一输入跑两次，`diagnostics.json` 的
**确定性字段**（守恒误差、自由能、迭代数、序参量最大值）应逐位相同。
墙钟/内存显然不会相同，单独归类。

---

## 四、验收判据

| # | 判据 | 通过条件 |
|---|---|---|
| 1 | 生成器固化 | `frozen/` 存在，SHA256 记录在案，`gen_aniso_nonad.py` 产出与 `/root/work/bak/` 逐位一致 |
| 2 | 生产值同步 | 源文件 `nl_abs_tol = 1e-9`、`dt = 1e-7`；`run_nonad_prod.sh` 过期注释已修 |
| 3 | `f_grain` 正确性 | 有限差分核对通过（相对误差 < 1e-6） |
| 4 | 诊断齐全 | `diagnostics.json` 含守恒误差、F_loc、F_grain、F_grad、8 个 `gr_max`、牛顿/线性迭代数、墙钟、峰值内存 |
| 5 | **可复现** | 档 A 跑两次，确定性字段逐位相同 |
| 6 | **守恒** | `total_solute` 相对漂移在机器精度量级 |
| 7 | 全尺寸代价已测 | 峰值内存、每步墙钟、`1e-9` 相对 `1e-6` 的牛顿迭代数增量 |

---

## 五、风险与不确定

| # | 风险 | 处置 |
|---|---|---|
| R1 | `f_grain` 交叉项系数 `γ/2` 推错 | 步骤 4 强制有限差分验证，不过不用 |
| R2 | `f_grain` 的绝对零点未知（MOOSE 残差只约束**梯度**，差一个常数） | **只用于比较与耗散检查（非增），不用于绝对数值**；在文档中明确标注 |
| R3 | 梯度能系数（`κ/2` vs `κ`）未直接验证 | 用"纯晶粒长大 F 非增"交叉验证；若系数错 2 倍，`F_grad` 会系统性偏 |
| R4 | `l_max_its` 定得太低导致 `DIVERGED_ITS` | 【审2】要求按实测日志定——**先跑档 A 看分布，再定值** |
| R5 | `1e-9` 全尺寸代价未知 | 正是步骤 5 档 B 要测的；若代价过高，需要重新评估生产配置（但**不因此放宽到 1e-6**） |
| R6 | CLI 覆盖对某些参数不生效 | 已实测 `Mesh/nx`、`Executioner/nl_rel_tol`、`Outputs/csv` 生效；**其余参数用前逐个验证**，`n_elem` 后处理器就是为此加的自检 |
| R7 | 小域与全尺寸的物理不一致（网格 1µm vs 粗化后 5µm） | 档 A **只用于回归与 API 验证，不用于物理结论** |

---

## 六、明确不在本 Gate 范围内

以下属于 Gate 1/2/3，**本 Gate 不做**，避免范围蔓延：

- 平面凝固前沿的 `W/(D/V)` 扫描与 `k_eff` 判据（Gate 1）
- GP / 抗截留的对比（Gate 1）
- 溶质拖曳的变分耦合（Gate 1）
- 参数分层扫描（Gate 2）
- NN 数据生成（Gate 3）
- C4（溶质截留）、C8（溶质→拓扑反馈）的**物理修复**

**Gate 0 的产出是一套"可信的尺子"，不是物理结论。**

---

## 七、实施顺序与工作量

| 步骤 | 内容 | 预估 |
|---|---|---|
| 1 | 固化生成器 + SHA256 | 20 分钟 |
| 2 | 改源文件（生产值 + 诊断） | 40 分钟 |
| 3 | `gate0_report.py` | 2–3 小时 |
| 4 | `f_grain` 有限差分验证 | 1 小时 |
| 5 | 档 A 回归 + 档 B 全尺寸 | 1 小时（含 30 分钟机时） |

**合计 1–2 天**，与专家给的工作量估计一致。
