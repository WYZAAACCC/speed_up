# 以【代码】为准的复核：哪些文档问题已被解决 / 已被绕过 / 仍然空着（2026-09-25）

> 方法：**只读代码**（模块、类、关键字、判据脚本、算例），再与文档里的开放问题逐条对照。
> 不依赖文档自述。范围：`pipeline/ca_pf_framework/`（v2 路线的实现）+ `pipeline/validated/`
> （生产 MOOSE 模型的 T 矩阵验证）+ 两者之间的引用关系。
> ⚠ 本文件是**代理记录**；涉及 `MATH_FRAMEWORK` / `IMPLEMENTATION_PLAN` 的改动建议**需用户确认**。

## 1. 代码清单（实况）

**v2 路线（Window A/B/C）**
| 文件 | 行数 | 实现内容（读代码） |
|---|---|---|
| `ca3d.py` | 1166 | **Window A 三维 CA**：形核（基底/体、连续谱）+ `IRF` 插值表生长 + decentered-octahedron 捕获 + **halo** + 滑窗 + 取向/竞争 |
| `ca3d_solute.py` | 161 | CA 上的**液相溶质输运**：亚网格 `f_s` + 杠杆律分配 + 只在液相通道扩散（无扩散 ⇒ 精确 Scheil）+ `Γ_GB` 输出 |
| `thermal_layer.py` | 352 | 焓式能量方程 + 潜热（L1-T） |
| `windowB_surface.py` | 1735 | **当前主实现**：多区域 **level-set 面场**（每胞一个标签）+ **面上 Γ 场**（McLean 吸附 / 保守边通量面扩散 / 面-体交换 / Stefan 排出 / 三叉线 ΣJ=0）+ `LevelSetSurface`（单畴解析判据）+ **M2 12 变体 3D RVE** + 各向异性刚度(Herring)/ENO 重init/速度延拓/射线交点量测 |
| `windowB_pf3d.py` | 499 | **多变体 PF 引擎 `PF3D`**：非守恒序参量 + **FFT 谱法微弹性** + ε⁰ 驱动 + **`sigma_ext`（外应力输入 ✓）** + 能量/力/步进；另含 `C_iso3`/`C_hex`/`C_cubic`/`C_rot4` |
| `windowB_pf.py` | 198 | **`MartensitePF`**：马氏体变体 PF（非守恒 + FFT 微弹性） |
| `windowB_gibbs.py` | 549 | **`GibbsLath`**：胞**重标号**动力学（提议随机顺序、**接受靠精确总能单调下降**）+ G1/G2/G3 能量判据（面能驱动粗化等）|
| `windowB_hybrid.py` | 391 | **`advance(..., rng)`：`draw = rng.random(...)` ⇒ 随机翻转**（KMC 式）|
| `windowB_rve3d.py` | 134 | PF 版 12 变体 3D RVE（含 `calibrate_L` 反标定迁移率到目标速度）|
| `windowB_ptmc.py` | 79 | PTMC 不变平面判据（λ₂=1）|
| `windowB_nucleus.py` | 69 | 晶核法向两条独立判据交叉（+ `_chk_334.py`/`_chk_nstar.py`）|
| `windowB_elastic.py` | 87 | 各向同性 FFT 微弹性地基 + T1/T2/T3 解析判据 |
| `windowB_aniso_elastic.py` | 168 | **不均匀/各向异性弹性求解器**（参考介质 + 极化迭代 + 热启动）|
| `windowB_drag.py` | 61 | **拖曳隐式闭合**（`solve_v`）|
| `windowB_coupling.py` | 96 | **层间守恒转移 Π**（`overlap_1d` + `ConservativeTransfer`）|
| `windowB_ti64_variants.py` | 187 | 12 个 Burgers 变体的 ε⁰（自带 C1–C6 自检）|
| `verify_framework.py` | 892 | 框架级 76 条判据（含 **IRF 生成器 `kgt_given_V`**、量纲/恒等式/闭式极限、**"必须用 AMG"的告警文本**）|

**判据脚本（34 个）**：`_chk_s1/_d4/_w2/_a3/_w1/_p1/_pf/_m2/_m2ab/_m2c/_m4/_m4_iso/_m4_iso2/_h6/_h7/_drag/_hex/_as/_aniso/_irf/_irf2/_thermo/_gamma_T/_334/_nstar/_liq/_win/_stefan_dbg/_Eel/_solid_total` + `pf1d_interface.py` + `pf1d_moose/p1c_prod1d.py`
**回归**：`_run_reg.sh`（S0/S1/M1/M3/M4/D4/A3/W2/W1/P1/PF/HX/AV/AS/H6/H7/drag + M2-A/B/C/D）
**MOOSE 算例**：`pf1d_moose/*.i`（35 个；含 `p1a_1d` P1-a 锐界面极限 ✓、`p1c_alpha2/p1c_kr/p1c_kcw/p1c_prod1d` 抗截留标定族、`min_1d/2d/3d` 等）
**生产 MOOSE 验证（另一套宇宙）**：`pipeline/validated/`（≈110 个脚本：`run_t8_dx.sh`、`run_kc_vs_keff.sh`、`_run_prod1d.sh`、`make_antitrap_prod.py`、`make_drag_prod.py`、`make_amr_prod.py`、`make_phase3_prod.py`、`gb_width_vs_s.py`、`robust_csv.py`、`lit_lookup.py`/`lit_scan.py`、`jacobian_test.sh` …）

## 2. ★ 文档说"没有"，**代码里其实有**（或被绕过）

| # | 文档里的说法 | 代码实况 | 判定 |
|---|---|---|---|
| **A1** | 「代码里 **`马氏体/α′` 0 命中**」（我此前多次这么写）| **6 个文件命中**：`windowB_pf.py`(`MartensitePF`)、`windowB_pf3d.py`(`PF3D`)、`windowB_gibbs.py`(`GibbsLath`)、`windowB_rve3d.py`、`windowB_ptmc.py`、`windowB_bench3d.py`。其中 **`PF3D`/`MartensitePF` 就是多变体马氏体 PF 引擎**（非守恒序参量 + FFT 微弹性 + ε⁰ 驱动）| **文档过强** ⇒ 应改为「引擎在、**T 依赖势垒/KM/束缚判据**不在」|
| **A2** | P2.1 判据 2「**变体选择**」未做 | `PF3D.__init__` **已接 `sigma_ext`（外应力）**；文件里有「变体选择」；M2 的 `npref` 就是"弹性最省能法向" | **机制已在**；缺的只是**判据脚本**（给定 σ ⇒ `ΔE_v=−σ:ε⁰_v` 最小）|
| **A3** | 惯习面 `{334}_β` "未核实" | **两个独立判据已经在**：`_chk_334.py`（{334} 族弹性能 vs 2000 随机方向的分位）+ `_chk_nstar.py`（把 **PTMC 不变平面法向**代入 `½ε:Λ(n):ε`）| **有判据、只是没进文档表** |
| **A4** | V6「窗口/halo 的 domain-size convergence ❌未做」| `ca3d.py` **有 halo**；`verify_framework.py` 有 halo 判据；`verify_ca3d_solute.py`/`verify_ca3d_wc_cet.py` 带 halo | **CA 侧已做**；**Window B 侧未做** ⇒ 必须**分侧记** |
| **A5** | 「Window B 的表示未定」 | **两条路都在**：`GibbsLath`（重标号/非热极限，带 G1–G3 判据）与 `LevelSetMulti`（level-set，当前主实现）。`WINDOWB_SURFACE_AUDIT` §7.1.1 写了"一律以 level-set 为主"，但 `MATH_FRAMEWORK`/`IMPLEMENTATION_PLAN` **没写** | **文档间不一致** ⇒ 权威文档里要写死「生产路径 = level-set」|
| **A6** | 「Gibbs 面还没接到真实晶粒网络」 | `_chk_liq.py` / `_chk_win.py` **直接读 CA 的输出 `meltpool_growth_gid.npz`** 做曲面/池形统计 ✓；`windowB_gibbs_rve.py` 也在 | **分析层已接**、**演化层未接** ⇒ 说法要精确 |

## 3. 代码里仍在、但按**用户硬约束**不该是主路径的（遗留 ✗）

| # | 代码 | 问题 | 处置建议 |
|---|---|---|---|
| **B1** | `windowB_hybrid.py::advance(..., rng)` | `draw = rng.random(...)` ⇒ **随机胞翻转**（KMC 式）⇒ 违反用户"模型层禁止元胞自动机 / 禁止随机胞翻转"✗ | 头部加"**历史原型，禁止作主路径**"（现在只有审计文件说过）|
| **B2** | `windowB_gibbs.py::GibbsLath.sweep` | **胞重标号**（提议顺序随机、接受用精确总能单调下降）——框架 §5.8.3 认可其"非热极限"语义，但**形式上仍是元胞重标号**，与"面场 + PDE"路线不同 | 标为"**非生产路径**，仅作 G1–G3 能量判据的参考实现" |
| **B3** | `windowB_rve3d.py` vs `windowB_surface.py::M2_twelve_variants` | **两套 12 变体 RVE**（PF 版 / level-set 版）并存；PF 版还带 `calibrate_L`（反标定迁移率到目标速度）| 明确"当前 = level-set 版"；PF 版留作对照 |

## 4. 文档说"已做/已过"，核对后要**打折**的

| # | 文档 | 实况 | 状态 |
|---|---|---|---|
| C1 | 交接表「M3 = 1.09e-4 ✅ / A3 PASS」| HEAD 上实测 **`nan` FAIL** ✗（本轮查到并修好，真 PASS）| **已更正** |
| C2 | 「生产 `F_at` 的 ALPHA=2 是标定过的」| 在本轮建的**生产公式 1D 条带**上实测：ALPHA=2 的 `c_int` 仍差 **−14%** ✗ | **已记账** |
| C3 | 「`irf_ti64.csv` 是 LKT 解」| 本轮**独立复算**核对全 115 行：R 1.1e-3 / ΔT 5.1e-4 ✓（并定出 μ_k=1.0）| **已补证据** |
| C4 | §5.8.5「Δx 由板条间距定（10–50 nm）」| 与文献/docx 的 µm 级板条冲突、且自相矛盾 ⇒ 更正为 **Δx≈0.1–0.5 µm（建议 0.25）** | **已更正** |

## 5. 代码里**确实是空的**（文档说法成立 ✓）

| 项 | 代码证据（关键词 0 命中） | 结论 |
|---|---|---|
| **B1 的 T 依赖驱动力 / KM 动力学** | `M_s`、`Koistinen`、`Landau`、`athermal` **全部 0 命中** | 确实没有（引擎在、驱动力与判据不在）|
| **P2.3 晶界 α 膜** | `晶界alpha`、`GB_alpha` **0 命中** | 确实没有 |
| **B2（α′→α+β 扩散分解，含 Al）** | 无实现（注意 `_diag_b2.py` 里的 "b2" 是别的量，别误读）| 确实没有 |
| **全局事件驱动调度（L0 混合自动机）** | `调度`/`scheduler` 0 命中；`ca3d.py` 的"自动机"只是**元胞自动机**这个词 | 确实没有 |
| **P1.4 AMG/迭代求解器** | `GAMG` **0 命中**；`verify_framework.py` 里的 "AMG" 只是**告警文本** | 确实没有 |
| **Window C 的「移动曲面 + 三叉线联合」** | H6 是**静态**三叉线、W2 是平/球面速度 ⇒ 没有同时做的算例 | 确实没有 |
| **Phase 5 算子 / teacher 数据** | 无训练相关代码 | 确实没有 |

## 6. 以代码为准的进度（一句话/每项都带代码依据）

- **Window A**：`ca3d.py` + `ca3d_solute.py` + `thermal_layer.py` **齐**（IRF 表已独立复核 ✓）；余：倾斜梯度取向、输运 dt 收敛。
- **Window B**：**表示层齐**（level-set 面场 + 面上 Γ + 各向异性/不均匀弹性 + 拖曳闭合 + Π）；**PF 引擎齐**（`PF3D`/`MartensitePF`，含外应力）；**物理驱动缺**（T 依赖势垒/KM/束缚）、**B2 缺**、**GB α 膜缺**、**判据脚本缺**（变体选择）。
- **Window C**：**面上热力学/守恒/面扩散/三叉线（静态）齐**；**移动曲面 + 三叉线联合缺**、**接真实网络（演化层）缺**。
- **跨窗口**：`Π` 守恒算子 ✓（小算例）；**halo（CA 侧）✓ / Window B 侧缺**；**AMG 缺**；**调度器缺**。
- **生产 MOOSE 侧**（`pipeline/validated/`）：T 矩阵脚本齐；本轮新增/影响：`F_at` 标定结论（ALPHA=2 欠修正）、`Δx` 口径更正、F1/F2 的文献+理论分析。
- **遗留 ✗**：`windowB_hybrid.py`（随机翻转）、`GibbsLath`（重标号）两条**非生产路径**仍在仓库，需在权威文档里标死。

## 7. 建议的文档更正（需用户点头的列在这里）

1. `IMPLEMENTATION_PLAN.md` P2.1：把「B1 未做」改成「**引擎已在（`PF3D`/`MartensitePF`），缺 T 依赖驱动力 + KM + 束缚 + 判据**」；
2. `MATH_FRAMEWORK.md` §5.8.5 附近：写明「**生产路径 = `windowB_surface.py`（level-set 面场）；`windowB_gibbs.py`/`windowB_hybrid.py` 为非生产参考**」；
3. `MATH_FRAMEWORK.md` §7 的 V6：拆成「**CA 侧 halo（已做）** / **Window B 侧（未做）**」；
4. 把 `_chk_334.py`/`_chk_nstar.py` 的结论并入「惯习面」那一行的证据栏；
5. 把「代码里 `马氏体/α′` 0 命中」这句在**所有文档**里改掉（改为「生产熔池输入里 0 命中」）。
