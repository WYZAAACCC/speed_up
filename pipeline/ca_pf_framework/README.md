# ca_pf_framework —— 新路线（v2）的数学框架与自检

对应研究路线：`Ti64_CA_PF_Gibbs_NeuralOperator_EventDriven_v2.docx`
（Window A = 滑动窗口 CA；Window B = 局部精细 PF；Window C = Gibbs 面最后做）

| 文件 | 作用 |
|---|---|
| `MATH_FRAMEWORK.md` | **主交付物**。状态/调度/四层方程/接口量/守恒/V&V/自检结论/决策记录 |
| `verify_framework.py` | 框架自检脚本（10 模块，76 条判据），所有结论都由它给数值证据 |
| `VERIFY_REPORT.md` | 自检快照（FAIL/WARN/RULE 清单 + 两份完整输出） |
| `verify_results.json` | 结构化判定表 |
| `irf_ti64.csv` | Window A 的界面响应函数 `V(\Delta T)`，115 点，可直接喂给 CA |
| `thermal_layer.py` | **L1-T 层实现**：焓式能量方程 + 潜热（决策 D3 的交付） |
| `CALPHAD_REQUEST.md` | **CALPHAD 数据任务书**（决策 D1 的执行件，26 个量 + 填表模板） |
| `make_report.py` | 把两份原始输出整理成 `VERIFY_REPORT.md` |
| `ca3d.py` | **Window A：三维 CA 求解器**（形核 / V(dT) / 26 邻居捕获 / Scheil / 滑动窗口） |
| `verify_ca3d.py` | Window A 的 21 项三维验证判据 |
| `demo_ca3d_meltpool.py` | 三维熔池底部凝固算例（产出 VTK + 切片图） |
| `CA3D_REPORT.md` | **三维 CA 的实现与验证报告** |
| `results_ca3d/` | 三维结果（VTK / npz / 切片 PNG / 诊断） |
| `ca3d_solute.py` | **液相溶质输运**（三维，逐胞有限体积）：产出 c_L（枝晶间→Window C）与 c_S（核心→Window B） |
| `verify_ca3d_solute.py` | 溶质输运的 11 项三维判据 |
| `verify_ca3d_physics.py` | 物理正确性判据（IRF 有效区间 / 初始固相区 / CET / 取向淘汰）14 项 |
| `ternary_thermo.py` | **三元（Al+V）热力学闭合**（单一参数来源）：系线族 / 液相线恒等式 (★) / 分配矩阵 / Langmuir 竞争 |
| `_chk_ternary.py` | 三元闭合的**数值判据 T-A0..T-A11（33 项）** + 完整输出 `_chk_ternary.txt` |
| `TERNARY_COMPAT_AUDIT.md` | **Al+V 双溶质兼容性审计 + 修复台账**（含三个潜伏 bug 与一个 no-go）|
| `ca3d_project.py` | **投影算子 Pi**（胞平均 -> 胞内分布，逐胞精确守恒），含 5 项自检 |
| `pf1d_interface.py` | P1.1 第一次尝试（**无效实现，仅作失败诊断保留**） |
| `P11_SPEC.md` | **P1.1 规格书**（含失败诊断 + MOOSE 落点 + 验收标准） |

## 上游文档（现行路线）

| 文件 | 作用 |
|---|---|
| `pipeline/RESEARCH_INTENT.md` | **研究意图与路线的权威记录（2026-09-27 修订：Window B = 体相场 + Gibbs 面）** |
| `IMPLEMENTATION_PLAN.md` | 实施计划：阶段、判据、依赖、算力预算、风险 |
| `CALPHAD_REQUEST.md` | 热力学参数数据任务书 |
| `HYBRID_FRAMEWORK.md` | **Window B 的「体相场 + Gibbs 面」数学框架与判据** |

## 一分钟看懂结论

**框架自检 76 项：PASS 55 / WARN 7 / FAIL 6 / RULE 8**
**热层自检 11 项：PASS 11 / WARN 0 / FAIL 0**
**Window A（三维 CA）验证 21 项：PASS 20 / WARN 1 / FAIL 0**
**液相溶质输运验证 11 项：PASS 11 / WARN 0 / FAIL 0**
**物理正确性验证 15 项：PASS 14 / WARN 1 / FAIL 0**（WARN = T1d 诊断退化，已记账）
**P1.1：未完成**（第一次尝试在定义层面失败，诊断与规格见 `P11_SPEC.md`，计 0 项通过）
**三元（Al+V）闭合 33 项：PASS 33 / WARN 0 / FAIL 0**（`_chk_ternary.py`；含二元退化复现 §5.2 到 +0.013 K）
**投影算子 Pi 5 项：PASS 5 / WARN 0 / FAIL 0**（守恒 1.27e-16）
累计 **138 项**判据（框架 76 + 热层 11 + 三维 CA 21 + 溶质输运 11 + 物理 14 + Pi 5）

6 条 FAIL 全是"必须处理"的实质问题：
1. 凝固区间参数不自洽（本项目 17.9 K vs 文档 45 K）→ 已开 CALPHAD 任务书
2. 同上另一种表述（要凑 45 K 需 `\Delta H_f` 小 2.6 倍）
3. 潜热不可忽略（凝固区间内是显热的 18.6 倍）→ **已补上并验证**
4-6. 全域 PF 要可信需 `\Delta x\le48` nm；生产 `\Delta x=2` µm 欠解析 **42 倍**

**F4–F6 是新路线最有力的论据**：全域精细不可能，所以"CA + 局部 PF"不是权宜之计。
**Window A 的化学可严格退化为 Scheil**（`Fo_L=7.7`、`\alpha_{bd}=1.6\times10^{-3}`）⇒ 算子不学 Window A。

## 用户已定的 7 个决策（`MATH_FRAMEWORK.md` §14）

D1 CALPHAD ｜**D2（2026-09-25 改判）全窗口三元 Al+V**，准二元只作退化对照 ｜D3 补能量方程+潜热（**已完成**）｜D4 盒子 B `20^3` µm 可接受
｜D5 算子目标重定位 ｜D6 参数文献优先、无则理论推导 ｜D7 保留 NO-Solidification 槽位但本轮不实现

## 复跑

`
/root/miniconda3/envs/ml/bin/python verify_framework.py
/root/miniconda3/envs/ml/bin/python thermal_layer.py > _raw_thermal.txt
/root/miniconda3/envs/ml/bin/python make_report.py
`

（`thermal_layer.py` 也可直接跑，stdout 就是完整报告。）

## 注意

- 本目录**没有改动** `pipeline/RESEARCH_INTENT.md` 与生产输入 `pipeline/stage1_meltpool_c.i`
  （后者 SHA256 已复核未变）。新旧路线的差异清单见 `MATH_FRAMEWORK.md` §12 —— 待用户确认后再改。
- 所有参数带来源标签：L = 文献 / T = 理论 / A = 指派。
