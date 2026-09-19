# `validated/` —— 验证分支与最小算例

本目录**不是生产**。生产链是 `pipeline/stage1_meltpool_c.i` → `run_nonad_prod.sh`。

本目录放的是审计材料包（`docs/guidence_material/audit_material_pack/`）要求的
**最小物理验证算例**、为修复 P0 而新建的**分支输入**，以及把二者接起来的**测试套件**。

> **当前状态与全部实测结果见 [`VALIDATION_STATUS.md`](VALIDATION_STATUS.md)。**
> 这份 README 只讲"有什么工具、怎么用"。

## 规矩（来自 `01_IMPLEMENTATION_PLAN.md`）

1. **不在生产文件上做物理改动**。物理修复一律写成本目录下的分支 `.i`，
   验证通过后由用户决定是否合入 `stage1_meltpool_c.i`。
2. **一次只改一个物理/数值因素**，并保存输入 diff、日志、CSV、诊断 JSON。
3. **不跑全尺寸生产跑**。只跑 1D、局部 2D、smoke test。
4. 文献缺失的参数必须标成 `calibration`，不得伪装成材料常数。

## 一条命令跑完

```bash
bash run_all_1d.sh            # T1/T2/T3/T4/T6/T12，约 10 分钟
bash run_all_1d.sh --full     # 再加 T5/T11，约 1 小时
```

结果写到 `$ROOT/SUMMARY.txt`（默认 `/mnt/f/speedup_work/validate_all/`）。

## 工具总表

### 生成器（生成 `.i`，不跑）

| 文件 | 用途 |
|---|---|
| `make_case.sh` | 从生产源输入生成一个 2D 验证算例（尺寸用环境变量覆盖，生成文件与生产**逐字相同**） |
| `make_1d_static.py` | **1D 静止平界面**算例生成器。T1/T2/T4/T5 的载体。<br>`--dl/--ds` 给出则启用**分层迁移率**（Phase 1.3） |
| `make_1d_gb.py` | **1D 固固晶界**算例（冻结 η0/η1）。T11/T12 的载体 |
| `make_1d_decay.py` | **1D 小扰动衰减**算例。T12 用——量的是 D 的**动力学后果**，不是材料属性取值 |
| `make_t9.py` | **三晶粒三叉晶界**算例。T9 用。⚠ 种子三角形必须是**锐角**（见文件头）。<br>**新增 `--hex-mesh`**：换成六边形域（T9 的判据只在 3 重对称的域上才有意义） |
| `make_hex_mesh.py` | **手写 GMSH 正六边形网格**（MOOSE 的 `GeneratedMesh` 造不出六边形）。<br>供 `make_t9.py --hex-mesh` 用。3 个菱形 × N×N 四边形，外边界 6 条各一个 physical group |
| `make_variant.py` | 从生产源输入生成**分支输入**：`--t-cap`（温度截断）/ `--d-layer`（迁移率分层）。同时写出 `.diff` |
| `make_jacfix.py` | 把 D 版输入里的 `ACGrGrPoly` 换成自建核 `ACGrGrPolyJ`（雅可比补全），并补上 `coupled_variables`。**恰好 8 处、无残留**才放行 |

> ⚠ **`make_variant.py` 的默认源已改成 `stage1_meltpool_c.premerge.i`**
> （见 `run_t10.sh` / `run_phase13_2d.sh` / `run_all_1d.sh` 的注释）：
> 1.2 / 1.3 已按用户决定**合入生产**，所以 `../stage1_meltpool_c.i` 里
> 已经有 `min(…, 3200)`、也再没有那个常数 `M` 的 `[ch_params]` 块，
> 再对它打这两个补丁会（**有意的**）报错退出。
> `premerge.i` 是用 `phase1_merge.diff` 反向打补丁重建的合入前副本，
> **SHA256 逐位等于**合入前的值（`1639d677…`）。

### 运行器（跑算例）

| 文件 | 用途 |
|---|---|
| `jacobian_test.sh` | T1：`-snes_test_jacobian` 对照 + `Missing coupled variables` 计数 |
| `compare_variants.sh` | 小网格上跑多个变体并对比后处理量（各自独立目录，避免 CSV 互相覆盖） |
| `run_t5.sh` | T5：`kappa_c` 极限，**每档两种 dx** |
| `run_t7.sh` | T7：平面前沿的 dx 收敛（速度与 k_eff） |
| `run_t8.sh` | T8：ε 收敛（圆晶粒）。自动按 `wGB` 重标定 κ/μ/L/dx/dt |
| `run_t9.sh` | T9：三叉晶界（**待建**；生成器与分析器已就绪） |
| `run_t9_hex.sh` | **T9（六边形周期胞版）**：一键复现 —— 生成六边形网格 → 生成算例 → 跑 → 量角度。**判据通过（0.78°）** |
| `run_t11.sh` | T11：`Γ_GB` 对 dx / w_gb 的收敛性（`LDOM` 可放大域长） |
| `run_t14.sh` | T14/Phase 2.3：AMR 的三组对照（只加密 / 加密+粗化 / 关状态材料重投影） |
| `run_t14_moving.sh` | T14b：**把 AMR 测试挪到移动前沿算例**——1D 静态界面本质上测不到粗化（见下） |
| `run_t14_diag.sh` | **【2026-09-19 新增】T14 判决性诊断**：同一算例「原样 + AMR」vs「**只删掉 2 个硬编码 `elementid` 后处理** + AMR」vs「删后不开 AMR」。**结论：段错误源于 `elementid` 后处理，不是 SplitCH** —— 旧结论被推翻，AMR 路重新打开 |
| `run_t14_2d.sh` | **【2026-09-19 新增】2D 生产配置的 AMR 验证**：`uniform` / `refine` / `both` 三档，查「崩不崩 / AMR 真没真生效（**看 `n_elem`**）/ 守恒 / 与 uniform 的差异」。**实测：不崩、单元数 1026→3015、守恒漂移 4e-14** |
| `run_t1_criterion.sh` | **【2026-09-19 新增】T1 正对照**：同一个二进制、只把核的 `jac_mode` 从 `full` 换成 `off`（删掉整个 η–η 非对角块），先验证**残差逐位不变**再做 FD 对照。⚠ 两档**必须放同一目录**共用 `.jitcache`，否则每次重付 JIT 编译代价 |
| `run_t1_step2.sh` | **【2026-09-19 新增】** T1 第 2 步补跑（复用已跑好的算例与热缓存）。⚠ 必须加 **`-snes_max_it 1`**：`-snes_convergence_test skip` 会让 SNES 永不收敛，在**每次非线性迭代**都重做 FD 比对 |
| `cmp_ident.py` | **【2026-09-19 新增】** 残差同一性比对（**数值**而非逐字节）。判据是「差异 ≤ 求解器容差量级」，不是「逐字节相同」——雅可比一变牛顿路径就变，末几位必然分叉 |
| `run_omega_calib.sh` | **【2026-09-19 新增】Ω₀ 标定**：wGB × {noseg, 旧 Ω₀, 新 Ω₀} 三路对照，把 Γ 换算成物理单位（at/nm²）与 Tan 2016 锚点对比。⚠ **必须带 `F_PART=h_solid`**，否则 `noseg` 基座就有 222 at/nm² 把信号盖住 |
| `run_kc0_cost.sh` | **【2026-09-19 新增】** `kappa_c = 0` / 去掉 `w` 的代价核算（三路：`base`/`kc0`/`do3`，隔离「κ_c 本身」与「三阶导代价」） |
| `make_phase3_prod.py` | **【2026-09-19 新增】Phase 3 合入生成器**：把「`h_solid` 驱动的分配项 + 独立偏析项」打进生产输入。**三处必须一起改**（`f_loc` 表达式、常量表、**`M` 的分母 `f_cc`**）。指示函数**显式内联**绕开链式法则病理。⚠ 改完**必须 `--dry-run` 看 diff** |
| `run_t10.sh` | T10：温度截断，在 **dx ≤ 2 µm 的局部算例**上比较 |
| `run_phase13_2d.sh` | Phase 1.3 的 **2D 动力学验证**：分层迁移率放进真实生产模型 |
| `run_all_1d.sh` | **一条命令跑完上面这些 1D 判据并打 PASS/FAIL** |
| `run_jacfix_test.sh` | **T1b**：`ACGrGrPolyJ` 的雅可比**前后 FD 对照**（同一二进制、同一算例，只差核类型）。预条件子覆盖为 LU/MUMPS |
| `run_t8_dx.sh` | **T8b**：**固定 `wGB` 只扫 `dx`** —— 回答"生产网格 `dx = 1 µm` 够不够"（T8 各档固定 `dx = wGB/16`，回答的是另一个问题） |
| `bisect_materials.sh` | **T1 诊断**：分别只去掉 `κ` / `γ` / `L` 的 η 依赖，二分出 FD 误差来自哪一个材料链 |
| `bisect_L.sh` | **T1 诊断（第二层）**：`L = L2a × L2b`，分别只关一半 |
| `inline_align4.sh` | **T1 诊断（第三层）**：把 `align4` 内联进 `L2b` 降一层嵌套。⚠ **会卡死**（求导树爆炸），留着是为了记录这个否定结果 |
| `analyze_jac_view.py` | 解析 `-snes_test_jacobian_view` 的输出，把差异按「属于哪个变量」分块统计 |

### 分析器（读结果，出判据）

| 文件 | 用途 |
|---|---|
| `check_D_layering.py` | T6：从 `.i` 的表达式原文数值求导，核对 `D = M·∂²f/∂c²`；**并扫连续剖面**（三态表看不出实现缺陷，剖面能） |
| `analyze_decay.py` | T12：拟合扰动衰减 → 有效扩散系数 → 与目标值比 |
| `analyze_t9.py` | T9：从 Exodus 量三叉角（环绕扫描找晶界方向）。`--times` 看收敛过程 |
| `exodus_lite.py` | 极简 Exodus 读取器（环境里没 meshio，用 netCDF4 自己读） |
| `robust_csv.py` | **读 `/mnt/f` 上的 CSV 必须用它**——9p 缓存会静默返回过期数据（见下） |

### 一次性诊断脚本（都是为查清某个具体问题写的，都留了结论）

| 文件 | 查了什么 |
|---|---|
| `repro_liquid_flag.py` | 温度截断到底会不会改变熔池几何（最小复现） |
| `why_cap_changes_liquid.py` | 上一条的**机制**：逐单元双线性插值，五个 cap 档位与 MOOSE 实测逐位对上 |
| `cap_safety_vs_mesh.py` | cap 的几何中性**从哪个 dx 开始成立**（答案：≤ 2 µm） |
| `repro_coupled_variables.py` | `coupled_variables` 到底改不改变 `SplitCHParsed` 的雅可比（答案：差 11000 倍） |

## 为什么用命令行覆盖尺寸，而不是另写缩小版 `.i`

本项目踩过的坑：网格是**生成器链**，`Mesh/nx=86` 静默无效（必须 `Mesh/gen/nx`），
改了等于没改、整个对照实验作废。

更重要的理由：**验证算例与生产必须解同一个方程**。
如果另写一份缩小版 `.i`，两份文件就会各自漂移，验证的就不是生产模型了。
所以 2D 算例只在**运行时刻**覆盖 `nx/ny/xmin/xmax/end_time`，磁盘上的文件是生产那一份。

`make_case.sh` 与 `run_t10.sh` 都会打出**实际生效**的网格与 dx，防止"以为改了其实没改"。

## ⚠ 最重要的一条：`/mnt/f` 上的读会**静默返回过期数据**

`/mnt/f` 是 Windows 盘经 **9p 协议**挂载的。对同一个正在被追加的 CSV
连续读三次，实测得到三个不同结果：

```
第 1 次: 1757 行, 末 t=0.0351
第 2 次: 2680 行, 末 t=0.0535
第 3 次: 6185 行, 末 t=0.1236   ← 与 shell 的 tail/wc 一致
```

**不报错，只是悄悄给你一个旧版本。**

本项目的**三次「时间倒退」怪象全部源于此**，并导致过两次误判
（一次以为"结果发散了"，一次以为"平衡依赖于 M"）。

**做法**：用 [`robust_csv.py`](robust_csv.py) 的 `read_rows()`，
它会反复读到与 `wc -l` 一致为止，并取行数最多的那一次。
对已跑完的文件用 `read_rows_strict()`（读两次，不一致就抛错）。

```python
import sys; sys.path.insert(0, "pipeline/validated")
from robust_csv import read_rows
rows = read_rows("/mnt/f/.../out.csv")     # 不要用 list(csv.DictReader(open(...)))
```

## 使用这些工具时踩过的坑（都写进对应文件的注释了）

| 坑 | 症状 | 真相 |
|---|---|---|
| **旧式 `[Adaptivity]` 是空操作** | 用 MOOSE 教程里那种嵌在 `[Executioner]` 里的写法，"能跑不崩" | **它被静默忽略，一格都没加密**。判据：**看单元数有没有变**（实测激进参数下仍是 160 = 基础值） |
| **`/mnt/f` 的读会过期** | 同一文件连续读得到不同结果；"时间倒退" | **9p 缓存**。用 `robust_csv.read_rows()`（见上） |
| `set -u` + `conda activate` | 脚本静默什么都不做 | conda 的 activate 脚本引用未定义的 `$CONDA_BUILD`，`set -u` 让它直接退出 |
| `for s in $CASES` 多行变量 | 每个 case 被拆成几块 | 按**空白分词**而非按行；要用数组 |
| `MaterialRealAux` + 节点变量 | 报 "Nodal AuxKernel attempted to reference material property" | 必须用 `order = CONSTANT, family = MONOMIAL` |
| 单元常量采样 | "应该正好等于某值"的判据带 1% 假偏差 | 取的是**第一个求积点**，不是质心。用极值或关系式做判据 |
| `LineValueSampler` 的 `execute_on` | 每个时间步写一个 CSV（实测 161 个） | 用 `'initial final'` |
| `[Variables] initial_condition` + `[ICs] FunctionIC` | 报重复定义 | 二者只能有一个 |
| `str.format()` 处理带 `{}` 的注释 | `KeyError: 'i<j'` | 注释里有 `Σ_{i<j}`；用 `.replace()` 代替 |
| 分析脚本里硬编码常数 | 扫参数时所有档套用同一个值 | `kappa_c` 一度硬编码 1e-14；必须从输入读 |
| 比时间序列时位置错位 | 误判"结果发散了" | 只比了前两项/末两项；必须**对齐位置**逐项比 |
