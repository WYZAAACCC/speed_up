# Ti64 LPBF 相场仿真 + 逐面神经算子

加速 **Ti-6Al-4V（Ti64）激光粉末床熔融（LPBF）** 中耦合的「晶粒结构演化 + 元素扩散」计算：
用 MOOSE 相场仿真生成训练数据，训练**神经算子**替代其中最昂贵的部分。

**硬约束**：算子要学的是**接近真实的物理**，不是复现一个粗网格模型。
因此模型的物理正确性本身就是指标，而不是「先跑通再说」。

---

## 仓库结构

| 目录 | 内容 |
|---|---|
| **`pipeline/`** | **主代码**。相场算例、生成器、生产脚本、诊断与验证工具、全部规划文档 |
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

⇒ 因此**文献原文不在仓库里**。报告 `REPORT_FOR_EXPERTS.md` §9 列出了全部需要的
文献及其 DOI，可据此自行获取。

---

## 许可

- 本项目自身代码：**MIT**（见 `LICENSE`）
- `reference/` 下的文件来自 **MOOSE 框架**，遵循 **LGPL 2.1**，原始许可证头已完整保留
