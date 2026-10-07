#!/bin/bash
# _t5_git_s226.sh --- 提交终态自动分析（v2，修正判据）
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_finalwatch.py pipeline/ca_pf_framework/_t5_finalwatch2.py \
        pipeline/ca_pf_framework/_t5_alive.sh 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s226 终态自动分析(v2): 修 v1 的真 BUG —— 进程名判据把在跑的臂全判成"已结束"

缺口(真实): 剂量-响应的关键交付是各臂 1400 步时的终态长宽比; 而监控 _t5_armon.py 只是周期性测当前快照
=> 若某臂结束时无人读, 它的终态就没人记录。=> 起"终态自动分析"作业补上。

★ v1 的 BUG(我自己的错, 留痕): v1 用 `ps -eo args` 里找 `dry_<tag>` 判断"臂是否还在跑",
实测**把 7 个还在跑的臂全判成"已结束"**, 并记下 step=40 当"终态"(真终态是 1400)。
症状正是"量具错了和被测量对象错了长得一模一样"(P6); 而它**没有任何正对照**就上了
=> 违反本仓库第 19 条纪律(探针必须先做正对照)。

v2 的修正判据(自洽, 不依赖进程名): 一个臂"已结束" ⟺ 同时满足
 1) 末步连续 6 次(3 min)检查完全不变; 且 2) 末步 >= 目标步数(1400) 或 日志出现结束标志。
=> 条件 1 单独不够(跑得慢时也会"不变") => 必须与 2 同时成立; 记录一律带上 step(第29条)。

实测: v1 的记录(step=40 当终态)**全部作废**, 已在日志里声明; v2 pid=30212 运行中。
MSGEOF
git log --oneline -1
