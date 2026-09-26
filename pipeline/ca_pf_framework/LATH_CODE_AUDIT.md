# LATH_CODE_AUDIT.md —— windowB_surface.py 深度代码审计（2026-09-26）

> 审计对象：`pipeline/ca_pf_framework/windowB_surface.py`（2126 行）
> 审计方式：读代码 + **写定向数值判据复现**（不靠推理下结论）。
> 结论分三部分：**A 确认存在的缺陷（10 项）** / **B 已验证无误（6 项）** / **C 仍未定位**。
>
> ⚠ **二次更正（2026-09-26）**：初版 #1/#2 的判据**漏掉曲率项**，其具体数字**已撤回**。
> #1 保留为"格式敏感"这一事实。10 项**已全部修复并回归**，见文末 E 节。

---

## A 确认存在的缺陷

### #1 `adv_grad` 格式**影响结果**（中；原判据已撤回）

**代码**：`LevelSetMulti.advance` 内 `gmag = self._upwind_grad(...)`

**方法论更正（重要）**：本条最初写成"迎风格式有取向相关偏差：n_hab 1.83 / w 0.071 / a 1.17"。
**该结论已撤回** —— 所用判据 `v实测/(M*df*Mfac)` **漏掉了曲率项**（`dG = df - gamma*kappa`），
"比值≠1"是判据缺陷而非代码偏差。改用**逐胞反推**（`_dbg_vnk.py`：由 `-dphi/(dt*|grad phi|)`
反推实际速度，取中位数）后，三个轴向比值为 **1.161 / 1.066 / 0.938** => **`Mfac` 生效正确**。

**仍然成立**：`adv_grad` 的选择**确实改变长时程结果** —— 同一 E6 配置 700 步，
`upwind` => 长/宽 **1.54**、f=0.727；`central` => **1.75**、f=0.846；且 central 无失稳。
=> 这是**格式敏感性**问题（需做格式收敛），不是"某格式有 N 倍偏差"。

**修复**：默认 `'upwind' -> 'central'`，并记账：**这改变后续所有结果的数值**，
与审计前的归档不可逐位比较；遇陡梯度失稳可传 `adv_grad='upwind'` 回退。

### #2 `w` 方向的"几乎不动"（**已撤回**）

原写"`w` 档实测位移 = 0，而预测应为 `M*df*Mfac*dt`"。**同样撤回**：该预测值
**不含曲率项**，而此构型下 `kappa` 项主导 => 预测值本身错。逐胞口径（`_dbg_vnk.py`）
给 `w` 档比值 **1.066** => **正常**。

### #3 `suggest_dt` 用 `dG_max`（**不含 Mfac**）—— 效率损失（低）

**代码**：`advance` 里 `self.dG_max = float(np.max(np.abs(dG_cell)))`；
`suggest_dt` 用 `dt = cfl*dx/(M*dmax)`。
`dG_cell` 不含 `Mfac` => 在 `Mfac` 小的界面上 dt 最多**保守 33 倍**（白算）。
**不是错误**，但显著浪费机时。

### #4 `nv=1` 时 `Mfac` **静默失效**（中，健壮性）

**代码**：`_need_ref = (pair_aniso and aniso>0) or (mob_aniso>0) or (mob_beta>0)`
后跟 `if _need_ref and getattr(self,'ncmp',None) is not None:`。
而 `self.ncmp` 只在 `C is not None and eps0 is not None` 时才建。
=> 若只跑"单变体 vs 母相"（`nv=1`、无 eps0），`ncmp=None` => `nd_ref_=None`
=> **`mob_beta` 完全不生效，且不报错**（本项目明令禁止的静默失败）。

**复现**：`_audit_mfac_ratio.py`（用 nv=1）=> 三个方向的实测位移**完全相同**（2.5e-8 m），
且 = `M*df*dt`（即无任何 Mfac）——一眼就能看出调制被跳过。

### #5 `_stefan` 的溶质再分配用 `np.roll`（**周期边界**）（低-中）

**代码**：`for d in (6 个邻居): nb = np.roll(swept, d, axis=(0,1,2)) ... self.c += ...`
`np.roll` 是**周期性**的 => 位于**域边界**的界面扫过时，排出的溶质会**从对面边界冒出来**
（非物理）。界面远离边界时影响小，但记账上必须知道。

### #6 `mob_aniso` 与 `mob_beta` **无互斥保护**（低）

两者都是 `if`（不是 `elif`）=> 同时给非零会**相乘**（双重调制）。
当前所有调用都只给其中一个，但缺少阻止误用的保护。

### #7 `_rank1_axes` 的 `w` 与种子长轴 `along` 不一致（低）

`_chk_m6_route.py` 里用 `_al = np.cross(npref, g.wtab[v+1])`
= `n x (n x a) = n(n.a) - a`。而 `n.a = cos(82.7 deg) = 0.127 != 0`
（rank-1 分解中 `a` 不要求垂直于 `n`）=> 种子长轴**偏离真 `a` 约 7.3 deg**。

### #8 `curvature_of` 用 `np.gradient`（一阶边界处理）（中）

**代码**：`curvature_of` = `sum(np.gradient(n[i], dx)[i])`，其中 `n = grad(phi)/|grad(phi)|`。
`np.gradient` 默认 `edge_order=1`（边界一阶）；对**只有数胞厚**的薄片，
`kappa` 的二阶导误差本就大（这是 #8 与"等轴化"怀疑链的一环）。

### #9 `elastic_driving` 用 **hard `region` 指示场**（中）

**代码**：`self.pf.phi[v] = (reg == v+1)`（0/1 硬指派）而不是平滑相场。
=> 界面胞的 `eps0` 分布是阶梯状 => FFT 谱法解出的 `sigma` 在界面处有
**O(1) 阶梯噪声** => 驱动 `ed` 在界面附近被污染。

### #10 `_finish_advance` 里 `reg` / `reg_adv` 重复赋值（无害）

`reg = self.region(); reg_adv = self.region()`（中间无修改）=> 冗余。
逻辑**正确**（`reg_adv` 确实取在 `reinitialize()` 之前 => 只反映平流扫过），只是重复计算。

---

## B 已验证无误（审计确认）

| 检查 | 判据 | 结果 |
|---|---|---|
| **推进方向符号** | `_audit_dir.py`：1D 平面界面、两种 `karr/larr` 顺序 | `phi_1` 减小、`phi_0` 增大、界面前进 **0.15 dx = 恰好 CFL** => 我一度怀疑的 `coef = sigma(本胞) x vcanon(界面胞)` **设计正确**（`sigma` 是逐胞定向，`vcanon` 是跨界面连续量） |
| `Mfac` 数值 | `_dbg_mfac.py` | 0.0301/0.0999/1.0000，与解析值逐位一致 |
| `_rank1_axes` 选解 | `_chk_rank1.py` | n vs npref **12/12 <15 deg**；w 与 npref 正交 12/12 |
| `_stefan` 守恒 | 代码审查 | 排出量按 `NRECV=7`（6 邻居+自己）等分 => 精确守恒 |
| `update_Gamma` | 代码审查 | 已改**保守边通量形式**（`F_ij = -D_s A_e (Gamma_j-Gamma_i)/l_ij`，切向投影）=> 逐位守恒、不跨界面扩散 |
| `seed_plate` 多核 | 代码审查 | `min`(本场) / `max`(他场) 累积语义正确（多核取并集）|

---

## C 仍未定位：等轴化的主因

**已被排除**（每条都有实验）：弹性驱动（NE1/NE0：1.47 vs 1.54）、
迎风格式（C1/U1：长/厚 2.51 vs 2.58 不变）、种子形状（E6/E1）、
重初始化频率、速度扩展带宽、凸各向异性强度（aniso 0->0.9 零效果）、`Mfac` 实现。

**剩余嫌疑（本轮审计后的排序）**：
1. **#9** 弹性驱动的 hard-region 阶梯噪声（界面处 `ed` 被污染）
2. **#8** 曲率 `kappa` 的离散（薄片只有几胞厚）
3. **#2** `w` 方向的异常压制（与 #1 同源或独立，未分离）

---

## D 附：本审计用到的判据脚本

```text
_audit_dir.py            推进方向符号（两种 karr/larr 顺序）
_audit_mfac_ratio.py     平面界面 v/(M*df*Mfac)，nv=1（暴露 #4）
_audit_mfac_ratio2.py    同上，nv=12（暴露 #1/#2）
_audit_ratio3.py         射线口径重测（该口径本身有缺陷，见文档）
_run_advgrad.py          C1(central) vs U1(upwind) 长时程对照
```

---

## E 修复状态（2026-09-26，10 项全部完成）

| # | 修复 | 验证 |
|---|---|---|
| **1** | `adv_grad` 默认 `'upwind' -> 'central'`（含记账）| `inspect.signature` 确认默认已变；方向回归通过 |
| **2** | 撤回（判据缺陷，非代码问题）| `_dbg_vnk.py` 中位数 1.066 |
| **3** | `dG_max` 改为**含 Mfac 的有效驱动**（Mfac 应用后重算；未开 Mfac 时保持原值 => 向后兼容）| 位移仍 = 0.15 dx |
| **4** | `_need_ref` 不再要求 `ncmp` 非空；缺失时退化为只用 `npref` | 代码审查 + nv=1 不再静默跳过 |
| **5** | `_stefan` 改**非周期移位**分配（越界份额留源胞）；接收者数由实际决定 | 体+面守恒 1.49e-14（与修复前同）|
| **6** | `mob_beta` 与 `mob_aniso` 同时非零 => `raise ValueError` | 代码审查 |
| **7** | 新增 `atab`（真长轴 a）；实测旧法 `n x w` 与真 a 差 **7.6-8.2 deg** | 数值验证 |
| **8** | `curvature_of` 用 `edge_order=2` | 首次修改引入 `[i]` 索引 bug，被回归抓住并修好 |
| **9** | 新增 `elastic_driving(soft=True)`：平滑指示场 `0.5(1-tanh(phi/1.5dx))`；**默认 False** | 代码审查 |
| **10** | 去掉 `_finish_advance` 里重复的 `self.region()` | 回归通过 |

**总回归**：`_audit_dir.py`（方向，两种 karr/larr 顺序）、`_dbg_vnk.py`（Mfac：1.161/1.066/0.938）、
3 步 smoke（默认路径）—— **全部通过**。

⚠ **#1 的默认值变更意味着审计前的所有 level-set 结果需重跑**才算与当前代码一致。
