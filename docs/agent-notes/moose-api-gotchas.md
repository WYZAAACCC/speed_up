---
name: moose-api-gotchas
description: MOOSE 输入文件层面的十九个坑（解析器可用标识符、symbol_values、dtmax、mu 属性名抢用、Exodus 分块、材料导数接口、GBAnisotropy、跨块 IC 取小编号块、Checkpoint 默认按墙钟、AllenCahn 雅可比完备性、序号式导数重载、GrainGrowthAction 也建变量、mpicxx 缺失致 JIT 全废），都是实测踩出来的
metadata: 
  node_type: memory
  type: reference
  originSessionId: b6decc92-d1df-4297-b052-ad15b31c0547
  modified: 2026-09-18T16:02:58.136Z
---

在 MOOSE 写输入文件时实测踩到的坑，`--check-input` 查不出来、要到运行时才炸：

1. **`pi` 在解析型网格生成器里未定义**，但在 `ParsedFunction` 里可用。
   `ParsedSubdomainMeshGenerator` 用 `combinatorial_geometry = 'x < pi'` 会报
   `Syntax error: Unknown identifier`。**解法**：把常数折叠成数值再写进表达式。

2. **`ParsedFunction` 的 `symbol_values` 只能是「数字」或「对象名」，不能是表达式。**
   写成 `symbol_values = 'x+3.3e-4-0.6*t'` 会在运行时才报
   `Unable to convert '...' to type double`。另外它**按空白切分**，内部若有空格会被切成多段，
   报 `Number of symbol_names must match...`。**解法**：整条表达式内联进 `expression`。

3. **最大步长是 `[Executioner] dtmax`，不是 TimeStepper 的 `max_dt`**
   （后者报 unused parameter）。自适应步长不加限制会一路涨，超过界面弛豫时间
   `1/(L*mu)` 后线性求解 `DIVERGED_ITS`（残差先停滞再发散，不易定位）。

4. **`ACGrGrPoly` 的驱动力正比于材料属性 `mu`，属性名是硬编码的**
   （`ACGrGrBase` 里 `getMaterialProperty<Real>("mu")`），但
   `ACInterface` 的 `mob_name`（默认 `L`）和 `kappa_name`（默认 `kappa_op`）是可配的。
   所以可以用 `DerivativeParsedMaterial` 提供 `mu`、且**不使用 `GBEvolution`**
   （否则属性重复声明冲突），从而让 `mu` 依赖温度甚至变负。

5. **【读 Exodus 时最容易静默出错的一条】多 subdomain 网格的 Exodus 是分块存储的。**
   连接表是 `connect1`/`connect2`/…，**单元变量也分块**：`vals_elem_var{j}eb{k}`。
   只读 `connect1` 会**静默丢掉其它块**，不报任何错。
   实测：LPBF 算例里熔池是独立 subdomain（占 15.9% 单元），被整个漏掉。
   节点变量（`vals_nod_var{j}`）不分块，不受影响。
   **读 Exodus 的代码一律要遍历 `connect{k}` 直到不存在。**

6. **`unique_grains`（GrainTracker 经 FeatureFloodCountAux 输出）的取值约定**：
   `-1` = 不属于任何晶粒（液相/未分配），`>= 0` = 晶粒 ID。
   **晶粒 ID `0` 是合法的**，用 `> 0` 判固相会把它误判成液相。
   另外它是**浮点**存储，做 `np.unique` 计数前必须 `np.rint` 取整，否则同一 ID 会被重复计数。

7. **Cahn-Hilliard 的 4 阶项有显式稳定性限，会把自适应步长卡死。**
   `M*kappa_c*grad^4(c)` 项给出
   ```
   dt < dx^4 / (16 * M * kappa_c)
   ```
   实测：dx=1e-6、M=2.22e-14、kappa_c=1.125e-5 → dt < 2.5e-7。
   症状很有特征：**自适应步长每次试图增长就被砍回来**（IterationAdaptiveDT
   反复 cutback，日志里一堆 DIVERGED_ITS），时间推进极慢但每步的非线性
   残差其实收敛得很好（3 次迭代到 1e-8）—— 所以别被"收敛正常"迷惑。
   **诊断方法**：看 `Time Step N` 行里 dt 的增长-回退锯齿。
   **解法**：调 dt 上限的四个量之一，优先动 M（它同时决定物理扩散系数
   D = M*f''，往往本来就不该乱设）。

8. **`ParsedMaterial` / `ParsedAux` 都**不认** `x` / `y` / `t`**，只有 `ParsedFunction` 认。
   最小对照实验（每个表达式单独 `--check-input`）实测：
   ```
   DerivativeParsedMaterial: 'u*u' 认 | 'x' 不认 | 'y' 不认 | 't' 不认
   ParsedAux              : 'x' 不认 | 'y' 不认 | 't' 不认
   ```
   报错是 `Syntax error: Unknown identifier`，且**不指出是哪个标识符**，
   表达式一长就极难定位。
   **解法**：依赖 (x,y,t) 的量先用 `ParsedFunction` + `FunctionAux` 算成 AuxVariable，
   再作为 `coupled_variables` 耦合进材料。这在数学上无损 ——
   若该量不依赖序参量，它相对序参量的导数确实是 0，雅可比不缺项。

9. **`material_property_names` 支持含二阶的链式法则**（已实测通过）。
   可以把一个巨大的 parsed 表达式拆成多个小材料逐层相乘/复合
   （如 `align4` → `L2b` → `L`），每个材料的符号求导树都小得多。
   **注意**：本 MOOSE 版本**没有** `DerivativeProductMaterial`；
   用 `material_property_names` 就是官方支持的组合方式。
   实测代价参考：28 对求和的表达式、`derivative_order = 2`、9 个耦合变量，
   setup 从 2.0 s / 319 MB 涨到 110 s / 790 MB（LLVM JIT 编译，一次性）。

10. **`GBAnisotropy` / `GBAnisotropyBase` 会 `declareProperty<Real>("mu")`**
    （源码 `GBAnisotropyBase.C` 构造函数），且其 `mu` 是常数
    `_mu_qp = 6*sigma_init/wGB`。若算例的 `mu` 是温度相关的熔化开关
    （见第 4 条），两者**抢同一个属性名**，会互相覆盖。
    **解法**：不用 `GBAnisotropy`，把它内部的 Moelans Algorithm 1
    预先在 Python 里算好，再以 parsed 表达式给出，`mu` 完全留给自己。

11. **`ACInterface` 对材料导数的要求是硬性的**（源码实测）：
    `_dLdop`、`_d2Ldop2`（**二阶**）、`_dkappadop`，以及
    对所有耦合自变量的 `_dLdarg[i]`、`_dkappadarg[i]`、`_d2Ldargdop[i]`、`_d2Ldarg2[i][j]`。
    所以 `L` 必须 `derivative_order = 2`，`kappa_op` 至少 1。
    而 `ACGrGrPoly` **只用 `_mu[_qp]`，不取任何导数** ——
    所以 `mu` 可以做成零导数的简单材料。

12. **判断"取向在 GrainTracker 重映射中会不会串"要靠日志，不能靠推理。**
    `Grain Tracker Status` 块里每个序参量的
    `Grains active index k: n -> n` 计数，如果在**整个模拟期间不变**，
    就说明没有合并、没有重映射，op↔晶粒↔取向的映射全程稳定。
    另一个前提是**核列表里没有形核核**（没有 `Nucleation`）——
    没有形核就没有新晶粒，也就没有序参量被回收。
    实测柱状基体算例：101 步全程 `index 0..2: 2->2`、`index 3..7: 1->1`。

13. **跨块共享节点的 IC：取 block 编号小的那个值，与输入顺序无关。**
    最小算例实测（1D、8 单元、两块交界于 x=4）：
    ```
    情形1: block0=1.0, block1=0.0  →  共享节点 x=4 得 1.00（block 0 的值）
    情形2: block0=0.0, block1=1.0  →  共享节点 x=4 得 0.00（block 0 的值）
    把两个 IC 段在输入文件里对调顺序 → **结果完全不变**
    ```
    ⇒ **"后写的 IC 覆盖前面的"在这里不成立**。想让某个块的值赢，必须让它
    **block 编号更小**。实测代价：曾以为用 `ConstantIC(block=1)` 能覆盖
    `PolycrystalColoringIC(block=0)`，结果初值**逐点差 0.000e+00**，整个算例白跑。
    **凡是跨块 IC 都要先验初值（比对两版 t=0 场的逐点差），不能只看"跑完了"。**

14. **`Checkpoint` 的 `wall_time_interval` 默认被设成 3600 s**（基类默认是无穷大）。
    而 `Output.C` 的逻辑是：**只有显式设了 `time_step_interval` 才按步数存**，
    否则按墙钟。所以想按步存（长跑可续跑）**必须写 `time_step_interval`**。
    续跑：`--recover`，且**必须用与原始运行相同的 `file_base`**
    （Exodus 在恢复模式下要接着往同一文件追加，否则报 `Error opening ExodusII mesh file`）。

15. **CSV 输出的文件名取自「输入文件名」，不是 `Outputs/file_base`。**
    `Outputs/file_base` 只改 Exodus（`[Outputs][exo]` 的 file_base 更是只管 exo）。
    后果：**两个并发算例（同一个 .i）会写同一个 CSV、互相覆盖**——
    实测为此白跑一次网格收敛测试（两个进程混写，分析作废）。
    **⇒ 并发运行必须各自独立目录。** 与"重跑前先删 `*_out.csv`"是同一类问题。

16. **`AllenCahn` 的雅可比是「符号完备」的，`MatReaction` 不是。**（源码实测）
    `AllenCahn` 从 `DerivativeParsedMaterial` 取**符号导数**：
    `AllenCahn.C:52` 对角 `∂²F/∂η²`、`:65` 非对角 `∂²F/∂η∂η_j`（对**全部**耦合变量）、
    `ACBulk.h:105` 再加迁移率的乘积法则项 `_dLdop*φ*dFdop`。
    ⇒ 只要 F 写对，雅可比自动完备，**不需要手写任何导数**。
    而 `MatReaction` 只对**已声明**的参数求导（`MatReaction.C:96-109`），
    缺的导数经 `getMaterialPropertyDerivative` **静默返回 0**。
    这与 D 版不收敛（雅可比少项、残差还在）是同一类坑 ⇒ **优先 AllenCahn**。
    对照：`ACGrGrPoly` 是**手写**雅可比（`:64` 对角、`:75` 非对角），
    只对 `SumOPj` 求导，**不取 `mu`/`gamma` 的任何导数**（见第 11 条）。

17. **`getMaterialPropertyDerivative(base, unsigned int i)` 里的 `i` 是
    「本对象自身 `coupled_variables` 的序号」，不是材料自己的变量序号。**
    （`DerivativeMaterialInterface.h:101-113`，注释写明 "indices into the
    `_coupled_standard_moose_vars` vector"。）
    ⇒ 只要核把自己的耦合变量列全，`_dLdarg[i]` 就不会错配。
    但**列不全就会少项**：`validateNonlinearCoupling` 会告警
    `Missing coupled variables {...}`，**只是告警不是报错**，很容易漏看。
    实测：`ACInterface`/`ACGrGrPoly` 在 D 版里就因此丢了整条"经 L/κ 传递到
    其他序参量"的雅可比项。

18. **`validateNonlinearCoupling` 只检查「非线性系统」的变量，AuxVariable 不查。**
    （`validateCouplingHelper(..., validate_aux=false)`；且只 `mooseWarning`。）
    ⇒ `L` 依赖 AuxVariable `T` 时，核的 `coupled_variables` 里**不写 T 也不会报错**
    （因为 T 是辅助变量，本来也不进雅可比 —— 写不写都不影响正确性）。

19. **`GrainGrowthAction` 自己也会创建序参量变量**（`GrainGrowthAction.C:203`
    `addVariables()`），所以 `[Variables][PolycrystalVariables]` 与
    `[Modules][PhaseField][GrainGrowth]` **同时存在不报错**。
    两个推论：
    * 想只留变量、不要它建的核，可以**只保留 `[Variables][PolycrystalVariables]`
      而删掉整个 `[Modules]`**（它的变量来自 `PolycrystalVariablesAction`，
      注册在 `Variables/PolycrystalVariables`）。
    * 它还会额外建一个 `bnds` 辅助变量（`BndsCalcAux`），删掉 action 就没了 ——
      本项目生产输入里没用它。
    它建的核是**每个序参量三个**：`TimeDerivative` + `ACGrGrPoly(v=除自己外的全部)`
    + `ACInterface(variable_L, kappa_name, mob_name)`（`GrainGrowthAction.C:118-175`）。

20. **`mpicxx` 只存在于 conda 环境 `moose` 里**
    （`/root/miniconda3/envs/moose/bin/mpicxx`；`phase_field-opt` 也链接到该
    环境的 `libtimpi`/`libpetsc`/`libmpi`）。
    **不 `conda activate moose` 就跑 MOOSE，`ParsedMaterial` 的 LLVM JIT
    会全部失败并刷屏 `sh: 1: mpicxx: not found` + `JIT compile failed`，
    静默退回解释执行。** 数值结果相同（已对照），但慢。
    `run_nonad_prod.sh` 本来就激活了 `moose`；手工跑长算例时别忘。
    JIT 编译是**一次性**成本（数十秒量级），短算例反而更慢，长算例才划算。

相关：[[wsl-moose-environment-setup]]、[[grain-solute-acceleration-project]]、[[neural-operator-pipeline-state]]、[[gate0-frozen-reproducibility]]、[[landau-melting-fix]]
