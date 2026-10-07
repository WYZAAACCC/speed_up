# Ti64 LPBF 相场仿真 + 逐面神经算子

加速 **Ti-6Al-4V（Ti64）激光粉末床熔融（LPBF）** 中耦合的「晶粒结构演化 + 元素扩散」计算：
用 MOOSE 相场仿真生成训练数据，训练**神经算子**替代其中最昂贵的部分。

**硬约束**：算子要学的是**接近真实的物理**，不是复现一个粗网格模型。
因此模型的物理正确性本身就是指标，而不是「先跑通再说」。

---

## ⚠ 给审阅者的第一份文件：Window B 板条马氏体仿真

> **这份 README 的主体（下面 §仓库结构 起）写的是早期目标：MOOSE 相场 + 晶界溶质。**
> **当前主攻方向已经转为 `pipeline/ca_pf_framework/` 的 Window B ——
> 纯 Python/numpy 的「体相场 + 零厚度 Gibbs 面」β→α′ 板条马氏体仿真。**
> **它的主仿真文件清单与实现路径见下一节。专家请从那里开始。**

### Window B 是什么（一句话）

在**一个 6 µm 立方盒**里，β 母相 + 若干 α′ 变体，每个变体是一个**有符号距离场 `φ_k`**；
界面用**零厚度 Gibbs 面**建模（`γ(n)`、`M(n)`、面上溶质过剩 `Γ`、面上薄膜序参量 `ψ` 都是"面"自己的本构量），
**不是弥散界面相场**。降到 `M_s` 以下、无扩散 ⇒ 板条以**形核 + 界面推进**的方式长大，
自发按 Burgers 取向分组（同变体 → block/colony，同惯习面族 → packet）。

**纯 Python + numpy，无外部求解器依赖。** 典型算例 `N=96`（6 µm）、400 步 ≈ 25 min / 4 核。

---

### 一、主仿真文件清单（**按"跑一次仿真会加载什么"排列**）

| 层 | 文件 | 规模 | 作用 |
|---|---|---|---|
| **引擎核心** | **`pipeline/ca_pf_framework/windowB_surface.py`** | **4 494 行 / 430 KB** | **唯一的求解器**。两个类：<br>· `LevelSetSurface`（单场，`advance` @`:817`）<br>· **`LevelSetMulti`（多场生产类，`__init__` @`:1025`）** |
| **生产驱动** | **`pipeline/ca_pf_framework/_bk_exp.py`** | **3 393 行 / 335 KB** | **CLI 入口 + 物理装配 + 全部落盘**。`run()` @`:1016`、`main()` @`:4000` |
| **量具** | **`pipeline/ca_pf_framework/_bk_measure.py`** | 1 138 行 / 73 KB | `measure_state()`：`nslab_n` / `nf3_col` / F3 面积 / 长厚比 / 块划分，16 条对照已验证 |
| 板条表 | `windowB_lath.py` | 424 行 | `LathTable`：逐板条变体 + 小转动 θ ⇒ **F3（低角晶界）面能 `γ_RS(θ)`** |
| 弹性 | `windowB_pf3d.py` | 779 行 | `PF3D`：FFT 谱法**三维**弹性求解器（`C_from_voigt`/`C_hex`/`C_rot4`、`λ` 算子、`argmin_normal`） |
| 弹性（各向异性） | `windowB_aniso_elastic.py` | 127 行 | `AnisoElastic`：逐变体模量路径。⚠ **默认关，且无 CLI ⇒ 当前跑不到**（见 §四） |
| Wulff 凸化 | `windowB_wulff.py` | 115 行 | `mrel(n)`、`support_from_table`、`build_hull_points`、`h(d)=max_j(x_j·d)`（凸包络速度律） |
| 闭合关系 | `windowB_closure.py` | 810 行 | 热力学/动力学闭合：`beta_h_of_T`、`alpha_km_n_lath`、`n_lath_int`、`M_s`… |
| 薄膜 | `windowB_film.py` | 194 行 | Gibbs 面上的薄膜序参量 `ψ` |
| 面片投影 | `_r68_facet_op.py` | 82 行 | `facet_project_one`：**数值脚手架，见 §四 ⛔** |
| **回归闸门** | **`pipeline/ca_pf_framework/_r30_regress.sh`** | — | **归档路径逐位回归**。任何改动主代码后必须过（判据：**共有列逐位一致**） |
| 材料常数 | `T16_verify_rve.py` | — | `C`（刚度）、`EPS0`（相变应变）、`NPF`（惯习面法向）、`DF`、`MOB` |

**报告**：`pipeline/ca_pf_framework/R*.md` —— **173 份**，从 `R1`（再初始化审计）到 `R707`（物理正确性审计）。
**读报告的入口**：先读 **`R707_PHYSICAL_CORRECTNESS_AUDIT.md`**（当前状态的诚实判定）
→ 再读 **`WINDOWB_ROADMAP_TO_CORRECT.md`**（从当前状态到"全部正确"的实施步骤与 §9.20 的根因判决）
→ 然后 **`BLOCK_SELFAC.md`**（多面体/自协调几何的设计与合法性论证）。

---

### 二、实现路径（**从 CLI 到落盘的完整链条**）

```
   bash/py 启动器 或 直接 _bk_exp.py <CLI 参数>
        │
        ▼
① 装配（_bk_exp.py:1029-2260）
   · laths = [int(x) for x in --laths.split(',')]  ⇒ M = len(laths)
     ⚠ `--laths` 是**变体列表**不是根数整数：`--laths 3` 给 `[3]` ⇒ **M=1**；
       要 M 根同变体板条必须写 `--laths 1,1,1`（`_bk_exp.py:1029`，`R707 §4`）
   · build_table(laths,...)  →  LathTable（逐板条变体 + θ ⇒ γ_RS(θ)）
   · 从 T16_verify_rve 取 C / EPS0 / NPF / DF / MOB
   · 播种：seed_plate(k, center, normal=n*, R, t, ...)   @windowB_surface:3181
        │
        ▼
② 构造 LevelSetMulti（windowB_surface:1025）——实测 46–64 s / 134 MB（N=64,nv=24）
        │
        ▼
③ 逐步推进  advance()  @windowB_surface:4327     ← 每步做四件事
   │
   ├─③a 弹性：PF3D 谱法求 σ 与 Δed          （windowB_pf3d.py）
   │      ⚠ 引擎**从不暴露 σ** ⇒ 判据 J2/J7 目前测不了
   │
   ├─③b 界面速度  v = M(n)·[Δf + η·Δed − γ_eff·κ]   （windowB_surface:4857-4859 / :5128）
   │      · M(n)：`--mob-wulff` 走**凸包络**（Wulff 刻面机制）；`--mob-dip` 加 45° 凹陷；
   │              `--mob-iform {exp2,ellipse}`；`--mob-ratio`；`--mob-beta-h/-w`
   │      · 曲率项 κ：`--gamma0`；`facet_lam>0` 时换成**尖点** Herring 刚度（与 aniso 互斥）
   │
   ├─③c 平流：upwind / proj2 / central（`--adv-grad`）+ Sussman 再初始化
   │      ⛔ **已知缺陷**：再初始化**磨角** + 平流**角平均** ⇒ 有效各向异性只剩设计的 50–70%
   │         （`WINDOWB_ROADMAP_TO_CORRECT.md §9.20`）
   │
   ├─③d 形核：nucleate()  @windowB_surface:1995
   │      `--nuc-mode {auto,driver}` + `--eng-cadence` + `--nuc-law` + `--grow-stack`
   │      `--nuc-shape {disc,ellipsoid}` + `--nuc-sites-refill` + `--nuc-init`
   │      · `--laths` 的逗号项数 M = **场数硬上限**
   │      · `--nuc-every 0` **不等于**"不形核"（引擎路径仍按 `--eng-cadence` 撒核）
   │
   └─③e _finish_advance() @:5588 / _advance_perfield() @:5626
          · 边界回卷 wrap_axes()（周期性）
          · 块内界面自检（n_occ vs M）
        │
        ▼
④ 量具（每 --every 步）_bk_measure.measure_state(g)
   · nslab_n（在场板条数）/ nf3_col（低角晶界列数）/ F3 面积（µm²，逐对）
   · 逐板条体积 vols / 厚度 ths；包围跨度；撞盒 box_touch；nc 连通分量
        │
        ▼
⑤ 落盘  outdir = <--out>/<arm>_<tag>/     （--out 默认 `_exp/_bk_block`）
   · series.csv    ← **主读数**，每测点一行，列定义见 `_bk_exp.py:52+` 的 `COLS`
   · meta.json     ← 引擎 sha256（_engine_sha @:494）+ 全部参数 + 臂定义
   · snap_%05d.npz ← 全量 φ + region 快照（--snap-every）
   · nuc_dbg.json  ← 形核诊断（事件数 / attach / stack / oob / cov …）
   · seeds.npz     ← 核的位点与取向
```

### 三、最小可跑示例

```bash
cd pipeline/ca_pf_framework
PY=/root/miniconda3/envs/ml/bin/python      # 任何含 numpy 的 Python 3 均可

# 只构造 + 播种 + 初始测量（不推进）——最快的健全性检查
$PY _bk_exp.py --dry-run

# 一个 6 µm 盒、400 步的标准算例（4 核亲和 + nice=10，机是共享的）
nice -n 10 taskset -c 0-3 $PY -u _bk_exp.py \
  --N 96 --dx-nm 62.5 --steps 400 --every 25 --snap-every 25 \
  --arm dry --laths 1,1,1,1,1,1 \
  --plate-L 125.0 --plate-W 125.0 --plate-T 125.0 \
  --nuc-shape disc --grow-stack --nuc-every 0 --nuc-init 0 \
  --nuc-law cadence --nuc-block-target 0 --nuc-mode auto --eng-cadence 30 \
  --gamma0 0.25 --gamma-film 0.6 --alpha-km 0.041739 \
  --T-end 298.0 --cool-rate 2352400.0 --qs-clock 1 --qs-max-relax 100 \
  --beta-h 6.477 --beta-w 2.3 --ed-eta 0.253 \
  --mob-iform exp2 --mob-ratio 9.0 --mob-dip 4.0 --band-cells 40 --mob-wulff \
  --facet-proj 0 --rank1-swap none --var-rule ed --nuc-sites-refill 1 \
  --tag myrun

# 改过主代码后：必须过归档逐位回归（判据 = 共有列逐位一致）
bash _r30_regress.sh
```

> **CPU 纪律**：机器 20 逻辑核，**核 8–19 留给用户**。每个仿真进程
> 用 `taskset` 绑 **≤4 核** 且 `nice=10`，多个实验用**不相交**核段。
> 完整正文见 `pipeline/ca_pf_framework/R630_CPU_BUDGET.md`。
>
> **实验隔离纪律**：实验**不得修改主代码**；正道是"只加新脚本 + 只传 CLI 参数 + 落独立 `--tag` 目录"。
> 若必须改，只能"新开关 + 默认关 + `_r30_regress.sh` 共有列差异 = 0"。
> 完整正文见 `pipeline/ca_pf_framework/R629_EXPERIMENT_ISOLATION.md`。

### 四、⚠ 当前**已知未闭合**的问题（请专家重点看这几条）

| # | 问题 | 出处 |
|---|---|---|
| **1** | **板条长厚比卡在 ~3.2，设计值是 33**。根因已定量：**`M(n)` 的有效各向异性只剩设计值的 50–70%**（`β_w^eff`=1.15 vs 2.3，`β_h^eff`=2.44 vs 3.5），**与网格无关**。修法候选四条**全被实测否掉**（加密网格 / `facet_lam` / `norm_smooth` / 调大 `β`）；**唯一剩下的杠杆是"不带反馈的界面法向估计"**，**尚未实施** | `WINDOWB_ROADMAP_TO_CORRECT.md §9.20/§9.20b/§9.20c`、`R707` |
| **2** | ⛔ **"打开刻面生长"这件事，做的是几何硬掰（`--facet-proj`，每步把 `φ_k` 覆盖成轴对齐盒子），不是物理修复。** 上游 `BLOCK_SELFAC.md §9.4` **明文禁止**把该口径下的长径比当物理量引用。⚠ **默认 `--facet-proj 0`** ⇒ **归档里的板条形状仍是不正确的那个；靶 9:1 在诚实口径下从未达到** | `R707`（审计）、`R649`、`R650` |
| **3** | **厚度停止的能量判据只有一半成立**：E1 ✅（弹性抵消 66% 化学驱动）、E2 ✅（界面能仅 0.3%）、**E3 ❌**（弹性项 880 步只变 6% ⇒ 是"跟随"不是"选定"）。⇒ **缺"厚度依赖的弹性能标度"，未实现** | `R646 §4`、`R632` |
| **4** | **增厚势垒推导完成但没进引擎**：`e_misfit = 0.4196 J/m²`、`ΔG* = 0.262 eV`、`β_h ∝ 1/T` 精确；但引擎 `Mfac` **只吃常数**，物理形式停在 `windowB_closure.beta_h_of_T` 里 | `R633`、`R646 §4` |
| **5** | **`elastic_soft` 是硬编码 `True`**（`windowB_surface.py:1253`），`_bk_exp.py` 里 **零命中 ⇒ 无 CLI**；**`aniso_elastic` 默认 `False`、同样无 CLI** ⇒ **三维弹性各向异性这条物理通道当前拿不到** | `R707 §3` |
| **6** | **`meta.json` 不落盘 `mob_wulff`/`mob_dip`/`facet_proj`/`band_cells`** ⇒ **配置无法自证**（因此出过一次错误结论） | `R690 §5`、`R694 §6` |
| **7** | 上游级冲突：goal 判据 `\|v/MΔf − 1\| < 0.02` 与仓库实测 `0.818`（`Δx = 62.5 nm`）冲突 ⇒ **按该判据现引擎已 FAIL** | `R684 §3.2` |
| **8** | **引擎从不暴露 `σ` 张量** ⇒ 多处判据（`[σ·n]=0`、`∇·σ=0`）**无法测** | `R678 §4` |

**踩过的坑（接手前必读）**：仓库根目录 **`AGENTS.md`** 的 §3（会静默出错的、会白烧机时的、会误判因果的三类）
与 §7.5–§7.7（Window B 的性能/实验隔离/CPU 纪律 `P1`–`P49`、`E1`–`E3`、`C1`–`C5`）。
⚠ **该文件已接近工作区指令预算上限（65 536 字节），读的时候若被截断，§7 的内容在
`pipeline/ca_pf_framework/R581_DISCIPLINES.md` 里有全文。**

---


## 仓库结构

| 目录 | 内容 |
|---|---|
| **`pipeline/ca_pf_framework/`** | ⭐ **Window B（当前主攻方向）**：纯 Python/numpy 的「体相场 + 零厚度 Gibbs 面」板条马氏体仿真。**主仿真文件清单与实现路径见本 README 开头那一节** |
| **`pipeline/`** | 早期目标的主代码（MOOSE）。相场算例、生成器、生产脚本、诊断与验证工具、全部规划文档 |
| **`pipeline/validated/`** | **验证分支与最小算例**（**不是生产**）。按独立审计的实施计划建：物理修复一律先在这里做，验证通过再议是否合入生产。入口见 `validated/VALIDATION_STATUS.md` |
| `docs/` | 两份专家审核意见 + **`agent-notes/`（代理工作笔记，接手前先读）** + `guidence_material/`（独立审计材料包） |
| `reference/` | MOOSE 参考源码（LGPL 2.1，许可证头完整保留；仅作查阅，非本项目代码） |
| `phase0a/` | Cahn–Hilliard 守恒性的早期验证算例 |

### 用 AI 代理接手这个项目

| 文件 | 给谁 |
|---|---|
| **[`AGENTS.md`](AGENTS.md)** | **Codex 及其它代理**——自动读取的工作指令：用户的标准约束、踩过的坑、环境事实 |
| **[`docs/agent-notes/`](docs/agent-notes/)** | 前任代理（Claude Code）的持久记忆 17 条，含排查历史与 API 陷阱 |

`AGENTS.md` §3「踩过的坑」是本仓库最值钱的部分——**那里面每一条都花过真实代价**。

### `pipeline/` 里先看这几份

| 文件 | 说明 |
|---|---|
| **`REPORT_FOR_EXPERTS.md`** | **完整进展报告**——目标、模型、决策理由、已完成工作、全部问题（P1–P19）与待专家回答的问题（Q1–Q14）。**想快速了解这个项目就读它** |
| `ROADMAP.md` | 技术路线、实测结论、操作踩过的坑 |
| `GATE0_PROGRESS.md` | Gate 0（冻结可重复性）的完整档案 |
| `GATE1_PLAN.md` | Gate 1（物理单元测试）的规划与滚动进展 |
| `GB_SOLUTE_GOAL.md` | 晶界溶质的目标与达标判据 |
| `OPEN_PROBLEMS.md` | 问题清单 |

---

## 执行结构

评审定的四个 Gate：

| Gate | 内容 | 状态 |
|---|---|---|
| Gate 0 | 冻结可重复性 | ✅ 完成 |
| Gate 1 | 物理单元测试 | 🚧 进行中（步骤 0、1 完成；步骤 3–5 未开始） |
| Gate 2 | 热力学输入分层 | ⬜ 未开始 |
| Gate 3 | 二维熔池与数据 | ⬜ 未开始 |

---

## 当前状态（一句话）

**已建成的**：2D 单熔池相场模型（430×150 µm，`dx = 1 µm`，8 个序参量 + 溶质分裂式
Cahn–Hilliard + 解析温度场），含取向差加权的晶界能/迁移率与热梯度对齐；
非 AD + BDF2 + ASM/ILU，牛顿二次收敛到 1e-10；生成器已冻结并带 SHA256 校验；
**晶粒核的雅可比已补全**（自建 MOOSE app `pipeline/app/`，补上上游 `ACGrGrPoly`
丢掉的两类项 —— 见 `pipeline/validated/VALIDATION_STATUS.md §1.4`）。

> ⚠ **但请注意**：补上之后 FD 比值**一位没变**（缺项只有 ~5e-7 相对）
> ⇒ **T1 的 1e-5 判据在生产配置上仍然过不了，而且原因不是它**。
> 主导误差**尚未定位**，§1.4 有排除表。不要引用这条修复去解释 T1。

**已知的硬问题**（详见 `REPORT_FOR_EXPERTS.md` §6）：

- **尺度分离**：弥散界面宽约 2 µm，真实溶质边界层 `D/V ≈ 4 nm`，相差 **476 倍** ⇒
  薄界面理论要求 `W < D/V` 才定量，**我们远离定量区**
- **网格欠解析（已定量）**：平衡界面宽 `w = sqrt(κ/µ) = 1.414 µm`，`dx = 1 µm`
  ⇒ 只有 **1.41 个单元/界面宽**。实测（T8b，`wGB = 4 µm` 固定、只扫 `dx`，
  以 `dx = 0.25 µm` 为基准）：`dx = 0.5 µm` 偏 **+1.61%** ✅，
  **`dx = 1 µm` 偏 +6.85% ❌**（判据 5%），拟合 R² 同步从 0.9999 掉到 0.994。
  ⇒ 该花的是网格（`dx → 0.5 µm`，4× 代价），**不是**改 `wGB`
  （`wGB = 2 µm` 要 64× ≈ 50 天）。完整论证见 `VALIDATION_STATUS.md §1.5`
- **文献空白**：Ti64 的晶界偏析焓、晶界扩散系数、三重积等定量数据**基本不存在**
- **模型缺口**：无形核（算不出等轴晶）、无溶质拖曳（自由能未进入序参量方程）
- **参数出处**：`σ = 0.6 J/m²`、`M₀ = 232 m⁴/(J·s)`、`A_ani = 0.7` 三个参数缺可靠出处

---

## 运行环境

- **MOOSE**：生产用 **自建 app** `/root/projects/gb_jac/gb_jac-opt`（= `phase_field`
  模块全部对象 + 本项目的雅可比补全核 `ACGrGrPolyJ`，源码在 `pipeline/app/`）。
  原版 `/root/moose/modules/phase_field/phase_field-opt` **未被改动**。
  重建自建 app：`bash pipeline/app/build_app.sh`
- 本工作使用 PETSc 3.25 / SLEPc 3.25
- **Python 3** + numpy（`extract.py` 读 Exodus 需要 `netCDF4`）
- ⚠ **跑 MOOSE 前必须激活含 `mpicxx` 的环境**（conda 的 `moose`），否则 `ParsedMaterial`
  的 LLVM JIT 会全部失败并**静默退回解释执行**（数值结果相同，但慢）。
  ⚠ 建 app 时**同样必须激活** —— libMesh / PETSc / WASP 全来自 conda 的 `moose-dev`，
  它们的位置由激活环境时设置的 `LIBMESH_DIR` / `PETSC_DIR` / `WASP_DIR` 指定。

```bash
# 建自建 app（只需一次；改了核再跑一次即可，增量编译）
bash app/build_app.sh

# 生成算例（在 pipeline/ 下）
python3 frozen/gen_aniso_nonad.py --op-num 8 --out aniso_block.i
python3 frozen/splice_aniso_nonad.py        # 合成 stage1_meltpool_d.i
python3 validated/make_jacfix.py --src stage1_meltpool_d.i --out N.i   # 换成补全核

# 语法检查（务必先做——MOOSE 的「未使用参数」检查在跑完之后）
/root/projects/gb_jac/gb_jac-opt --check-input -i N.i

# 生产运行（自动做上面全部步骤 + 哈希校验 + 断言）
bash run_nonad_prod.sh
```

**`frozen/` 下的两个生成器已冻结并登记 SHA256**（见 `frozen/SHA256SUMS`），
`run_nonad_prod.sh` 会在运行前校验哈希，被改动就拒绝运行。

---

## 本仓库未包含的内容

`.gitignore` 排除了三类，理由各不相同：

| 类别 | 例子 | 理由 |
|---|---|---|
| 机器相关 / 可再生 | `.conda/`、`__pycache__/`、`.vscode/` | 不该进版本库 |
| 体积大且可再生 | `*.e`（Exodus，单个 42 MB） | 可由 `.i` 重新生成 |
| **第三方版权材料** | 期刊论文 PDF、出版商网页、论文插图、论文抽取正文 | **公开仓库不能分发** |
| **Window B 的重产物** | `pipeline/ca_pf_framework/_exp/`、`prod_mob_snap*/`、`**/*.npz`、`pf1d_moose/` | **实测 33 GB + 1.7 GB + 4.7 GB**，全部可由 `.py`/`.sh` + 归档 `series.csv` 重新生成 |
| 就地回退副本 | `*.b2orig`、`*_backup_windowB_surface.py_*`、`_r580_backup/` | `R629 E3`/`B2-D4` 的回退锚点，非项目内容 |

> ⚠ **Window B 的源码与报告是入库的**：`windowB_*.py`、`_bk_*.py`、`R*.md`（173 份）、
> 启动器与量具脚本、`_r30_regress.sh` —— 这些是审阅对象。
> 被排除的只是**大数组快照**与**文献缓存**。

⇒ 因此**文献原文不在仓库里**。报告 `REPORT_FOR_EXPERTS.md` §9 列出了全部需要的
文献及其 DOI，可据此自行获取；Window B 的文献索引见
`pipeline/ca_pf_framework/BLOCK_LIT_REQUEST.md` 与 `R665`/`R670`/`R691`（含 DOI/URL）。

---

## 许可

- 本项目自身代码：**MIT**（见 `LICENSE`）
- `reference/` 下的文件来自 **MOOSE 框架**，遵循 **LGPL 2.1**，原始许可证头已完整保留
