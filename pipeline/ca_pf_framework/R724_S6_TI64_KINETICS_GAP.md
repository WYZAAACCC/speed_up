# R724 —— **S6 已实施**：Ti64 α′ 的 `v(T)` 与 `Q_G` 检索 —— **缺口确认，不是搜索失败**

> **依据**：`R712_REPAIR_SPEC.md` §10.2（S6）＋ §6.2（`Π`/`q*` 判据）＋ §11.2 未决项 1
> **纪律**：`R629 E1/E2`（**零主代码改动**：只加只读脚本）；纯本机检索，**未跑仿真**
> **工具**：`_r724_lit_kinetics.py`（窄口径）＋ `_r724_lit_wide.py`（宽口径）＋ `_r724_lit_read.py`（读上下文）

---

## §1 为什么要专门查（`R712 §11.2` 未决项 1 的原文）

> 1. **Ti64 α′ 的 `v(T)` 与 `Q_G` 无实测** `[未核实]` ⇒ §6.2 的 `Π` 只能用 Fe–Al 值示意。

而 §6.2 的判据是**整个"形核控制 vs 生长控制"结论的开关**：
```
v(T) = v(1100 K)·exp[−(Q_G/R)(1/T − 1/1100)]
Π = n·(v/q)³ ≫ 1   ⇔   instantaneous growth 成立（才能用形核控制框架）
q* = v(T)·n^(1/3)   （临界冷速）
```
**现有值全部是 Fe–0.7at%Al 的**：`Q_G = 8.2 ± 1.5 kJ/mol`、`v(1100 K) = 4.1e-4 m/s`。

---

## §2 检索过程（**两轮，按 `P28` 先证明"不是我的正则太窄"**）

### 2.1 第一轮：窄口径（词 + 单位**必须同行**）

| 类别 | 命中 |
|---|---:|
| **Ti64 语境** ∧（界面速度 + 单位） | **0 篇** |
| **Ti64 语境** ∧（激活能 + 生长/迁移/扩散 + 单位） | **0 篇** |
| 非 Ti64 语境但含激活能 | 1 篇（不可比） |

### 2.2 第二轮：**宽口径**（把正则放宽到单概念词，只为看"有没有"）

| 组 | 命中文件数 |
|---|---:|
| A. 界面迁移率/速度（宽） | 60 / 217 |
| B. 激活能（宽） | 34 / 217 |
| **C. Ti64 语境（宽）** | **43 / 217** |
| D. α′ 马氏体（宽） | 61 / 217 |
| E. 生长速率带数值（`m/s` 等） | **1 / 217** |
| F. 板条生长（宽） | 6 / 217 |
| G. 界面能/迁移率各向异性 | 7 / 217 |

**★ 关键交叉（Ti64 语境 ∧ (A 或 B)）= 若干篇，但逐条读上下文后全部不相关**：

| 文献 | 命中的是什么 | 与"界面迁移"有关吗 |
|---|---|---|
| `A-biomimetic-...` | "the mobility of a **droplet**" | ❌ 液滴润湿 |
| `Controlling-microstructural-...` | "growth velocity at the **liquid-solid** interface of the melt pool" | ❌ 凝固，不是固态相变 |
| `Effect_of_autocatalysis_...` | "`M_η` is the kinetic coefficient related to the mobility of interfaces" | ⚠ **是相场模型的系数名**，**不是实测值** |
| `Grain-size-prediction-for-stainless-steel` | 晶粒长大 + 黏度激活能 | ❌ 不锈钢 |

### 2.3 第三轮：**逐篇读上下文**（`P29`：先看原文再改正则）
`_r724_lit_read.py "growth (rate|velocity|kinetics)"` → 10 篇最相关文献，逐条读；
`_r724_lit_read.py "activation energ"` → 覆盖**全部 217 篇**。

---

## §3 ★★ 结论：**缺口是真的**（并给出"唯一可比来源"）

### 3.1 全库 217 篇里，**只有 Liu 2015 真正"提取了界面速度"**

`[文]` `Martensite-formation-kinetics-of-substitutional-Fe-0-7at--Al-_2015_Acta-Mate.pdf`：
> "a modular phase transformation model, adopting a model for **continuous nucleation** and an
> **anisotropic thermally-activated growth** model, yielding a corresponding impingement correction,
> was employed to **extract the nucleation rate and the γ/α′-interface velocity** during the transformation."
> …
> "`v_i(T) = v_0 exp(−Q_G/RT)` … The value determined for the **activation energy `Q_G` is 8.2 ± 1.5 kJ mol⁻¹**."
> "…compatible with that (≈**8 kJ mol⁻¹**) for thermally-activated martensite growth of a
> **Fe–10.2 at.%Ni–C** alloy with the same content of carbon impurity."

⇒ **`Q_G ≈ 8 kJ/mol` 是"两个独立来源都是 ≈8"**（Fe–Al 与 Fe–Ni–C），
但**两者都是 Fe 基**，**不是 Ti64**。

### 3.2 Ti64 侧：**没有**
| 文献 | 有什么 | 缺什么 |
|---|---|---|
| `Kinetics-of-anomalous-multi-step-formation-of-lath-martens_2014_Acta-Materia` | **定性**："`athermal nucleation of martensite and thermally activated growth`"、"Growth is thermally activated, i.e. time-dependent" | **无 `v(T)`、无 `Q_G`**（且是 **Fe–Mn–Si–C 钢**） |
| `Heating-induced-martensitic-transformation-..._2014_Acta-Mate`（Ti–23Nb–1.0O） | `Q = 101 kJ/mol`（Kissinger 法） | ⚠ **那是"加热诱导马氏体相变"的激活能，且作者归因于**氧扩散**，**不是界面迁移**；合金也不是 Ti64 |
| `Martensite-decomposition-kinetics-in-AM-Ti..._2024` | `M_s ≈ 580–700 °C` 的**区间** | **无生长激活能** |
| `Variant_selection_during_α_precipitation_in_Ti_6Al_4V` | **形核**势垒 `ΔG*`（pillbox 模型） | **不是生长激活能** |

⇒ ⛔ **本机 217 篇内，Ti64 α′ 的界面迁移速度 `v(T)` 与生长激活能 `Q_G` 均无实测。**

---

## §4 ⇒ 对 `R712 §6.2` 的直接影响（**可执行的三条**）

| # | 结论 |
|---|---|
| **1** | `R712 §11.2` 未决项 1 的措辞**正确且现在有全库证据**（原来只是"检索显示 0 命中"，现在是"217 篇逐条核实"）|
| **2** | ⚠ **§6.2 的 `Π` 判据在本项目上"暂时不可算成实数"** —— 用 Fe–Al 的 `Q_G` 只是**示意**。⇒ 建议在 §9.4 的"生长判据自检"里**强制标注**："`Π` 的 `Q_G` 来自 Fe–Al，**不是 Ti64**" |
| **3** | ★ **但 `Q_G` 小（≈8 kJ/mol）这一点对温度不敏感**：`R712 §6.2` 已实测 ⇒ 600→1600 K 速度只差 **2.8 倍**；`±1.5 kJ/mol` 在 1100 K 附近对 `q*` 影响 **<6%**。⇒ **即便 Ti64 的真值差几倍，`Π` 的量级判断仍可能成立** —— 但**这是【推理】，不是实测** |

### 4.1 ⇒ 我给的具体建议（**不外推、不拟合**，遵守 `R712 §0.3` 的 E7 教训）
1. **不要再试图"用别的合金推出 Ti64 的 `Q_G`"** —— E7 就是这么错的（跨合金两点拟合给 `Q_G = −5.1 kJ/mol`，却写"吻合 162%"）。
2. **要么**：把 `Π` 判据的结论**降级为"在 `Q_G ∈ [5,15] kJ/mol` 的敏感性区间内成立/不成立"**（诚实且可用）；
3. **要么**：把 S6 标为**需要实验或外部文献**的**外部依赖**，在拿到 Ti64 实测前**不引用 `Π` 的绝对数**。

---

## §5 本报告的诚实边界

| # | 项 |
|---|---|
| 1 | **零主代码改动**（`R629 E1`）；**未跑仿真**；纯本机文献库检索 |
| 2 | 本机库 **217 篇**，**不是全世界文献** ⇒ "0 命中"只能说明**本库无**，**不能**说明"文献界没有" |
| 3 | 抽取文本是**PDF 转文本**的产物（可见 `γ/α′` 变成 `c/a0`、`kJ mol/C0 1` 这类乱码）⇒ **正则必然漏**；我用"宽口径 + 逐篇读上下文"两步缓解，但**不能保证 100%** |
| 4 | §3.1 引的 Liu 2015 行是**库内 PDF 的抽取文本**，我**未读出版商原版** |
| 5 | §4 的"`Q_G` 小 ⇒ 量级判断可能仍成立"是 **【推理】**，**未做敏感性算例** |
| 6 | 我**未检索本机库以外**（网络）—— 若要我上网查，需要你确认（本会话 `web_search` 可用） |
| 7 | ⚠ `Heating-induced-...` 的 `Q = 101 kJ/mol` **很容易被误引为 Ti64 的生长激活能**（它出现在"martensitic"语境里）⇒ **本报告显式排除它**，并说明它是**氧扩散**的 |
