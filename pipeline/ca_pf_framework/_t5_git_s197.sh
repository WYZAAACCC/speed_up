#!/bin/bash
# _t5_git_s197.sh --- 提交"无管道重启"的修（head -6 的 SIGPIPE 风险）
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_autojudge_start.sh pipeline/ca_pf_framework/_t5_readlog.sh
git commit -F - <<'MSGEOF'
R581-T5R-s197 ★★★★ 修持久交接机制的致命缺陷(管道 head -6 ⇒ SIGPIPE 风险)

我在 job_list 里发现: 自动判定作业是 `bash _t5_auto_judge.sh 2>&1 | head -6` 启动的
=> head -6 读满 6 行就退出 => stdout 管道关闭 => 脚本之后每次 echo 触发 SIGPIPE
=> 整个持久交接机制有静默失效的风险(作业显示 running, 但管道对侧已关)。

修法: 新增 _t5_autojudge_start.sh —— 不用管道, 把 stdout/stderr 全部重定向到 F 盘日志,
并用 nohup + & 后台运行(不随父 shell 退出而死); 启动后 5 秒验证 pid 存活。
实测: pid=19900 存活, 正在写 _w2_t5_auto_judge.log。

教训(并入纪律): 凡"要长期后台运行并写日志"的作业, **绝不能用管道接到 head/tail 之类的短读端**
—— 短读端退出会导致 SIGPIPE 静默杀死写端; 一律用 `>> 文件` 重定向。
MSGEOF
git log --oneline -1
