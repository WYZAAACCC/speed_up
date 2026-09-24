---
name: amr-crash-root-cause
description: AMR 段错误的真正原因（硬编码 elementid 后处理，不是 SplitCH），以及 AMR 在生产模型上实测可用
metadata: 
  node_type: memory
  type: project
  originSessionId: b6decc92-d1df-4297-b052-ad15b31c0547
  modified: 2026-09-19T12:06:52.084Z
---

**「SplitCH + AMR ⇒ 段错误」这条旧结论是误判。真正的元凶是硬编码 `elementid` 后处理。**

2026-09-19 判决性实验（`pipeline/validated/run_t14_diag.sh`），同一算例只差那两个后处理块：

| 变体 | 配置 | 单元数 | 结果 |
|---|---|---|---|
| A | `front1d.i` 原样 + AMR | 160→186 | ❌ 段错误（6 秒） |
| B | **只删掉 2 个 `elementid` 后处理** | 160→**298** | ✅ 跑完 107 步 |
| C | 同 B 不开 AMR | 160→160 | ✅ 对照 |

旧结论来自 `front1d.i`（崩）与 `grain_growth_circle.i`（不崩）的对照 ——
但两者在**维度、物理、材料、后处理**上**全都不同**，隔离不成立。
真正差异是 `front1d.i` 有 `ElementalVariableValue` + 硬编码 `elementid = 4 / 155`；
AMR 后该 id 变成非活动父单元，其 DOF 不在解向量里 ⇒
`PetscVector::get(std::vector<unsigned long>, double*)` 越界 —— **正是已解出的崩溃符号**。

**2D 生产配置已实测可用**（`run_t14_2d.sh`，生产输入本来就零 `elementid`）：
`refine` 档单元数 1026→3015、**`total_solute` 漂移 0.00e+00**、
`liquid_frac` 与 `uniform` 差 0.07%（判据 5%）。

**怎么用**：开 AMR 时不要用靠 `elementid` 取值的后处理，换 `ElementExtremeValue` /
`ElementAverageValue` / `NodalExtremeValue`；**并且必须看 `NumElements` 确认 AMR 真生效**
（老式 `Adaptivity` 写法会「跑完不报错但一个单元都没动」）。

**Why**：这条直接决定「dx 要不要加密到 0.5 µm」这个决策 ——
均匀加密 4×（19h→76h/轨迹），而 AMR 定向加密的代价远低于此。

**How to apply**：要提 dx 精度时先考虑 AMR；改任何 AMR 算例后查 `n_elem` 变没变。

相关：[[grain-solute-acceleration-project]]、[[moose-api-gotchas]]
