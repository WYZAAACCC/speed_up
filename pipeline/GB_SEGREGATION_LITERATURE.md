# Ti64 晶界溶质偏析：定量参数文献调研

> 调研日期：2026-09-19
> 起因：用户决定「Phase 3 的偏析参数先查文献；查不到就出一份『需要查什么』的清单，我让别人去查」。
> 目标体系：**Ti-6Al-4V，β 相，T ≈ 1900–2000 K**（LPBF 熔池刚凝固）
> 目标量：`Γ_GB`、`s·δ·D_GB`、富集因子 `s = c_GB/c_bulk` 及其温度依赖
>
> ⚠ **可信度分级**：本报告中标为「已取得」的数值，其表格来自出版社官方端点、逐项核对过；
> 其余文献只核对了**著录信息与摘要**。凡未取得的数值一律显式标为「未取得」，
> **没有用相似体系的数据冒充 Ti64**。

---

## 0 摘要

### 0.1 已找到、可直接用作标定目标的

| 量 | 值 | 体系 / 温度 | 出处 |
|---|---|---|---|
| **V 的 Gibbs 界面过剩** | **+2.2 ± 0.1**（10 mm 试样）/ **+5.3 ± 0.4**（20 mm）**at·nm⁻²** | EBM Ti64，**923 K** | Tan 2016 |
| **Al 的界面过剩（贫化）** | **−4.3 ± 0.3 / −7.0 ± 0.5 at·nm⁻²** | 同上 | Tan 2016 |
| 偏析引起的界面能变化 `ΔE_tot` | V：−28.0 / −67.5 mJ·m⁻²；Al：+54.8 / +89.2 mJ·m⁻² | 同上 | Tan 2016 |
| **α/β 分配比** | Al **3.4–4.1**；V **8.9–10.7**；Fe ≈ 20.5 | EBM Ti64 | Tan 2016 |
| `Q_gb / Q_bulk` 经验比 | **≈ 0.6**（hcp 第 IV 族） | α-Ti / α-Zr / α-Hf | Herzig 2002 |
| α-Ti 晶界扩散三重积 | 有 Arrhenius 表达式（473–873 K，B 型动力学） | **Co** 在 α-Ti（不是 Al/V） | Popov 2025 |

**单位换算（可直接写进模型）**：1 at·nm⁻² = **1.661×10⁻⁶ mol·m⁻²**。
⇒ V 的 `Γ_GB` = **3.7×10⁻⁶ ～ 8.8×10⁻⁶ mol·m⁻²**；Al 为 **−7.1×10⁻⁶ ～ −1.16×10⁻⁵ mol·m⁻²**。

### 0.2 明确**没**找到的（这是本报告同等重要的另一半）

1. **Al、V 在 β-Ti（bcc）晶界上的偏析焓 `ΔH_seg` 数值** —— 有两篇论文算过
   （Song 2025 的 48 元素 β-Ti Σ5(310)；Scheiber 2024 的高通量数据库含 Ti），
   但**数值都在付费墙后的表格里**，本轮未取得。
2. **偏析熵 `ΔS_seg`** —— 除 Tuchinda/Schuh 的 MLP 谱数据库外，**Ti 体系没有公开数值**。
   ⚠ 而**高温外推对它最敏感**，这是最大的隐患。
3. **Al、V 在 Ti 晶界中的 `D_GB` 与三重积** —— **一篇都没有**。
   Ti 晶界扩散的实测数据全是 **Ti 自扩散**和 **Co/Fe/Ni** 这类快扩散元素。
4. **β-Ti（bcc）晶界的扩散数据** —— **完全空白**（α-Ti hcp 有，bcc 没有）。
5. **Ti64 同相晶界上富集因子 `s` 的实测数值** —— 定性结论有（V 富集、Al 贫化），
   **数值未取得**。

---

## 0.3 ★ `Ω₀` 应该等于什么 —— 有理论公式，且能反推出数值（2026-09-19 增补）

> 本节回答用户问题（3）。**结论：有理论公式，不需要再查文献就能定出量级；
> 但当前生产值大了约两个数量级。**

### 0.3.1 理论公式：Cahn 1962 的相互作用势

Cahn 把晶界当成一块**有限厚度、带相互作用势 `E(x)` 的板**，稳态平衡分布为

```
c(x)/[1−c(x)] = c_∞/(1−c_∞) · exp(−E(x)/k_B T)
```
（J. W. Cahn, *Acta Metall.* **10** (1962) 789,
[DOI 10.1016/0001-6160(62)90092-5](https://doi.org/10.1016/0001-6160(62)90092-5)）

相场里的标准对应写法是把这一项直接放进自由能：

```
F = ∫[ f_chem + c·E + (κ_c/2)|∇c|² + (κ_η/2)|∇η|² ] dV,    E = −m·λ·g(η₁…η_g)
```

**⇒ 我们的 `f_seg = (Ω₀/w_GB)·(c−c₀)·h_gb` 与 `c·E` 是同一件事**，逐项对照：

| 我们的量 | Cahn / 相场文献 | 含义 |
|---|---|---|
| `h_gb(x)` | `g(η₁…η_g)` | 晶界指示函数 |
| `Ω₀/w_GB` | 势幅值 `mλ` | 晶界中心的偏析势 |
| `c₀` 线性项 | 只移动能量零点，不改平衡 | — |

**映射公式（本节的核心交付）**：

```
Ω₀ = w_GB · ΔG_seg / v_m            （v_m = 摩尔体积, m³/mol）
⇔ 富集比  s = c_GB/c_bulk = exp(−ΔG_seg/RT)
```

**物理上更透明的等价写法**是把偏析项直接写成

```
f_seg = (ΔG_seg / v_m) · (c − c₀) · h_gb
```

这样模型在稀溶液极限下**精确复现 McLean 等温线**，而且**自带正确的温度依赖**
（见 0.3.5）。

> 相场实现与 Cahn 解析式对标的先例：Guin, Verma, Bandyopadhyay, Lo, Mukherjee,
> [arXiv:2308.08262](https://arxiv.org/abs/2308.08262)（全文可读，公式 (1)(7) 已提取）；
> 母模型 Heo, Bhattacharyya, Chen, *Acta Mater.* **59** (2011) 7800,
> [DOI 10.1016/j.actamat.2011.08.045](https://doi.org/10.1016/j.actamat.2011.08.045)。

**另一条独立的取数链条**（不依赖 Γ 实测）：**Eshelby 型弹性失配**，是唯一能"从可测量
直接算出 `ΔH_seg`"的闭式公式：

```
E_seg,el = −(V_A − V_B)² / ( (3/2)·V_A/G_A + 2·V_B/K_B ) + [晶界位点项]
```
（V = 原子体积，G/K = 剪切/体模量；出处 Scheiber, Pippan, Puschnig, Romaner,
*MSMSE* **24** (2016) 035013, [DOI 10.1088/0965-0393/24/3/035013](https://doi.org/10.1088/0965-0393/24/3/035013)。
bcc Ti-Mo Σ5 上的应用见 Umashankar et al., [arXiv:2503.03538](https://arxiv.org/abs/2503.03538)，
结论是**强偏析元素由弹性主导**；但 Al、V 与 Ti 的原子体积都接近
⇒ **弹性贡献可能很小，化学项不可省**。）

### 0.3.2 ⚠ 一个必须先纠正的量纲问题（差 10⁵ 倍）

`c` 是**摩尔分数（无量纲）**，所以实测后处理

```
gamma_gb = c_total − c_edge·L = ∫(c − c_far) dx
```

的单位是 **[m]，不是 mol/m²，也不是 mol/m**。要得到物理的 Gibbs 过剩**必须乘摩尔密度**：

```
Γ [mol·m⁻²] = ρ_mol · ∫(c − c_far) dx ,     ρ_mol(β-Ti) ≈ 1.01×10⁵ mol·m⁻³
```
（ρ_mol 由 Tan 2016 原文给的 ρ(β) = **61.0 at·nm⁻³** 换算，对应摩尔体积
9.9×10⁻⁶ m³/mol，与 Ti64 实测密度 4.43 g/cm³ 一致 —— **这是原文值，不是估算**。）

> ⚠ **两种错法分别落在文献值的两侧，所以"量级看起来对"纯属巧合**：
> 忘了乘 `ρ_mol` ⇒ 小 5 个数量级；直接当 mol/m² 读 ⇒ 比 Tan 小 1000 倍。
> **不能因为"量级差不多"就免检这一条。**

### 0.3.3 换算后：**当前 `Ω₀` 大了约两个数量级**

标定链（**已用模型自己的实测数字自洽校验**）：

```
Δc   = |Ω₀| / (w_GB · f_cc)                      ← 偏析项给的局域富集
∫h_gb dx = (4/3)·w_GB                            ← 解析推导（h_gb = sech⁴u）
⇒ Γ_len ≡ ∫(c−c_far)dx = (4/3)·|Ω₀| / f_cc       ← **与 w_GB 无关**（重标定生效）
⇒ Γ_phys = ρ_mol · Γ_len
⇒ **|Ω₀| = (3/4) · f_cc · Γ_target / ρ_mol**
```

**自洽校验**：取 `Ω₀ = −4.6e-9`、`f_cc ≈ 1.164` ⇒ `Γ_len = 5.27×10⁻⁹ m`。
而 VALIDATION_STATUS 里**实测**的偏析项单独贡献是 `4.79×10⁻⁹`（wGB=0.4 µm 的 `seg−noseg`）
⇒ **吻合到 9%**（差的是远场贫化）。推导链与实测对得上。

**对比文献锚点**：

| 量 | 值 |
|---|---|
| 模型 Γ（原始读数） | 4.8×10⁻⁹ m |
| **换算后** | **4.8×10⁻⁴ mol·m⁻² = 2.9×10² at·nm⁻²** |
| Tan 2016 的 V 锚点 | 3.7~8.8×10⁻⁶ mol·m⁻² = **2.2 ~ 5.3 at·nm⁻²** |
| **比值** | **大 55 ~ 133 倍** |

**直观校验**：β-Ti (110) 面单层位点密度 ≈ **12.9 at·nm⁻²**
⇒ Tan 的 V 过剩 = **0.17~0.41 个单层**（合理）；
模型给的是 **~16~23 个单层**（物理上不可能，纯粹是 400 nm 假宽度的产物）。

**反推 `Ω₀`**（`f_cc ≈ 1.164`、`ρ_mol = 1.01×10⁵`）：

| 目标 Γ_target | 需要的 `Ω₀` |
|---|---|
| V 的 2.2 at·nm⁻² | **−3.2×10⁻¹¹** |
| V 的 5.3 at·nm⁻² | **−7.6×10⁻¹¹** |

> ⇒ **`Ω₀ ≈ −(3~8)×10⁻¹¹`，工程上取 `−5×10⁻¹¹`。**
> **当前生产值 `−4.6×10⁻⁹` 是它的 60~150 倍。**

**温度修正（⚠ 量级估算，不是文献值）**：Tan 是 **923 K 的 α/β 相界面**，
我们要的是 **~1950 K 的 β/β 晶界**。按 McLean，若 `ΔG_seg ≈ −20 kJ/mol`，
富集比 `s` 从 923 K 的 ~13 掉到 1950 K 的 ~3.4 ⇒ **1950 K 下 `Ω₀` 可能还要再小 ~4 倍，
即 ~−1×10⁻¹¹**。方向明确：**当前值无论如何都大 2 个数量级以上。**

### 0.3.4 ⚠ 弥散模型**无法同时对上** `s` 和 `Γ` —— 必须选一个

| 刻画方式 | 模型（Ω₀=−4.6e-9） | 真实（Tan, 923 K） | 谁偏了 |
|---|---|---|---|
| **富集比 s** | 1.44（Δc ≈ 1 at%） | ~3~10 | **模型偏小 2~7 倍** |
| **Γ_GB** | 290 at·nm⁻² | 2.2~5.3 at·nm⁻² | **模型偏大 ~100 倍** |

两者**反向偏**，根因是同一个：**真实晶界 ~1 nm，模型 400 nm~4 µm**
（`w_model/w_real ~ 10²–10³`）。**这不是 `Ω₀` 一个数能同时修好的。**

**按本项目的立足点（`GB_SOLUTE_GOAL.md`：以积分量为标定目标）应标到 `Γ`**
⇒ **代价是模型的局域 `c` 剖面不再具有物理意义，论文里必须明写。**

### 0.3.5 另外三条必须记账的发现

1. **温度依赖完全缺失。** 现在 `f_loc` 里没有 `T`，`Ω₀` 是常数
   ⇒ 模型给出的富集比**与温度无关**。真实体系 923 K → 1950 K 要掉约 4 倍。
   **审稿人会问。** 修法就是 0.3.1：写成 `(ΔG_seg/v_m)(c−c₀)h_gb`，让 `ΔG_seg` 带 `T`。

2. **模型的自由能不具物理量纲**，所以 `Ω₀` **无法用量纲分析推出**。
   `f_loc = k_c/2(c−c₀)² + A_part·c²·S`，`k_c = 0.9`；
   而真实稀溶液 `f_cc = RT/(v_m·c(1−c)) ≈ 4.2×10¹⁰ J·m⁻³`
   ⇒ **`k_c` 比物理曲率小 10 个数量级**。
   （这与 **T13 实测「拖曳耦合比势垒弱 9 个数量级」自洽** —— 两条独立证据指向同一件事。）
   ⇒ **`Ω₀` 的绝对数值只能在模型自身的单位制内、通过可观测量 `Γ` 来标定**；
   想让它"等于某个文献 `ΔG_seg`"必须先重写 `f_loc`。

3. **`Ω₀` 的单位在文档里写错了。** `f_seg` 要与 `k_c/2(c−c₀)²` 同量纲，
   则 `Ω₀` 的单位是**自由能密度 × 长度**：若 `f` 是 J/m³ 则 `Ω₀` 是 **J/m²**；
   若 `f` 无量纲（本模型更接近这种）则是 **m**。
   **之前记的「J/m」两种读法都不满足**，建议改掉 —— 否则「`Ω₀` 的量级」这句话没有意义。

### 0.3.6 本节的证据等级（必须如实标注）

| 内容 | 等级 |
|---|---|
| Cahn 1962 公式形式、Guin 2023 相场映射、Eshelby 公式形式 | **文献直读** |
| Tan 2016 Table 2 全部数值、ρ(β)/ρ(α) | **文献直读，已从 Nature 开放获取原文核对** |
| `Γ_len` 的单位判定、`∫h_gb dx = (4/3)w_GB` 的推导、`Ω₀` 反推、温度修正、单层位点密度 | **本项目的推导/估算，不是文献值** |
| Al/V 在 β-Ti **晶界**的 `ΔH_seg`、`ΔS_seg`、`D_GB` | **查不到**，见 §5 缺口清单 E1–E6 |

---

## 1 晶界偏析热力学

### 1.1 Ti64 实测 Gibbs 界面过剩 —— 唯一拿到完整数值的来源

**Tan, Kok, Toh, Tan, Descoins, Mangelinck, Tor, Leong, Chua,
*Scientific Reports* **6** (2016) 26039, [DOI 10.1038/srep26039](https://doi.org/10.1038/srep26039)**
（**开放获取**）

电子束熔融（EBM）Ti64，APT + proxigram 分析 α/β 界面。论文用「相对 Gibbs 界面过剩」：

```
Γ_i^rel = (ρ/A) · Σ_p Δx · (c_i^p − c̄_i)
```

原子密度取论文原值 **ρ(β) = 61.0 at·nm⁻³，ρ(α) = 57.6 at·nm⁻³**。

**Table 2（原文数值，923 K）**

| 试样 | 溶质 | Γ (at·nm⁻²) | ΔE_tot (mJ·m⁻²) | w_α/β (nm) |
|---|---|---|---|---|
| 10 mm | **V** | **+2.2 ± 0.1** | −28.0 | 2.2 ± 0.1 |
| 10 mm | **Al** | **−4.3 ± 0.3** | +54.8 | — |
| 20 mm | **V** | **+5.3 ± 0.4** | −67.5 | 5.3 ± 0.4 |
| 20 mm | **Al** | **−7.0 ± 0.5** | +89.2 | — |

**Table 1（相成分，at%）**：α 相 Al 10.49 / V 2.65（10 mm），Al 9.41 / V 2.57（20 mm）；
β 相 Al 3.13 / **V 23.68**（10 mm），Al 2.32 / **V 27.43**（20 mm）。
分配比：**Al 3.4 / 4.1，V 8.9 / 10.7，Fe 20.5 / 20.9，O 1.7 / 2.1**。

> **重要限定**：这是 **α/β 异相界面**，**不是同相晶界**（α/α 或 β/β）。
> 论文明确说 V 在 β 侧形成 "bump"（因为 V 在 β 中扩散慢），Al 在界面贫化。

### 1.2 Ti64 同相晶界的实测 —— 有结论，无数字

**Breen, Davids, Chen, Mai, Nomoto, Cui, Liao, Primig, Ringer,
*Acta Materialia* **306** (2026) 121904,
[DOI 10.1016/j.actamat.2026.121904](https://doi.org/10.1016/j.actamat.2026.121904)**

**这是与需求最吻合的一篇**：E-PBF Ti64，correlative TKD + APT，
**直接量化晶界的 Gibbsian interfacial excess（V、Fe、Al）**，并配了第一性原理计算。
摘要结论（已核实原文摘要）：

- **V 和 Fe 富集，Al 贫化**；
- **V 的偏析随晶界取向差增大而增强**；
- 界面平面之间偏析有空间起伏，但**与晶界曲率无一致关联**；
- DFT（model α/α 晶界）确认了 V 富集 / Al 贫化的热力学偏好。

**具体数值未取得**：出版社版本 403；UNSW 机构库的 accepted manuscript PDF 字体子集损坏，
文本抽取与页面渲染都是乱码。**这是补数据的第一优先级目标** ——
它同时给出 `Γ_GB`、富集因子与 DFT 偏析能。

### 1.3 计算的偏析能（DFT / 机器学习势）—— 知道在哪，数值待取

| 文献 | 体系 | 内容 | 状态 |
|---|---|---|---|
| **Song et al., *Rare Metals* (2025), [DOI 10.1007/s12598-025-03578-3](https://doi.org/10.1007/s12598-025-03578-3)** | **β-Ti Σ5(310) 晶界**（bcc！） | **48 种金属原子**的溶解能、偏析能、Rice-Wang 强化能 | 摘要已核实；**数值在付费表格中**。这是唯一直接对应「LPBF β 相」的偏析能来源 |
| **Scheiber, Razumovskiy, Peil, Romaner, *Adv. Eng. Mater.* **26** (2024) 2400269, [DOI 10.1002/adem.202400269](https://doi.org/10.1002/adem.202400269)** | Al, Cu, Fe, Mg, Mo, Nb, Ni, Ta, **Ti**, W | 高通量 DFT 晶界+表面偏析能，含 ML 外推 | **开放获取**（Wiley pdfdirect），本机被 Cloudflare 403。**从能上网的机器直接下 PDF/SI** |
| **Tuchinda, Schuh, *Scripta Mater.* **264** (2025) 116682, [DOI 10.1016/j.scriptamat.2025.116682](https://doi.org/10.1016/j.scriptamat.2025.116682)**（预印本 [arXiv:2502.08017](https://arxiv.org/abs/2502.08017)） | 16 元素含 **Al、Ti、V**，240 个二元合金多晶 | 偏析能**与**过剩振动熵的「谱数据库」 | **解决 `ΔS_seg` 缺口的最佳路径** |
| **Wagih, Lei, Ng, Schuh, *Acta Mater.* **294** (2025) 121169, [DOI 10.1016/j.actamat.2025.121169](https://doi.org/10.1016/j.actamat.2025.121169)** | BCC 钒基合金（V 是 bcc，与 β-Ti 同结构） | 量子精度偏析谱 + 实验验证 | 「bcc 基体」的类比数据 |
| Aksyonov, Lipnitskii, Kolobov, [arXiv:1302.4836](https://arxiv.org/abs/1302.4836) (2013) | α-Ti Σ7 晶界，**C/N/O 间隙原子** | 结论是「不利偏析」 | 全文可读。⚠ 讲的是间隙元素，**不是 Al/V** |
| Hu, Dingreville, Boyce, *Comput. Mater. Sci.* **232** (2024) 112596, [DOI 10.1016/j.commatsci.2023.112596](https://doi.org/10.1016/j.commatsci.2023.112596) | 综述 | 晶界偏析计算建模（DFT→相场） | **方法学入口，建议先读这篇再定方法** |

### 1.4 偏析熵 `ΔS_seg`

**未找到 Ti 体系的公开数值。** 唯一已知的可获得路径是 Tuchinda & Schuh 的谱数据库
（含 "excess vibrational entropy of segregation"，
见 [npj Comput. Mater. 10 (2024), DOI 10.1038/s41524-024-01260-3](https://doi.org/10.1038/s41524-024-01260-3)）。

---

## 2 晶界扩散

### 2.1 综述与总体规律（可直接引用）

**Herzig, Mishin, Divinski, *Metall. Mater. Trans. A* **33** (2002) 765–775,
[DOI 10.1007/s11661-002-1006-4](https://doi.org/10.1007/s11661-002-1006-4)**

覆盖 α-Ti、α-Zr、α-Hf 的体扩散与**晶界自扩散**、置换溶质扩散。
**最关键的可引用结论**：

> 高纯 hcp 材料中的晶界扩散可解释为「本征正常的空位介导晶界扩散」，
> **晶界与体扩散激活焓之比 `Q_gb/Q ≈ 0.6`**。

这条经验规律是**在没有 β-Ti 数据时构造 `D_GB` Arrhenius 参数的唯一有文献依据的锚点**。

### 2.2 实测三重积 —— 有，但是 Ti 自扩散和 Co，不是 Al/V

- **Herzig, Wilger, Przeorski, Hisker, Divinski, *Intermetallics* **9** (2001) 431–442,
  [DOI 10.1016/S0966-9795(01)00022-X](https://doi.org/10.1016/S0966-9795(01)00022-X)**
  —— Ti 示踪原子在 α-Ti、α₂-Ti₃Al、γ-TiAl 晶界及 α₂/γ 相界中的扩散。**数值未取得**。
- **Popov, Istomina, Osinnikov, Falahutdinov, *Phys. Met. Metallogr.* **126** (2025) 408–412,
  [DOI 10.1134/S0031918X24603585](https://doi.org/10.1134/S0031918X24603585)**
  —— **⁵⁷Co 在 α-Ti 晶界的扩散，473–873 K**，逐层放射化学分析，B 型动力学，
  **测定了三重积**并给出 Arrhenius 表达式。**数值未取得**。
  这是最接近「`s·δ·D_GB` 实测」需求的一篇。

### 2.3 Al、V 的**体扩散**（不是晶界，但是必要的分母）

**Liu, Welsch, *Metall. Trans. A* **19** (1988) 1121–1125,
[DOI 10.1007/BF02628396](https://doi.org/10.1007/BF02628396)**
—— O、Al、V 在 α-Ti、β-Ti 及金红石中的扩散数据文献综述，
是 Al/V 在 Ti 中体扩散的经典汇集出处（另有 1991 年补充通讯
[DOI 10.1007/BF02659006](https://doi.org/10.1007/BF02659006)）。**具体 D₀、Q 未取得**。

### 2.4 晶界厚度 `δ`

**这是约定，不是测量值**：晶界扩散文献中 `δ` 通常取 **0.5 nm**（亦有取 1 nm），
三重积记作 `P = s·δ·D_gb`。

- 定义了该约定的开放文献例：**Glienke et al., *Acta Mater.* **193** (2020),
  [DOI 10.1016/j.actamat.2020.05.009](https://doi.org/10.1016/j.actamat.2020.05.009)**
  （预印本 [arXiv:2003.10157](https://arxiv.org/abs/2003.10157)）—— 高熵合金晶界扩散。
- Herzig 2002 综述也用该约定。

### 2.5 β-Ti 晶界扩散 —— **空白**

**未找到任何 β-Ti（bcc）晶界扩散的实验或计算数据。**
这不是检索不力：α-Ti 晶界扩散本身就只有 Herzig 组的少数工作，
bcc 相的晶界扩散在 Ti 中基本无人测过（温度高、相变干扰、晶粒粗化快）。
**这是本课题最大的数据缺口。**

---

## 3 方法学参考：相场/界面模型怎么处理晶界偏析

| 文献 | 要点 |
|---|---|
| **Guin, Verma, Bandyopadhyay, Lo, Mukherjee, "Solute Segregation in a Moving Grain Boundary: A Novel Phase-Field Approach", [arXiv:2308.08262](https://arxiv.org/abs/2308.08262)** | **最对口**。相场方法处理**移动晶界**的溶质偏析；通过选择参数控制「溶质-晶界交互势」，得到与 **Cahn 溶质拖曳理论**一致的偏析剖面。**这就是 G3（拖曳）该对标的方法** |
| **Hu, Dingreville, Boyce (2024)**（同上） | 晶界偏析计算建模**综述**，DFT→连续介质的桥接。**建议作为方法章节的主引用** |
| **Pham, Ohno, Sahara, Kuwahara, Bhattacharyya, *J. Phys.: Condens. Matter* **32** (2020), [DOI 10.1088/1361-648X/ab7ad5](https://doi.org/10.1088/1361-648X/ab7ad5)** | **第一性原理相场（FPPF）**：**不引入任何热力学参数**就复现了 Ti64 中 Al 富集于 α、V 富集于 β 的分配，且与实验一致。**「以自由能第一性原理定标定」的范例**，双组元方案可直接借鉴 |
| **Wilson, "Complexions in a modified Langmuir–McLean model…", [arXiv:2208.04129](https://arxiv.org/abs/2208.04129)** | 对 Langmuir–McLean 等温线的严格化：给定体相浓度时**最可几偏析偏离标准 L–M 关系**，且可能出现两个稳定界面成分。若用标准 McLean，值得引这篇说明适用范围 |
| **Tan 2016**（同上） | 用 Gibbs 吸附定理把 `Γ` 与 `ΔE_tot` 挂钩 ⇒ `ΔE_tot` 是可直接对标的热力学量。**对本项目「以积分量为标定目标」的立足点是直接的文献支持** |
| **Mai, Cui, Hickel, Neugebauer, Ringer, [arXiv:2503.05640](https://arxiv.org/abs/2503.05640)** | 全周期表 × 6 个 bcc Fe 晶界的偏析能数据库。⚠ 其中 **Han Lin Mai 与 Xiangyuan Cui 也是 Breen 2026（Ti64 那篇）的作者** ⇒ Ti64 的 DFT 用的是同一套方法学。**自算 β-Ti 时可作模板** |

---

## 4 迁移性评估：这些值用到 Ti64 LPBF（β 相，1900–2000 K）合理吗？

### 4.1 相态不匹配 —— 最大的问题

模型算的是 **β（bcc）相、1900–2000 K**。但现有数据：

| 来源 | 相态 | 温度 |
|---|---|---|
| Breen 2026 | **α/α 晶界 + α/β 界面** | APT 室温；DFT 0 K |
| Tan 2016 | α/β 界面 | 923 K |
| Song 2025 | **β-Ti Σ5(310)**（相态对，但只有一个模型晶界） | 0 K |
| Herzig 组 | 全部 **α-Ti（hcp）** | 各种 |
| β-Ti 晶界扩散 | — | **无数据** |

⇒ **没有任何一个量是「β-Ti 晶界 + 1900–2000 K」的实测值。论文里必须明说。**

### 4.2 温度外推的量级估算（**这是算术，不是文献值**）

Langmuir–McLean：

```
x_GB/(1−x_GB) = x_bulk/(1−x_bulk) · exp(−ΔH_seg / RT)
```

`T = 1950 K` 时 `RT = 16.2 kJ/mol`。若 V 在 β-Ti 的 `ΔH_seg` 落在 −10 ～ −30 kJ/mol
（DFT 常见量级），则

```
s = exp(10/16.2) … exp(30/16.2) ≈ 1.9 … 6.4
```

**⇒ 高温下偏析被强烈稀释**：一个在 900 K 下 `s ≈ 10` 的体系，到 1950 K 只剩 `s ≈ 1.5–2`。
**因此直接把低温 APT 的 `Γ_GB` 拿去对标 1900 K 是错的**，必须用 `ΔH_seg`/`ΔS_seg` 外推。

### 4.3 各量分项评估

| 量 | 迁移到 Ti64-β @1950 K 的合理性 |
|---|---|
| `Γ_GB` 的**量级**（Tan 2016：V 2–5 at·nm⁻²，Al 负值） | **趋势可迁移，绝对值不可直接搬**。趋势（V 富集、Al 贫化）由 Breen 2026 的 DFT 在 Ti 体系独立确认；但 923 K → 1950 K 需按 McLean 折减 |
| α/β 分配比 `k`（Al 3.4–4.1，V 8.9–10.7） | **不能用于 1900 K 的 β 单相**。但可用来修当前的占位 `k = 0.63` —— ⚠ **注意两者的 `k` 定义未必一致**（我们的是液/固或相间分配），**先确认定义再谈替换** |
| `Q_gb/Q_bulk ≈ 0.6` | hcp 第 IV 族的规律。**外推到 bcc β-Ti 无直接依据**，但作为「无数据时的显式假设 + 敏感性分析」是可辩护的 |
| `D_GB` **绝对值** | **不可迁移**。只能给「`D_GB/D_bulk ≈ 10⁴–10⁵`（低温）」这类量级假设，并**明确标为假设** |
| `δ = 0.5 nm` | 约定值，可迁移（本来就不是测量值） |
| `ΔS_seg` | **缺失，且高温外推对它最敏感** —— 最大隐患 |

### 4.4 一条对本项目有利的文献支撑

Tan 2016 的 `ΔE_tot`（V 每 at·nm⁻² 过剩约 −12.7 mJ/m²，Al 约 +12.7 mJ/m²）说明：
**V 偏析降低界面能、Al 贫化升高界面能**，且 V 项占优 ⇒ 总界面能净降低 ⇒ 驱动 β 粗化。
这与本项目「以 `Γ` 为标定目标、后果自然正确」的论证方向一致，**可直接引用来支撑方法论**。

---

## 5 缺口清单与获取建议

| # | 缺口 | 影响 | 建议获取方式 |
|---|---|---|---|
| **E1** | **Breen 2026 的 `Γ_GB` 数值表与 DFT 偏析能** | **头号**，直接是「与 APT 实测对比」判据 | ⚠ **2026-09-19 复核后本条更严重**：UNSW 机构库那版**不只是文本抽取失败 —— 把页面渲染成图后字形本身就是乱码**（CID 字体程序损坏，`MuPDF: unknown cid font type`），**图像路线也救不了**。⇒ 唯一可行：① **ScienceDirect 的 CC-BY 版本**（在有正常网络的机器上）；② **直接邮件问 Andrew Breen (UNSW)** |
| **E2** | **Al、V 在 β-Ti 晶界的 `ΔH_seg` 数值** | McLean 参数 | ① **Scheiber 2024 确认是 OA**：`https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/adem.202400269` —— 去**能过 Cloudflare** 的机器下正文+SI（本机被拦，`curl` 返回 "Just a moment..."）；② **Song 2025**（Rare Metals）的 48 元素表，问作者或买；③ 自行 DFT（模板 Mai et al. [arXiv:2503.05640](https://arxiv.org/abs/2503.05640)；方法学 Umashankar et al. [arXiv:2503.03538](https://arxiv.org/abs/2503.03538)） |
| **E3** | **`ΔS_seg`（Ti–Al、Ti–V）** | 高温外推精度 | **Tuchinda & Schuh [arXiv:2502.08017](https://arxiv.org/abs/2502.08017)**：**已确认 Ti 基谱图 = Fig. S13、V 基谱图 = Fig. S14**。⚠ **数值在图里，无法从文本抽取** ⇒ 直接**联系作者要原始数据** |
| **E4** | **Al、V 在 Ti 晶界的 `D_GB` 与三重积** | 晶界扩散那部分的**全部** | **文献上没有。**只能：① 用 `Q_gb/Q ≈ 0.6` + 体扩散（Liu & Welsch 1988）构造，**明确标为假设**；② MD/DFT 自算；③ 实验唯一可行的是放射性示踪 + 逐层剥离，**对 Ti64 没人做过，成本极高** |
| **E5** | **β-Ti 晶界扩散的任何数据** | 高温段 | **文献空白**。建议在论文中作为已知局限明写，并做**敏感性分析**（`D_GB` 取 10⁴/10⁵/10⁶ × `D_bulk` 看 `Γ` 演化） |
| **E6** | Ti64 同相晶界上 Al 富集因子的实测 | 校核 | Breen 2026 是唯一来源（其结论是 **Al 贫化**）。若需要 β/β 晶界上的 Al 行为，**目前无实验数据** |
| **E7** | Liu & Welsch 1988 的具体 `D₀/Q` | 体扩散分母 | 该综述是二次文献；直接查它引用的原始示踪实验，或用最新评估（CALPHAD/动力学数据库） |
| **E8** | 晶界 α 形核与偏析的耦合（亚稳 β-Ti） | 若涉及相变 | 线索：[OSTI 2311370 "Computational modeling of grain boundary segregation: A review"](https://www.osti.gov/pages/biblio/2311370) |

---

## 6 参考文献（著录信息经 Crossref / OpenAlex 核对）

1. A. J. Breen, W. J. Davids, H. Chen, H. L. Mai, K. Nomoto, X. Cui, X. Liao, S. Primig, S. P. Ringer. *Quantifying changes to solute segregation behaviour at interfaces in additively manufactured Ti-6Al-4V.* **Acta Materialia 306 (2026) 121904.** [10.1016/j.actamat.2026.121904](https://doi.org/10.1016/j.actamat.2026.121904) ← **最重要**
2. X. Tan, Y. Kok, W. Q. Toh, Y. J. Tan, M. Descoins, D. Mangelinck, S. B. Tor, K. F. Leong, C. K. Chua. *Revealing martensitic transformation and α/β interface evolution in electron beam melting three-dimensional-printed Ti-6Al-4V.* **Scientific Reports 6 (2016) 26039.** [10.1038/srep26039](https://doi.org/10.1038/srep26039) ← **唯一拿到完整数值表**
3. C. Herzig, Y. Mishin, S. Divinski. *Bulk and interface boundary diffusion in group IV hexagonal close-packed metals and alloys.* **Metall. Mater. Trans. A 33 (2002) 765–775.** [10.1007/s11661-002-1006-4](https://doi.org/10.1007/s11661-002-1006-4)
4. Chr. Herzig, T. Wilger, T. Przeorski, F. Hisker, S. Divinski. *Titanium tracer diffusion in grain boundaries of α-Ti, α₂-Ti₃Al, and γ-TiAl and in α₂/γ interphase boundaries.* **Intermetallics 9 (2001) 431–442.** [10.1016/S0966-9795(01)00022-X](https://doi.org/10.1016/S0966-9795(01)00022-X)
5. V. V. Popov, A. Yu. Istomina, E. V. Osinnikov, R. M. Falahutdinov. *Grain Boundary Diffusion of ⁵⁷Co in α-Ti.* **Physics of Metals and Metallography 126 (2025) 408–412.** [10.1134/S0031918X24603585](https://doi.org/10.1134/S0031918X24603585)
6. Z. Liu, G. Welsch. *Literature Survey on Diffusivities of Oxygen, Aluminum, and Vanadium in Alpha Titanium, Beta Titanium, and in Rutile.* **Metall. Trans. A 19 (1988) 1121–1125.** [10.1007/BF02628396](https://doi.org/10.1007/BF02628396)
7. W. Song, S. Feng, Q. Du, Y. Xu, L. Yang, L. Wang, R. Liu. *Insights into solute atom doping effects on mechanical properties and grain boundary behaviors in β-Ti Σ5(310).* **Rare Metals (2025).** [10.1007/s12598-025-03578-3](https://doi.org/10.1007/s12598-025-03578-3)
8. D. Scheiber, V. I. Razumovskiy, O. E. Peil, L. Romaner. *High-Throughput First-Principles Calculations and Machine Learning of Grain Boundary Segregation in Metals.* **Adv. Eng. Mater. 26 (2024) 2400269.** [10.1002/adem.202400269](https://doi.org/10.1002/adem.202400269)
9. N. Tuchinda, C. A. Schuh. *Grain boundary segregation spectra from a generalized machine-learning potential.* **Scripta Materialia 264 (2025) 116682.** [10.1016/j.scriptamat.2025.116682](https://doi.org/10.1016/j.scriptamat.2025.116682)（[arXiv:2502.08017](https://arxiv.org/abs/2502.08017)）
10. N. Tuchinda, C. A. Schuh. *Computed entropy spectra for grain boundary segregation in polycrystals.* **npj Comput. Mater. 10 (2024).** [10.1038/s41524-024-01260-3](https://doi.org/10.1038/s41524-024-01260-3)
11. M. Wagih, T. Lei, D. Ng, C. A. Schuh. *Grain boundary segregation in BCC vanadium-based alloys.* **Acta Materialia 294 (2025) 121169.** [10.1016/j.actamat.2025.121169](https://doi.org/10.1016/j.actamat.2025.121169)
12. D. A. Aksyonov, A. G. Lipnitskii, Yu. R. Kolobov. *Grain boundary segregation of C, N and O in hcp titanium from first-principles.* [arXiv:1302.4836](https://arxiv.org/abs/1302.4836) (2013)
13. C. Hu, R. Dingreville, B. L. Boyce. *Computational modeling of grain boundary segregation: A review.* **Comput. Mater. Sci. 232 (2024) 112596.** [10.1016/j.commatsci.2023.112596](https://doi.org/10.1016/j.commatsci.2023.112596)
14. S. Guin, M. Verma, S. Bandyopadhyay, Y.-C. Lo, R. Mukherjee. *Solute Segregation in a Moving Grain Boundary: A Novel Phase-Field Approach.* [arXiv:2308.08262](https://arxiv.org/abs/2308.08262)
15. T. N. Pham, K. Ohno, R. Sahara, R. Kuwahara, S. Bhattacharyya. *Clear evidence for element partitioning effects in a Ti–6Al–4V alloy by the first-principles phase field method.* **J. Phys.: Condens. Matter 32 (2020).** [10.1088/1361-648X/ab7ad5](https://doi.org/10.1088/1361-648X/ab7ad5)
16. S. R. Wilson. *Complexions in a modified Langmuir–McLean model of grain boundary segregation.* [arXiv:2208.04129](https://arxiv.org/abs/2208.04129)
17. M. Glienke et al. *Grain boundary diffusion in CoCrFeMnNi high entropy alloy.* **Acta Materialia 193 (2020).** [10.1016/j.actamat.2020.05.009](https://doi.org/10.1016/j.actamat.2020.05.009)
18. S. Pedrazzini et al. *Effect of Substrate Bed Temperature on Solute Segregation and Mechanical Properties in Ti–6Al–4V Produced by Laser Powder Bed Fusion.* **Metall. Mater. Trans. A 54 (2023) 3069–3085.** [10.1007/s11661-023-07070-4](https://doi.org/10.1007/s11661-023-07070-4)（**明确 LPBF**；V 在孪晶界面与位错处偏析）
19. H. L. Mai, X.-Y. Cui, T. Hickel, J. Neugebauer, S. Ringer. *A high-throughput ab initio study of elemental segregation and cohesion at ferritic-iron grain boundaries.* [arXiv:2503.05640](https://arxiv.org/abs/2503.05640)

---

## 7 下一步建议（按性价比排序）

> **2026-09-19 更新**：`Ω₀` 的标定**不再阻塞于文献**——见 §0.3，理论公式（Cahn 1962）
> 已找到，且用 Tan 2016 的锚点反推出 **`Ω₀ ≈ −5×10⁻¹¹`**（当前值 `−4.6×10⁻⁹` 大了
> 约 100 倍）。**当务之急不是查文献，而是把生产值改对。**

0. **【最优先，不需要任何新文献】把 `Ω₀` 从 `−4.6×10⁻⁹` 改成 `≈−5×10⁻¹¹`**，
   并同时做三件事：① 修正 `Γ` 的量纲（×`ρ_mol`，见 §0.3.2）；
   ② 把偏析项改写成 `(ΔG_seg/v_m)(c−c₀)h_gb` 以带上温度依赖（§0.3.5）；
   ③ 在文档里明写「模型无法同时复现 `s` 与 `Γ`，本工作标定 `Γ`」（§0.3.4）。
1. **先拿到 Breen 2026 与 Scheiber 2024 的 PDF**（都是 CC-BY / OA），
   这两篇直接给 `Γ_GB` 数值与 Ti 的 DFT 偏析能表。
   ⚠ **Scheiber 2024 网址已确认**（见 E2）；**Breen 2026 的 UNSW 版字体损坏到渲染都是乱码**，
   只能走 ScienceDirect CC-BY 或直接问作者（见 E1）。
2. **用 Tan 2016 的 `Γ` 与 `ΔE_tot` 作为第一版标定目标** ——
   它是唯一完整、可核查、且是 AM Ti64 的定量数据。
   ⚠ 但要如实标注两个不匹配：**是 α/β 相界面不是晶界；923 K 与目标差约 1000 K**。
3. **晶界扩散那部分要尽早承认是空白**，改用「`Q_gb/Q_bulk = 0.6` + 敏感性分析」的写法，
   而不是假装有数据。
4. **Tuchinda/Schuh 的谱数据库**是解决 `ΔS_seg` 与高温外推的唯一现实路径，
   建议直接联系作者索取 Ti–Al、Ti–V 二元的结果（**图号已定位**：Fig. S13 / S14）。

---

## 8 检索说明（可核查性）

- **数据库**：Crossref REST API（著录信息核对）、OpenAlex API（摘要）、Unpaywall（OA 定位）、WebSearch。
- **关键词组**（均实际使用）：`grain boundary segregation enthalpy titanium alloy DFT Al V beta-Ti`、
  `solute excess grain boundary Ti-6Al-4V`、`grain boundary diffusion Al titanium triple product`、
  `triple product s delta D grain boundary`、`Gibbsian excess segregation phase field`、
  `atom probe Ti-6Al-4V V enrichment Al depletion`、`grain boundary alpha metastable beta titanium review`、
  中文「β-Ti Σ5(310) 晶界 偏聚能」。
- **本次检索的网络限制**：`WebFetch` 全域不可用；ScienceDirect、Wiley、OSTI、SSRN 的部分路径
  403/超时。所有内容通过 `curl` 直取可访问页面完成，**未使用任何非授权镜像**。
