# 块 = 多根同类板条堆叠 + 低角晶界分隔 + 板条间 Gibbs 面

> **本文件 = 阶段 1 交付物：数学定义与公式推导。**
>
> | 项 | 值 |
> |---|---|
> | 服务窗口 | **Window B**（`pipeline/RESEARCH_INTENT.md` §2.2：体相场 + Gibbs 零厚度面） |
> | 上游权威 | `pipeline/RESEARCH_INTENT.md`（§一、§2.2、§五 硬约束） |
> | 下游 | 阶段 2（代码实现）→ 阶段 3（实验） |
> | 状态 | **推导完成，等待自洽性审查（本文件 §7）与用户裁定（本文件 §11）** |
> | 日期 | 2026-09-29 |
>
> **标记约定**（沿用 `WINDOWB_PARAMS.md`）：**【文献】/【推导】/【实测】/【占位】/【未知】/【未核实】**。
> 凡标【推导】者，本文件给出算式；凡标【实测】者，给出仓库内脚本/日志名。

---

## §0.0 修订记录 —— v2（2026-09-29，**对抗性审查后**）

> **v1 犯了 **11 处错，其中 3 处会直接改变阶段 3 的读数与结论。**
> 审查报告：**`BLOCK_DERIVATION_REVIEW.md`**（419 行，逐条 A1–A8 + B1–B6，
> 每条负面结论都配了正对照；复现脚本 `_bkr_a12b.py` / `_bkr_misc.py` / `_bkr_f3.py` /
> `_bkr_guard.py` / `_bkr_csv.py` / `_bkr_area.py`）。
> **本文件 = v2 = 已按审查结论修正。** 下面逐条记账（编号用审查报告的 E-*）。

| 编号 | v1 的错 | v2 的改法 | 影响 |
|---|---|---|---|
| **E-4** | §6.6 用"毛细通道只占驱动 0.3%"论证"γ_Σ 无动力学效应" | **该论据错**：0.3% 是 **F1（α′/β）**的读数；F3 上 @@\Delta f=\Delta e_{\rm el}=0@@ ⇒ 毛细项是**全部**驱动力 ⇒ 位移**线性**依赖 γ_Σ。改成**两条硬理由**：**κ≡0 逐位不动** + `reinit_guard_region` | ★ **改结论** |
| **E-1 / E-3** | §2.3 说"`k=l` 时对角 NaN ⇒ 已自动回退 `npref`" | **理由错**：F3 是 **k≠l**，而 `de=0` ⇒ `_argmin_normal` 返回**有限垃圾向量** `[0.01,0,0.99995]` ⇒ 回退**永不触发**。⇒ 必须**显式守卫**；F3 钉扎只有 **2–8.6×**（不是 10–33×），最坏 `d_curv` **1.89Δx** | ★ **改结论** |
| **E-5 / E-6** | §4.4 把 @@-h\lvert\Delta g_{\rm chem}\rvert@@ 当"化学收益" | **符号反了**：@@T<M_s@@ 时 β 比 α′ 高 @@DF@@ ⇒ 膜是**代价** @@+h\cdot DF@@。C-1 方向更稳；C-2 的 0.5 J/m² → **≥1.75 J/m²** | ★ **改数字** |
| E-7 | §2.4/附录 A-1 写"24 元素点群" | hcp 的**纯转动**点群是 **622（12 个）**；按 24 个 + naive 迹公式会 **NaN**（反演 @@\mathrm{tr}=-3@@）。成立范围 @@\theta<30^\circ@@ | 实现会崩 |
| E-9 | §6.4 / P-6 "界面面积单调不增" | 只对**无体驱动、无三叉线**的闭合界面成立。归档 `A_tot` 实涨 **×7.84/8.30/8.90** ⇒ **P-6 作废** | 判据会误判 |
| E-8 | §6.5 声称"无遗漏" | 缺 (a) @@(\kappa_\psi/2)\lvert\nabla_\Sigma\psi\rvert^2@@ 对 Gibbs–Thomson 刚度的贡献、(b) 切向 Marangoni 项；且引擎**没有面网格**，I-5 必须先定义面 Laplacian | 实现缺口 |
| E-10 | §6.1 的 (4.9) 量纲行 | @@[L_\psi]\ne[M]@@；@@L_\psi\gamma@@ 的单位是 **1/s**；"面扩散"组合是 @@L_\psi\kappa_\psi\sim\mathrm{m^2/s}@@ | 量纲 |
| E-11 | §4.6 "面带占 0.023% 胞" | 与归档差 4.5–32×；按 §9.2 主臂应为 **0.2%–1.2%** | 数字 |
| A8 | §6.8 "块内有几根板条 = 涌现" | **是自欺**：根数 = 播了几个核 ⇒ **规定**。另缺"变体分组/M(n) 的 β_h,β_w/核形状位置取向"三行 | 防自欺 |
| A1 附 | §3.2 的 `+1` 与 @@G(T)@@ 口径 | `+1` 是**自洽性约定**不是推导；@@\gamma_m\propto G@@ ⇒ 应给 600 °C 口径；**`c+a` 位错会让 C-1 翻转** ⇒ 必须写成前提 | 表述 |
| B1 | §6.9 与 §5.3 的 `nreg` 上限两套口径 | 统一为「结构上限 **127** / 本阶段实取 **7**」 | 表述 |

**审查明确判为「正确、不要改」的部分**（v2 保留）：
§3.2 的 Read–Shockley 代数与数值（恒等 4e-16、`E0=1.512998`、`γ_m=0.396102`、
表 3.1 八档 0.9987–1.0019、`|b|=a_α` 实算比 1.000000、@@C^1@@ 通过、`0.15 ⇔ 1.83°`）；
§5.4 的 @@\Delta e_{\rm el}=0@@（实测 **逐位 0.000e+00**，含 `elastic_soft=True` 路径）；
§4.4 的 @@h\to0@@ Cahn 判据；§4.9 的 ψ 符号；式 (2.3) 的 @@O(\theta^3)@@；
B1/B2/B3/B5/B6 的代码事实。

**⚠ 引擎版本声明**：本文件 v1 冻结在 git `b00914f6`（引擎 sha `89ec9471…`）。
按 E-1 的守卫已在工作区实现（`_pair_normals` 内 `if not np.any(np.abs(de) > 1e-30): continue`），
**引擎 sha 因此不再是 `89ec9471`**；归档读数与工作区的可比性按 `_bk_engine_identity.py` 的
T-1（12 变体、`lath=None` ⇒ **逐位相同**）重新声明。

---

## §0 记号

| 记号 | 含义 |
|---|---|
| @@\Omega@@ | 周期立方盒 @@[0,L]^3@@，@@N^3@@ 胞，@@\Delta x=L/N@@ |
| @@\varphi_\alpha@@ | 第 @@\alpha@@ 个水平集场（有符号距离），@@\alpha=0,1,\dots,M@@ |
| @@\alpha=0@@ | 母相 **β**（prior-β 晶粒内部） |
| @@\alpha\ge1@@ | **板条**（lath）。注意：**下标是"板条身份"，不是"变体身份"** |
| @@M@@ | 板条总数（本文件把它与变体数解耦，这是整个推导的前提） |
| @@v(\alpha)\in\{1,\dots,12\}@@ | 板条 @@\alpha@@ 的 **Burgers 变体标签** |
| @@R(\mathbf x)@@ | @@=\arg\min_\alpha\varphi_\alpha(\mathbf x)@@ —— 区域图 |
| @@\Sigma_{\alpha\beta}@@ | @@\{\varphi_\alpha=\varphi_\beta\}@@ —— @@\alpha/\beta@@ 界面的零水平集 |
| @@\mathbf n@@ | 界面单位法向（由 @@\nabla\varphi@@ 给出） |
| @@\kappa@@ | 界面平均曲率（@@\nabla\cdot\mathbf n@@） |
| @@\theta_{\alpha\beta}@@ | 两条板条的**取向差角**（disorientation angle，§3.1） |
| @@\gamma_\Sigma@@ | 界面的**面能**（Gibbs 面的本构量）[J/m²] |
| @@\psi@@ | 面上的**独立状态量**：薄膜序参量（0 = 干晶界，1 = 有膜）【`RESEARCH_INTENT` §一原话】 |
| @@M(\mathbf n)@@ | 界面迁移率 [m⁴/(J·s)] |
| @@\Delta f@@ | 化学驱动力 [J/m³]，本引擎 @@DF=3.5\times10^8@@ |
| @@\Delta e_{\rm el}@@ | 微弹性驱动力 [J/m³]（Khachaturyan 谱法） |
| @@\mathbf n^*_\alpha@@ | 板条 @@\alpha@@ 的**惯习面法向**（= 弹性最省能法向，代码 `npref`） |
| @@\mathbf a_\alpha@@ | 板条**长轴**（rank-1 分解的位移方向，代码 `atab`） |
| @@\mathbf w_\alpha=\mathbf n^*_\alpha\times\mathbf a_\alpha@@ | 板条**宽度方向**（代码 `wtab`） |
| @@\boldsymbol\varepsilon^0_\alpha@@ | 形状应变（本征应变） |

---

## §1 问题的精确陈述：现有框架为什么表示不了"块"

### 1.1 现有结构（**代码事实**，`windowB_surface.py`）

```
self.nv   = len(eps0)          # 变体数（真实 12）
self.nreg = self.nv + 1        # 场数 = 13；index 0 = 母相
self.phi  = np.full((nreg, N, N, N), 1e3)
region()  = argmin(phi, axis=0)          #  :1161
```

⇒ **场下标 = 变体下标，一一对应（双射）。**

### 1.2 差距的精确定位

> **块的内部低角晶界表示不出来，唯一原因是：场↔变体是双射。**
> 两根**同变体**的板条必须共用一个 @@\varphi@@ ⇒ 它们**从初始条件起就是同一个对象**，
> 谈不上"合并"，因为**从未分开过**。

这条比此前的表述（`R1_PROBLEM_LEDGER.md` A-5：「同变体板条接触即合并」）更准确：

* A-5 的说法暗示"先分开、后合并" —— **不是**。
* 真实情况是"**从来没有两个对象**"。

### 1.3 由此必须纠正的一条历史结论

`R1_VERDICTS_RESTATED.md` §117 / `R1_PHASE3_BLOCKS.md` §18 写：

> 「同变体的两根板条接触即合并 ⇒ 块内低角晶界不可表示」

**这句话的因果是错的。** 正确的表述分两层：

| 层 | 陈述 | 性质 |
|---|---|---|
| L-a | **在"场=变体"的双射结构下**，同变体板条不可分 | **结构事实**（可由 §1.1 直接读出） |
| L-b | **在"场=板条、场→变体多对一"的结构下**，同变体板条可分，低角晶界可表示 | **本文件 §2 要建立的东西** |

⇒ L-b 此前**从未被检验过**，因为从未实现过。

### 1.4 R1 实验 4/5/6 的"合并"是**装置**造成的 【实测 + 代码证据】

`_r1_exp.py:599`：

```python
for i, c in enumerate(centers):
    K = vlist[i % len(vlist)]          # ← 变体列表循环取
    seed_one(g, K, shape, c, aa, nh)   # ← 播进**同一个场** K
```

而实验 4/5/6 的 `variants=[1]`（默认 `vlist=[K0]=[1]`）⇒

> **6 个核全部播进 @@\varphi_1@@ 一个场。**
> `nsig` 从 6 降到 1 是**必然的**，与"合并"这一物理过程无关。

⇒ **R1 实验 4/5/6 对"板条会不会合并"这个问题没有分辨力**；它们实际测的是
"一个场里播 6 个种子会长成什么形状"。

**记账**：这不推翻实验 4/5/6 的其它读数（长径比、B-1 分组等），
但**推翻了它们作为"块"这一命题证据的资格**。见 §9.3。

---

## §2 推广的状态描述：板条身份 vs 变体身份

### 2.1 场结构

$$
\varphi_0,\ \varphi_1,\dots,\varphi_M,\qquad
R(\mathbf x)=\arg\min_{\alpha}\varphi_\alpha(\mathbf x)
$$

**没有新的方程**：`advance` 的逐胞速度律、`reinit`、迎风对流**全部逐字不变** ——
引擎本来就对"场的个数"是通用的。变的只是**属性表怎么建**。

### 2.2 板条属性表（`vmap`）

设真实变体表为 @@\{\hat{\boldsymbol\varepsilon}^0_v,\hat{\mathbf n}^*_v,\hat{\mathbf a}_v,\hat{\mathbf w}_v,\widehat{df}_v\}_{v=1}^{12}@@
（代码：`windowB_ti64_variants.variants()` + `npref/atab/wtab`，已验）。

每根板条 @@\alpha@@ 带三个属性：

$$
\boxed{\;
v(\alpha)\in\{1..12\},\qquad
\boldsymbol\omega_\alpha\in\mathbb R^3\ (\text{小转动矢量}),\qquad
\mathsf r_\alpha=\exp[\boldsymbol\omega_\alpha]_\times
\;}
$$

**逐场派生量（全部由 @@v(\alpha)@@ 复制，不引入新物理量）：**

$$
\Delta f_\alpha=\widehat{df}_{v(\alpha)},\qquad
\boldsymbol\varepsilon^0_\alpha=\hat{\boldsymbol\varepsilon}^0_{v(\alpha)},\qquad
\mathbf n^*_\alpha=\hat{\mathbf n}^*_{v(\alpha)},\qquad
\mathbf a_\alpha=\hat{\mathbf a}_{v(\alpha)},\qquad
\mathbf w_\alpha=\hat{\mathbf w}_{v(\alpha)}
\tag{2.1}
$$

> ⚠ **层级 1 / 层级 2 的分岔点在这里，必须写明**：
> * **层级 1（本阶段采用）**：@@\boldsymbol\varepsilon^0_\alpha@@ **不含** @@\mathsf r_\alpha@@
>   ⇒ 同变体的两根板条 @@\boldsymbol\varepsilon^0@@ **逐位相同**
>   ⇒ @@\Delta f=0,\ \Delta e_{\rm el}=0@@ ⇒ **块内界面是纯毛细界面**（§6.6 的核心）。
> * **层级 2（本阶段不做，登记在案）**：@@\boldsymbol\varepsilon^0_\alpha=\mathsf r_\alpha\hat{\boldsymbol\varepsilon}^0_{v(\alpha)}\mathsf r_\alpha^{\!\top}@@
>   ⇒ 取向差带来 @@\Delta\boldsymbol\varepsilon^0\sim\theta@@ 的弹性相互作用
>   ⇒ 这是"薄膜的**力学容纳**"那一项（见 §5.6）唯一能进来的通道。
>
> 层级 1 是**低角晶界的标准锐界面处理**：低角晶界对**体相**性质是一阶小量，
> 它的效应集中在**面**上（面能 @@\gamma(\theta)@@、面扩散、位错阻挡）。
> ⇒ **层级 1 不是"砍掉物理"，而是"低角晶界物理的正确落点是面、不是体"。**

### 2.3 面片身份与三类界面

一胞的**面片身份** @@(I^-,I^+)=(k,l)@@ = (winner, runner-up)。按 @@v(\cdot)@@ 分三类：

| 类 | 条件 | 物理 | 面能 |
|---|---|---|---|
| **F1** | 恰一侧为 0 | α′ / 母相 β | @@\gamma_{1}(n)@@ —— **现有**（`npref` + Herring） |
| **F2** | @@v(k)\ne v(l)@@ | α′ / α′，**异变体** | @@\gamma_{2}(n)@@ —— **现有**（`ncmp` + Herring） |
| **F3** | @@v(k)=v(l)\ne0@@ | α′ / α′，**同变体** ⇒ **低角晶界** | @@\gamma_{\rm LAGB}(\theta_{kl})@@ —— **本文件新增** |

> ★★ **F3 的参考法向必须显式守卫 —— v1 在这里的推理是错的（E-1，已修正）**
>
> **v1 的错误理由**：「@@k=l@@ 时 `ncmp[k,k]=nan` ⇒ `facet_nref` 已经回退 `npref[k]`
> ⇒ 回退分支恰好正确」。
> **为什么错**：F3 面片是 @@(k,l)@@ 且 **@@k\ne l@@**（两根同变体板条是**两个不同的场**）
> ⇒ 它走的是 `_pair_normals` 的**非对角**分支，而那里 @@\Delta\boldsymbol\varepsilon^0=0@@
> ⇒ `argmin_normal(C, 0)` 的泛函**恒等于 0** ⇒ `argmin` 取球面采样表第 0 项
> ⇒ **返回一个有限的垃圾向量**，不崩、不 NaN。
> 【实测 `BLOCK_DERIVATION_REVIEW.md` B4 / `_bkr_guard.py`】：`n = [0.01, 0, 0.99995]`、`E=0`、`cons=0`。
> ⇒ `ncmp[k,l]` **有限** ⇒ `facet_nref` 的 `good = has_pair & isfinite(cand)` 为真
> ⇒ **回退永远不触发**。
>
> **后果（v1 没算的账）**：
>
> | 量 | 有守卫（正确） | 无守卫（v1 描述的状态） |
> |---|---|---|
> | @@( \mathbf n^*_v\cdot\mathbf n_{\rm garbage})^2@@ | 1（回退到 @@\mathbf n^*@@） | 0.200–0.615（**逐变体不同**） |
> | @@M_{\rm eff}/M_0=\exp[-\beta_h(\cdot)^2]@@ | **0.0302** | **0.116–0.497**（V8 最坏 0.497） |
> | §3.3 的"钉扎倍数" | **33×** | **2.0–8.6×** |
> | §6.6 的 @@d_{\rm curv}@@（@@\gamma@@=0.396） | **0.115 @@\Delta x@@** | **0.44–1.89 @@\Delta x@@** |
> | 同，@@\gamma_\Sigma@@=1.1（`wet` 臂） | 0.32 @@\Delta x@@ | **最坏 5.2 @@\Delta x@@** |
> | Herring 择优轴 | @@\mathbf n^*@@ | 垃圾向量 |
>
> ⇒ **必须把守卫做成硬条件**（已实现，见 §10 I-2）：
> @@\lVert\Delta\boldsymbol\varepsilon^0\rVert=0@@（等价于 @@v(k)=v(l)@@ 且 @@k\ne l@@）
> ⇒ `ncmp[k,l] = NaN` ⇒ `facet_nref`/`nd_ref` 双双回退 @@\mathbf n^*@@。
> **回归判据**：`_bk_engine_identity.py` 的 **T-2.1/T-2.3**（`ncmp[1,2]` 全 NaN；
> `facet_nref(1, larr=2) == npref[1]`）。
> ⚠ **不得**为了省内存把重复的 `eps0` 去重 —— 那会静默退回垃圾向量。
>
> 守卫生效后：块内堆叠的板条"宽面贴宽面"，界面就是**惯习面**本身
> ⇒ @@\mathbf n_{\rm ref}=\mathbf n^*_{v}@@ ✓（**这一句结论仍对，只是理由要换**）。

### 2.4 取向差角

设板条的**晶格取向** @@\mathsf R_\alpha=\mathsf R_{v(\alpha)}\mathsf r_\alpha@@
（@@\mathsf R_v@@ 是 Burgers 变体转动，@@\mathsf r_\alpha@@ 是该板条的小转动）。

相对转动：@@\Delta\mathsf R_{\alpha\beta}=\mathsf R_\alpha\mathsf R_\beta^{\!\top}@@。
**取向差角**（对晶体**纯转动**点群 @@\mathcal S@@ 取极小，即"disorientation"）：

$$
\theta_{\alpha\beta}=\min_{\mathsf s\in\mathcal S}\arccos\!\Big(\tfrac12\big[\mathrm{tr}(\mathsf s\,\Delta\mathsf R_{\alpha\beta})-1\big]\Big)
\tag{2.2}
$$

> ★★ **@@\mathcal S@@ = hcp 的纯转动点群 622，阶 = 12**（E-7：v1 写"24 个元素"是**错的**）
>
> hcp 的**完整**点群是 @@6/mmm@@（阶 24），但其中 **12 个是镜面/反演**（@@\det=-1@@）。
> 取向差是**两个转动**之间的角 ⇒ 只能在**纯转动**子群上取极小。
> 按 24 个 + naive 迹公式实现会**直接崩**：反演给 @@\mathrm{tr}(\mathsf s\Delta\mathsf R)=-3
> \Rightarrow\arccos(-2)@@，实测 21 个小角抽样**全部** `math domain error`。
> ⇒ 实现用 @@\{C_{6z}^k,\ C_{6z}^kC_{2x}\}@@（@@k=0..5@@）共 **12 个**，@@\det@@ 全 @@+1@@，
> 非恒等元的**最小转角 = 60°**（`windowB_lath._selftest` S-1.3 逐位核过）。
>
> **裸角公式 (2.3) 的成立范围是 @@\theta<30^\circ@@**（不是"任意小角"）：
> 群元最小转角 60° ⇒ 要把它拉得比裸角更接近恒等需要 @@\theta>30^\circ@@。
> 实测：@@\theta\le30^\circ@@ **逐位**等于裸角；@@40^\circ\to23.93^\circ@@、@@59^\circ\to15.77^\circ@@。
> 本阶段 @@\theta\le5^\circ@@ ⇒ **远在范围内** ✓。

**同变体情形是干净的**：

$$
\Delta\mathsf R_{\alpha\beta}
=\mathsf R_v\underbrace{\mathsf r_\alpha\mathsf r_\beta^{\!\top}}_{\displaystyle \Delta\mathsf r}\mathsf R_v^{\!\top}
\;\Longrightarrow\;
\theta_{\alpha\beta}=\big|\boldsymbol\omega_\alpha-\boldsymbol\omega_\beta\big|+\mathcal O(\theta^3)
\tag{2.3}
$$

（转动角在共轭下不变 ⇒ 变体转动 @@\mathsf R_v@@ **完全约掉**；
实测两种口径之差 **3.6e-12 度**。两小转动之积的角 = 转动矢量之差的一阶，
偏差的阶实测 **slope = 3.000**（`windowB_lath._selftest` S-2.2）。）

> **自洽性检查 S-1（已做，见附录 A-1）**：@@\mathcal S@@ 的 **12** 个纯转动元
> 对小的 @@\Delta\mathsf r@@ 是否真的给出同一个 @@\theta@@？⇒ 是，@@\theta\le30^\circ@@ 内逐位相等。

---

## §3 低角晶界的数学

### 3.1 Read–Shockley 面能

$$
\boxed{\;
\gamma_{\rm RS}(\theta)=
\begin{cases}
\gamma_m\dfrac{\theta}{\theta_m}\Big(1-\ln\dfrac{\theta}{\theta_m}\Big), & 0<\theta\le\theta_m\\[6pt]
\gamma_m, & \theta>\theta_m
\end{cases}
\;}
\qquad \theta_m\equiv15^\circ
\tag{3.1}
$$

三条**结构性质**（都要用到）：

| # | 性质 | 后果 |
|---|---|---|
| P1 | @@\gamma_{\rm RS}(0)=0@@ | 取向差为零 ⇒ 面能零 ⇒ **与"根本没界面"连续**（不会造出无源的界面能） |
| P2 | @@\gamma_{\rm RS}'(\theta_m)=0@@，且 @@\gamma_{\rm RS}(\theta_m^-)=\gamma_{\rm RS}(\theta_m^+)=\gamma_m@@ | **@@C^1@@ 连续** ⇒ Gibbs–Thomson 项**无尖点** ⇒ 不需要额外凸化 |
| P3 | @@\gamma_{\rm RS}@@ **不依赖 @@\mathbf n@@** | Herring 项 @@\gamma_{\theta\theta}=0@@ ⇒ 与现有 `herring_stiffness` 的**法向**各向异性正交、不打架 |

> P3 是**近似**（§7 S-4 记账）：真实低角晶界分**倾转/扭转**，面能依赖界面是否含转动轴。
> 本阶段取各向同性 RS（文献里最常见的用法），并把**转动轴**作为观测量存下来备查。

### 3.2 从位错墙推导 @@\gamma_m@@（**这一步把 [占位] 变成 [推导]**）

Frank 公式：对称倾转晶界 = 间距 @@D=b/\theta@@ 的刃位错墙。单位面积位错数 @@\rho_\perp=\theta/b@@。
单位长度刃位错的应力场能量（芯外，截断半径 @@r_0@@）：

$$
E_{\rm disl}=\frac{Gb^2}{4\pi(1-\nu)}\ln\frac{R}{r_0}
\;\Longrightarrow\;
\gamma_{\rm LAGB}=\rho_\perp E_{\rm disl}=\frac{Gb\,\theta}{4\pi(1-\nu)}\Big(\ln\frac{1}{\theta}+C\Big)
$$

取 @@C=1+\ln\theta_m@@ 即在 @@\theta=\theta_m@@ 处接上平台 @@\gamma_m@@：

$$
\gamma_{\rm LAGB}(\theta)=E_0\,\theta\Big(1-\ln\frac{\theta}{\theta_m}\Big),
\qquad
\boxed{\;E_0\equiv\frac{G\,b}{4\pi(1-\nu)},\qquad \gamma_m=E_0\,\theta_m\;}
\tag{3.2}
$$

**Ti-6Al-4V 的数值**：

| 量 | 值 | 出处 |
|---|---|---|
| @@a_\alpha@@ | 0.2950 nm | 【文献】`WINDOWB_PARAMS.md` §1 |
| @@\mathbf b=\tfrac{a}{3}\langle11\bar20\rangle,\ \vert\mathbf b\vert=a_\alpha@@ | **0.295 nm** | 【文献】hcp 完美 @@a@@ 型位错 |
| @@G@@ | **42.5 GPa** | 【推导】@@E=114\,\mathrm{GPa},\nu=0.34\Rightarrow G=E/2(1+\nu)@@ |
| @@\nu@@ | 0.34 | 【文献】 |
| @@E_0=Gb/[4\pi(1-\nu)]@@ | **1.513 J/m²** | 【推导】@@=42.537\text{e}9\times0.295\text{e}{-9}/(4\pi\times0.66)@@ |
| @@\theta_m@@ | 15° = 0.2618 rad | 【文献】 |
| **@@\gamma_m=E_0\theta_m@@** | **0.396 J/m²** | 【推导】 |

**表 3.1 —— @@\gamma_{\rm RS}(\theta)@@ 数值**

| @@\theta@@ | 0.5° | 1° | **1.83°** | 2° | 3° | 5° | 10° | 15° |
|---|---|---|---|---|---|---|---|---|
| @@\gamma@@ [J/m²] | 0.058 | 0.098 | **0.150** | 0.159 | 0.207 | 0.277 | 0.371 | 0.396 |

> 表 3.1 由 `_bk_verify.py` 的 A-2.4 逐档核对（**8/8 PASS**）；@@E_0@@ 由 A-2.2 核对。

> ⚠⚠ **三条必须写进结论的口径（A1 附，v1 漏了）**
>
> **(a) `+1` 不是推导出来的，是"取芯半径 @@r_0=b/e@@（等价地 @@C=1+\ln\theta_m@@）"这个约定。**
> 即：@@\gamma_m=E_0\theta_m@@ 是**用平台值反向定 C** 得到的**自洽性约定**，
> **不是独立预言**。文献里 @@\gamma_m@@ 通常是**独立输入**，两者一般不重合。
> ⇒ 用 @@E_0@@ 预测 @@\gamma_m@@ 时，只能说"**与取 @@r_0=b/e@@ 的位错墙模型自洽**"。
>
> **(b) @@E_0\propto G(T)@@，温度口径必须与 @@\gamma_{\alpha'\beta}@@ 一致。**
> v1 用**室温** @@E=114$$ GPa@@ 算 @@\gamma_m=0.396@@，却拿它去比 **600 °C** 的 @@\gamma_{\alpha'\beta}@@。
> 取 600 °C 的 @@G@@（约 −20%）⇒ @@\gamma_m\approx0.317@@
> ⇒ **C-1 更稳**（见 §4.4）。本文件报两个口径。
>
> **(c) ★ C-1 的隐含前提：低角界面由 `a` 型位错构成（@@\lvert\mathbf b\rvert=a_\alpha=0.295$$ nm@@）。**
> 若由 `c+a` 位错构成（@@\lvert\mathbf b\rvert\approx0.55$$ nm@@）
> ⇒ @@\gamma_m=0.74$$ J/m²@@ **大于** @@2\gamma_{\alpha'\beta}=0.596@@
> ⇒ **C-1（B1 无稳定 β 膜）会翻转**。⇒ 这条前提必须写在 C-1 旁边，不能只写在附录。

> ★★ **与现有 [占位] 的一致性核对（重要）**
>
> `WINDOWB_PARAMS.md` §5 现在把 @@\gamma_{\rm lath}@@ 记为 **0.15 J/m² [占位]**
> （注："α/α′ 低角界面文献 0.1–0.3"）。
> 表 3.1 反查：@@\gamma_{\rm RS}=0.15@@ ⇔ **@@\theta=1.83^\circ@@**（`_bk_verify.py` A-2.5 核对）。
> ⇒ **那个占位数是一个 ≈1.8° 低角晶界的 RS 值。**
> ⇒ 它不是随手填的，**现在它有推导了**：@@\gamma_{\rm lath}=\gamma_{\rm RS}(\theta)@@，
>    @@\theta@@ 从 [占位] 变成**可指定、可扫描的物理输入**（块内板条取向差）。

### 3.3 迁移率：沿用 @@M(\mathbf n)@@，并给出定量钉扎（**依赖 §2.3 的守卫**）

物理：低角晶界的迁移由**位错芯扩散/攀移**控制，与高角晶界/相界**不同机制** ⇒ 用同一个 @@M(\mathbf n)@@ 是**近似**（§7 S-5 记账）。

**在守卫生效（E-1）的前提下**，F3 界面的 @@\mathbf n_{\rm ref}@@ 就是 @@\mathbf n^*@@：

$$
\frac{M(\mathbf n^*)}{M_0}=e^{-\beta_h}=e^{-3.5}=\mathbf{0.0302}\quad(\beta_h=3.5)
\qquad
\frac{M(\mathbf w)}{M_0}=e^{-\beta_w}=e^{-2.3}=\mathbf{0.1003}\quad(\beta_w=2.3)
$$

⇒ **钉扎 33×（面贴面沿 @@\mathbf n^*@@ 堆叠）/ 10×（侧靠沿 @@\mathbf w@@）**。

> ⚠⚠ **v1 这里写"10–33× 钉扎、无需新增机制"是不完整的（E-1/E-3）**：
> **没有守卫时** @@\mathbf n_{\rm ref}@@ 是垃圾向量，
> @@(\mathbf n^*_v\cdot\mathbf n_{\rm g})^2\in[0.200,0.615]@@ **逐变体不同**
> ⇒ @@M_{\rm eff}/M_0\in[0.116,0.497]@@ ⇒ 钉扎只有 **2.0–8.6×**
> （V8 最坏 0.497 ⇒ 2.0×）。
> ⇒ **这句话的正确写法是**：「**在 `de=0 ⇒ ncmp=NaN` 守卫下**，块内界面得到
> 33×（面贴面）/10×（侧靠）的钉扎」。**守卫是这条结论的前提，不是实现细节。**
>
> 另：@@\beta_h,\beta_w@@ 是 **规定的设计参数**（`_r1_exp.py:712`），不是从文献推来的
> ⇒ 已按 A8 补进 §6.8 的防自欺表。

---

## §4 板条间薄膜：Gibbs 面的数学

### 4.1 真实几何

板条间薄膜 = `α′ | β_film(h) | α′` 三明治，@@h\sim@@ 几 nm。

**为什么不能解析它**（用户的判断，**本文件确认它是对的，而且比用户说的更硬**）：

| 分辨率 | 薄膜 @@h@@=5–20 nm 占几个胞 | 代价 |
|---|---|---|
| **§3 已批准的 @@\Delta x=10$$ nm** | **0.5–2 胞** | 已批设计本身就解析不了 |
| R1 现用 @@\Delta x=125$$ nm | **0.04–0.16 胞** | — |
| 真要 4 胞 ⇒ @@\Delta x\approx2$$ nm | 4 胞 ✓ | 胞数 ×**(125/2)³≈2.4×10⁵** |

⇒ **用 Gibbs 面替代不是妥协，是这个尺度分离下唯一可行的表示。**

### 4.2 Gibbs 分割面与面积过剩量

取分割面 @@\mathcal S@@（= 零水平集）落在界面处。对任意广延量 @@\Phi@@，
**面积过剩量**定义为

$$
\Phi^\sigma\equiv\frac{1}{A}\Big[\Phi_{\rm real}-\Phi_{\rm ref}\Big],
\qquad\text{例如}\qquad
\Gamma_i=\frac{1}{A}\int\big[c_i(z)-c_i^{\rm ref}(z)\big]\,\mathrm dz
\tag{4.1}
$$

**Gibbs 吸附等温式**（形状无关的恒等式）：

$$
\mathrm d\gamma=-\sum_i\Gamma_i\,\mathrm d\mu_i-S^\sigma\,\mathrm dT
\tag{4.2}
$$

> ⚠ **规范依赖**：单个 @@\Gamma_i@@ 依赖分割面取在哪里；只有 @@\gamma@@ 或 @@\sum_i\Gamma_i\mathrm d\mu_i@@ 有意义
> （`RESEARCH_INTENT.md` §7.2 第 11 条 —— 这是**已经写进防跑偏清单**的坑）。
> ⇒ 本文件所有 @@\Gamma@@ **必须连同"分割面约定"一起报**，否则不可比。

### 4.3 零厚度折叠（h → 0）

把厚度 @@h@@ 的膜折成零厚度的面，**逐量建立映射**：

| 真体积量 | 折算后面量 | 说明 |
|---|---|---|
| 溶质库存 @@c_i^{\rm film}h@@ | @@\Gamma_i=c_i^{\rm film}h@@ [mol/m²] | 守恒的**面密度** |
| 扩散电导 @@D_i^{\rm film}h@@ | @@D_i^\sigma@@ [m³/s]（薄层电导） | 标准表面扩散写法 |
| 自由能 @@h\,\Delta g_{\rm film}@@ | 并入 @@\gamma_\Sigma@@ | 见 (4.3) |
| **体积** | **丢弃** | @@t_f/(t_{\rm lath}+t_f)\approx10/310\approx\mathbf{3\%}@@ ⇒ 可忽略但**必须记账** |

**面自由能（折叠后）**：

$$
\boxed{\;
\gamma_f(\theta)=2\gamma_{\alpha'\beta}(\theta)+h_{\rm eq}\,\Delta g_{\rm film}(\theta)+\Pi(h_{\rm eq})
\;}
\tag{4.3}
$$

@@\Pi@@ = 两界面间的**分离压**（disjoining pressure）积分，@@h_{\rm eq}@@ 由 @@\partial\gamma_f/\partial h=0@@ 定。
**零厚度极限下 @@h@@ 不再是自由度** ⇒ @@\gamma_f@@ 变成一个**本构函数** @@\gamma_f(\theta)@@，
其参数由 @@(h_{\rm eq},c^{\rm film})@@ 折叠得到。

### 4.4 ★ 薄膜**存在性判据**（本推导最关键的一节）

问：@@\beta@@ 膜能不能在两根同变体 @@\alpha'@@ 板条之间存在？

**判据的正确写法：造出这层膜，是让能量升还是降？**（单位面积）

$$
\boxed{\;
\Gamma_{\rm dry}=\gamma_{\rm LAGB}(\theta),
\qquad
\Gamma_{\rm film}=2\gamma_{\alpha'\beta}
+\underbrace{h\big(\Delta G^{\beta\to\alpha'}_{\rm vol}+\Delta g_{\rm el}^{\rm film}\big)}_{\text{体积代价（见下）}}
\;}
\tag{4.4a}
$$

**膜存在 ⇔ @@\Gamma_{\rm film}<\Gamma_{\rm dry}@@ ⇔**

$$
\boxed{\;\Delta\gamma_{\rm surf}\;\equiv\;\gamma_{\rm LAGB}(\theta)-2\gamma_{\alpha'\beta}
\;>\;h\big(\Delta G^{\beta\to\alpha'}_{\rm vol}+\Delta g_{\rm el}^{\rm film}\big)\;}
\tag{4.5}
$$

> ★★★ **符号（E-5，v1 在这里写反了）**
>
> @@T<M_s@@ 时 **β 相对 α′ 高** @@\lvert\Delta G^{\beta\to\alpha'}_{\rm vol}\rvert=DF@@
> ⇒ 一块 β 膜的体自由能是**代价** @@+h\,DF@@，**不是收益** @@-h\lvert\Delta g_{\rm chem}\rvert@@。
> v1 的 (4.4) 把它写成"化学收益"，**与 §4.4.1 自己的结论（B1 无扩散 ⇒ 化学通道关闭）自相矛盾**。
> ⇒ v2 改成 (4.4a)：**两项都是代价** —— 体自由能代价 @@h\,DF@@（β 亚稳）
> + 约束弹性能代价 @@h\,\Delta g_{\rm el}^{\rm film}@@（@@\ge0@@）。
> **@@h\to0@@ 的极限不变**（这也正是下面 (4.6) 仍然成立的原因）。

**@@h\to0@@ 极限 ⇒ 经典 Cahn 润湿判据**：

$$
\boxed{\;\text{薄膜润湿低角晶界}\iff \gamma_{\rm LAGB}(\theta)>2\gamma_{\alpha'\beta}\;}
\tag{4.6}
$$

#### 4.4.1 化学（成分）通道：**B1 里关闭**（不是"暂时不做"，是**物理上不成立**）

**成分 partitioning** 属 **B2（α′→α+β，扩散型）**，而 B2 在 LPBF 建造期内不发生
（【实测】1073 K 需 0.33 h）⇒ B1 里 β 膜**不能靠 V 富集稳定**。
但 ⚠ **这不等于体积项为零**：β 亚稳本身就是一份体积代价 @@h\,DF@@（见 4.4.2）。

#### 4.4.2 力学通道：把数代进去（**v2 重算**）

用引擎自己的数（`_r1_exp.py`：@@DF=3.5\times10^8$$ J/m³）：

| 量 | 值 | 出处 |
|---|---|---|
| 体自由能代价 @@\Delta G^{\beta\to\alpha'}_{\rm vol}@@ | @@+3.5\times10^8$$ J/m³（**β 亚稳**） | 模型参数 `DF` |
| 约束弹性能代价 @@\Delta g_{\rm el}^{\rm film}@@ | @@\ge0@@（共格薄膜，**未标定**） | 【未核实】 |
| @@h=5$$ nm 的体积项**下限**（取 @@\Delta g_{\rm el}=0@@） | @@5\times10^{-9}\times3.5\times10^8=\mathbf{\ge1.75}$$ J/m² | 【推导】 |
| @@h=1$$ nm 同上 | @@\ge0.35$$ J/m² | 【推导】 |
| @@\Delta\gamma_{\rm surf}@@ 的**上界** | @@0.396-2\gamma_{\alpha'\beta}<0@@ | 见 4.4.3 |

> ⚠ **v1 这里写"@@h=5$$ nm ⇒ +0.5$$ J/m²@@"是错的（E-5）**：那个数来自
> @@(\lvert\Delta g_{\rm chem}\rvert-\Delta g_{\rm el})\approx1.0\times10^8@@ 的**相减**，
> 而两项**都被误识别**：@@\Delta g_{\rm chem}@@ 用了符号反的 @@DF@@，
> @@\Delta g_{\rm el}=2.5\times10^8@@ 是从 R1 的 **`ed` 读数（变体受到的弹性驱动力）**借来的，
> **不是 β 薄膜的弹性代价**。
> ⇒ 正确下限 **≥1.75 J/m²**（丢掉弹性项），**"体积项更不利"这个方向成立且比 v1 说的更强**。

#### 4.4.3 ★★ @@\gamma_{\alpha'\beta}@@ 的文献值 —— 判据在此**定量闭合**

**【文献】Murzinova 2017**（*Lett. Mater.* **7**(1) 55–59, DOI `10.22226/2410-3535-2017-1-55-59`）：
用 van der Merwe–Shiflet 半共格界面模型算了 Ti-6Al-4V 的 **β/α 界面比能**，
对四种"平面"半共格匹配方案：

$$
\gamma_{\alpha'\beta}=
\begin{cases}
\mathbf{0.201\text{–}0.337}\ \mathrm{J/m^2}, & 975^\circ\mathrm C\\[3pt]
\mathbf{0.298\text{–}0.429}\ \mathrm{J/m^2}, & 600^\circ\mathrm C
\end{cases}
$$

降温到 @@M_s=848$$ K @@=575^\circ\mathrm C@@（`WINDOWB_PARAMS.md` §1）⇒ 取 **@@\gamma_{\alpha'\beta}\approx0.30\text{–}0.43$$ J/m²**，
中心值 **0.35 J/m²**。

$$
2\gamma_{\alpha'\beta}\approx\mathbf{0.60\text{–}0.86}\ \mathrm{J/m^2}
\quad\gg\quad
\max_\theta\gamma_{\rm LAGB}=\gamma_m=\mathbf{0.396}\ \mathrm{J/m^2}
$$

$$
\Longrightarrow\quad
\boxed{\;\Delta\gamma_{\rm surf}=\gamma_{\rm LAGB}(\theta)-2\gamma_{\alpha'\beta}\;<\;0
\quad\text{对所有}\ \theta\;}
\tag{4.7}
$$

**⇒ 结论（三条，都要写进结论）**

| # | 结论 | 依据 |
|---|---|---|
| **C-1** | **B1 里不存在热力学稳定的板条间 β 薄膜** —— 润湿判据 (4.6) 在**任何** @@\theta@@ 下都不成立 | (4.6)+(4.7) |
| **C-2** | 体积项**更**不利：@@h=5$$ nm 时代价 @@\ge1.75$$ J/m²@@（v2 重算；v1 的 0.5 是符号反的产物）⇒ 连"有限厚度稳定化"也没有 | (4.5) |
| **C-3** | 因此 **B1 里板条间的物理实体 = 干低角晶界** @@\gamma_{\rm RS}(\theta)@@，而**不是** β 薄膜 | C-1+C-2 |

**余量有多大（**只对"面能通道"有效** —— E-6）**：

| @@T@@ | @@2\gamma_{\alpha'\beta}@@ | 对 @@\gamma_m=0.396@@（室温 @@G@@） | 对 @@\gamma_m=0.317@@（600 °C @@G@@） |
|---|---|---|---|
| 600 °C（接近 @@M_s@@=575 °C） | 0.596–0.858 | **1.51–2.17×** | **1.88–2.71×** |
| 975 °C | 0.402–0.674 | **1.02–1.70×** | 1.27–2.13× |

> ⚠⚠ **v1 在这张表下的读法是误导的（E-6）**
>
> v1 写「最不利的一档（975 °C、@@\gamma=0.201@@）余量只有 1.5% ⇒ 高温端险胜」。
> **错**：975 °C 时 **β 是稳定相** ⇒ @@\Delta G^{\beta\to\alpha'}_{\rm vol}<0@@
> ⇒ (4.5) 右边的体积项**反号**（膜**更**有利）。
> 用一张**只含面能**的表去说高温端"险胜"，会把读者引向**相反**的方向。
> ⇒ **本表只对"面能通道"有效**；跨温度比较必须把 @@h\,\Delta G^{\beta\to\alpha'}@@ 一起算。
> ⇒ 对 **B1（@@T<M_s@@，接近 600 °C）**，体积项是**代价**且 @@\ge1.75$$ J/m²@@（@@h=5$$ nm@@）
> ⇒ **C-1 比 v1 说的更稳**。
>
> **C-1 的三条前提/风险（必须与结论并列，不能只放附录）**：
> 1. **`a` 型位错**（@@\lvert\mathbf b\rvert=a_\alpha@@）。若是 `c+a`（@@\lvert\mathbf b\rvert=0.55$$ nm@@）
>    ⇒ @@\gamma_m=0.74>0.596@@ ⇒ **判据翻转**（§3.2 note (c)）。
> 2. **@@\gamma_{\alpha'\beta}@@ 是跨机制借用的**：Murzinova 2017 的值属 **600–975 °C 的扩散型 α+β 平衡界面**
>    （摘要原话：diffusion β/α transformation + V enrichment），把它外推到**位移型、无分配**的 B1
>    是机制外推，**未核实**。
> 3. 若界面有溶质使 @@\gamma_{\alpha'\beta}<0.20$$ J/m²@@ ⇒ 判据可能翻转。
>
> ⇒ **这正是必须保留 `dry`/`wet`/`auto` 三臂的定量理由**，不是走过场。

> ★★ **这同时是一条与冶金学事实的独立对账**：
> as-built LPBF Ti-6Al-4V 的组织就是 **α′（几乎无残余 β）**；
> 残余 β 薄膜出现在 **α′→α+β 分解之后**（即 B2 / 原位回热 / 热处理）。
> ⇒ 模型给出"C-1：B1 无膜"，与实测组织**一致**。
> ⇒ 这不是"模型少放了东西"，而是**模型给对了**。

> ⚠ **另一种"膜"要区分开**：α+β 区里晶界 α/β **allotriomorph**（晶界 β 层）是
> **扩散长大**现象（厚度 @@\propto\sqrt{Dt}@@），**不是润湿平衡**。
> ⇒ 它同属 B2，不进 B1。

### 4.5 ⚠ 与用户指示的关系（**必须显式记账，不得静默省略**）

用户 2026-09-29 指示：「板条之间的薄膜使用 Gibbs 面」「板条之间有 Gibbs 面形成的薄膜」。

本推导的处理方式是**两者都保留、可切换、用实验判决**，而不是单方面删掉薄膜：

| 模式 | @@\gamma_\Sigma@@ | 物理含义 | 用途 |
|---|---|---|---|
| `dry` | @@\gamma_{\rm RS}(\theta)@@ | **C-1/C-3 的结论**，B1 的正确物理 | **主臂** |
| `wet` | @@\gamma_f@@（面能输入，@@\gamma_f<2\gamma_{\alpha'\beta}@@ 时被"规定"） | **人为规定的亚稳膜**（用户要的那个） | **配对对照臂** |
| `auto` | 由面上的 @@\psi@@ 场按 (4.7)/(4.8) **自发**演化 | 让模型自己选 | **判决臂** |

**三臂共用同一套代码**，差别只在 @@\gamma_\Sigma@@ 的取值 ⇒ 满足"单变量对照"。
**`auto` 臂是从初值 @@\psi\equiv1@@（处处有膜）出发、看它会不会自己退湿** ——
这是一个**可否证**的预言（见 §8 P-2）。若 `auto` 不退湿 ⇒ 我上面的 C-1 推导错了。

### 4.6 面上的独立状态量 @@\psi@@（"零厚度的面 + **面上的独立状态量**"）

`RESEARCH_INTENT.md` §一原话就要求 Gibbs 面**承载面上的独立状态量**。这里给它定成 @@\psi@@。

**面自由能泛函**（@@\psi=0@@=干晶界，@@\psi=1@@=有膜）：

$$
\mathcal F_\Sigma[\psi]=\int_{\mathcal S}\Big[\gamma_\Sigma(\psi,\theta)+\tfrac{\kappa_\psi}{2}\lvert\nabla_\Sigma\psi\rvert^2\Big]\mathrm dA
\tag{4.8a}
$$

$$
\gamma_\Sigma(\psi,\theta)=\big[1-f(\psi)\big]\gamma_{\rm dry}(\theta)+f(\psi)\,\gamma_f+W\,g(\psi),
\qquad
f(\psi)=\psi^2(3-2\psi),\quad g(\psi)=\psi^2(1-\psi)^2
\tag{4.8b}
$$

两井：@@\gamma_\Sigma(0)=\gamma_{\rm dry}@@，@@\gamma_\Sigma(1)=\gamma_f@@；井间势垒 @@\propto W@@。

**演化（非保守 Allen–Cahn，面 Laplacian）**：

$$
\boxed{\;
\partial_t\psi=-L_\psi\Big[
f'(\psi)\big(\gamma_f-\gamma_{\rm dry}(\theta)\big)+W g'(\psi)-\kappa_\psi\nabla_\Sigma^2\psi
\Big]\;}
\tag{4.9}
$$

@@f'=6\psi(1-\psi),\ g'=2\psi(1-\psi)(1-2\psi)@@。

**性质核对（都在 §7）**：

| 检查 | 结果 |
|---|---|
| @@\psi\equiv0@@ 是解？ | 是（@@f'(0)=g'(0)=0@@ 且 @@\nabla^2_\Sigma\psi=0@@）✓ |
| @@\psi\equiv1@@ 是解？ | 是（@@f'(1)=g'(1)=0@@）✓ |
| @@\gamma_f<\gamma_{\rm dry}@@ 时 @@\psi\to1@@？ | 是：驱动 @@f'(\psi)(\gamma_f-\gamma_{\rm dry})<0@@ ⇒ 向 @@\psi@@ 增大漂移 ✓ |
| @@\gamma_f>\gamma_{\rm dry}@@（**就是本项目的 C-1 情形**）⇒ @@\psi\to0@@（退湿） | 是 ✓ **这是预言 P-2** |
| 是否守恒？ | **不守恒**（结构序参量，非守恒密度）。若将来把 @@\Gamma_i@@ 也放上去，那条要换成面 Cahn–Hilliard ✓ |

**反馈到界面速度**：@@\gamma_\Sigma(\psi,\theta)@@ **替换** Gibbs–Thomson 里的 @@\gamma@@（§5）。
**计算代价**：@@\nabla_\Sigma^2@@ 只在界面带（@@\lvert\varphi\rvert<1.5\Delta x@@）上算。
带胞占比 **按 §9.2 主臂量级 0.2%–1.2%**（v1 写的 0.023% **低了 4.5–32×**，E-11；
归档 `_exp/e4_lath6/series.csv` 的 `nif` 列首 0.104% / 末 0.748%）⇒ **代价仍可忽略**。

### 4.7 面上的溶质过剩 @@\Gamma_i@@（Window C 暂缓，但**留槽 + 冻结记账**）

按 `RESEARCH_INTENT` §2.3，Window C 暂缓。本阶段的处理：

* 变量 @@\Gamma_i@@ **存在**（`LevelSetMulti._Gam_mol` 已经在，`surface_chem=False` 默认关闭）；
* B1 的 **@@k_{\rm part}=1.0@@**（`windowB_surface.py:952`，T4 已判）⇒ **界面扫过溶质原样继承**，@@\Gamma\equiv0@@；
* ⇒ **本阶段所有"薄膜"读数都是几何/能量读数，不含溶质**。**必须写进结论**（否则等于偷偷声称了 Window C）。

---

## §5 速度律与引擎对接（符号级）

### 5.1 现有律（**代码事实**，`windowB_surface.py:2759`）

```
dG_cell = (df[karr] - df[larr]) + (edk - edl) - stk * kap_cell
v_cell  = M * dG_cell                      # 或带 drag
v_cell *= Mfac                             # mob_beta 各向异性
stk     = gamma + gamma_tt                 # Herring，_stiff_of:2145
```

### 5.2 推广律（**形式不变，只有 @@\gamma@@ 的来源变**）

$$
v_n^{kl}=M_{kl}(\mathbf n)\Big[
\underbrace{\big(\Delta f_k-\Delta f_l\big)}_{=0\ \text{若同变体}}
+\underbrace{\big(\Delta e_k-\Delta e_l\big)}_{=0\ \text{若同变体 (层级1)}}
-\;\underbrace{\mathrm{stk}_{kl}(\mathbf n,\theta_{kl})}_{\displaystyle \gamma_\Sigma(\psi,\theta_{kl})+\gamma_{\theta\theta}}\;\kappa\Big]
\tag{5.1}
$$

### 5.3 逐项对应表（**每一行都要能在代码里指出位置**）

| 数学量 | 现有代码 | 本阶段改动 | 风险 |
|---|---|---|---|
| 场 @@\varphi_\alpha@@ | `self.phi` | **无**（`M` 从 12 放开） | `nreg` 必须 @@\le127@@（`region()` 用 `int8`） |
| @@v(\alpha)@@ | — | **新增** `vmap` | — |
| @@\Delta f_\alpha@@ | `self.df` | 建表时**复制** | 无 |
| @@\boldsymbol\varepsilon^0_\alpha@@ | `self._eps0_ref` | 建表时**复制** | ★ `_pair_normals` 对 `de=0` 会退化，**必须守卫** |
| @@\mathbf n^*_\alpha,\mathbf a_\alpha,\mathbf w_\alpha@@ | `npref/atab/wtab` | 建表时**复制** | 无 |
| @@\mathbf n_{\rm ref}(k,l)@@ | `facet_nref` :2074 | ★ **必须加守卫**（§2.3）：`de=0` ⇒ `ncmp[k,l]=NaN` ⇒ 才回退 `npref[k]`。**没有守卫时回退永不触发**（E-1） | ★★ 见 §2.3 |
| @@\gamma_\Sigma@@ | `gamma0` 标量 | **新增** `facet_gamma(k,larr)` 逐胞表 | ★ 见下 |
| @@M(\mathbf n)@@ | `mob_beta`+`nd_ref` | ★ **同受守卫保护**：`nd_ref` 也来自 `ncmp[karr,larr]` ⇒ 无守卫时 F3 的 @@M_{\rm eff}/M_0\in[0.116,0.497]@@ 而非 0.0302（E-1） | ★★ |
| @@\psi@@ | — | **新增** 面带上的 AC 步 | 新增参数 @@L_\psi,W,\kappa_\psi@@ **[占位]** |

> ★ **@@\gamma_\Sigma@@ 逐胞化为什么是低风险的**：
> `herring_stiffness` 与 `herring_stiffness_cusp` **都对 `gamma0` 严格线性**
> （`windowB_surface.py:317,327-328`）⇒
> 可以先用 `gamma0=1` 算出无量纲的 @@\mathrm{stk}/\gamma_0@@，**再逐胞乘** @@\gamma_\Sigma@@。
> ⇒ 不改动任何已验证的几何/迎风/Herring 代码。

> ★★ **并行适配 + 内存（用户 2026-09-29 明确要求，v2 新增）**
>
> `advance` 的逐场几何跑在 `self.par.for_each(...)` 的**工作线程**里
> （`windowB_surface.py:2551`）⇒ 塞进 `_geom_k` 的新代码必须**纯函数 + 不在 worker 里大分配**。
>
> **v1 的写法**：在 `_geom_k` 内逐场调用 `facet_gamma_sub(k, larr[bb], gamma0)`
> ⇒ 每个活跃场分配 3–4 份子盒临时数组（@@N=192@@ 时 56 MB/份、7 场 ≈ **1.2 GB/步**）
> ⇒ 实测把 WSL 推到 **swap 8189/8192 = 99.9%**、一个进程卡在 **`D` 态**。
>
> **v2 的写法**：**主线程一次性向量化建只读表 `_gc_full`，worker 只做零分配切片 `_gc_full[bb]`**，
> 用完（`for_each` 返回后）立即释放。
>
> **判据 `_bk_par_identity.py`（6 条，FAIL = 0）**：
> * P-1.1 快速路径与参考路径 @@\gamma@@ **逐位相同**（max|Δ| = 0.000e+00）；
> * P-1.3 `lath=None` 时 `_gc_full` **不被建立** ⇒ 原路径逐位不变；
> * **P-2 `nthreads=1` vs `nthreads=8` ⇒ `phi` 逐位相同、region 翻转 0**（臂 N 与臂 L 各一次）
>   ⇒ **线程数仍不是物理参数**（本仓库既有验收口径）；
> * P-2.C 正对照证明"相同"不是空转。

### 5.4 块内界面的三项驱动力：**两项严格为零**

对 F3（同变体）：

$$
\Delta f_k-\Delta f_l=\widehat{df}_v-\widehat{df}_v=0,
\qquad
\Delta e_k-\Delta e_l=0\ \text{（层级 1：(2.1) 逐位相同）}
$$

⇒ @@v_n=-M_{\rm eff}\gamma_\Sigma\kappa@@ —— **纯曲率流**。

**注意这是一个"干净"的结果，不是"少放了东西"**：
两根**取向完全相同的**晶体之间**没有驱动力**是**正确的物理**；
真实块内界面的稳定性来自（i）低角晶界迁移率极低、（ii）无扩散 ⇒ 结构冻结。

---

## §6 自洽性检查（逐条给判据）

### 6.1 量纲

| 式 | 量纲核对 |
|---|---|
| (3.1) | @@E_0\theta@@：J/m² ✓（@@Gb@@ = Pa·m = J/m²） |
| (4.4) | @@h\Delta g@@：m·J/m³ = J/m² ✓ |
| (4.9) | @@[L_\psi]=@@ m²/(J·s) —— ⚠ **与界面 @@M@@=@@ m⁴/(J·s) **不是**同一量纲**（E-10）；@@L_\psi\gamma@@ 的单位是 **1/s**（弛豫率）✓。**"面扩散型"的正确组合是 @@L_\psi\kappa_\psi\sim$$ m²/s** |
| (5.1) | @@M\cdot\Delta f@@：m⁴/(J·s)·J/m³ = m/s ✓；@@M\gamma\kappa@@：m⁴/(J·s)·J/m²·1/m = m/s ✓ |

### 6.2 极限行为

| 极限 | 应有行为 | 本框架 |
|---|---|---|
| @@\theta\to0@@ | 界面能 → 0，与"无界面"连续 | @@\gamma_{\rm RS}\to0@@ ✓ (P1) |
| @@\theta\to\theta_m@@ | @@\gamma@@ 与 @@\gamma'@@ 连续 | ✓ (P2) |
| @@\gamma_f=\gamma_{\rm dry}@@ | @@\psi@@ 无驱动 | @@f'(\psi)\cdot0@@ ⇒ 只剩势垒 ✓ |
| @@M\to0@@ | 冻结 | ✓ |
| @@\psi@@ 面 Laplacian 关掉 | 退回"逐胞 0 维" | ✓（@@\kappa_\psi=0@@ ⇒ 每胞独立） |

### 6.3 对称性

| 对称 | 核对 |
|---|---|
| 交换 @@k\leftrightarrow l@@ | @@\theta_{kl}=\theta_{lk}@@，@@\gamma_\Sigma@@ 对称 ✓ |
| 变体转动共轭 | (2.3)：@@\mathsf R_v@@ 在 @@\theta@@ 里约掉 ✓ |
| 平移 | 全部是局域量 ⇒ 平移不变 ✓ |
| 各向同性空间转动 | @@\gamma_{\rm RS}(\theta)@@ 只依赖标量 @@\theta@@ ✓；@@M(\mathbf n)@@/Herring 依赖 @@\mathbf n\cdot\mathbf n^*@@ ✓ |

### 6.4 守恒

| 量 | 是否守恒 | 说明 |
|---|---|---|
| 总体积 | 是（`region()` 划分，@@\sum V_k=V_{\rm box}@@） | 已有守恒判据 |
| 溶质 | **平凡守恒**（@@k_{\rm part}=1@@，@@c@@ 不动） | 已有逐位判据 |
| @@\psi@@ | **不守恒** | 正确（结构序参量） |
| 面积 | 不守恒。⚠ **v1 写"按 @@\dot A=-M\gamma\!\int\kappa^2\mathrm dA@@ 单调减"是错的（E-9）**：该恒等式只对**无体驱动、无三叉线**的闭合界面成立。归档实测 `A_tot`（coarea 面积）在 e4/e5/e6 上各涨 **×7.84 / ×8.30 / ×8.90** —— 因为三叉线（板条端部）随长大推进，**正常长大就会增大界面面积** | |

### 6.5 变分一致性

@@v_n=M\big[-\delta\mathcal F/\delta\phi\big]@@ 形式下，@@\gamma_\Sigma@@ 的变分给出 @@-\gamma_\Sigma\kappa@@（Gibbs–Thomson）✓。
@@\psi@@ 的变分给出 (4.9) ✓。**两式共用同一个 @@\gamma_\Sigma(\psi,\theta)@@** ⇒ **不是重复计数** ✓。

> ⚠⚠ **但 v1 接着写的"无遗漏"是错的（E-8）。至少缺两项：**
>
> **(a) 梯度能对 Gibbs–Thomson 刚度的贡献。**
> 把面法向位移 @@\delta n@@ 代入 @@\mathcal F_\Sigma=\int[\gamma_\Sigma(\psi)+(\kappa_\psi/2)\lvert\nabla_\Sigma\psi\rvert^2]\mathrm dA@@，
> 面积元变 @@\mathrm dA\to(1-\kappa\,\delta n)\mathrm dA@@ ⇒ 法向力里出现的刚度是
> @@\big(\gamma_\Sigma+\tfrac{\kappa_\psi}{2}\lvert\nabla_\Sigma\psi\rvert^2\big)\kappa@@，
> 而 (5.1) 只用了 @@\gamma_\Sigma\kappa@@。平界面或 @@\nabla_\Sigma\psi=0@@ 时该项为零
> ⇒ **本阶段可能可忽略，但不能声称"无遗漏"**。
>
> **(b) 切向（Marangoni）项。** @@\psi@@ 沿面变化 ⇒ @@\gamma_\Sigma@@ 沿面变化
> ⇒ 面内应力散度 @@-\nabla_\Sigma\gamma_\Sigma\ne0@@。
> 固-固 Gibbs 面**没有面内流动通道**，这一项应由**体相弹性**承担；
> 而本引擎的弹性只吃 @@\boldsymbol\varepsilon^0(\text{region})@@、**不吃面上的切向牵引**
> ⇒ 这是一条**未记账的耦合缺口**（须进 §7 记账表）。
>
> **(c) 实现层：引擎里根本没有面网格。** 把 @@\psi@@ 存在界面带
> （@@\lvert\varphi\rvert<1.5\Delta x@@ 的 3D 胞）上再做 3D @@\nabla^2@@，
> 得到的是**体 Laplacian**，不是 @@\nabla_\Sigma^2@@（法向只有 1–2 层胞，法向二阶差分会污染）。
> ⇒ **§10 I-5 在动手前必须先给出 @@\nabla_\Sigma^2@@ 的离散定义并验证**
> （候选：@@\nabla_\Sigma^2\psi=\nabla^2\psi-(\mathbf n\cdot\nabla)^2\psi@@，只在带内用）。
>
> **(d) Cahn 判据只在平界面上成立**：曲率会通过 Laplace 压修正润湿条件（@@h_{\rm eq}(\kappa)@@）。
> (4.6) 用于"块内界面"时，板条端部是**弯曲**的 ⇒ 必须声明适用范围。
>
> **(e) 敏感度应扫 @@L_\psi\kappa_\psi@@ 这个组合**（= 面扩散系数 m²/s），而不是分别扫。

> ⚠ **一处必须记账的不一致（沿用现有的）**：@@\gamma_{\theta\theta}@@ 用的是
> `herring_stiffness` 的**法向**各向异性，而 @@\gamma_{\rm RS}@@ 是 @@\mathbf n@@ 无关的。
> 两者**正交且可加**（§3.1 P3），但严格说"低角晶界的 @@\mathbf n@@ 依赖"被设成了 0。
> ⇒ 记账为近似 S-4。

### 6.6 ★★ 核心：**为什么不合并**（**v2 重写 —— E-3/E-4**）

> ⚠⚠ **v1 这一节的**主论证是错的**，v2 换掉。**
> v1 用"毛细通道只占驱动 0.36%/3.6%"来论证"γ_Σ 无动力学效应 ⇒ 不会合并"。
> **错在**：那 0.3% 是 **F1（α′/β）界面**的读数；而按 §5.4 自己的结论，
> F3 上 @@\Delta f=\Delta e_{\rm el}=0@@（代码 `:2759` 逐字可核）
> ⇒ **毛细项是 F3 的全部驱动力**，位移**线性**依赖 γ_Σ
> （@@\gamma_\Sigma@@ 从 0.15 扫到 1.1 会把位移界放大 **7.3×**）。
> ⇒ **"毛细通道 0.3%" 不能用来支持任何关于 F3 的结论。**

#### 6.6.1 主论证（两条，都是**结构性**的，与 γ_Σ 取值无关）

**(i) ★ F3 的驱动力**只有**毛细项**，且用实测 κ 代进去，整个窗口的位移 @@\ll0.1\Delta x@@。**

对 F3：@@dG_{\rm cell}=0+0-\mathrm{stk}\cdot\kappa_{\rm cell}@@（`windowB_surface.py:2759` 逐字）。

**实测（`_bk_engine_identity.py` T-2.4，Δx=62.5 nm，N=32，两片贴合）**：
F3 胞上的 @@\max\lvert\kappa\rvert=\mathbf{2.246\times10^7}$$ m⁻¹@@@@=0.28/\Delta x@@
⇒ 120 步位移预测 **0.0052 @@\Delta x@@**；
而独立跑的 120 步算例（`_w2_f3ns.log`，§9.4）实测 **−0.010 @@\Delta x@@** ✓ **吻合**。

> ⚠⚠ **v2 在此更正审查报告的一句话，也更正文件上一版的写法（两者都过强）**
>
> 审查报告 E-4 的 (i) 写「平 F3 界面 @@\kappa\equiv0@@ ⇒ @@dG@@ 逐位为 0」。
> **本文件实测：这句话只对"无限大严格平面"成立。**
> * 平坦共享面的**内部**（424 胞）@@\max\lvert\kappa\rvert=1.73\times10^7@@ —— **不是 0**
>   （有限板条的棱、以及 @@\mathrm{stk}@@ 沿面的不齐都会贡献）；
> * **周界**（三叉线处）@@\max\lvert\kappa\rvert=2.25\times10^7@@。
> * ⇒ **正确的表述是**：F3 上的 κ **不是 0**，但由它算出的位移在整个窗口内 **< 0.01 @@\Delta x@@**
>   （因为 @@M_{\rm eff}=0.0302M_0@@ 极小）。
> * 审查报告测到的 @@dG_{\max}=6.4\times10^{-10}$$ J/m³@@ 是**它们那个装置**（零应变差的球/平面、无板条棱）
>   的读数，不能推广成"F3 上 @@dG@@ 逐位为 0"。
>
> **⇒ 结论方向不变（不合并），但依据改成"位移量级"，不是"逐位为 0"。**

**(ii) `reinit` 不是合并通道：引擎有 `reinit_guard_region` 硬守卫。**

`windowB_surface.py:3389-3396`：重初始化造成的**区域翻转会被原样退回**
⇒ 定时 reinit 不会把两根板条并成一根。
【`e7d_pair34` 的 `regflip=162` 统计的正是**被退回**的翻转（区域实际没变）。】

**其余通道审查也逐个排除了**（`BLOCK_DERIVATION_REVIEW.md` A4）：
@@k_{\rm part}=1.0@@ ⇒ `_stefan` 恒等；两场共用同一个 `Vvec` ⇒ 差分场刚性平推；
`extend_along_normal` 在 R1 默认 `adv_grad='proj2'` 下**不参与**。

#### 6.6.2 二次保险：把曲率上界代进去（**v1 的算术，保留但降级**）

若界面因长大而**失平**（三叉线推进、板条端部），则 @@v_n=-M_{\rm eff}\gamma_\Sigma\kappa@@。
取**网格上可能的最大曲率** @@\kappa_{\max}\approx2/\Delta x@@
（⚠ **这是未证伪的假设**，不是定理：代码 `_gn=\sqrt{\sum g^2}+10^{-30}`
理论上允许 @@|\nabla d|\to0@@ 处 κ 无界 ⇒ 若要证伪需量演化态的 κ 分布）：

| 量 | 值 | 来源 |
|---|---|---|
| @@M_{\rm eff}=M_0e^{-\beta_h}@@ | @@3.02\text{e}{-11}@@ m⁴/(J·s) | **依赖 §2.3 的守卫** |
| @@\kappa_{\max}=2/\Delta x@@ | @@3.2\text{e}7$$ m⁻¹ | **假设** |
| @@dt=0.15\Delta x/(M_0DF)@@ | @@2.679\text{e}{-8}$$ s | 引擎 |
| @@t_{\rm sim}=700\,dt@@ | @@1.875\text{e}{-5}$$ s | 700 步 |

| @@\gamma_\Sigma@@ | 有守卫（@@M_{\rm eff}=0.0302M_0@@） | **无守卫**（@@M_{\rm eff}/M_0\in[0.116,0.497]@@） |
|---|---|---|
| 0.159（@@\theta=2^\circ@@） | 2.9 nm = **0.046 @@\Delta x@@** | 0.17–0.73 @@\Delta x@@ |
| 0.396（@@\theta\ge15^\circ@@） | 7.2 nm = **0.115 @@\Delta x@@** | **0.44–1.89 @@\Delta x@@** |
| 1.1（`wet` 臂） | 0.32 @@\Delta x@@ | **1.2–5.2 @@\Delta x@@** |

> ⇒ **v1 的 0.115 @@\Delta x@@ 只在守卫存在时成立；没有守卫时最坏 1.89 @@\Delta x@@（`wet` 臂 5.2）。**
> ⇒ 这就是为什么 §2.3 的守卫 + §10 I-2 的回归判据是**结论的一部分**，不是实现细节。

**正对照（同一把尺子量"应该动的"）**：同一段时间里，α′/β 尖端（法向 ≈ @@\mathbf a@@，@@M\approx M_0@@）
以 @@v=M_0\Delta f=0.35$$ m/s@@ 前进 ⇒ @@6.56\,\mu@@m ⇒ 与 7.17 nm 之比 **≈915×**
⇒ 两个过程差三个数量级 ⇒ 实验能干净地把"板条长大"与"界面合并"分开。

#### 6.6.3 ★ 对 γ_Σ 的正确结论（**替换 v1 的"无可测影响"**）

> **v1 说**：「γ_Σ 从 0.15 换到 1.1 对合并/块形成**没有可测影响**，因为毛细通道只有 0.3%」。
> **v2 更正**：**在 F3 上，γ_Σ 是唯一驱动力，位移线性正比于它**
> （@@d\propto M_{\rm eff}\gamma_\Sigma\kappa t@@）。
> ⇒ 正确的陈述分两层：
>
> | 情形 | 结论 |
> |---|---|
> | **界面保持平**（κ≡0） | 位移**逐位为 0**，与 γ_Σ **完全无关** ⇒ 不合并 |
> | **界面失平**（κ≠0） | 位移**线性正比 γ_Σ**：@@\gamma=0.15\to1.1@@ ⇒ 位移界 **0.044→0.32 @@\Delta x@@**（有守卫）；**这是一个可测的量，不是"无影响"** |
>
> ⇒ **P-3 必须重写成"位移正比于 γ_Σ，且在物理 γ（0.15–0.4）下仍 < 0.12 @@\Delta x@@ 的线性预言"**，
> 而**不是**"扫 γ_Σ 无可测变化"。

**薄膜在 B1 里真正的作用**（仍然成立，只是理由换掉）：
（i）**溶质储存**（Window C）、（ii）**异变体界面的力学容纳**（层级 2）—— 两者本阶段都没打开。
**必须写进结论。**

### 6.7 与已有结论的一致性

| 已有结论 | 本框架 |
|---|---|
| A-2：界面能只占驱动力 0.1–0.3% | ✓（**那是 F1 的读数**；F3 上毛细项是全部驱动力，见 §6.6.3 —— 两者不矛盾，但**不得混用**） |
| A-3：`facet_lam` 0→0.4 只差 1.1% | ✓ 同源（毛细通道小） |
| B-18：`norm_smooth` 是权衡不是最优 | 不冲突（本改动不碰 `norm_smooth`） |
| B-1f/g：`cells per seed` 是控制变量 | ⚠ **本阶段换 @@\Delta x@@ 到 62.5 nm ⇒ 必须重测** |
| T4：B1 @@k_{\rm part}=1@@，@@\Gamma\equiv0@@ | ✓ §4.7 沿用 |
| `nstar_conv` 证书（12 变体能谱一致） | ⚠ 建表复制后**重复项** ⇒ 需检查证书不被破坏 |

### 6.8 ★ 涌现 vs 规定（防自欺表 —— **本文件最重要的一张表**）

| 现象 | 性质 | 依据 |
|---|---|---|
| 板条数目、形状、堆叠几何 | **涌现**（形状与堆叠形态） | 由形核输入 + 动力学决定 |
| **块内有几根板条** | ⚠ **规定，不是涌现（A8 修正）** | 根数 = **播了几个同变体核**（§9.2 场数 1+6=7）；引擎里**没有**任何板条分裂/合并机制能改变它（`nuc_cfg()` 还要显式调用）。**涌现的只是它们各自长成什么形状** |
| **变体分组 / block–colony–packet 本身** | ⚠ **规定（A8 补行）** | @@v(\alpha)@@ 由播种时手写；`LevelSetMulti` 只存 `df/eps0/npref/atab/wtab`，**没有任何取向自由度** —— 而 `RESEARCH_INTENT §2.2` 要的正是板条"**自发**按 Burgers 分组" |
| **@@M(\mathbf n)@@ 的 @@\beta_h=3.5/\beta_w=2.3@@** | ⚠ **规定（A8 补行）** | `_r1_exp.py:712` 的**设计参数**；§6.6 的整个量级结论都建在 @@e^{-\beta_h}@@ 上 |
| **核的形状 / 位置 / 取向** | ⚠ **规定（A8 补行）** | `SHAPES` / `centers`，`_r1_exp.py:71-75, 555-601` |
| **@@\mathbf n_{\rm ref}@@ 的退化** | ⚠ **数值规定（A8 补行）** | §2.3 的守卫决定 @@M_{\rm eff}@@ 是 0.0302 还是 0.116–0.497（E-1/E-3） |
| 界面**是否**存在（分离 vs 合并） | **半规定** | 场结构规定"它们一开始就是两个对象"；**不合并**才是涌现的 —— 而按 §6.6.1，主因是 **κ≡0 的结构性结果** |
| 界面位置 | 涌现（但见 §6.6：**几乎不动**） | — |
| @@\gamma_\Sigma@@ 的**数值** | **规定**（输入） | §3.2/§4.3 |
| @@\theta@@（取向差） | **规定**（输入） | §2.2 |
| @@\psi@@（膜的有无） | `auto` 臂：**涌现**；`dry/wet` 臂：规定 | §4.5 |
| @@\Gamma_i@@（溶质） | **不存在**（Window C 暂缓） | §4.7 |

> ⚠ **必须写进一切结论的一句话**：
> **"板条被低角晶界分隔"这件事，在本模型里是"场结构 + 低迁移率"的**半规定**结果；
> 本阶段真正**涌现**的是：板条各自的长大几何、堆叠形态、界面是否移动（不动）、
> 以及 `auto` 臂里膜会不会自发退湿。**

### 6.9 已知失效模式 / 不可观测项

| # | 失效/不可观测 | 怎么办 |
|---|---|---|
| 1 | **膜厚 @@h@@ 不可观测** | 不报 @@h@@。只报面能、面积、@@\psi@@ |
| 2 | @@\theta@@ 无自由度选取机制（层级 1 弹性不依赖 @@\mathsf r_\alpha@@） | 报"@@\theta@@ 是输入"；**不得**声称"取向差自组织" |
| 3 | @@\kappa@@ 仍由网格算（A-1 未解决） | 沿用 `norm_smooth=4`；**报 m=0 与 m=4 两档** |
| 4 | 低角晶界的 @@\mathbf n@@ 依赖设为 0 | 记账 S-4 |
| 5 | 低角晶界迁移率用 @@M(\mathbf n)@@（机制不同） | 记账 S-5；做 @@M_{\rm LAGB}@@ 敏感度 |
| 6 | 薄膜力学容纳（层级 2）未实现 | 记账；只影响 F2，本阶段主臂是 F3 |
| 7 | 场数上限 | **结构上限 @@nreg\le127@@**（`region()` 用 `int8`，**128 会静默变 −128**，`_bkr` B1 实测）；**本阶段实取 @@M=6@@ ⇒ `nreg=7`** |

---

## §7 建模近似记账表（**推翻时必须能回溯**）

| # | 近似 | 后果 | 怎么检验 | 何时作废 |
|---|---|---|---|---|
| **S-1** | 层级 1：@@\boldsymbol\varepsilon^0@@ 不含 @@\mathsf r_\alpha@@ | 同变体板条间无弹性相互作用 ⇒ 无"容纳"项 | 与层级 2 对照（未来） | 做 F2 薄膜/力学容纳时 |
| **S-2** | 零厚度折叠丢弃膜的**体积** | 板条周期少 @@\sim3\%@@ | 量 @@t_f/(t_l+t_f)@@ | 若 @@t_f/t_l>10\%@@ |
| **S-3** | @@\Gamma_i@@ 冻结为 0 | 薄膜无化学身份 | 已由 T4 判（@@k_{\rm part}=1@@） | Window C / B2 开工 |
| **S-4** | @@\gamma_{\rm LAGB}@@ 取**各向同性** RS | 倾转/扭转差别被抹掉 | 存转动轴，查分布 | 有倾转/扭转分辨数据 |
| **S-5** | 低角晶界迁移率 = @@M(\mathbf n)@@ | 机制不同（位错芯 vs 界面） | @@M_{\rm LAGB}@@ 敏感度扫描 | 有低角晶界迁移率数据 |
| **S-6** | @@L_\psi,W,\kappa_\psi@@ 为 **[占位]** | @@\psi@@ 的时间尺度 | 三档敏感度（必须做） | 有界面动力学数据 |
| **S-7** | 取向差 @@\theta@@ 为**输入** | 不能声称自组织 | — | 加取向自由度/层级 2 |
| **S-8** | 仍用 @@\Delta x@@ 上的 @@\kappa@@ | 见 A-1 | m=0 / m=4 双报 | 加曲率重构 |
| **S-9** | ★ **新增（E-8b）**：$$\psi$$ 沿面变化带来的**切向 Marangoni 项** @@-\nabla_\Sigma\gamma_\Sigma@@ **未实现**；固-固面无面内流动通道，该项应由体相弹性承担，而弹性只吃 $$\boldsymbol\varepsilon^0(\text{region})$$ | 面上"干/湿"过渡带的力平衡**不完整** | 量 $$\lvert\nabla_\Sigma\psi\rvert$$；$$\psi$$ 均匀时该项为零 | 加面-体弹性耦合 |
| **S-10** | ★ **新增**：$$\kappa_{\max}=2/\Delta x$$（§6.6.2）是**假设**，未证伪 | 位移上界的**绝对值** | 从落盘 `snap_*.npz` 离线量 `\|κ\|` 分布 | 量到真实 κ 分布 |
| **S-11** | ★ **新增（E-8a）**：Gibbs–Thomson 刚度里 $$\tfrac{\kappa_\psi}{2}\lvert\nabla_\Sigma\psi\rvert^2$$ 那一项未计入 | 只在 $$\psi$$ 有面内梯度时非零 | 同上 | 实现面带梯度能 |
| **S-12** | ★ **新增（E-6）**：$$\gamma_{\alpha'\beta}$$ 借自**扩散型** α+β 平衡界面（Murzinova 2017），外推到位移型 B1 | C-1 的定量余量 | 找同机制的界面能数据 | 拿到 B1 专用值 |

---

## §8 可检验预言（**阶段 3 的判据从这里出**）

| # | 预言 | 可否证判据 | 若被否证意味着 |
|---|---|---|---|
| **P-1** | **块内界面在 700 步内位移 < 0.12 @@\Delta x@@**（**有守卫**） | 量界面位置 vs 步数，拟合斜率 | 我的 §6.6.2 量级分析错了 |
| **P-1b** | ★ **主判据**：由 F3 上**实测 κ** 预测的全程位移 < 0.05 @@\Delta x@@，且实测 @@\Delta pos@@ 与之一致 | 逐步量 F3 的 κ 分布与 `Δpos`；用 `d=M_{\rm eff}\gamma_\Sigma\kappa t_{\rm sim}` 对账 | §6.6.2 的量级分析错了 |
| **P-2** | **`auto` 臂从 @@\psi\equiv1@@ 出发会自发退湿（@@\bar\psi\to0@@）** | @@\bar\psi(t)@@ 单调降 | **C-1 润湿判据错了** ⇒ 薄膜可稳定 |
| **P-3** | ★ **改写（E-4）**：界面失平后，**位移线性正比于 γ_Σ**；物理 γ（0.15–0.4）下 < 0.12 @@\Delta x@@，而 @@\gamma=1.1@@（`wet` 臂）应给出 **≈7.3×** 于 @@\gamma=0.15@@ 的位移 | **配对臂**：同一装置只改 @@\gamma_\Sigma@@，量位移比是否 ≈ γ 之比 | 若"扫 γ_Σ 完全无差别" ⇒ **界面一直保持 κ≡0**（那也是 6.6.1 的结论，但要报明） |
| **P-4** | 6 根同变体板条**各自长大**，不出现"一个场吃掉另一个" | 每根板条的 @@V>0@@ 且单调；`nslab_n ≡ 6` | 数值格式在 F3 上失稳 |
| **P-5** | 块的长径比由**排布**决定，单根板条的长径比由**动力学**决定 | 分别量 @@LW_{\rm lath}@@ 与 @@LT_{\rm block}@@ | 与已有 R1 结论冲突 |
| **P-6** | ~~界面面积单调不增~~ ⛔ **作废（E-9）**：该恒等式只对无体驱动、无三叉线的闭合界面成立；归档 `A_tot` 实涨 ×7.8–8.9。**若真要用，必须只对"单根孤立板条的 F1 面积在无长大时"用** | — | — |
| **P-7** | ★ **新增**：`de=0` 的配对被守卫 ⇒ `ncmp` 为 NaN、`facet_nref` 返回 `npref`、@@M_{\rm eff}/M_0=0.0302@@ | `_bk_engine_identity.py` **T-2.1/T-2.3** 三行探针 | 守卫被"去重优化"掉 |

---

## §9 与分辨率的关系（**阶段 3 的盒子怎么定**）

### 9.1 需要解析什么

| 对象 | 尺寸 | 需要几胞 | @@\Delta x@@ 上限 |
|---|---|---|---|
| 板条厚 @@T@@ | 0.25–0.5 µm | ≥4 | 62.5–125 nm |
| 板条宽 @@W@@ | 0.5–1 µm | ≥8 | ≤125 nm |
| 板条长 @@L@@ | 4–7 µm | ≥32 | ≤200 nm |
| **块跨距**（6 根堆叠） | @@6T+5g\approx@@ 1.8–4 µm | — | 盒 @@\ge@@ 2× 跨距 |
| 薄膜 @@h@@ | 5–20 nm | **永不解析** | — （用 Gibbs 面） |

### 9.2 推荐盒子（**阶段 3 主臂**）

| 参数 | 值 | 理由 |
|---|---|---|
| @@N@@ | **192** | 与 R1 标准同规模 ⇒ 单步成本已知 |
| @@\Delta x@@ | **62.5 nm** | **R1 标准的一半** ⇒ @@T@@=250 nm 有 **4 胞**（R1 只有 2.4 胞） |
| @@L@@ | **12 µm** | 装得下 1.8–4 µm 的块 + 长大余量 |
| 场数 | @@1+6=7@@ | **比现在的 13 少** ⇒ 单步更快 |
| 步数 | 700 | 与 R1 可比 |
| 预算 | **~2 h/臂**（估，待 `_bench` 实测） | |

### 9.3 与 R1 口径的关系（**必须同时报**）

* `cells per seed` 是已识别的控制变量（B-1f/B-1g）⇒ 换 @@\Delta x@@ **触发重测**；
* 板条厚从 2.4 胞 → 4 胞 ⇒ **`ΔT:ΔL` 读数会变**，不得与 R1 的 0.027 直接比；
* ⇒ 阶段 3 同时跑一个 **@@\Delta x=125$$ nm 对照臂**（同一物理种子）作为跨分辨率检查。

### 9.4 ★★ `norm_smooth` 与薄板条**冲突**（本阶段实测发现，v1 没有）

`norm_smooth=m` 把 @@\nabla d@@ 在 @@(2m+1)^3@@ **胞**上做盒滤波。
在 @@\Delta x=62.5$$ nm 上 @@m=4@@ ⇒ **±250 nm**，而板条**厚 250 nm**
⇒ 滤波窗**横跨整根板条** ⇒ 界面法向失去意义。

**四臂实测（★★ 单变量，只差 `norm_smooth`；`_bk_scan.py` 汇总，原始 CSV 在 `_exp/_bk_f3smoke/<臂>/`）**：

| `norm_smooth` | @@\Delta pos@@（120 步） | `ncomp_1` 末 | @@V_1/V_2@@ 末（µm³） | `nslab_n` | `box_touch` | 判读 |
|---|---|---|---|---|---|---|
| **0** | **−0.010 @@\Delta x@@** | 4 | **0.4976 / 0.4968**（对称到 **0.2%**） | 2 | 0 | ✓ **干净** |
| 1 | +0.505 @@\Delta x@@ | 19 | 0.9221 / 0.5789（**+59%**） | 2 | 0 | ✗ 第 100–120 步**突发碎裂** |
| 2 | +0.400 @@\Delta x@@ | 23 | 0.8977 / 0.5669（**+58%**） | 2 | 0 | ✗ 同上 |
| **4**（R1 生产默认） | +0.146 @@\Delta x@@ | **30** | 0.954 / 0.597（**+60%**） | 2 | 0 | ✗ 同上 |

* **`box_touch` 全为 0** ⇒ 突发**不是**盒壁碰撞；
* `nslab_n` **四臂全 = 2** ⇒ **主判据（拓扑）对这个问题不敏感** ⇒ 量具是稳的；
* 但**几何量**（`V`、`Δpos`、`ncomp`）在 @@m\ge1@@ 上**全部不可用**。

⇒ **在 @@\Delta x=62.5$$ nm + 250 nm 板条这个配置下，`norm_smooth\ge1` 会碎裂，必须用 `m=0`。**

> ⚠⚠⚠ **但这个结论在本轮被后续数据打了折 —— 必须与 §9.5 一起读，不得单独引用。**
>
> 上面 4 个臂都在 **@@L=4$$ µm（@@N=64@@）** 的**小盒**里跑。
> 更长、带守卫的臂 `ns0_v2guard`（150 步）实测：
> 板条沿 @@\mathbf a@@ 从 2397 nm 长到 **4724 nm > 盒 4000 nm**
> ⇒ **周期自接触** ⇒ `box_touch=1`、`ncomp` 从 1 爆到 **31**、@@V@@ 在 150 步突跳。
> 而 @@m\ge1@@ 的臂恰好在 **100–120 步**碎掉 —— **时间点与"长到盒壁"吻合**。
> ⇒ **"@@m\ge1@@ 碎裂"被"盒太小"这个混杂因子污染 ⇒ 不能据此判 `norm_smooth`。**
> ⇒ 在**足够大的盒**里重测 `norm_smooth` 列为**待办**。

**可选出路（阶段 3 用；但必须在足够大的盒里复核）**：
1. **`m=0`（当前采用）** —— 保住板条，A-1 的角噪声回来；
2. `m=1`（±1 胞）折中 —— **需在大盒里重测**（上表的"碎裂"不可信）；
3. 把 @@\Delta x@@ 再减半到 31.25 nm（@@N@@ 不变 ⇒ 盒更小，**与 §9.5 冲突**）；
4. 保持 `m=0`，把 A-1 归因到**板条长径比**而不是块结构上
   —— 本轮实验的主判据 `nslab_n`/`nf3_col` 是**拓扑量**，对尖端角噪声不敏感（上表已证）。

> **⇒ 记两条硬约束进阶段 3 设计**：
> **(1) `norm_smooth` 的物理窗 @@(2m+1)\Delta x@@ 必须显著小于最薄特征（板条厚）；**
> **(2) 主判据必须用对数值噪声不敏感的**拓扑量**（`nslab_n`/`nf3_col`），
> 几何量（`V`/`Δpos`/`ncomp`）只作辅助。**

### 9.5 ★★ 盒子必须按**实测长大速率**定（本阶段最重要的设计约束）

**实测**（`_bk_chk1.py`，`ns0_v2guard`，@@\Delta x=62.5$$ nm）：板条沿 @@\mathbf a@@ 的长度

| step | 0 | 50 | 75 | 100 | 125 | 150 |
|---|---|---|---|---|---|---|
| @@a_1@@ [nm] | 2397 | 2687 | 2732 | **3718** | **4554** | **4724** |
| `ncomp_1` | 1 | 1 | 1 | **3** | **9** | **31** |
| `box_touch` | 0 | 0 | 0 | 0 | 0 | **1** |

$$
\frac{d(\text{板条长})}{d\,\text{step}}\approx\frac{4724-2397}{150}=\mathbf{15.5\ nm/step}
\quad(=0.25\,\Delta x/\text{step})
$$

与解析估计 @@2v_{\rm tip}dt=2\times0.35\times2.679\times10^{-8}=18.8$$ nm/step@ @ 同量级 ✓。

**⇒ 设计判据**：@@\text{盒长}\ \ge\ \text{种子长}+2\times(\text{步数}\times15.5\ \mathrm{nm})\ +\ \text{余量}@@

| 步数 | 板条终长 | 需要盒长 | @@N@@（@@\Delta x=62.5$$ nm@@） | 代价 |
|---|---|---|---|---|
| 400 | 8.6 µm | ≥17.2 µm | 275 → **288** | 3.4× @@N=192@@ |
| **200** | **5.5 µm** | **≥11 µm** | **176 → 192** ✓ | **1×** |
| 700 | 13.2 µm | ≥26 µm | 416 | 10× |

> ### ⇒ **阶段 3 采用：@@N=192@@、@@\Delta x=62.5$$ nm（@@L=12$$ µm）、200 步。**
> 700 / 400 步都**装不下** —— 而 R1 的 700 步之所以没炸，是因为它 @@\Delta x=125$$ nm
> （同样 700 步只长 3.3 µm，@@L=24$$ µm 装得下）。
> ⚠ **这也意味着 §9.4 的四臂对照必须在大盒里重做**（它们的"碎裂"是盒壁造成的）。

---

## §10 待实现的接口清单（**给阶段 2 用，不是本阶段的结论**）

| # | 内容 | 必做/选做 |
|---|---|---|
| I-1 | `vmap` 板条表（变体 + 转动矢量）并派生 `df/eps0/npref/atab/wtab` | **必做** |
| I-2 | ★★ **@@\lVert\Delta\boldsymbol\varepsilon^0\rVert=0@@ 的配对（= @@v(k)=v(l)@@ 且 @@k\ne l@@）必须把 `ncmp[k,l]` 置 NaN** —— **不是** v1 写的"`k=l` 时"。因为 F3 是 @@k\ne l@@，而 `argmin_normal(C,0)` 返回**有限垃圾向量**（实测 `[0.01,0,0.99995]`）⇒ 回退永不触发；无守卫时 @@M_{\rm eff}/M_0@@ 从 0.0302 变 **0.116–0.497**。**并留回归判据**（P-7） | **必做（已实现）** |
| I-3 | `facet_gamma(k,larr)` 逐胞 @@\gamma_\Sigma@@（利用 @@\gamma_0@@ 线性） | **必做（已实现）** |
| I-4 | Read–Shockley @@\gamma_{\rm RS}(\theta)@@ + **12 个纯转动（622）** 的 disorientation（含 @@\theta<30^\circ@@ 对照）。⛔ **禁止**按 24 元素 + naive 迹公式实现（会 NaN） | **必做（已实现）** |
| I-5 | @@\psi@@ 面带 + (4.9) 的 AC 步。⚠ **动手前必须先定义并验证 @@\nabla_\Sigma^2@@** —— 引擎没有面网格，直接对 3D 带胞做 @@\nabla^2@@ 得到的是**体** Laplacian（E-8）。候选 @@\nabla_\Sigma^2\psi=\nabla^2\psi-(\mathbf n\cdot\nabla)^2\psi@@ | **必做，但先补算子定义** |
| I-6 | 全量状态落盘（`region` 图 + 带内稀疏 @@\varphi@@）到 F 盘 | **必做**（用户明确要求） |
| I-7 | 量具：板条数/根、块、低角界面面积、界面位移、@@\psi@@ 均值 | **必做** |
| I-8 | 层级 2 弹性（@@\boldsymbol\varepsilon^0@@ 带 @@\mathsf r_\alpha@@） | 选做（本阶段不做） |
| I-9 | 面上 @@\Gamma_i@@ 输运 | 不做（Window C） |

---

## §11 待用户裁定 / 需注意的分歧

| # | 事项 | 我的建议 |
|---|---|---|
| **D-1** | **B1 里板条间的物理实体按推导是"干低角晶界"（C-1/C-3），不是 β 薄膜。** 用户指示要"板条间有 Gibbs 面形成的薄膜"。 | **两臂都跑 + `auto` 判决臂**（§4.5）。默认主臂 = `wet`（尊重指示），配对臂 = `dry`（物理结论），`auto` 给出判决。**不改用户的实验目标，只增加一个对照。** |
| **D-2** | @@\gamma_{\alpha'\beta}@@ 用的是 Murzinova 2017 的计算值 0.30–0.43（600 °C） | 先用作 **[文献]**；C-1 的余量 @@\ge1.5\times@@（600 °C @@G@@ 口径下 @@\ge1.88\times@@），**但有三条前提**（§3.2(c)：`a` 型位错；§4.4.3：跨机制借用；溶质）。若用户有实验值请替换 |
| **D-3** | 阶段 3 主盒从 R1 的 @@\Delta x=125$$ nm 改为 **62.5 nm** | 必须改：R1 分辨率下 @@T@@ 只有 2.4 胞，"板条被分隔"根本量不准 |
| **D-4** | 取向差 @@\theta@@ 在层级 1 下是**输入**，不是涌现 | 如实报；不声称"取向差自组织" |
| **D-5** | ★ **新增**：**`de=0` 守卫是 C-1/§6.6 结论的一部分**，不是实现细节 | 已实现（`_bk_engine_identity.py` T-2.1/T-2.3 回归判据）。**若将来为省内存把重复 `eps0` 去重，必须同步保留 `facet_nref` 的回退** |
| **D-6** | ★ **新增**：**`norm_smooth` 与薄板条冲突（§9.4）** | 主臂用 `norm_smooth=0`，并跑 `m=1` 配对臂；**报告里必须写清"用了哪个 m、为什么"**，因为 R1 的归档读数全部是 `m=4` |
| **D-7** | ★ **新增**：**薄膜在 B1 里"无热力学地位"**（C-1），用户要的薄膜臂是**人为规定的亚稳面能** | 三臂（`dry`/`wet`/`auto`）都跑；`auto` 是判决臂。**不改用户的实验目标** |

---

## 附录 A —— 推导中**必须数值核验**的三件事（阶段 1 自检脚本）

| # | 核验 | 脚本（待写） | 通过判据 |
|---|---|---|---|
| A-1 | **12 个纯转动（622）** 下 disorientation = 裸角（成立范围 @@\theta<30^\circ@@）；⛔ **禁止 24 元素 + naive 迹公式**（反演 @@\mathrm{tr}=-3@@ ⇒ NaN） | `_bk_verify.py` **A-1**、`windowB_lath._selftest` **S-1/S-2** | 12 元；@@\theta\le5^\circ@@ 逐位相等；偏差阶 **slope=3.000** |
| A-2 | @@\gamma_{\rm RS}@@ 的 @@C^1@@ 与数值表 | `_bk_verify.py` **A-2** | 表 3.1 八档 **8/8 PASS**；@@C^1@@ 通过 |
| A-3 | @@\psi@@ 方程的不动点 + `auto` 退湿 | `_bk_verify.py` **A-3** | @@\psi\equiv0,1@@ 逐位不动；@@\gamma_f>\gamma_{\rm dry}@@ 时单调退湿 |
| A-4 | **@@de=0@@ 守卫回归判据（P-7）** | `_bk_engine_identity.py` **T-2.1/T-2.3** | `ncmp[1,2]` 全 NaN；`facet_nref` 返回 `npref` |
| A-5 | **引擎改动对生产路径逐位无害** | `_bk_engine_identity.py` **T-1** | 12 变体 + `lath=None` ⇒ `phi` **逐位相同**、`region` 翻转 0 |

## 附录 B —— 文献出处

| 量 | 值 | 出处 |
|---|---|---|
| @@\gamma_{\alpha'\beta}@@ (Ti-6Al-4V) | 0.201–0.337 J/m² @975 °C；0.298–0.429 J/m² @600 °C | Murzinova M.A., *Lett. Mater.* **7**(1) 55–59 (2017), DOI `10.22226/2410-3535-2017-1-55-59` 【读到摘要全文，正文未读】 |
| @@a_\alpha,c_\alpha,\mathrm{Ms}@@、板条尺寸 | 见 `WINDOWB_PARAMS.md` §1 | 该文件已登记 DOI |
| @@\theta_m=15^\circ@@、RS 形式 | 教科书标准 | 【文献，未逐条核 DOI】 |
