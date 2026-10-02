#!/bin/bash
# _t5_append_s101.sh --- 第 101 轮：逼近判定点（21/23 事件）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
cat >> R581_T5_RESTART.md <<'EOF'

---

## §101 第 101 轮：**逼近判定点**（形核 21 / K = 23）

### §101.1 读数
```
形核公告 = **21**（原 18）/ **被拒 0**        ← 距 K = 23 **只差 2 个事件**
离线块表（40 步）：
  step 520: nblk_sig=1  n_var_sig=1  blk_laths=18
  step 560: nblk_sig=1  n_var_sig=1  blk_laths=18
  step 600: nblk_sig=1  n_var_sig=1  blk_laths=18
```
**⇒ `blk_laths` = 18（= `nslab_n`）⇒ 18 根板条**仍全在同一个块里**；`n_var_sig` 仍 = 1。**

### §101.2 ★ 判据（**不变**，§93.4 预先写死）
| 条件 | 期望 |
|---|---|
| 事件数 ≥ 23 | 出现**第一个 `fresh` 事件**（= **新块**）|
| 同上 | **`n_var_sig` 应变为 > 1** |
| 同上 | **`nblk_sig` 应变为 ≥ 2** |

**⇒ **2 个事件后**（约 20–30 分钟）即到判定点 —— 那时再看，**在此之前不下结论**。**
EOF
echo "已追加，现在 $(wc -l < R581_T5_RESTART.md) 行"
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/R581_T5_RESTART.md pipeline/ca_pf_framework/_t5_append_s101.sh
git commit -F - <<'MSGEOF'
R581-T5R-s101 逼近判据⑥判定点: 形核 21 / K=23 (只差2个事件)

离线块表 step 520/560/600: nblk_sig=1, n_var_sig=1, blk_laths=18 (=nslab_n)
=> 18 根板条仍全在同一个块里。

判据不变(§93.4): 事件>=23 时应出现第一个 fresh 事件 / n_var_sig >1 / nblk_sig >=2。
2 个事件后(约20-30分钟)到判定点, 在此之前不下结论。
MSGEOF
git log --oneline -1
