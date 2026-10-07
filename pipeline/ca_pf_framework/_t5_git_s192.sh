#!/bin/bash
# _t5_git_s192.sh --- 提交自动判定作业
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_auto_judge.sh
git commit -F - <<'MSGEOF'
R581-T5R-s192 ★★★ 自动判定作业(结果写进 F 盘, 不怕会话结束)

为什么必须做: pwsh-2561/2562 的判定结果只出现在会话内的作业输出里 => 若会话结束结果就丢了,
而判定要 1-13 小时才出来。

本作业(_t5_auto_judge.sh, 已作为 pwsh-2579 运行)覆盖三个里程碑, 判据预先写死在既有工具里:
  M1  t5V2 形核事件 >= 23 或 fresh >= 1  => 跑 _t5_v2judge.sh (判 ④⑥)
  M2  t5H3 末步 >= 1400 / snap_01400     => 跑充填率序列(验"紧凑场 <6"的预测) + _t5_fill.py
  M3  t5H3/t5V2 的 nf2 > 0               => 判据④ 的直接签名, 一出现就报判决器 + 两臂健康
最多跑 6 小时; 每一步都追加到 F 盘的 _w2_t5_auto_judge.log, 任何人/任何会话都能读到。
MSGEOF
git log --oneline -1
