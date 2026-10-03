#!/bin/bash
# _t5_git_s269.sh --- ★★★★★★ 根因链条落盘 + 修法范围缺口（用户总目标的核心进展）
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_patch_nonuc.py pipeline/ca_pf_framework/_t5_fix_nonuc.py \
        pipeline/ca_pf_framework/_t5_patch_diag.py pipeline/ca_pf_framework/_t5_patch_edsign.py \
        pipeline/ca_pf_framework/_t5_patch_edsign2.py pipeline/ca_pf_framework/_t5_B4Sdiag.sh \
        pipeline/ca_pf_framework/_t5_B4S2.sh pipeline/ca_pf_framework/_t5_B4Dclean.sh \
        pipeline/ca_pf_framework/_t5_B4Schk.sh pipeline/ca_pf_framework/_t5_readdf2.py \
        pipeline/ca_pf_framework/_t5_bandgap.py pipeline/ca_pf_framework/_t5_readv.sh \
        pipeline/ca_pf_framework/_t5_readdG.sh pipeline/ca_pf_framework/_t5_readdf.sh \
        pipeline/ca_pf_framework/_t5_readel.sh pipeline/ca_pf_framework/_t5_readfcrit.sh \
        pipeline/ca_pf_framework/_t5_readext.sh pipeline/ca_pf_framework/_t5_edsign.sh \
        pipeline/ca_pf_framework/_t5_dgchk.sh pipeline/ca_pf_framework/_t5_git_s265.sh \
        pipeline/ca_pf_framework/_t5_git_s26*.sh pipeline/ca_pf_framework/_t5_1to1.sh 2>/dev/null
git add -u pipeline/ca_pf_framework/windowB_surface.py pipeline/ca_pf_framework/_bk_exp.py \
        pipeline/ca_pf_framework/_t5_short.py 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s269 ★★★★★★ 根因链条完整：**形核判据与演化驱动力不是同一个量** + 修法范围缺口

## 一、★ 根因（**实测链条，每一步都有数据**）
```
① **演化驱动力**（`windowB_surface.py:4352`，逐字）：
     dG_cell = (df[karr] − df[larr]) + (ed_k − ed_l) − stk·κ
               └ 化学 ┘              └ 弹性 ┘        └ 曲率 ┘
     v_cell = M · dG_cell（`:4610`）⇒ **符号完全由 dG_cell 决定**
② **实测三项**（`--diag-terms`，F1 = 孤立种子的界面，N=64 单根算例 t5B4D）：
     化学 `df[1] − df[0]` = **+1.426e+08**（从断点直读，step 300，T=801.12 K）
     弹性 `Δed`          = **−2.955e+08**（**带符号**，`<0` 占 **100.0%**，10~90 分位 [−3.81e8, −2.02e8]）
     曲率 `−stk·κ`        = **−2.6e+06**（**只有弹性的 0.93%** ⇒ **可忽略**）
   ⇒ **净驱动力 `dG ≈ 1.43e8 − 2.96e8 − 2.6e6 = −1.55e8 < 0`** ⇒ **界面必然后退** ✓
③ **实测后果**（两个**独立**量具一致）：
     孤立种子体积 **1022 胞 → 128 胞（−87%）**；`band`(127) 与 `region`(128) **差 1 胞** ✓
     ⇒ **相真的在退回母相**（`_t5_dissolve.py`：失去的胞 43–94% 归属"无任何场 φ<0"）
④ **符号与量级都是对的**（`windowB_surface.py:3549-3559` docstring 逐字）：
     `ed[0]`（母相）**恒为 0**；`ed_k` 本就应当为负（**弹性能罚能**）——
     代码的独立判决给出球体 **−1.43e8 J/m³**，薄板实测 **−2.96e8**（**薄板罚能更大，合理**）
   ⇒ **⇒ 问题不在符号，而在"判据与驱动不是同一个量"**
⑤ **形核判据实际生效的形式**（`windowB_surface.py:2042` / `:2051`）：
     `(df + max_k ed_k) > 4γ/d`  —— **但这个判据由 `use_fcrit` 门控，默认 False**
     ⇒ 默认下**完全不比较** ⇒ 等价于"**只看弹性能项 > 阈值**"（`4γ/t ≈ 3.2e6`）
     ⇒ **在"弹性能有利"处播种，却不检查净驱动力够不够** ⇒ **核注定溶解**
```

## 二、★ 一句话根因
> **形核判据（默认生效的）只看"弹性能单项 > 阈值"，而演化用的是"化学 + 弹性能罚能"；
> 两者不是同一个量 ⇒ 模型会在**净驱动力为负**的位置/时刻播种 ⇒ 播下的核**出生即溶解**，
> 于是出现**体积流失、被啃成多块（"一个场多根板条"）、长宽比退化**。**

## 三、⚠⚠ **修法的范围缺口**（**必须随结论一起给，否则会误判"修好了"**）
```
windowB_surface.py:1583  判定式 `(df + max_k ed_k) > fcrit`；`df` 经 `nucleate(df=…)` 传入。
_bk_exp.py:1817          ⚠ 同样**只覆盖 `fresh` 通道**（范围缺口与 `use_fcrit` 相同）
_bk_exp.py:2539          **没有速率律**（`use_fcrit` 只覆盖 `fresh` 通道）。**不得含糊。**
★ 而 t5N276F 的事件分布实测：**attach 16 ｜ stack 9 ｜ fresh 2**（共 27）
  ⇒ **`--nuc-fcrit 1` 只影响那 2 个 `fresh` 事件 ⇒ 25/27 的事件不受判据约束**
  ⇒ **单开 `--nuc-fcrit 1` **不足以**修好问题** ⇒ 必须把判据**扩到 `attach`/`stack`**。
```

## 四、修法（两处，落点都已找到）
| # | 落点 | 现状 | 改成 |
|---|---|---|---|
| **①** | `windowB_surface.py:2051` 的 `if c.get('use_fcrit', False):` | **只在 `fresh` 分支内** | 让 `attach`/`stack` **也过同一判据** `(df + max_k ed_k) > 4γ/d` |
| **②** | `_bk_exp.py:2570` 的 `while n_ath_tgt < _tgt`（`_tgt = min(B·n(T), nv)`）| `n(T)=floor(α·ΔT)` **线性** ⇒ 每档恒 3 个核 ⇒ **无 burst** | 按 KM **分数律** `f(T)=1−exp(−α·ΔT)` 加权 ⇒ **Ms 附近爆发 + 随后饱和**（**物理正确**）|

## 五、★ 本批新增的**量具与工具**（全部自带自检）
* **`--diag-terms` 透传**（`_t5_patch_diag.py`）：R208 三项分离诊断，**F1 单列**;
* **`Δed` 带符号统计**（`_t5_patch_edsign.py` + `_t5_patch_edsign2.py`）：新增
  `med_ed_signed` / `frac_ed_neg` / `q10` / `q90` ⇒ **这是本轮定位根因的关键量具**;
  ⚠ 两处**纯记账**：`--diag-terms` 关时（默认）**逐位不变**;
* **`--no-nucleation`**（`_t5_patch_nonuc.py` + `_t5_fix_nonuc.py`）：**保留 `--grow-stack`**、
  只把 `--nuc-init` 设 0 ⇒ **t=0 播 1 片 + 零形核名额** = 真正的"单根"实验。
  ⚠ **踩过的坑（已记账）**：v1 连 `--grow-stack` 一起去掉 ⇒ `grow=False` ⇒ 引擎走
  **t=0 多片播种**分支（`_bk_exp.py:1636`）⇒ `nvar 1·m 23` 要播 23 片 × 0.51 µm = 11.7 µm > 盒 4 µm
  ⇒ `ValueError: margin −2.376e-06`（中心出盒）;
* **从断点直读 `df`**（`_t5_readdf2.py`）：`_bk_exp.py:674` 把 `df` 存进了 ckpt ⇒ **零代码改动**可核。

## 六、⚠ 本轮我犯并已记账的**比较错误**（第三次同类）
```
我一度报"化学项恒为 0"（依据是 `--diag-terms` 在 **step 20–60** 的读数），
而断点直读（**step 300**）给出 `df[1] = 1.426e8` **非零**。
⇒ **两者不矛盾：step 20–60 时 T 刚过 Ms ⇒ `drive_of_T(T) ≈ 0`（物理正确）**。
⇒ **纪律：诊断的每条读数都必须绑定它自己的 step**（跨 step 比较已第三次出错）。
```

## 七、当前算例状态
| 臂 | 用途 | 状态 |
|---|---|---|
| `t5N276F` | 修复版（问题 A：stack 建新场）| 运行中 · **唯一性 1.00** |
| `t5B3L` | 低密度判别（N=160 · 1 变体）| 运行中 |
| `t5B4D` | **单根 + 三项诊断**（本轮关键实验）| 运行中（N=64）|
| `t5B4S` / `t5B2` / `t5N276` | 前序判别臂 | 已跑完 |
MSGEOF
git log --oneline -1
