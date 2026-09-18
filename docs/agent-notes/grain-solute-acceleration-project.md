---
name: grain-solute-acceleration-project
description: 用户在 F:\speed_up 推进的研究方向——晶粒组织演化 + 溶质扩散耦合的加速计算，含实测结论与文献核查结果
metadata: 
  node_type: memory
  type: project
  originSessionId: 5a8d92ac-94c6-4a23-856f-0d7a42daf5b8
  modified: 2026-09-17T08:27:43.432Z
---

用户课题：**加速"晶粒组织演化 + 元素扩散"的耦合计算**，目标体系 Ti-6Al-4V，要求三维。原始思路见 `F:\speed_up\研究思路简化版.docx`。

## ⚠️ 方向调整（2026-09-17）：转向 LPBF 增材制造

用户把应用领域锁定为 **LPBF 增材制造 + Ti64**，要"从温度场到最终凝固晶粒的完整演化"，分两阶段、各配一个神经算子：

- **阶段一**：熔融→凝固。输入温度场，输出"热的"晶粒
- **阶段二**：降到室温

用户已确认的四个选择：
1. **算子只学溶质**，晶粒几何仍来自相场参考解（保持现 pipeline 架构）
2. **阶段二只做 β 晶粒长大/粗化**，暂不碰 β→α′ 马氏体
3. **温度场自己造**（激光照射 Ti64），不要求绝对精确
4. **先做一个熔池**，打通再说

方案见 `F:\speed_up\LPBF方案_单熔池.md`。关键结论：
- **最大风险在阶段一的参考求解器**：全库零个示例把 GrainTracker 与液相放在一起；凝固是**连续形核**，而 GrainTracker 的 `reserve_op` 机制是为"消失"设计的 → 序参量槽位会耗尽
- 阶段二几乎零新物理：`GBEvolutionBase` 的 `T` 本来就是耦合变量（Arrhenius），官方 `temperature_gradient.i` 用 `variable_mobility = true` + `FunctionAux` 驱动 T 场
- 温度场已标定（`pipeline/thermal_field.py`）：Rosenthal 解，熔池 95×48 μm、冷速 1.79e6 K/s
- **发现既有算例的 bug**：`phase2_prod.i` 的 `A_scale=0.5` 与 `ACGBPoly` 差因子 2，变分不自洽（应改 1.0）
- `replay_transfer.py` 的"面出现"分支是空实现（`take=0.0`），而凝固阶段以"诞生"为主 → 必须先补

## 关键实测结论（2026-09-16，在 MOOSE 上跑出来的）

在 **相场 + GrainTracker** 路线上做了三点对照实验：

| 配置 | ΔM 相对漂移 |
|---|---|
| 固定网格 80×80 | **0.000e+00**（严格零） |
| 固定网格 640×640 | **0.000e+00** |
| AMR 自适应 | **-3.6e-4** |
| AMR 只细化不粗化 | **-2.0e-3**（更大，说明不是粗化的锅） |

**结论：晶粒消失（拓扑事件）完全不破坏守恒；破坏守恒的是"网格本身在变"（AMR）。**
原因：网格固定、`GrainTracker::swapSolutionValues()` 只交换序参量、不碰浓度场。

**这意味着**：用户原初设想的"显式界面追踪 + 拓扑事件守恒"才是真问题所在；而相场路线把这个问题的前提消解掉了。

## 文献核查（2026-09-16，OpenAlex/arXiv 穷尽检索）

用户的具体想法：**传统拓扑演化 + 神经算子作用在晶界面网络（面）上**。

- **没人完整做过**。硬证据：`"grain growth" AND "operator learning"`=0、`"polycrystal" AND "operator learning"`=0、`"neural operator" AND "surface mesh"`=0、`"grain boundary" AND "neural operator"`=1（无关）
- **但两侧都有人站着**：
  - GrainGNN（*JCP* 510:113061, 2024）已在 GB 网络图上做学习演化，且处理拓扑事件——**但拓扑裁决权在神经网络手里**，且不是 operator、无溶质
  - Bugas & Runnels（*JMPS* 2024）用图论做经典 GB 网络动力学——**但无学习**
- **最可能的抢先者：Biros 组**（GrainGNN 作者），下一步自然就是把拓扑裁决换成经典判据 + 加溶质
- **风险**：新颖性属"表述的重新划分"而非新方法学，审稿人可能说"GrainGNN + front-tracking 的自然组合"。**立足点必须是可量化优势**（拓扑变化时的守恒严格性、分辨率不变性、跨晶粒尺度泛化）

## 产出文件

- `F:\speed_up\研究方案_深化版.md` — 完整方案（含核验后的更正清单）
- `F:\speed_up\研究规划_详细版.md` — 18 个月分阶段规划
- `F:\speed_up\grain-solute-plan.html` — 排版版
- `F:\speed_up\phase0a\` — 可运行的 MOOSE 实验（输入文件、分析脚本、运行脚本、结果）
- `F:\speed_up\reference\` — MOOSE 源码笔记（ACGBPoly、GrainGrowthAction、GBEvolution、GrainTracker 等）

环境：MOOSE 装在 WSL（整个 WSL 在 F 盘），见 [[wsl-moose-environment-setup]]。

相关：[[artifact-publishing-unavailable]]
