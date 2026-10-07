#!/bin/bash
# _t5_git_s89.sh --- 提交第 89 轮（避开 PowerShell 引号地狱）
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/R581_T5_RESTART.md pipeline/ca_pf_framework/_t5_append_s89.sh
git commit -F - <<'MSGEOF'
R581-T5R-s89 观察到潜在设计冲突: blk_laths 恒等于 nslab_n => 所有板条在同一个块里, 且 n_var_sig=1 => 单变体单块

判据④(块间 nf2>0) 与 ⑥(多变体) 都要求"多"; abA 满足过(320/620/2580)。

怀疑: --nvar 3 --m 24 破了场封顶, 但可能把形核都引向同一变体组。
现在不能定论(配置不同 + 尺度 620 未到)。

若成立则有可行解 --nvar 2 --m 36 (nv=72 不变, m=36>=23, nvar>=2)。
列为第一优先待查项; 不动长跑。
MSGEOF
git log --oneline -1
