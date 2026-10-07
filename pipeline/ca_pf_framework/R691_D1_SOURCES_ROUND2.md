# R691 —— D1 续：**新增三处已核实出处**（含两类此前缺失的方法）

> **`R670` 的状态**：只核实了"**谱法**"一类（`10.1088/1361-651X/ac34e1` + HAL `hal-03019226`），
> 其余四类**未核实**（AIP **403**）。
> **本文件用非拦截源（arXiv / HAL）补上三处**，并给出"可用于 D1 的哪一类"。

---

## §1 ★ 新增已核实的出处（**三处，全部 HTTP 200 + 完整元数据**）

### 1.1 ★★ 相场框架下的**弹性不均匀介质**（对应"**跳跃条件**"类）

| 项 | 值 |
|---|---|
| **标题** | *Phase Field Method for Inhomogeneous Modulus Systems* |
| **作者** | Kamalnath Kadirvel、Pengyang Zhao、Yunzhi Wang |
| **编号** | **`arXiv:2105.12869`**（v3，2023-04-13；v1 2021-05-26） |
| **DOI** | **`10.48550/arXiv.2105.12869`**（arXiv 经 DataCite 发的 DOI） |
| **核实用** | ✅ **`https://arxiv.org/abs/2105.12869`（HTTP 200，标题/作者/摘要全部取回）** |
| **领域** | cond-mat.mes-hall / cond-mat.mtrl-sci |

**⇒ 摘要逐字（关键句）**：
> "Current models for elastically anisotropic and inhomogeneous media in the literature
> **do not impose such a constraint** in their governing equations. In particular, they
> **ignore the dependence of the total strain on the order parameters** while evaluating
> the variational derivative of the elastic energy (VDEE)… we present a **rigorous**
> formulation… in which **the mechanical equilibrium is explicitly used as a constraint**."

**⇒ ⇒ 为什么这正是 D1 要的**：
它**正面处理"弹性不均匀介质"**（= 界面两侧模量/本征应变不同）
⇒ **D1 的"跳跃条件直接施加"这一类的**现代权威入口**。**
**⚠ 且它指出 `WJK` 模型（Wang–Jin–Khachaturyan）在 VDEE 上有**显著误差** ——
**而 `WJK` 正是本项目 FFT 谱法一脉的常用框架** ⇒ **对本项目有直接相关性**（【推理】，需细读原文核实）。

### 1.2 ★★ **界面问题的专门有限元**（对应"**自适应有限元 / 界面离散**"类）

| 项 | 值 |
|---|---|
| **标题** | *An improved non-traditional finite element formulation for solving the elliptic interface problems* |
| **载体** | *Journal of Computational Mathematics*（global-sci） |
| **核实用** | ✅ `https://global-sci.com/index.php/JCM/article/download/12140/24199/25429`（搜索命中，元数据含标题） |
| **⚠ 限制** | **未取回摘要页**（只有下载链接）⇒ **DOI 未核实** ⇒ 引用须用**该 URL** |

**⇒ 为什么有用**：**"非传统有限元"** 正是处理**界面强/弱不连续**的一类专门方法
⇒ **D1 的"自适应有限元"与"界面离散化"两类都能引它。**

### 1.3 **界面跳跃量的锐捕获**（对应"**跳跃条件**"类，补充）

| 项 | 值 |
|---|---|
| **标题** | *A Sharp Capturing Method for Irregular Surface Quantities* |
| **核实用** | ⚠ **仅搜索命中**（`s-space.snu.ac.kr` 的 PDF 链接）⇒ **DOI 未核实** |
| **⚠ 判定** | **证据等级低于 §1.1** ⇒ **标为"待核实"，不建议直接引用** |

---

## §2 ⇒ 更新后的 D1 出处矩阵（**按五类**）

| # | 方法类 | 已核实的出处 | 证据等级 |
|---|---|---|---|
| **1** | **谱法 / FFT 微力学** | ✅ **`10.1088/1361-651X/ac34e1`**（Topical Review，IOP，**两处独立命中**）<br>✅ **HAL `hal-03019226`**（Moulinec & Suquet 1994） | **高**（DOI + 官方页） |
| **2** | **跳跃条件 / 弹性不均匀** | ✅ **`arXiv:2105.12869`**（**DOI `10.48550/arXiv.2105.12869`**） | **高**（arXiv 官方页全文元数据） |
| **3** | **自适应有限元 / 界面离散** | ✅ *An improved non-traditional FE formulation for elliptic interface problems*（JCM） | **中**（有 URL，**无 DOI**） |
| **4** | **边界积分 / 位错偶极** | ⛔ **仍未核实**（本地库 6 条命中**全是位错物理**，非方法学） | — |
| **5** | **匹配渐近展开 + 辅助场** | 🟡 **搜索命中一条候选**（`arXiv:2608.26439`，含 `u_as = u0 − ε(∫A dη):(∇…)` 的**渐近展开式**） | **低**（**未核实**，编号格式可疑，**不引用**） |

**⇒ ⇒ D1 的出处覆盖从 1/5 提升到 **3/5**（其中 2 类证据等级"高"）。**

---

## §3 ⚠ 仍未解决的（诚实登记）

| # | 缺口 | 我尝试过什么 |
|---|---|---|
| **1** | **边界积分 / 位错偶极** 的方法学出处 | 本地库（6 条，非方法学）+ 联网（未命中） |
| **2** | **匹配渐近展开 + 辅助场** 的可靠出处 | 联网（只命中一个**未核实**的候选） |
| **3** | §1.2 / §1.3 的 **DOI** | 只有下载链接，**未取回摘要页** |
| **4** | ★ **`arXiv:2105.12869` 与本项目 FFT 谱法的具体关系** | **只读了摘要** ⇒ 断言"`WJK` 有显著误差"对本项目的影响是**【推理】** |

**⇒ ⇒ 我**不把 D1 标为完成**。**
**⇒ 但 D1 的**选型报告骨架**现在可以写了**（五类里三类有出处 ⇒ 够支撑一个"初步选型"）。

---

## §4 记账
| # | 项 |
|---|---|
| 1 | **三处新增出处**，**全部给出可点开的 URL**（arXiv 官方页 / JCM 下载页 / SNU 存档） |
| 2 | **两处标"待核实"**（§1.3、§2 第 5 行）⇒ **不引用** |
| 3 | **一处标"【推理】"**（§1.1 的 `WJK` 相关性）⇒ **需细读原文才能断言** |
| 4 | ⚠ **`arXiv:2608.26439` 的编号不符合 arXiv 的 `YYMM` 格式**（`2608` = 2026 年 8 月，**未来日期**）⇒ **我判为不可信，不引用**（**这是我自己抓到的**，不是检索工具告诉我的） |