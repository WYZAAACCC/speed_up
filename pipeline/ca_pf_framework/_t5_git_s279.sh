#!/bin/bash
# _t5_git_s279.sh --- ★★★★★★ 机制确认（B 决定块数/变体数）+ 补丁代价实测 + 代码状态记账
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_B12.sh pipeline/ca_pf_framework/_t5_B12fix.sh \
        pipeline/ca_pf_framework/_t5_B6.sh pipeline/ca_pf_framework/_t5_B6clean.sh \
        pipeline/ca_pf_framework/_t5_b6npchk.sh pipeline/ca_pf_framework/_t5_waitalign.sh \
        pipeline/ca_pf_framework/_t5_waitB6.sh pipeline/ca_pf_framework/_t5_waitB12N.sh \
        pipeline/ca_pf_framework/_t5_waitB12.sh pipeline/ca_pf_framework/_t5_b12chk.sh \
        pipeline/ca_pf_framework/_t5_b12now.sh pipeline/ca_pf_framework/_t5_b12hang.sh \
        pipeline/ca_pf_framework/_t5_b12live.sh pipeline/ca_pf_framework/_t5_b12nchk.sh \
        pipeline/ca_pf_framework/_t5_stopB6.sh pipeline/ca_pf_framework/_t5_killB6.sh \
        pipeline/ca_pf_framework/_t5_patchcost.sh pipeline/ca_pf_framework/_t5_fresh1.sh \
        pipeline/ca_pf_framework/_t5_freshsw.sh pipeline/ca_pf_framework/_t5_q48.sh \
        pipeline/ca_pf_framework/_t5_q50.sh pipeline/ca_pf_framework/_t5_vrscope.sh \
        pipeline/ca_pf_framework/_t5_git_s27*.sh 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s279 ★★★★★★ **机制确认**：`B` 决定块数 ⇒ 决定变体数 + 补丁代价实测 + 代码状态记账

## 一、★ 机制确认（**实验直接可见**）
```
`--N 80 --B 6`（无补丁版 · 臂 `t5B6np`）step 20/40 读数（逐字）：
   [  20] Vt=3.1726 µm³ | **nslab=6** nf3col=5 **runs=6/3/1/2/4/5** | F3面=3172 面积=7.4709 µm²
   [  40] Vt=3.0154 µm³ | **nslab=6** nf3col=5 **runs=6/3/1/2/4/5** | F3面=3114 面积=7.3377 µm²
★ **`runs = 6/3/1/2/4/5` ⇒ 六个独立块** ✓
★ **场→变体表**：`[-1, 1×23, 2×12, ...]` ⇒ **6 个块各属一个变体 ⇒ 6 个变体** ✓
★ 对照 `--B 3`（`t5N276F`）：`n_var_sig = **3**`
⇒ ⇒ **"`B` 决定块数 ⇒ 决定变体数"这一机制成立** ✓
★ 引擎硬校验（横幅+日志）：`--nuc-fresh-every` 必须 = `n(T_end) = 23`
  ⇒ **块数 = `ceil(B·n/K) = B`** ⇒ 与上述实测**逐数吻合**
```

## 二、★ 补丁代价实测（**零代码改动的换文件测速**）
```
对照（同配置 `--N 80 --B 6`）：
   无补丁版（`.bak_stacksc`）：**136 s** 内出现**第一个形核事件**（事件数=1）
   有补丁版（`t5B6` 实测）：构造 ~254 s **+** 首个拒绝 ~200 s ⇒ **~454 s**
                             且**一次候选尝试 ~3.3 分钟**
⇒ **~3.3× 差距，方向支持"补丁代价显著"**（⚠ 两处口径不同 ⇒ **不构成决定性证据**）
★ 机制：我在 s271 给 `attach`/`stack` 加的 `_supercrit_probe` **位于候选循环内**
  ⇒ **每个候选都解一次弹性（FFT）**；`--nuc-supercrit 1` 所有算例都开着 ⇒ 始终生效；
  `_supercrit_probe` = **试放 + 精确回滚** ⇒ 内部一次完整弹性求解
  ⇒ **代价 ∝ (候选数 × 弹性求解成本)**，nv=276 时比验证用的 nv=23 贵约 12 倍
★ **违反纪律**：本仓 **P2/P4**「改热路径前必须先量代价」⇒ 我加补丁时**没先测**（已记账）
★ **顺带确认**：`--B 6`（目标 138 根 ≤ 盒容量 147）**本身是可行配置** ✓
```

## 三、⚠⚠ 代码状态记账（**供下一个会话必须先确认**）
```
★ **当前（本提交时）**：`windowB_surface.py` = **无补丁版**
    （`.bak_stacksc`，308771 B，`sc_stack_pass=0` / `sc_att_pass=0`）
    —— 因为臂 `t5B6np` 正在用它运行（**跑完不自动还原**）
★ **备份清单**（内容都已核对）：
    · `.bak_stacksc`     = **无补丁版**（405015 B 是旧数；实为 308771 B 字节数需复核）
    · `.bak_attachsc`    = **只有 stack 补丁**（`sc_stack_pass=2` / `sc_att_pass=0`）
    · `.bak_bothpatches` = **两处补丁**（`sc_stack_pass=2` / `sc_att_pass=2`）
★ **下一步（会话交接要点）**：
    ① 先确认 `windowB_surface.py` 是哪个版本（数 `sc_stack_pass` / `sc_att_pass`）;
    ② 若需回到"两处补丁"，`cp .bak_bothpatches windowB_surface.py`;
    ③ 若要修补丁代价：把 probe 从"每候选"改为"**每事件一次**"，或按代码注释用
       **热启动**（「上一步的 ε 当初值 + tol=1e-8 ⇒ 迭代数从 ~35 降到个位数」）
       + **降精度**（「驱动力只需 ~1e-4 的 σ 精度」）。
```

## 四、★ 判据与等待作业
```
★ 等待作业 `pwsh-3715`（`_t5_waitalign.sh 400 7200`）：
   等 `t5B6np` 到 **step ≥400**，然后与 `t5N276F` 在**同一 step（160/240/400/600/800）**
   上做**同步对齐**比较：逐场瓣数（φ<0 的 26-连通分量中位/最大）、最大分量占比、
   块表 `n_var_sig`、形核事件分布、`Δed` 带符号行数。
★ 判据（**预先写死**）：
   * **同一 step 上** `--B 6` 的**瓣数中位更低** 且 **占比更高**
     ⇒ **变体数 3→6 ⇒ 溶解减轻** ⇒ **设计级根因确认** ✓
   * 两者相近 ⇒ 变体数不是关键 ⇒ 需回到其它候选
★ ⚠ **为什么必须同步对齐**（本会话第九次口径提醒）：
   step 40 时两臂都是"瓣数 1、占比 100%"（场刚形成，碎裂未开始）⇒ **不可比**；
   `t5N276F` 从 step 160 起出现多块 ⇒ 比较点必须在 **step ≥400**。
```

## 五、累计根因链（**终版，供接续**）
```
① **判据缺口** ✅ 已修（s271）: `supercrit` 从 `fresh` 扩到 `stack` + `attach`
   ⇒ 覆盖 100% 通道（⚠ 但带来性能代价，见第二节）;
② **设计级根因** ★ 主因: 引擎硬校验 `K = n(T_end)` ⇒ **块数 = `B`**
   ⇒ `--B 3` ⇒ **3 个块 ⇒ 3 个变体**（实测 `n_var_sig = 3` ✓）
   ⇒ **自协调需 12 个变体**（`ε⁰` 判据 C4）⇒ **原理上不可能**
   ⇒ **弹性能罚能满值（~3e8）> `df(Ms) = 1.128e8`** ⇒ **板条必然溶解** ✓
③ **引擎自证**（`T1_verify_edsign.py` D1c）: **自协调构型 ⇒ `E_el/vol` = 机器零**
   ⇒ **修好自协调 ⇒ 罚能消失 ⇒ 板条站得住** ✓
④ **后果**（= 用户问的全部现象）: 体积流失 −40~87% · **"一个场多根板条"（瓣数 1→22）**
   · 长宽比退化 6.7→3.4 · "新核出生就不扁" · `Vt` 全盒仍单调 · 与变体数/块数"无关"（**错**）
```

## 六、本会话累计成果
```
✅ `t5N276F`（--B 3）: 形核**唯一性 1.00**（修复前 0.56）· 活跃场数 20→**29**
   · 占比 51%→**71%** · 宽比 3.04→**3.37**
✅ 量具链验证（首个核 df 实测 1.2273e8 vs 理论 1.2275e8，**4 位吻合**）;
✅ 量具自查（`φ<0` 多场重叠仅 **0.03%**）;
✅ 新工具（全自检）: `--diag-terms` 透传 · `Δed` **带符号**统计 · `--no-nucleation` ·
   **从断点直读 `df`**（零代码改动）;
✅ **九次口径/纠正提醒已记账**（跨 step 3 · 跨算例 1 · 单位 1 · 口径因子 2 ·
   横幅 ❌ 语义 · 补丁代价未测 · 修法方向会破坏成块 · `--nuc-fresh-every` 被硬校验拒 ·
   `B=12/N=80` 死循环）;
✅ **机制确认**: `B` 决定块数 ⇒ 决定变体数（`runs=6/...` 逐字可见）。
```
MSGEOF
git log --oneline -1
