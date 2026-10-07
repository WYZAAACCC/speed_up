#!/bin/bash
# _t5_git_s126.sh --- 提交第 126 轮
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/R581_T5_RESTART.md pipeline/ca_pf_framework/_t5_patch_handoff2.py \
        pipeline/ca_pf_framework/_t5_both.sh
git commit -F - <<'MSGEOF'
R581-T5R-s126 给「接手须知」补上 V2 臂 (否则接手者不知道它在跑)

原因: 接手须知只描述 t5H3; 而 t5V2 是判据③(多块)/④/⑥ 的唯一有路 =>
若不写明, 接手者会把另一条臂当野生进程, 或白等 t5H3 出多块。

补的内容: V2 的配置(--nvar 2 --m 36 --var-rule random, nv=72 内存不变)/
预登记判据(n_var_sig>1, nblk_sig>=2, nf2>0)/恢复命令/
为什么要它(t5H3 的 m=24 已用尽, 逐字消息"无可用空场/落位失败" @ step 801 => 封顶于 24)。

验证: 接手须知开头含 t5V2 / 含判据 / 含恢复命令 / 文档结构完好。
MSGEOF
git log --oneline -1
