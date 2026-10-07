#!/bin/bash
# _t5_git_s115.sh --- 提交第 115 轮（避开 PowerShell 引号地狱，用 heredoc）
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/R581_T5_RESTART.md pipeline/ca_pf_framework/_t5_patch_handoff.py
git commit -F - <<'MSGEOF'
R581-T5R-s115 更新接手须知里判据④⑥ 那一行 (§108 已把答案查明)

原因: 接手须知原写 "判定点 = 第 23 个形核事件", 而那个点已在 §106 到达、
答案已在 §108 查明 (fresh 被拒) => 若不更新, 接手的会话会去白等一个已过去的判定点。

改后: 判据 ④ 那行改为 "真因已查明(直接证据): fresh 通道每次尝试都被拒
(事件 #24: 23 attach + 1 次 fresh 被拒; abA 同期 5 个 fresh 成功)
=> 下一步 = 判系统性, 等事件 47/70 (~3.5h, 不需改代码)"。

验证: 过时文本已清除 / 新结论在 / 文档结构完好。
MSGEOF
git log --oneline -1
du -sh .git | cut -f1
