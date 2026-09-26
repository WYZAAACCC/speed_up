# LATH_PROBLEM_FOR_EXPERTS.md —— 板条形貌长不出来：问题、代码定位与复现指南

> 生成日期 2026-09-26 · 分支 `main` · 仓库 `github.com/WYZAAACCC/speed_up`
> 本文档的目的是**让第三方能独立复现并定位**以下问题。所有命令都可直接复制执行。

---

## 0 一句话问题

在 Window B 的 level-set + 体相场表示里，我们实现了「界面**迁移率**各向异性」`M(n)`
（双轴，轴向由 rank-1 不变平面分解给出），并用三条独立判据证明它**实现正确且确实生效**
（逐胞反推 `vnk/v_theory` 中位数 0.94~1.16）。**但它仍然无法塑造出板条形貌**：

* 把晶核种子设成 `6:1` 的长条，演化 700 步后被**抹平到 1.54:1**（圆盘种子是 1.40）；
* 末态 长/厚 只有 `2.6~2.9`，而文献 Ti-6Al-4V 的 `alpha'` 板条是 `10~30`；
* 即存在一个**比 `M(n)` 各向异性更强**的「等轴化机制」，**尚未定位**。

**请专家帮助定位这个等轴化机制。**

---

## 1 背景（最小必要）

* 目标物理：`beta -> alpha'` 板条马氏体（**位移型**、无扩散、athermal）。
* 数值表示：`LevelSetMulti`（12 个变体的 `phi` 场 + 1 个母相 = 13 个区域；
  `region = argmin_k phi_k`）。界面零厚度（level-set），体相量（弹性、溶质）在体相场里。
* 界面动力学：`v_n = M(n) * [ dG - gamma(n) * kappa ]`
  （`dG` 含化学驱动 `df` 与弹性驱动 `ed`；`kappa` 为差分场的曲率）。
* **物理动机（关键）**：位移型界面靠**界面位错的保守滑移**迁移（Olson–Cohen / Christian），
  位错只能在其**滑移面 = 惯习面 = 不变平面**内滑移 ⇒ 面内长大容易、**法向长大必须容纳失配**
  ⇒ 于是

```
    M(n) = M0 * exp[ -beta_h * (n . n_hab)^2 - beta_w * (n . w)^2 ]
```

  其中 `n_hab` = 惯习面法向（= 弹性最省能法向，由 `eps0[v]` 的最小化给出），
  `a` = rank-1 分解的位移方向（= 板条**长轴**），`w = n_hab x a`（= 板条**宽度方向**）。
  标定：`beta_h = 3.5`、`beta_w = 2.3`，由「观测板条 长/厚 ~25、长/宽 ~10」反推，
  且两条独立路径（失配位错环形成能 ~0.42 J/m^2；观测纵横比）互校自洽。

---

## 2 问题（精确陈述）

### 2.1 现象 A：长条种子被抹平（**主问题**）

`A` 实验：24 个长条晶核（每个变体 2 个），种子面内为椭圆 `elong = 6`（长/宽 = 6），
厚 10 胞。演化 700 步后，按**连通块 + 中位数**口径测形状：

| 实验 | 种子 长/宽 | 末态 长 | 末态 宽 | 末态 厚 | 长/厚 | **长/宽** |
|---|---|---|---|---|---|---|
| **E6** | **6.0** | 1.020 | 0.715 | 0.379 | 2.58 | **1.54** |
| E1 | 1.0 | 0.836 | 0.656 | 0.311 | 2.82 | 1.40 |
| LR1 | 1.0 | 0.815 | 0.650 | 0.295 | 2.89 | 1.39 |
| 文献板条 | ~10 | 1–20 | 0.25–0.9 | 0.1–0.3 | **10–30** | ~10 |

`单位：um。`

**弹性驱动已排除（2026-09-26 实测）**：关掉弹性（`--noelastic 1`）后 长/宽 = **1.47**，与开弹性的 1.54 **几乎相同** ⇒ 等轴化**不是**弹性驱动造成的。

**读法**：种子设 6:1，末态只剩 1.54:1 ⇒ 形状被强烈等轴化。
而 `M(n)` 预测面内两方向的速度比应为 `Mfac_a : Mfac_w = 1.0 : 0.100`
⇒ 长/宽 本应趋于 ~10。**实际只有 1.54。**

### 2.2 现象 B：形状读数对 dx 不收敛（次要但致命）

同一个孤立单核（R = 0.3 um，厚 0.2 um），只改 `dx`：

| 档 | dx | 末态 厚 | aspect |
|---|---|---|---|
| F1 | 20 nm | 0.497 um | 2.25 |
| F3 | 10 nm | **0.258 um** | 3.05 |

⇒ `dx` 减半、厚度**减半** ⇒ 绝对厚度读数**尚未收敛**，不能报进论文。

### 2.3 现象 C：变体-变体界面取向完全随机（独立缺口）

`M6c`（变体-变体界面法向 vs 两变体的 rank-1 相容法向）= **59.9 deg**，随机对照 59.8 deg
⇒ 变体之间的界面**没有**落在不变平面上（自协调没有发生）。
（注：变体-**母相**界面是好的：宽面占比 `P(|n.n_hab|>0.8)` = 0.45–0.69，随机 0.20。）

---

## 3 如何复现（可直接复制）

### 3.1 环境

```bash
# Windows 侧（PowerShell）进入 WSL；项目在 F 盘
wsl.exe -d Ubuntu -- bash -c "cd /mnt/f/speed_up/pipeline/ca_pf_framework && <下面的命令>"
```

* Python 必须用 **ml 环境**：`/root/miniconda3/envs/ml/bin/python`
* **必须设** `PYTHONDONTWRITEBYTECODE=1`（9p 文件系统上 .pyc 会让 Python 跑旧字节码）
* 机器：20 逻辑核；单条 level-set 轨迹只吃 ~1 核 ⇒ **多档并行**才是最大化利用

### 3.2 复现「长条被抹平」（主问题，约 33 min）

```bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1

# E6：长条种子（elong=6）
OMP_NUM_THREADS=10  _chk_m6_route.py --tag E6 --N 80 --dx 2e-8   --nplate 2 --rfrac 0.1875 --plate_dx 10 --df 2e8 --nstep 700   --mob_beta 3.5 --mob_beta_w 2.3 --elong 6.0

# E1：圆盘种子（对照，elong=1）
OMP_NUM_THREADS=10  _chk_m6_route.py --tag E1 --N 80 --dx 2e-8   --nplate 2 --rfrac 0.1875 --plate_dx 10 --df 2e8 --nstep 700   --mob_beta 3.5 --mob_beta_w 2.3 --elong 1.0

# 测定（按连通块 + 中位数；这是**唯一可靠**的形状口径）
 _chk_lath_final.py results_m6route_E6_final.npz results_m6route_E1_final.npz
```

预期输出（E6）：`长/厚 中位 2.58`、`长/宽 中位 1.54` ⇒ 种子 6:1 被抹平。

### 3.3 复现「M(n) 其实是正确的」（用来排除"Mfac 没生效"）

```bash
 _dbg_vnk.py        # 逐胞反推 vnk vs M*df*Mfac
```

预期：`ratio eff/theory` 的**中位数** ≈ 1.0（n/w/a = 1.161 / 1.066 / 0.938），
而**均值**是 5.59 / 3.95 / 1.48 ⇒ **均值被尾部污染**。这是本项目的关键教训：
`vnk` 与 `dG` 在界面上是**重尾分布**，判形状/速度**只能用中位数**。

```bash
 _dbg_mfac.py            # Mfac 在界面上的方向分布（应：|n.n_hab|->1 处最小）
 _dbg_plane_med.py       # 平界面速度比（中位数口径）
 _chk_rank1.py           # D12: rank-1 分解 + 按 npref 选解（应 12/12 通过）
```

### 3.4 复现「dx 不收敛」（现象 B，约 11 + 55 min）

```bash
# dx = 20 nm（L=1.6um, N=80）
 _chk_single_lath.py --tag F1 --N 80  --dx 2e-8 --R 3.0e-7 --t 2.0e-7     --df 2e8 --nstep 2000 --beta 3.5 --beta_w 2.3
# dx = 10 nm（L=1.6um, N=160）—— 这一步较慢（~11 s/步）
 _chk_single_lath.py --tag F3 --N 160 --dx 1e-8 --R 3.0e-7 --t 2.0e-7     --df 2e8 --nstep 800  --beta 3.5 --beta_w 2.3
```

预期：F1 厚 0.497 um、F3 厚 0.258 um ⇒ **dx 减半、厚度减半**。

### 3.5 判定「等轴化是否来自弹性驱动」（我们正在跑）

```bash
# NE1 = 关弹性驱动；NE0 = 开弹性（对照）。同一长条种子。
 _chk_m6_route.py --tag NE1 --noelastic 1 --N 80 --dx 2e-8 --nplate 2   --rfrac 0.1875 --plate_dx 10 --df 2e8 --nstep 700 --mob_beta 3.5 --mob_beta_w 2.3 --elong 6.0
 _chk_m6_route.py --tag NE0 --noelastic 0 --N 80 --dx 2e-8 --nplate 2   --rfrac 0.1875 --plate_dx 10 --df 2e8 --nstep 700 --mob_beta 3.5 --mob_beta_w 2.3 --elong 6.0
 _chk_lath_final.py results_m6route_NE1_final.npz results_m6route_NE0_final.npz
```

**实测结果**（已跑完）：

| 档 | 长 | 宽 | 厚 | 长/厚 | **长/宽** |
|---|---|---|---|---|---|
| NE1（**关弹性**）| 1.040 | 0.765 | 0.490 | 2.40 | **1.47** |
| NE0（开弹性，= E6）| 1.020 | 0.715 | 0.379 | 2.58 | **1.54** |

⇒ **两者几乎相同 => 弹性驱动被排除**。等轴化来自**数值格式层**。

---

## 4 代码定位（专家请重点看这几处）

核心库：`pipeline/ca_pf_framework/windowB_surface.py`

| 位置 | 函数 / 内容 | 说明 |
|---|---|---|
| ~line 118 | `herring_stiffness` | 凸各向异性 `gamma+gamma_tt`（Lambda<1）—— 实测**无效**，保留为对照 |
| ~line 129 | `herring_stiffness_cusp` | 尖点界面能（处处凸，无需 Wulff 凸化）—— 实测对本构型不产生力 |
| ~line 661 | `LevelSetMulti._rank1_axes` | **新增**：rank-1 分解 `eps = 0.5(a n^T + n a^T)`，按 npref 选解，返回 (n_hab, a, w) |
| ~line 620 | `LevelSetMulti._pair_normals` | **新增**：配对 (k,l) 的 rank-1 相容法向表 ncmp |
| ~line 640 | `__init__` 里的 `self.wtab` | **新增**：每变体的宽度轴 w = n_hab x a |
| ~line 760 | `seed_plate(..., elong, along)` | **新增**：长条形种子（面内椭圆），elong = 长/宽 |
| ~line 1054 | `LevelSetMulti.advance` 签名 | 新增 `pair_aniso / mob_aniso / pin_min / mob_beta / mob_beta_w / facet_lam / facet_eps` |
| ~line 1197 | `advance` 内 `M(n)` 的**应用处** | `v_cell = v_cell * exp(-mob_beta*(n.n_ref)^2 - mob_beta_w*(n.w)^2)` |
| ~line 1240 | `advance` 内**配对规范形 + 速度扩展** | `sigma = where(karr<larr,1,-1); vcanon = sigma*v_cell`；EDT 按最近界面点扩展 |
| ~line 1280 | `advance` 内**推进** | `phi_k -= dt * vnk * gmag`，`gmag = _upwind_grad(phi_k, sgn)`（Godunov 迎风） |

诊断/实验脚本（全部在 `pipeline/ca_pf_framework/`）：

| 脚本 | 作用 |
|---|---|
| `_chk_m6_route.py` | 主实验驱动（RVE / 多核 / elong / noelastic / mob_beta / mb_beta_w） |
| `_chk_single_lath.py` | 孤立单核自由生长（可设 N/dx/beta/beta_w/facet/track） |
| `_chk_lath_final.py` | **★ 唯一可靠的形状测定**（按连通块 + 中位数 + 物理轴 w/a） |
| `_chk_lath_shape.py` | 同类测定（旧版，按块，含 --min 门槛） |
| `_dbg_vnk.py` | **★ 证明 Mfac 生效**（逐胞反推 vnk，中位数) |
| `_dbg_plane_med.py` | 平界面速度比（中位数口径） |
| `_dbg_mfac.py` | Mfac 在界面上的方向分布 |
| `_dbg_plane_internal.py` | 打印 advance 内部 dG_cell / Mfac / v_cell |
| `_chk_rank1.py` | D12：rank-1 分解与选解 |
| `_chk_morph_full.py` | 多维几何测定（M1–M10，含 M6q 宽面占比） |
| `_chk_m6p.py` | 变体-母相界面法向 vs 惯习面 |
| `fig_mob.py` | 可视化（三正交剖面 + 3D 点云 + 取向直方图） |

完整分析与记账：`pipeline/ca_pf_framework/LATH_FACET_PLAN.md`
（§9 beta 标定 / §10 双轴实现 / §11 反常与逐项归因 / **§12 真正原因：统计量口径** / §13 RVE 结果）

---

## 5 已排除的候选（逐条附证据，请勿重复这些方向）

| 候选 | 判定 | 证据 |
|---|---|---|
| **弹性驱动** `ed` 把长条拉回 | **排除** | NE1（关弹性）长/宽 1.47 vs NE0 1.54，几乎相同 |
| `M(n)` 没实现 / 参数没传 | **排除** | `_dbg_vnk.py`：逐胞反推/理论 中位数 1.16/1.07/0.94；`_dbg_mfac.py`：分布与解析值逐位一致 (0.0301/0.0999/1.0000) |
| 参考取向用错（用 npref 代替配对 ncmp） | **已修，但无实际效果** | 修前/修后 M6 都是 55.4 deg（A/B/C/D 四档） |
| 凸各向异性强度不够（Lambda 太小） | **排除** | `aniso` 从 0 到 0.9（凸界极限）对界面取向**零效果** |
| 尖点界面能（近奇异）能抗粗化 | **撤回** | 大面 `kappa~0`、边缘 `gamma_eff~gamma_0` ⇒ 该形式对本构型**不产生力** |
| 重初始化频率 / 速度扩展带宽 | **排除** | reinit=5 vs 25、band=6 vs 20，结论同族 |
| 种子太薄（2 胞）造成数值伪影 | **排除** | 2/6/10 胞三种子结论一致 |
| 「三方向增长次序反了」 | **是统计量假象，已撤回** | 见 `_dbg_vnk.py`：中位数口径下完全正确 |
| 变体-变体界面是否自协调 (`M6c` 随机) | **未解决（独立缺口）** | M6c = 59.9 deg ≈ 随机 59.8 |

**特别提醒（本项目反复踩到）**：`vnk` / `dG` 在界面上是**重尾**的（少数胞是均值的 ~10 倍，
它们落在弹性奇异区）。因此：
* 判「界面速度 / 形状演化」**必须用中位数或逐胞口径**；
* **不要**用 `mean`、包围盒 `extent`、`dV/A` 换算位移（斜平面上面积因子还随取向变）。
我们此前用这些量得出了 4 个错误的"反常"结论，全部已撤回。

---

## 6 我们怀疑的方向（供专家参考，非结论）

1. **弹性驱动 `ed`**（最强嫌疑）：`ed` 依赖形状，量级可达 ~5e8 > `df` = 2e8，
   有力把偏离低能形状的长条拉回。**正在用 NE1/NE0 判定**（3.5 节）。
2. **level-set 推进格式**：`phi -= dt*vnk*|grad phi|` 用 Godunov 迎风 `_upwind_grad`。
   W1 判据曾记「迎风把各向异性压低 ~8%」，但**在非轴对齐界面上的系统偏差**未做定量标定；
   建议对照 `adv_grad='central'`（代码里已有开关）。注：该函数用 `np.roll`（周期边界），
   在**域边界**会产生垃圾值（体相 |grad phi| = 1.0，边界 1–2 层 ~200）；界面在域中央时不受影响，
   但若把边界算进统计平均会得到虚假的 ~10 倍速度。
3. **曲率 `kappa` 的离散**：对只有数胞厚度的薄片，`kappa` 的数值误差可能主导，
   从而伪造出"端面收缩 => 等轴化"的效果。
4. **`dx` 收敛未达标**（现象 B）：若厚度读数 ∝ dx，则所有绝对尺寸结论都要等 dx=5 nm 档。
5. **形核是输入**这一环：真实板条的形核胚可能是**薄片状**且带晶体学取向；我们用 `elong`
   近似它，但**被抹平了** ⇒ 说明"输入一个长条种子"不足以维持长条，必须有机制**维持**它。

---

## 7 关键数据文件（都已随本次提交推送）

```text
results_m6route_E6_final.npz      # 长条种子 elong=6（现象 A 的主角）
results_m6route_E1_final.npz      # 圆盘种子对照
results_m6route_LR1_final.npz     # 有钉扎 RVE
results_m6route_LR2_final.npz     # 无钉扎 RVE（对照）
results_m6route_NE1_final.npz     # 关弹性（若已完成）
results_m6route_NE0_final.npz     # 开弹性（若已完成）
results_single_F1.json/.log       # 孤立单核 dx=20nm
results_single_F3.json/.log       # 孤立单核 dx=10nm（现象 B 的主角）
results_m6route_*_traj.csv        # 逐步轨迹
results_single_*_track.csv        # 逐时主轴跟踪
```

每个 npz 内含 `reg`（末态区域标签）、`phi`、`ncmp`、`npref`、`N`、`dx`、`f`。

---

## 8 最希望专家回答的三个问题

1. 长条种子被从 6:1 抹平到 1.54:1（**弹性已排除**）。
   我们现在的候选排序是：**曲率 `kappa` 的离散 > Godunov 迎风 `|grad phi|` > 速度扩展(EDT)**。
   请专家判断：对只有 5-10 胞厚的薄片，`kappa` 应如何离散才不会伪造出「端面收缩」？
2. 对只有 ~5–10 胞厚度的薄片，level-set 的 `kappa` 与 `|grad phi|` 应如何离散才可信？
   现在的 `dx` 收敛行为（厚度 ∝ dx）是格式问题还是物理？
3. 变体-变体界面完全随机（M6c = 59.9 deg）：在 `pair_aniso` 已开的前提下，
   还缺什么才能让界面落在 rank-1 不变平面上？
