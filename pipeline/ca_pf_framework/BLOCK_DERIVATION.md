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

> ★ **F3 的参考法向不需要新定义**：块内堆叠的板条是"宽面贴宽面"，
> 界面就是**惯习面**本身 ⇒ @@\mathbf n_{\rm ref}=\mathbf n^*_{v}@@。
> 而代码里 @@k=l@@ 时 `ncmp[k,k]=nan` ⇒ `facet_nref` **已经**回退到 `npref[k]`
> （`windowB_surface.py:2094-2101`）⇒ **回退分支恰好就是正确的那一支**。
> 【实测：读码确认】

### 2.4 取向差角

设板条的**晶格取向** @@\mathsf R_\alpha=\mathsf R_{v(\alpha)}\mathsf r_\alpha@@
（@@\mathsf R_v@@ 是 Burgers 变体转动，@@\mathsf r_\alpha@@ 是该板条的小转动）。

相对转动：@@\Delta\mathsf R_{\alpha\beta}=\mathsf R_\alpha\mathsf R_\beta^{\!\top}@@。
**取向差角**（对晶体点群 @@\mathcal S@@ 取极小，即"disorientation"）：

$$
\theta_{\alpha\beta}=\min_{\mathsf s\in\mathcal S}\arccos\!\Big(\tfrac12\big[\mathrm{tr}(\mathsf s\,\Delta\mathsf R_{\alpha\beta})-1\big]\Big)
\tag{2.2}
$$

**同变体情形是干净的**：

$$
\Delta\mathsf R_{\alpha\beta}
=\mathsf R_v\underbrace{\mathsf r_\alpha\mathsf r_\beta^{\!\top}}_{\displaystyle \Delta\mathsf r}\mathsf R_v^{\!\top}
\;\Longrightarrow\;
\theta_{\alpha\beta}=\big|\boldsymbol\omega_\alpha-\boldsymbol\omega_\beta\big|+\mathcal O(\theta^3)
\tag{2.3}
$$

（转动角在共轭下不变 ⇒ 变体转动 @@\mathsf R_v@@ **完全约掉**；
两小转动之积的角 = 转动矢量之差的一阶。）

> **自洽性检查 S-1（必须做，见 §7）**：@@\mathcal S@@ 有 24 个元素，
> 对小的 @@\Delta\mathsf r@@ 是否**真的**给出同一个 @@\theta@@？
> ⇒ 需数值核验 @@\min_{\mathsf s}@@ 在小角极限下等于裸角（附录 A 脚本）。

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

> ★★ **与现有 [占位] 的一致性核对（重要）**
>
> `WINDOWB_PARAMS.md` §5 现在把 @@\gamma_{\rm lath}@@ 记为 **0.15 J/m² [占位]**
> （注："α/α′ 低角界面文献 0.1–0.3"）。
> 表 3.1 反查：@@\gamma_{\rm RS}=0.15@@ ⇔ **@@\theta=1.83^\circ@@**（`_bk_verify.py` A-2.5 核对）。
> ⇒ **那个占位数是一个 ≈1.8° 低角晶界的 RS 值。**
> ⇒ 它不是随手填的，**现在它有推导了**：@@\gamma_{\rm lath}=\gamma_{\rm RS}(\theta)@@，
>    @@\theta@@ 从 [占位] 变成**可指定、可扫描的物理输入**（块内板条取向差）。

### 3.3 迁移率：沿用 @@M(\mathbf n)@@，并给出定量钉扎

物理：低角晶界的迁移由**位错芯扩散/攀移**控制，与高角晶界/相界**不同机制** ⇒ 用同一个 @@M(\mathbf n)@@ 是**近似**（§7 S-5 记账）。

但**符号与量级恰好都对**，因为 F3 界面的法向就是 @@\mathbf n^*@@：

$$
\frac{M(\mathbf n^*)}{M_0}=e^{-\beta_h}=e^{-3.5}=\mathbf{0.0302}\quad(\beta_h=3.5)
\qquad
\frac{M(\mathbf w)}{M_0}=e^{-\beta_w}=e^{-2.3}=\mathbf{0.1003}\quad(\beta_w=2.3)
$$

⇒ **现有的迁移率各向异性已经给块内界面 10–33× 的钉扎**，无需新增机制。【推导，参数见 `_r1_exp.py` 默认】

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

**"膜消失"这一过程的能量变化**（单位面积）：

$$
\Delta\Gamma(h)=
\underbrace{-h\,|\Delta g_{\rm chem}|}_{\text{化学收益}}
+\underbrace{\big[\gamma_{\rm LAGB}(\theta)-2\gamma_{\alpha'\beta}\big]}_{\displaystyle \equiv\ \Delta\gamma_{\rm surf}}
+\underbrace{h\,\Delta g_{\rm el}}_{\text{约束弹性能代价}}
\tag{4.4}
$$

**膜稳定（@@\Delta\Gamma>0@@）⇔**

$$
\boxed{\;\Delta\gamma_{\rm surf}\;>\;h\big(|\Delta g_{\rm chem}|-\Delta g_{\rm el}\big)\;}
\tag{4.5}
$$

**@@h\to0@@ 极限 ⇒ 经典 Cahn 润湿判据**：

$$
\boxed{\;\text{薄膜润湿低角晶界}\iff \gamma_{\rm LAGB}(\theta)>2\gamma_{\alpha'\beta}\;}
\tag{4.6}
$$

#### 4.4.1 化学通道：**B1 里关闭**（不是"暂时不做"，是**物理上不成立**）

@@\Delta g_{\rm chem}@@ 与 @@\Delta g_{\rm el}@@ 都是**体积**量，而 B1 是**位移型、无扩散**
（`RESEARCH_INTENT` §2.2 / §4.2 D2′）⇒ **β 膜不能靠成分 partitioning 稳定**。
成分通道属 **B2（α′→α+β，扩散型）**，而 B2 在 LPBF 建造期内不发生（【实测】1073 K 需 0.33 h）。

#### 4.4.2 力学通道：把数代进去

用引擎自己的数（`_r1_exp.py`：@@DF=3.5\times10^8$$ J/m³）：

| 量 | 值 | 出处 |
|---|---|---|
| @@\vert\Delta g_{\rm chem}\vert@@ | @@3.5\times10^8$$ J/m³ | 模型参数 |
| @@\Delta g_{\rm el}@@（约束弹性反对量） | @@\sim2.5\times10^8$$ J/m³ | 【实测】R1 `ed` 读数 |
| 净 @@\vert\Delta g_{\rm chem}\vert-\Delta g_{\rm el}@@ | @@\approx1.0\times10^8$$ J/m³ | 【推导】 |
| @@h=5$$ nm 时的体积项 | @@5\times10^{-9}\times10^8=\mathbf{0.5}$$ J/m² | 【推导】 |
| @@\Delta\gamma_{\rm surf}@@ 的**上界** | @@0.396-2\gamma_{\alpha'\beta}<0@@ | 见下 |

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
| **C-2** | 体积项**更**不利（@@+0.5$$ J/m²@@ at 5 nm）⇒ 连"有限厚度稳定化"也没有 | (4.5) |
| **C-3** | 因此 **B1 里板条间的物理实体 = 干低角晶界** @@\gamma_{\rm RS}(\theta)@@，而**不是** β 薄膜 | C-1+C-2 |

**余量有多大（诚实报边界）**：

| @@T@@ | @@2\gamma_{\alpha'\beta}@@ | 对 @@\gamma_m=0.396@@ 的余量 |
|---|---|---|
| 600 °C（接近 @@M_s@@=575 °C） | 0.596–0.858 | **1.51–2.17×** |
| 975 °C（远离 B1 工况） | 0.402–0.674 | **1.02–1.70×** |

> ⚠ **最不利的一档（975 °C、γ=0.201）余量只有 1.5%** —— 也就是说
> C-1 的结论在**高温端**是"险胜"。
> ⇒ 若将来采用更小的 @@\gamma_{\alpha'\beta}@@（或界面上有溶质使 @@\gamma@@ 降低），
> **润湿可能发生**。⇒ 这正是必须保留 `wet`/`auto` 两臂的**定量**理由，而不是走过场。

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
**计算代价**：@@\nabla_\Sigma^2@@ 只在界面带（@@\lvert\varphi\rvert<1.5\Delta x@@，**实测 0.023%@% of cells @ @@N=192@@）⇒ **可忽略**。

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
| @@\mathbf n_{\rm ref}(k,l)@@ | `facet_nref` :2074 | **无**（`k=l` 已回退 `npref[k]`，正好对） | 无 |
| @@\gamma_\Sigma@@ | `gamma0` 标量 | **新增** `facet_gamma(k,larr)` 逐胞表 | ★ 见下 |
| @@M(\mathbf n)@@ | `mob_beta`+`nd_ref` | **无** | 无 |
| @@\psi@@ | — | **新增** 面带上的 AC 步 | 新增参数 @@L_\psi,W,\kappa_\psi@@ **[占位]** |

> ★ **@@\gamma_\Sigma@@ 逐胞化为什么是低风险的**：
> `herring_stiffness` 与 `herring_stiffness_cusp` **都对 `gamma0` 严格线性**
> （`windowB_surface.py:317,327-328`）⇒
> 可以先用 `gamma0=1` 算出无量纲的 @@\mathrm{stk}/\gamma_0@@，**再逐胞乘** @@\gamma_\Sigma@@。
> ⇒ 不改动任何已验证的几何/迎风/Herring 代码。

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
| (4.9) | @@[L_\psi]=@@ m²/(J·s)（与界面 @@M@@ 同量纲） ⇒ @@L_\psi\gamma\sim@@ m²/s ✓ |
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
| 面积 | 不守恒，按 @@\dot A=-M\gamma\!\int\kappa^2\mathrm dA@@ 单调减 | §6.6 定量 |

### 6.5 变分一致性

@@v_n=M\big[-\delta\mathcal F/\delta\phi\big]@@ 形式下，@@\gamma_\Sigma@@ 的变分给出 @@-\gamma_\Sigma\kappa@@（Gibbs–Thomson）✓。
@@\psi@@ 的变分给出 (4.9) ✓。**两式共用同一个 @@\gamma_\Sigma(\psi,\theta)@@** ⇒ 无重复计数、无遗漏 ✓。

> ⚠ **一处必须记账的不一致（沿用现有的）**：@@\gamma_{\theta\theta}@@ 用的是
> `herring_stiffness` 的**法向**各向异性，而 @@\gamma_{\rm RS}@@ 是 @@\mathbf n@@ 无关的。
> 两者**正交且可加**（§3.1 P3），但严格说"低角晶界的 @@\mathbf n@@ 依赖"被设成了 0。
> ⇒ 记账为近似 S-4。

### 6.6 ★★ 核心：**为什么不合并**（定量，可否证）

对 F3 界面 @@\Delta f=\Delta e_{\rm el}=0@@（§5.4）⇒ @@v_n=-M_{\rm eff}\gamma_\Sigma\kappa@@。

用**网格上可能出现的最大曲率** @@\kappa_{\max}\approx2/\Delta x@@（Nyquist），
则整个仿真窗口内界面的**最大位移**：

$$
d_{\rm curv}=M_{\rm eff}\,\gamma_\Sigma\,\kappa_{\max}\,t_{\rm sim}
$$

**代入生产配置（@@\Delta x=62.5$$ nm, @@N=192@@, 700 步）**：

| 量 | 值 |
|---|---|
| @@M_{\rm eff}=M_0e^{-\beta_h}@@ | @@1.0\text{e}{-9}\times0.0302=3.02\text{e}{-11}@@ m⁴/(J·s) |
| @@\gamma_\Sigma@@（最坏：@@\theta=15^\circ@@） | 0.396 J/m² |
| @@\kappa_{\max}=2/\Delta x@@ | @@3.2\text{e}7$$ m⁻¹ |
| @@dt=0.15\Delta x/(M_0DF)@@ | @@2.679\text{e}{-8}$$ s |
| @@t_{\rm sim}=700\,dt@@ | @@1.875\text{e}{-5}$$ s |
| **@@d_{\rm curv}@@（最坏）** | **@@7.2$$ nm = @@0.11\,\Delta x@@** |
| @@d_{\rm curv}@@（@@\theta=2^\circ@@，@@\gamma=0.159@@） | **2.9 nm = @@0.046\,\Delta x@@** |

> ### ⇒ **在整个仿真窗口内，曲率驱动最多让块内界面移动 0.11 个胞。**
> ### **几何上不可能合并。**

**正对照（同一把尺子量"应该动的"）**：同一段时间里，α′/β 尖端（法向 ≈ @@\mathbf a@@，@@M\approx M_0@@）
以 @@v=M_0\Delta f=0.35$$ m/s@@ 前进 ⇒ @@6.6\,\mu@@m。

$$
\boxed{\;\frac{\text{板条长大}}{\text{块内界面曲率移动}}=\frac{6.56\,\mu\mathrm m}{7.17\,\mathrm{nm}}\approx\mathbf{915\times}\;}
$$

⇒ **两个过程相差三个数量级 ⇒ 实验能干净地把"板条长大"与"界面合并"分开**（可分辨性判据）。

**并且这与已有结论自洽**：界面能通道占驱动力的比例

$$
\frac{\gamma_\Sigma\kappa}{\Delta f}\in
\begin{cases}
0.36\%, & \kappa=1/(5\Delta x)\ \text{（近平界面实际解析曲率）}\\
3.6\%, & \kappa=2/\Delta x\ \text{（Nyquist 上界）}
\end{cases}
$$

与 A-2/A-3 已测的"界面能只占驱动 0.1–0.3%"同源 ✓（那里用的是 @@\Delta x=125$$ nm 上的**实际**解析曲率）。

**⇒ 顺带得到一条对用户很重要的结论**：

> **在当前参数区制下，把块内面能 @@\gamma_\Sigma@@ 从 0.15 换到 1.1 J/m²（干界面 vs 有膜），
> 对"会不会合并"和"块形不形成"都**没有可测影响** —— 因为毛细通道只有 0.3%。**
> ⇒ 薄膜的**动力学**作用在 B1 里可忽略；它真正的作用在（i）**溶质储存**（Window C）、
> （ii）**异变体界面的力学容纳**（层级 2）——两者本阶段都没打开。**必须写进结论。**

### 6.7 与已有结论的一致性

| 已有结论 | 本框架 |
|---|---|
| A-2：界面能只占驱动力 0.1–0.3% | ✓ §6.6 独立复算得 0.34% |
| A-3：`facet_lam` 0→0.4 只差 1.1% | ✓ 同源（毛细通道小） |
| B-18：`norm_smooth` 是权衡不是最优 | 不冲突（本改动不碰 `norm_smooth`） |
| B-1f/g：`cells per seed` 是控制变量 | ⚠ **本阶段换 @@\Delta x@@ 到 62.5 nm ⇒ 必须重测** |
| T4：B1 @@k_{\rm part}=1@@，@@\Gamma\equiv0@@ | ✓ §4.7 沿用 |
| `nstar_conv` 证书（12 变体能谱一致） | ⚠ 建表复制后**重复项** ⇒ 需检查证书不被破坏 |

### 6.8 ★ 涌现 vs 规定（防自欺表 —— **本文件最重要的一张表**）

| 现象 | 性质 | 依据 |
|---|---|---|
| 板条数目、形状、堆叠几何 | **涌现** | 由形核输入 + 动力学决定 |
| 块内有几根板条 | **涌现**（本阶段才第一次可观测） | 场数 > 变体数 |
| 界面**是否**存在（分离 vs 合并） | **~~涌现~~** ⚠ **半规定** | 场结构规定"它们一开始就是两个对象"；**不合并**才是涌现的（§6.6 定量） |
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
| 7 | 12 变体 ⇒ 场数上限 | @@M\le12@@（@@nreg\le13@@，`int8` 安全） |

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

---

## §8 可检验预言（**阶段 3 的判据从这里出**）

| # | 预言 | 可否证判据 | 若被否证意味着 |
|---|---|---|---|
| **P-1** | **块内界面在 700 步内位移 < 0.2 @@\Delta x@@** | 量界面位置 vs 步数，拟合斜率 | 我的 §6.6 量级分析错了 |
| **P-2** | **`auto` 臂从 @@\psi\equiv1@@ 出发会自发退湿（@@\bar\psi\to0@@）** | @@\bar\psi(t)@@ 单调降 | **C-1 润湿判据错了** ⇒ 薄膜可稳定 |
| **P-3** | **@@\gamma_\Sigma@@ 从 0.15 扫到 1.1 J/m² 时块几何无可测变化** | 配对臂 @@\Delta W,\Delta T,\Delta L@@ 差 < 5% | 毛细通道被低估 |
| **P-4** | 6 根同变体板条**各自长大**，不出现"一个场吃掉另一个" | 每根板条的 @@ncell>0@@ 且单调；`region` 数 = 6 | 数值格式在 F3 上失稳 |
| **P-5** | 块的长径比由**排布**决定，单根板条的长径比由**动力学**决定 | 分别量 @@LW_{\rm lath}@@ 与 @@LT_{\rm block}@@ | 与已有 R1 结论冲突 |
| **P-6** | 界面**面积**单调不增（@@\dot A=-M\gamma\!\int\kappa^2\le0@@） | 量 @@A(t)@@ | 格式产生面积（色散）|

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

---

## §10 待实现的接口清单（**给阶段 2 用，不是本阶段的结论**）

| # | 内容 | 必做/选做 |
|---|---|---|
| I-1 | `vmap` 板条表（变体 + 转动矢量）并派生 `df/eps0/npref/atab/wtab` | **必做** |
| I-2 | @@k=l@@ 时 `ncmp` 的 NaN 守卫（`de=0` 会让 `_argmin_normal` 退化） | **必做** |
| I-3 | `facet_gamma(k,larr)` 逐胞 @@\gamma_\Sigma@@（利用 @@\gamma_0@@ 线性） | **必做** |
| I-4 | Read–Shockley @@\gamma_{\rm RS}(\theta)@@ + 24 元素点群 disorientation（含小角对照） | **必做** |
| I-5 | @@\psi@@ 面带 + (4.9) 的 AC 步 | **必做**（`auto` 臂需要） |
| I-6 | 全量状态落盘（`region` 图 + 带内稀疏 @@\varphi@@）到 F 盘 | **必做**（用户明确要求） |
| I-7 | 量具：板条数/根、块、低角界面面积、界面位移、@@\psi@@ 均值 | **必做** |
| I-8 | 层级 2 弹性（@@\boldsymbol\varepsilon^0@@ 带 @@\mathsf r_\alpha@@） | 选做（本阶段不做） |
| I-9 | 面上 @@\Gamma_i@@ 输运 | 不做（Window C） |

---

## §11 待用户裁定 / 需注意的分歧

| # | 事项 | 我的建议 |
|---|---|---|
| **D-1** | **B1 里板条间的物理实体按推导是"干低角晶界"（C-1/C-3），不是 β 薄膜。** 用户指示要"板条间有 Gibbs 面形成的薄膜"。 | **两臂都跑 + `auto` 判决臂**（§4.5）。默认主臂 = `wet`（尊重指示），配对臂 = `dry`（物理结论），`auto` 给出判决。**不改用户的实验目标，只增加一个对照。** |
| **D-2** | @@\gamma_{\alpha'\beta}@@ 用的是 Murzinova 2017 的计算值 0.30–0.43（600 °C） | 先用作 **[文献]**；C-1 的余量 @@\ge1.5\times@@，不改变结论；若用户有实验值请替换 |
| **D-3** | 阶段 3 主盒从 R1 的 @@\Delta x=125$$ nm 改为 **62.5 nm** | 必须改：R1 分辨率下 @@T@@ 只有 2.4 胞，"板条被分隔"根本量不准 |
| **D-4** | 取向差 @@\theta@@ 在层级 1 下是**输入**，不是涌现 | 如实报；不声称"取向差自组织" |

---

## 附录 A —— 推导中**必须数值核验**的三件事（阶段 1 自检脚本）

| # | 核验 | 脚本（待写） | 通过判据 |
|---|---|---|---|
| A-1 | 24 元素点群下小角 disorientation = 裸角 | `_bk_pgsym.py` | 对 @@\theta\le5^\circ@@，@@\vert\min_{\mathsf s}\theta-\vert\boldsymbol\omega_\alpha-\boldsymbol\omega_\beta\vert\vert<10^{-12}@@ |
| A-2 | @@\gamma_{\rm RS}@@ 的 @@C^1@@ 与解析数值表 | `_bk_rs.py` | 与 §表 3.1 逐档一致（6 位） |
| A-3 | @@\psi@@ 方程的三条不动点 + `auto` 退湿 | `_bk_psi.py` | @@\psi\equiv0,1@@ 逐位不动；@@\gamma_f>\gamma_{\rm dry}@@ 时 @@\bar\psi@@ 单调降到 0 |

## 附录 B —— 文献出处

| 量 | 值 | 出处 |
|---|---|---|
| @@\gamma_{\alpha'\beta}@@ (Ti-6Al-4V) | 0.201–0.337 J/m² @975 °C；0.298–0.429 J/m² @600 °C | Murzinova M.A., *Lett. Mater.* **7**(1) 55–59 (2017), DOI `10.22226/2410-3535-2017-1-55-59` 【读到摘要全文，正文未读】 |
| @@a_\alpha,c_\alpha,\mathrm{Ms}@@、板条尺寸 | 见 `WINDOWB_PARAMS.md` §1 | 该文件已登记 DOI |
| @@\theta_m=15^\circ@@、RS 形式 | 教科书标准 | 【文献，未逐条核 DOI】 |
