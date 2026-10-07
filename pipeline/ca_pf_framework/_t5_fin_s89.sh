#!/bin/bash
# _t5_fin_s89.sh --- 补跑第 89 轮的文档追加并提交（上一次脚本漏了 append）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
bash _t5_append_s89.sh || exit 1
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/R581_T5_RESTART.md
git commit -F - <<'MSGEOF'
R581-T5R-s89b 补交滚动记录的 §89 (上一脚本漏跑 append, 只提交了脚本本身)

内容: 潜在设计冲突 —— blk_laths 恒等于 nslab_n => 单变体单块,
而判据④⑥ 要求"多"; 可行解 --nvar 2 --m 36; 列为第一优先待查项, 不动长跑。
MSGEOF
git log --oneline -2
