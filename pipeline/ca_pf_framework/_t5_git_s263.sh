#!/bin/bash
# _t5_git_s263.sh --- ★★★★★★ 阶段快照落盘（用户要求：先把当前状态 git 到本地）
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_whyB.py \
        pipeline/ca_pf_framework/_t5_dissolve.py \
        pipeline/ca_pf_framework/_t5_isreal.py \
        pipeline/ca_pf_framework/_t5_bandchk.py \
        pipeline/ca_pf_framework/_t5_bandtrack.py \
        pipeline/ca_pf_framework/_t5_bandcomp.py \
        pipeline/ca_pf_framework/_t5_wholost.py \
        pipeline/ca_pf_framework/_t5_steal.py \
        pipeline/ca_pf_framework/_t5_cut.py \
        pipeline/ca_pf_framework/_t5_1to1.sh \
        pipeline/ca_pf_framework/_t5_split3d.py \
        pipeline/ca_pf_framework/_t5_split3d2.py \
        pipeline/ca_pf_framework/_t5_bigstatus.sh \
        pipeline/ca_pf_framework/_t5_waitB2.sh \
        pipeline/ca_pf_framework/_t5_B3low.sh \
        pipeline/ca_pf_framework/_t5_B2verdict.py \
        pipeline/ca_pf_framework/_t5_276Fchk.sh \
        pipeline/ca_pf_framework/_t5_twoB.sh \
        pipeline/ca_pf_framework/_t5_mon_addB3L.sh \
        pipeline/ca_pf_framework/_t5_git_s26*.sh 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s263 ★★★★★★ 阶段快照：量具修正链 + 问题定位到"同场多瓣"

## 一、用户新目标（本轮下达，**总纲**）
1. **先把当前状态 git 到本地**（本提交）;
2. **彻查代码（一行一行）**：为什么**一个场里会有多根板条**;
3. 若数据不足 ⇒ **起实验**，保留足够判据信息，找出机制;
4. 找到并确认修复后 ⇒ **修 `burst`（当前不物理正确）**;
5. 全部解决后 ⇒ **按同样初始条件继续做大实验**;
6. **持续监控七项**：形核是否正确 / 新核是否板条状 / 长宽比变化 / 是否堆叠成块 /
   块间是否相互影响 / 是否自协调 / **一场是否只对应一根板条**;
7. 任一项出问题 ⇒ 找原因 ⇒ 修复 ⇒ **迭代到全部通过**。

## 二、量具修正链（**本轮之前的关键教训**）
| # | 我先前用的量具 | 问题 | 修正 |
|---|---|---|---|
| 1 | `region`（`argmin(φ)`）| **归属标签**，不是物理相 | 改用 **`band_val`（符号距离 φ）** |
| 2 | **整场 PCA 跨度** | 场被打散后，跨度 = 最远两点距离 | **改按 26-连通分量测** |
| 3 | `nslab_n`（引擎自报）| 有尺寸阈值 ⇒ 低估 | 并报**活跃场数** |
| 4 | 判据"宽比 ≥5" | **两条曲线都在降时无分辨力** | 改判**下降率 / 逐数对比** |

**★ 量具自洽校验**：由 `band` 算的相体积合计 = **18.003 µm³** vs `series.csv` 的 `Vt` = **18.19 µm³**
⇒ **差 1%** ⇒ **量具可信** ✓

## 三、已确认的事实（**物理量具**）
```
① **一个场**不是**一根板条**：场 2 的 φ<0 分量数 **1（step 120）→ 3（160）→ 10（1000）→ 22（1720）**;
② **主板始终是干净的长薄板**：L 4537→4109 nm（−9%）· W 681→726 · **T 310 不变** ⇒
   **"W/T 暴涨"是我先前整场跨度的假象**（已修正）;
③ **卫星块出现在**盒内另一处**（与主板相距 1.5–2 µm，**远大于界面宽**）
   ⇒ **不是"主板裂下的一角"，而是**同一场在别处出现了相****;
④ 被切掉的胞 **100% 变回母相**（不是被别的场拿走）⇒ **是"回退"，不是"重归属"**;
⑤ `Vt`（全盒）**严格单调** ⇒ 全盒无净溶解（但**逐场**在流失）;
⑥ 形核层面：**27 事件 → 27 个唯一场号** ⇒ 形核时场号唯一。
```

## 四、当前两个候选（**待判甲/乙**）
| # | 候选 | 性质 |
|---|---|---|
| **甲** | **`nfsv` 用 `reg` 判"场是否为空"** ⇒ 被吞掉的旧场"看起来是空的" ⇒ **重复播种旧场** | **代码逻辑缺陷** |
| **乙** | **`seed_plate` 的 `max(φ_j, −sdf)` 在**远处**写出负值**（代码注释已警告"`sdf` 的**正值小量**区间（例如 `1e3 → 0.2`）⇒ `argmin(phi)` 会翻"）| **播种式缺陷** |

## 五、本批落盘的工具（**全部是判据/量具，不含生产改动**）
`_t5_bandchk.py`（核实 band 含义 + 自洽校验）· `_t5_bandtrack.py`（物理量具逐场跟踪）
· `_t5_bandcomp.py`（按分量测，修正跨度假象）· `_t5_wholost.py`（①一场一块？②碎裂？③流失去向）
· `_t5_steal.py`（核验 attach 是否吃源场 ⇒ **已证伪**）· `_t5_cut.py`（定位切块来源 ⇒ **100% 回退**）
· `_t5_dissolve.py` · `_t5_isreal.py`（Vt 单调性）· `_t5_1to1.sh`（代码核验：无"一场一块"强制）
· `_t5_split3d*.py`（三维对比图）· `_t5_B3low.sh`（低密度判别臂）· `_t5_twoB.sh`（三臂步对齐）

## 六、新增实验臂
**`t5B2`**（1 变体 · B=1 · N=80 · **已跑完**，19 场 · 宽比 4.92）
**`t5B3L`**（1 变体 · B=1 · **N=160 低密度** · 运行中）
MSGEOF
git log --oneline -1
echo '── 工作区状态 ──'
git status --short | head -20
