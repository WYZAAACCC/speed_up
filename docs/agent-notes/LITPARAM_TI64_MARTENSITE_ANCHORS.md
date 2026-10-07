# Ti-6Al-4V β→α′ 文献参数锚点（动力学与热学）

> 采集日期：本轮会话。**采集通道受限**：本会话 `web_fetch` 对**所有**主机名返回
> `Error: URL hostname "..." resolves to a non-public IP address`（DNS 被解析到非公网地址），
> PowerShell 返回 `write EPIPE`。**唯一可用工具是 `web_search`**，它只能返回
> 「源标题 + 被检索命中的原文片段」。⇒ **本轮未读到任何一篇原文全文。**
> 所有数字均为**片段级**证据，标注 `【片段】`；未能取到的一律标 `【未核实】`。

---

## 1. M_s / M_f 与成分、冷速依赖

| 量 | 值 | 来源 | 备注 |
|---|---|---|---|
| M_s (Ti-6Al-4V) | **842 °C = 1115 K**【片段】 | https://www.sciencedirect.com/science/article/pii/S223878542302834X | 原文片段：`critical cooling rate above 410 °C s⁻¹ and a Ms of 842 °C [24,64,65]`。**该值偏高**，疑与氧含量/高纯组织有关 |
| 临界冷速（形成 α′） | **> 410 °C/s** ≈ 683 K/s【片段】 | 同上 | — |
| β transus | **995 °C = 1268 K**【片段】 | 近 α/α+β 钛合金 T_β 汇总表 https://core.ac.uk/download/222968113.pdf | 与项目给定值一致 |
| M_s 对成分依赖 | **【未核实】** | — | 本轮**未取到** Ti-6Al-4V 的 V/Al 定量系数。物理方向（V、Al 均为 β 稳定元素 ⇒ 降低 M_s）为教科书共识，但**无 URL 数值** |
| M_s 对冷速依赖 | **【未核实】** | — | 仅取到「M_s 与冷速无关」的一般性陈述（西班牙语源 https://nuclea.cnea.gob.ar/bitstreams/1912f080-52de-4c4f-a481-f4564bc8665e/download ），**未取到 Ti-6Al-4V 专门实验** |

- 氧的影响有专文，但**数值未取到**：`On the transformation temperatures of Ti-6Al-4V: Effect of oxygen pick-up during Laser Powder Bed Fusion`
  https://www.sciencedirect.com/science/article/abs/pii/S1044580323006824
- **冲突未解决**：842 °C 是**高**值；文献常见「Ms 随 V 增加而下降」。二者不矛盾，但本会话无法给出该文成分与氧含量以判断可比性。

---

## 2. LPBF/SLM 冷速与 t_cool

| 量 | 值 | 来源 | 备注 |
|---|---|---|---|
| 冷速范围 | **10³–10⁸ K/s**【片段】 | https://scholarworks.sjsu.edu/cgi/viewcontent.cgi?article=9096&context=etd_theses | 原文片段 `high cooling rates (10⁻³-10⁻⁸ K/s)`。⚠ **上标丢失**：字面读作 10⁻³–10⁻⁸，物理上应为 **10³–10⁸ K/s** |
| 实测/模拟冷速（LPBF 其他合金） | **7×10⁴ – 5×10⁵ K/s**（Al-33Cu）【片段】 | http://publications.rwth-aachen.de/record/992525/files/992525.pdf | 明确标注 `Experiment`。**非同种合金**，仅作量级参照 |
| Ti6Al4V 热动力学 | 未取到数值 | https://doi.org/10.1038/s41598-020-63281-4 | 该文正是 LPBF Ti6Al4V 热动力学计算，**全文未读到**【未核实】 |
| Melt pool 冷速 | 未取到数值 | https://spiral.imperial.ac.uk/server/api/core/bitstreams/49ae8804-9fc7-4ca2-af88-cf9736245261/content | `Melt pool temperature and cooling rates in laser powder bed fusion`，**全文未读到**【未核实】 |
| **代表冷却曲线段** | **未取到** | — | 任务要求的「从 995 °C 到室温的逐点温度-时间段」**本轮完全未取到**。这是最大缺口 |

**t_cool 只能由冷速区间推算**【推理，非文献直引】：
t_cool = (1268 − 293) K / q̇，跨 ΔT = 975 K
- q̇ = 10³ K/s ⇒ t_cool ≈ **0.98 s**
- q̇ = 10⁶ K/s ⇒ t_cool ≈ **0.98 ms**
- q̇ = 10⁸ K/s ⇒ t_cool ≈ **9.8 µs**

⇒ 可用窗口 **0.98 s ↔ 9.8 µs，跨 5 个数量级**。这直接决定第 6 节答案的区间宽度。

---

## 3. 界面迁移率 M 与板条生长速度

| 量 | 值 | 来源 | 备注 |
|---|---|---|---|
| 马氏体生长速度（一般性） | **与**剪切波速/声速**可比**（"velocities comparable to the speed..."）【片段】 | https://www.nature.com/articles/s41524-024-01499-w.pdf | 片段被截断，**具体数值范围未取到** |
| 马氏体生长速度（钢，经典实验） | **未取到数值** | `Rate of Propagation of Martensite` https://onemine.org/files/get/300-000-016-538.pdf ；Fe-30Ni 定量测量 https://doi.org/10.1007/bf02663194 （Bunshah & Mehl / Beisswenger & Scheil / Mukherjee 被引于 https://www.jstage.jst.go.jp/article/isijinternational1966/15/4/15_175/_pdf/-char/en ） | 经典测量确实存在且被广泛引用，但**数值本轮未取到** |
| β→α 界面迁移率 M（Ti） | **未取到数值**【未核实】 | `Coherent and semicoherent α/β interfaces in titanium: structure, thermodynamics, migration` https://ar5iv.labs.arxiv.org/html/2311.02897 （亦见 npj Comput. Mater. https://doi.org/10.1038/s41524-023-01170-w ）；`Dislocation-mediated migration of the α/β interfaces in titanium` https://doi.org/10.1016/j.actamat.2023.119364 | **这两篇最可能就是 M 的直接来源，但本会话无法读取正文** |
| α′ 是否为 athermal | **是**（一般性）：`nucleation controlled, which presupposes that growth of the martensite units is instantaneous`【片段】 | https://backend.orbit.dtu.dk/ws/files/375796314/PhD_Thesis_Basit_Ali.pdf | 钢的博士论文语境；Ti 专门证据【未核实】 |

---

## 4. Athermal vs isothermal

- 有支持性片段（见上，DTU 博士论文；另有 http://arxiv.org/pdf/cond-mat/0601569 关于 MT 微观动力学分类的讨论），
  但**均为普适/钢的语境**。
- **Ti-6Al-4V α′ 专门的 athermal 证据本轮【未核实】**。
- 一个**反向信号**（值得记账）：LPBF Ti6Al4V 中在 α′ 板条**内部**观测到
  **纳米尺度 V 偏聚（nanoscale vanadium clustering）**，并被描述为
  `A transition from diffusion-limited phase transformation to kinetic-limited phase transformation`
  —— https://www.tandfonline.com/doi/full/10.1080/21663831.2020.1772396
  ⇒ 说明**板条形成之后**仍有极短程的 V 再分配。这不推翻 athermal 形核控制，
  但意味着「完全无扩散」在 LPBF 时间尺度上需要打折扣。

---

## 5. α′ 相场/level-set 模拟

**全部【未核实】——本轮未取到任何一篇的 M 取值。** 但已定位到若干**很可能含 M 的目标**：

| 目标 | URL | 为什么值得追 |
|---|---|---|
| Boccardo, Zou, … Panwisawas, *Martensite decomposition kinetics in AM Ti-6Al-4V: in-situ + phase-field* | https://doi.org/10.1016/j.matdes.2024.113112 ；预印本 https://ar5iv.labs.arxiv.org/html/2404.09806 | 唯一明确的 **Ti-6Al-4V 马氏体相场**论文 |
| `Table 1. Material properties of Ti6Al4V alloy adopted for the phase field` | https://iris.polito.it/retrieve/handle/11583/2980970/662698 | 整张参数表 |
| 开源复现：6 变体单 prior-β 晶粒内马氏体相场（MATLAB） | https://github.com/akihoo/phase-field-simulation-of-Ti-6Al-4V---MT-about-6-variants-within-a-single-parent-grain | **与本项目 Window B 目标几乎同构**（单晶粒内 6 变体） |
| 相场参数表（Δx = 8 nm，含 interface width） | https://doi.org/10.1080/17452759.2025.2544759 | 有显式数值参数表 |
| Panwisawas 微观元胞自动机（DED Ti6Al4V 固态相变） | https://qmro.qmul.ac.uk/xmlui/bitstream/handle/123456789/101465/ | 含界面速度/迁移率标定 |

---

## 6. 核心问题：0.25 µm 厚 α′ 板条长 4 µm 需要多大界面速度？

### 6.1 纵向推进速度（决定"能否长到 4 µm"）

v = L / t_cool，L = 4 µm = 4×10⁻⁶ m，t_cool 取自第 2 节：

| q̇ (K/s) | t_cool (s) | v = 4 µm / t_cool |
|---|---|---|
| 10³ | 0.975 | **4.1×10⁻⁶ m/s** |
| 10⁶ | 9.75×10⁻⁴ | **4.1×10⁻³ m/s** |
| 10⁸ | 9.75×10⁻⁶ | **0.41 m/s** |

**⇒ 所需界面速度区间 ≈ 4×10⁻⁶ – 4×10⁻¹ m/s（跨 5 个数量级）。**

### 6.2 与检索到的速度值比对

- 检索到的唯一速度性陈述是「马氏体形成速度**与剪切波速可比**」（Nature npj Comput. Mater.）。
  Ti 剪切波速 ~3×10³ m/s（**量级引用，非本会话取得**）⇒ 该陈述给出 ~10²–10³ m/s 量级。
- 所需速度**上界 0.41 m/s 比之低 3–4 个数量级**；**下界 4×10⁻⁶ m/s 低约 9 个数量级**。
- **⇒ 所需速度与「马氏体板条生长极快」的判断完全一致：即使取最苛刻的 10⁸ K/s 冷速，
  4 µm 的纵向推进也只需 0.41 m/s，远低于马氏体界面所能达到的速度。纵向推进不构成瓶颈。**

### 6.3 增厚速度（决定"能否增厚到 0.25 µm"）

两个自由面同时推进 ⇒ v_thick = (w/2)/t_cool，w = 0.25 µm：

| q̇ (K/s) | v_thick |
|---|---|
| 10³ | **1.3×10⁻⁷ m/s** |
| 10⁶ | **1.3×10⁻⁴ m/s** |
| 10⁸ | **0.13 m/s** |

### 6.4 反推等效界面迁移率 M

用 v = M·ΔG/V_m（V_m(Ti) ≈ 1.06×10⁻⁵ m³/mol，**标准值，非本会话取得**）：

- 取 ΔG = 10² J/mol ⇒ ΔG/V_m = 9.4×10⁶ Pa
- 取 ΔG = 10³ J/mol ⇒ ΔG/V_m = 9.4×10⁷ Pa

M_required = v / (ΔG/V_m)：

| 工况 | v (m/s) | M @ΔG=10² (m·s⁻¹·Pa⁻¹) | M @ΔG=10³ |
|---|---|---|---|
| 纵向, 10³ K/s | 4.1×10⁻⁶ | **4.4×10⁻¹³** | 4.4×10⁻¹⁴ |
| 纵向, 10⁸ K/s | 0.41 | **4.4×10⁻⁸** | 4.4×10⁻⁹ |
| 增厚, 10⁶ K/s | 1.3×10⁻⁴ | **1.4×10⁻¹¹** | 1.4×10⁻¹² |

**⇒ 所需 M 落在 ~10⁻¹³ – 10⁻⁸ m·s⁻¹·Pa⁻¹。**
这个量级与固–固相变相场模拟常用的 mobility 区间是**相容的**（【推理】，
未取得 Ti 的直接文献值 ⇒ 不能当作已验证结论）。

### 6.5 结论

1. **纵向 4 µm 与横向 0.25 µm 在整个 LPBF 冷却窗口内都只需 10⁻⁶ – 10⁻¹ m/s 量级的速度**，
   这比 athermal 马氏体界面**实际能跑的速度慢 3–9 个数量级**。
2. ⇒ **生长不是限制环节。** 最终板条厚度由**形核密度 + 相互碰撞（impingement）**决定，
   而不是由生长动力学决定 —— 这与第 4 节 athermal 判据一致。
3. **对 Window B 建模的直接含义**：把 α′ 生长当作**瞬时**（nucleation-controlled，
   v → ∞ 或 v = v_max）在物理上是安全的；需要标定的量是
   **形核率/形核密度与变体选择规则**，而不是界面迁移率 M。
   M 只在需要「板条增厚速率有限」这一细节时才进入模型。
4. ⚠ **本结论建立在「冷速区间 10³–10⁸ K/s」这一个片段级数字上**。
   若实际 LPBF 冷速上限只有 ~10⁶ K/s（更接近实测值），则所需速度上限降到
   4×10⁻³ m/s，结论**更强**。

---

## 7. 汇总表

| quantity | value | units | source URL | confidence |
|---|---|---|---|---|
| M_s (Ti-6Al-4V) | 842 (= 1115 K) | °C | https://www.sciencedirect.com/science/article/pii/S223878542302834X | 中（片段直引，但与常见值冲突） |
| 临界冷速（得 α′） | > 410 (> 683 K/s) | °C/s | 同上 | 中 |
| β transus | 995 (= 1268 K) | °C | https://core.ac.uk/download/222968113.pdf | 高 |
| M_f (Ti-6Al-4V) | — | — | — | 【未核实】 |
| M_s–成分 (V, Al) 定量式 | — | — | — | 【未核实】 |
| M_s–冷速 定量关系 | — | — | — | 【未核实】 |
| LPBF/SLM 冷速 | 10³–10⁸（原文上标丢失） | K/s | https://scholarworks.sjsu.edu/cgi/viewcontent.cgi?article=9096&context=etd_theses | 中 |
| 实测冷速（Al-33Cu LPBF，参照） | 7×10⁴ – 5×10⁵ | K/s | http://publications.rwth-aachen.de/record/992525/files/992525.pdf | 中（异种合金） |
| t_cool（推算） | 0.98 s – 9.8 µs | s | 【推理，由上式冷速算得】 | 【推理】 |
| 代表冷却曲线段 | — | — | — | 【未核实】 |
| 马氏体生长速度（一般性） | "comparable to shear wave speed" | m/s | https://www.nature.com/articles/s41524-024-01499-w.pdf | 低（数值被截断） |
| β→α 界面 M（Ti） | — | m·s⁻¹·Pa⁻¹ | https://doi.org/10.1038/s41524-023-01170-w | 【未核实】 |
| α′ athermal（形核控制） | "growth … instantaneous" | — | https://backend.orbit.dtu.dk/ws/files/375796314/PhD_Thesis_Basit_Ali.pdf | 中（普适/钢语境） |
| Ti-6Al-4V α′ 相场 M 取值 | — | — | https://doi.org/10.1016/j.matdes.2024.113112 | 【未核实】 |
| **所需纵向速度（4 µm）** | 4.1×10⁻⁶ – 0.41 | m/s | 本报告 §6.1 算术 | 【推理】 |
| **所需增厚速度（0.25 µm）** | 1.3×10⁻⁷ – 0.13 | m/s | 本报告 §6.3 算术 | 【推理】 |
| **所需等效 M** | ~10⁻¹³ – 10⁻⁸ | m·s⁻¹·Pa⁻¹ | 本报告 §6.4 算术 | 【推理】 |

---

## 8. 未完成事项（供接手）

**唯一障碍是网络**。若在 `web_fetch` 可用的环境重跑，按此顺序即可补齐：
1. `/doi/10.1016/j.matdes.2024.113112` 与 `ar5iv 2404.09806` → Ti-6Al-4V 马氏体相场 M 与板条厚度/速度
2. `iris.polito.it/.../662698` → 相场参数表
3. `github.com/akihoo/...` → 单晶粒 6 变体相场实现
4. `ar5iv 2311.02897` / `doi 10.1038/s41524-023-01170-w` → Ti α/β 界面迁移率
5. `s41598-020-63281-4` 与 `spiral.imperial.ac.uk/.../49ae8804` → **真实冷却曲线段**
6. `S1044580323006824` → M_s 的氧依赖（可解决 842 °C 的冲突）
