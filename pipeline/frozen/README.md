# frozen/ —— 冻结的生成器

> 建立：2026-09-18（Gate 0 步骤 1）
> 目的：**消除"同名不同内容"的生成器漂移**

---

## 一、为什么要有这个目录

仓库里有两个功能相同、文件名相同、**内容不同**的生成器，产出物**都叫
`stage1_meltpool_d.i`**。在本次固化之前，**没有任何哈希能区分产物是哪个版本生成的**。

这不是假想的风险——本项目已经因为"选错生成器"误诊过一次（C1 验证第一版把 AD 版的
收敛问题错误归因到 `k = 0.63`）。

|candidate|位置|性质|
|---|---|---|
| **非 AD 版** | `/root/work/bak/gen_aniso.py`（生产用，WSL，**无版本管理**） | 生产 |
| AD 版 | `pipeline/gen_aniso.py` | 实验/对照 |

⇒ 生产版本只存在于 WSL 的一个 `bak/` 目录里，**随时可能因误删/误改而永久丢失**。
本目录把生产版复制进仓库，两版并存。

---

## 二、冻结清单与 SHA256

| 文件 | SHA256 | 行数 | 来源 |
|---|---|---|---|
| `gen_aniso_nonad.py` | `07629ed6272b39ede93edfa47cdf4acd47adf157636b8c51b86757d9f725f875` | 556 | `cp -p /root/work/bak/gen_aniso.py` |
| `splice_aniso_nonad.py` | `1009d666f6e9101d7ad78692cb9bba642237c6d78f60469a837c117f177e14b7` | 236 | `cp -p /root/work/bak/splice_aniso.py` |

**对照（未改动，仅登记）**：

| 文件 | SHA256 | 行数 |
|---|---|---|
| `../gen_aniso.py`（AD） | `78c7705b5b31a2ada5b8dea2025f97c227c4b8472a407d56d0a042c807b3043f` | 608 |
| `../splice_aniso.py`（AD） | `9d1167aa2208bfdc80bafb323a77600dc9c2622033c80057547d915a06cc8311` | 252 |

四个哈希**两两不同**——确认确实是四份不同的文件。

**复制保真性已验证**：`cmp` 逐位比对通过，复制后 SHA256 与源完全一致。
`/root/work/bak/` 原件与 `pipeline/` 下的 AD 版**均未移动、未修改**。

---

## 三、两版差异（实测 `diff`，不是凭印象）

### 3.1 `gen_aniso` 的差异（250 行）

**(a) 取向集的默认值不同 —— 这是最危险的差异**

| 版本 | 默认取向分布 |
|---|---|
| 非 AD | 固定确定性铺开，`[0,90)` 内等间距 + 抖动 |
| AD | `--texture fiber`（默认！），`<100>` 纤维织构，`hwhm=20°` |

实测（`op_num = 8`）：

```
非 AD                : [0.0, 14.85, 29.7, 34.65, 49.5, 64.35, 69.3, 84.15]
AD --texture random  : [0.0, 14.85, 29.7, 34.65, 49.5, 64.35, 69.3, 84.15]   ← 逐位相同
AD --texture fiber   : [2.67, 8.30, 15.07, 26.06, 63.94, 74.93, 81.70, 87.33] ← 完全不同
```

> **⇒ 非 AD 版 ≡ AD 版加 `--texture random`，逐位相同。**
> 而 AD 版的**默认**是 fiber，与生产版**不是同一套物理**。
> 谁若直接用 `python3 gen_aniso.py`（不带参数）去复现生产结果，取向集就错了。

**(b) 实现机制不同（数学等价）**

| | 非 AD | AD |
|---|---|---|
| 材料类型 | `DerivativeParsedMaterial` | `ADDerivativeParsedMaterial` |
| `gdir` | 独立材料 `gdir_p`/`gdir_q`，经 `material_property_names` 分层 | 内联进 `align4` 表达式 |
| `L` | 三层 `L2a × L2b`，各自显式 `coupled_variables` | 单层内联 |
| kernel | `TimeDerivative` / `ACGrGrPoly` / `ACInterface` | `ADTimeDerivative` / `ADGrainGrowth` / `ADACInterface` |
| 辅助变量 | `MaterialRealAux` | `ADMaterialRealAux` |

已逐行核对：两版的 `align4` 与 `L` **数学表达式等价**（非 AD 的属性名
`gdir_p`/`gdir_q` 正是 AD 内联进去的那两个表达式，`GDIR_EPS=1e-30`、`DELTA=1e-3`
等常量也完全相同）。⇒ **差异只在机制与取向集，不在 L 的数学形式。**

**(c) AD 版多一个 `--texture` / `--hwhm` CLI 参数**（非 AD 版没有）。

### 3.2 `splice_aniso` 的差异（16 行）

AD 版多一段：把 `[Materials]/barrier_mu` 从 `DerivativeParsedMaterial` 强制换成
`ADDerivativeParsedMaterial`（附有"不是就 `sys.exit`"的守卫），以及上面表格里的
三个 kernel / aux 类型替换。

**原因**（AD 版自己的注释）：MOOSE 禁止同一属性既有 AD 又有非 AD 声明，
而 `ADGrainGrowth` 用 `getADMaterialProperty("mu")` 取 `mu`。

**⇒ `splice_aniso_nonad.py` 从不修改 `barrier_mu`**，这一点与非 AD 生产的
熔化开关语义一致，不要混用。

---

## 四、生产流程（照 `../run_nonad_prod.sh` 实录）

```
conda activate ml
python3 gen_aniso_nonad.py --op-num 8 --out aniso_block.i     # 不能传 --texture
python3 splice_aniso_nonad.py                                  # 产出 stage1_meltpool_d.i
# —— 然后是一段 Python 正则补丁，产出真正的运行文件 N.i ——
phase_field-opt -i N.i
```

### ⚠️ 真正被运行的是 `N.i`，不是 `stage1_meltpool_d.i`

`run_nonad_prod.sh:46-62` 的补丁 heredoc 会**无条件覆盖**以下 6 项：

| 项 | `stage1_meltpool_c.i` 里 | 补丁后 `N.i` |
|---|---|---|
| `l_max_its` | 30 | **300** |
| `l_tol` | 1e-6 | 1e-6（不变） |
| **`nl_abs_tol`** | 1e-7 | **1e-6** ← 见下 |
| `end_time` | 6.5e-4 | 6.5e-4（不变） |
| `file_base` | `stage1c` | `N` |
| `time_step_interval` | 1 | **5** |

该补丁还断言核是修好的那一版（`type = TimeDerivative` 恰好 8 个、
`variable_L = true` 存在、`type = ADGrainGrowth` 一个都没有）。

> **⇒ 只改 `stage1_meltpool_c.i` 的 `nl_abs_tol` 是无效的**——补丁第 56 行会把它
> 重新覆盖回 `1e-6`。Gate 0 步骤 2 必须同时处理这一行（详见 `../GATE0_PLAN.md` 步骤 2）。

### 该补丁里已过期的归因（**必须修正**）

`run_nonad_prod.sh` 文件头（第 12-16 行）与第 55-56 行仍写着：

> 非 AD 版唯一的缺陷是 `ACGrGrPoly` 丢 `dL/deta_j` → 雅可比误差 1.2e-3
> → 牛顿残差地板 **7.3e-07**（只比 `nl_abs_tol=1e-7` 高 7 倍）
> => 把 `nl_abs_tol` 放到 `1e-6` 即可推进。

**这个归因已被实测推翻**：残差地板来自 **ASM/ILU 预条件子**，不是 Jacobian 不完备——
非 AD + MUMPS 能二次收敛到 **4.01e-10**。若不改这条，将来一定会有人照着它把容差放宽。

---

## 五、复现基线

### 5.1 改前基线（2026-09-18，历史，仅用于证明冻结版可用）

用本目录的两个文件、对当时（2026-09-18，未改前）的
`../stage1_meltpool_c.i` 跑完整流程，产物基线：

```
stage1_meltpool_d.i   sha256 = 6914a7cdbecd1dd38d5da4ed9507c710237ba6a53a62ae74b7b59b6f3455913d
                      28924 字节 / 24651 字符
```

`splice` 自报的分段：Functions 667 字符、AuxVariables 309、AuxKernels 1336、
替换 Materials 10127 字符。

`gen_aniso` 自检：`kappa_op = 1.799943021e-06` vs 基线 `1.8e-6`，相对偏差 `3.17e-05`。

### 5.2 **当前**基线（2026-09-19，Phase 1 修复已合入生产）

`../stage1_meltpool_c.i` 已按用户决定合入三项修复（见
`../validated/phase1_merge.diff`，**恰好 3 个 hunk**）：

| 修复 | 内容 |
|---|---|
| 1.1 | `[coupled_parsed]` 增加 `coupled_variables = 'gr0 … gr7'` |
| 1.2 | `[laser_T]` 外包 `min(…, 3200)`（温度截断） |
| 1.3 | `[ch_params]` 常数 `M` 拆成 `S_eta2` / `Q_eta4` / `h_gb` / `h_solid` / `solute_mobility`；`[coupled_res]` 同步加 `coupled_variables` |

两个生成器**一个字都没改**（`SHA256SUMS` 仍然有效）。

```
stage1_meltpool_c.i   76a421e2dd5224813ee1f868d475d40fe632c77708a66770e77f79c2f1dc9ab2   899 行
stage1_meltpool_d.i   c68e9e31731f76bffe8c1164ec28140bbbdf2782563aa6a761be00c600248372  1199 行
aniso_block.i         645938539da57f3c7efc84bf33afcb5f5f8bbcdbfc272a457b6d673df46599e9
N.i                   8b5f48d7631db97d92a1e00dbfee520dbc53c8171bffbea66755399cb3410a37  1207 行
                      （= d.i 再经 validated/make_jacfix.py，ACGrGrPoly → ACGrGrPolyJ）
```

复现命令见 `../run_nonad_prod.sh`（它自己会做哈希校验 + 生成 + 替换 + 断言）。

> ⚠ **改前/改后的 `d.i` 哈希必然不同**，这是预期的：C 源输入变了。
> 新旧基线都登记在这里，是为了让"哪次运行用了哪一版"可追溯
> —— 这正是本目录存在的理由（见开头第一节）。

> ⚠ **`splice_aniso_nonad.py` 本身仍然逐位未改**。
> `gen_aniso_nonad.py` **在 2026-09-19 有一次纯增量改动**（见 §5.3）——
> 已经登记进 `SHA256SUMS`，校验仍然全 OK。
> `ACGrGrPolyJ` 的替换是**生成之后**由 `make_jacfix.py` 做的，
> 故意不塞进 splice —— 因为 splice 的职责是「逐字复刻 GrainGrowthAction 建的核」，
> 让它知道本项目补了一个核，职责就混了。

---

### 5.3 【2026-09-19】Phase 3 合入 + 织构能力

**两件事，都是纯增量：**

| # | 改了什么 | 验证 |
|---|---|---|
| A | `stage1_meltpool_c.i` 合入 **Phase 3**（`../validated/make_phase3_prod.py`，**恰好 3 个 hunk**）：① `f_loc` 的分配项由 `Ση²` 改为 `h_solid` ② 加独立偏析项 `(Omega0/wgb)(c−c0)h_gb`，`Ω₀ = −5e-11` ③ `M` 的分母 `f_cc` 同步 | 1D 平衡：Γ 从 222 → **0.00** at/nm²，且新 Ω₀ 给出 Γ ≈ **2.5 at/nm²**（落 Tan 锚点 2.2~5.3 内）；2D 生产 smoke：不崩、守恒漂移 **0.00e+00**、`c_max−c_min` **0.60×** |
| B | `gen_aniso_nonad.py` 增 `--texture {random,fiber}` / `--hwhm`（移植 AD 版的 `_inv_norm_cdf`）。**默认仍是 `random`** | **默认档产出与原版逐字节相同**（`cmp` 验证，见 `SHA256SUMS` 注释） |

```
stage1_meltpool_c.i   34b63e4b30a8e76c4937fe62af6dc14aba14701877a620b06840f8135d0b3425   899 行
                      （改前：76a421e2dd5224813ee1f868d475d40fe632c77708a66770e77f79c2f1dc9ab2）
                      改前版本另存为 stage1_meltpool_c.prephase3.i
gen_aniso_nonad.py    8e53c9c9beee2c7bf1c82829d73f094d36165136f5be452b425efb0b131c640e
                      （改前：f61c725042bc27089bb10dbe2185394faae8b3504f8ff79ed39d551324f4e696）
```

**⚠ 顺带修了一个被合入暴露出来的守卫 bug**：`run_nonad_prod.sh` 原来用

```bash
grep -q "constant_expressions = '0.9 0.036 0.264'"      # ← 错
```

检查溶质参数。合入后那一行变成 `'0.9 0.036 0.264 -5e-11 4e-06'`，
**闭合引号没了 ⇒ 守卫会把合法输入判成"参数不对"而拒绝跑**。
已改成**前缀匹配** `^[[:space:]]*constant_expressions = '0\.9 0\.036 0\.264`。
（这是 `validated/smoke_prod_chain.sh` 抓出来的 —— 它专门复刻生产链并验证
「合入的改动在生成阶段有没有被吃掉」。）

---

### 5.4 【2026-09-19】AMR 合入生产（用户决定「改用 AMR」）

**背景**：`dx` 原来只有「不加密（ε 偏 +6.85% ❌）」或「均匀加密 4×（19h→76h/轨迹）」两个选项。
AMR 打开后（见 `../validated/VALIDATION_STATUS.md` §1.6）多了第三条路。

**目标由 Q10 的裁决直接给出**：判据 `d/dx ≥ 4`，`d = sqrt(2κ/μ0) = 2.00 µm`
⇒ 界面处需要 `dx = 0.5 µm`。基础网格 `dx = 1 µm` ⇒ **`max_h_level = 1` 就够**。

| 改了什么 | 内容 |
|---|---|
| 新增 | 节点型 AuxVariable `S_eta2_aux` = Ση² + 对应 `ParsedAux` |
| 新增 | `[Adaptivity]`：`GradientJumpIndicator(S_eta2_aux)` + `ErrorFractionMarker`，`max_h_level = 1`、`coarsen = 0.02`、`interval = 2` |

**实测**（`../validated/run_prod_amr.sh`，54×19 缩小网格）：

| 档 | 墙钟 | `n_elem` | 守恒漂移 | vs uniform |
|---|---|---|---|---|
| `uniform` | 187 s | 1026→1026 | 0.00e+00 | — |
| **`amr1`** | **177 s** | 1026→**1587** | **0.00e+00** | **0.453%** |
| `amr2` | 198 s | 1026→2934 | 0.00e+00 | 0.661% |

⇒ **level=1 反而比 uniform 快**（单元多 55%，但自适应步长走的步数更少）。

⚠ **`coarsen` 必须小到不破坏守恒**：实测 0.05/0.1 会让 `total_solute` 漂移 1e-7~2e-7
（超 T2 的 1e-8 判据），而 **0.02 保持精确 0**。原设 0.1 是拿守恒换了一个短算例里
看不到的收益。⚠ 长跑下 0.02 能不能压住单元数**仍未验证**。

```
stage1_meltpool_c.i   34b63e4b…  →  e703567a5879141db9c628d13adad739024d3d08f7579fbee68beb7f20774165
                      （改前另存 stage1_meltpool_c.preamr.i）
```
验证：`../validated/smoke_prod_chain.sh` 存活检查 **9 项全过** + `--check-input` **Syntax OK**。

### 5.5 【2026-09-19】溶质拖曳项合入（修热力学不一致）

**改了什么**：新增 8 个 `AllenCahn(f_loc)` 核（每个序参量一个），让 `f_loc` **也进 η 方程**。

**为什么必须补**：原来 `f_loc` 只进 c 方程 ⇒ `δF/δη` 与 `δF/δc` 来自**不同的自由能**
⇒ **模型不是变分的**（仓库自己的笔记就写着「源码自述：暂时没有溶质拖曳」）。
⚠ 这是**形式上的热力学不一致**，与量级无关。

**量级**：新增项比势垒小 **9~11 个数量级** ⇒ **可测量影响为零**。
**这个补丁的价值是「一致性」，不是「预测变了」**（与 T13 的结论一致）。

⚠ **不要**改用 `ACGrGrPoly` 或 `MatReaction` —— `AllenCahn` 的雅可比是**符号完备**的，
而 `ACGrGrPoly` 正是本项目**缺项**的那一个（所以才写了 `ACGrGrPolyJ`）。

```
stage1_meltpool_c.i   e703567a…  →  bffa17426f4f2b17a97652730b27a02e4345d3b31812462ea4ec5614c9f10817
                      （改前另存 stage1_meltpool_c.predrag.i）
```
验证：`../validated/run_drag_check.sh`（判据是**「看不出差别」才算通过** —— 因为它改的是一致性）。

**✅ 实测（54×19 网格，`end_time=2e-6`）**：

| 档 | rc | **NL 迭代** | `total_solute` 漂移 | 观测量差异 |
|---|---|---|---|---|
| `nodrag` | 0 | **21** | 1.41e-07 | — |
| `drag` | 0 | **21** | 1.41e-07 | 只在**第 11~13 位有效数字** |

**非线性迭代数完全相同 ⇒ 不拖慢收敛**；`liquid_frac` 逐位相同。
⇒ **量级估计成立**（新增项确实在求解器容差之下）。
⚠ 两档墙钟（83 s vs 8 s）**不可比**（单次运行 + 机器状态），不作为判据。

**三条合入（Phase 3 + AMR + 拖曳）全部走通生产链**：
`../validated/smoke_prod_chain.sh` 的「合入改动存活检查」**11 项全过** + `--check-input` **Syntax OK**。

---

### 5.6 【2026-09-20】**候选，尚未合入**：抗截留项（缺口 #3 的修复主体）

> ⚠ **这一节与上面 5.3~5.5 不同：它还没有合入 `stage1_meltpool_c.i`。**
> 生产源保持原样；候选输入另存为 `../stage1_meltpool_c.antitrap.i`。

**为什么需要它**：实测（`../validated/run_prod_1d.sh`）生产工作点上模型给出
`k_eff = 0.999015`，而物理值（Aziz，`a0 = 0.3 nm`）是 `0.6549`
⇒ **界面排出的溶质被低估 350 倍 ⇒ 微偏析被低估 350 倍**，
而微偏析正是本课题要预测的量（晶界偏析 `Γ_GB` 的来源）。

**根因**（两条都实测排除过别的可能）：

| | 机制 | 证据 |
|---|---|---|
| ① | `tests/front1d.i` 的 `kappa_c` **停在 `1.125e-11`**，生产早在 2026-09-18 就改成 `1e-14` | `run_kc_vs_keff.sh`：改对后 `k_eff` 0.877→0.795 |
| ② | **溶质是在整个弥散界面 `ξ` 上被排出的**（不是锐前沿） | `run_kc_fix_res.sh`：**`L_eff = δ_c + 1.5·ξ`**（4 档反解 1.29~1.36），生产外推 476 倍仍成立（3.17 µm vs 预测 3.00 µm） |

⚠ **不是网格问题**：`k_eff` 在 `δ_c/dx` 从 **0.5 到 16** 全部网格收敛到 <0.5%。

**改动**（`../validated/make_antitrap_prod.py`，**96 行 diff，纯增量**）：

| # | 内容 |
|---|---|
| A | 新增材料 `[at_susc]`：`F_at = 2·2e-6·(1−0.6303)·c·(1−h_gb) + 0*w` |
| B | 新增 8 个 `AntitrappingCurrent` 核（每个序参量一个），作用在 `w` 上 |

* **系数 `ALPHA = 2`** 是 1D 标定值（`run_antitrap2.sh`，4 档 `s`）：
  基线误差 17~46% → **≤6.6%**。⚠ 最优 `ALPHA` 随 `ξ/δ_c` 从 2.5 漂到 1.7
  ⇒ 它是**领头阶**修正，不是精确的与宽度无关的重整化，如实写。
* **`(1−h_gb)` 不是可选项**：本模型的 η 兼表固/液与晶粒身份，晶粒长大时 `η̇ ≠ 0`
  ⇒ 不抑制就会在**每条迁移中的晶界**上凭空产生溶质流。
* **`+ 0*w` 不是装饰**：MOOSE 的 `CoupledSusceptibilityTimeDerivative` 会索取
  `dF/dw`，我们的 `F` 不依赖 `w` ⇒ 正确值是 0，但**不能让框架静默填零**
  （本仓库 §3.1 那条教训）⇒ 显式写出来把属性做实。
* **不影响已有验证**：抗截留项是散度项，`φ̇ = 0` 时恒为 0 ⇒
  T4（平衡分配）/ T11（`Γ_GB`）/ `Ω₀` 标定 **一个都不受影响**。
  1D 实测守恒漂移 **0.00e+00**。

**验证状态**：

| 项 | 状态 |
|---|---|
| 1D 系数标定（4 档 `s`） | ✅ `run_antitrap2.sh` + `report_antitrap2.py` |
| 生产链存活（17 项） | ✅ `run_antitrap_check.sh` —— 8 个新核 + 原有 11 项合入都没被 splice 吃掉 |
| 打补丁输入的端到端跑通 | ✅ 86×30 网格上**跑完完整一步**（`Finished Executing [45 s]`、`n_lin=23`、`n_nonlin=8`、`grain_tracker=11`），`total_solute` **逐位不变** |
| `W` 取哪个定义 | ✅ **已澄清**：两个模型的 η 剖面**尾部衰减长相同**（都是 `λ_tail = 1.0 µm` ⇒ tanh 等效标度 2 µm），所以 `ALPHA=2 / W=2 µm` 可直接搬 |
| **`D_L` 子网格闭合**（修复第 3 条） | 🟡 **未改生产** —— 生产 `δ_c = 4.2 nm < dx = 1 µm`，必须把 `D_L` 提到 `≈2V·dx = 1.2e-6` |
| 2D 生产端到端 | ⬜ |

⚠ **第 3 条（`D_L`）与这一条是配套的，缺一不可**：抗截留项把 `L_eff` 从
`δ_c + 1.5ξ` 拉回 `δ_c`，但 `δ_c = 4.2 nm` 在 `dx = 1 µm` 上**根本不可解析**。
两者都做到后，精确关系给出 `c_max − c0 = 2A c0/k_c` —— **与 `D_L`、与网格都无关**。
副作用核算：熔池混合 `D_L·t/L² = 0.02 ≪ 1` ✓；
`D(η)` 的构造保证 `D_S`/`D_GB` **逐点精确不变** ⇒ 不影响 `s·δ·D_GB` ✓。

---

## 六、使用约定

1. **生产只用本目录的两个文件**，不要再从 `/root/work/bak/` 取。
2. 本目录文件**不得修改**。需要改动时，另存新文件并在此登记新哈希与理由。
3. 每次生产运行的产物 `stage1_meltpool_d.i` / `N.i` 的 SHA256 应记入该次运行的
   `diagnostics.json`（Gate 0 步骤 3），使"哪次运行用了哪个生成器"可追溯。
4. `--texture` 只在 AD 版存在。若要复现生产取向集而必须用 AD 版，
   **必须显式传 `--texture random`**。
