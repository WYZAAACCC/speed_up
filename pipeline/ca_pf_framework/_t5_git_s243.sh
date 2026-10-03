#!/bin/bash
# _t5_git_s243.sh --- ★★★★★★ 更正：eng-elong 的长程崩塌 + ed 仍可多块
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_d1000fin.sh pipeline/ca_pf_framework/_t5_two_arms.sh \
        pipeline/ca_pf_framework/_t5_varrule_chk.sh pipeline/ca_pf_framework/_t5_rv_arm.sh \
        pipeline/ca_pf_framework/_t5_mon_all2.sh pipeline/ca_pf_framework/_t5_waitnr.sh \
        pipeline/ca_pf_framework/_t5_keeper_all.sh pipeline/ca_pf_framework/_t5_start_keeper_all.sh \
        pipeline/ca_pf_framework/_t5_keeper_chk.sh pipeline/ca_pf_framework/_t5_keeper_chk2.sh \
        pipeline/ca_pf_framework/_t5_blkmon.py pipeline/ca_pf_framework/_t5_armon.py \
        pipeline/ca_pf_framework/_t5_waitmile.sh 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s243 ★★★★★★ 两处重要更正：① eng-elong 长程崩塌 ② ed 仍可多块

## 触发：`t5AD_1000`（eng-elong=10）跑完（exit=0，step 1400，墙钟 11361 s）

### 更正①：**`--eng-elong` 的长宽比在长程中会**崩塌****（我先前说"稳定"的适用域太宽）
```
t5AD_1000  eng-elong=10:
  step  120 : 长宽比 **7.32**  长厚比 **14.47**   （早先读数）
  step 1240 : 长宽比 **1.26**  长厚比 **1.16**
  step 1280 : 长宽比 1.27     长厚比 1.15
  step 1320 : 长宽比 1.27     长厚比 1.15
  step 1360 : 长宽比 **1.24**  长厚比 **1.15**
```
=> **从 7.32 掉到 1.24（−83%）** ⇒ **我先前"≤2% / 5× 步数稳定"的结论**只在 step 40–200 成立**。**
**⇒ ⇒ 对正在跟踪的 `t5N276`（eng-elong=7，现 6.59）的直接含义：**
   **不能假定它会保持** —— **必须把"能保持多久"当作监控重点判据**（而不是"是否达标"）。

### 更正②：**`--var-rule ed` ⇒ 单**变体**，但**不排除多**块****
```
t5AD_1000 块表：
  step 100/200/300 : nblk_sig=1  n_var_sig=1  blk_laths=3/6/9
  step 400         : **nblk_sig=2**  n_var_sig=1  **blk_laths=10/2**   ← **出现第二个块**
```
=> 我上一轮说"`ed` ⇒ 单变体 ⇒ **只有 1 个块**" —— **后半句错**：
   **"块"是**空间连通分量**，同变体的板条若分成两簇就是两块** ⇒ `nblk_sig` 可以 >1。
=> **但 `nf2` 仍需**异变体**才 >0** ⇒ **"同变体多块"不会让判据④ 达成** —— **这一条仍成立** ✓

### 同时确认的一件**好事**（对判据④）
`t5N276`（ed）已到 step 380、`nslab_n`=12，而 **`nblk_sig`/`n_var_sig` 仍恒 = 1、`nf2` 恒 = 0**
=> **六个块表点全部符合"ed ⇒ 单变体"的预测** ✓
=> 而 `t5NR`（random，20:18 起）已出 step 40、无错误 ⇒ **对照臂进入可比较阶段**。

## 本批同时落盘的工具
* `_t5_two_arms.sh`（两臂一行式状态）· `_t5_d1000fin.sh`（终态提取）
* `_t5_varrule_chk.sh`（从**进程命令行**证实 var-rule 取值）· `_t5_rv_arm.sh`（起 random 对照臂）
* `_t5_blkmon.py` **改为多臂**（第 3 参数 = 逗号分隔 tag）· `_t5_armon.py` TAGS += t5NR
* `_t5_keeper_all.sh` + `_t5_start_keeper_all.sh`（**三监控守护**，66 h）
* `_t5_waitmile.sh`（阻塞等 ★M；**已修 P48 的 `grep -c` 多行 bug**）
MSGEOF
git log --oneline -1
