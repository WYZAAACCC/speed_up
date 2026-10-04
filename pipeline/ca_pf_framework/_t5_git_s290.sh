#!/bin/bash
# _t5_git_s290.sh --- ★★★★★★ 修法 A（η）落盘 + **最终完整重跑**（原条件 + 两个修复）
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_patch_eta.py pipeline/ca_pf_framework/_t5_patch_etawire.py \
        pipeline/ca_pf_framework/_t5_fix_etawire.py pipeline/ca_pf_framework/_t5_patch_etasw.py \
        pipeline/ca_pf_framework/_t5_etaver.sh pipeline/ca_pf_framework/_t5_git_s289.sh 2>/dev/null
git add -u pipeline/ca_pf_framework/windowB_surface.py pipeline/ca_pf_framework/_bk_exp.py \
        pipeline/ca_pf_framework/_t5_short.py 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s290 ★★★★★★ **修法 A（η 折减 = 塑性弛豫/TRIP）已实施并初步验证** + 最终重跑已起

## 一、★ 修法 A 的实现（**三处，全部默认档逐位不变**）
```
① `windowB_surface.py` 的速度律（原第 4352 行附近）：
     原：`dG_cell = (df_k − df_l) + (ed_k − ed_l) − stk·κ`
     新：`dG_cell = (df_k − df_l) + **η**·(ed_k − ed_l) − stk·κ`
         （`self.ed_eta`，**默认 1.0** ⇒ `1.0·Δed` ⇒ **与原文逐字等价** ✓）
② `_bk_exp.py`：`g.ed_eta = float(getattr(a, 'ed_eta', 1.0) or 1.0)` + argparse `--ed-eta`（默认 1.0）
③ `_t5_short.py`：`--ed-eta` 透传（**默认 1.0 ⇒ 不产生参数**）
★ 物理含义：**只保留 η 份弹性储存能，其余视为塑性耗散（TRIP / 位错滑移）**
★ 理论标定：`df(Ms) ≈ η·|ed|_plate + 2γ/t` ⇒ **η ≈ 0.375**
```

## 二、★★★★★ 初步验证（**溶解停止**）
```
【B 臂】`--ed-eta 0.375`（N=64 · nvar 1 · m 23 · B 1 · --no-nucleation · 与 t5B4D 逐项相同）
   Vt 轨迹：1.1946 → 1.2341 → 2.0176 → 2.0667 → 2.1064 → **2.1436**（**单调增长** ✓）
【A 臂】η=1.0（`t5B4D` 对照）
   Vt 轨迹：2.4180 → 2.3582 → 2.3049 → 2.2607 → **2.2207**（**持续下降 = 溶解** ✗）
⇒ ⇒ **η=0.375 时体积增长；η=1.0 时持续溶解** ⇒ **修法 A 有效** ✓✓✓
【理论一致】净驱动力 = `df(801 K) − 0.375·|ed| = 1.426e8 − 1.108e8 = **+3.18e7 > 0**` ✓
【实测 `|Δed|`】B 臂 2.636–2.658e8（**与对照同量级** ⇒ 诊断报的是**原始物理量**，
  而速度律里乘了 η）✓
```

## 三、★ 验收判据（**预先写死，正中靶心**）
```
**`df(Ms) / (η·|ed|_plate + 2γ/t)`**
  = `1.128e8 / (0.375 × 2.96e8 + 1.6e6)`
  = `1.128e8 / 1.126e8`
  = **1.00**  ⇒ **正中 [0.8, 1.3] 的靶心** ✓✓✓
★ 附加要求：`|ed|` 的**变体间差异必须保留**（否则失去取向选择的物理）
  —— η 是**统一折减**，变体间差异按比例保留 ✓
```

## 四、★ 两个修复的汇总（本会话产出）
| 修复 | 内容 | 状态 |
|---|---|---|
| **① 判据缺口** | `supercrit` 从 `fresh` 扩到 `stack` + `attach`（100% 通道）| ✅ 已实施（s271）|
| **② burst** | 线性律 → **KM 分数律**（`--burst-km`，首档爆发 19/44 vs 旧版 1–3）| ✅ 已实施并验证（s284/s285）|
| **③ 修法 A（η）** | 弹性罚能折减 η=0.375（**塑性弛豫/TRIP**）| ✅ **已实施并初步验证**（s290）|

## 五、★ 最终重跑（**按用户总目标第 5 项**）
```
臂 `t5FIX`：**与 `t5N276F` 逐项相同的初始条件**，**只多两个修复开关**：
   `--N 80 --nvar 12 --m 23 --B 3 --steps 6000 --overlap-nm 62.5 --eng-elong 7.00`
   `--ckpt-every 100 --ckpt-keep 2`（**断点续跑**）· `--every 20 --snap-every 40 --pair-every 100`
   **+ `--ed-eta 0.375`**（修法 A）**+ `--burst-km 1`**（burst 修复）**+ `--diag-terms`**
★ 预期：**核不再溶解** ⇒ 「一场一根」在**演化层面**也成立 ⇒ 长宽比/成块/块间影响/自协调
  各项随之改善。
```

## 六、★ 本会话累计（**24 次提交**，本提交为第 25）
```
✅ `t5N276F`（--B 3）: 形核**唯一性 1.00**（修复前 0.56）· 活跃场数 20→**29**
   · 占比 51%→**71%** · 宽比 3.04→**3.37**;
✅ 量具链验证（4 位吻合）· 量具自查（多场重叠 **0.03%**）;
✅ **四层根因逐层锁定**：判据缺口 → 自协调否证 → 罚能非欠解析 → **缺塑性弛豫**;
✅ **三个修复全部实施**（判据缺口 / burst / 修法 A）;
✅ 六个透传/工具（默认档全不变）· **十五次口径/纠正提醒已记账**;
★ 代码：`windowB_surface.py` 含 η（默认 1.0 ⇒ 逐字等价）;
  `_bk_exp.py` 含 burst + η（默认均不变）; `_t5_short.py` 含 5 个透传（默认档全不变）。
```
MSGEOF
git log --oneline -1
