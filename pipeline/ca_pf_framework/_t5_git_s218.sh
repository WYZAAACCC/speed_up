#!/bin/bash
# _t5_git_s218.sh --- 提交监控守护
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_mon_keeper.sh pipeline/ca_pf_framework/_t5_ab_dose.sh \
        pipeline/ca_pf_framework/_t5_res.sh 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s218 监控守护: 监控若结束/退出则自动续起(保证"持续"监控)

为什么: _t5_armon.py 只跑固定轮数(80 轮 ≈ 6.7 h), 而 t5V2 还要跑 10+ h
=> 监控会在长臂跑完前就停 => 与"持续监控"不符。
做法: _t5_mon_keeper.sh 每 600 s 检查一次; 若监控进程不在(结束或崩溃), 就 setsid 续起 80 轮;
共 400 轮 ≈ 66 h。安全: 不删任何日志(一直 >>); 不用 pkill/pgrep -f(自匹配坑 §215),
用 ps + 方括号技巧; 内存开销可忽略。
实测: 守护 pid=28448 已起; 监控 pid=27802 存活。

另: 备好剂量-响应 A/B(_t5_ab_dose.sh, eng-elong 0/3.75/5/7, N=80/400步, 语法已验证),
但**现在不起** —— 现有 5 个 bk_exp 进程用 10.9 GB, 再起 4 臂(各 ~2.5 GB)会到 ~21 GB,
距本机 22 GB 上限只剩 1 GB => 有 swap 抖动/整机卡死风险(AGENTS.md §3.12 实测过)。
=> 等当前四臂跑完(~1h)后再起。这是主动的资源约束决策, 不是遗漏。
MSGEOF
git log --oneline -1
