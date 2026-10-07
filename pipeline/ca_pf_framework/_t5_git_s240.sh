#!/bin/bash
# _t5_git_s240.sh --- ★★★★★ 三路监控就位 + t5N276 早期读数（长宽比已达标）
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_blkmon.py pipeline/ca_pf_framework/_t5_blkmon_restart.sh \
        pipeline/ca_pf_framework/_t5_blkcol.sh pipeline/ca_pf_framework/_t5_n276read.sh 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s240 ★★★★★ t5N276 三路监控就位 + 早期读数（长宽比/长厚比已达标）

## 目标（用户）：持续跟进 t5N276 —— ①长宽比 ②长厚比 ③是否成块 ④块间是否相互影响
## 缺口：原监控 `_t5_armon.py` 只测**几何量**（覆盖①②），**不读块表列** ⇒ ③④ 无量具
=> 新建 `_t5_blkmon.py`（每 5 分钟读 series.csv），覆盖：
   ① 生长（Vt/nslab_n/nf3_col/runs）· ③ 成块（**nblk_sig**/blk_laths/runs）
   ④ 块间影响（**nf2**/f2_area_m2）· ⑤ 自协调（**n_var_sig**/r_selfac）

## ★ 抓到并修掉一个**判据 bug**（我自己的）
第一版用 **`nf2` 非空** 判断"块表行" —— **错**：
 * `nf2` 是**常规列**（每行都有值）；而**块表值只在 `step` 的 100 倍数行**；
 * ⇒ 旧判据把普通行（step 140）当块表行 ⇒ **永远读不到 `nblk_sig`**。
实测确认（`_t5_blkcol.sh`）：块表值出现在 **step 0 / 100**。
=> **修正：块表行 = `nblk_sig` 非空**（重启后正确报出 step=100）。

## t5N276 早期读数（19:53–19:54）
```
① 进度：末步=140 · 快照=4 · 引擎存活 ✓
② 几何：step 0 1.86/1.87（种子） → **step 80 长宽比 6.65 · 长厚比 12.17**
        => ★ **已进入真实板条区间（5–20 / 10–50）** ⇒ eng-elong=7 在 nv=276 上同样有效；
           且与 nv=72 的 t5AD_700（step40 6.66/12.15）几乎相同 ⇒ **nv 不改变几何**
①' 生长：Vt=2.868 µm³ · nslab_n=6 · **nf3_col=5 = nslab_n−1**
        => **每根板条都被低角晶界分开** —— 这是"成块"的**正确结构** ✓
③ 成块：**nblk_sig=1** · blk_laths=**3**（step 100）=> 1 个块含 3 根板条（**早期**）
④ 块间：**nf2=0** => 块间**尚未相遇**（符合早期预期）
⑤ 自协调：**n_var_sig=1** · r_selfac=1.0 => 目前**单变体**（早期）
```
## 记账
* 内存：用 16032 / 余 7821 MB ⇒ 健康；
* 三路监控并存：`_t5_armon.py`（几何）· `_t5_blkmon.py`（块/块间）· `_t5_mon_keeper.sh`（守护）；
* ⚠ 日志里两行 `nf2: command not found` 是我写日志时**反引号未转义**的笔误 —— **不影响监控**。
MSGEOF
git log --oneline -1
