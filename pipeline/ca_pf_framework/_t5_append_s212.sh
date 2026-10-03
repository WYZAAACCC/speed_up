#!/bin/bash
# _t5_append_s212.sh --- ★★★★★★ B 组查清：三个独立缺口（核不扁 + 生长无拉长 + facet 没跑）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
cat >> R581_T5_RESTART.md <<'EOF'

---

## §212 ★★★★★★★ 第 212 轮：**B 组查清** —— 长宽比小是**三个独立缺口叠加**

### §212.1 ③ `--facet-proj` / `--facet-excl`：**默认就是 0 ⇒ 棱面机制从未跑过**
```
3901:  ap.add_argument('--facet-proj', type=int, **default=0**)
3913:  ap.add_argument('--facet-excl', type=int, **default=0**, choices=(0,1))
我的启动器：'--facet-proj', '0', '--facet-excl', '0'      ← 等于默认值
代码逐字（1232 / 3911）：
  "⚠ `facet_proj = 0`（默认）时 `facet_project()` **根本不被调用** ⇒ 本行无副作用。"
  "`facet_project()` **一次都不被调用** ⇒ 回归（`_r30_regress.sh` 不带该开关）**逐位不变**。"
```
**⇒ ★★★ **"棱面投影"（= 让界面形成**平整宽面**的机制）**一次都没跑过**** ⇒
   **界面不会自发变平 ⇒ 形状偏圆**（**且这是**项目默认**，不是我关的** —— 但**从没被打开过**）。

### §212.2 ⑥ 界面各向异性：**开着（`aniso = 0.4`）**
```
1923:  kw = dict(aniso=**0.4**, npref=npref, band_cells=int(a.band_cells), ...)
```
**⇒ **有**界面刚度各向异性（`γ_eff = γ + γ_θθ`，Herring 项）⇒ **有一定取向偏好**；
   **⚠ 但它作用在"面内 vs 法向"上 ⇒ 只能**部分**抑制厚度，**不能**在面内把板条拉长**。

### §212.3 ④ `elong` 的**作用范围**：**只管形核，不管生长**
```
1724:  "`elong=L/W=3.75, along=a_ax, flat_end=True`"        ← 注释，讲 `seed_plate`
1724 / 1732 / 2165 / 2569 / 2631 : `elong` **全部**传给 `seed_plate(...)`
1751:  "**`fresh` 通道更彻底：它**根本不传** `elong/along/flat_end`**"
```
**⇒ ★★★ **`elong` 只用于**形核**；`advance`（生长）里**完全没有它**** ⇒
   **生长阶段没有任何"沿长轴优先"的机制** ⇒ **长宽比只能靠"保持不变"**。
**⚠ 而 `fresh`（**造新块的通道**）连 `elong` 与 `flat_end` 都不传 ⇒ **它的核更圆****
   ⇒ **新块从一开始就比 `stack` 通道的更圆**。

### §212.4 ⑦ 生长项的**数学形式**（`windowB_surface.py:774` 的 docstring）
```
∂φ/∂t + v_n|∇φ| = 0，   v_n = M[Δf − γ_eff(n) κ]     （γ_eff = γ + γ_θθ）
```
**⇒ 生长速度里**只有**：①体驱动力 `Δf`（**各向同性**）；②界面能 `γ_eff(n)`（**有各向异性** ⇒ 可影响形状）。
**⇒ **没有**任何"沿某方向更快"的项** ⇒ **面内拉长在方程层面就不存在**。

### §212.5 ★★★★★ 结论：**三个独立缺口叠加**
| # | 缺口 | 性质 | 证据 |
|---|---|---|---|
| **①** | **起点不够扁**：核 `elong = 2.0`（应 **3.75**；`flat_end=True` 那条路更没走）| **配置**（我没传 `--eng-elong`）| §210 |
| **②** | **生长**没有**拉长机制**：`elong` 只进 `seed_plate`，`advance` 里没有 | **模型结构**（不是配置）| 本轮 ④ |
| **③** | **厚度抑制不足**：`facet_project()` **一次都没跑**（`facet-proj` 默认 0）| **默认关闭**（从没打开）| 本轮 ③ |
**⇒ **所以长宽比小**不是单一原因** —— 而是：
   **核不扁（② 的起点） + 生长不拉长（② 无机制） + 只靠 `aniso=0.4` 部分抑厚（③ 缺口）**。**

### §212.6 ★★ 对"该怎么办"的直接含义（**须用户拍板**）
| 项 | 是否需要改代码 | 说明 |
|---|---|---|
| **`--eng-elong 3.75`** | **不需要**（只是传参）| **可立刻做**（但只改起点，不改生长）|
| **打开 `--facet-proj`** | **不需要**（传参）| **⚠ 但它从未被验证过**（代码说"一次都没跑"）⇒ **须先做正确性验证** |
| **给生长加"拉长"机制** | **需要改物理**（方程层面）| **⚠ 这是模型开发，不是调参** ⇒ **必须由用户决定** |
EOF
echo "已追加，现在 $(wc -l < R581_T5_RESTART.md) 行"
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/R581_T5_RESTART.md pipeline/ca_pf_framework/_t5_bcheck.sh pipeline/ca_pf_framework/_t5_append_s212.sh
git commit -F - <<'MSGEOF'
R581-T5R-s212 ★★★★★★ B 组查清: 长宽比小是三个独立缺口叠加

③ --facet-proj/--facet-excl: 定义 default=0, 我传的也是 0; 代码逐字 "facet_proj = 0(默认)时
   facet_project() 根本不被调用" / "facet_project() 一次都不被调用 => 回归逐位不变"
   => "棱面投影"(让界面形成平整宽面的机制)一次都没跑过 => 界面不会自发变平 => 形状偏圆
   (且这是项目默认, 不是我关的 —— 但从没被打开过)。

⑥ 界面各向异性: 1923 行 kw=dict(aniso=**0.4**, npref=npref,...) => 有界面刚度各向异性
   (gamma_eff = gamma + gamma_tt, Herring 项) => 有一定取向偏好; 但它作用在"面内 vs 法向"上
   => 只能部分抑制厚度, 不能在面内把板条拉长。

④ elong 的作用范围: 1724/1732/2165/2569/2631 全部传给 seed_plate(形核);
   1751 "fresh 通道更彻底: 它根本不传 elong/along/flat_end"
   => elong 只用于形核; advance(生长)里完全没有它 => 生长阶段没有任何"沿长轴优先"的机制
   => 长宽比只能靠"保持不变"; 而 fresh(造新块的通道)连 elong 与 flat_end 都不传 => 它的核更圆。

⑦ 生长项数学形式(windowB_surface.py:774 docstring):
   dphi/dt + v_n|grad phi| = 0,  v_n = M[df - gamma_eff(n) kappa]
   => 生长速度里只有 ①体驱动力 df(各向同性) ②界面能 gamma_eff(n)(有各向异性, 可影响形状);
   没有任何"沿某方向更快"的项 => 面内拉长在方程层面就不存在。

结论: 三个独立缺口叠加 —— ①起点不够扁(核 elong=2.0, 应 3.75, 且 flat_end 那条路没走);
②生长没有拉长机制(elong 只进 seed_plate, advance 里没有) —— 这是模型结构, 不是配置;
③厚度抑制不足(facet_project() 一次都没跑, facet-proj 默认 0)。

对"该怎么办": --eng-elong 3.75 不需改代码可立刻做(但只改起点);
打开 --facet-proj 不需改代码但它从未被验证过(代码说"一次都没跑") => 须先做正确性验证;
给生长加"拉长"机制需要改物理(方程层面) => 这是模型开发, 不是调参 => 必须由用户决定。
MSGEOF
git log --oneline -1
