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
| `docs/` | 两份专家审核意见 |
| `reference/` | MOOSE 参考源码（LGPL 2.1，许可证头完整保留；仅作查阅，非本项目代码） |
| `phase0a/` | Cahn–Hilliard 守恒性的早期验证算例 |

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
非 AD + BDF2 + ASM/ILU，牛顿二次收敛到 1e-10；生成器已冻结并带 SHA256 校验。

**已知的硬问题**（详见 `REPORT_FOR_EXPERTS.md` §6）：

- **尺度分离**：弥散界面宽约 2 µm，真实溶质边界层 `D/V ≈ 4 nm`，相差 **476 倍** ⇒
  薄界面理论要求 `W < D/V` 才定量，**我们远离定量区**
- **文献空白**：Ti64 的晶界偏析焓、晶界扩散系数、三重积等定量数据**基本不存在**
- **模型缺口**：无形核（算不出等轴晶）、无溶质拖曳（自由能未进入序参量方程）
- **参数出处**：`σ = 0.6 J/m²`、`M₀ = 232 m⁴/(J·s)`、`A_ani = 0.7` 三个参数缺可靠出处

---

## 运行环境

- **MOOSE**（`phase_field-opt`），本工作使用 PETSc 3.25 / SLEPc 3.25
- **Python 3** + numpy（`extract.py` 读 Exodus 需要 `netCDF4`）
- ⚠ **跑 MOOSE 前必须激活含 `mpicxx` 的环境**，否则 `ParsedMaterial` 的 LLVM JIT
  会全部失败并**静默退回解释执行**（数值结果相同，但慢）

```bash
# 生成算例（在 pipeline/ 下）
python3 frozen/gen_aniso_nonad.py --op-num 8 --out aniso_block.i
python3 frozen/splice_aniso_nonad.py        # 合成 stage1_meltpool_d.i

# 语法检查（务必先做——MOOSE 的「未使用参数」检查在跑完之后）
phase_field-opt --check-input -i stage1_meltpool_d.i

# 生产运行
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
